import { useState, useEffect } from 'react';
import { Box, Container, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, LinearProgress, Card, Button } from '@mui/material';
import { EmojiEvents, ArrowBack } from '@mui/icons-material';
import { overlays } from '../theme';
import { useSmartBack } from '../hooks/use-smart-back';

interface LeaderboardEntry {
  rank: number;
  username: string;
  agentName: string;
  score: number;
  wins: number;
  losses: number;
  winRate: number;
  language: string;
  gameId: string;
}

export function Leaderboard() {
  const [selectedGame] = useState<string>('chess');
  const goBack = useSmartBack('/dashboard');
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        setLoading(true);
        const { agentsApi } = await import('../services/api/agents');
        const data = await agentsApi.getLeaderboard(selectedGame);
        setEntries(data.map((d: any, index: number) => {
          const matchesPlayed = d.matches_played || (d.wins + d.losses);
          const winRate = matchesPlayed > 0 ? (d.wins / matchesPlayed) * 100 : 0;
          return {
            id: d.id,
            rank: index + 1,
            username: d.username,
            agentName: d.agent_name,
            score: d.elo || 0,
            wins: d.wins,
            losses: d.losses,
            winRate: winRate,
            language: 'Unknown',
            gameId: d.game_type
          };
        }));
      } catch (err) {
        console.error('Failed to fetch leaderboard:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchLeaderboard();
  }, [selectedGame]);

  const getRankBadge = (rank: number) => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return `#${rank}`;
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 2 }}>
        Back
      </Button>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <EmojiEvents sx={{ fontSize: 32 }} /> Leaderboard
        </Typography>
        <Typography color="text.secondary">
          Top performing AI agents across all games
        </Typography>
      </Box>

      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Rank</TableCell>
                <TableCell>User</TableCell>
                <TableCell>Agent</TableCell>
                <TableCell>Language</TableCell>
                <TableCell align="right">Score</TableCell>
                <TableCell align="right">Wins</TableCell>
                <TableCell align="right">Losses</TableCell>
                <TableCell>Win Rate</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {entries.map((entry) => (
                <TableRow
                  key={entry.rank}
                  sx={{
                    backgroundColor: entry.rank <= 3 ? overlays.primaryGlowFaint : 'inherit'
                  }}
                >
                  <TableCell>
                    <Typography variant="h6" sx={{ fontSize: '1rem' }}>
                      {getRankBadge(entry.rank)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <strong>{entry.username}</strong>
                  </TableCell>
                  <TableCell>{entry.agentName}</TableCell>
                  <TableCell>
                    <Chip label={entry.language} size="small" />
                  </TableCell>
                  <TableCell align="right">
                    <Typography color="primary" fontWeight="bold">
                      {entry.score}
                    </Typography>
                  </TableCell>
                  <TableCell align="right" sx={{ color: 'success.main' }}>
                    {entry.wins}
                  </TableCell>
                  <TableCell align="right" sx={{ color: 'error.main' }}>
                    {entry.losses}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 120 }}>
                      <Box sx={{ flexGrow: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={entry.winRate}
                          sx={{ height: 6 }}
                        />
                      </Box>
                      <Typography variant="body2" sx={{ minWidth: 50 }}>
                        {entry.winRate.toFixed(1)}%
                      </Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>
    </Container>
  );
}
