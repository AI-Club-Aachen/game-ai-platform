import type { ReactNode } from 'react';
import { Box, Chip, Typography } from '@mui/material';
import type { ChipProps } from '@mui/material';

interface PrimarySecondaryCellProps {
  primary: ReactNode;
  secondary?: ReactNode;
  badge?: ReactNode;
  title?: string;
}

export function PrimarySecondaryCell({ primary, secondary, badge, title }: PrimarySecondaryCellProps) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
        <Typography variant="body2" fontWeight={600} noWrap title={title}>
          {primary}
        </Typography>
        {badge}
      </Box>
      {secondary && (
        <Typography
          component="div"
          variant="caption"
          color="text.secondary"
          sx={{ fontFamily: 'monospace', mt: 0.25 }}
        >
          {secondary}
        </Typography>
      )}
    </Box>
  );
}

export function ActiveBadge() {
  return (
    <SmallBadge label="Active" color="primary" />
  );
}

interface SmallBadgeProps {
  label: string;
  color?: ChipProps['color'];
}

export function SmallBadge({ label, color = 'default' }: SmallBadgeProps) {
  return (
    <Chip
      label={label}
      size="small"
      variant="outlined"
      color={color}
      sx={{ height: 20, fontSize: '0.7rem', fontWeight: 600 }}
    />
  );
}
