import { useCallback, useEffect, useMemo, useState } from 'react';
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
import { ArrowBack, EmojiEvents } from '@mui/icons-material';
import { useSmartBack } from '../hooks/use-smart-back';
import { tournamentsApi, TournamentBracket } from '../services/api/tournaments';
import { BracketView } from '../components/tournaments/BracketView';
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

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 2 }}>
        Back
      </Button>

      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Typography variant="h4" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <EmojiEvents sx={{ fontSize: 32 }} /> {tournament.name}
        </Typography>
        <StatusIndicator status={tournament.status} />
      </Box>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        {gameName} · Double Elimination · Best of 3 · {bracket.entrants.length} entrants ·{' '}
        {tournament.config.turn_time_limit}s per turn
      </Typography>

      {tournament.status === 'completed' && championName && (
        <Alert icon={<EmojiEvents />} severity="success" sx={{ mb: 3 }}>
          Champion:{' '}
          <Link to={`/agents/${tournament.winner_agent_id}`} style={{ fontWeight: 700, color: 'inherit' }}>
            {championName}
          </Link>
        </Alert>
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
                    {standing.placement === 1 ? (
                      <EmojiEvents fontSize="small" sx={{ color: 'warning.main' }} />
                    ) : (
                      standing.placement ?? '—'
                    )}
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
    </Container>
  );
}
