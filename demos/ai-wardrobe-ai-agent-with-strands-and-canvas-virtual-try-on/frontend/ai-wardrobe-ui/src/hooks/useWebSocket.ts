import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketMessage, ChatMessage } from '../types';
import { createWebSocketConnection } from '../services/api';

interface UseWebSocketProps {
  userId: string;
  onMessage?: (message: ChatMessage) => void;
  onWardrobeData?: (data: any) => void;
  onOutfitsData?: (data: any) => void;
}

export const useWebSocket = ({ userId, onMessage, onWardrobeData, onOutfitsData }: UseWebSocketProps) => {
  const ws = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const sessionId = useRef(`session-${Date.now()}`);
  const streamingMessage = useRef<ChatMessage | null>(null);

  useEffect(() => {
    if (!userId) return;

    // Close existing connection if any
    if (ws.current?.readyState === WebSocket.OPEN || ws.current?.readyState === WebSocket.CONNECTING) {
      ws.current.close();
    }

    const connect = () => {
      try {
        // WebSocket connection enabled
        console.log('Attempting WebSocket connection...');
        console.log('  sessionId:', sessionId.current);
        console.log('  userId:', userId);
        
        const websocket = createWebSocketConnection(sessionId.current);
        if (!websocket) {
          console.error('Failed to create WebSocket connection');
          return;
        }
        
        console.log('WebSocket created, state:', websocket.readyState);
        
        ws.current = websocket;

        websocket.onopen = () => {
          console.log('WebSocket connected');
          // Initialize session with user ID immediately
          if (websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({
              type: 'init',
              userId,
            }));
          }
        };

        websocket.onmessage = (event) => {
          const data: WebSocketMessage = JSON.parse(event.data);
          
          switch (data.type) {
            case 'init_complete':
              console.log('Session initialized');
              setIsConnected(true);
              break;
              
            case 'thinking':
              setIsThinking(true);
              break;
              
            case 'thinking_complete':
              setIsThinking(false);
              break;
              
            case 'stream':
              if (data.content) {
                if (!streamingMessage.current) {
                  streamingMessage.current = {
                    id: `msg-${Date.now()}`,
                    role: 'assistant',
                    content: data.content,
                    timestamp: new Date(),
                    isStreaming: true,
                  };
                  onMessage?.(streamingMessage.current);
                } else {
                  streamingMessage.current.content += data.content;
                  onMessage?.({
                    ...streamingMessage.current,
                    content: streamingMessage.current.content,
                  });
                }
              }
              break;
              
            case 'complete':
              if (streamingMessage.current) {
                onMessage?.({
                  ...streamingMessage.current,
                  isStreaming: false,
                });
                streamingMessage.current = null;
              }
              setIsThinking(false);
              break;
              
            case 'error':
              console.error('WebSocket error:', data.message);
              setIsThinking(false);
              break;
              
            case 'wardrobe_data':
              onWardrobeData?.(data.data);
              break;
              
            case 'outfits_data':
              onOutfitsData?.(data.data);
              break;
          }
        };

        websocket.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason);
          setIsConnected(false);
          // Don't auto-reconnect to prevent connection spam
          // User can manually reconnect if needed
        };

        websocket.onerror = (error) => {
          console.error('WebSocket error:', error);
          // Try to provide more meaningful error message
          if ((error as any).target?.readyState === WebSocket.CLOSED) {
            console.error('Failed to connect to WebSocket server. Make sure the backend is running on port 8080.');
          }
        };
      } catch (error) {
        console.error('Failed to connect WebSocket:', error);
      }
    };

    connect();

    return () => {
      if (ws.current?.readyState === WebSocket.OPEN || ws.current?.readyState === WebSocket.CONNECTING) {
        ws.current?.close(1000, 'Component unmounting');
      }
    };
  }, [userId]); // Remove callback dependencies to prevent unnecessary reconnections

  const sendMessage = useCallback((message: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'message',
        message,
      }));
      return true;
    }
    return false;
  }, []);

  const requestWardrobe = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'get_wardrobe',
      }));
    }
  }, []);

  const requestOutfits = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'get_outfits',
      }));
    }
  }, []);

  return {
    isConnected,
    isThinking,
    sendMessage,
    requestWardrobe,
    requestOutfits,
  };
};