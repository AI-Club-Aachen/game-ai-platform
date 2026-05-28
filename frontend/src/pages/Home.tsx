import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import { Box, Container, Typography, Button, Card, CardContent, Chip } from '@mui/material';
import {
  Analytics,
  ArrowForward,
  Code,
  EmojiEvents,
  PlayCircle,
  RocketLaunch,
  Shield,
} from '@mui/icons-material';
import { getActiveGames } from '../config/games';
import { overlays } from '../theme';
import { legalLinks } from './LegalPages';

interface Feature {
  icon: ReactNode;
  title: string;
  desc: string;
}

const features: Feature[] = [
  {
    icon: <Code />,
    title: 'Ship agents, not setup scripts',
    desc: 'Upload your bot and let the platform build it. Focus on strategy, not infrastructure.',
  },
  {
    icon: <PlayCircle />,
    title: 'Watch matches unfold live',
    desc: 'Spectate games in real time, inspect replays, and turn every loss into insight.',
  },
  {
    icon: <Analytics />,
    title: 'Read the meta at a glance',
    desc: 'Track Elo, win rates, and match history — strong ideas rise above lucky streaks.',
  },
  {
    icon: <Shield />,
    title: 'Compete in a fair arena',
    desc: 'Containerized submissions keep games reproducible, isolated, and ready for events.',
  },
];

const workflow = [
  { step: '01', title: 'Pick a game', text: 'Browse the active arenas and choose your challenge.' },
  { step: '02', title: 'Upload your agent', text: 'Submit your code — the build pipeline handles the rest.' },
  { step: '03', title: 'Climb the ladder', text: 'Run matches, study replays, and fight for leaderboard spots.' },
];

export function Home() {
  const activeGames = getActiveGames();

  return (
    <Box
      sx={{
        minHeight: '100vh',
        overflow: 'hidden',
        background:
          'radial-gradient(ellipse at 50% 0%, rgba(59, 130, 246, 0.14) 0%, transparent 60%), linear-gradient(180deg, var(--color-bg-base) 0%, #070A12 50%, var(--color-bg-base) 100%)',
        '& .MuiTypography-h2': {
          fontSize: { xs: '2.15rem', md: '2.35rem' },
        },
        '& .MuiTypography-h5': {
          fontSize: '1.3rem',
        },
        '& .MuiTypography-h6': {
          fontSize: '1.12rem',
        },
        '& .MuiTypography-body1': {
          fontSize: '1.08rem',
        },
        '& .MuiTypography-body2': {
          fontSize: '0.95rem',
        },
        '& .MuiTypography-caption': {
          fontSize: '0.86rem',
        },
        '& .MuiTypography-overline': {
          fontSize: '0.86rem',
        },
        '& .MuiButton-root': {
          fontSize: '1rem',
        },
        '& .MuiButton-sizeLarge': {
          fontSize: '1.12rem',
        },
        '& .MuiChip-sizeSmall': {
          height: 30,
        },
        '& .MuiChip-label': {
          fontSize: '0.9rem',
        },
      }}
    >
      {/* ─── Header ─────────────────────────────────────────────────── */}
      <Box
        component="header"
        sx={{
          borderBottom: '1px solid',
          borderColor: 'divider',
          backgroundColor: 'rgba(9, 9, 11, 0.72)',
          backdropFilter: 'blur(18px)',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <Container
          maxWidth="lg"
          sx={{
            minHeight: 82,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 2,
          }}
        >
          <Box component={Link} to="/" sx={{ display: 'flex', alignItems: 'center', gap: 1.25, color: 'text.primary', textDecoration: 'none' }}>
            <Box
              sx={{
                width: 44,
                height: 44,
                borderRadius: '14px',
                display: 'grid',
                placeItems: 'center',
                overflow: 'hidden',
                backgroundColor: 'rgba(255, 255, 255, 0.06)',
                boxShadow: '0 12px 32px rgba(59, 130, 246, 0.2)',
              }}
            >
              <Box
                component="img"
                src="/favicon.svg"
                alt="AI Club Aachen logo"
                sx={{ width: 34, height: 34, display: 'block' }}
              />
            </Box>
            <Box>
              <Typography variant="h6" sx={{ fontSize: '1.25rem', lineHeight: 1.12 }}>
                Game AI Platform
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.9rem' }}>
                by AI Club Aachen e.V.
              </Typography>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Button component={Link} to="/login" variant="text" sx={{ fontSize: '1.02rem' }}>
              Sign in
            </Button>
            <Button component={Link} to="/register" variant="contained" sx={{ display: { xs: 'none', sm: 'inline-flex' }, fontSize: '1.02rem' }}>
              Join arena
            </Button>
          </Box>
        </Container>
      </Box>

      {/* ─── Main Content ───────────────────────────────────────────── */}
      <Box
        component="main"
        sx={{
          position: 'relative',
          '&::before': {
            content: '""',
            position: 'absolute',
            inset: 0,
            pointerEvents: 'none',
            opacity: 0.28,
            backgroundImage:
              'linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)',
            backgroundSize: '72px 72px',
            maskImage: 'linear-gradient(to bottom, black, transparent 60%)',
          },
        }}
      >
        {/* ─── Hero ───────────────────────────────────────────────── */}
        <Container
          maxWidth="lg"
          sx={{
            position: 'relative',
            pt: { xs: 10, md: 16 },
            pb: { xs: 8, md: 12 },
            textAlign: 'center',
          }}
        >
          <Chip
            label="Open-source competitive AI platform"
            size="small"
            sx={{
              mb: 3,
              px: 1,
              border: '1px solid rgba(96, 165, 250, 0.2)',
              backgroundColor: 'rgba(59, 130, 246, 0.08)',
              color: 'primary.light',
              fontWeight: 500,
            }}
          />

          <Typography
            variant="h1"
            sx={{
              maxWidth: 820,
              mx: 'auto',
              py: 0.5,
              fontSize: { xs: '3.1rem', sm: '4.45rem', md: '5.55rem' },
              lineHeight: { xs: 1.16, md: 1.12 },
              letterSpacing: '-0.06em',
              fontWeight: 800,
              background: 'linear-gradient(135deg, var(--color-text-primary) 40%, var(--color-primary) 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Build agents. Compete. Prove your strategy.
          </Typography>

          <Typography
            color="text.secondary"
            sx={{
              mt: 3,
              mx: 'auto',
              maxWidth: 640,
              fontSize: { xs: '1.12rem', md: '1.32rem' },
              lineHeight: 1.7,
            }}
          >
            Submit AI agents, battle across classic games, watch decisions
            play out live, and climb a leaderboard that rewards smarter play.
          </Typography>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, mt: 5, justifyContent: 'center' }}>
            <Button
              component={Link}
              to="/register"
              variant="contained"
              size="large"
              endIcon={<ArrowForward />}
              sx={{
                px: 4,
              }}
            >
              Create your agent
            </Button>
            <Button
              component={Link}
              to="/login"
              variant="outlined"
              size="large"
              sx={{
                px: 4,
                borderColor: 'rgba(255,255,255,0.12)',
                color: 'text.secondary',
                '&:hover': {
                  borderColor: 'rgba(255,255,255,0.24)',
                  backgroundColor: 'rgba(255,255,255,0.04)',
                  color: 'text.primary',
                },
              }}
            >
              Enter platform
            </Button>
          </Box>

          {/* Stat pills */}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              flexWrap: 'wrap',
              gap: { xs: 1.5, sm: 2.5 },
              mt: 5,
            }}
          >
            {[
              [`${activeGames.length} active games`, undefined],
              ['Live match viewer', undefined],
              ['Elo ranked ladder', undefined],
            ].map(([label]) => (
              <Box
                key={label}
                sx={{
                  px: 2,
                  py: 0.75,
                  borderRadius: '999px',
                  border: '1px solid rgba(255,255,255,0.08)',
                  backgroundColor: 'rgba(255,255,255,0.03)',
                }}
              >
                <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', letterSpacing: '0.02em' }}>
                  {label}
                </Typography>
              </Box>
            ))}
          </Box>
        </Container>

        {/* ─── Games ──────────────────────────────────────────────── */}
        <Container id="games" maxWidth="lg" sx={{ py: { xs: 5, md: 8 } }}>
          <Box sx={{ textAlign: 'center', mb: 5 }}>
            <Typography variant="overline" color="primary.light" sx={{ fontWeight: 800, letterSpacing: '0.16em' }}>
              Active Arenas
            </Typography>
            <Typography variant="h2" sx={{ mt: 0.5, maxWidth: 480, mx: 'auto' }}>
              Choose your battleground.
            </Typography>
          </Box>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: `repeat(${Math.min(activeGames.length, 3)}, 1fr)` },
              gap: 2.5,
            }}
          >
            {activeGames.map((game) => (
              <Card
                key={game.id}
                sx={{
                  position: 'relative',
                  overflow: 'hidden',
                  background:
                    'linear-gradient(160deg, rgba(24,27,37,0.94), rgba(15,17,23,0.96))',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    inset: 0,
                    borderRadius: 'inherit',
                    padding: '1px',
                    background: 'linear-gradient(135deg, rgba(59,130,246,0.25), rgba(96,165,250,0.1), transparent)',
                    mask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
                    maskComposite: 'exclude',
                    WebkitMaskComposite: 'xor',
                    pointerEvents: 'none',
                    opacity: 0,
                    transition: 'opacity 0.3s ease',
                  },
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    '&::before': { opacity: 1 },
                  },
                }}
              >
                <CardContent sx={{ display: 'flex', flexDirection: 'column', minHeight: 220 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 3 }}>
                    <Box
                      sx={{
                        width: 56,
                        height: 56,
                        borderRadius: '18px',
                        display: 'grid',
                        placeItems: 'center',
                        fontSize: 32,
                        backgroundColor: overlays.primaryGlow,
                        color: 'primary.light',
                      }}
                    >
                      {game.icon === 'chess' ? '♟' : game.icon === 'tictactoe' ? 'XO' : '●'}
                    </Box>
                    <Chip label={game.difficulty} size="small" />
                  </Box>
                  <Typography variant="h5" sx={{ mb: 1 }}>{game.name}</Typography>
                  <Typography color="text.secondary" sx={{ mb: 3, flexGrow: 1, fontSize: '1rem', lineHeight: 1.6 }}>
                    {game.description}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Chip label={`${game.minPlayers}–${game.maxPlayers} players`} size="small" variant="outlined" />
                    <Chip label={game.category} size="small" variant="outlined" />
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>

          <Box sx={{ textAlign: 'center', mt: 4 }}>
            <Button component={Link} to="/register" variant="outlined" endIcon={<RocketLaunch />}>
              Submit an agent
            </Button>
          </Box>
        </Container>

        {/* ─── Workflow ───────────────────────────────────────────── */}
        <Container id="workflow" maxWidth="lg" sx={{ py: { xs: 5, md: 8 } }}>
          <Box sx={{ textAlign: 'center', mb: 5 }}>
            <Typography variant="overline" color="primary.light" sx={{ fontWeight: 800, letterSpacing: '0.16em' }}>
              How It Works
            </Typography>
            <Typography variant="h2" sx={{ mt: 0.5, maxWidth: 520, mx: 'auto' }}>
              From idea to arena in three moves.
            </Typography>
          </Box>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' },
              gap: { xs: 2, md: 3 },
              position: 'relative',
            }}
          >
            {/* Connecting line on desktop */}
            <Box
              sx={{
                display: { xs: 'none', md: 'block' },
                position: 'absolute',
                top: 32,
                left: 'calc(16.67% + 20px)',
                right: 'calc(16.67% + 20px)',
                height: '1px',
                background: 'rgba(59, 130, 246, 0.2)',
                pointerEvents: 'none',
              }}
            />

            {workflow.map((item) => (
              <Box
                key={item.step}
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: { xs: 'flex-start', md: 'center' },
                  textAlign: { xs: 'left', md: 'center' },
                }}
              >
                <Box
                  sx={{
                    width: 48,
                    height: 48,
                    borderRadius: '50%',
                    display: 'grid',
                    placeItems: 'center',
                    mb: 2,
                    fontSize: '1rem',
                    fontWeight: 800,
                    color: 'primary.light',
                    border: '2px solid',
                    borderColor: 'rgba(59, 130, 246, 0.3)',
                    backgroundColor: 'rgba(59, 130, 246, 0.08)',
                    position: 'relative',
                    zIndex: 1,
                  }}
                >
                  {item.step}
                </Box>
                <Typography variant="h6" sx={{ mb: 0.75 }}>{item.title}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 280 }}>
                  {item.text}
                </Typography>
              </Box>
            ))}
          </Box>
        </Container>

        {/* ─── Features ───────────────────────────────────────────── */}
        <Container id="features" maxWidth="lg" sx={{ py: { xs: 5, md: 8 } }}>
          <Box sx={{ textAlign: 'center', maxWidth: 560, mx: 'auto', mb: 5 }}>
            <Typography variant="overline" color="primary.light" sx={{ fontWeight: 800, letterSpacing: '0.16em' }}>
              Platform
            </Typography>
            <Typography variant="h2" sx={{ mt: 0.5 }}>
              Built for competitive AI.
            </Typography>
          </Box>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
              gap: 2.5,
            }}
          >
            {features.map((feature) => (
              <Card
                key={feature.title}
                sx={{
                  height: '100%',
                  position: 'relative',
                  overflow: 'hidden',
                  backgroundColor: 'rgba(15,17,23,0.76)',
                  '&::before': {
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: '2px',
                    background: 'var(--color-primary)',
                    opacity: 0,
                    transition: 'opacity 0.3s ease',
                  },
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    borderColor: 'rgba(59, 130, 246, 0.3)',
                    '&::before': { opacity: 1 },
                  },
                }}
              >
                <CardContent>
                  <Box
                    sx={{
                      width: 44,
                      height: 44,
                      borderRadius: '14px',
                      display: 'grid',
                      placeItems: 'center',
                      mb: 2.5,
                      color: 'primary.light',
                      backgroundColor: 'rgba(59, 130, 246, 0.08)',
                    }}
                  >
                    {feature.icon}
                  </Box>
                  <Typography variant="h6" gutterBottom sx={{ fontSize: '1.12rem' }}>
                    {feature.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.65 }}>
                    {feature.desc}
                  </Typography>
                </CardContent>
              </Card>
            ))}
          </Box>
        </Container>

        {/* ─── CTA ────────────────────────────────────────────────── */}
        <Container maxWidth="lg" sx={{ pt: { xs: 5, md: 8 }, pb: { xs: 7, md: 11 } }}>
          <Box
            sx={{
              py: { xs: 5, md: 7 },
              px: { xs: 3, md: 6 },
              borderRadius: 3,
              textAlign: 'center',
              position: 'relative',
              overflow: 'hidden',
              background:
                'radial-gradient(ellipse at 50% 0%, rgba(59, 130, 246, 0.1), transparent 70%), linear-gradient(180deg, rgba(24,27,37,0.94), rgba(15,17,23,0.98))',
              border: '1px solid rgba(96, 165, 250, 0.15)',
            }}
          >
            <Typography variant="h2" sx={{ maxWidth: 560, mx: 'auto' }}>
              Ready to give your agent a worthy opponent?
            </Typography>
            <Typography color="text.secondary" sx={{ mt: 2, mb: 4, maxWidth: 480, mx: 'auto' }}>
              Join the arena, submit your first bot, and let the leaderboard
              tell you what to improve next.
            </Typography>
            <Button
              component={Link}
              to="/register"
              variant="contained"
              size="large"
              endIcon={<EmojiEvents />}
              sx={{
                px: 4,
              }}
            >
              Start competing
            </Button>
          </Box>
        </Container>
      </Box>

      {/* ─── Footer ───────────────────────────────────────────────── */}
      <Box
        component="footer"
        sx={{
          borderTop: '1px solid',
          borderColor: 'divider',
          py: 3,
          px: 3,
        }}
      >
        <Container
          maxWidth="lg"
          sx={{
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            alignItems: { xs: 'flex-start', sm: 'center' },
            justifyContent: 'space-between',
            gap: 2,
          }}
        >
          <Typography variant="body2" color="text.secondary">
            © {new Date().getFullYear()} AI Club Aachen e.V.
          </Typography>
          <Box
            component="nav"
            aria-label="Legal"
            sx={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: { xs: 1.5, sm: 2.5 },
            }}
          >
            {legalLinks.map((link) => (
              <Typography
                key={link.to}
                component={Link}
                to={link.to}
                variant="body2"
                color="text.secondary"
                sx={{
                  '&:hover': { color: 'primary.main' },
                }}
              >
                {link.label}
              </Typography>
            ))}
          </Box>
        </Container>
      </Box>
    </Box>
  );
}
