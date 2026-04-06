import React from 'react';
import { TicTacToeRenderer } from './TicTacToeRenderer';
import { FallbackRenderer } from './FallbackRenderer';

/**
 * Props passed to every game renderer component.
 */
export interface GameRendererProps {
  /** The raw game state dict from the backend */
  gameState: any;
  /** The game type identifier (e.g. "tictactoe") */
  gameType: string;
  /** Ordered list of agent UUIDs participating in the match */
  agentIds: string[];
}

/**
 * Registry mapping game_type strings to their renderer components.
 *
 * To add a new game renderer:
 * 1. Create a new component that accepts GameRendererProps
 * 2. Add an entry to this map
 */
const GAME_RENDERERS: Record<string, React.ComponentType<GameRendererProps>> = {
  tictactoe: TicTacToeRenderer,
  // chess: ChessRenderer,
  // connect_four: ConnectFourRenderer,
};

/**
 * Get the appropriate renderer component for a game type.
 * Returns the FallbackRenderer if no specific renderer exists.
 */
export function getGameRenderer(gameType: string): React.ComponentType<GameRendererProps> {
  return GAME_RENDERERS[gameType] ?? FallbackRenderer;
}

export { TicTacToeRenderer, FallbackRenderer };
