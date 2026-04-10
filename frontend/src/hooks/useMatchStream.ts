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
  /** Whether the SSE connection is active */
  isConnected: boolean;
  /** Error message if connection failed */
  error: string | null;
}

/**
 * Custom hook that connects to the match SSE stream and provides
 * real-time game state updates.
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
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!matchId) return;

    // Clean up previous connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const url = `${API_BASE_URL}/matches/${matchId}/stream`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setGameState(data.game_state ?? null);
        setMatchStatus(data.status ?? null);
        setGameType(data.game_type ?? null);
        setAgentIds(data.agent_ids ?? []);
        setResult(data.result ?? null);

        // If match is in a terminal state, close the connection
        const terminalStatuses = ['completed', 'failed', 'client_error'];
        if (data.status && terminalStatuses.includes(data.status)) {
          eventSource.close();
          setIsConnected(false);
        }
      } catch {
        // Ignore parse errors (e.g. keepalive comments)
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      eventSource.close();

      // Don't reconnect if we already have a terminal status
      const terminalStatuses = ['completed', 'failed', 'client_error'];
      setMatchStatus((prev) => {
        if (prev && terminalStatuses.includes(prev)) {
          return prev; // Don't reconnect
        }
        // Schedule reconnect
        setError('Connection lost. Reconnecting...');
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
        return prev;
      });
    };
  }, [matchId]);

  useEffect(() => {
    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
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
    isConnected,
    error,
  };
}
