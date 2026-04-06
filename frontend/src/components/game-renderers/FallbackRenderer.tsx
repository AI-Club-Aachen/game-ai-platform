import { Box, Typography } from '@mui/material';
import type { GameRendererProps } from './index';

/**
 * Fallback renderer for game types that don't have a dedicated visual component.
 * Displays the raw game state as formatted JSON.
 */
export function FallbackRenderer({ gameState, gameType }: GameRendererProps) {
  if (!gameState) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography color="text.secondary">Waiting for game state...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ py: 2 }}>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, textAlign: 'center' }}>
        No dedicated renderer for <strong>{gameType}</strong> — showing raw game state
      </Typography>
      <Box
        component="pre"
        sx={{
          backgroundColor: 'action.hover',
          borderRadius: 2,
          p: 2,
          overflow: 'auto',
          maxHeight: 400,
          fontSize: '0.85rem',
          fontFamily: '"JetBrains Mono", "Fira Code", monospace',
          lineHeight: 1.6,
          border: '1px solid',
          borderColor: 'divider',
        }}
      >
        {JSON.stringify(gameState, null, 2)}
      </Box>
    </Box>
  );
}
