import { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../services/api/client';

export interface MatchStreamState {
  /** The current game state dict from the backend */
  gameState: any | null;
  /** Current match status (queued, running, completed, failed, client_error) */
  matchStatus: string | null;
  /** Game type identifier (e.g. "tictactoe") */
  gameType: string | null;
  /** Ordered list of agent UUIDs */
  agentIds: string[];
  /** Match result data (scores, winner, etc.) */
  result: any | null;
  /** Logs from the match execution */
  logs: string;
  /** Whether the SSE connection is active */
  isConnected: boolean;
  /** Error message if connection failed */
  error: string | null;
}

const TERMINAL_STATUSES = ['completed', 'failed', 'client_error'];

/**
 * Custom hook that connects to the match SSE stream and provides
 * real-time game state updates.
 *
 * Uses fetch-based streaming instead of EventSource because the stream
 * endpoint requires a Bearer token (spectating is login-only) and
 * EventSource cannot send an Authorization header.
 *
 * @param matchId - The UUID of the match to spectate
 * @returns Live match state, connection status, and any errors
 */
export function useMatchStream(matchId: string | undefined): MatchStreamState {
  const [gameState, setGameState] = useState<any | null>(null);
  const [matchStatus, setMatchStatus] = useState<string | null>(null);
  const [gameType, setGameType] = useState<string | null>(null);
  const [agentIds, setAgentIds] = useState<string[]>([]);
  const [result, setResult] = useState<any | null>(null);
  const [logs, setLogs] = useState<string>('');
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastStatusRef = useRef<string | null>(null);

  const connect = useCallback(() => {
    if (!matchId) return;

    // Clean up previous connection
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const handleEvent = (data: any) => {
      setGameState(data.game_state ?? null);
      setMatchStatus(data.status ?? null);
      setGameType(data.game_type ?? null);
      setAgentIds(data.agent_ids ?? []);
      setResult(data.result ?? null);
      if (data.logs !== undefined) {
        setLogs(data.logs ?? '');
      }
      if (data.status) {
        lastStatusRef.current = data.status;
      }
    };

    const scheduleReconnect = () => {
      setIsConnected(false);
      if (lastStatusRef.current && TERMINAL_STATUSES.includes(lastStatusRef.current)) {
        return; // Match is over; nothing to reconnect to
      }
      setError('Connection lost. Reconnecting...');
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    };

    const run = async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/matches/${matchId}/stream`, {
        headers: {
          Accept: 'text/event-stream',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        signal: abortController.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Stream request failed with status ${response.status}`);
      }

      setIsConnected(true);
      setError(null);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by a blank line
        let separatorIndex;
        while ((separatorIndex = buffer.indexOf('\n\n')) !== -1) {
          const rawEvent = buffer.slice(0, separatorIndex);
          buffer = buffer.slice(separatorIndex + 2);

          // Collect the data lines; ignore comment lines (": keepalive")
          const dataPayload = rawEvent
            .split('\n')
            .filter((line) => line.startsWith('data:'))
            .map((line) => line.slice(5).trimStart())
            .join('\n');
          if (!dataPayload) continue;

          try {
            const data = JSON.parse(dataPayload);
            handleEvent(data);
            if (data.status && TERMINAL_STATUSES.includes(data.status)) {
              abortController.abort();
              setIsConnected(false);
              return;
            }
          } catch {
            // Ignore malformed payloads
          }
        }
      }

      // Server closed the stream (match ended server-side or connection dropped)
      setIsConnected(false);
      if (!(lastStatusRef.current && TERMINAL_STATUSES.includes(lastStatusRef.current))) {
        scheduleReconnect();
      }
    };

    run().catch((err: unknown) => {
      if (abortController.signal.aborted) {
        // Intentional close (cleanup or terminal state) — not an error
        setIsConnected(false);
        return;
      }
      console.error('Match stream error:', err);
      scheduleReconnect();
    });
  }, [matchId]);

  useEffect(() => {
    connect();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  return {
    gameState,
    matchStatus,
    gameType,
    agentIds,
    result,
    logs,
    isConnected,
    error,
  };
}
