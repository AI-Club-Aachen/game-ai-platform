import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Box, Container, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, LinearProgress, Card, Button, FormControl, Select, MenuItem, TableSortLabel } from '@mui/material';
import { EmojiEvents, ArrowBack } from '@mui/icons-material';
import { overlays } from '../theme';
import { useSmartBack } from '../hooks/use-smart-back';
import { getActiveGames, toApiGameType } from '../config/games';

interface LeaderboardEntry {
  id: string;
  rank: number;
  username: string;
  agentName: string;
  elo: number;
  wins: number;
  losses: number;
  winRate: number;
  gameId: string;
}

export function Leaderboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const gameFromQuery = searchParams.get('game');
  const [selectedGame, setSelectedGame] = useState<string>(gameFromQuery || 'chess');
  const goBack = useSmartBack('/dashboard');
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);

  type Order = 'asc' | 'desc';
  const [order, setOrder] = useState<Order>('desc');
  const [orderBy, setOrderBy] = useState<keyof LeaderboardEntry>('elo');

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const { agentsApi } = await import('../services/api/agents');
        const data = await agentsApi.getLeaderboard(toApiGameType(selectedGame));
        setEntries(data.map((d: any, index: number) => {
          const matchesPlayed = d.matches_played || (d.wins + d.losses);
          const winRate = matchesPlayed > 0 ? (d.wins / matchesPlayed) * 100 : 0;
          return {
            id: d.id,
            rank: index + 1,
            username: d.username,
            agentName: d.agent_name,
            elo: d.elo || 0,
            wins: d.wins,
            losses: d.losses,
            winRate: winRate,
            gameId: d.game_type
          };
        }));
      } catch (err) {
        console.error('Failed to fetch leaderboard:', err);
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

  const handleRequestSort = (property: keyof LeaderboardEntry) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const sortedEntries = [...entries].sort((a, b) => {
    let valA = a[orderBy];
    let valB = b[orderBy];

    // Handle string comparisons
    if (typeof valA === 'string' && typeof valB === 'string') {
      valA = valA.toLowerCase();
      valB = valB.toLowerCase();
    }

    if (valA < valB) return order === 'asc' ? -1 : 1;
    if (valA > valB) return order === 'asc' ? 1 : -1;
    return 0;
  });

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 2 }}>
        Back
      </Button>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <EmojiEvents sx={{ fontSize: 32 }} /> Leaderboard
          </Typography>
          <Typography color="text.secondary">
            Top performing AI agents across all games
          </Typography>
        </Box>
        <FormControl variant="outlined" size="small" sx={{ minWidth: 200 }}>
          <Select
            value={selectedGame}
            onChange={(e) => {
              const newGame = e.target.value as string;
              setSelectedGame(newGame);
              setSearchParams({ game: newGame });
            }}
          >
            {getActiveGames().map(game => (
              <MenuItem key={game.id} value={game.id}>{game.name}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sortDirection={orderBy === 'rank' ? order : false}>
                  <TableSortLabel
                    active={orderBy === 'rank'}
                    direction={orderBy === 'rank' ? order : 'asc'}
                    onClick={() => handleRequestSort('rank')}
                  >
                    Rank
                  </TableSortLabel>
                </TableCell>
                <TableCell sortDirection={orderBy === 'username' ? order : false}>
                  <TableSortLabel
                    active={orderBy === 'username'}
                    direction={orderBy === 'username' ? order : 'asc'}
                    onClick={() => handleRequestSort('username')}
                  >
                    User
                  </TableSortLabel>
                </TableCell>
                <TableCell sortDirection={orderBy === 'agentName' ? order : false}>
                  <TableSortLabel
                    active={orderBy === 'agentName'}
                    direction={orderBy === 'agentName' ? order : 'asc'}
                    onClick={() => handleRequestSort('agentName')}
                  >
                    Agent
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right" sortDirection={orderBy === 'elo' ? order : false}>
                  <TableSortLabel
                    active={orderBy === 'elo'}
                    direction={orderBy === 'elo' ? order : 'asc'}
                    onClick={() => handleRequestSort('elo')}
                  >
                    Elo
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right" sortDirection={orderBy === 'wins' ? order : false}>
                  <TableSortLabel
                    active={orderBy === 'wins'}
                    direction={orderBy === 'wins' ? order : 'asc'}
                    onClick={() => handleRequestSort('wins')}
                  >
                    Wins
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right" sortDirection={orderBy === 'losses' ? order : false}>
                  <TableSortLabel
                    active={orderBy === 'losses'}
                    direction={orderBy === 'losses' ? order : 'asc'}
                    onClick={() => handleRequestSort('losses')}
                  >
                    Losses
                  </TableSortLabel>
                </TableCell>
                <TableCell sortDirection={orderBy === 'winRate' ? order : false}>
                  <TableSortLabel
                    active={orderBy === 'winRate'}
                    direction={orderBy === 'winRate' ? order : 'asc'}
                    onClick={() => handleRequestSort('winRate')}
                  >
                    Win Rate
                  </TableSortLabel>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedEntries.map((entry) => (
                <TableRow
                  key={entry.id}
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
                  <TableCell align="right">
                    <Typography color="primary" fontWeight="bold">
                      {entry.elo}
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
