import { useMemo, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, CircularProgress, Container, MenuItem, TextField, Typography } from '@mui/material';
import { ArrowBack, CloudUpload, SmartToy } from '@mui/icons-material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useSmartBack } from '../hooks/use-smart-back';
import { agentsApi } from '../services/api/agents';
import { getLatestBuildJob, submissionsApi, Submission } from '../services/api/submissions';
import { useAuth } from '../context/AuthContext';
import { fromApiGameType, getActiveGames, toApiGameType } from '../config/games';
import { overlays, palette } from '../theme';

const BUILD_POLL_MS = 2000;
const BUILD_POLL_ATTEMPTS = 60;

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

class SubmissionBuildPendingError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'SubmissionBuildPendingError';
    }
}

async function waitForSubmission(submissionId: string): Promise<Submission> {
    for (let attempt = 0; attempt < BUILD_POLL_ATTEMPTS; attempt += 1) {
        const submission = await submissionsApi.getSubmission(submissionId);
        const latestJob = getLatestBuildJob(submission);

        if (latestJob?.status === 'completed' || latestJob?.status === 'failed') {
            return submission;
        }

        await sleep(BUILD_POLL_MS);
    }

    throw new SubmissionBuildPendingError('The build is still running. You can check the submission details in a moment.');
}

export function NewAgent() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const goBack = useSmartBack('/dashboard');
    const { user } = useAuth();

    const availableGames = getActiveGames();
    const requestedGameId = searchParams.get('gameId') ?? '';
    const initialGameId = useMemo(() => {
        const normalized = fromApiGameType(requestedGameId);
        return availableGames.some(game => game.id === normalized)
            ? normalized
            : availableGames[0]?.id ?? 'chess';
    }, [availableGames, requestedGameId]);

    const [gameId, setGameId] = useState(initialGameId);
    const [agentName, setAgentName] = useState('');
    const [submissionName, setSubmissionName] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [statusMessage, setStatusMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [createdAgentId, setCreatedAgentId] = useState<string | null>(null);
    const [createdSubmissionId, setCreatedSubmissionId] = useState<string | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const nextFile = e.target.files?.[0] ?? null;
        setFile(nextFile);
        setError(null);
    };

    const handleSubmit = async () => {
        if (!user) {
            setError('You need to be logged in to create an agent.');
            return;
        }

        try {
            setLoading(true);
            setError(null);
            setCreatedAgentId(null);
            setCreatedSubmissionId(null);

            setStatusMessage('Creating your agent...');
            const agent = await agentsApi.createAgent({
                user_id: user.id,
                game_type: toApiGameType(gameId),
                name: agentName.trim() || undefined,
                active_submission_id: null,
            });
            setCreatedAgentId(agent.id);

            if (!file) {
                navigate(`/agents/${agent.id}`);
                return;
            }

            setStatusMessage('Uploading your submission...');
            const submission = await submissionsApi.submitAgent(file, submissionName.trim() || undefined);
            setCreatedSubmissionId(submission.id);

            setStatusMessage('Building your submission and linking it to the agent if it succeeds...');
            const completedSubmission = await waitForSubmission(submission.id);
            const latestJob = getLatestBuildJob(completedSubmission);

            if (latestJob?.status === 'completed') {
                await agentsApi.updateAgent(agent.id, { active_submission_id: completedSubmission.id });
                navigate(`/agents/${agent.id}`);
                return;
            }

            setError('The agent was created, but the submission build failed. The agent is still available without a linked submission.');
        } catch (err: any) {
            console.error('Agent creation failed:', err);
            if (err instanceof SubmissionBuildPendingError) {
                setStatusMessage(null);
                return;
            }

            setError(err.message || 'Failed to create agent. Please try again.');
        } finally {
            setLoading(false);
            setStatusMessage(null);
        }
    };

    return (
        <Container maxWidth="md" sx={{ py: 4 }}>
            <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 2 }}>
                Back
            </Button>

            <Typography variant="h4" gutterBottom>
                Create New Agent
            </Typography>

            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Agent Setup
                    </Typography>
                    <Typography variant="body2" color="text.secondary" paragraph>
                        Create an agent for a game first. Uploading a ZIP file is optional here. If you upload one now,
                        we will build it and automatically link it to the new agent when the build succeeds.
                    </Typography>

                    {error && (
                        <Alert severity="error" sx={{ mb: 3 }}>
                            {error}
                        </Alert>
                    )}

                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                        <TextField
                            label="Agent Name"
                            value={agentName}
                            onChange={(e) => setAgentName(e.target.value)}
                            disabled={loading}
                            fullWidth
                            helperText="Optional. If left blank, the agent ID will be used as the name."
                        />

                        <TextField
                            select
                            label="Game"
                            value={gameId}
                            onChange={(e) => setGameId(e.target.value)}
                            disabled={loading}
                            fullWidth
                        >
                            {availableGames.map((game) => (
                                <MenuItem key={game.id} value={game.id}>
                                    {game.name}
                                </MenuItem>
                            ))}
                        </TextField>

                        <TextField
                            label="Submission Name"
                            value={submissionName}
                            onChange={(e) => setSubmissionName(e.target.value)}
                            disabled={loading}
                            fullWidth
                            helperText="Optional. Only used if you upload a submission now."
                        />

                        <Box sx={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            p: 6,
                            border: '2px dashed',
                            borderColor: file ? 'primary.main' : 'divider',
                            borderRadius: 2,
                            backgroundColor: file ? `${palette.primary}10` : overlays.overlayLight,
                            transition: 'all 0.2s',
                        }}>
                            <CloudUpload sx={{ fontSize: 48, color: file ? 'primary.main' : 'text.secondary', mb: 2 }} />
                            <Typography variant="body1" sx={{ mb: 1, fontWeight: 500 }}>
                                {file ? file.name : 'Optional: upload a ZIP file now'}
                            </Typography>
                            {file && (
                                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                                    {(file.size / 1024 / 1024).toFixed(2)} MB
                                </Typography>
                            )}
                            <Button variant={file ? 'outlined' : 'contained'} component="label" disabled={loading}>
                                {file ? 'Change File' : 'Browse Files'}
                                <input
                                    type="file"
                                    hidden
                                    accept=".zip,application/zip"
                                    onChange={handleFileChange}
                                />
                            </Button>
                        </Box>

                        {statusMessage && (
                            <Alert severity="info" icon={<CircularProgress size={18} color="inherit" />}>
                                {statusMessage}
                            </Alert>
                        )}

                        {(createdAgentId || createdSubmissionId) && error && (
                            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                                {createdAgentId && (
                                    <Button
                                        variant="outlined"
                                        startIcon={<SmartToy />}
                                        onClick={() => navigate(`/agents/${createdAgentId}`)}
                                    >
                                        View Agent
                                    </Button>
                                )}
                                {createdSubmissionId && (
                                    <Button
                                        variant="outlined"
                                        onClick={() => navigate(`/submissions/${createdSubmissionId}`)}
                                    >
                                        View Submission
                                    </Button>
                                )}
                            </Box>
                        )}
                    </Box>

                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 4 }}>
                        <Button variant="outlined" onClick={goBack} disabled={loading}>
                            Cancel
                        </Button>
                        <Button
                            variant="contained"
                            onClick={handleSubmit}
                            disabled={loading}
                            sx={{ minWidth: 180 }}
                        >
                            {loading ? <CircularProgress size={24} color="inherit" /> : 'Create Agent'}
                        </Button>
                    </Box>
                </CardContent>
            </Card>
        </Container>
    );
}
