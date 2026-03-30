import { useState } from 'react';
import { Box, Container, Typography, Button, Card, CardContent, CircularProgress, Alert, TextField } from '@mui/material';
import { ArrowBack, CloudUpload } from '@mui/icons-material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useSmartBack } from '../hooks/use-smart-back';
import { submissionsApi } from '../services/api/submissions';
import { agentsApi } from '../services/api/agents';
import { overlays, palette } from '../theme';

const BUILD_POLL_MS = 2000;
const BUILD_POLL_ATTEMPTS = 60;

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export function NewSubmission() {
    const navigate = useNavigate();
    const goBack = useSmartBack('/dashboard');
    const [searchParams] = useSearchParams();
    const agentId = searchParams.get('agentId');
    const [submissionName, setSubmissionName] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [statusMessage, setStatusMessage] = useState<string | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setFile(e.target.files[0]);
            setError(null);
        }
    };

    const handleSubmit = async () => {
        if (!file) {
            setError('Please select a ZIP file to upload.');
            return;
        }

        try {
            setLoading(true);
            setError(null);
            setStatusMessage('Uploading your submission...');
            const submission = await submissionsApi.submitAgent(file, submissionName.trim() || undefined);

            if (!agentId) {
                navigate(`/submissions/${submission.id}`);
                return;
            }

            setStatusMessage('Waiting for the build to finish so we can link it to the agent...');
            for (let attempt = 0; attempt < BUILD_POLL_ATTEMPTS; attempt += 1) {
                const currentSubmission = await submissionsApi.getSubmission(submission.id);
                const latestJob = currentSubmission.build_jobs?.[0];

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

                    <TextField
                        label="Submission Name"
                        value={submissionName}
                        onChange={(e) => setSubmissionName(e.target.value)}
                        disabled={loading}
                        fullWidth
                        helperText="Optional. If left blank, the submission ID will be used as the name."
                        sx={{ mb: 3 }}
                    />

                    <Box sx={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        p: 6,
                        mt: 2,
                        mb: 4,
                        border: '2px dashed',
                        borderColor: file ? 'primary.main' : 'divider',
                        borderRadius: 2,
                        backgroundColor: file ? `${palette.primary}10` : overlays.overlayLight,
                        transition: 'all 0.2s',
                    }}>
                        <CloudUpload sx={{ fontSize: 48, color: file ? 'primary.main' : 'text.secondary', mb: 2 }} />
                        <Typography variant="body1" sx={{ mb: 1, fontWeight: 500 }}>
                            {file ? file.name : 'Select a ZIP file to upload'}
                        </Typography>
                        {file && (
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                                {(file.size / 1024 / 1024).toFixed(2)} MB
                            </Typography>
                        )}
                        <Button
                            variant={file ? 'outlined' : 'contained'}
                            component="label"
                        >
                            {file ? 'Change File' : 'Browse Files'}
                            <input
                                type="file"
                                hidden
                                accept=".zip,application/zip"
                                onChange={handleFileChange}
                            />
                        </Button>
                    </Box>

                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
                        <Button variant="outlined" onClick={() => navigate('/dashboard')} disabled={loading}>
                            Cancel
                        </Button>
                        <Button
                            variant="contained"
                            color="primary"
                            onClick={handleSubmit}
                            disabled={!file || loading}
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
