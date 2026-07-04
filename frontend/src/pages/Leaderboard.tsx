import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Box, Container, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, LinearProgress, Card, Button, FormControl, Select, MenuItem, TableSortLabel } from '@mui/material';
import { EmojiEvents, ArrowBack } from '@mui/icons-material';
import { overlays } from '../theme';
import { useSmartBack } from '../hooks/use-smart-back';
import { getGameById, fromApiGameType } from '../config/games';
import { arenasApi, ArenaRead } from '../services/api/arenas';

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
  const arenaFromQuery = searchParams.get('arena');

  const [arenas, setArenas] = useState<ArenaRead[]>([]);
  const [selectedArena, setSelectedArena] = useState<string>(arenaFromQuery || '');
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [arenasLoading, setArenasLoading] = useState<boolean>(true);

  const goBack = useSmartBack('/dashboard');

  type Order = 'asc' | 'desc';
  const [order, setOrder] = useState<Order>('desc');
  const [orderBy, setOrderBy] = useState<keyof LeaderboardEntry>('elo');

  // Fetch active arenas once on mount
  useEffect(() => {
    const fetchArenas = async () => {
      try {
        setArenasLoading(true);
        const data = await arenasApi.getArenas();
        const activeArenas = data.filter(a => a.is_active);
        setArenas(activeArenas);
      } catch (err) {
        console.error('Failed to fetch arenas:', err);
      } finally {
        setArenasLoading(false);
      }
    };
    fetchArenas();
  }, []);

  // Update selectedArena when query param or arenas list changes
  useEffect(() => {
    if (arenas.length === 0) return;

    if (arenaFromQuery && arenas.some(a => a.id === arenaFromQuery)) {
      setSelectedArena(arenaFromQuery);
    } else {
      // Default to the first arena
      setSelectedArena(arenas[0].id);
      setSearchParams({ arena: arenas[0].id });
    }
  }, [arenaFromQuery, arenas, setSearchParams]);

  useEffect(() => {
    if (!selectedArena) return;

    const fetchLeaderboard = async () => {
      setLoading(true);
      try {
        const { agentsApi } = await import('../services/api/agents');
        const data = await agentsApi.getLeaderboardByArena(selectedArena);
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
      } finally {
        setLoading(false);
      }
    };
    fetchLeaderboard();
  }, [selectedArena]);

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
          {selectedArena && arenas.length > 0 ? (
            (() => {
              const arenaObj = arenas.find(a => a.id === selectedArena);
              const game = arenaObj ? getGameById(fromApiGameType(arenaObj.game_type)) : null;
              return (
                <Typography color="text.secondary">
                  Top performing AI agents in {arenaObj?.name || 'this arena'}{game ? ` (${game.name})` : ''}
                </Typography>
              );
            })()
          ) : (
            <Typography color="text.secondary">
              Top performing AI agents across all arenas
            </Typography>
          )}
        </Box>
        <FormControl variant="outlined" size="small" sx={{ minWidth: 260 }}>
          <Select
            value={selectedArena}
            onChange={(e) => {
              const arenaId = e.target.value as string;
              setSelectedArena(arenaId);
              setSearchParams({ arena: arenaId });
            }}
            disabled={arenasLoading || arenas.length === 0}
            displayEmpty
          >
            {arenasLoading ? (
              <MenuItem disabled value="">
                Loading arenas...
              </MenuItem>
            ) : arenas.length === 0 ? (
              <MenuItem disabled value="">
                No arenas available
              </MenuItem>
            ) : (
              arenas.map(arena => {
                const game = getGameById(fromApiGameType(arena.game_type));
                return (
                  <MenuItem key={arena.id} value={arena.id}>
                    {arena.name} ({game?.name || arena.game_type})
                  </MenuItem>
                );
              })
            )}
          </Select>
        </FormControl>
      </Box>

      <Card sx={{ position: 'relative' }}>
        {loading && (
          <LinearProgress
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              zIndex: 1,
              height: 4,
            }}
          />
        )}
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
              {!loading && sortedEntries.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 6, color: 'text.secondary' }}>
                    No ranked agents in this arena yet.
                  </TableCell>
                </TableRow>
              ) : (
                sortedEntries.map((entry) => (
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
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>
    </Container>
  );
}
