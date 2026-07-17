import { useEffect, useState } from 'react';
import { Box, Container, Typography, Button, Card, CardContent, CircularProgress, Alert, TextField, MenuItem } from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useSmartBack } from '../hooks/use-smart-back';
import { useSubmissionFreeze } from '../hooks/useSubmissionFreeze';
import { useAuth } from '../context/AuthContext';
import { getLatestBuildJob, submissionsApi } from '../services/api/submissions';
import { agentsApi } from '../services/api/agents';
import { arenasApi, ArenaRead } from '../services/api/arenas';
import { fromApiGameType, getGameById } from '../config/games';
import { FileUploadBox } from '../components/common/FileUploadBox';
import { SubmissionFreezeBanner } from '../components/common/SubmissionFreezeBanner';

const BUILD_POLL_MS = 2000;
const BUILD_POLL_ATTEMPTS = 60;

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export function NewSubmission() {
    const navigate = useNavigate();
    const goBack = useSmartBack('/dashboard');
    const { isAdmin } = useAuth();
    const { frozen } = useSubmissionFreeze();
    const blockedByFreeze = frozen && !isAdmin;
    const [searchParams] = useSearchParams();
    const agentId = searchParams.get('agentId');

    const [arenas, setArenas] = useState<ArenaRead[]>([]);
    const [arenasLoading, setArenasLoading] = useState(true);
    const [arenaId, setArenaId] = useState('');
    const [submissionName, setSubmissionName] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [statusMessage, setStatusMessage] = useState<string | null>(null);

    useEffect(() => {
        const initPage = async () => {
            try {
                setArenasLoading(true);
                const fetchedArenas = await arenasApi.getArenas();
                const activeArenas = fetchedArenas.filter(a => a.is_active);
                setArenas(activeArenas);

                if (agentId) {
                    const agent = await agentsApi.getAgent(agentId);
                    setArenaId(agent.arena_id);
                } else if (activeArenas.length > 0) {
                    setArenaId(activeArenas[0].id);
                }
            } catch (err: any) {
                console.error('Failed to initialize page:', err);
                setError(err.message || 'Failed to load configuration.');
            } finally {
                setArenasLoading(false);
            }
        };

        initPage();
    }, [agentId]);

    const handleSubmit = async () => {
        if (!file) {
            setError('Please select a ZIP file to upload.');
            return;
        }

        if (!arenaId) {
            setError('Please choose an arena for this submission.');
            return;
        }

        try {
            setLoading(true);
            setError(null);
            setStatusMessage('Uploading your submission...');
            const submission = await submissionsApi.submitAgent(file, arenaId, submissionName.trim() || undefined);

            if (!agentId) {
                navigate(`/submissions/${submission.id}`);
                return;
            }

            setStatusMessage('Waiting for the build to finish so we can link it to the agent...');
            for (let attempt = 0; attempt < BUILD_POLL_ATTEMPTS; attempt += 1) {
                const currentSubmission = await submissionsApi.getSubmission(submission.id);
                const latestJob = getLatestBuildJob(currentSubmission);

                if (latestJob?.status === 'completed') {
                    await agentsApi.updateAgent(agentId, { active_submission_id: currentSubmission.id });
                    navigate(`/agents/${agentId}`);
                    return;
                }

                if (latestJob?.status === 'failed') {
                    navigate(`/submissions/${submission.id}`);
                    return;
                }

                await sleep(BUILD_POLL_MS);
            }

            navigate(`/submissions/${submission.id}`);
        } catch (err: any) {
            console.error('Submission failed:', err);
            setError(err.message || 'Failed to upload agent submission. Please try again.');
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
                {agentId ? 'Upload Submission' : 'New Submission'}
            </Typography>
            <Card>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Upload Agent ZIP
                    </Typography>
                    <Typography variant="body2" color="text.secondary" paragraph>
                        Submit a new AI agent packaged as a ZIP file. The ZIP archive must contain your agent script (e.g., `main.py`)
                        and any necessary dependency files (e.g., `requirements.txt`).
                    </Typography>

                    {blockedByFreeze && <SubmissionFreezeBanner sx={{ mb: 3 }} />}

                    {error && (
                        <Alert severity="error" sx={{ mb: 3 }}>
                            {error}
                        </Alert>
                    )}

                    {statusMessage && (
                        <Alert severity="info" sx={{ mb: 3 }}>
                            {statusMessage}
                        </Alert>
                    )}

                    {arenasLoading ? (
                        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 3 }}>
                            <CircularProgress size={20} />
                            <Typography color="text.secondary">Loading arenas...</Typography>
                        </Box>
                    ) : (
                        <TextField
                            select
                            label="Arena"
                            value={arenaId}
                            onChange={(e) => setArenaId(e.target.value)}
                            disabled={loading || Boolean(agentId)}
                            fullWidth
                            helperText={agentId ? 'This submission will be linked to the agent.' : 'Choose the arena this submission is uploaded to.'}
                            sx={{ mb: 3 }}
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

                    <TextField
                        label="Submission Name"
                        value={submissionName}
                        onChange={(e) => setSubmissionName(e.target.value)}
                        disabled={loading}
                        fullWidth
                        helperText="Optional. If left blank, the submission ID will be used as the name."
                        sx={{ mb: 3 }}
                    />

                    <FileUploadBox
                        file={file}
                        onFileChange={setFile}
                        onError={setError}
                        disabled={loading || arenasLoading}
                        title="Select a ZIP file to upload"
                        sx={{ mt: 2, mb: 4 }}
                    />

                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
                        <Button variant="outlined" onClick={() => navigate('/dashboard')} disabled={loading}>
                            Cancel
                        </Button>
                        <Button
                            variant="contained"
                            color="primary"
                            onClick={handleSubmit}
                            disabled={!file || !arenaId || loading || arenasLoading || blockedByFreeze}
                            sx={{ minWidth: 140 }}
                        >
                            {loading ? <CircularProgress size={24} color="inherit" /> : agentId ? 'Upload Submission' : 'Submit Agent'}
                        </Button>
                    </Box>
                </CardContent>
            </Card>
        </Container>
    );
}
