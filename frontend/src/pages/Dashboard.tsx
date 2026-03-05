import { useAuth } from '../context/AuthContext';
import { Box, Container, Typography, Button, Card, CardContent, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip } from '@mui/material';
import { AdminPanelSettings, Dashboard as DashboardIcon } from '@mui/icons-material';
import { overlays } from '../theme';

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
        {/* Stats Overview */}
        <Box sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
          gap: 3
        }}>
          {[
            { value: '3', label: 'Active Agents' },
            { value: '135', label: 'Total Games' },
            { value: '68%', label: 'Win Rate' },
            { value: '#3', label: 'Best Rank' },
          ].map((stat, i) => (
            <Card key={i}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography variant="h3" color="primary" sx={{ fontWeight: 700, mb: 0.5 }}>{stat.value}</Typography>
                <Typography variant="body2" color="text.secondary">{stat.label}</Typography>
              </CardContent>
            </Card>
          ))}
        </Box>

        {/* Submissions Section */}
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6">Recent Submissions</Typography>
              <Button variant="contained" size="small">+ New Submission</Button>
            </Box>
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
                        <Typography component="code" sx={{ fontSize: '0.8125rem', backgroundColor: overlays.overlayLight, px: 1, py: 0.5, borderRadius: 1 }}>
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
                          <Button variant="outlined" size="small">Review</Button>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>

        {/* Agent Tracking Section */}
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 3 }}>Agent Tracking</Typography>
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
                        <Typography component="span" sx={{ color: 'success.main' }}>{agent.wins}W</Typography>
                        {' / '}
                        <Typography component="span" sx={{ color: 'error.main' }}>{agent.losses}L</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={`#${agent.rank}`} color="primary" size="small" />
                      </TableCell>
                      <TableCell>{agent.lastActive}</TableCell>
                      <TableCell>
                        <Button variant="outlined" size="small">View</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
}
