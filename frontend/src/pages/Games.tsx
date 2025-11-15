import { Link } from 'react-router-dom';
import { GAMES, getActiveGames } from '../config/games';
import { Box, Container, Typography, Button, Card, CardContent, Chip } from '@mui/material';
import { SportsEsports, Casino, Close, Circle, Album, PanoramaFishEye } from '@mui/icons-material';

const iconMap: Record<string, React.ReactNode> = {
  chess: '♟',
  tictactoe: (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontSize: 64 }}>
      <Close sx={{ fontSize: 'inherit' }} />
      <PanoramaFishEye sx={{ fontSize: 'inherit' }} />
    </Box>
  ),
  circle: <Circle sx={{ fontSize: 64 }} />,
  album: <Album sx={{ fontSize: 64 }} />,
  casino: <Casino sx={{ fontSize: 64 }} />,
};

export function Games() {
  const activeGames = getActiveGames();
  const inactiveGames = GAMES.filter(game => !game.active);

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return '#10b981';
      case 'medium': return '#f59e0b';
      case 'hard': return '#ef4444';
      default: return '#888';
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SportsEsports sx={{ fontSize: 36 }} /> Available Games
        </Typography>
        <Typography color="text.secondary">
          Choose a game to view details and start competing
        </Typography>
      </Box>      <Box sx={{ mb: 6 }}>
        <Typography variant="h5" gutterBottom>
          Active Games
        </Typography>
        <Box sx={{ 
          display: 'grid', 
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' },
          gap: 3 
        }}>
          {activeGames.map((game) => (
            <Card key={game.id} sx={{ 
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              transition: 'transform 0.3s',
              '&:hover': {
                transform: 'translateY(-8px)',
              }
            }}>
              <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ 
                  display: 'flex', 
                  justifyContent: 'center', 
                  alignItems: 'center',
                  mb: 2, 
                  fontSize: 64, 
                  color: '#00A6FF',
                  minHeight: 80
                }}>
                  {iconMap[game.icon] || game.icon}
                </Box>
                <Typography variant="h6" gutterBottom>
                  {game.name}
                </Typography>
                <Typography color="text.secondary" sx={{ mb: 2, flexGrow: 1 }}>
                  {game.description}
                </Typography>
                
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Players:</Typography>
                    <Typography variant="body2">
                      {game.minPlayers === game.maxPlayers 
                        ? game.maxPlayers 
                        : `${game.minPlayers}-${game.maxPlayers}`}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Category:</Typography>
                    <Typography variant="body2">{game.category}</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2" color="text.secondary">Difficulty:</Typography>
                    <Chip 
                      label={game.difficulty} 
                      size="small"
                      sx={{ 
                        backgroundColor: `${getDifficultyColor(game.difficulty)}22`, 
                        color: getDifficultyColor(game.difficulty),
                        borderRadius: 0
                      }}
                    />
                  </Box>
                </Box>

                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button 
                    component={Link} 
                    to={`/leaderboard?game=${game.id}`} 
                    variant="outlined"
                    size="small"
                    fullWidth
                  >
                    Leaderboard
                  </Button>
                  <Button 
                    component={Link} 
                    to={`/games/live?game=${game.id}`} 
                    variant="contained"
                    size="small"
                    fullWidth
                  >
                    Watch Live
                  </Button>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Box>

      {inactiveGames.length > 0 && (
        <Box>
          <Typography variant="h5" gutterBottom>
            Coming Soon
          </Typography>
          <Box sx={{ 
            display: 'grid', 
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' },
            gap: 3 
          }}>
            {inactiveGames.map((game) => (
              <Card key={game.id} sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                opacity: 0.6,
                position: 'relative'
              }}>
                <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                  <Box sx={{ 
                    display: 'flex', 
                    justifyContent: 'center', 
                    alignItems: 'center',
                    mb: 2, 
                    fontSize: 64, 
                    color: '#888',
                    minHeight: 80
                  }}>
                    {iconMap[game.icon] || game.icon}
                  </Box>
                  <Typography variant="h6" gutterBottom>
                    {game.name}
                  </Typography>
                  <Typography color="text.secondary" sx={{ mb: 2, flexGrow: 1 }}>
                    {game.description}
                  </Typography>
                  
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" color="text.secondary">Players:</Typography>
                      <Typography variant="body2">
                        {game.minPlayers === game.maxPlayers 
                          ? game.maxPlayers 
                          : `${game.minPlayers}-${game.maxPlayers}`}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" color="text.secondary">Category:</Typography>
                      <Typography variant="body2">{game.category}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" color="text.secondary">Difficulty:</Typography>
                      <Chip 
                        label={game.difficulty} 
                        size="small"
                        sx={{ 
                          backgroundColor: `${getDifficultyColor(game.difficulty)}22`, 
                          color: getDifficultyColor(game.difficulty),
                          borderRadius: 0
                        }}
                      />
                    </Box>
                  </Box>

                  <Chip 
                    label="Coming Soon" 
                    color="default"
                    sx={{ 
                      position: 'absolute',
                      top: 16,
                      right: 16,
                      borderRadius: 0
                    }}
                  />
                </CardContent>
              </Card>
            ))}
          </Box>
        </Box>
      )}
    </Container>
  );
}
