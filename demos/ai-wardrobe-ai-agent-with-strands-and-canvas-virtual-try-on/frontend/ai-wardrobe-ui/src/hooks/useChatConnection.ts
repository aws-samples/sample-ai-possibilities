import { useEffect, useRef, useCallback } from 'react';
import { User } from '../types';

// Simplified, reliable WebSocket protocol
export interface ServerMessage {
  type: 'init_complete' | 'thinking' | 'thinking_complete' | 'stream' | 'virtual_tryon_loading' | 'virtual_tryon_result' | 'complete' | 'error';
  content?: string;
  tryOnImageUrl?: string;
  outfitData?: any;
  error?: string;
  message?: string;
}

export interface ClientMessage {
  type: 'init' | 'message';
  userId?: string;
  content?: string;
}

interface UseChatConnectionProps {
  user: User;
  onMessage: (message: ServerMessage) => void;
  onConnect: () => void;
  onDisconnect: () => void;
  onError: (error: string) => void;
}

export function useChatConnection({ 
  user, 
  onMessage, 
  onConnect, 
  onDisconnect, 
  onError 
}: UseChatConnectionProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return; // Already connected or connecting
    }

    try {
      const sessionId = `chat-${user.userId}-${Date.now()}`;
      const wsUrl = `ws://localhost:8080/ws/${sessionId}`;
      
      console.log('🔌 Connecting to WebSocket:', wsUrl);
      wsRef.current = new WebSocket(wsUrl);
      
      // Add connection timeout
      const connectionTimeout = setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CONNECTING) {
          console.log('⏱️ Connection timeout, closing and retrying...');
          wsRef.current.close();
        }
      }, 3000); // 3 second timeout

      wsRef.current.onopen = () => {
        console.log('✅ WebSocket connected');
        clearTimeout(connectionTimeout);
        reconnectAttemptsRef.current = 0;
        
        // Initialize session
        const initMessage: ClientMessage = {
          type: 'init',
          userId: user.userId
        };
        
        wsRef.current?.send(JSON.stringify(initMessage));
        onConnect();
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as ServerMessage;
          console.log('📨 WebSocket message received:', data.type, data);
          onMessage(data);
        } catch (error) {
          console.error('❌ Failed to parse WebSocket message:', error);
          onError('Failed to parse server message');
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('🔌 WebSocket closed:', event.code, event.reason);
        onDisconnect();
        
        // Attempt to reconnect if not a manual close
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(500 * Math.pow(1.5, reconnectAttemptsRef.current), 5000);
          console.log(`🔄 Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          onError('Connection lost. Please refresh the page.');
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        onError('Connection error occurred');
      };

    } catch (error) {
      console.error('❌ Failed to create WebSocket connection:', error);
      onError('Failed to establish connection');
    }
  }, [user.userId, onMessage, onConnect, onDisconnect, onError]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message = {
        type: 'message',
        message: content
      };
      
      console.log('📤 Sending message:', content);
      wsRef.current.send(JSON.stringify(message));
      return true;
    } else {
      console.error('❌ WebSocket not connected');
      onError('Not connected to server');
      return false;
    }
  }, [onError]);

  const isConnected = () => {
    return wsRef.current?.readyState === WebSocket.OPEN;
  };

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    
    return () => {
      // Cleanup function - prevent race conditions
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      
      if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
        try {
          wsRef.current.close(1000, 'Component unmount');
        } catch (error) {
          console.warn('Error closing WebSocket during cleanup:', error);
        }
        wsRef.current = null;
      }
    };
  }, []);

  return {
    sendMessage,
    isConnected,
    connect,
    disconnect
  };
}