/**
 * Custom hook for WebSocket connection management with auto-reconnect
 */

import { useEffect, useState, useCallback, useRef } from "react";
import { StreamingUpdate, EventType } from "@/types/streaming";

interface UseWebSocketOptions {
  url: string;
  onMessage?: (update: StreamingUpdate) => void;
  onError?: (error: Error) => void;
  onClose?: () => void;
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  initialReconnectDelay?: number;
}

export const useWebSocket = ({
  url,
  onMessage,
  onError,
  onClose,
  autoReconnect = true,
  maxReconnectAttempts = 10,
  initialReconnectDelay = 1000,
}: UseWebSocketOptions) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<StreamingUpdate | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log(`WebSocket connected to ${url}`);
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const update: StreamingUpdate = JSON.parse(event.data);
          setLastMessage(update);
          onMessage?.(update);
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
          onError?.(new Error("Invalid message format"));
        }
      };

      ws.onerror = (event: Event) => {
        const error = new Error("WebSocket error");
        console.error(error);
        onError?.(error);
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected");
        setIsConnected(false);
        onClose?.();

        // Auto-reconnect logic
        if (
          autoReconnect &&
          reconnectAttemptsRef.current < maxReconnectAttempts
        ) {
          const delay = initialReconnectDelay * Math.pow(2, reconnectAttemptsRef.current);
          console.log(
            `Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`
          );
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, delay);
        }
      };

      wsRef.current = ws;
    } catch (e) {
      const error = e instanceof Error ? e : new Error("Failed to create WebSocket");
      console.error(error);
      onError?.(error);
    }
  }, [url, onMessage, onError, onClose, autoReconnect, maxReconnectAttempts, initialReconnectDelay]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const send = useCallback((message: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    } else {
      console.warn("WebSocket is not connected");
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    send,
    disconnect,
  };
};
