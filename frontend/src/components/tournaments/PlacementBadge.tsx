import { Box, Typography } from '@mui/material';
import { alpha, Theme } from '@mui/material/styles';

/**
 * Flat, theme-tinted placement markers for tournament standings — the same
 * primary-alpha language the rest of the UI uses (no trophies, no gold).
 */
export const placementStyles = (theme: Theme): Record<number, object> => ({
  1: {
    backgroundColor: theme.palette.primary.main,
    color: '#fff',
  },
  2: {
    backgroundColor: alpha(theme.palette.primary.main, 0.18),
    color: theme.palette.primary.main,
  },
  3: {
    backgroundColor: alpha(theme.palette.primary.main, 0.08),
    border: `1px solid ${alpha(theme.palette.primary.main, 0.25)}`,
    color: theme.palette.primary.main,
  },
});

interface PlacementBadgeProps {
  placement: number | null;
  size?: number;
}

/**
 * Rounded-square badge for the top three placements; plain number otherwise.
 */
export function PlacementBadge({ placement, size = 24 }: PlacementBadgeProps) {
  if (placement === null) {
    return (
      <Typography component="span" variant="body2" color="text.disabled">
        —
      </Typography>
    );
  }

  if (placement > 3) {
    return (
      <Typography component="span" variant="body2" color="text.secondary">
        {placement}
      </Typography>
    );
  }

  return (
    <Box
      component="span"
      sx={(theme) => ({
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: size,
        height: size,
        borderRadius: `${theme.shape.borderRadius}px`,
        fontSize: size * 0.5,
        fontWeight: 700,
        lineHeight: 1,
        ...placementStyles(theme)[placement],
      })}
    >
      {placement}
    </Box>
  );
}
