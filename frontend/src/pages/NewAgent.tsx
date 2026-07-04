import { useMemo, useState, useEffect } from 'react';
import { Alert, Box, Button, Card, CardContent, CircularProgress, Container, MenuItem, TextField, Typography, InputAdornment, IconButton } from '@mui/material';
import { ArrowBack, SmartToy, Visibility, VisibilityOff, Lock } from '@mui/icons-material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useSmartBack } from '../hooks/use-smart-back';
import { useSubmissionFreeze } from '../hooks/useSubmissionFreeze';
import { agentsApi } from '../services/api/agents';
import { getLatestBuildJob, submissionsApi, Submission } from '../services/api/submissions';
import { arenasApi, ArenaRead } from '../services/api/arenas';
import { useAuth } from '../context/AuthContext';
import { fromApiGameType, getGameById } from '../config/games';
import { FileUploadBox } from '../components/common/FileUploadBox';
import { SubmissionFreezeBanner } from '../components/common/SubmissionFreezeBanner';

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
    const { user, isAdmin } = useAuth();
    const { frozen } = useSubmissionFreeze();
    const blockedByFreeze = frozen && !isAdmin;

    const [arenas, setArenas] = useState<ArenaRead[]>([]);
    const [arenasLoading, setArenasLoading] = useState(true);
    
    const requestedArenaId = searchParams.get('arenaId') ?? '';
    const [arenaId, setArenaId] = useState(requestedArenaId);
    const [agentName, setAgentName] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [submissionName, setSubmissionName] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [statusMessage, setStatusMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [createdAgentId, setCreatedAgentId] = useState<string | null>(null);
    const [createdSubmissionId, setCreatedSubmissionId] = useState<string | null>(null);

    useEffect(() => {
        setArenasLoading(true);
        arenasApi.getArenas()
            .then(data => {
                const activeArenas = data.filter(a => a.is_active);
                setArenas(activeArenas);
                if (activeArenas.length > 0 && !arenaId) {
                    setArenaId(activeArenas[0].id);
                }
            })
            .catch(err => {
                setError(err.message || 'Failed to load arenas');
            })
            .finally(() => setArenasLoading(false));
    }, []);

    const selectedArena = useMemo(() => {
        return arenas.find(a => a.id === arenaId);
    }, [arenas, arenaId]);

    const handleSubmit = async () => {
        if (!user) {
            setError('You need to be logged in to create an agent.');
            return;
        }

        if (!selectedArena) {
            setError('Please select a valid arena.');
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
                game_type: selectedArena.game_type,
                arena_id: selectedArena.id,
                name: agentName.trim(),
                password: selectedArena.has_password && password.trim() ? password : undefined,
                active_submission_id: null,
            });
            setCreatedAgentId(agent.id);

            if (!file) {
                navigate(`/arenas/${selectedArena.id}`);
                return;
            }

            setStatusMessage('Uploading your submission...');
            const submission = await submissionsApi.submitAgent(file, selectedArena.id, submissionName.trim());
            setCreatedSubmissionId(submission.id);

            setStatusMessage('Building your submission and linking it to the agent if it succeeds...');
            const completedSubmission = await waitForSubmission(submission.id);
            const latestJob = getLatestBuildJob(completedSubmission);

            if (latestJob?.status === 'completed') {
                await agentsApi.updateAgent(agent.id, { active_submission_id: completedSubmission.id });
                navigate(`/arenas/${selectedArena.id}`);
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
                Submit Agent
            </Typography>

            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Agent Setup
                    </Typography>
                    <Typography variant="body2" color="text.secondary" paragraph>
                        Select a target arena to create and submit an agent. If the arena is password-protected, you must supply the password to join.
                    </Typography>

                    {blockedByFreeze && <SubmissionFreezeBanner sx={{ mb: 3 }} />}

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
                            helperText="Optional. If left blank, a default name will be assigned."
                        />

                        {arenasLoading ? (
                            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                                <CircularProgress size={20} />
                                <Typography color="text.secondary">Loading arenas...</Typography>
                            </Box>
                        ) : (
                            <TextField
                                select
                                label="Arena"
                                value={arenaId}
                                onChange={(e) => setArenaId(e.target.value)}
                                disabled={loading}
                                fullWidth
                            >
                                {arenas.map((arena) => {
                                    const gameConfig = getGameById(fromApiGameType(arena.game_type));
                                    return (
                                        <MenuItem key={arena.id} value={arena.id}>
                                            {arena.name} ({gameConfig?.name || arena.game_type})
                                        </MenuItem>
                                    );
                                })}
                            </TextField>
                        )}

                        {selectedArena?.has_password && (
                            <TextField
                                label="Arena Password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                disabled={loading}
                                type={showPassword ? 'text' : 'password'}
                                required
                                fullWidth
                                helperText="This arena is protected. Please enter the password to submit your agent."
                                InputProps={{
                                    startAdornment: (
                                        <InputAdornment position="start">
                                            <Lock sx={{ color: 'warning.main', fontSize: 18 }} />
                                        </InputAdornment>
                                    ),
                                    endAdornment: (
                                        <InputAdornment position="end">
                                            <IconButton onClick={() => setShowPassword(!showPassword)} edge="end" disabled={loading}>
                                                {showPassword ? <VisibilityOff /> : <Visibility />}
                                            </IconButton>
                                        </InputAdornment>
                                    )
                                }}
                            />
                        )}

                        <TextField
                            label="Submission Name"
                            value={submissionName}
                            onChange={(e) => setSubmissionName(e.target.value)}
                            disabled={loading}
                            fullWidth
                            helperText="Optional. Descriptive label for your code bundle."
                        />

                        <FileUploadBox
                            file={file}
                            onFileChange={setFile}
                            onError={setError}
                            disabled={loading}
                        />

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
                            disabled={loading || blockedByFreeze || arenasLoading || !arenaId}
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
