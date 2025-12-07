import { useState } from 'react';
import { Box, Container, Typography, Card, CardContent, Button, Chip, LinearProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import { Visibility, ArrowBack, PlayCircle, Videocam, History, EmojiEvents, PlayArrow } from '@mui/icons-material';

interface LiveGame {
  id: string;
  player1: {
    name: string;
    agent: string;
    score: number;
  };
  player2: {
    name: string;
    agent: string;
    score: number;
  };
  gameType: string;
  startedAt: string;
  viewers: number;
  round: number;
  maxRounds: number;
}

interface PastGame {
  id: string;
  player1: { name: string; agent: string; score: number };
  player2: { name: string; agent: string; score: number };
  winner: string;
  gameType: string;
  playedAt: string;
  duration: string;
  rounds: number;
}

export function LiveGames() {
  const [selectedGame, setSelectedGame] = useState<string | null>(null);

  const liveGames: LiveGame[] = [
    {
      id: 'game_1',
      player1: { name: 'AImaster', agent: 'GammaNet v1.5', score: 45 },
      player2: { name: 'BotBuilder', agent: 'DeepMind v2.0', score: 42 },
      gameType: 'Chess AI',
      startedAt: '10 min ago',
      viewers: 127,
      round: 15,
      maxRounds: 50,
    },
    {
      id: 'game_2',
      player1: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 38 },
      player2: { name: 'CodeNinja', agent: 'SwiftAI v3.0', score: 35 },
      gameType: 'Strategy Game',
      startedAt: '5 min ago',
      viewers: 89,
      round: 22,
      maxRounds: 100,
    },
    {
      id: 'game_3',
      player1: { name: 'MLEngineer', agent: 'TensorBot v1.0', score: 15 },
      player2: { name: 'GameDev', agent: 'StrategyX v2.1', score: 18 },
      gameType: 'RTS Battle',
      startedAt: '2 min ago',
      viewers: 52,
      round: 8,
      maxRounds: 30,
    },
  ];

  const pastGames: PastGame[] = [
    { id: 'past_1', player1: { name: 'AImaster', agent: 'GammaNet v1.5', score: 50 }, player2: { name: 'BotBuilder', agent: 'DeepMind v2.0', score: 45 }, winner: 'AImaster', gameType: 'Chess AI', playedAt: '2025-11-01 10:30', duration: '15m 32s', rounds: 50 },
    { id: 'past_2', player1: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 42 }, player2: { name: 'CodeNinja', agent: 'SwiftAI v3.0', score: 48 }, winner: 'CodeNinja', gameType: 'Strategy Game', playedAt: '2025-11-01 09:15', duration: '22m 18s', rounds: 100 },
    { id: 'past_3', player1: { name: 'MLEngineer', agent: 'TensorBot v1.0', score: 25 }, player2: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 28 }, winner: 'demo_user', gameType: 'RTS Battle', playedAt: '2025-10-31 18:45', duration: '18m 05s', rounds: 30 },
    { id: 'past_4', player1: { name: 'GameDev', agent: 'StrategyX v2.1', score: 38 }, player2: { name: 'demo_user', agent: 'AlphaBot v1.1', score: 35 }, winner: 'GameDev', gameType: 'Strategy Game', playedAt: '2025-10-31 14:20', duration: '25m 42s', rounds: 100 },
    { id: 'past_5', player1: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 48 }, player2: { name: 'Competitor', agent: 'AlgoMaster v1.0', score: 40 }, winner: 'demo_user', gameType: 'Chess AI', playedAt: '2025-10-30 16:00', duration: '12m 55s', rounds: 50 },
  ];

  const selectedGameData = liveGames.find(g => g.id === selectedGame);

  if (selectedGame && selectedGameData) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Button startIcon={<ArrowBack />} onClick={() => setSelectedGame(null)} sx={{ mb: 3 }}>
          Back to Live Games
        </Button>
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 4, flexGrow: 1 }}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h6">{selectedGameData.player1.name}</Typography>
                  <Typography variant="body2" color="text.secondary">{selectedGameData.player1.agent}</Typography>
                  <Typography variant="h4" color="primary" sx={{ mt: 1 }}>{selectedGameData.player1.score}</Typography>
                </Box>
                <Typography variant="h5" color="text.secondary">VS</Typography>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h6">{selectedGameData.player2.name}</Typography>
                  <Typography variant="body2" color="text.secondary">{selectedGameData.player2.agent}</Typography>
                  <Typography variant="h4" color="primary" sx={{ mt: 1 }}>{selectedGameData.player2.score}</Typography>
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>
        <Card sx={{ mb: 3, minHeight: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <CardContent sx={{ textAlign: 'center' }}>
            <Videocam sx={{ fontSize: 64, mb: 2, color: 'primary.main' }} />
            <Typography variant="h4" gutterBottom>Game Visualization</Typography>
            <Typography variant="h6" color="text.secondary" gutterBottom>Round {selectedGameData.round} of {selectedGameData.maxRounds}</Typography>
            <Chip label="LIVE" color="error" sx={{ mt: 2 }} />
          </CardContent>
        </Card>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' }, gap: 2 }}>
          <Card><CardContent><Typography variant="body2" color="text.secondary">Game Type</Typography><Typography variant="h6">{selectedGameData.gameType}</Typography></CardContent></Card>
          <Card><CardContent><Typography variant="body2" color="text.secondary">Started</Typography><Typography variant="h6">{selectedGameData.startedAt}</Typography></CardContent></Card>
          <Card><CardContent><Typography variant="body2" color="text.secondary">Viewers</Typography><Typography variant="h6"><Visibility sx={{ fontSize: 20, mr: 0.5, verticalAlign: 'middle' }} />{selectedGameData.viewers}</Typography></CardContent></Card>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PlayCircle sx={{ fontSize: 36 }} /> Games
        </Typography>
        <Typography color="text.secondary">Watch live games or review past matches</Typography>
      </Box>

      {/* Live Games Section */}
      <Box sx={{ mb: 6 }}>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Videocam sx={{ fontSize: 28 }} /> Live Games
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#ef4444', animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite', '@keyframes pulse': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.5 } } }} />
            <Typography color="text.secondary">{liveGames.length} games currently in progress</Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }, gap: 3 }}>
          {liveGames.map((game) => (
            <Card key={game.id}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                  <Chip label={game.gameType} size="small" sx={{ borderRadius: 0 }} />
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}><Visibility sx={{ fontSize: 16 }} /><Typography variant="body2">{game.viewers}</Typography></Box>
                </Box>
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Box><Typography variant="body2" fontWeight="bold">{game.player1.name}</Typography><Typography variant="caption" color="text.secondary">{game.player1.agent}</Typography></Box>
                    <Typography variant="h5" color="primary">{game.player1.score}</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', my: 1 }}>VS</Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box><Typography variant="body2" fontWeight="bold">{game.player2.name}</Typography><Typography variant="caption" color="text.secondary">{game.player2.agent}</Typography></Box>
                    <Typography variant="h5" color="primary">{game.player2.score}</Typography>
                  </Box>
                </Box>
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="caption">Round {game.round} / {game.maxRounds}</Typography>
                    <Typography variant="caption">{game.startedAt}</Typography>
                  </Box>
                  <LinearProgress variant="determinate" value={(game.round / game.maxRounds) * 100} sx={{ height: 6, borderRadius: 0, backgroundColor: '#333', '& .MuiLinearProgress-bar': { background: 'linear-gradient(90deg, #00D98B 0%, #00A6FF 100%)' } }} />
                </Box>
                <Button variant="gradientBorder" fullWidth onClick={() => setSelectedGame(game.id)}>Watch Game</Button>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Box>

      {/* Past Games Section */}
      <Box>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <History sx={{ fontSize: 28 }} /> Past Games
          </Typography>
          <Typography color="text.secondary">Review and analyze previous matches</Typography>
        </Box>
        <TableContainer component={Card}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Players</TableCell>
                <TableCell>Game Type</TableCell>
                <TableCell>Winner</TableCell>
                <TableCell>Score</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell>Played At</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {pastGames.map((game) => (
                <TableRow key={game.id} sx={{ '&:hover': { backgroundColor: '#2a2a2a' } }}>
                  <TableCell>
                    <Box>
                      <Typography variant="body2" fontWeight="bold">{game.player1.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{game.player1.agent}</Typography>
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ my: 0.5 }}>vs</Typography>
                    <Box>
                      <Typography variant="body2" fontWeight="bold">{game.player2.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{game.player2.agent}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip label={game.gameType} size="small" sx={{ borderRadius: 0 }} />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <EmojiEvents sx={{ fontSize: 16, color: '#f59e0b' }} />
                      <Typography>{game.winner}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography>{game.player1.score} - {game.player2.score}</Typography>
                  </TableCell>
                  <TableCell>{game.duration}</TableCell>
                  <TableCell>{game.playedAt}</TableCell>
                  <TableCell align="right">
                    <Button 
                      size="small" 
                      startIcon={<PlayArrow />}
                      variant="gradientBorder"
                      onClick={() => setSelectedGame(game.id)}
                    >
                      Replay
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Container>
  );
}
