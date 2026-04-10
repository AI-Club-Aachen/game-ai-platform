import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Box, Container, Typography, Card, CardContent, Button, Chip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, CircularProgress, Alert } from '@mui/material';
import { ArrowBack, PlayCircle, Videocam, History, PlayArrow } from '@mui/icons-material';
import { palette } from '../theme';
import { useSmartBack } from '../hooks/use-smart-back';
import { matchesApi } from '../services/api/matches';
import { agentsApi } from '../services/api/agents';
import { toApiGameType, getGameById, fromApiGameType } from '../config/games';

export function Matches() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const gameParam = queryParams.get('game') || '';
  
  const goBack = useSmartBack(gameParam ? `/games/${gameParam}` : '/games');

  const [matches, setMatches] = useState<any[]>([]);
  const [agentMap, setAgentMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    const apiGameType = gameParam ? toApiGameType(gameParam) : undefined;
    
    Promise.all([
      matchesApi.getMatches({ game_type: apiGameType }),
      agentsApi.getAgents(0, 1000, true)
    ])
      .then(([matchesData, agentsData]: any) => {
        if (!mounted) return;
        setMatches(Array.isArray(matchesData) ? matchesData : matchesData.data || []);
        
        const agentsArr = Array.isArray(agentsData) ? agentsData : agentsData.data || [];
        const map: Record<string, string> = {};
        agentsArr.forEach((a: any) => { map[a.id] = a.name; });
        setAgentMap(map);
        
        setError(null);
      })
      .catch((err: any) => {
        if (!mounted) return;
        setError('Failed to load matches and agents. ' + (err.message || ''));
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
      return () => { mounted = false; };
  }, [gameParam]);

  const liveMatches = matches.filter(m => m.status === 'running' || m.status === 'in_progress');
  const pastMatches = matches.filter(m => m.status === 'completed' || m.status === 'failed' || m.status === 'client_error');

  const gameInfo = getGameById(gameParam);
  const title = gameInfo ? `${gameInfo.name} Matches` : 'Matches';

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return 'success';
      case 'running': return 'primary';
      case 'failed':
      case 'client_error': return 'error';
      case 'queued': return 'warning';
      default: return 'default';
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Button startIcon={<ArrowBack />} onClick={goBack} sx={{ mb: 2 }}>
        Back
      </Button>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PlayCircle sx={{ fontSize: 32 }} /> {title}
        </Typography>
        <Typography color="text.secondary">Watch live matches or review past matches</Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          {/* Live Matches Section */}
          <Box sx={{ mb: 6 }}>
            <Box sx={{ mb: 3 }}>
              <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Videocam sx={{ fontSize: 24 }} /> Live Matches
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Box sx={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  backgroundColor: palette.error,
                  animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                  '@keyframes pulse': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.5 } },
                }} />
                <Typography variant="body2" color="text.secondary">
                  {liveMatches.length} match{liveMatches.length !== 1 ? 'es' : ''} currently in progress
                </Typography>
              </Box>
            </Box>
            {liveMatches.length === 0 ? (
              <Card><CardContent><Typography color="text.secondary">No live matches at the moment.</Typography></CardContent></Card>
            ) : (
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }, gap: 3 }}>
                {liveMatches.map((match) => (
                  <Card key={match.id}>
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                        <Chip label={fromApiGameType(match.game_type)} size="small" />
                        <Chip label={match.status} color="error" size="small" variant="outlined" />
                      </Box>
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>Agents:</Typography>
                        {match.agent_ids && match.agent_ids.length > 0 ? (
                          match.agent_ids.map((id: string, idx: number) => (
                            <Box key={id} sx={{ mb: 0.5, display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography variant="body2" fontWeight={600}>Agent {idx + 1}:</Typography>
                              <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>{agentMap[id] || id.substring(0, 8) + '...'}</Typography>
                            </Box>
                          ))
                        ) : (
                          <Typography variant="body2" color="text.secondary">No agents</Typography>
                        )}
                      </Box>
                      <Box sx={{ mb: 3 }}>
                        <Typography variant="caption" color="text.secondary">
                          Started: {new Date(match.created_at).toLocaleString()}
                        </Typography>
                      </Box>
                      <Button variant="outlined" fullWidth onClick={() => navigate('/games/live/' + match.id)} color="error" startIcon={<Videocam />}>
                        Watch Match
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            )}
          </Box>

          {/* Past Matches Section */}
          <Box>
            <Box sx={{ mb: 3 }}>
              <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <History sx={{ fontSize: 24 }} /> Past Matches
              </Typography>
              <Typography variant="body2" color="text.secondary">Review and analyze previous matches</Typography>
            </Box>
            <Card>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Match ID</TableCell>
                      <TableCell>Game Type</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Agents</TableCell>
                      <TableCell>Date</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {pastMatches.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                          <Typography color="text.secondary">No past matches found.</Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      pastMatches.map((match) => (
                        <TableRow key={match.id}>
                          <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                            {match.id.substring(0, 8)}...
                          </TableCell>
                          <TableCell>
                            <Chip label={fromApiGameType(match.game_type)} size="small" />
                          </TableCell>
                          <TableCell>
                            <Chip label={match.status} size="small" color={getStatusColor(match.status) as any} />
                          </TableCell>
                          <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                            {match.agent_ids && match.agent_ids.length > 0
                              ? match.agent_ids.map((id:string)=>agentMap[id] || id.substring(0,8)).join(' vs ')
                              : 'None'}
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {new Date(match.created_at).toLocaleDateString()}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {new Date(match.created_at).toLocaleTimeString()}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Button
                              size="small"
                              startIcon={<PlayArrow />}
                              variant="outlined"
                              onClick={() => navigate('/games/live/' + match.id)}
                            >
                              Replay
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Card>
          </Box>
        </>
      )}
    </Container>
  );
}
