import { Link } from 'react-router-dom';
import { Box, Container, Typography, Button, Card, CardContent } from '@mui/material';
import { SmartToy, EmojiEvents, Analytics, Visibility } from '@mui/icons-material';

export function Home() {
  return (
    <Box sx={{ minHeight: 'calc(100vh - 80px)' }}>
      {/* Hero Section */}
      <Box
        sx={{
          textAlign: 'center',
          py: 8,
          px: 4,
          background: 'linear-gradient(135deg, rgba(0, 217, 139, 0.1) 0%, rgba(0, 166, 255, 0.1) 100%)',
          borderRadius: 0,
          my: 4,
          mx: 'auto',
          maxWidth: 1200,
        }}
      >
        <Typography
          variant="h1"
          sx={{
            fontSize: { xs: '2.5rem', md: '4rem' },
            mb: 2,
            background: 'linear-gradient(90deg, #00D98B 0%, #00A6FF 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}
        >
          AICA Game Platform
        </Typography>
        <Typography variant="h5" color="text.secondary" sx={{ mb: 4 }}>
          Build, train, and compete with intelligent AI agents
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Button
            component={Link}
            to="/login"
            variant="gradientBorder"
            size="large"
            sx={{
              px: 6,
              py: 2,
              fontSize: '1.3rem',
              '&:hover': {
                transform: 'translateY(-2px)',
              },
              transition: 'transform 0.3s',
            }}
          >
            Get Started
          </Button>
        </Box>
      </Box>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ py: 8 }}>
        <Box sx={{ 
          display: 'grid', 
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
          gap: 4 
        }}>
          <Card
            sx={{
              height: '100%',
              textAlign: 'center',
              transition: 'transform 0.3s, box-shadow 0.3s',
              '&:hover': {
                transform: 'translateY(-8px)',
              },
            }}
          >
            <CardContent>
              <SmartToy sx={{ fontSize: 48, mb: 2, color: '#00A6FF' }} />
              <Typography variant="h6" gutterBottom>
                Build AI Agents
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Create and submit your AI agents using Python, JavaScript, or TypeScript
              </Typography>
            </CardContent>
          </Card>

          <Card
            sx={{
              height: '100%',
              textAlign: 'center',
              transition: 'transform 0.3s, box-shadow 0.3s',
              '&:hover': {
                transform: 'translateY(-8px)',
              },
            }}
          >
            <CardContent>
              <EmojiEvents sx={{ fontSize: 48, mb: 2, color: '#00D98B' }} />
              <Typography variant="h6" gutterBottom>
                Compete in Tournaments
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Join tournaments and climb the leaderboard to prove your AI's superiority
              </Typography>
            </CardContent>
          </Card>

          <Card
            sx={{
              height: '100%',
              textAlign: 'center',
              transition: 'transform 0.3s, box-shadow 0.3s',
              '&:hover': {
                transform: 'translateY(-8px)',
              },
            }}
          >
            <CardContent>
              <Analytics sx={{ fontSize: 48, mb: 2, color: '#00A6FF' }} />
              <Typography variant="h6" gutterBottom>
                Track Performance
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Monitor your agent's stats, win rates, and rankings in real-time
              </Typography>
            </CardContent>
          </Card>

          <Card
            sx={{
              height: '100%',
              textAlign: 'center',
              transition: 'transform 0.3s, box-shadow 0.3s',
              '&:hover': {
                transform: 'translateY(-8px)',
              },
            }}
          >
            <CardContent>
              <Visibility sx={{ fontSize: 48, mb: 2, color: '#e53935' }} />
              <Typography variant="h6" gutterBottom>
                Watch Live Games
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Spectate live matches and replay past games to learn strategies
              </Typography>
            </CardContent>
          </Card>
        </Box>
      </Container>
    </Box>
  );
}
