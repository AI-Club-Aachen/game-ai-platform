import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TablePagination,
  Alert,
  Snackbar,
  CircularProgress,
  Autocomplete,
  Divider,
  Switch,
  FormControlLabel,
  InputAdornment,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  PlayCircleOutline as PlayIcon,
  Visibility as VisibilityIcon,
  Settings as SettingsIcon,
  InfoOutlined as InfoIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';
import { matchesApi } from '../services/api/matches';
import { agentsApi, Agent } from '../services/api/agents';
import { arenasApi, ArenaRead } from '../services/api/arenas';
import { fromApiGameType, getGameById } from '../config/games';
import { PrimarySecondaryCell } from '../components/common/TableCells';
import { StatusIndicator } from '../components/common/StatusIndicator';

// Mirrors backend MatchConfig – update here when new fields are added.
interface MatchConfig {
  turn_time_limit: number;
}

interface MatchResult {
  winner?: string;
  reason?: string;
  [key: string]: unknown;
}

interface AdminMatch {
  id: string;
  game_type: string;
  status: string;
  created_at?: string | null;
  updated_at?: string | null;
  agent_ids?: string[];
  result?: MatchResult | null;
  config?: MatchConfig | Record<string, unknown> | null;
}

const MIN_TURN_TIME_LIMIT = 0.1;
const DEFAULT_TURN_TIME_LIMIT = 10;
const FALLBACK_MAX_TURN_TIME_LIMIT = 120;
const rawMaxTurnTimeLimit = Number(import.meta.env.MAX_TURN_TIME_LIMIT_SECONDS);
const MAX_TURN_TIME_LIMIT = Number.isFinite(rawMaxTurnTimeLimit) && rawMaxTurnTimeLimit >= MIN_TURN_TIME_LIMIT
  ? rawMaxTurnTimeLimit
  : FALLBACK_MAX_TURN_TIME_LIMIT;

const DEFAULT_CONFIG: MatchConfig = {
  turn_time_limit: Math.min(DEFAULT_TURN_TIME_LIMIT, MAX_TURN_TIME_LIMIT),
};

const shortId = (id?: string | null, length = 8) => {
  if (!id) return '—';
  return id.length > length ? `${id.slice(0, length)}…` : id;
};

const formatShortDateTime = (isoDate?: string | null): string => {
  if (!isoDate) return '—';

  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatFullDateTime = (isoDate?: string | null): string => {
  if (!isoDate) return '—';

  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }

  return date.toLocaleString();
};

const isFailureStatus = (status?: string | null) => {
  const normalized = status?.toLowerCase();
  return normalized === 'failed' || normalized === 'client_error';
};

export function MatchManagement() {
  const navigate = useNavigate();
  const [matches, setMatches] = useState<AdminMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const [filterGameType, setFilterGameType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const [createDialogOpen, setDialogOpen] = useState(false);
  const [arenas, setArenas] = useState<ArenaRead[]>([]);
  const [newMatchArenaId, setNewMatchArenaId] = useState('');
  const [matchConfig, setMatchConfig] = useState<MatchConfig>(DEFAULT_CONFIG);
  const [selectedAgents, setSelectedAgents] = useState<Agent[]>([]);

  const [agents, setAgents] = useState<Agent[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);

  const [isCreating, setIsCreating] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState<string | null>(null);

  const [schedulerDialogOpen, setSchedulerDialogOpen] = useState(false);
  const [schedulerConfig, setSchedulerConfig] = useState({ enabled: false, interval_seconds: 10, strategy: 'least_played', scheduling_strategy: 'serial' });
  const [isSavingScheduler, setIsSavingScheduler] = useState(false);

  const selectedArena = arenas.find(a => a.id === newMatchArenaId);
  const selectedGameConfig = selectedArena ? getGameById(fromApiGameType(selectedArena.game_type)) : null;
  const minRequiredAgents = selectedGameConfig?.minPlayers ?? 2;
  const maxAllowedAgents = selectedGameConfig?.maxPlayers ?? minRequiredAgents;
  const hasValidAgentCount = selectedAgents.length >= minRequiredAgents && selectedAgents.length <= maxAllowedAgents;

  const fetchMatches = useCallback(async () => {
    setLoading(true);
    try {
      const response = await matchesApi.getMatches({
        skip: page * rowsPerPage,
        limit: rowsPerPage,
        game_type: filterGameType !== 'all' ? filterGameType : undefined,
        status: filterStatus !== 'all' ? filterStatus : undefined,
      });
      setMatches(Array.isArray(response) ? response : (response as any).data || []);
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch matches:', err);
      setError('Failed to load matches.');
    } finally {
      setLoading(false);
    }
  }, [page, rowsPerPage, filterGameType, filterStatus]);

  useEffect(() => {
    fetchMatches();
  }, [fetchMatches]);

  useEffect(() => {
    setLoadingAgents(true);
    agentsApi.getAllAgents(true)
      .then(agentsData => {
        setAgents(agentsData);
      })
      .catch(err => console.error("Failed to fetch agents", err))
      .finally(() => setLoadingAgents(false));

    arenasApi.getArenas()
      .then(data => {
        const activeArenas = data.filter(a => a.is_active);
        setArenas(activeArenas);
        if (activeArenas.length > 0) {
          setNewMatchArenaId(activeArenas[0].id);
        }
      })
      .catch(err => console.error("Failed to load arenas", err));
  }, []);

  const handleChangePage = (_event: unknown, newPage: number) => setPage(newPage);

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleOpenDialog = () => {
    setMatchConfig(DEFAULT_CONFIG);
    setSelectedAgents([]);
    if (arenas.length > 0) {
      setNewMatchArenaId(arenas[0].id);
    }
    setDialogOpen(true);
  };

  const buildConfig = (): MatchConfig => ({
    turn_time_limit: matchConfig.turn_time_limit ?? 10,
  });

  const handleCreateMatch = async () => {
    const agentIdsArray = selectedAgents.map(a => a.id);
    const config = buildConfig();

    setIsCreating(true);
    try {
      await matchesApi.createMatch({
        arena_id: newMatchArenaId,
        config,
        agent_ids: agentIdsArray,
      });

      setSnackbarMessage('Match created successfully');
      setDialogOpen(false);
      fetchMatches();
    } catch (err: any) {
      console.error('Error creating match', err);
      setSnackbarMessage('Failed to create match. ' + (err.message || ''));
    } finally {
      setIsCreating(false);
    }
  };

  const handleOpenSchedulerDialog = async () => {
    try {
      const config = await matchesApi.getSchedulerConfig();
      setSchedulerConfig(config);
      setSchedulerDialogOpen(true);
    } catch (err: any) {
      console.error('Failed to get scheduler config:', err);
      setSnackbarMessage('Failed to get scheduler configuration');
    }
  };

  const handleSaveSchedulerConfig = async () => {
    setIsSavingScheduler(true);
    try {
      await matchesApi.updateSchedulerConfig(schedulerConfig);
      setSnackbarMessage('Scheduler configuration saved successfully');
      setSchedulerDialogOpen(false);
    } catch (err: any) {
      console.error('Failed to update scheduler config:', err);
      setSnackbarMessage('Failed to update scheduler configuration. ' + (err.message || ''));
    } finally {
      setIsSavingScheduler(false);
    }
  };

  const findAgent = (agentId: string) => agents.find(agent => agent.id === agentId);

  const getAgentLabel = (agentId: string) => findAgent(agentId)?.name || shortId(agentId);

  const formatAgentNames = (agentIds?: string[]) => {
    if (!agentIds?.length) return 'No agents';
    return agentIds.map(getAgentLabel).join(' vs ');
  };

  const formatAgentIds = (agentIds?: string[]) => {
    if (!agentIds?.length) return undefined;
    return agentIds.map(id => shortId(id)).join(' · ');
  };

  const formatWinner = (match: AdminMatch) => {
    const status = match.status?.toLowerCase();
    const winner = match.result?.winner;

    if (status === 'completed') {
      if (winner === 'draw') return 'Draw';
      if (winner) return getAgentLabel(winner);
      return '—';
    }

    if (isFailureStatus(status)) {
      return '—';
    }

    return '—';
  };

  return (
    <Box>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          Match Management
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchMatches}
            sx={{ mr: 2 }}
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            startIcon={<ScheduleIcon />}
            onClick={handleOpenSchedulerDialog}
            sx={{ mr: 2 }}
          >
            Scheduler Settings
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleOpenDialog}
          >
            New Match
          </Button>
        </Box>
      </Box>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Game Type</InputLabel>
            <Select
              value={filterGameType}
              label="Game Type"
              onChange={(e) => {
                setFilterGameType(e.target.value);
                setPage(0);
              }}
            >
              <MenuItem value="all">All Games</MenuItem>
              <MenuItem value="tictactoe">Tic-Tac-Toe</MenuItem>
              <MenuItem value="hex">Hex</MenuItem>
              <MenuItem value="connect_four">Connect Four</MenuItem>
              <MenuItem value="chess">Chess</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={filterStatus}
              label="Status"
              onChange={(e) => {
                setFilterStatus(e.target.value);
                setPage(0);
              }}
            >
              <MenuItem value="all">All Statuses</MenuItem>
              <MenuItem value="queued">Queued</MenuItem>
              <MenuItem value="running">Running</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
              <MenuItem value="failed">Failed</MenuItem>
              <MenuItem value="client_error">Client Error</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
        )}

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Match</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Winner</TableCell>
                <TableCell>Agents</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : matches.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">No matches found</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                matches.map((match) => {
                  const createdAt = formatFullDateTime(match.created_at);
                  const updatedAt = formatFullDateTime(match.updated_at);

                  return (
                    <TableRow key={match.id}>
                      <TableCell>
                        <PrimarySecondaryCell
                          primary={shortId(match.id)}
                          secondary={fromApiGameType(match.game_type)}
                          title={match.id}
                        />
                      </TableCell>
                      <TableCell>
                        <StatusIndicator status={match.status} />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {formatWinner(match)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <PrimarySecondaryCell
                          primary={formatAgentNames(match.agent_ids)}
                          secondary={formatAgentIds(match.agent_ids)}
                          title={match.agent_ids?.join('\n')}
                        />
                      </TableCell>
                      <TableCell>
                        <PrimarySecondaryCell
                          primary={formatShortDateTime(match.created_at)}
                          secondary={`Updated ${formatShortDateTime(match.updated_at)}`}
                          title={`Created: ${createdAt}\nUpdated: ${updatedAt}`}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<VisibilityIcon />}
                          onClick={() => navigate(`/games/live/${match.id}`)}
                        >
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          component="div"
          count={-1}
          page={page}
          onPageChange={handleChangePage}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          rowsPerPageOptions={[5, 10, 25, 50]}
          labelDisplayedRows={({ from, to }: { from: number; to: number }) => `${from}-${to}`}
        />
      </Paper>

      {/* Create Match Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Start New Match</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>

            {/* Arena */}
            <FormControl fullWidth>
              <InputLabel>Arena</InputLabel>
              <Select
                value={newMatchArenaId}
                onChange={(e) => {
                  setNewMatchArenaId(e.target.value);
                  setSelectedAgents([]);
                }}
                label="Arena"
              >
                {arenas.map((arena) => (
                  <MenuItem key={arena.id} value={arena.id}>
                    {arena.name} ({getGameById(fromApiGameType(arena.game_type))?.name || arena.game_type})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Agent picker */}
            <Autocomplete
              multiple
              options={agents.filter(a => a.arena_id === newMatchArenaId)}
              getOptionLabel={(option) => `${option.name} (${option.id.substring(0, 8)}...)`}
              value={selectedAgents}
              onChange={(_, newValue) => setSelectedAgents(newValue)}
              filterSelectedOptions
              disableCloseOnSelect
              limitTags={2}
              loading={loadingAgents}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Select Agents"
                  placeholder="Select participating agents"
                  helperText={`Select ${minRequiredAgents}-${maxAllowedAgents} agents. List filtered by selected arena.`}
                  error={!hasValidAgentCount && selectedAgents.length > 0}
                  InputProps={{
                    ...params.InputProps,
                    endAdornment: (
                      <>
                        {loadingAgents ? <CircularProgress color="inherit" size={20} /> : null}
                        {params.InputProps.endAdornment}
                      </>
                    ),
                  }}
                />
              )}
            />

            {/* ---- Match Configuration section ---- */}
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                <SettingsIcon fontSize="small" color="action" />
                <Typography variant="subtitle2" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Match Configuration
                </Typography>
              </Box>
              <Divider sx={{ mb: 2 }} />

              {/* Turn time limit */}
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                <Box sx={{ flex: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                    <Typography variant="body2" fontWeight={500}>
                      Turn Time Limit
                    </Typography>
                    <Tooltip title="Maximum seconds an agent may take per turn. Exceeding this forfeits the game. Agents are paused while it is not their turn.">
                      <InfoIcon fontSize="inherit" color="action" sx={{ cursor: 'help', fontSize: '1rem' }} />
                    </Tooltip>
                  </Box>
                  <TextField
                    id="turn-time-limit-input"
                    type="number"
                    size="small"
                    value={matchConfig.turn_time_limit ?? 10}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      setMatchConfig(prev => ({
                        ...prev,
                        turn_time_limit: isNaN(val) ? DEFAULT_TURN_TIME_LIMIT : Math.max(0.1, val),
                      }));
                    }}
                    inputProps={{ min: 0.1, step: 0.5 }}
                    InputProps={{
                      endAdornment: <InputAdornment position="end">s</InputAdornment>,
                    }}
                    sx={{ width: 140 }}
                  />
                </Box>
              </Box>
            </Box>

          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} variant="outlined" disabled={isCreating}>
            Cancel
          </Button>
          <Button
            onClick={handleCreateMatch}
            variant="contained"
            disabled={isCreating || !hasValidAgentCount}
            startIcon={isCreating ? <CircularProgress size={20} /> : <PlayIcon />}
          >
            Start Match
          </Button>
        </DialogActions>
      </Dialog>

      {/* Scheduler Settings Dialog */}
      <Dialog open={schedulerDialogOpen} onClose={() => setSchedulerDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Scheduler Settings</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={schedulerConfig.enabled}
                  onChange={(e) => setSchedulerConfig({ ...schedulerConfig, enabled: e.target.checked })}
                  color="primary"
                />
              }
              label="Enable Match Scheduler"
            />

            <TextField
              label="Interval (Seconds)"
              type="number"
              fullWidth
              value={schedulerConfig.interval_seconds}
              onChange={(e) => setSchedulerConfig({ ...schedulerConfig, interval_seconds: parseFloat(e.target.value) || 10 })}
              disabled={!schedulerConfig.enabled}
              inputProps={{ min: 1, step: 1 }}
              helperText="How often the scheduler checks for queued matches."
            />

            <FormControl fullWidth disabled={!schedulerConfig.enabled}>
              <InputLabel>Agent Selection</InputLabel>
              <Select
                value={schedulerConfig.strategy}
                label="Agent Selection"
                onChange={(e) => setSchedulerConfig({ ...schedulerConfig, strategy: e.target.value })}
              >
                <MenuItem value="random">Random</MenuItem>
                <MenuItem value="least_played">Least Played (prioritize agents with fewer games)</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth disabled={!schedulerConfig.enabled}>
              <InputLabel>Scheduling Mode</InputLabel>
              <Select
                value={schedulerConfig.scheduling_strategy}
                label="Scheduling Mode"
                onChange={(e) => setSchedulerConfig({ ...schedulerConfig, scheduling_strategy: e.target.value })}
              >
                <MenuItem value="serial">Serial (one match at a time)</MenuItem>
                <MenuItem value="concurrent">Concurrent (keep all workers busy)</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSchedulerDialogOpen(false)} variant="outlined" disabled={isSavingScheduler}>
            Cancel
          </Button>
          <Button
            onClick={handleSaveSchedulerConfig}
            variant="contained"
            disabled={isSavingScheduler}
            startIcon={isSavingScheduler ? <CircularProgress size={20} /> : <SettingsIcon />}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!snackbarMessage}
        autoHideDuration={6000}
        onClose={() => setSnackbarMessage(null)}
        message={snackbarMessage}
      />
    </Box>
  );
}
