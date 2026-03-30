import { useState, useEffect } from 'react';
import { Box, Container, Typography, Button, Card, CardContent, CircularProgress, Alert, Chip, Divider } from '@mui/material';
import { ArrowBack, Code, Terminal } from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { useSmartBack } from '../hooks/use-smart-back';
import { submissionsApi, Submission } from '../services/api/submissions';
import { agentsApi } from '../services/api/agents';
import { fromApiGameType } from '../config/games';
import { overlays } from '../theme';

export function SubmissionDetails() {
    const navigate = useNavigate();
    const goBack = useSmartBack('/dashboard');
    const { id } = useParams<{ id: string }>();

    const [submission, setSubmission] = useState<Submission | null>(null);
    const [loading, setLoading] = useState(true);
    const [deleting, setDeleting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchSubmission = async () => {
        if (!id) return;
        try {
            setLoading(true);
            const data = await submissionsApi.getSubmission(id);
            setSubmission(data);
            setError(null);
        } catch (err: any) {
            console.error('Failed to fetch submission:', err);
            setError('Failed to load submission details. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSubmission();
    }, [id]);

    useEffect(() => {
        const hasActiveJobs = submission?.build_jobs?.some(job => job.status === 'queued' || job.status === 'running');
        if (!hasActiveJobs) return;

        // Auto-refresh if the submission might still be building
        const intervalId = setInterval(() => {
            fetchSubmission();
        }, 5000);

        return () => clearInterval(intervalId);
    }, [id, submission]);

    if (loading && !submission) {
        return (
            <Container maxWidth="lg" sx={{ py: 8, display: 'flex', justifyContent: 'center' }}>
                <CircularProgress />
            </Container>
        );
    }

    if (error || !submission) {
        return (
            <Container maxWidth="lg" sx={{ py: 4 }}>
                <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 2 }}>
                    Back
                </Button>
                <Alert severity="error">{error || 'Submission not found'}</Alert>
            </Container>
        );
    }

    const latestJob = submission.build_jobs && submission.build_jobs.length > 0
        ? submission.build_jobs[0]
        : null;

    const getStatusColor = (status?: string) => {
        switch (status) {
            case 'completed': return 'success';
            case 'running': return 'info';
            case 'queued': return 'warning';
            case 'failed': return 'error';
            default: return 'default';
        }
    };

    const handleDeleteSubmission = async () => {
        if (!id || !submission) return;

        const confirmed = window.confirm(`Delete submission "${submission.name}"?`);
        if (!confirmed) return;

        try {
            setDeleting(true);
            setError(null);
            const agents = await agentsApi.getAgents(0, 100);
            const linkedAgent = agents.find((agent) => agent.active_submission_id === submission.id);
            await submissionsApi.deleteSubmission(id);
            if (linkedAgent) {
                navigate(`/games/${fromApiGameType(linkedAgent.game_type)}`);
                return;
            }
            navigate('/dashboard');
        } catch (err: any) {
            console.error('Failed to delete submission:', err);
            setError(err.message || 'Failed to delete this submission.');
        } finally {
            setDeleting(false);
        }
    };

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                <Button startIcon={<ArrowBack />} onClick={goBack}>
                    Back
                </Button>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <Button variant="outlined" startIcon={<Code />} onClick={() => fetchSubmission()} disabled={deleting}>
                        Refresh Status
                    </Button>
                    <Button
                        variant="outlined"
                        onClick={handleDeleteSubmission}
                        disabled={deleting}
                        sx={{
                            color: 'error.main',
                            borderColor: 'error.main',
                            '&:hover': {
                                borderColor: 'error.dark',
                                backgroundColor: 'rgba(211, 47, 47, 0.08)',
                            },
                        }}
                    >
                        {deleting ? 'Deleting...' : 'Delete Submission'}
                    </Button>
                </Box>
            </Box>

            <Typography variant="h4" gutterBottom>
                {submission.name}
            </Typography>

            <Card sx={{ mb: 4 }}>
                <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Box>
                            <Typography variant="h6">Submission Info</Typography>
                            <Typography variant="body2" color="text.secondary">ID: {submission.id}</Typography>
                        </Box>
                        {latestJob && (
                            <Chip
                                label={latestJob.status.toUpperCase()}
                                color={getStatusColor(latestJob.status) as any}
                                sx={{ fontWeight: 'bold' }}
                            />
                        )}
                    </Box>
                    <Divider sx={{ mb: 2 }} />
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        <Typography variant="body2">
                            <strong>Submitted at:</strong> {new Date(submission.created_at).toLocaleString()}
                        </Typography>
                        {latestJob?.image_tag && (
                            <Typography variant="body2">
                                <strong>Image Tag:</strong> {latestJob.image_tag}
                            </Typography>
                        )}
                    </Box>
                </CardContent>
            </Card>

            <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Terminal /> Build Logs
            </Typography>

            {latestJob ? (
                <Box sx={{
                    backgroundColor: overlays.overlayDark,
                    p: 2,
                    borderRadius: 2,
                    minHeight: 200,
                    maxHeight: 600,
                    overflowY: 'auto',
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                    lineHeight: 1.6,
                    color: '#e0e0e0',
                    border: '1px solid',
                    borderColor: 'divider',
                    whiteSpace: 'pre-wrap'
                }}>
                    {latestJob.logs || 'Waiting for build to start...'}
                </Box>
            ) : (
                <Alert severity="info" sx={{ mt: 2 }}>
                    No build jobs have been assigned to this submission yet.
                </Alert>
            )}

            {latestJob?.status === 'completed' && (
                <Box sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
                    <Typography color="success.main" variant="h6">
                        Build completed successfully! Your agent is ready to play.
                    </Typography>
                </Box>
            )}
        </Container>
    );
}
