import { Link } from 'react-router-dom';
import { Box, Container, Typography, Button, Card, CardContent } from '@mui/material';
import { SmartToy, EmojiEvents, Analytics, Visibility } from '@mui/icons-material';
import { overlays } from '../theme';

export function Home() {
  return (
    <Box sx={{ minHeight: '100vh' }}>
      {/* Hero Section */}
      <Box
        sx={{
          textAlign: 'center',
          py: { xs: 8, md: 12 },
          px: 4,
          background: overlays.heroGradient,
          position: 'relative',
        }}
      >
        <Typography
          variant="h1"
          sx={{
            fontSize: { xs: '2.5rem', md: '3.5rem' },
            mb: 2,
            color: 'text.primary',
            fontWeight: 700,
            letterSpacing: '-0.03em',
          }}
        >
          AICA Game Platform
        </Typography>
        <Typography
          variant="h5"
          color="text.secondary"
          sx={{
            mb: 5,
            maxWidth: 560,
            mx: 'auto',
            fontWeight: 400,
            fontSize: { xs: '1rem', md: '1.125rem' },
            lineHeight: 1.6,
          }}
        >
          Build, train, and compete with intelligent AI agents
        </Typography>
        <Button
          component={Link}
          to="/login"
          variant="contained"
          size="large"
          sx={{
            px: 5,
            py: 1.75,
            fontSize: '1.125rem',
          }}
        >
          Get Started
        </Button>
      </Box>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ py: { xs: 6, md: 10 } }}>
        <Box sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
          gap: 3,
        }}>
          {[
            {
              icon: <SmartToy sx={{ fontSize: 40, color: 'primary.main' }} />,
              title: 'Build AI Agents',
              desc: 'Create and submit your AI agents using Python, JavaScript, or TypeScript',
            },
            {
              icon: <EmojiEvents sx={{ fontSize: 40, color: 'warning.main' }} />,
              title: 'Compete in Tournaments',
              desc: "Join tournaments and climb the leaderboard to prove your AI's superiority",
            },
            {
              icon: <Analytics sx={{ fontSize: 40, color: 'primary.main' }} />,
              title: 'Track Performance',
              desc: "Monitor your agent's stats, win rates, and rankings in real-time",
            },
            {
              icon: <Visibility sx={{ fontSize: 40, color: 'error.main' }} />,
              title: 'Watch Live Matches',
              desc: 'Spectate live matches and replay past matches to learn strategies',
            },
          ].map((feature, i) => (
            <Card
              key={i}
              sx={{
                textAlign: 'center',
                p: 1,
              }}
            >
              <CardContent>
                <Box sx={{ mb: 2 }}>{feature.icon}</Box>
                <Typography variant="h6" gutterBottom>
                  {feature.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {feature.desc}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Container>
    </Box>
  );
}
