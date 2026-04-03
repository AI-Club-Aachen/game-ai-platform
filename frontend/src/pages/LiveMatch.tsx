import { useParams } from 'react-router-dom';
import { Box, Container, Typography, Card, CardContent, Button, Chip } from '@mui/material';
import { Visibility, ArrowBack, Videocam } from '@mui/icons-material';
import { useSmartBack } from '../hooks/use-smart-back';

export function LiveMatch() {
  const { matchId } = useParams<{ matchId: string }>();
  const goBack = useSmartBack('/games/matches');

  // Stub data depending on matchId
  const selectedMatchData = {
    id: matchId || 'match_1',
    player1: { name: 'AImaster', agent: 'GammaNet v1.5', score: 45 },
    player2: { name: 'BotBuilder', agent: 'DeepMind v2.0', score: 42 },
    gameType: 'Chess AI',
    startedAt: '10 min ago',
    viewers: 127,
    round: 15,
    maxRounds: 50,
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 3 }} variant="text">
        Back to Matches
      </Button>
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 4, flexGrow: 1 }}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h6">{selectedMatchData.player1.name}</Typography>
                <Typography variant="body2" color="text.secondary">{selectedMatchData.player1.agent}</Typography>
                <Typography variant="h4" color="primary" sx={{ mt: 1 }}>{selectedMatchData.player1.score}</Typography>
              </Box>
              <Typography variant="h5" color="text.secondary">VS</Typography>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h6">{selectedMatchData.player2.name}</Typography>
                <Typography variant="body2" color="text.secondary">{selectedMatchData.player2.agent}</Typography>
                <Typography variant="h4" color="primary" sx={{ mt: 1 }}>{selectedMatchData.player2.score}</Typography>
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>
      <Card sx={{ mb: 3, minHeight: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <CardContent sx={{ textAlign: 'center' }}>
          <Videocam sx={{ fontSize: 56, mb: 2, color: 'primary.main' }} />
          <Typography variant="h4" gutterBottom>Match Visualization</Typography>
          <Typography variant="h6" color="text.secondary" gutterBottom>Round {selectedMatchData.round} of {selectedMatchData.maxRounds}</Typography>
          <Chip label="LIVE" color="error" sx={{ mt: 2 }} />
        </CardContent>
      </Card>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' }, gap: 3 }}>
        <Card><CardContent><Typography variant="body2" color="text.secondary">Game</Typography><Typography variant="h6">{selectedMatchData.gameType}</Typography></CardContent></Card>
        <Card><CardContent><Typography variant="body2" color="text.secondary">Started</Typography><Typography variant="h6">{selectedMatchData.startedAt}</Typography></CardContent></Card>
        <Card><CardContent><Typography variant="body2" color="text.secondary">Viewers</Typography><Typography variant="h6"><Visibility sx={{ fontSize: 18, mr: 0.5, verticalAlign: 'middle' }} />{selectedMatchData.viewers}</Typography></CardContent></Card>
      </Box>
    </Container>
  );
}
