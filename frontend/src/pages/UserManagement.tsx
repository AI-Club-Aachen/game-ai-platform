import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  CheckCircle as VerifiedIcon,
  Cancel as UnverifiedIcon,
} from '@mui/icons-material';
import { usersApi } from '../services/api';

interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  email_verified: boolean;
  created_at: string;
}

export function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [editedRole, setEditedRole] = useState<string>('user');
  const [actionLoading, setActionLoading] = useState(false);

  // Fetch users on mount
  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await usersApi.listUsers();
      setUsers(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (user: User) => {
    setSelectedUser(user);
    setEditedRole(user.role);
    setEditDialogOpen(true);
  };

  const handleDelete = (user: User) => {
    setSelectedUser(user);
    setDeleteDialogOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!selectedUser) return;

    try {
      setActionLoading(true);
      setError(null);

      // Update role if changed
      if (editedRole !== selectedUser.role) {
        await usersApi.updateUserRole(selectedUser.id, editedRole);
      }

      // Refresh users list
      await fetchUsers();
      setEditDialogOpen(false);
      setSelectedUser(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user');
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!selectedUser) return;

    try {
      setActionLoading(true);
      setError(null);
      await usersApi.deleteUser(selectedUser.id);
      await fetchUsers();
      setDeleteDialogOpen(false);
      setSelectedUser(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete user');
    } finally {
      setActionLoading(false);
    }
  };

  const handleVerifyEmail = async (userId: string) => {
    try {
      setError(null);
      await usersApi.verifyUserEmail(userId);
      await fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to verify email');
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          User Management
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Username</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Email Verified</TableCell>
                <TableCell>Created At</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>{user.username}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    <Chip
                      label={user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                      color={user.role === 'admin' ? 'primary' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {user.email_verified ? (
                      <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', color: '#4caf50' }}>
                        <VerifiedIcon sx={{ fontSize: 18 }} />
                        <Typography variant="body2">Verified</Typography>
                      </Box>
                    ) : (
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                        <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', color: '#ff9800' }}>
                          <UnverifiedIcon sx={{ fontSize: 18 }} />
                          <Typography variant="body2">Unverified</Typography>
                        </Box>
                        <Button
                          size="small"
                          variant="text"
                          onClick={() => handleVerifyEmail(user.id)}
                          sx={{
                            fontSize: '0.75rem',
                            padding: '2px 8px',
                            minWidth: 'auto',
                            color: '#888',
                            backgroundColor: 'transparent !important',
                            backgroundImage: 'none !important',
                            '&:hover': {
                              color: '#fff',
                              backgroundColor: 'transparent !important',
                              backgroundImage: 'none !important',
                            }
                          }}
                        >
                          Verify manually
                        </Button>
                      </Box>
                    )}
                  </TableCell>
                  <TableCell>
                    {new Date(user.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => handleEdit(user)}
                      sx={{ 
                        mr: 1,
                        color: '#ffffff',
                        backgroundColor: 'transparent !important',
                        backgroundImage: 'none !important',
                        '&:hover': {
                          backgroundColor: 'transparent !important',
                          backgroundImage: 'none !important',
                        }
                      }}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(user)}
                      color="error"
                      sx={{
                        backgroundColor: 'transparent !important',
                        backgroundImage: 'none !important',
                        '&:hover': {
                          backgroundColor: 'transparent !important',
                          backgroundImage: 'none !important',
                        }
                      }}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {users.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography color="text.secondary">
              No users found
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ textAlign: 'center' }}>Edit User</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <TextField
              label="Username"
              value={selectedUser?.username || ''}
              disabled
              sx={{ 
                mb: 3,
                width: 350,
                '& .MuiInputBase-input.Mui-disabled': {
                  WebkitTextFillColor: '#999999',
                },
                '& .MuiOutlinedInput-root.Mui-disabled .MuiOutlinedInput-notchedOutline': {
                  borderColor: '#999999',
                },
                '& .MuiInputLabel-root.Mui-disabled': {
                  color: '#999999',
                }
              }}
            />
            <TextField
              label="Email"
              value={selectedUser?.email || ''}
              disabled
              sx={{ 
                mb: 3,
                width: 350,
                '& .MuiInputBase-input.Mui-disabled': {
                  WebkitTextFillColor: '#999999',
                },
                '& .MuiOutlinedInput-root.Mui-disabled .MuiOutlinedInput-notchedOutline': {
                  borderColor: '#999999',
                },
                '& .MuiInputLabel-root.Mui-disabled': {
                  color: '#999999',
                }
              }}
            />
            <FormControl sx={{ mb: 3, width: 350 }}>
              <InputLabel>Role</InputLabel>
              <Select
                value={editedRole}
                onChange={(e) => setEditedRole(e.target.value)}
                label="Role"
              >
                <MenuItem value="guest">Guest</MenuItem>
                <MenuItem value="user">User</MenuItem>
                <MenuItem value="admin">Admin</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions sx={{ justifyContent: 'center', px: 3, pb: 2 }}>
          <Button 
            onClick={() => setEditDialogOpen(false)}
            variant="gradientBorder"
            disabled={actionLoading}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleSaveEdit} 
            variant="gradientBorder"
            disabled={actionLoading}
          >
            {actionLoading ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ textAlign: 'center' }}>Delete User</DialogTitle>
        <DialogContent>
          <Typography sx={{ textAlign: 'center' }}>
            Are you sure you want to delete user "{selectedUser?.username}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ justifyContent: 'center', px: 3, pb: 2 }}>
          <Button 
            onClick={() => setDeleteDialogOpen(false)}
            variant="gradientBorder"
            disabled={actionLoading}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleConfirmDelete} 
            variant="gradientBorder"
            disabled={actionLoading}
          >
            {actionLoading ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
