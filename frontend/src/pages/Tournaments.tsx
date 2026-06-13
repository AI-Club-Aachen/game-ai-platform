import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Container,
  Typography,
} from '@mui/material';
import { tournamentsApi, Tournament, TournamentStatus } from '../services/api/tournaments';
import { StatusIndicator } from '../components/common/StatusIndicator';
import { PlacementBadge } from '../components/tournaments/PlacementBadge';
import { getGameById, fromApiGameType } from '../config/games';

type StatusFilter = 'all' | TournamentStatus;

const FILTERS: { key: StatusFilter; label: string }[] = [
  { key: 'all', label: 'All Tournaments' },
  { key: 'pending', label: 'Pending' },
  { key: 'running', label: 'Running' },
  { key: 'completed', label: 'Completed' },
  { key: 'cancelled', label: 'Cancelled' },
];

const formatDate = (isoDate: string) => {
  const date = new Date(isoDate);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleDateString();
};

const gameName = (gameType: string) => getGameById(fromApiGameType(gameType))?.name ?? gameType;

export function Tournaments() {
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [tournaments, setTournaments] = useState<Tournament[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTournaments = useCallback(async () => {
    setLoading(true);
    try {
      const data = await tournamentsApi.getTournaments({
        status: filter !== 'all' ? filter : undefined,
        limit: 100,
      });
      setTournaments(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch tournaments:', err);
      setError('Failed to load tournaments.');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchTournaments();
  }, [fetchTournaments]);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Tournaments
        </Typography>
        <Typography color="text.secondary">
          Double-elimination tournaments between the platform's AI agents
        </Typography>
      </Box>

      <Box sx={{ mb: 4, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        {FILTERS.map(({ key, label }) => (
          <Button
            key={key}
            onClick={() => setFilter(key)}
            variant={filter === key ? 'contained' : 'text'}
            size="small"
            sx={{
              ...(filter !== key && {
                border: '1px solid',
                borderColor: 'divider',
              }),
            }}
          >
            {label}
          </Button>
        ))}
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : tournaments.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <Typography color="text.secondary">No tournaments found</Typography>
        </Box>
      ) : (
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' },
            gap: 3,
          }}
        >
          {tournaments.map((tournament) => (
            <Card
              key={tournament.id}
              component={Link}
              to={`/tournaments/${tournament.id}`}
              sx={{
                textDecoration: 'none',
                transition: 'transform 0.15s, box-shadow 0.15s',
                '&:hover': { transform: 'translateY(-2px)', boxShadow: 4 },
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1, gap: 1 }}>
                  <Typography variant="h6" noWrap title={tournament.name}>
                    {tournament.name}
                  </Typography>
                  <StatusIndicator status={tournament.status} />
                </Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {gameName(tournament.game_type)} · Double Elimination · Best of 3
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Created {formatDate(tournament.created_at)}
                </Typography>
                {tournament.status === 'completed' && tournament.winner_agent_id && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1.5 }}>
                    <PlacementBadge placement={1} size={20} />
                    <Typography variant="body2" color="text.secondary">
                      Champion crowned — view the podium
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          ))}
        </Box>
      )}
    </Container>
  );
}
