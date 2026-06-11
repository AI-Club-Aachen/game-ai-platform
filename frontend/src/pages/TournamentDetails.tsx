import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { useSmartBack } from '../hooks/use-smart-back';
import { tournamentsApi, TournamentBracket } from '../services/api/tournaments';
import { alpha } from '@mui/material/styles';
import { BracketView } from '../components/tournaments/BracketView';
import { PlacementBadge } from '../components/tournaments/PlacementBadge';
import { PodiumDialog, PodiumEntry } from '../components/tournaments/PodiumDialog';
import { StatusIndicator } from '../components/common/StatusIndicator';
import { getGameById, fromApiGameType } from '../config/games';

const POLL_INTERVAL_MS = 5000;

const bracketLabel: Record<string, string> = {
  winners: 'Winners Bracket',
  losers: 'Losers Bracket',
  grand_final: 'Grand Final',
  grand_final_reset: 'Bracket Reset',
};

export function TournamentDetails() {
  const goBack = useSmartBack('/tournaments');
  const { id } = useParams<{ id: string }>();

  const [bracket, setBracket] = useState<TournamentBracket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [podiumOpen, setPodiumOpen] = useState(false);

  const fetchBracket = useCallback(async () => {
    if (!id) return;
    try {
      const data = await tournamentsApi.getBracket(id);
      setBracket(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch tournament bracket:', err);
      setError('Failed to load the tournament.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    setLoading(true);
    fetchBracket();
  }, [fetchBracket]);

  // Live-refresh the bracket while the tournament engine is advancing it.
  const status = bracket?.tournament.status;
  useEffect(() => {
    if (status !== 'running' && status !== 'needs_attention') return;
    const interval = setInterval(fetchBracket, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [status, fetchBracket]);

  // Celebrate when the tournament finishes while the page is open.
  const prevStatusRef = useRef<string | undefined>(undefined);
  useEffect(() => {
    const previous = prevStatusRef.current;
    prevStatusRef.current = status;
    if (previous && previous !== 'completed' && status === 'completed') {
      setPodiumOpen(true);
    }
  }, [status]);

  const agentNames = useMemo(() => {
    const names: Record<string, string> = {};
    for (const entrant of bracket?.entrants ?? []) {
      if (entrant.agent_name) names[entrant.agent_id] = entrant.agent_name;
    }
    return names;
  }, [bracket]);

  const seeds = useMemo(() => {
    const result: Record<string, number> = {};
    for (const entrant of bracket?.entrants ?? []) {
      if (entrant.seed !== null) result[entrant.agent_id] = entrant.seed;
    }
    return result;
  }, [bracket]);

  const podiumEntries: PodiumEntry[] = useMemo(
    () =>
      (bracket?.standings ?? [])
        .filter((standing) => standing.placement !== null && standing.placement <= 3)
        .slice(0, 3)
        .map((standing) => ({
          agentId: standing.agent_id,
          name: standing.agent_name ?? `${standing.agent_id.slice(0, 8)}…`,
          placement: standing.placement as number,
        })),
    [bracket],
  );

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error || !bracket) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 2 }}>
          Back
        </Button>
        <Alert severity="error">{error ?? 'Tournament not found.'}</Alert>
      </Container>
    );
  }

  const { tournament, standings, matchups } = bracket;
  const gameName = getGameById(fromApiGameType(tournament.game_type))?.name ?? tournament.game_type;
  const championName = tournament.winner_agent_id
    ? agentNames[tournament.winner_agent_id] ?? tournament.winner_agent_id
    : null;
  const boardSize = tournament.config.state_init_data?.board_size as number | undefined;

  return (
    <Container maxWidth={false} sx={{ py: 4 }}>
      <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 2 }}>
        Back
      </Button>

      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Typography variant="h4">{tournament.name}</Typography>
        <StatusIndicator status={tournament.status} />
      </Box>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        {gameName} · Double Elimination · Best of 3 · {bracket.entrants.length} entrants ·{' '}
        {tournament.config.turn_time_limit}s per turn
        {boardSize ? ` · ${boardSize}×${boardSize} board` : ''}
      </Typography>

      {tournament.status === 'completed' && championName && (
        <Paper
          variant="outlined"
          sx={(theme) => ({
            mb: 3,
            p: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 2,
            flexWrap: 'wrap',
            borderColor: alpha(theme.palette.primary.main, 0.35),
            background: `linear-gradient(95deg, ${alpha(theme.palette.primary.main, 0.08)} 0%, transparent 55%)`,
          })}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, minWidth: 0 }}>
            <PlacementBadge placement={1} size={36} />
            <Box sx={{ minWidth: 0 }}>
              <Typography
                variant="overline"
                color="primary"
                sx={{ letterSpacing: '0.15em', lineHeight: 1.2, fontWeight: 600 }}
              >
                Champion
              </Typography>
              <Typography
                component={Link}
                to={`/agents/${tournament.winner_agent_id}`}
                variant="h6"
                noWrap
                sx={{
                  display: 'block',
                  color: 'text.primary',
                  fontWeight: 700,
                  textDecoration: 'none',
                  '&:hover': { textDecoration: 'underline' },
                }}
              >
                {championName}
              </Typography>
            </Box>
          </Box>
          {podiumEntries.length > 0 && (
            <Button variant="outlined" size="small" onClick={() => setPodiumOpen(true)}>
              View podium
            </Button>
          )}
        </Paper>
      )}
      {tournament.status === 'needs_attention' && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          A matchup in this tournament needs admin attention before the bracket can continue.
        </Alert>
      )}
      {tournament.status === 'pending' && (
        <Alert severity="info" sx={{ mb: 3 }}>
          This tournament has not been started yet. The bracket is seeded when it starts.
        </Alert>
      )}

      {matchups.length > 0 && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <BracketView matchups={matchups} agentNames={agentNames} seeds={seeds} />
        </Paper>
      )}

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Standings
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>#</TableCell>
                <TableCell>Agent</TableCell>
                <TableCell align="right">Seed</TableCell>
                <TableCell align="right">Matchups W–L</TableCell>
                <TableCell>Eliminated In</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {standings.map((standing) => (
                <TableRow key={standing.agent_id}>
                  <TableCell>
                    <PlacementBadge placement={standing.placement} />
                  </TableCell>
                  <TableCell>
                    <Link to={`/agents/${standing.agent_id}`} style={{ color: 'inherit' }}>
                      {standing.agent_name ?? `${standing.agent_id.slice(0, 8)}…`}
                    </Link>
                  </TableCell>
                  <TableCell align="right">{standing.seed ?? '—'}</TableCell>
                  <TableCell align="right">
                    {standing.matchup_wins}–{standing.matchup_losses}
                  </TableCell>
                  <TableCell>
                    {standing.eliminated_in_bracket
                      ? `${bracketLabel[standing.eliminated_in_bracket] ?? standing.eliminated_in_bracket}${
                          standing.eliminated_in_bracket === 'winners' || standing.eliminated_in_bracket === 'losers'
                            ? ` · Round ${standing.eliminated_in_round}`
                            : ''
                        }`
                      : standing.placement === 1
                        ? 'Champion'
                        : tournament.status === 'completed' || tournament.status === 'cancelled'
                          ? '—'
                          : 'Still playing'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <PodiumDialog
        open={podiumOpen}
        onClose={() => setPodiumOpen(false)}
        tournamentName={tournament.name}
        entries={podiumEntries}
      />
    </Container>
  );
}
