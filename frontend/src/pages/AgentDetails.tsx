import { useState, useEffect } from 'react';
import { Box, Container, Typography, Button, Card, CardContent, CircularProgress, Alert, Grid, Divider } from '@mui/material';
import { ArrowBack, EmojiEvents, Gamepad } from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { agentsApi, Agent } from '../services/api/agents';
import { getActiveGames } from '../config/games';

export function AgentDetails() {
    const navigate = useNavigate();
    const { id } = useParams<{ id: string }>();

    const [agent, setAgent] = useState<Agent | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!id) return;

        const fetchAgent = async () => {
            try {
                setLoading(true);
                const data = await agentsApi.getAgent(id);
                setAgent(data);
                setError(null);
            } catch (err: any) {
                console.error('Failed to fetch agent details:', err);
                setError('Failed to load agent details. Please try again.');
            } finally {
                setLoading(false);
            }
        };

        fetchAgent();
    }, [id]);

    if (loading) {
        return (
            <Container maxWidth="lg" sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
                <CircularProgress />
            </Container>
        );
    }

    if (error || !agent) {
        return (
            <Container maxWidth="lg" sx={{ py: 4 }}>
                <Button startIcon={<ArrowBack />} onClick={() => navigate('/dashboard')} sx={{ mb: 2 }}>
                    Back to Dashboard
                </Button>
                <Alert severity="error">{error || 'Agent not found'}</Alert>
            </Container>
        );
    }

    const { stats } = agent;
    const wins = stats?.wins || 0;
    const losses = stats?.losses || 0;
    const matchesPlayed = stats?.matches_played || (wins + losses);
    const winRate = matchesPlayed > 0 ? Math.round((wins / matchesPlayed) * 100) : 0;

    // Attempt to guess the game if stats has a game_id, otherwise fallback
    const games = getActiveGames();
    const gameId = stats?.game_id || 'chess';
    const game = games.find(g => g.id === gameId);

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Button startIcon={<ArrowBack />} onClick={() => navigate('/dashboard')} sx={{ mb: 2 }}>
                Back to Dashboard
            </Button>

            <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                    <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Gamepad fontSize="large" color="primary" />
                        Agent Details
                    </Typography>
                    <Typography color="text.secondary">
                        ID: {agent.id}
                    </Typography>
                </Box>
                <Button
                    variant="outlined"
                    onClick={() => navigate(`/submissions/${agent.active_submission_id}`)}
                >
                    View Source Submission
                </Button>
            </Box>

            <Grid container spacing={4}>
                <Grid item xs={12} md={8}>
                    <Card sx={{ height: '100%' }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>
                                Performance Overview
                            </Typography>
                            <Divider sx={{ mb: 3 }} />

                            <Box sx={{
                                display: 'grid',
                                gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' },
                                gap: 3,
                                textAlign: 'center',
                                mb: 4
                            }}>
                                <Box>
                                    <Typography variant="h3" color="primary">{matchesPlayed}</Typography>
                                    <Typography variant="body2" color="text.secondary">Matches Played</Typography>
                                </Box>
                                <Box>
                                    <Typography variant="h3" color="success.main">{winRate}%</Typography>
                                    <Typography variant="body2" color="text.secondary">Win Rate</Typography>
                                </Box>
                                <Box>
                                    <Typography variant="h3" color="warning.main">
                                        {stats?.rank ? `#${stats.rank}` : '-'}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">Current Rank</Typography>
                                </Box>
                            </Box>

                            <Box sx={{ display: 'flex', gap: 4, justifyContent: 'center', my: 2 }}>
                                <Box sx={{ textAlign: 'center' }}>
                                    <Typography variant="h4" color="success.main">{wins}</Typography>
                                    <Typography variant="body2" color="text.secondary">Wins</Typography>
                                </Box>
                                <Box sx={{ textAlign: 'center' }}>
                                    <Typography variant="h4" color="error.main">{losses}</Typography>
                                    <Typography variant="body2" color="text.secondary">Losses</Typography>
                                </Box>
                            </Box>

                        </CardContent>
                    </Card>
                </Grid>

                <Grid item xs={12} md={4}>
                    <Card sx={{ height: '100%' }}>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>
                                Info
                            </Typography>
                            <Divider sx={{ mb: 2 }} />

                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                <Box>
                                    <Typography variant="caption" color="text.secondary">Game</Typography>
                                    <Typography variant="body1">{game?.name || gameId}</Typography>
                                </Box>
                                <Box>
                                    <Typography variant="caption" color="text.secondary">Created</Typography>
                                    <Typography variant="body1">{new Date(agent.created_at).toLocaleString()}</Typography>
                                </Box>
                                <Box>
                                    <Typography variant="caption" color="text.secondary">Last Updated</Typography>
                                    <Typography variant="body1">{new Date(agent.updated_at).toLocaleString()}</Typography>
                                </Box>
                                <Box>
                                    <Typography variant="caption" color="text.secondary">Status</Typography>
                                    <Typography variant="body1" color="success.main" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                        <EmojiEvents fontSize="small" /> Active
                                    </Typography>
                                </Box>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>
        </Container>
    );
}
