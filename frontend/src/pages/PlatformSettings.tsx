import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControlLabel,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { Refresh as RefreshIcon, RestartAlt as ResetIcon } from '@mui/icons-material';
import { useLocation } from 'react-router-dom';
import { platformApi, PlatformSetting, SettingSource } from '../services/api/platform';

const SOURCE_CHIP: Record<SettingSource, { label: string; color: 'primary' | 'default' | 'info' }> = {
  override: { label: 'Set here', color: 'primary' },
  environment: { label: 'Environment', color: 'info' },
  default: { label: 'Default', color: 'default' },
};

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'not set';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return String(value);
}

/** Like formatValue, but shows choice values by their display name. */
function formatSettingValue(setting: PlatformSetting, value: unknown): string {
  const label = setting.option_labels?.[String(value)];
  return label ?? formatValue(value);
}

/** Section anchor, e.g. "Match scheduler" -> "match-scheduler" (linked from Match Management). */
function groupId(group: string): string {
  return group.toLowerCase().replace(/[^a-z0-9]+/g, '-');
}

function formatBytes(value: unknown): string | null {
  if (typeof value !== 'number' || value <= 0) return null;
  const units = ['B', 'KiB', 'MiB', 'GiB'];
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${Number.isInteger(size) ? size : size.toFixed(1)} ${units[unit]}`;
}

function rangeHint(setting: PlatformSetting): string | undefined {
  const { minimum, maximum } = setting;
  if (minimum !== null && maximum !== null) return `Allowed: ${minimum} to ${maximum}`;
  if (minimum !== null) return `Minimum: ${minimum}`;
  if (maximum !== null) return `Maximum: ${maximum}`;
  return undefined;
}

/** Input value (string while typing) -> value sent to the API. */
function parseDraft(setting: PlatformSetting, raw: unknown): unknown {
  if (setting.type === 'int' || setting.type === 'float') {
    const text = String(raw).trim();
    if (text === '') return raw;
    const num = Number(text);
    return Number.isNaN(num) ? raw : num;
  }
  return raw;
}

function SettingInput({
  setting,
  value,
  onChange,
}: {
  setting: PlatformSetting;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  if (setting.type === 'bool') {
    return (
      <FormControlLabel
        control={<Switch checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />}
        label={value ? 'On' : 'Off'}
      />
    );
  }
  if (setting.type === 'choice') {
    return (
      <Select size="small" value={String(value)} onChange={(e) => onChange(e.target.value)} sx={{ minWidth: 200 }}>
        {(setting.options ?? []).map((option) => (
          <MenuItem key={option} value={option}>
            {setting.option_labels?.[option] ?? option}
          </MenuItem>
        ))}
      </Select>
    );
  }
  const numeric = setting.type === 'int' || setting.type === 'float';
  const bytes = setting.name.endsWith('_BYTES') ? formatBytes(value) : null;
  return (
    <TextField
      size="small"
      type={numeric ? 'number' : 'text'}
      value={value === null || value === undefined ? '' : String(value)}
      onChange={(e) => onChange(e.target.value)}
      slotProps={{
        htmlInput: {
          min: setting.minimum ?? undefined,
          max: setting.maximum ?? undefined,
          step: setting.type === 'float' ? 'any' : 1,
        },
      }}
      helperText={bytes ?? rangeHint(setting)}
      sx={{ width: numeric ? 200 : 260 }}
    />
  );
}

export function PlatformSettings() {
  const [settings, setSettings] = useState<PlatformSetting[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState<string | null>(null);
  const [filter, setFilter] = useState('');
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const { hash } = useLocation();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await platformApi.getSettings();
      setSettings(data.settings);
      setWarnings(data.warnings);
      setDrafts({});
    } catch (err: any) {
      setError(err.message || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Links like /settings-admin#match-scheduler scroll to that section and flash it.
  const hasSettings = settings.length > 0;
  useEffect(() => {
    const id = hash.slice(1);
    if (!id || !hasSettings) return;
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setHighlighted(id);
    const timer = window.setTimeout(() => setHighlighted(null), 2000);
    return () => window.clearTimeout(timer);
  }, [hash, hasSettings]);

  const groups = useMemo(() => {
    const byGroup = new Map<string, PlatformSetting[]>();
    for (const setting of settings) {
      if (!setting.editable || !setting.group) continue;
      byGroup.set(setting.group, [...(byGroup.get(setting.group) ?? []), setting]);
    }
    return [...byGroup.entries()];
  }, [settings]);

  const deployment = useMemo(() => {
    const query = filter.trim().toLowerCase();
    return settings.filter((s) => !s.editable && (!query || s.name.toLowerCase().includes(query)));
  }, [settings, filter]);

  const changed = useMemo(() => {
    const result: Record<string, unknown> = {};
    for (const setting of settings) {
      if (!(setting.name in drafts)) continue;
      const value = parseDraft(setting, drafts[setting.name]);
      if (value !== setting.value) result[setting.name] = value;
    }
    return result;
  }, [drafts, settings]);
  const changeCount = Object.keys(changed).length;

  const save = async (values: Record<string, unknown>, message: string) => {
    setSaving(true);
    setError(null);
    try {
      const data = await platformApi.updateSettings(values);
      setSettings(data.settings);
      setWarnings(data.warnings);
      // Keep unsaved edits of other settings (e.g. when resetting a single one).
      setDrafts((prev) => Object.fromEntries(Object.entries(prev).filter(([name]) => !(name in values))));
      setSnackbar(message);
    } catch (err: any) {
      setError(err.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading && settings.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ pb: changeCount ? 10 : 0 }}>
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" component="h1">
          Platform Settings
        </Typography>
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={load} disabled={loading || saving}>
          Refresh
        </Button>
      </Box>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Changes apply immediately and survive restarts. A value set here overrides the deployment
        environment; reset it to go back to the environment or default value.
      </Typography>

      {error && changeCount === 0 && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {warnings.map((warning) => (
        <Alert key={warning} severity="warning" sx={{ mb: 2 }}>
          {warning}
        </Alert>
      ))}

      {groups.map(([group, items]) => (
        <Paper
          key={group}
          id={groupId(group)}
          sx={{
            p: 3,
            mb: 3,
            scrollMarginTop: 16,
            outline: 2,
            outlineColor: highlighted === groupId(group) ? 'primary.main' : 'transparent',
            transition: 'outline-color 0.6s',
          }}
        >
          <Typography variant="h6" sx={{ mb: 1 }}>
            {group}
          </Typography>
          {items.map((setting) => {
            const value = setting.name in drafts ? drafts[setting.name] : setting.value;
            const isDirty = setting.name in changed;
            return (
              <Box
                key={setting.name}
                sx={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  gap: 2,
                  py: 1.5,
                  borderTop: 1,
                  borderColor: 'divider',
                }}
              >
                <Box sx={{ flex: '1 1 320px', minWidth: 0 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                    <Typography fontWeight={600}>{setting.label ?? setting.name}</Typography>
                    <Chip size="small" {...SOURCE_CHIP[setting.source]} />
                    {isDirty && <Chip size="small" color="warning" label="Unsaved" />}
                  </Box>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ fontFamily: 'monospace', wordBreak: 'break-all', display: 'block' }}
                  >
                    {setting.name}
                  </Typography>
                  {setting.description && (
                    <Typography variant="body2" color="text.secondary">
                      {setting.description}
                    </Typography>
                  )}
                  {setting.source === 'override' && (
                    <Typography variant="caption" color="text.secondary">
                      Without this override: {formatSettingValue(setting, setting.base_value)}
                    </Typography>
                  )}
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <SettingInput
                    setting={setting}
                    value={value}
                    onChange={(next) => setDrafts((prev) => ({ ...prev, [setting.name]: next }))}
                  />
                  {setting.source === 'override' && (
                    <Tooltip title={`Reset to ${formatSettingValue(setting, setting.base_value)}`}>
                      <span>
                        <Button
                          size="small"
                          startIcon={<ResetIcon />}
                          disabled={saving}
                          onClick={() => save({ [setting.name]: null }, `${setting.name} reset`)}
                        >
                          Reset
                        </Button>
                      </span>
                    </Tooltip>
                  )}
                </Box>
              </Box>
            );
          })}
        </Paper>
      ))}

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2, mb: 1 }}>
          <Typography variant="h6">Deployment configuration</Typography>
          <TextField size="small" placeholder="Filter by name" value={filter} onChange={(e) => setFilter(e.target.value)} />
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Read-only. These come from the environment variables in Dokploy and change with a redeploy. Secrets are hidden.
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Value</TableCell>
                <TableCell>Source</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {deployment.map((setting) => (
                <TableRow key={setting.name}>
                  <TableCell sx={{ fontFamily: 'monospace' }}>
                    <Tooltip title={setting.description ?? ''} placement="top-start">
                      <span>{setting.name}</span>
                    </Tooltip>
                  </TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
                    {formatValue(setting.value)}
                  </TableCell>
                  <TableCell>
                    <Chip size="small" {...SOURCE_CHIP[setting.source]} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {changeCount > 0 && (
        <Paper
          elevation={8}
          sx={{
            position: 'sticky',
            bottom: 16,
            p: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 2,
            flexWrap: 'wrap',
          }}
        >
          <Box sx={{ flex: '1 1 300px', minWidth: 0 }}>
            <Typography>
              {changeCount} unsaved change{changeCount === 1 ? '' : 's'}
            </Typography>
            {error && (
              <Typography variant="body2" color="error">
                {error}
              </Typography>
            )}
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button onClick={() => setDrafts({})} disabled={saving}>
              Discard
            </Button>
            <Button
              variant="contained"
              onClick={() => save(changed, 'Settings saved')}
              disabled={saving}
              startIcon={saving ? <CircularProgress size={16} /> : undefined}
            >
              Save
            </Button>
          </Box>
        </Paper>
      )}

      <Snackbar
        open={!!snackbar}
        autoHideDuration={4000}
        onClose={() => setSnackbar(null)}
        message={snackbar}
        // Stay above the save bar while it is shown.
        sx={changeCount ? { bottom: { xs: 112, sm: 112 } } : undefined}
      />
    </Box>
  );
}
