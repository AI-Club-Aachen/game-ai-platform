export interface Game {
  id: string;
  name: string;
  description: string;
  icon: string;
  maxPlayers: number;
  minPlayers: number;
  category: 'strategy' | 'puzzle' | 'card' | 'board';
  difficulty: 'easy' | 'medium' | 'hard';
  active: boolean;
}

export const GAMES: Game[] = [
  {
    id: 'chess',
    name: 'Chess',
    description: 'Classic chess game with AI agents',
    icon: '♟️',
    maxPlayers: 2,
    minPlayers: 2,
    category: 'board',
    difficulty: 'hard',
    active: true,
  },
  {
    id: 'tictactoe',
    name: 'Tic-Tac-Toe',
    description: 'Simple 3x3 grid game',
    icon: '❌',
    maxPlayers: 2,
    minPlayers: 2,
    category: 'board',
    difficulty: 'easy',
    active: true,
  },
  {
    id: 'connect4',
    name: 'Connect Four',
    description: 'Connect 4 pieces in a row to win',
    icon: '🔴',
    maxPlayers: 2,
    minPlayers: 2,
    category: 'board',
    difficulty: 'medium',
    active: true,
  },
  {
    id: 'go',
    name: 'Go',
    description: 'Ancient strategy board game',
    icon: '⚫',
    maxPlayers: 2,
    minPlayers: 2,
    category: 'board',
    difficulty: 'hard',
    active: false,
  },
  {
    id: 'poker',
    name: 'Poker',
    description: 'Texas Hold\'em poker',
    icon: '🃏',
    maxPlayers: 6,
    minPlayers: 2,
    category: 'card',
    difficulty: 'medium',
    active: false,
  },
];

export function getGameById(id: string): Game | undefined {
  return GAMES.find(game => game.id === id);
}

export function getActiveGames(): Game[] {
  return GAMES.filter(game => game.active);
}

export function getGamesByCategory(category: Game['category']): Game[] {
  return GAMES.filter(game => game.category === category);
}
