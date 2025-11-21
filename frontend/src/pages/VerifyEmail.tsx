import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Box, Container, Typography, Card, CardContent, CircularProgress, Alert, Button } from '@mui/material';
import { CheckCircle, Error as ErrorIcon } from '@mui/icons-material';
import { authApi } from '../services/api';

export function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    
    if (!token) {
      setStatus('error');
      setMessage('Invalid verification link');
      return;
    }

    const verifyEmail = async () => {
      try {
        await authApi.verifyEmail(token);
        setStatus('success');
        setMessage('Your email has been successfully verified! You can now log in.');
        
        // Redirect to login after 3 seconds
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      } catch (err) {
        setStatus('error');
        setMessage(err instanceof Error ? err.message : 'Email verification failed. The link may be invalid or expired.');
      }
    };

    verifyEmail();
  }, [searchParams, navigate]);

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #121212 0%, #1a1a1a 100%)',
        py: 4,
      }}
    >
      <Container maxWidth="sm">
        <Card sx={{ p: 2 }}>
          <CardContent>
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              {status === 'loading' && (
                <>
                  <CircularProgress size={64} sx={{ mb: 2 }} />
                  <Typography variant="h5" gutterBottom>
                    Verifying your email...
                  </Typography>
                </>
              )}

              {status === 'success' && (
                <>
                  <CheckCircle sx={{ fontSize: 64, color: '#00D98B', mb: 2 }} />
                  <Typography variant="h5" gutterBottom>
                    Email Verified!
                  </Typography>
                </>
              )}

              {status === 'error' && (
                <>
                  <ErrorIcon sx={{ fontSize: 64, color: '#ef4444', mb: 2 }} />
                  <Typography variant="h5" gutterBottom>
                    Verification Failed
                  </Typography>
                </>
              )}
            </Box>

            {status === 'success' && (
              <Alert severity="success" sx={{ mb: 3, borderRadius: 0 }}>
                {message}
              </Alert>
            )}

            {status === 'error' && (
              <Alert severity="error" sx={{ mb: 3, borderRadius: 0 }}>
                {message}
              </Alert>
            )}

            {status === 'success' && (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center' }}>
                Redirecting to login page...
              </Typography>
            )}

            {status === 'error' && (
              <Box sx={{ textAlign: 'center', mt: 3 }}>
                <Button
                  component={Link}
                  to="/login"
                  variant="contained"
                  sx={{ mr: 2 }}
                >
                  Go to Login
                </Button>
                <Button
                  component={Link}
                  to="/register"
                  variant="gradientBorder"
                >
                  Register Again
                </Button>
              </Box>
            )}
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
}
