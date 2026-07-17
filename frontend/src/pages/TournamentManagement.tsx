import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputAdornment,
  InputLabel,
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
  TablePagination,
  TextField,
  Typography,
} from '@mui/material';
import {
  Add as AddIcon,
  Cancel as CancelIcon,
  EmojiEvents as TrophyIcon,
  PlayArrow as StartIcon,
  Refresh as RefreshIcon,
  ReportProblemOutlined as AttentionIcon,
  Visibility as VisibilityIcon,
} from '@mui/icons-material';
import {
  tournamentsApi,
  Tournament,
  TournamentMatchup,
  TournamentBracket,
} from '../services/api/tournaments';
import { agentsApi, Agent } from '../services/api/agents';
import { arenasApi, ArenaRead } from '../services/api/arenas';
import { platformApi } from '../services/api/platform';
import { StatusIndicator } from '../components/common/StatusIndicator';
import { PrimarySecondaryCell } from '../components/common/TableCells';
import { fromApiGameType, getGameById } from '../config/games';

const DEFAULT_TURN_TIME_LIMIT = 10;
const DEFAULT_MAX_CONCURRENT = 4;

const shortId = (id?: string | null, length = 8) => {
  if (!id) return '—';
  return id.length > length ? `${id.slice(0, length)}…` : id;
};

const formatShortDateTime = (isoDate?: string | null): string => {
  if (!isoDate) return '—';
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const gameName = (gameType: string) => getGameById(fromApiGameType(gameType))?.name ?? gameType;

export function TournamentManagement() {
  const navigate = useNavigate();

  const [tournaments, setTournaments] = useState<Tournament[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const [agents, setAgents] = useState<Agent[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [arenas, setArenas] = useState<ArenaRead[]>([]);
  const [newArenaId, setNewArenaId] = useState('');
  const [selectedAgents, setSelectedAgents] = useState<Agent[]>([]);
  const [turnTimeLimit, setTurnTimeLimit] = useState(DEFAULT_TURN_TIME_LIMIT);
  const [maxConcurrent, setMaxConcurrent] = useState(DEFAULT_MAX_CONCURRENT);
  const [isCreating, setIsCreating] = useState(false);

  const [resolveDialogOpen, setResolveDialogOpen] = useState(false);
  const [resolveBracket, setResolveBracket] = useState<TournamentBracket | null>(null);
  const [resolveMatchupId, setResolveMatchupId] = useState('');
  const [resolveWinnerId, setResolveWinnerId] = useState('');
  const [isResolving, setIsResolving] = useState(false);

  const [actionInFlight, setActionInFlight] = useState<string | null>(null);
  const [snackbarMessage, setSnackbarMessage] = useState<string | null>(null);

  const [submissionFreeze, setSubmissionFreeze] = useState(false);
  const [freezeSaving, setFreezeSaving] = useState(false);

  const fetchTournaments = useCallback(async () => {
    setLoading(true);
    try {
      const data = await tournamentsApi.getTournaments({
        skip: page * rowsPerPage,
        limit: rowsPerPage,
        status: filterStatus !== 'all' ? (filterStatus as Tournament['status']) : undefined,
      });
      setTournaments(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch tournaments:', err);
      setError('Failed to load tournaments.');
    } finally {
      setLoading(false);
    }
  }, [page, rowsPerPage, filterStatus]);

  useEffect(() => {
    fetchTournaments();
  }, [fetchTournaments]);

  useEffect(() => {
    setLoadingAgents(true);
    agentsApi
      .getAllAgents(true)
      .then((res) => setAgents(Array.isArray(res) ? res : []))
      .catch((err) => console.error('Failed to fetch agents', err))
      .finally(() => setLoadingAgents(false));

    arenasApi
      .getArenas()
      .then((res) => {
        const activeArenas = res.filter(a => a.is_active);
        setArenas(activeArenas);
        if (activeArenas.length > 0) {
          setNewArenaId(activeArenas[0].id);
        }
      })
      .catch((err) => console.error('Failed to fetch arenas', err));
  }, []);

  useEffect(() => {
    platformApi
      .getSubmissionFreeze()
      .then((state) => setSubmissionFreeze(state.enabled))
      .catch((err) => console.error('Failed to load submission-freeze state', err));
  }, []);

  const handleToggleFreeze = async (enabled: boolean) => {
    setFreezeSaving(true);
    try {
      const state = await platformApi.setSubmissionFreeze(enabled);
      setSubmissionFreeze(state.enabled);
      setSnackbarMessage(
        state.enabled ? 'Submissions frozen — entrants can no longer change agents.' : 'Submission freeze lifted.',
      );
    } catch (err: any) {
      console.error('Failed to update submission freeze', err);
      setSnackbarMessage('Failed to update submission freeze. ' + (err.message || ''));
    } finally {
      setFreezeSaving(false);
    }
  };

  // Entrants must have an active submission; the backend additionally checks
  // for a successful build on creation.
  const eligibleAgents = useMemo(
    () => agents.filter((agent) => agent.arena_id === newArenaId && agent.active_submission_id !== null),
    [agents, newArenaId],
  );

  const agentNameById = useMemo(() => {
    const names: Record<string, string> = {};
    for (const agent of agents) names[agent.id] = agent.name;
    return names;
  }, [agents]);

  const handleOpenCreateDialog = () => {
    setNewName('');
    if (arenas.length > 0) {
      setNewArenaId(arenas[0].id);
    }
    setSelectedAgents([]);
    setTurnTimeLimit(DEFAULT_TURN_TIME_LIMIT);
    setMaxConcurrent(DEFAULT_MAX_CONCURRENT);
    setCreateDialogOpen(true);
  };

  const handleCreateTournament = async () => {
    setIsCreating(true);
    try {
      await tournamentsApi.createTournament({
        name: newName.trim(),
        arena_id: newArenaId,
        agent_ids: selectedAgents.map((agent) => agent.id),
        config: {
          turn_time_limit: turnTimeLimit,
          max_concurrent_matches: maxConcurrent,
        },
      });
      setSnackbarMessage('Tournament created');
      setCreateDialogOpen(false);
      fetchTournaments();
    } catch (err: any) {
      console.error('Error creating tournament', err);
      setSnackbarMessage('Failed to create tournament. ' + (err.message || ''));
    } finally {
      setIsCreating(false);
    }
  };

  const handleStart = async (tournament: Tournament) => {
    setActionInFlight(tournament.id);
    try {
      await tournamentsApi.startTournament(tournament.id);
      setSnackbarMessage(`Tournament "${tournament.name}" started`);
      fetchTournaments();
    } catch (err: any) {
      console.error('Error starting tournament', err);
      setSnackbarMessage('Failed to start tournament. ' + (err.message || ''));
    } finally {
      setActionInFlight(null);
    }
  };

  const handleCancel = async (tournament: Tournament) => {
    if (!window.confirm(`Cancel tournament "${tournament.name}"? This cannot be undone.`)) return;
    setActionInFlight(tournament.id);
    try {
      await tournamentsApi.cancelTournament(tournament.id);
      setSnackbarMessage(`Tournament "${tournament.name}" cancelled`);
      fetchTournaments();
    } catch (err: any) {
      console.error('Error cancelling tournament', err);
      setSnackbarMessage('Failed to cancel tournament. ' + (err.message || ''));
    } finally {
      setActionInFlight(null);
    }
  };

  const handleOpenResolveDialog = async (tournament: Tournament) => {
    try {
      const bracket = await tournamentsApi.getBracket(tournament.id);
      setResolveBracket(bracket);
      const stuck = bracket.matchups.filter((m) => m.status === 'needs_attention');
      setResolveMatchupId(stuck[0]?.id ?? '');
      setResolveWinnerId('');
      setResolveDialogOpen(true);
    } catch (err: any) {
      console.error('Failed to load bracket', err);
      setSnackbarMessage('Failed to load the tournament bracket. ' + (err.message || ''));
    }
  };

  const stuckMatchups = useMemo(
    () => resolveBracket?.matchups.filter((m) => m.status === 'needs_attention') ?? [],
    [resolveBracket],
  );
  const selectedStuckMatchup = stuckMatchups.find((m) => m.id === resolveMatchupId);

  const resolveAgentName = (agentId: string | null) => {
    if (!agentId) return 'Unknown';
    const entrant = resolveBracket?.entrants.find((e) => e.agent_id === agentId);
    return entrant?.agent_name ?? agentNameById[agentId] ?? shortId(agentId);
  };

  const matchupLabel = (matchup: TournamentMatchup) =>
    `${matchup.bracket.replace(/_/g, ' ')} · round ${matchup.round} — ` +
    `${resolveAgentName(matchup.agent1_id)} vs ${resolveAgentName(matchup.agent2_id)}`;

  const handleResolve = async () => {
    if (!resolveBracket || !selectedStuckMatchup || !resolveWinnerId) return;
    setIsResolving(true);
    try {
      await tournamentsApi.resolveMatchup(resolveBracket.tournament.id, selectedStuckMatchup.id, resolveWinnerId);
      setSnackbarMessage('Matchup resolved');
      setResolveDialogOpen(false);
      fetchTournaments();
    } catch (err: any) {
      console.error('Error resolving matchup', err);
      setSnackbarMessage('Failed to resolve matchup. ' + (err.message || ''));
    } finally {
      setIsResolving(false);
    }
  };

  const canCreate = newName.trim().length > 0 && Boolean(newArenaId) && selectedAgents.length >= 2;

  return (
    <Box>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          Tournament Management
        </Typography>
        <Box>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={fetchTournaments} sx={{ mr: 2 }}>
            Refresh
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenCreateDialog}>
            New Tournament
          </Button>
        </Box>
      </Box>

      <Paper sx={{ p: 2.5, mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}>
        <Box>
          <FormControlLabel
            control={
              <Switch
                checked={submissionFreeze}
                disabled={freezeSaving}
                onChange={(e) => handleToggleFreeze(e.target.checked)}
                color="warning"
              />
            }
            label={<Typography fontWeight={600}>Freeze submissions</Typography>}
          />
          <Typography variant="body2" color="text.secondary">
            While on, non-admin users cannot upload, delete, or re-point agents — turn this on before starting a
            tournament so entrants can't swap their code mid-run.
          </Typography>
        </Box>
        {submissionFreeze && (
          <Typography variant="body2" fontWeight={700} color="warning.main" sx={{ whiteSpace: 'nowrap' }}>
            ● Frozen
          </Typography>
        )}
      </Paper>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
          <FormControl size="small" sx={{ minWidth: 180 }}>
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
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="running">Running</MenuItem>
              <MenuItem value="needs_attention">Needs Attention</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
              <MenuItem value="cancelled">Cancelled</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Tournament</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Arena</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : tournaments.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">No tournaments found</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                tournaments.map((tournament) => (
                  <TableRow key={tournament.id}>
                    <TableCell>
                      <PrimarySecondaryCell
                        primary={tournament.name}
                        secondary={shortId(tournament.id)}
                        title={tournament.id}
                      />
                    </TableCell>
                    <TableCell>
                      <StatusIndicator status={tournament.status} />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {arenas.find(a => a.id === tournament.arena_id)?.name || shortId(tournament.arena_id) || gameName(tournament.game_type)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{formatShortDateTime(tournament.created_at)}</Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                        {tournament.status === 'pending' && (
                          <Button
                            size="small"
                            variant="contained"
                            startIcon={<StartIcon />}
                            disabled={actionInFlight === tournament.id}
                            onClick={() => handleStart(tournament)}
                          >
                            Start
                          </Button>
                        )}
                        {tournament.status === 'needs_attention' && (
                          <Button
                            size="small"
                            variant="outlined"
                            color="warning"
                            startIcon={<AttentionIcon />}
                            onClick={() => handleOpenResolveDialog(tournament)}
                          >
                            Resolve
                          </Button>
                        )}
                        {(tournament.status === 'pending' ||
                          tournament.status === 'running' ||
                          tournament.status === 'needs_attention') && (
                          <Button
                            size="small"
                            variant="outlined"
                            color="error"
                            startIcon={<CancelIcon />}
                            disabled={actionInFlight === tournament.id}
                            onClick={() => handleCancel(tournament)}
                          >
                            Cancel
                          </Button>
                        )}
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<VisibilityIcon />}
                          onClick={() => navigate(`/tournaments/${tournament.id}`)}
                        >
                          View
                        </Button>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          component="div"
          count={-1}
          page={page}
          onPageChange={(_event, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(event) => {
            setRowsPerPage(parseInt(event.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[5, 10, 25, 50]}
          labelDisplayedRows={({ from, to }: { from: number; to: number }) => `${from}-${to}`}
        />
      </Paper>

      {/* Create Tournament Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>New Tournament</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <TextField
              label="Name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              fullWidth
              inputProps={{ maxLength: 100 }}
            />

            <FormControl fullWidth>
              <InputLabel>Arena</InputLabel>
              <Select
                value={newArenaId}
                label="Arena"
                onChange={(e) => {
                  setNewArenaId(e.target.value);
                  setSelectedAgents([]);
                }}
              >
                {arenas.map((arena) => (
                  <MenuItem key={arena.id} value={arena.id}>
                    {arena.name} ({getGameById(fromApiGameType(arena.game_type))?.name || arena.game_type})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Autocomplete
              multiple
              options={eligibleAgents}
              getOptionLabel={(option) => `${option.name} (${option.id.substring(0, 8)}…)`}
              value={selectedAgents}
              onChange={(_, newValue) => setSelectedAgents(newValue)}
              filterSelectedOptions
              disableCloseOnSelect
              limitTags={4}
              loading={loadingAgents}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Entrant Agents"
                  placeholder="Select participating agents"
                  helperText={`Select at least 2 agents with an active submission (${selectedAgents.length} selected). Byes are assigned automatically for non-power-of-2 counts.`}
                  error={selectedAgents.length === 1}
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

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="Turn Time Limit"
                type="number"
                size="small"
                value={turnTimeLimit}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  setTurnTimeLimit(Number.isNaN(val) ? DEFAULT_TURN_TIME_LIMIT : Math.max(0.1, val));
                }}
                inputProps={{ min: 0.1, step: 0.5 }}
                InputProps={{ endAdornment: <InputAdornment position="end">s</InputAdornment> }}
                sx={{ width: 170 }}
              />
              <TextField
                label="Max Concurrent Matches"
                type="number"
                size="small"
                value={maxConcurrent}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  setMaxConcurrent(Number.isNaN(val) ? DEFAULT_MAX_CONCURRENT : Math.max(1, val));
                }}
                inputProps={{ min: 1, max: 64, step: 1 }}
                helperText="Parallel matches within a round"
                sx={{ width: 200 }}
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)} variant="outlined" disabled={isCreating}>
            Cancel
          </Button>
          <Button
            onClick={handleCreateTournament}
            variant="contained"
            disabled={isCreating || !canCreate}
            startIcon={isCreating ? <CircularProgress size={20} /> : <TrophyIcon />}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Resolve Matchup Dialog */}
      <Dialog open={resolveDialogOpen} onClose={() => setResolveDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Resolve Stuck Matchup</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Alert severity="warning">
              These matchups could not be completed automatically (for example after repeated infrastructure
              failures). Declare a winner so the bracket can continue.
            </Alert>

            {stuckMatchups.length === 0 ? (
              <Typography color="text.secondary">No matchups need attention.</Typography>
            ) : (
              <>
                <FormControl fullWidth>
                  <InputLabel>Matchup</InputLabel>
                  <Select
                    value={resolveMatchupId}
                    label="Matchup"
                    onChange={(e) => {
                      setResolveMatchupId(e.target.value);
                      setResolveWinnerId('');
                    }}
                  >
                    {stuckMatchups.map((matchup) => (
                      <MenuItem key={matchup.id} value={matchup.id}>
                        {matchupLabel(matchup)}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {selectedStuckMatchup && (
                  <FormControl fullWidth>
                    <InputLabel>Winner</InputLabel>
                    <Select
                      value={resolveWinnerId}
                      label="Winner"
                      onChange={(e) => setResolveWinnerId(e.target.value)}
                    >
                      {[selectedStuckMatchup.agent1_id, selectedStuckMatchup.agent2_id]
                        .filter((agentId): agentId is string => agentId !== null)
                        .map((agentId) => (
                          <MenuItem key={agentId} value={agentId}>
                            {resolveAgentName(agentId)}
                          </MenuItem>
                        ))}
                    </Select>
                  </FormControl>
                )}
              </>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResolveDialogOpen(false)} variant="outlined" disabled={isResolving}>
            Close
          </Button>
          <Button
            onClick={handleResolve}
            variant="contained"
            color="warning"
            disabled={isResolving || !selectedStuckMatchup || !resolveWinnerId}
            startIcon={isResolving ? <CircularProgress size={20} /> : <AttentionIcon />}
          >
            Resolve
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
