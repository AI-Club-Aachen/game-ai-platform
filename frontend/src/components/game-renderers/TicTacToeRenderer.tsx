import { Box, Typography, Chip } from '@mui/material';
import type { GameRendererProps } from './index';

/**
 * Maps cell values to display content.
 * -1 = empty, 0 = Player 0 (X), 1 = Player 1 (O)
 */
function CellContent({ value }: { value: number }) {
  if (value === 0) {
    return (
      <Typography
        sx={{
          fontSize: '2.5rem',
          fontWeight: 800,
          lineHeight: 1,
          color: '#6366f1',
          textShadow: '0 0 20px rgba(99, 102, 241, 0.4)',
          animation: 'cellPop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
          '@keyframes cellPop': {
            '0%': { transform: 'scale(0)', opacity: 0 },
            '100%': { transform: 'scale(1)', opacity: 1 },
          },
        }}
      >
        ✕
      </Typography>
    );
  }
  if (value === 1) {
    return (
      <Typography
        sx={{
          fontSize: '2.5rem',
          fontWeight: 800,
          lineHeight: 1,
          color: '#f43f5e',
          textShadow: '0 0 20px rgba(244, 63, 94, 0.4)',
          animation: 'cellPop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
          '@keyframes cellPop': {
            '0%': { transform: 'scale(0)', opacity: 0 },
            '100%': { transform: 'scale(1)', opacity: 1 },
          },
        }}
      >
        ○
      </Typography>
    );
  }
  return null;
}

/**
 * Interpret the game status value:
 *  -2 = draw
 *  -1 = ongoing
 *   0 = player 0 wins
 *   1 = player 1 wins
 */
function getStatusText(status: number): { text: string; color: string } {
  switch (status) {
    case -2:
      return { text: 'Draw!', color: 'warning.main' };
    case -1:
      return { text: 'In Progress', color: 'info.main' };
    case 0:
      return { text: `Player 1 wins!`, color: '#6366f1' };
    case 1:
      return { text: `Player 2 wins!`, color: '#f43f5e' };
    default:
      return { text: 'Unknown', color: 'text.secondary' };
  }
}

/**
 * TicTacToe game renderer.
 *
 * Expects gameState to have the shape:
 * { board: number[], turn: number, status: number }
 */
export function TicTacToeRenderer({ gameState, agentIds }: GameRendererProps) {
  if (!gameState || !gameState.board) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography color="text.secondary">Waiting for game state...</Typography>
      </Box>
    );
  }

  const { board, turn, status: gameStatus } = gameState as {
    board: number[];
    turn: number;
    status: number;
  };

  const statusInfo = getStatusText(gameStatus);
  const isGameOver = gameStatus !== -1;

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 3,
        py: 2,
      }}
    >
      {/* Turn / Status indicator */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        {!isGameOver && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                backgroundColor: turn === 0 ? '#6366f1' : '#f43f5e',
                animation: 'pulse 1.5s ease-in-out infinite',
                '@keyframes pulse': {
                  '0%, 100%': { opacity: 1 },
                  '50%': { opacity: 0.4 },
                },
              }}
            />
            <Typography variant="body1" fontWeight={600}>
              {turn === 0 ? 'Player 1' : 'Player 2'}'s turn
            </Typography>
          </Box>
        )}
        <Chip
          label={statusInfo.text}
          size="small"
          sx={{
            backgroundColor: isGameOver ? statusInfo.color : undefined,
            color: isGameOver ? '#fff' : undefined,
            fontWeight: 600,
          }}
          color={isGameOver ? undefined : 'default'}
        />
      </Box>

      {/* Player legend */}
      <Box sx={{ display: 'flex', gap: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography sx={{ color: '#6366f1', fontWeight: 800, fontSize: '1.2rem' }}>✕</Typography>
          <Typography variant="body2" color="text.secondary">
            Player 1 {agentIds[0] ? `(${agentIds[0].slice(0, 8)}…)` : ''}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography sx={{ color: '#f43f5e', fontWeight: 800, fontSize: '1.2rem' }}>○</Typography>
          <Typography variant="body2" color="text.secondary">
            Player 2 {agentIds[1] ? `(${agentIds[1].slice(0, 8)}…)` : ''}
          </Typography>
        </Box>
      </Box>

      {/* 3x3 Grid */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '4px',
          width: 'min(100%, 320px)',
          aspectRatio: '1 / 1',
          backgroundColor: 'divider',
          borderRadius: 2,
          overflow: 'hidden',
          boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
        }}
      >
        {board.map((cell: number, index: number) => (
          <Box
            key={index}
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'background.paper',
              transition: 'background-color 0.2s ease',
              cursor: 'default',
              '&:hover': {
                backgroundColor: cell === -1 ? 'action.hover' : undefined,
              },
            }}
          >
            <CellContent value={cell} />
          </Box>
        ))}
      </Box>
    </Box>
  );
}
