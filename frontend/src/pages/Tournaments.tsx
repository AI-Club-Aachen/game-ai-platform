import { useState } from 'react';
import { Box, Container, Typography, Button, Card, CardContent, Chip, LinearProgress } from '@mui/material';
import { EmojiEvents, CalendarToday, PlayArrow, CheckCircle } from '@mui/icons-material';

interface Tournament {
  id: string;
  name: string;
  status: 'upcoming' | 'active' | 'completed';
  participants: number;
  maxParticipants: number;
  prizePool: string;
  startDate: string;
  endDate: string;
  format: string;
}

export function Tournaments() {
  const [filter, setFilter] = useState<'all' | 'upcoming' | 'active' | 'completed'>('all');

  const tournaments: Tournament[] = [
    { id: '1', name: 'Fall Championship 2025', status: 'active', participants: 48, maxParticipants: 64, prizePool: '$5,000', startDate: '2025-11-01', endDate: '2025-11-15', format: 'Single Elimination' },
    { id: '2', name: 'Winter League Qualifiers', status: 'upcoming', participants: 32, maxParticipants: 128, prizePool: '$10,000', startDate: '2025-12-01', endDate: '2025-12-20', format: 'Round Robin' },
    { id: '3', name: 'Quick Match Tournament', status: 'upcoming', participants: 12, maxParticipants: 32, prizePool: '$1,000', startDate: '2025-11-10', endDate: '2025-11-11', format: 'Double Elimination' },
    { id: '4', name: 'October Masters', status: 'completed', participants: 64, maxParticipants: 64, prizePool: '$3,000', startDate: '2025-10-01', endDate: '2025-10-20', format: 'Swiss System' },
    { id: '5', name: 'Summer Championship', status: 'completed', participants: 128, maxParticipants: 128, prizePool: '$15,000', startDate: '2025-08-01', endDate: '2025-08-31', format: 'Single Elimination' },
  ];

  const filteredTournaments = tournaments.filter(
    t => filter === 'all' || t.status === filter
  );

  const getStatusConfig = (status: Tournament['status']) => {
    const configs = {
      upcoming: { icon: CalendarToday, color: 'default' as const },
      active: { icon: PlayArrow, color: 'success' as const },
      completed: { icon: CheckCircle, color: 'default' as const },
    };
    return configs[status];
  };

  const filters: { key: typeof filter; label: string }[] = [
    { key: 'all', label: 'All Tournaments' },
    { key: 'upcoming', label: 'Upcoming' },
    { key: 'active', label: 'Active' },
    { key: 'completed', label: 'Completed' },
  ];

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <EmojiEvents sx={{ fontSize: 32 }} /> Tournaments
        </Typography>
        <Typography color="text.secondary">
          Compete with the best AI agents in competitive tournaments
        </Typography>
      </Box>

      <Box sx={{ mb: 4, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        {filters.map(f => (
          <Button
            key={f.key}
            onClick={() => setFilter(f.key)}
            variant={filter === f.key ? 'contained' : 'text'}
            size="small"
            sx={{
              ...(filter !== f.key && {
                border: '1px solid',
                borderColor: 'divider',
              }),
            }}
          >
            {f.label}
          </Button>
        ))}
      </Box>

      <Box sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' },
        gap: 3,
      }}>
        {filteredTournaments.map((tournament) => {
          const statusConfig = getStatusConfig(tournament.status);
          const participationRate = (tournament.participants / tournament.maxParticipants) * 100;

          return (
            <Card key={tournament.id}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Typography variant="h6" sx={{ flexGrow: 1, pr: 1 }}>
                    {tournament.name}
                  </Typography>
                  <Chip
                    icon={<statusConfig.icon />}
                    label={tournament.status}
                    color={statusConfig.color}
                    size="small"
                  />
                </Box>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Format:</Typography>
                    <Typography variant="body2">{tournament.format}</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Prize Pool:</Typography>
                    <Typography variant="body2" color="primary" fontWeight="bold">
                      {tournament.prizePool}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Dates:</Typography>
                    <Typography variant="body2">
                      {tournament.startDate} — {tournament.endDate}
                    </Typography>
                  </Box>
                </Box>

                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Participants</Typography>
                    <Typography variant="body2">
                      {tournament.participants} / {tournament.maxParticipants}
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={participationRate}
                    sx={{ height: 4 }}
                  />
                </Box>

                <Box>
                  {tournament.status === 'upcoming' && (
                    <Button variant="contained" fullWidth>Register</Button>
                  )}
                  {tournament.status === 'active' && (
                    <Button variant="outlined" fullWidth>View Bracket</Button>
                  )}
                  {tournament.status === 'completed' && (
                    <Button variant="outlined" fullWidth>View Results</Button>
                  )}
                </Box>
              </CardContent>
            </Card>
          );
        })}
      </Box>
    </Container>
  );
}
