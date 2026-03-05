import { useState, useEffect, useCallback } from 'react';
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
  TablePagination,
  Alert,
  Snackbar,
  CircularProgress,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  CheckCircle as VerifiedIcon,
  Cancel as UnverifiedIcon,
} from '@mui/icons-material';
import { usersApi } from '../services/api/users';

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [totalUsers, setTotalUsers] = useState(0);

  const [filterRole, setFilterRole] = useState<string>('all');
  const [filterVerified, setFilterVerified] = useState<string>('all');

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [editedRole, setEditedRole] = useState<string>('user');

  const [snackbarMessage, setSnackbarMessage] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await usersApi.listUsers({
        skip: page * rowsPerPage,
        limit: rowsPerPage,
        role: filterRole !== 'all' ? filterRole : undefined,
        email_verified: filterVerified !== 'all' ? (filterVerified === 'true') : undefined,
      });
      setUsers(response.data);
      setTotalUsers(response.total);
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch users:', err);
      setError('Failed to load users. Please ensuring you are an admin.');
    } finally {
      setLoading(false);
    }
  }, [page, rowsPerPage, filterRole, filterVerified]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleChangePage = (_event: unknown, newPage: number) => setPage(newPage);

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
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
    if (selectedUser) {
      try {
        await usersApi.updateUserRole(selectedUser.id, editedRole);
        setSnackbarMessage('User role updated successfully');
        fetchUsers();
      } catch (err) {
        setSnackbarMessage('Failed to update user role');
      }
    }
    setEditDialogOpen(false);
    setSelectedUser(null);
  };

  const handleConfirmDelete = async () => {
    if (selectedUser) {
      try {
        await usersApi.deleteUser(selectedUser.id);
        setSnackbarMessage('User deleted successfully');
        fetchUsers();
      } catch (err) {
        setSnackbarMessage('Failed to delete user');
      }
    }
    setDeleteDialogOpen(false);
    setSelectedUser(null);
  };

  const handleVerifyEmail = async (userId: string) => {
    try {
      await usersApi.verifyUserEmail(userId);
      setSnackbarMessage('Email verified manually');
      fetchUsers();
    } catch (err) {
      setSnackbarMessage('Failed to verify email');
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          User Management
        </Typography>
      </Box>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Role</InputLabel>
            <Select
              value={filterRole}
              label="Role"
              onChange={(e) => {
                setFilterRole(e.target.value);
                setPage(0);
              }}
            >
              <MenuItem value="all">All Roles</MenuItem>
              <MenuItem value="user">User</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
              <MenuItem value="guest">Guest</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Verification</InputLabel>
            <Select
              value={filterVerified}
              label="Verification"
              onChange={(e) => {
                setFilterVerified(e.target.value);
                setPage(0);
              }}
            >
              <MenuItem value="all">All Status</MenuItem>
              <MenuItem value="true">Verified</MenuItem>
              <MenuItem value="false">Unverified</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
        )}

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
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : users.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">No users found</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                users.map((user) => (
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
                        <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', color: 'success.main' }}>
                          <VerifiedIcon sx={{ fontSize: 18 }} />
                          <Typography variant="body2">Verified</Typography>
                        </Box>
                      ) : (
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                          <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', color: 'warning.main' }}>
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
                              color: 'text.secondary',
                              '&:hover': {
                                color: 'text.primary',
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
                      <IconButton size="small" onClick={() => handleEdit(user)} sx={{ mr: 1 }}>
                        <EditIcon />
                      </IconButton>
                      <IconButton size="small" onClick={() => handleDelete(user)} color="error">
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          component="div"
          count={totalUsers}
          page={page}
          onPageChange={handleChangePage}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          rowsPerPageOptions={[5, 10, 25, 50, 100]}
        />
      </Paper>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit User Role</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <TextField
              label="Username"
              value={selectedUser?.username || ''}
              disabled
              fullWidth
            />
            <TextField
              label="Email"
              value={selectedUser?.email || ''}
              disabled
              fullWidth
            />
            <FormControl fullWidth>
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
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)} variant="outlined">
            Cancel
          </Button>
          <Button onClick={handleSaveEdit} variant="contained">
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
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} variant="outlined">
            Cancel
          </Button>
          <Button
            onClick={handleConfirmDelete}
            variant="contained"
            sx={{
              bgcolor: 'error.main',
              '&:hover': { bgcolor: 'error.dark' },
            }}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!snackbarMessage}
        autoHideDuration={6000}
        onClose={() => setSnackbarMessage(null)}
        message={snackbarMessage}
      />
    </Box>
  );
}
