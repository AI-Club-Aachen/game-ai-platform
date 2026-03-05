import { useEffect, useState, useRef } from 'react';
import { useSearchParams, useNavigate, Link, useLocation } from 'react-router-dom';
import { Box, Container, Typography, Card, CardContent, CircularProgress, Alert, Button, TextField, Divider } from '@mui/material';
import { CheckCircle, Error as ErrorIcon, MarkEmailRead, Send } from '@mui/icons-material';
import { emailApi } from '../services/api/email';

export function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const urlToken = searchParams.get('token');

  const [token, setToken] = useState(urlToken || '');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const [email, setEmail] = useState(location.state?.email || '');
  const [resendStatus, setResendStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [resendMessage, setResendMessage] = useState('');

  const verificationAttempted = useRef(false);

  useEffect(() => {
    if (urlToken && !verificationAttempted.current) {
      verificationAttempted.current = true;
      verifyToken(urlToken);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlToken]);

  const verifyToken = async (tokenToVerify: string) => {
    setStatus('loading');
    setMessage('');
    try {
      await emailApi.verifyEmail(tokenToVerify);
      setStatus('success');
      setMessage('Your email has been successfully verified! Redirecting to login...');

      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err) {
      setStatus('error');
      setMessage(err instanceof Error ? err.message : 'Verification failed. The token may be invalid or expired.');
    }
  };

  const handleManualVerify = (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    verifyToken(token);
  };

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setResendStatus('loading');
    setResendMessage('');
    try {
      const response = await emailApi.resendVerification(email);
      setResendStatus('success');
      setResendMessage(response.message || 'If an account exists with this email, a verification link has been sent.');
    } catch (err) {
      setResendStatus('error');
      setResendMessage(err instanceof Error ? err.message : 'Failed to resend verification email.');
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'radial-gradient(ellipse at 50% 0%, rgba(25, 181, 255, 0.06) 0%, transparent 60%)',
        py: 4,
      }}
    >
      <Container maxWidth="sm">
        <Card sx={{ p: { xs: 2, sm: 3 } }}>
          <CardContent>
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <MarkEmailRead sx={{ fontSize: 44, color: 'primary.main', mb: 2 }} />
              <Typography variant="h4" gutterBottom>
                Verify Email
              </Typography>
              <Typography color="text.secondary">
                Registration successful! Please check your email to verify your account.
                <br />
                Don't forget to check your <u><b>spam folder</b></u>.
              </Typography>
            </Box>

            {status === 'loading' && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
                <CircularProgress />
              </Box>
            )}

            {status === 'success' && (
              <Box sx={{ textAlign: 'center', mb: 3 }}>
                <CheckCircle sx={{ fontSize: 56, color: 'success.main', mb: 2 }} />
                <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>
              </Box>
            )}

            {status === 'error' && (
              <Box sx={{ textAlign: 'center', mb: 3 }}>
                <ErrorIcon sx={{ fontSize: 56, color: 'error.main', mb: 2 }} />
                <Alert severity="error" sx={{ mb: 2 }}>{message}</Alert>
              </Box>
            )}

            {status !== 'success' && (
              <form onSubmit={handleManualVerify}>
                <TextField
                  fullWidth
                  label="Verification Token"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  disabled={status === 'loading'}
                  sx={{ mb: 2 }}
                  placeholder="Paste your verification code here"
                />
                <Button
                  type="submit"
                  variant="contained"
                  fullWidth
                  disabled={status === 'loading' || !token}
                  sx={{ mb: 2 }}
                >
                  Verify Token
                </Button>
              </form>
            )}

            {status !== 'success' && <Divider sx={{ my: 4 }}>OR</Divider>}

            {status !== 'success' && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Resend Verification Email
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Didn't receive the code? Enter your email address below to request a new one.
                </Typography>

                {resendStatus === 'success' && (
                  <Alert severity="success" sx={{ mb: 2 }}>{resendMessage}</Alert>
                )}
                {resendStatus === 'error' && (
                  <Alert severity="error" sx={{ mb: 2 }}>{resendMessage}</Alert>
                )}

                <form onSubmit={handleResend}>
                  <TextField
                    fullWidth
                    label="Email Address"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={resendStatus === 'loading'}
                    sx={{ mb: 2 }}
                    placeholder="Enter your email"
                  />
                  <Button
                    type="submit"
                    variant="outlined"
                    fullWidth
                    disabled={resendStatus === 'loading' || !email}
                    endIcon={resendStatus === 'loading' ? <CircularProgress size={20} /> : <Send />}
                  >
                    Resend Verification Link
                  </Button>
                </form>
              </Box>
            )}

            <Box sx={{ textAlign: 'center', mt: 4 }}>
              <Link to="/login" style={{ textDecoration: 'none' }}>
                <Typography color="primary" sx={{ cursor: 'pointer', fontWeight: 500 }}>
                  Back to Login
                </Typography>
              </Link>
            </Box>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
}
