import { useAuth } from '../context/AuthContext';
import { Box, Container, Typography, Button, Card, CardContent, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip } from '@mui/material';
import { AdminPanelSettings, Dashboard as DashboardIcon, Settings } from '@mui/icons-material';

interface Submission {
  id: string;
  agentName: string;
  version: string;
  status: 'pending' | 'approved' | 'rejected';
  submittedAt: string;
  score?: number;
}

interface Agent {
  id: string;
  name: string;
  language: string;
  wins: number;
  losses: number;
  rank: number;
  lastActive: string;
}

export function Dashboard() {
  const { user, isAdmin } = useAuth();

  // Mock data
  const submissions: Submission[] = [
    { id: '1', agentName: 'AlphaBot', version: 'v1.2', status: 'approved', submittedAt: '2025-10-30', score: 1250 },
    { id: '2', agentName: 'BetaAI', version: 'v2.0', status: 'pending', submittedAt: '2025-11-01' },
    { id: '3', agentName: 'AlphaBot', version: 'v1.1', status: 'rejected', submittedAt: '2025-10-28', score: 980 },
  ];

  const agents: Agent[] = [
    { id: '1', name: 'AlphaBot', language: 'Python', wins: 45, losses: 12, rank: 3, lastActive: '2025-11-01' },
    { id: '2', name: 'BetaAI', language: 'JavaScript', wins: 38, losses: 19, rank: 7, lastActive: '2025-10-30' },
    { id: '3', name: 'GammaNet', language: 'Python', wins: 52, losses: 8, rank: 1, lastActive: '2025-11-01' },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved': return 'success';
      case 'pending': return 'warning';
      case 'rejected': return 'error';
      default: return 'default';
    }
  };

  if (!user) {
    return (
      <Container maxWidth="lg" sx={{ py: 8, textAlign: 'center' }}>
        <Typography variant="h4" gutterBottom>
          Please log in to view your dashboard
        </Typography>
        <Typography color="text.secondary">
          Use the login buttons in the navigation to continue
        </Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {isAdmin ? <><AdminPanelSettings /> Admin Dashboard</> : <><DashboardIcon /> User Dashboard</>}
        </Typography>
        <Typography color="text.secondary">
          Welcome back, {user.username}!
        </Typography>
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {/* Submissions Section */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              📤 Recent Submissions
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Agent Name</TableCell>
                    <TableCell>Version</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Submitted</TableCell>
                    <TableCell>Score</TableCell>
                    {isAdmin && <TableCell>Actions</TableCell>}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {submissions.map(sub => (
                    <TableRow key={sub.id}>
                      <TableCell>{sub.agentName}</TableCell>
                      <TableCell>
                        <Typography component="code" sx={{ fontSize: '0.875rem', backgroundColor: '#333', px: 1, py: 0.5, borderRadius: 0 }}>
                          {sub.version}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={sub.status} color={getStatusColor(sub.status) as any} size="small" />
                      </TableCell>
                      <TableCell>{sub.submittedAt}</TableCell>
                      <TableCell>{sub.score || '-'}</TableCell>
                      {isAdmin && (
                        <TableCell>
                          <Button variant="gradientBorder" size="small">Review</Button>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            <Box sx={{ mt: 2 }}>
              <Button variant="contained">+ New Submission</Button>
            </Box>
          </CardContent>
        </Card>

        {/* Agent Tracking Section */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              🤖 Agent Tracking
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Language</TableCell>
                    <TableCell>W/L</TableCell>
                    <TableCell>Rank</TableCell>
                    <TableCell>Last Active</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {agents.map(agent => (
                    <TableRow key={agent.id}>
                      <TableCell><strong>{agent.name}</strong></TableCell>
                      <TableCell>{agent.language}</TableCell>
                      <TableCell>
                        {agent.wins}W / {agent.losses}L
                      </TableCell>
                      <TableCell>
                        <Chip label={`#${agent.rank}`} color="primary" size="small" />
                      </TableCell>
                      <TableCell>{agent.lastActive}</TableCell>
                      <TableCell>
                        <Button variant="gradientBorder" size="small">View</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>

        {/* Stats Overview */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              📈 Quick Stats
            </Typography>
            <Box sx={{ 
              display: 'grid', 
              gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
              gap: 3 
            }}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h3" color="primary">3</Typography>
                <Typography color="text.secondary">Active Agents</Typography>
              </Box>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h3" color="primary">135</Typography>
                <Typography color="text.secondary">Total Games</Typography>
              </Box>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h3" color="primary">68%</Typography>
                <Typography color="text.secondary">Win Rate</Typography>
              </Box>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h3" color="primary">#3</Typography>
                <Typography color="text.secondary">Best Rank</Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* Admin Only Section */}
        {isAdmin && (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Settings /> Admin Controls
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Button variant="contained">Manage Users</Button>
                <Button variant="contained">Review Submissions</Button>
                <Button variant="contained">View System Logs</Button>
                <Button variant="contained">Configure Tournaments</Button>
              </Box>
            </CardContent>
          </Card>
        )}
      </Box>
    </Container>
  );
}
