import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Avatar,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Snackbar,
} from '@mui/material';
import { Person as PersonIcon } from '@mui/icons-material';
import { getAvatarUrl } from '../utils/avatar';
import { authApi } from '../services/api';
import { useEffect } from 'react';

export function Profile() {
  const { user, refreshUser, logout } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState(user?.username || '');
  const [email, setEmail] = useState(user?.email || '');

  useEffect(() => {
    if (user) {
      setUsername(user.username);
      setEmail(user.email);
    }
  }, [user]);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  // Email confirmation state
  const [emailConfirmOpen, setEmailConfirmOpen] = useState(false);

  // Feedback state
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState<'success' | 'error'>('success');

  const handleCloseSnackbar = () => {
    setSnackbarOpen(false);
  };

  const showFeedback = (message: string, severity: 'success' | 'error') => {
    setSnackbarMessage(message);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleUpdateProfile = async () => {
    if (!username || !email) {
      showFeedback('Username and email are required', 'error');
      return;
    }

    // Check if email has changed
    if (user && email !== user.email) {
      setEmailConfirmOpen(true);
      return;
    }

    // Just username change
    try {
      await authApi.updateProfile({ username });
      await refreshUser();
      showFeedback('Profile updated successfully', 'success');
    } catch (error: any) {
      showFeedback(error.message || 'Failed to update profile', 'error');
    }
  };

  const handleConfirmEmailChange = async () => {
    try {
      await authApi.updateProfile({ username, email });
      setEmailConfirmOpen(false);

      // Email changed, logout user
      logout();
      navigate('/login');
    } catch (error: any) {
      setEmailConfirmOpen(false);
      showFeedback(error.message || 'Failed to update email', 'error');
    }
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      showFeedback('Passwords do not match', 'error');
      return;
    }

    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      showFeedback('Password changed successfully', 'success');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error: any) {
      showFeedback(error.message || 'Failed to change password', 'error');
    }
  };

  const handleDeleteAccount = async () => {
    if (!user) return;

    try {
      await authApi.deleteAccount(user.id);
      logout();
      navigate('/login');
    } catch (error: any) {
      setDeleteDialogOpen(false);
      showFeedback(error.message || 'Failed to delete account', 'error');
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" sx={{ mb: 4 }}>
        Profile
      </Typography>

      <Paper sx={{ p: 4 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 4 }}>
          <Avatar
            src={user ? getAvatarUrl(user.username, user.profile_picture_url) : undefined}
            alt={user?.username}
            sx={{
              width: 100,
              height: 100,
              mb: 2,
              bgcolor: '#00A6FF',
              fontSize: '2.5rem',
            }}
          >
            {!user?.profile_picture_url && <PersonIcon sx={{ fontSize: '3rem' }} />}
          </Avatar>
          <Typography variant="h5">{username}</Typography>
          <Typography variant="body2" color="text.secondary">
            {user?.role === 'admin' ? 'Administrator' : 'User'}
          </Typography>
        </Box>

        <Divider sx={{ mb: 3 }} />

        <Box sx={{ mb: 3 }}>
          <TextField
            label="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            sx={{ mb: 3, width: 400 }}
          />
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            sx={{ mb: 3, width: 400 }}
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 2, mb: 4 }}>
          <Button
            variant="gradientBorder"
            onClick={handleUpdateProfile}
            sx={{
              '&:hover': {
                background: 'transparent', // Clear any background
                backgroundImage: 'none', // Clear specific gradient image
                borderColor: '#00D98B',
                color: '#00D98B'
              }
            }}
          >
            Save Changes
          </Button>
          {/* Logout moved to Danger Zone */}
        </Box>

        <Divider sx={{ mb: 3 }} />

        <Typography variant="h6" sx={{ mb: 2 }}>
          Change Password
        </Typography>

        <Box sx={{ mb: 3 }}>
          <TextField
            label="Current Password"
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            sx={{ mb: 2, width: 400 }}
          />
          <TextField
            label="New Password"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            sx={{ mb: 2, width: 400 }}
          />
          <TextField
            label="Confirm New Password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            sx={{ mb: 2, width: 400 }}
          />
        </Box>

        <Button
          variant="gradientBorder"
          onClick={handleChangePassword}
          disabled={!currentPassword || !newPassword || !confirmPassword}
        >
          Change Password
        </Button>

        <Divider sx={{ mb: 3, mt: 4 }} />

        <Typography variant="h6" sx={{ mb: 2, color: '#f44336' }}>
          Danger Zone
        </Typography>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Button
            variant="outlined"
            onClick={handleLogout}
            sx={{
              color: '#ff9800',
              borderColor: '#ff9800',
              background: 'transparent',
              backgroundImage: 'none',
              '&:hover': {
                borderColor: '#f57c00',
                backgroundColor: 'rgba(255, 152, 0, 0.08)',
                background: 'rgba(255, 152, 0, 0.08)',
                backgroundImage: 'none',
              }
            }}
          >
            Logout
          </Button>

          <Button
            variant="contained"
            onClick={() => setDeleteDialogOpen(true)}
            sx={{
              bgcolor: '#d32f2f', // MUI red[700]
              color: 'white',
              background: '#d32f2f',
              backgroundImage: 'none',
              boxShadow: 'none',
              '&:hover': {
                bgcolor: '#c62828',
                background: '#c62828',
                backgroundImage: 'none',
              }
            }}
          >
            Delete Account
          </Button>
        </Box>
      </Paper>

      {/* Delete Account Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Account</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete your account? This action cannot be undone and all your data will be permanently deleted.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setDeleteDialogOpen(false)}
            variant="outlined"
            sx={{
              color: 'text.primary',
              borderColor: 'rgba(0, 0, 0, 0.23)', // Default MUI border color
              background: 'transparent',
              backgroundImage: 'none',
              '&:hover': {
                borderColor: 'text.primary',
                bgcolor: 'rgba(0, 0, 0, 0.04)',
                background: 'rgba(0, 0, 0, 0.04)',
                backgroundImage: 'none',
              }
            }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleDeleteAccount}
            variant="contained"
            sx={{
              bgcolor: '#d32f2f',
              color: 'white',
              background: '#d32f2f', // Force solid background
              backgroundImage: 'none', // Explicitly remove gradient
              boxShadow: 'none',
              '&:hover': {
                bgcolor: '#c62828',
                background: '#c62828',
                backgroundImage: 'none',
              }
            }}
          >
            Delete Account
          </Button>
        </DialogActions>
      </Dialog>

      {/* Email Change Confirmation Dialog */}
      <Dialog open={emailConfirmOpen} onClose={() => setEmailConfirmOpen(false)}>
        <DialogTitle>Confirm Email Change</DialogTitle>
        <DialogContent>
          <Typography sx={{ mb: 2 }}>
            Changing your email address requires re-verification.
          </Typography>
          <Typography color="warning.main" sx={{ fontWeight: 'bold' }}>
            You will be logged out immediately and must verify your new email before logging in again.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setEmailConfirmOpen(false)}
            variant="outlined"
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirmEmailChange}
            variant="gradientBorder"
          >
            Confirm & Logout
          </Button>
        </DialogActions>
      </Dialog>

      {/* Feedback Snackbar */}
      <Snackbar open={snackbarOpen} autoHideDuration={6000} onClose={handleCloseSnackbar}>
        <Alert onClose={handleCloseSnackbar} severity={snackbarSeverity} sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}
