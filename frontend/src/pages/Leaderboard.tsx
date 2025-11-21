import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getActiveGames } from '../config/games';
//import { getGameById } from '../config/games'; //TODO
import { Box, Container, Typography, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, LinearProgress } from '@mui/material';
import { EmojiEvents } from '@mui/icons-material';

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
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedGame, setSelectedGame] = useState<string>(searchParams.get('game') || 'chess');
  const activeGames = getActiveGames();

  useEffect(() => {
    const gameParam = searchParams.get('game');
    if (gameParam) {
      setSelectedGame(gameParam);
    }
  }, [searchParams]);

  const handleGameChange = (gameId: string) => {
    setSelectedGame(gameId);
    setSearchParams({ game: gameId });
  };

  const entries: LeaderboardEntry[] = [
    { rank: 1, username: 'AImaster', agentName: 'GammaNet', score: 2450, wins: 52, losses: 8, winRate: 86.7, language: 'Python', gameId: selectedGame },
    { rank: 2, username: 'BotBuilder', agentName: 'DeepMind', score: 2380, wins: 48, losses: 10, winRate: 82.8, language: 'Python', gameId: selectedGame },
    { rank: 3, username: 'demo_user', agentName: 'AlphaBot', score: 2250, wins: 45, losses: 12, winRate: 78.9, language: 'Python', gameId: selectedGame },
    { rank: 4, username: 'CodeNinja', agentName: 'SwiftAI', score: 2180, wins: 42, losses: 15, winRate: 73.7, language: 'JavaScript', gameId: selectedGame },
    { rank: 5, username: 'MLEngineer', agentName: 'TensorBot', score: 2140, wins: 40, losses: 16, winRate: 71.4, language: 'Python', gameId: selectedGame },
    { rank: 6, username: 'GameDev', agentName: 'StrategyX', score: 2090, wins: 39, losses: 18, winRate: 68.4, language: 'TypeScript', gameId: selectedGame },
    { rank: 7, username: 'RoboticsExpert', agentName: 'BetaAI', score: 2020, wins: 38, losses: 19, winRate: 66.7, language: 'JavaScript', gameId: selectedGame },
    { rank: 8, username: 'Competitor', agentName: 'AlgoMaster', score: 1980, wins: 35, losses: 20, winRate: 63.6, language: 'Python', gameId: selectedGame },
    { rank: 9, username: 'NewPlayer', agentName: 'FirstBot', score: 1920, wins: 32, losses: 23, winRate: 58.2, language: 'JavaScript', gameId: selectedGame },
    { rank: 10, username: 'Learner', agentName: 'BasicAI', score: 1850, wins: 28, losses: 27, winRate: 50.9, language: 'Python', gameId: selectedGame },
  ];

  const getRankBadge = (rank: number) => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return `#${rank}`;
  };

  //const currentGame = getGameById(selectedGame); //TODO

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <EmojiEvents sx={{ fontSize: 36 }} /> Leaderboard
        </Typography>
        <Typography color="text.secondary">
          Top performing AI agents across all games
        </Typography>
      </Box>

      <Box sx={{ mb: 4 }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Select Game:
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {activeGames.map((game) => (
            <Button
              key={game.id}
              onClick={() => handleGameChange(game.id)}
              size="small"
              sx={{
                borderRadius: 0,
                border: selectedGame === game.id ? 'none' : '1px solid #333',
                backgroundColor: selectedGame === game.id ? '#2a2a2a !important' : 'transparent',
                backgroundImage: 'none !important',
                color: selectedGame === game.id ? '#00A6FF !important' : '#ddd',
                '&:hover': {
                  border: '1px solid #00A6FF',
                  backgroundColor: '#2a2a2a !important',
                  backgroundImage: 'none !important',
                  color: '#00A6FF !important',
                },
              }}
            >
              {game.name}
            </Button>
          ))}
        </Box>
      </Box>

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
                  backgroundColor: entry.rank <= 3 ? 'rgba(0, 217, 139, 0.1)' : 'inherit'
                }}
              >
                <TableCell>
                  <Typography variant="h6">
                    {getRankBadge(entry.rank)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <strong>{entry.username}</strong>
                </TableCell>
                <TableCell>{entry.agentName}</TableCell>
                <TableCell>
                  <Chip label={entry.language} size="small" sx={{ borderRadius: 0 }} />
                </TableCell>
                <TableCell align="right">
                  <Typography color="primary" fontWeight="bold">
                    {entry.score}
                  </Typography>
                </TableCell>
                <TableCell align="right" sx={{ color: '#10b981' }}>
                  {entry.wins}
                </TableCell>
                <TableCell align="right" sx={{ color: '#ef4444' }}>
                  {entry.losses}
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 120 }}>
                    <Box sx={{ flexGrow: 1 }}>
                      <LinearProgress
                        variant="determinate"
                        value={entry.winRate}
                        sx={{
                          height: 8,
                          borderRadius: 0,
                          backgroundColor: '#333',
                          '& .MuiLinearProgress-bar': {
                            background: 'linear-gradient(90deg, #00D98B 0%, #00A6FF 100%)'
                          }
                        }}
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
    </Container>
  );
}
