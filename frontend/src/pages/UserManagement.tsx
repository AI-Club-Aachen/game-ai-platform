import { useState } from 'react';
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
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  CheckCircle as VerifiedIcon,
  Cancel as UnverifiedIcon,
} from '@mui/icons-material';

interface User {
  id: string;
  username: string;
  email: string;
  role: 'user' | 'admin';
  email_verified: boolean;
  created_at: string;
}

export function UserManagement() {
  const [users, setUsers] = useState<User[]>([
    {
      id: '1',
      username: 'admin',
      email: 'admin@example.com',
      role: 'admin',
      email_verified: true,
      created_at: '2025-01-01T00:00:00Z',
    },
    {
      id: '2',
      username: 'aser',
      email: 'aserhisham21@gmail.com',
      role: 'user',
      email_verified: false,
      created_at: '2025-12-06T10:04:00Z',
    },
  ]);

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [editedRole, setEditedRole] = useState<'user' | 'admin'>('user');
  const [editedVerified, setEditedVerified] = useState(false);

  const handleEdit = (user: User) => {
    setSelectedUser(user);
    setEditedRole(user.role);
    setEditedVerified(user.email_verified);
    setEditDialogOpen(true);
  };

  const handleDelete = (user: User) => {
    setSelectedUser(user);
    setDeleteDialogOpen(true);
  };

  const handleSaveEdit = () => {
    if (selectedUser) {
      setUsers(users.map(u => 
        u.id === selectedUser.id 
          ? { ...u, role: editedRole, email_verified: editedVerified }
          : u
      ));
    }
    setEditDialogOpen(false);
    setSelectedUser(null);
  };

  const handleConfirmDelete = () => {
    if (selectedUser) {
      setUsers(users.filter(u => u.id !== selectedUser.id));
    }
    setDeleteDialogOpen(false);
    setSelectedUser(null);
  };

  const handleVerifyEmail = (userId: string) => {
    setUsers(users.map(u => 
      u.id === userId 
        ? { ...u, email_verified: true }
        : u
    ));
  };

  return (
    <Box>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          User Management
        </Typography>
      </Box>

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
        <DialogTitle>Edit User</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
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
                onChange={(e) => setEditedRole(e.target.value as 'user' | 'admin')}
                label="Role"
              >
                <MenuItem value="user">User</MenuItem>
                <MenuItem value="admin">Admin</MenuItem>
              </Select>
            </FormControl>
            <FormControl sx={{ width: 350 }}>
              <InputLabel>Email Verified</InputLabel>
              <Select
                value={editedVerified ? 'true' : 'false'}
                onChange={(e) => setEditedVerified(e.target.value === 'true')}
                label="Email Verified"
              >
                <MenuItem value="true">Verified</MenuItem>
                <MenuItem value="false">Unverified</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions sx={{ justifyContent: 'flex-start', px: 3, pb: 2 }}>
          <Button 
            onClick={() => setEditDialogOpen(false)}
            variant="gradientBorder"
          >
            Cancel
          </Button>
          <Button 
            onClick={handleSaveEdit} 
            variant="gradientBorder"
          >
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Delete User</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete user "{selectedUser?.username}"? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ justifyContent: 'flex-start', px: 3, pb: 2 }}>
          <Button 
            onClick={() => setDeleteDialogOpen(false)}
            variant="gradientBorder"
          >
            Cancel
          </Button>
          <Button 
            onClick={handleConfirmDelete} 
            variant="gradientBorder"
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
