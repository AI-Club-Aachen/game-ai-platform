import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Box, Container, Typography, Button, Card, CardContent, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, CircularProgress, Alert } from '@mui/material';
import { AdminPanelSettings, Dashboard as DashboardIcon } from '@mui/icons-material';
import { overlays } from '../theme';
import { agentsApi, Agent } from '../services/api/agents';
import { submissionsApi, Submission } from '../services/api/submissions';

export function Dashboard() {
  const { user, isAdmin } = useAuth();

  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;

    const fetchData = async () => {
      try {
        setLoading(true);
        const [fetchedSubmissions, fetchedAgents] = await Promise.all([
          submissionsApi.getSubmissions(0, 3),
          agentsApi.getAgents()
        ]);
        setSubmissions(fetchedSubmissions);
        setAgents(fetchedAgents);
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
        setError('Failed to load dashboard data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user]);

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'running': return 'info';
      case 'queued': return 'warning';
      case 'failed': return 'error';
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

  // Calculate stats
  const totalGames = agents.reduce((acc, agent) => acc + (agent.stats?.matches_played || 0), 0);
  const totalWins = agents.reduce((acc, agent) => acc + (agent.stats?.wins || 0), 0);
  const winRate = totalGames > 0 ? Math.round((totalWins / totalGames) * 100) : 0;
  const bestRank = agents.length > 0
    ? Math.min(...agents.filter(a => a.stats?.rank).map(a => a.stats.rank as number))
    : null;

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

      {error && (
        <Alert severity="error" sx={{ mb: 4 }}>{error}</Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {/* Stats Overview */}
          <Box sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
            gap: 3
          }}>
            {[
              { value: agents.length.toString(), label: 'Active Agents' },
              { value: totalGames.toString(), label: 'Total Games' },
              { value: `${winRate}%`, label: 'Win Rate' },
              { value: bestRank !== null && bestRank !== Infinity ? `#${bestRank}` : '-', label: 'Best Rank' },
            ].map((stat, i) => (
              <Card key={i}>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Typography variant="h3" color="primary" sx={{ fontWeight: 700, mb: 0.5 }}>{stat.value}</Typography>
                  <Typography variant="body2" color="text.secondary">{stat.label}</Typography>
                </CardContent>
              </Card>
            ))}
          </Box>

          {/* Agent Tracking Section */}
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 3 }}>Agent Tracking</Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Agent ID</TableCell>
                      <TableCell>W/L</TableCell>
                      <TableCell>Rank</TableCell>
                      <TableCell>Created</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {agents.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          <Typography color="text.secondary">No agents found</Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      agents.map(agent => (
                        <TableRow key={agent.id}>
                          <TableCell>
                            <Typography component="code" sx={{ fontSize: '0.8125rem', backgroundColor: overlays.overlayLight, px: 1, py: 0.5, borderRadius: 1 }}>
                              {agent.id.substring(0, 8)}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography component="span" sx={{ color: 'success.main' }}>{agent.stats?.wins || 0}W</Typography>
                            {' / '}
                            <Typography component="span" sx={{ color: 'error.main' }}>{agent.stats?.losses || 0}L</Typography>
                          </TableCell>
                          <TableCell>
                            <Chip label={agent.stats?.rank ? `#${agent.stats.rank}` : 'Unranked'} color="primary" size="small" />
                          </TableCell>
                          <TableCell>{new Date(agent.created_at).toLocaleDateString()}</TableCell>
                          <TableCell>
                            <Button component={Link} to={`/agents/${agent.id}`} variant="outlined" size="small">View</Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>

          {/* Submissions Section */}
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h6">Recent Submissions</Typography>
              </Box>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Submission ID</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Submitted</TableCell>
                      {isAdmin && <TableCell>Actions</TableCell>}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {submissions.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={isAdmin ? 4 : 3} align="center">
                          <Typography color="text.secondary">No submissions found</Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      submissions.slice(-3).map(sub => {
                        const status = sub.build_jobs && sub.build_jobs.length > 0
                          ? sub.build_jobs[0].status
                          : 'unknown';

                        return (
                          <TableRow key={sub.id}>
                            <TableCell>
                              <Typography component="code" sx={{ fontSize: '0.8125rem', backgroundColor: overlays.overlayLight, px: 1, py: 0.5, borderRadius: 1 }}>
                                {sub.id.substring(0, 8)}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Chip label={status} color={getStatusColor(status) as any} size="small" />
                            </TableCell>
                            <TableCell>{new Date(sub.created_at).toLocaleString()}</TableCell>
                            {isAdmin && (
                              <TableCell>
                                <Button component={Link} to={`/submissions/${sub.id}`} variant="outlined" size="small">Review</Button>
                              </TableCell>
                            )}
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Box>
      )}
    </Container>
  );
}
