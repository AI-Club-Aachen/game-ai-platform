import { useState, useEffect } from 'react';
import { Box, Container, Typography, Button, Card, CardContent, CircularProgress, Alert, Chip, Divider, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import { ArrowBack, EmojiEvents, CalendarToday, People } from '@mui/icons-material';
import { useParams } from 'react-router-dom';
import { useSmartBack } from '../hooks/use-smart-back';
import { tournamentsApi } from '../services/api/tournaments';
import { submissionsApi, Submission } from '../services/api/submissions';
import { useAuth } from '../context/AuthContext';
import { palette } from '../theme';

export function TournamentDetails() {
    const goBack = useSmartBack('/tournaments');
    const { id } = useParams<{ id: string }>();
    const { user } = useAuth();

    const [tournament, setTournament] = useState<any | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [mySubmissions, setMySubmissions] = useState<Submission[]>([]);
    const [selectedSubmissionId, setSelectedSubmissionId] = useState<string>('');
    const [registering, setRegistering] = useState(false);
    const [registerError, setRegisterError] = useState<string | null>(null);
    const [registerSuccess, setRegisterSuccess] = useState(false);

    useEffect(() => {
        if (!id) return;

        const fetchData = async () => {
            try {
                setLoading(true);
                const tourneyData = await tournamentsApi.getTournament(id);
                setTournament(tourneyData);
                setError(null);

                // If user is logged in and tournament is upcoming, fetch submissions for registration
                if (user && tourneyData.status === 'upcoming') {
                    const subs = await submissionsApi.getSubmissions();
                    // Filter for successful builds or just show all
                    const validSubs = subs.filter(s => s.build_jobs?.some(job => job.status === 'completed'));
                    setMySubmissions(validSubs);
                }
            } catch (err: any) {
                console.error('Failed to fetch tournament:', err);
                setError('Failed to load tournament details. Please try again.');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [id, user]);

    const handleRegister = async () => {
        if (!id || !selectedSubmissionId) return;

        try {
            setRegistering(true);
            setRegisterError(null);
            await tournamentsApi.registerForTournament(id, selectedSubmissionId);
            setRegisterSuccess(true);

            // Re-fetch tournament to update participants
            const updatedTourney = await tournamentsApi.getTournament(id);
            setTournament(updatedTourney);
        } catch (err: any) {
            console.error('Registration failed:', err);
            setRegisterError(err.message || 'Failed to register. Please try again.');
        } finally {
            setRegistering(false);
        }
    };

    if (loading) {
        return (
            <Container maxWidth="lg" sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
                <CircularProgress />
            </Container>
        );
    }

    if (error || !tournament) {
        return (
            <Container maxWidth="lg" sx={{ py: 4 }}>
                <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 2 }}>
                    Back to Tournaments
                </Button>
                <Alert severity="error">{error || 'Tournament not found'}</Alert>
            </Container>
        );
    }

    const { name, status, start_date, end_date, game_id, participants } = tournament;

    const isUpcoming = status === 'upcoming';
    const isRegistered = participants?.some((p: any) => p.user_id === user?.id);

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 2 }}>
                Back to Tournaments
            </Button>

            <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Box>
                    <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <EmojiEvents fontSize="large" color="primary" />
                        {name}
                    </Typography>
                    <Typography color="text.secondary">
                        Game: {game_id}
                    </Typography>
                </Box>
                <Chip
                    label={status.toUpperCase()}
                    color={status === 'active' ? 'success' : status === 'completed' ? 'default' : 'primary'}
                />
            </Box>

            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '2fr 1fr' }, gap: 4 }}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                    <Card>
                        <CardContent>
                            <Typography variant="h6" gutterBottom>Details</Typography>
                            <Divider sx={{ mb: 2 }} />

                            <Box sx={{ display: 'flex', gap: 4, mb: 2 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <CalendarToday color="action" />
                                    <Box>
                                        <Typography variant="body2" color="text.secondary">Start Date</Typography>
                                        <Typography variant="body1">{new Date(start_date).toLocaleDateString()}</Typography>
                                    </Box>
                                </Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <CalendarToday color="action" />
                                    <Box>
                                        <Typography variant="body2" color="text.secondary">End Date</Typography>
                                        <Typography variant="body1">{new Date(end_date).toLocaleDateString()}</Typography>
                                    </Box>
                                </Box>
                            </Box>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardContent>
                            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <People /> Participants ({participants?.length || 0})
                            </Typography>
                            <Divider sx={{ mb: 2 }} />

                            {participants && participants.length > 0 ? (
                                <Box component="ul" sx={{ pl: 2, m: 0 }}>
                                    {participants.map((p: any) => (
                                        <Typography component="li" key={p.user_id} sx={{ mb: 1 }}>
                                            {p.username}
                                            {p.user_id === user?.id && " (You)"}
                                        </Typography>
                                    ))}
                                </Box>
                            ) : (
                                <Typography color="text.secondary">No participants registered yet.</Typography>
                            )}
                        </CardContent>
                    </Card>
                </Box>

                <Box>
                    {isUpcoming ? (
                        <Card sx={{ border: `1px solid ${palette.primary}`, backgroundColor: `${palette.primary}05` }}>
                            <CardContent>
                                <Typography variant="h6" gutterBottom color="primary">
                                    Registration
                                </Typography>
                                <Typography variant="body2" paragraph>
                                    Select one of your successfully built agent submissions to enter this tournament.
                                </Typography>

                                {registerSuccess || isRegistered ? (
                                    <Alert severity="success" sx={{ mt: 2 }}>
                                        You are registered for this tournament!
                                    </Alert>
                                ) : !user ? (
                                    <Alert severity="warning">
                                        Please log in to register.
                                    </Alert>
                                ) : (
                                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
                                        {registerError && <Alert severity="error">{registerError}</Alert>}

                                        <FormControl fullWidth size="small">
                                            <InputLabel>Select Agent</InputLabel>
                                            <Select
                                                value={selectedSubmissionId}
                                                label="Select Agent"
                                                onChange={(e) => setSelectedSubmissionId(e.target.value)}
                                            >
                                                {mySubmissions.map(sub => (
                                                    <MenuItem key={sub.id} value={sub.id}>
                                                        Submission {sub.id.substring(0, 8)}
                                                        ({new Date(sub.created_at).toLocaleDateString()})
                                                    </MenuItem>
                                                ))}
                                                {mySubmissions.length === 0 && (
                                                    <MenuItem disabled value="">
                                                        No completed builds found
                                                    </MenuItem>
                                                )}
                                            </Select>
                                        </FormControl>

                                        <Button
                                            variant="contained"
                                            onClick={handleRegister}
                                            disabled={!selectedSubmissionId || registering}
                                            fullWidth
                                        >
                                            {registering ? <CircularProgress size={24} /> : 'Register Now'}
                                        </Button>
                                    </Box>
                                )}
                            </CardContent>
                        </Card>
                    ) : (
                        <Card>
                            <CardContent>
                                <Typography variant="h6" gutterBottom>
                                    Match Results
                                </Typography>
                                <Typography color="text.secondary" variant="body2">
                                    {status === 'active'
                                        ? 'Tournament is currently ongoing. Match results will be displayed here soon.'
                                        : 'Tournament has concluded. Final standings and match history will be displayed here.'}
                                </Typography>
                            </CardContent>
                        </Card>
                    )}
                </Box>
            </Box>
        </Container>
    );
}
