import { useState, useEffect } from 'react';
import { Box, Container, Typography, Button, Card, CardContent, CircularProgress, Alert, Grid, Divider, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip } from '@mui/material';
import { ArrowBack, EmojiEvents, Gamepad } from '@mui/icons-material';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useSmartBack } from '../hooks/use-smart-back';
import { agentsApi, Agent } from '../services/api/agents';
import { getActiveGames } from '../config/games';
import { submissionsApi, Submission } from '../services/api/submissions';
import { useAuth } from '../context/AuthContext';
import { overlays } from '../theme';

export function AgentDetails() {
    const navigate = useNavigate();
    const goBack = useSmartBack('/dashboard');
    const { id } = useParams<{ id: string }>();
    const { isAdmin } = useAuth();

    const [agent, setAgent] = useState<Agent | null>(null);
    const [submissions, setSubmissions] = useState<Submission[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!id) return;

        const fetchData = async () => {
            try {
                setLoading(true);
                const [agentData, submissionsData] = await Promise.all([
                    agentsApi.getAgent(id),
                    submissionsApi.getSubmissions(0, 100)
                ]);
                setAgent(agentData);
                setSubmissions(
                    agentData.active_submission_id
                        ? submissionsData.filter(sub => sub.id === agentData.active_submission_id)
                        : []
                );
                setError(null);
            } catch (err: any) {
                console.error('Failed to fetch details:', err);
                setError('Failed to load agent details. Please try again.');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [id]);

    const getStatusColor = (status?: string) => {
        switch (status) {
            case 'completed': return 'success';
            case 'running': return 'info';
            case 'queued': return 'warning';
            case 'failed': return 'error';
            default: return 'default';
        }
    };

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
                <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 2 }}>
                    Back
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
    const gameId = agent.game_type || stats?.game_id || 'chess';
    const game = games.find(g => g.id === gameId);

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 2 }}>
                Back
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
                {agent.active_submission_id && (
                    <Button
                        variant="outlined"
                        onClick={() => navigate(`/submissions/${agent.active_submission_id}`)}
                    >
                        View Source Submission
                    </Button>
                )}
            </Box>

            <Grid container spacing={4} sx={{ mb: 4 }}>
                <Grid size={{ xs: 12, md: 7 }}>
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

                <Grid size={{ xs: 12, md: 5 }}>
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
                <Grid size={12}>
                    <Card>
                        <CardContent>
                            <Typography variant="h6" sx={{ mb: 3 }}>Agent Submissions</Typography>
                            <TableContainer>
                                <Table>
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>Submission ID</TableCell>
                                            <TableCell>Status</TableCell>
                                            <TableCell>Submitted</TableCell>
                                            {isAdmin && <TableCell>Actions</TableCell>}
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {submissions.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={isAdmin ? 4 : 3} align="center">
                                                    <Typography color="text.secondary">No submissions found for this agent</Typography>
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            submissions.map(sub => {
                                                const status = sub.build_jobs && sub.build_jobs.length > 0
                                                    ? sub.build_jobs[0].status
                                                    : 'unknown';

                                                return (
                                                    <TableRow key={sub.id}>
                                                        <TableCell>
                                                            <Typography component="code" sx={{ fontSize: '0.8125rem', backgroundColor: overlays.overlayLight, px: 1, py: 0.5, borderRadius: 1 }}>
                                                                {sub.id.substring(0, 8)}
                                                            </Typography>
                                                        </TableCell>
                                                        <TableCell>
                                                            <Chip label={status} color={getStatusColor(status) as any} size="small" />
                                                        </TableCell>
                                                        <TableCell>{new Date(sub.created_at).toLocaleString()}</TableCell>
                                                        {isAdmin && (
                                                            <TableCell>
                                                                <Button component={Link} to={`/submissions/${sub.id}`} variant="outlined" size="small">Review</Button>
                                                            </TableCell>
                                                        )}
                                                    </TableRow>
                                                );
                                            })
                                        )}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>
        </Container>
    );
}
