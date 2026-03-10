import { useState } from 'react';
import { Box, Container, Typography, Button, Card, CardContent, CircularProgress, Alert } from '@mui/material';
import { ArrowBack, CloudUpload } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { submissionsApi } from '../services/api/submissions';
import { overlays, palette } from '../theme';

export function NewSubmission() {
    const navigate = useNavigate();
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

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
            const submission = await submissionsApi.submitAgent(file);
            navigate(`/submissions/${submission.id}`);
        } catch (err: any) {
            console.error('Submission failed:', err);
            setError(err.message || 'Failed to upload agent submission. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Container maxWidth="md" sx={{ py: 4 }}>
            <Button startIcon={<ArrowBack />} onClick={() => navigate('/dashboard')} sx={{ mb: 2 }}>
                Back to Dashboard
            </Button>
            <Typography variant="h4" gutterBottom>
                New Submission
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
                            {loading ? <CircularProgress size={24} color="inherit" /> : 'Submit Agent'}
                        </Button>
                    </Box>
                </CardContent>
            </Card>
        </Container>
    );
}
