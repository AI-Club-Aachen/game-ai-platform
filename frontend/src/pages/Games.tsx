import { Link } from 'react-router-dom';
import { GAMES, getActiveGames } from '../config/games';
import { Box, Container, Typography, Card, CardContent, Chip } from '@mui/material';
import { SportsEsports, Casino, Close, Circle, Album, PanoramaFishEye } from '@mui/icons-material';
import { palette } from '../theme';

const iconMap: Record<string, React.ReactNode> = {
  chess: '♟',
  tictactoe: (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, fontSize: 56 }}>
      <Close sx={{ fontSize: 'inherit' }} />
      <PanoramaFishEye sx={{ fontSize: 'inherit' }} />
    </Box>
  ),
  circle: <Circle sx={{ fontSize: 56 }} />,
  album: <Album sx={{ fontSize: 56 }} />,
  casino: <Casino sx={{ fontSize: 56 }} />,
};

export function Games() {
  const activeGames = getActiveGames();
  const inactiveGames = GAMES.filter(game => !game.active);

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return palette.success;
      case 'medium': return palette.warning;
      case 'hard': return palette.error;
      default: return palette.textMuted;
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SportsEsports sx={{ fontSize: 32 }} /> Available Games
        </Typography>
        <Typography color="text.secondary">
          Click a game to view details, matches, leaderboard and manage your agents
        </Typography>
      </Box>

      <Box sx={{ mb: 6 }}>
        <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
          Active Games
        </Typography>
        <Box sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' },
          gap: 3,
        }}>
          {activeGames.map((game) => (
            <Card
              key={game.id}
              component={Link}
              to={`/games/${game.id}`}
              sx={{
                display: 'flex',
                flexDirection: 'column',
                textDecoration: 'none',
                cursor: 'pointer',
                '&:hover': {
                  borderColor: palette.primary,
                  transform: 'translateY(-2px)',
                },
                transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
              }}
            >
              <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <Box sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  mb: 2,
                  fontSize: 56,
                  color: 'primary.main',
                  minHeight: 72,
                }}>
                  {iconMap[game.icon] || game.icon}
                </Box>
                <Typography variant="h6" gutterBottom>
                  {game.name}
                </Typography>
                <Typography color="text.secondary" sx={{ mb: 2, flexGrow: 1, fontSize: '0.8125rem' }}>
                  {game.description}
                </Typography>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
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
                        backgroundColor: `${getDifficultyColor(game.difficulty)}18`,
                        color: getDifficultyColor(game.difficulty),
                      }}
                    />
                  </Box>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Box>

      {inactiveGames.length > 0 && (
        <Box>
          <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
            Coming Soon
          </Typography>
          <Box sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' },
            gap: 3,
          }}>
            {inactiveGames.map((game) => (
              <Card key={game.id} sx={{
                display: 'flex',
                flexDirection: 'column',
                opacity: 0.5,
                position: 'relative',
                '&:hover': {
                  borderColor: 'divider',
                  boxShadow: 'none',
                },
              }}>
                <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                  <Box sx={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    mb: 2,
                    fontSize: 56,
                    color: 'text.secondary',
                    minHeight: 72,
                  }}>
                    {iconMap[game.icon] || game.icon}
                  </Box>
                  <Typography variant="h6" gutterBottom>
                    {game.name}
                  </Typography>
                  <Typography color="text.secondary" sx={{ mb: 2, flexGrow: 1, fontSize: '0.8125rem' }}>
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
                          backgroundColor: `${getDifficultyColor(game.difficulty)}18`,
                          color: getDifficultyColor(game.difficulty),
                        }}
                      />
                    </Box>
                  </Box>

                  <Chip
                    label="Coming Soon"
                    size="small"
                    sx={{
                      position: 'absolute',
                      top: 16,
                      right: 16,
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
