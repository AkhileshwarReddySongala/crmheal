import { useEffect, useRef, useState } from "react";

export function useSSE(batchId, onBatchUpdate) {
  const [events, setEvents] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const pollingRef = useRef(null);

  useEffect(() => {
    if (!batchId) return;
    let closed = false;
    const source = new EventSource(`/api/events/${batchId}`);

    const startPolling = () => {
      if (pollingRef.current) return;
      pollingRef.current = window.setInterval(async () => {
        try {
          const response = await fetch(`/api/status/batch/${batchId}`);
          if (!response.ok) return;
          const batch = await response.json();
          onBatchUpdate?.(batch);
        } catch (err) {
          setError(err.message);
        }
      }, 2000);
    };

    source.onopen = () => {
      if (!closed) setIsConnected(true);
    };

    source.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data);
        setEvents((current) => [event, ...current].slice(0, 120));
        if (event.type === "status_update" || event.type === "ghost_persisted" || event.type === "ghost_skipped" || event.type === "ghost_failed") {
          fetch(`/api/status/batch/${batchId}`)
            .then((response) => response.json())
            .then((batch) => onBatchUpdate?.(batch))
            .catch(() => {});
        }
      } catch (err) {
        setError(err.message);
      }
    };

    source.onerror = () => {
      setIsConnected(false);
      setError("SSE disconnected, polling fallback active");
      startPolling();
    };

    return () => {
      closed = true;
      source.close();
      if (pollingRef.current) window.clearInterval(pollingRef.current);
      pollingRef.current = null;
    };
  }, [batchId, onBatchUpdate]);

  return { events, isConnected, error };
}
