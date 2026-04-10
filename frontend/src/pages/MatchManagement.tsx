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
  Chip,
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
} from '@mui/icons-material';
import { matchesApi } from '../services/api/matches';
import { agentsApi, Agent } from '../services/api/agents';

// Mirrors backend MatchConfig – update here when new fields are added.
interface MatchConfig {
  turn_time_limit: number | null;
}

const DEFAULT_CONFIG: MatchConfig = {
  turn_time_limit: 10,
};

export function MatchManagement() {
  const navigate = useNavigate();
  const [matches, setMatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const [filterGameType, setFilterGameType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const [createDialogOpen, setDialogOpen] = useState(false);
  const [newMatchGameType, setNewMatchGameType] = useState('tictactoe');
  const [matchConfig, setMatchConfig] = useState<MatchConfig>(DEFAULT_CONFIG);
  const [timeLimitEnabled, setTimeLimitEnabled] = useState(true);
  const [selectedAgents, setSelectedAgents] = useState<Agent[]>([]);

  const [agents, setAgents] = useState<Agent[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);

  const [isCreating, setIsCreating] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState<string | null>(null);

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
    agentsApi.getAgents(0, 1000, true)
      .then(res => {
        const agentsData = Array.isArray(res) ? res : (res as any).data || [];
        setAgents(agentsData);
      })
      .catch(err => console.error("Failed to fetch agents", err))
      .finally(() => setLoadingAgents(false));
  }, []);

  const handleChangePage = (_event: unknown, newPage: number) => setPage(newPage);

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleOpenDialog = () => {
    setMatchConfig(DEFAULT_CONFIG);
    setTimeLimitEnabled(true);
    setSelectedAgents([]);
    setNewMatchGameType('tictactoe');
    setDialogOpen(true);
  };

  const buildConfig = (): MatchConfig => ({
    turn_time_limit: timeLimitEnabled ? (matchConfig.turn_time_limit ?? 10) : null,
  });

  const handleCreateMatch = async () => {
    const agentIdsArray = selectedAgents.map(a => a.id);
    const config = buildConfig();

    setIsCreating(true);
    try {
      await matchesApi.createMatch({
        game_type: newMatchGameType,
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

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return 'success';
      case 'running': return 'primary';
      case 'failed':
      case 'client_error': return 'error';
      case 'queued': return 'warning';
      default: return 'default';
    }
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
                <TableCell>ID</TableCell>
                <TableCell>Game Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Created At</TableCell>
                <TableCell>Agents</TableCell>
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
                matches.map((match) => (
                  <TableRow key={match.id}>
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                      {match.id.substring(0, 8)}...
                    </TableCell>
                    <TableCell>
                      {match.game_type}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={match.status}
                        color={getStatusColor(match.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {new Date(match.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                      {match.agent_ids && match.agent_ids.length > 0
                        ? match.agent_ids.map((id: string) => {
                          const found = agents.find(a => a.id === id);
                          return found ? found.name : id.substring(0, 8) + '...';
                        }).join(', ')
                        : 'None'}
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
                ))
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

            {/* Game type */}
            <FormControl fullWidth>
              <InputLabel>Game Type</InputLabel>
              <Select
                value={newMatchGameType}
                onChange={(e) => {
                  setNewMatchGameType(e.target.value);
                  setSelectedAgents([]);
                }}
                label="Game Type"
              >
                <MenuItem value="tictactoe">Tic-Tac-Toe</MenuItem>
                <MenuItem value="connect_four">Connect Four</MenuItem>
                <MenuItem value="chess">Chess</MenuItem>
              </Select>
            </FormControl>

            {/* Agent picker */}
            <Autocomplete
              multiple
              options={agents.filter(a => a.game_type === newMatchGameType)}
              getOptionLabel={(option) => `${option.name} (${option.id.substring(0, 8)}...)`}
              value={selectedAgents}
              onChange={(_, newValue) => setSelectedAgents(newValue)}
              filterSelectedOptions
              loading={loadingAgents}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Select Agents"
                  placeholder="Select participating agents"
                  helperText="Search and select agents by name or ID. List filtered by selected game type."
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
                    disabled={!timeLimitEnabled}
                    value={timeLimitEnabled ? (matchConfig.turn_time_limit ?? 10) : ''}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      setMatchConfig(prev => ({
                        ...prev,
                        turn_time_limit: isNaN(val) ? null : Math.max(0.1, val),
                      }));
                    }}
                    inputProps={{ min: 0.1, step: 0.5 }}
                    InputProps={{
                      endAdornment: <InputAdornment position="end">s</InputAdornment>,
                    }}
                    sx={{ width: 140 }}
                  />
                </Box>
                <FormControlLabel
                  control={
                    <Switch
                      checked={timeLimitEnabled}
                      onChange={(e) => setTimeLimitEnabled(e.target.checked)}
                      size="small"
                    />
                  }
                  label={
                    <Typography variant="body2" color="text.secondary">
                      {timeLimitEnabled ? 'Enabled' : 'Disabled'}
                    </Typography>
                  }
                  sx={{ mt: 3, mr: 0 }}
                />
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
            disabled={isCreating}
            startIcon={isCreating ? <CircularProgress size={20} /> : <PlayIcon />}
          >
            Start Match
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
