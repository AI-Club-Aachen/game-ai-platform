import { useNavigate } from 'react-router-dom';
import { Box, Container, Typography, Card, CardContent, Button, Chip, LinearProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import { Visibility, ArrowBack, PlayCircle, Videocam, History, EmojiEvents, PlayArrow } from '@mui/icons-material';
import { palette } from '../theme';
import { useSmartBack } from '../hooks/use-smart-back';

interface LiveMatch {
  id: string;
  player1: { name: string; agent: string; score: number };
  player2: { name: string; agent: string; score: number };
  gameType: string;
  startedAt: string;
  viewers: number;
  round: number;
  maxRounds: number;
}

interface PastMatch {
  id: string;
  player1: { name: string; agent: string; score: number };
  player2: { name: string; agent: string; score: number };
  winner: string;
  gameType: string;
  playedAt: string;
  duration: string;
  rounds: number;
}

export function Matches() {
  const navigate = useNavigate();
  const goBack = useSmartBack('/games');

  const liveMatches: LiveMatch[] = [
    {
      id: 'match_1',
      player1: { name: 'AImaster', agent: 'GammaNet v1.5', score: 45 },
      player2: { name: 'BotBuilder', agent: 'DeepMind v2.0', score: 42 },
      gameType: 'Chess AI',
      startedAt: '10 min ago',
      viewers: 127,
      round: 15,
      maxRounds: 50,
    },
    {
      id: 'match_2',
      player1: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 38 },
      player2: { name: 'CodeNinja', agent: 'SwiftAI v3.0', score: 35 },
      gameType: 'Strategy Game',
      startedAt: '5 min ago',
      viewers: 89,
      round: 22,
      maxRounds: 100,
    },
    {
      id: 'match_3',
      player1: { name: 'MLEngineer', agent: 'TensorBot v1.0', score: 15 },
      player2: { name: 'GameDev', agent: 'StrategyX v2.1', score: 18 },
      gameType: 'RTS Battle',
      startedAt: '2 min ago',
      viewers: 52,
      round: 8,
      maxRounds: 30,
    },
  ];

  const pastMatches: PastMatch[] = [
    { id: 'past_1', player1: { name: 'AImaster', agent: 'GammaNet v1.5', score: 50 }, player2: { name: 'BotBuilder', agent: 'DeepMind v2.0', score: 45 }, winner: 'AImaster', gameType: 'Chess AI', playedAt: '2025-11-01 10:30', duration: '15m 32s', rounds: 50 },
    { id: 'past_2', player1: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 42 }, player2: { name: 'CodeNinja', agent: 'SwiftAI v3.0', score: 48 }, winner: 'CodeNinja', gameType: 'Strategy Game', playedAt: '2025-11-01 09:15', duration: '22m 18s', rounds: 100 },
    { id: 'past_3', player1: { name: 'MLEngineer', agent: 'TensorBot v1.0', score: 25 }, player2: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 28 }, winner: 'demo_user', gameType: 'RTS Battle', playedAt: '2025-10-31 18:45', duration: '18m 05s', rounds: 30 },
    { id: 'past_4', player1: { name: 'GameDev', agent: 'StrategyX v2.1', score: 38 }, player2: { name: 'demo_user', agent: 'AlphaBot v1.1', score: 35 }, winner: 'GameDev', gameType: 'Strategy Game', playedAt: '2025-10-31 14:20', duration: '25m 42s', rounds: 100 },
    { id: 'past_5', player1: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 48 }, player2: { name: 'Competitor', agent: 'AlgoMaster v1.0', score: 40 }, winner: 'demo_user', gameType: 'Chess AI', playedAt: '2025-10-30 16:00', duration: '12m 55s', rounds: 50 },
  ];

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 2 }}>
        Back
      </Button>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PlayCircle sx={{ fontSize: 32 }} /> Matches
        </Typography>
        <Typography color="text.secondary">Watch live matches or review past matches</Typography>
      </Box>

      {/* Live Matches Section */}
      <Box sx={{ mb: 6 }}>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Videocam sx={{ fontSize: 24 }} /> Live Matches
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: palette.error,
              animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
              '@keyframes pulse': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.5 } },
            }} />
            <Typography variant="body2" color="text.secondary">{liveMatches.length} matches currently in progress</Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }, gap: 3 }}>
          {liveMatches.map((match) => (
            <Card key={match.id}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                  <Chip label={match.gameType} size="small" />
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'text.secondary' }}>
                    <Visibility sx={{ fontSize: 16 }} />
                    <Typography variant="body2">{match.viewers}</Typography>
                  </Box>
                </Box>
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Box>
                      <Typography variant="body2" fontWeight={600}>{match.player1.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{match.player1.agent}</Typography>
                    </Box>
                    <Typography variant="h5" color="primary">{match.player1.score}</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', my: 0.5 }}>VS</Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box>
                      <Typography variant="body2" fontWeight={600}>{match.player2.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{match.player2.agent}</Typography>
                    </Box>
                    <Typography variant="h5" color="primary">{match.player2.score}</Typography>
                  </Box>
                </Box>
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="caption">Round {match.round} / {match.maxRounds}</Typography>
                    <Typography variant="caption">{match.startedAt}</Typography>
                  </Box>
                  <LinearProgress variant="determinate" value={(match.round / match.maxRounds) * 100} sx={{ height: 4 }} />
                </Box>
                <Button variant="outlined" fullWidth onClick={() => navigate('/games/live/' + match.id)}>Watch Match</Button>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Box>

      {/* Past Matches Section */}
      <Box>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <History sx={{ fontSize: 24 }} /> Past Matches
          </Typography>
          <Typography variant="body2" color="text.secondary">Review and analyze previous matches</Typography>
        </Box>
        <Card>
          <TableContainer>
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
                {pastMatches.map((match) => (
                  <TableRow key={match.id}>
                    <TableCell>
                      <Box>
                        <Typography variant="body2" fontWeight={600}>{match.player1.name}</Typography>
                        <Typography variant="caption" color="text.secondary">{match.player1.agent}</Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary" sx={{ my: 0.5 }}>vs</Typography>
                      <Box>
                        <Typography variant="body2" fontWeight={600}>{match.player2.name}</Typography>
                        <Typography variant="caption" color="text.secondary">{match.player2.agent}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip label={match.gameType} size="small" />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <EmojiEvents sx={{ fontSize: 16, color: 'warning.main' }} />
                        <Typography>{match.winner}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography>{match.player1.score} - {match.player2.score}</Typography>
                    </TableCell>
                    <TableCell>{match.duration}</TableCell>
                    <TableCell>{match.playedAt}</TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        startIcon={<PlayArrow />}
                        variant="outlined"
                        onClick={() => navigate('/games/live/' + match.id)}
                      >
                        Replay
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      </Box>
    </Container>
  );
}
