import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Box, Button, CircularProgress, Divider, Paper, Switch, Tooltip, Typography } from '@mui/material';
import { Tune as TuneIcon } from '@mui/icons-material';
import { platformApi, PlatformSetting } from '../../services/api/platform';

const NAMES = [
  'MATCH_SCHEDULER_ENABLED',
  'MATCH_SCHEDULER_INTERVAL_SECONDS',
  'MATCH_SCHEDULER_SELECTION',
  'MATCH_SCHEDULING_STRATEGY',
  'MATCH_MAX_CONCURRENT_MATCHES',
] as const;

type SchedulerSettings = Partial<Record<(typeof NAMES)[number], PlatformSetting>>;

function pick(settings: PlatformSetting[]): SchedulerSettings {
  return Object.fromEntries(settings.filter((s) => (NAMES as readonly string[]).includes(s.name)).map((s) => [s.name, s]));
}

/** "Least played (agents with fewer games first)" -> "Least played" */
function optionLabel(setting: PlatformSetting | undefined): string {
  const value = String(setting?.value ?? '');
  return (setting?.option_labels?.[value] ?? value).split(' (')[0];
}

/**
 * Current state of the automatic match scheduler, with an on/off switch.
 * Everything else about it is configured on the Platform Settings page.
 */
export function SchedulerStatus({ onError }: { onError: (message: string) => void }) {
  const [scheduler, setScheduler] = useState<SchedulerSettings | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    platformApi
      .getSettings()
      .then((data) => setScheduler(pick(data.settings)))
      .catch((err) => onError('Failed to load scheduler status. ' + (err.message || '')));
  }, [onError]);

  const toggle = async (enabled: boolean) => {
    setSaving(true);
    try {
      const data = await platformApi.updateSettings({ MATCH_SCHEDULER_ENABLED: enabled });
      setScheduler(pick(data.settings));
    } catch (err: any) {
      onError('Failed to change the scheduler. ' + (err.message || ''));
    } finally {
      setSaving(false);
    }
  };

  if (!scheduler) return null;

  const enabled = Boolean(scheduler.MATCH_SCHEDULER_ENABLED?.value);
  const concurrent = scheduler.MATCH_SCHEDULING_STRATEGY?.value === 'concurrent';
  const details = [
    `Every ${scheduler.MATCH_SCHEDULER_INTERVAL_SECONDS?.value} s`,
    optionLabel(scheduler.MATCH_SCHEDULER_SELECTION),
    concurrent
      ? `Concurrent, up to ${scheduler.MATCH_MAX_CONCURRENT_MATCHES?.value} matches`
      : optionLabel(scheduler.MATCH_SCHEDULING_STRATEGY),
  ];

  return (
    <Paper variant="outlined" sx={{ px: 2, py: 1, mb: 3, display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
      <Typography fontWeight={600}>Auto-scheduler</Typography>
      <Tooltip title={enabled ? 'Stop queueing arena matches automatically' : 'Queue arena matches automatically'}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Switch
            checked={enabled}
            disabled={saving}
            onChange={(e) => toggle(e.target.checked)}
            slotProps={{ input: { role: 'switch', 'aria-label': 'Auto-scheduler enabled' } }}
          />
          <Typography sx={{ minWidth: 28 }} color={enabled ? 'success.main' : 'text.secondary'}>
            {enabled ? 'On' : 'Off'}
          </Typography>
          {saving && <CircularProgress size={16} sx={{ ml: 1 }} />}
        </Box>
      </Tooltip>
      <Box
        sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap', flex: '1 1 auto', color: enabled ? 'text.primary' : 'text.disabled' }}
      >
        {details.map((detail, i) => (
          <Box key={detail} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            {i > 0 && <Divider orientation="vertical" flexItem />}
            <Typography variant="body2">{detail}</Typography>
          </Box>
        ))}
      </Box>
      <Button component={Link} to="/settings-admin#match-scheduler" size="small" startIcon={<TuneIcon />}>
        Configure
      </Button>
    </Paper>
  );
}
