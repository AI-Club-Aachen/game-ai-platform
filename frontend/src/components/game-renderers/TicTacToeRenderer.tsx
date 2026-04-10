import { Box, Typography, Chip } from '@mui/material';
import type { GameRendererProps } from './index';

/**
 * Maps cell values to display content.
 * -1 = empty, 0 = Player 0 (X), 1 = Player 1 (O)
 */
function CellContent({ value }: { value: number }) {
  const baseStyle = {
    position: 'absolute' as const,
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    animation: 'cellPop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
    '@keyframes cellPop': {
      '0%': { transform: 'scale(0)', opacity: 0 },
      '100%': { transform: 'scale(1)', opacity: 1 },
    },
  };

  if (value === 0) {
    return (
      <Box sx={baseStyle}>
        <Typography
          sx={{
            fontSize: '2.5rem',
            fontWeight: 800,
            lineHeight: 1,
            color: '#6366f1',
            textShadow: '0 0 20px rgba(99, 102, 241, 0.4)',
            userSelect: 'none',
          }}
        >
          ✕
        </Typography>
      </Box>
    );
  }
  if (value === 1) {
    return (
      <Box sx={baseStyle}>
        <Typography
          sx={{
            fontSize: '2.5rem',
            fontWeight: 800,
            lineHeight: 1,
            color: '#f43f5e',
            textShadow: '0 0 20px rgba(244, 63, 94, 0.4)',
            userSelect: 'none',
          }}
        >
          ○
        </Typography>
      </Box>
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
function getStatusText(status: number, name0: string, name1: string): { text: string; color: string } {
  switch (status) {
    case -2:
      return { text: 'Draw!', color: 'warning.main' };
    case -1:
      return { text: 'In Progress', color: 'info.main' };
    case 0:
      return { text: `${name0} wins!`, color: '#6366f1' };
    case 1:
      return { text: `${name1} wins!`, color: '#f43f5e' };
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
export function TicTacToeRenderer({ gameState, agentIds, agentMap, matchStatus, result }: GameRendererProps) {
  // Resolve a display name for a player index (0 or 1)
  const agentName = (index: number): string => {
    const id = agentIds[index];
    if (!id) return `Player ${index + 1}`;
    return agentMap?.[id] ?? id.slice(0, 8) + '…';
  };

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

  const name0 = agentName(0);
  const name1 = agentName(1);
  let statusInfo = getStatusText(gameStatus, name0, name1);
  let isGameOver = gameStatus !== -1;

  // Override status if match ended externally (time limit, crash, etc)
  const isTerminal = matchStatus === 'completed' || matchStatus === 'failed' || matchStatus === 'client_error';
  if (isTerminal && gameStatus === -1) {
    isGameOver = true;
    if (matchStatus === 'failed' || matchStatus === 'client_error') {
      statusInfo = { text: 'Match Error', color: '#f43f5e' };
    } else if (result?.winner) {
      if (result.winner === 'draw') {
        statusInfo = { text: 'Draw (Match over)', color: 'warning.main' };
      } else {
        const wIndex = agentIds.indexOf(result.winner);
        statusInfo = wIndex === 0 
          ? { text: `${name0} wins!`, color: '#6366f1' }
          : wIndex === 1
            ? { text: `${name1} wins!`, color: '#f43f5e' }
            : { text: 'Match Complete', color: 'success.main' };
      }
    } else {
      statusInfo = { text: 'Terminated', color: 'text.secondary' };
    }
  }

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
      {/* Turn / Status indicator — always rendered to prevent layout shift */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, minHeight: 32 }}>
        {/* Turn label: always occupies space, hidden when game is over */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            visibility: isGameOver ? 'hidden' : 'visible',
          }}
        >
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
            {turn === 0 ? name0 : name1}'s turn
          </Typography>
        </Box>
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
          <Typography variant="body2" fontWeight={600} sx={{ color: '#6366f1' }}>
            {name0}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography sx={{ color: '#f43f5e', fontWeight: 800, fontSize: '1.2rem' }}>○</Typography>
          <Typography variant="body2" fontWeight={600} sx={{ color: '#f43f5e' }}>
            {name1}
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
              position: 'relative',
              overflow: 'hidden',
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
