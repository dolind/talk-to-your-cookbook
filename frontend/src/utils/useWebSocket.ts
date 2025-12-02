import {useEffect, useRef} from 'react';
import {GraphBroadCast} from "../lib/model.ts";

export const useWebSocket = (
    path: string,
    onMessage: (data: GraphBroadCast) => void
) => {
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        if (wsRef.current) return; // prevent duplicate connections

        const backendPort = 8000;
        const backendHost = 'localhost'; // or use `import.meta.env.VITE_API_HOST` etc.
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const ws = new WebSocket(`${protocol}://${backendHost}:${backendPort}/api/v1/ws/status`);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('[WS] Connected');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data?.message === 'ping') return;

                onMessage(data as GraphBroadCast);
            } catch (e) {
                console.error('[WS] Parse error:', e);
            }
        };

        ws.onerror = (e) => {
            console.error('[WS] Error:', e);
        };

        ws.onclose = () => {
            console.warn('[WS] Closed');
            wsRef.current = null;
        };

        return () => {
            console.log('[WS] Cleanup');
            ws.close();
            wsRef.current = null;
        };
    }, [path, onMessage]);
};
