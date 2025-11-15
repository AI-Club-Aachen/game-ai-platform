import { useState } from 'react';
import { Box, Container, Typography, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, Card, CardContent } from '@mui/material';
import { ArrowBack, PlayArrow, EmojiEvents, History, Movie, SkipPrevious, SkipNext } from '@mui/icons-material';

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

export function PastGames() {
  const [filter, setFilter] = useState<'all' | 'wins' | 'losses'>('all');
  const [selectedGame, setSelectedGame] = useState<string | null>(null);

  const pastGames: PastGame[] = [
    { id: 'past_1', player1: { name: 'AImaster', agent: 'GammaNet v1.5', score: 50 }, player2: { name: 'BotBuilder', agent: 'DeepMind v2.0', score: 45 }, winner: 'AImaster', gameType: 'Chess AI', playedAt: '2025-11-01 10:30', duration: '15m 32s', rounds: 50 },
    { id: 'past_2', player1: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 42 }, player2: { name: 'CodeNinja', agent: 'SwiftAI v3.0', score: 48 }, winner: 'CodeNinja', gameType: 'Strategy Game', playedAt: '2025-11-01 09:15', duration: '22m 18s', rounds: 100 },
    { id: 'past_3', player1: { name: 'MLEngineer', agent: 'TensorBot v1.0', score: 25 }, player2: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 28 }, winner: 'demo_user', gameType: 'RTS Battle', playedAt: '2025-10-31 18:45', duration: '18m 05s', rounds: 30 },
    { id: 'past_4', player1: { name: 'GameDev', agent: 'StrategyX v2.1', score: 38 }, player2: { name: 'demo_user', agent: 'AlphaBot v1.1', score: 35 }, winner: 'GameDev', gameType: 'Strategy Game', playedAt: '2025-10-31 14:20', duration: '25m 42s', rounds: 100 },
    { id: 'past_5', player1: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 48 }, player2: { name: 'Competitor', agent: 'AlgoMaster v1.0', score: 40 }, winner: 'demo_user', gameType: 'Chess AI', playedAt: '2025-10-30 16:00', duration: '12m 55s', rounds: 50 },
  ];

  const filteredGames = pastGames.filter((game) => {
    if (filter === 'all') return true;
    if (filter === 'wins') return game.winner === 'demo_user';
    if (filter === 'losses') return game.winner !== 'demo_user';
    return true;
  });

  const selectedGameData = pastGames.find(g => g.id === selectedGame);

  if (selectedGame && selectedGameData) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Button startIcon={<ArrowBack />} onClick={() => setSelectedGame(null)} sx={{ mb: 3 }}>Back to Past Games</Button>
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Box><Typography variant="h5">Game Replay</Typography><Typography color="text.secondary">{selectedGameData.gameType} - {selectedGameData.playedAt}</Typography></Box>
              <Box sx={{ textAlign: 'right' }}><Typography variant="h6" color="primary">Winner: {selectedGameData.winner}</Typography><Typography variant="body2">Duration: {selectedGameData.duration}</Typography></Box>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-around', my: 3 }}>
              <Box sx={{ textAlign: 'center' }}><Typography variant="h6">{selectedGameData.player1.name}</Typography><Typography variant="body2" color="text.secondary">{selectedGameData.player1.agent}</Typography><Typography variant="h4" color="primary" sx={{ mt: 1 }}>{selectedGameData.player1.score}</Typography></Box>
              <Typography variant="h5" color="text.secondary" sx={{ alignSelf: 'center' }}>VS</Typography>
              <Box sx={{ textAlign: 'center' }}><Typography variant="h6">{selectedGameData.player2.name}</Typography><Typography variant="body2" color="text.secondary">{selectedGameData.player2.agent}</Typography><Typography variant="h4" color="primary" sx={{ mt: 1 }}>{selectedGameData.player2.score}</Typography></Box>
            </Box>
          </CardContent>
        </Card>
        <Card sx={{ mb: 3, minHeight: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <CardContent sx={{ textAlign: 'center' }}>
            <Movie sx={{ fontSize: 64, mb: 2, color: 'primary.main' }} />
            <Typography variant="h4" gutterBottom>Game Replay</Typography>
            <Typography color="text.secondary">Use controls below to navigate through the game</Typography>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', mt: 3 }}>
              <Button variant="outlined" startIcon={<SkipPrevious />}>Previous</Button>
              <Button variant="contained" startIcon={<PlayArrow />}>Play</Button>
              <Button variant="outlined" startIcon={<SkipNext />}>Next</Button>
            </Box>
          </CardContent>
        </Card>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' }, gap: 2 }}>
          <Card><CardContent><Typography variant="body2" color="text.secondary">Total Rounds</Typography><Typography variant="h6">{selectedGameData.rounds}</Typography></CardContent></Card>
          <Card><CardContent><Typography variant="body2" color="text.secondary">Final Score</Typography><Typography variant="h6">{selectedGameData.player1.score} - {selectedGameData.player2.score}</Typography></CardContent></Card>
          <Card><CardContent><Typography variant="body2" color="text.secondary">Duration</Typography><Typography variant="h6">{selectedGameData.duration}</Typography></CardContent></Card>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <History sx={{ fontSize: 48 }} /> Past Games
        </Typography>
        <Typography color="text.secondary">Review and analyze previous matches</Typography>
      </Box>
      <Box sx={{ mb: 3, display: 'flex', gap: 1 }}>
        <Button
          onClick={() => setFilter('all')}
          sx={{
            borderRadius: 0,
            border: filter === 'all' ? 'none' : '1px solid #333',
            backgroundColor: filter === 'all' ? '#2a2a2a !important' : 'transparent',
            backgroundImage: 'none !important',
            color: filter === 'all' ? '#00A6FF !important' : '#ddd',
            '&:hover': {
              border: '1px solid #00A6FF',
              backgroundColor: '#2a2a2a !important',
              backgroundImage: 'none !important',
              color: '#00A6FF !important',
            },
          }}
        >
          All Games
        </Button>
        <Button
          onClick={() => setFilter('wins')}
          sx={{
            borderRadius: 0,
            border: filter === 'wins' ? 'none' : '1px solid #333',
            backgroundColor: filter === 'wins' ? '#2a2a2a !important' : 'transparent',
            backgroundImage: 'none !important',
            color: filter === 'wins' ? '#00A6FF !important' : '#ddd',
            '&:hover': {
              border: '1px solid #00A6FF',
              backgroundColor: '#2a2a2a !important',
              backgroundImage: 'none !important',
              color: '#00A6FF !important',
            },
          }}
        >
          My Wins
        </Button>
        <Button
          onClick={() => setFilter('losses')}
          sx={{
            borderRadius: 0,
            border: filter === 'losses' ? 'none' : '1px solid #333',
            backgroundColor: filter === 'losses' ? '#2a2a2a !important' : 'transparent',
            backgroundImage: 'none !important',
            color: filter === 'losses' ? '#00A6FF !important' : '#ddd',
            '&:hover': {
              border: '1px solid #00A6FF',
              backgroundColor: '#2a2a2a !important',
              backgroundImage: 'none !important',
              color: '#00A6FF !important',
            },
          }}
        >
          My Losses
        </Button>
      </Box>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow><TableCell>Date</TableCell><TableCell>Game Type</TableCell><TableCell>Player 1</TableCell><TableCell>Score</TableCell><TableCell>Player 2</TableCell><TableCell>Winner</TableCell><TableCell>Duration</TableCell><TableCell>Actions</TableCell></TableRow>
          </TableHead>
          <TableBody>
            {filteredGames.map((game) => (
              <TableRow key={game.id}>
                <TableCell>{game.playedAt}</TableCell>
                <TableCell><Chip label={game.gameType} size="small" sx={{ borderRadius: 0 }} /></TableCell>
                <TableCell><Typography fontWeight="bold">{game.player1.name}</Typography><Typography variant="caption" color="text.secondary">{game.player1.agent}</Typography></TableCell>
                <TableCell><Typography>{game.player1.score} - {game.player2.score}</Typography></TableCell>
                <TableCell><Typography fontWeight="bold">{game.player2.name}</Typography><Typography variant="caption" color="text.secondary">{game.player2.agent}</Typography></TableCell>
                <TableCell><Chip icon={game.winner === 'demo_user' ? <EmojiEvents /> : undefined} label={game.winner} color={game.winner === 'demo_user' ? 'success' : 'default'} size="small" sx={{ borderRadius: 0 }} /></TableCell>
                <TableCell>{game.duration}</TableCell>
                <TableCell><Button variant="outlined" size="small" onClick={() => setSelectedGame(game.id)}>Replay</Button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Container>
  );
}
