import { Link } from 'react-router-dom';
import { Box, Button, Dialog, DialogActions, DialogContent, Typography } from '@mui/material';
import { alpha, Theme } from '@mui/material/styles';

export interface PodiumEntry {
  agentId: string;
  name: string;
  placement: number;
}

interface PodiumDialogProps {
  open: boolean;
  onClose: () => void;
  tournamentName: string;
  entries: PodiumEntry[]; // top placements, sorted (champion first)
}

const PODIUM_HEIGHTS: Record<number, number> = { 1: 136, 2: 96, 3: 68 };
const PODIUM_DELAYS: Record<number, string> = { 1: '0.5s', 2: '0.25s', 3: '0s' };

const barStyles = (theme: Theme): Record<number, object> => ({
  1: {
    background: `linear-gradient(180deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
    // Soft breathing glow instead of a metallic shine.
    animation:
      'podium-rise 0.6s cubic-bezier(0.22, 1, 0.36, 1) forwards, podium-glow 2.4s ease-in-out 1.2s infinite',
    '@keyframes podium-glow': {
      '0%, 100%': { boxShadow: `0 8px 24px ${alpha(theme.palette.primary.main, 0.25)}` },
      '50%': { boxShadow: `0 8px 32px ${alpha(theme.palette.primary.main, 0.5)}` },
    },
  },
  2: {
    backgroundColor: alpha(theme.palette.primary.main, 0.2),
    border: `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
    borderBottom: 'none',
  },
  3: {
    backgroundColor: alpha(theme.palette.primary.main, 0.08),
    border: `1px solid ${theme.palette.divider}`,
    borderBottom: 'none',
  },
});

function PodiumColumn({ entry }: { entry: PodiumEntry }) {
  const height = PODIUM_HEIGHTS[entry.placement] ?? 60;
  const delay = PODIUM_DELAYS[entry.placement] ?? '0s';
  const isChampion = entry.placement === 1;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 132, minWidth: 0 }}>
      <Box
        sx={{
          mb: 1.5,
          textAlign: 'center',
          opacity: 0,
          animation: 'podium-fade 0.45s ease-out forwards',
          animationDelay: `calc(${delay} + 0.4s)`,
          '@keyframes podium-fade': {
            from: { opacity: 0, transform: 'translateY(6px)' },
            to: { opacity: 1, transform: 'translateY(0)' },
          },
          maxWidth: '100%',
        }}
      >
        {isChampion && (
          <Typography
            variant="overline"
            color="primary"
            sx={{ letterSpacing: '0.15em', lineHeight: 1.4, display: 'block', fontWeight: 600 }}
          >
            Champion
          </Typography>
        )}
        <Typography
          component={Link}
          to={`/agents/${entry.agentId}`}
          variant={isChampion ? 'h6' : 'body2'}
          noWrap
          title={entry.name}
          sx={{
            display: 'block',
            color: 'text.primary',
            textDecoration: 'none',
            fontWeight: isChampion ? 700 : 500,
            '&:hover': { color: 'primary.main' },
          }}
        >
          {entry.name}
        </Typography>
      </Box>
      <Box
        sx={(theme) => ({
          width: '100%',
          height,
          borderRadius: `${theme.shape.borderRadius}px ${theme.shape.borderRadius}px 0 0`,
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'center',
          pt: 1.5,
          transformOrigin: 'bottom',
          transform: 'scaleY(0)',
          animation: 'podium-rise 0.6s cubic-bezier(0.22, 1, 0.36, 1) forwards',
          animationDelay: delay,
          '@keyframes podium-rise': {
            from: { transform: 'scaleY(0)' },
            to: { transform: 'scaleY(1)' },
          },
          ...barStyles(theme)[entry.placement],
        })}
      >
        <Typography
          sx={{
            fontWeight: 700,
            fontSize: '1.125rem',
            color: isChampion ? '#fff' : 'primary.main',
            opacity: isChampion ? 1 : 0.9,
          }}
        >
          {entry.placement}
        </Typography>
      </Box>
    </Box>
  );
}

/**
 * Shown when a tournament completes: animated podium for the top three.
 */
export function PodiumDialog({ open, onClose, tournamentName, entries }: PodiumDialogProps) {
  const byPlacement = new Map(entries.map((entry) => [entry.placement, entry]));
  // Classic podium order: runner-up, champion, third.
  const columns = [byPlacement.get(2), byPlacement.get(1), byPlacement.get(3)].filter(
    (entry): entry is PodiumEntry => entry !== undefined,
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogContent
        sx={{
          pt: 4,
          background: 'radial-gradient(ellipse at 50% 100%, var(--color-primary-glow) 0%, transparent 65%)',
        }}
      >
        <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: '0.1em' }}>
          Final standings
        </Typography>
        <Typography variant="h5" fontWeight={700} gutterBottom>
          {tournamentName}
        </Typography>
        <Box
          sx={{
            mt: 4,
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'center',
            gap: 1.5,
            borderBottom: '1px solid',
            borderColor: 'divider',
            minHeight: 216,
          }}
        >
          {columns.map((entry) => (
            <PodiumColumn key={entry.agentId} entry={entry} />
          ))}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
