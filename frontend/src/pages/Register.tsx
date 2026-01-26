import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
//import { useAuth } from '../context/AuthContext'; //TODO
import { Box, Container, Typography, TextField, Button, Card, CardContent, Alert, Checkbox, FormControlLabel, List, ListItem, ListItemIcon, ListItemText, IconButton, InputAdornment } from '@mui/material';
import { PersonAdd, CheckCircle, Cancel, Visibility, VisibilityOff } from '@mui/icons-material';
import { authApi } from '../services/api/auth';

export function Register() {
  const navigate = useNavigate();
  //const { login } = useAuth(); //TODO
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  // Password Validation State
  const [passwordValidations, setPasswordValidations] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    digit: false,
    special: false,
  });

  useEffect(() => {
    const { password } = formData;
    setPasswordValidations({
      length: password.length >= 12,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      digit: /[0-9]/.test(password),
      special: /[!@#$%^&*()_+\-=[\]{}|;:',.<>?/\\`~]/.test(password),
    });
  }, [formData.password]);

  const allRequirementsMet = Object.values(passwordValidations).every(Boolean);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (!allRequirementsMet) {
      setError('Please ensure your password meets all security requirements');
      return;
    }

    if (formData.username.length < 3 || formData.username.length > 50) {
      setError('Username must be between 3 and 50 characters');
      return;
    }

    if (!agreedToTerms) {
      setError('You must agree to the terms and conditions');
      return;
    }

    setLoading(true);

    try {
      await authApi.register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
      });

      setSuccess('Registration successful! Please check your email to verify your account.');

      // Clear form
      setFormData({
        username: '',
        email: '',
        password: '',
        confirmPassword: '',
      });
      setAgreedToTerms(false);

      // Redirect to verification page after 3 seconds
      setTimeout(() => {
        navigate('/verify-email', { state: { email: formData.email } });
      }, 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const ValidationItem = ({ met, text }: { met: boolean; text: string }) => (
    <ListItem dense sx={{ py: 0 }}>
      <ListItemIcon sx={{ minWidth: 32 }}>
        {met ? (
          <CheckCircle sx={{ fontSize: 16, color: 'success.main' }} />
        ) : (
          <Cancel sx={{ fontSize: 16, color: 'error.main' }} />
        )}
      </ListItemIcon>
      <ListItemText
        primary={text}
        primaryTypographyProps={{
          variant: 'caption',
          color: met ? 'text.primary' : 'text.secondary'
        }}
      />
    </ListItem>
  );

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
              <PersonAdd sx={{ fontSize: 48, color: '#00D98B', mb: 2 }} />
              <Typography variant="h4" gutterBottom>
                Create Account
              </Typography>
              <Typography color="text.secondary">
                Join the AICA gaming platform today
              </Typography>
            </Box>

            {error && (
              <Alert severity="error" sx={{ mb: 3, borderRadius: 0 }}>
                {error}
              </Alert>
            )}

            {success && (
              <Alert severity="success" sx={{ mb: 3, borderRadius: 0 }}>
                {success}
              </Alert>
            )}

            <form onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="Username"
                name="username"
                value={formData.username}
                onChange={handleChange}
                required
                sx={{ mb: 3 }}
                autoComplete="username"
              />

              <TextField
                fullWidth
                label="Email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                required
                sx={{ mb: 3 }}
                autoComplete="email"
              />

              <TextField
                fullWidth
                label="Password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={handleChange}
                required
                sx={{ mb: 1 }}
                autoComplete="new-password"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle password visibility"
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                        sx={{ color: 'text.primary' }}
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <Box sx={{ mb: 3, ml: 1 }}>
                <Typography variant="caption" color="text.secondary" sx={{ ml: 1, fontWeight: 'bold' }}>
                  Password Requirements:
                </Typography>
                <List dense sx={{ pt: 0.5 }}>
                  <ValidationItem met={passwordValidations.length} text="At least 12 characters" />
                  <ValidationItem met={passwordValidations.uppercase} text="One uppercase letter (A-Z)" />
                  <ValidationItem met={passwordValidations.lowercase} text="One lowercase letter (a-z)" />
                  <ValidationItem met={passwordValidations.digit} text="One number (0-9)" />
                  <ValidationItem met={passwordValidations.special} text="One special character (!@#$%^&*...)" />
                </List>
              </Box>

              <TextField
                fullWidth
                label="Confirm Password"
                name="confirmPassword"
                type={showConfirmPassword ? 'text' : 'password'}
                value={formData.confirmPassword}
                onChange={handleChange}
                required
                sx={{ mb: 3 }}
                autoComplete="new-password"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle confirm password visibility"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        edge="end"
                        sx={{ color: 'text.primary' }}
                      >
                        {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <FormControlLabel
                control={
                  <Checkbox
                    checked={agreedToTerms}
                    onChange={(e) => setAgreedToTerms(e.target.checked)}
                    sx={{
                      color: '#00A6FF',
                      '&.Mui-checked': {
                        color: '#00A6FF',
                      },
                    }}
                  />
                }
                label={
                  <Typography variant="body2" color="text.secondary">
                    I agree to the{' '}
                    <Link
                      to="/terms"
                      style={{
                        color: '#00A6FF',
                        textDecoration: 'none',
                      }}
                    >
                      Terms and Conditions
                    </Link>
                  </Typography>
                }
                sx={{ mb: 3 }}
              />

              <Button
                type="submit"
                variant="contained"
                fullWidth
                disabled={loading}
                sx={{ mb: 2, py: 1.5 }}
              >
                {loading ? 'Creating account...' : 'Create Account'}
              </Button>


              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary">
                  Already have an account?{' '}
                  <Link
                    to="/login"
                    style={{
                      color: '#00A6FF',
                      textDecoration: 'none',
                      fontWeight: 600,
                    }}
                  >
                    Sign in
                  </Link>
                </Typography>
              </Box>
            </form>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
}
