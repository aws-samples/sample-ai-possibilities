import { useRef, useCallback, useEffect } from 'react';
import { WebSocketMessage } from '../types';

interface UseWebSocketProps {
  url: string;
  onMessage: (data: WebSocketMessage) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export const useWebSocket = ({
  url,
  onMessage,
  onOpen,
  onClose,
  onError,
  reconnect = true,
  reconnectInterval = 1000,
  maxReconnectAttempts = 5,
}: UseWebSocketProps) => {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      wsRef.current = new WebSocket(url);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        reconnectAttemptsRef.current = 0;
        onOpen?.();
      };

      wsRef.current.onmessage = (event: MessageEvent) => {
        const data: WebSocketMessage = JSON.parse(event.data);
        onMessage(data);
      };

      wsRef.current.onerror = (error: Event) => {
        console.error('WebSocket error:', error);
        onError?.(error);
      };

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        onClose?.();

        if (reconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(reconnectInterval * Math.pow(2, reconnectAttemptsRef.current), 30000);
          reconnectAttemptsRef.current++;
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      onError?.(error as Event);
    }
  }, [url, onMessage, onOpen, onClose, onError, reconnect, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const send = useCallback((data: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    send,
    disconnect,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  };
};