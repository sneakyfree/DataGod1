/**
 * DataGod WebSocket Hook
 * Provides reconnecting WebSocket connection with typed events
 */

import { useEffect, useRef, useCallback, useState } from 'react';

interface WebSocketMessage {
    event: string;
    type?: string;
    title?: string;
    message?: string;
    data?: Record<string, any>;
    timestamp?: string;
}

interface UseWebSocketOptions {
    url?: string;
    userId?: string;
    token?: string;
    reconnectInterval?: number;
    maxReconnectAttempts?: number;
    onMessage?: (message: WebSocketMessage) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
}

interface UseWebSocketReturn {
    isConnected: boolean;
    lastMessage: WebSocketMessage | null;
    sendMessage: (message: Record<string, any>) => void;
    disconnect: () => void;
}

export function useWebSocket({
    url,
    userId,
    token,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    onMessage,
    onConnect,
    onDisconnect,
}: UseWebSocketOptions): UseWebSocketReturn {
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectAttemptsRef = useRef(0);
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>();
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

    const wsUrl =
        url ||
        `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:8000/ws/${userId || 'anonymous'}`;

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        try {
            const fullUrl = token ? `${wsUrl}?token=${token}` : wsUrl;
            const ws = new WebSocket(fullUrl);

            ws.onopen = () => {
                setIsConnected(true);
                reconnectAttemptsRef.current = 0;
                onConnect?.();
            };

            ws.onmessage = (event) => {
                try {
                    const message: WebSocketMessage = JSON.parse(event.data);
                    setLastMessage(message);
                    onMessage?.(message);
                } catch (e) {
                    console.warn('Failed to parse WebSocket message:', event.data);
                }
            };

            ws.onclose = () => {
                setIsConnected(false);
                wsRef.current = null;
                onDisconnect?.();

                // Attempt reconnection
                if (reconnectAttemptsRef.current < maxReconnectAttempts) {
                    reconnectAttemptsRef.current += 1;
                    const delay = reconnectInterval * Math.min(reconnectAttemptsRef.current, 5);
                    reconnectTimerRef.current = setTimeout(connect, delay);
                }
            };

            ws.onerror = () => {
                ws.close();
            };

            wsRef.current = ws;
        } catch (e) {
            console.error('WebSocket connection error:', e);
        }
    }, [wsUrl, token, reconnectInterval, maxReconnectAttempts, onMessage, onConnect, onDisconnect]);

    const sendMessage = useCallback((message: Record<string, any>) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
        }
    }, []);

    const disconnect = useCallback(() => {
        if (reconnectTimerRef.current) {
            clearTimeout(reconnectTimerRef.current);
        }
        reconnectAttemptsRef.current = maxReconnectAttempts; // Prevent reconnect
        wsRef.current?.close();
    }, [maxReconnectAttempts]);

    useEffect(() => {
        connect();
        return () => {
            if (reconnectTimerRef.current) {
                clearTimeout(reconnectTimerRef.current);
            }
            reconnectAttemptsRef.current = maxReconnectAttempts;
            wsRef.current?.close();
        };
    }, [connect, maxReconnectAttempts]);

    return { isConnected, lastMessage, sendMessage, disconnect };
}
