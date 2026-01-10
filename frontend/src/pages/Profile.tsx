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
} from '@mui/material';
import { Person as PersonIcon } from '@mui/icons-material';
import { getAvatarUrl } from '../utils/avatar';
import { useEffect } from 'react';

export function Profile() {
  const { user, logout } = useAuth();
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

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleChangePassword = () => {
    if (newPassword !== confirmPassword) {
      console.error('Passwords do not match');
      return;
    }
    // Change password logic
    console.log('Password changed');
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
  };

  const handleDeleteAccount = () => {
    // Delete account logic
    console.log('Account deleted');
    logout();
    navigate('/login');
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
            onClick={() => {
              // Save profile changes
              console.log('Profile updated');
            }}
          >
            Save Changes
          </Button>
          <Button
            variant="outlined"
            color="error"
            onClick={handleLogout}
          >
            Logout
          </Button>
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

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Once you delete your account, there is no going back. Please be certain.
        </Typography>

        <Button
          variant="outlined"
          color="error"
          onClick={() => setDeleteDialogOpen(true)}
        >
          Delete Account
        </Button>
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
            variant="gradientBorder"
          >
            Cancel
          </Button>
          <Button
            onClick={handleDeleteAccount}
            variant="outlined"
            color="error"
          >
            Delete Account
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
