import { Box, Typography } from '@mui/material';

type StatusTone = 'success' | 'info' | 'warning' | 'error' | 'muted';

interface StatusConfig {
  label: string;
  tone: StatusTone;
  pulse?: boolean;
}

interface StatusIndicatorProps {
  status?: string | null;
}

const statusConfigs: Record<string, StatusConfig> = {
  completed: { label: 'Completed', tone: 'success' },
  verified: { label: 'Verified', tone: 'success' },
  running: { label: 'Running', tone: 'info', pulse: true },
  in_progress: { label: 'In Progress', tone: 'info', pulse: true },
  queued: { label: 'Queued', tone: 'warning' },
  unverified: { label: 'Unverified', tone: 'warning' },
  failed: { label: 'Failed', tone: 'error' },
  client_error: { label: 'Client Error', tone: 'error' },
  unknown: { label: 'Unknown', tone: 'muted' },
};

const toneColor: Record<StatusTone, string> = {
  success: 'success.main',
  info: 'info.main',
  warning: 'warning.main',
  error: 'error.main',
  muted: 'text.disabled',
};

const formatFallbackLabel = (status?: string | null) => {
  if (!status) return 'Unknown';

  return status
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase());
};

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const normalizedStatus = status?.toLowerCase() ?? 'unknown';
  const config = statusConfigs[normalizedStatus] ?? {
    label: formatFallbackLabel(status),
    tone: 'muted' as const,
  };
  const color = toneColor[config.tone];

  return (
    <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
      <Box
        aria-hidden
        sx={{
          width: 7,
          height: 7,
          borderRadius: '50%',
          flexShrink: 0,
          backgroundColor: color,
          boxShadow: config.pulse ? `0 0 0 4px currentColor` : 'none',
          color,
          opacity: config.pulse ? 0.9 : 1,
          animation: config.pulse ? 'status-indicator-pulse 1.8s ease-in-out infinite' : 'none',
          '@keyframes status-indicator-pulse': {
            '0%, 100%': { boxShadow: '0 0 0 0 currentColor', opacity: 1 },
            '50%': { boxShadow: '0 0 0 4px transparent', opacity: 0.7 },
          },
        }}
      />
      <Typography
        component="span"
        variant="body2"
        sx={{
          color: config.tone === 'muted' ? 'text.secondary' : 'text.primary',
          fontWeight: 500,
          whiteSpace: 'nowrap',
        }}
      >
        {config.label}
      </Typography>
    </Box>
  );
}