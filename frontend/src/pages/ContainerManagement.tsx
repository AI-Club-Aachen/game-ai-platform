import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Box, Container, Typography, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Card, CardContent, Chip } from '@mui/material';
import { Close, Refresh, Stop, Delete, Lock, Storage, Article } from '@mui/icons-material';
import { palette, overlays } from '../theme';
import { containersApi } from '../services/api';

interface ContainerInfo {
  id: string;
  containerId: string;
  name: string;
  status: 'running' | 'stopped' | 'error';
  image: string;
  created: string;
  uptime: string;
  cpu: number;
  memory: number;
  agentName: string;
  logs: string;
}

const formatUptime = (seconds: number): string => {
  if (!seconds || seconds <= 0) {
    return '-';
  }

  const total = Math.floor(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  }
  return `${secs}s`;
};

const formatCreated = (isoDate: string): string => {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return '-';
  }
  return date.toLocaleString();
};

const normalizeStatus = (status: string): ContainerInfo['status'] => {
  if (status === 'running' || status === 'stopped' || status === 'error') {
    return status;
  }
  if (status === 'paused' || status === 'created' || status === 'restarting') {
    return 'running';
  }
  if (status === 'exited' || status === 'dead' || status === 'removing') {
    return 'stopped';
  }
  return 'error';
};

export function ContainerManagement() {
  const { isAdmin } = useAuth();
  const [selectedContainer, setSelectedContainer] = useState<string | null>(null);
  const [containers, setContainers] = useState<ContainerInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const loadContainers = async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const data = await containersApi.getContainers({ limit: 200 });
      const mapped: ContainerInfo[] = data.map((item) => ({
        id: item.id,
        containerId: item.container_id,
        name: item.name || item.container_id.slice(0, 12),
        status: normalizeStatus(item.status),
        image: item.image,
        created: formatCreated(item.created_at),
        uptime: formatUptime(item.uptime_seconds),
        cpu: Number(item.cpu_percent || 0),
        memory: Number(item.memory_mb || 0),
        agentName: item.agent_name || item.agent_id,
        logs: item.logs || '',
      }));
      setContainers(mapped);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load containers';
      setFetchError(message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadContainers();
    const id = window.setInterval(() => {
      void loadContainers();
    }, 5000);

    return () => window.clearInterval(id);
  }, []);

  const getStatusColor = (status: ContainerInfo['status']) => {
    const colors = { running: 'success' as const, stopped: 'default' as const, error: 'error' as const };
    return colors[status];
  };

  if (!isAdmin) {
    return (
      <Container maxWidth="lg" sx={{ py: 8, textAlign: 'center' }}>
        <Lock sx={{ fontSize: 56, mb: 2, color: 'error.main' }} />
        <Typography variant="h4" gutterBottom>Access Denied</Typography>
        <Typography color="text.secondary">You need admin privileges to access this page</Typography>
      </Container>
    );
  }

  const runningCount = useMemo(() => containers.filter(c => c.status === 'running').length, [containers]);
  const stoppedCount = useMemo(() => containers.filter(c => c.status === 'stopped').length, [containers]);
  const errorCount = useMemo(() => containers.filter(c => c.status === 'error').length, [containers]);
  const selectedContainerEntry = useMemo(
    () => containers.find((container) => container.id === selectedContainer) || null,
    [containers, selectedContainer],
  );
  const selectedContainerLogs = useMemo(
    () => (selectedContainerEntry?.logs ? selectedContainerEntry.logs.split(/\r?\n/) : []),
    [selectedContainerEntry],
  );

  const statusDotColor = (color: string) => ({
    width: 10,
    height: 10,
    borderRadius: '50%',
    backgroundColor: color,
    flexShrink: 0,
  });

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Storage /> Container Management
        </Typography>
        <Typography color="text.secondary">Monitor and manage Docker containers for AI agents</Typography>
        <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button variant="outlined" size="small" startIcon={<Refresh />} onClick={() => void loadContainers()}>
            Refresh
          </Button>
          {isLoading && <Typography variant="body2" color="text.secondary">Loading...</Typography>}
          {fetchError && <Typography variant="body2" color="error">{fetchError}</Typography>}
        </Box>
      </Box>

      {/* Status Cards */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' }, gap: 3, mb: 4 }}>
        <Card>
          <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={statusDotColor(palette.success)} />
            <Box>
              <Typography variant="h4">{runningCount}</Typography>
              <Typography variant="body2" color="text.secondary">Running</Typography>
            </Box>
          </CardContent>
        </Card>
        <Card>
          <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={statusDotColor(palette.textMuted)} />
            <Box>
              <Typography variant="h4">{stoppedCount}</Typography>
              <Typography variant="body2" color="text.secondary">Stopped</Typography>
            </Box>
          </CardContent>
        </Card>
        <Card>
          <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={statusDotColor(palette.error)} />
            <Box>
              <Typography variant="h4">{errorCount}</Typography>
              <Typography variant="body2" color="text.secondary">Error</Typography>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* Container Table */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 3 }}>Active Containers</Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Status</TableCell>
                  <TableCell>Container Name</TableCell>
                  <TableCell>Container ID</TableCell>
                  <TableCell>Agent</TableCell>
                  <TableCell>Image</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell>Uptime</TableCell>
                  <TableCell>CPU %</TableCell>
                  <TableCell>Memory (MB)</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {containers.map((container) => (
                  <TableRow key={container.id}>
                    <TableCell>
                      <Chip label={container.status} color={getStatusColor(container.status)} size="small" />
                    </TableCell>
                    <TableCell>
                      <Typography component="code" sx={{ fontSize: '0.8125rem', backgroundColor: overlays.overlayLight, px: 1, py: 0.5, borderRadius: 1 }}>
                        {container.name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography component="code" sx={{ fontSize: '0.8125rem', backgroundColor: overlays.overlayLight, px: 1, py: 0.5, borderRadius: 1 }}>
                        {container.containerId.slice(0, 12)}
                      </Typography>
                    </TableCell>
                    <TableCell>{container.agentName}</TableCell>
                    <TableCell>
                      <Typography component="code" sx={{ fontSize: '0.8125rem', backgroundColor: overlays.overlayLight, px: 1, py: 0.5, borderRadius: 1 }}>
                        {container.image}
                      </Typography>
                    </TableCell>
                    <TableCell>{container.created}</TableCell>
                    <TableCell>{container.uptime}</TableCell>
                    <TableCell>
                      <Typography color={container.cpu > 50 ? 'error' : 'inherit'}>{container.cpu}%</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography color={container.memory > 500 ? 'error' : 'inherit'}>{container.memory}</Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        {container.status === 'running' && (
                          <>
                            <Button variant="outlined" size="small" color="error"><Stop fontSize="small" /></Button>
                          </>
                        )}
                        {container.status === 'stopped' && (
                          <Button variant="outlined" size="small" onClick={() => setSelectedContainer(container.id)}>Logs</Button>
                        )}
                        {container.status === 'error' && (
                          <Button variant="outlined" size="small" color="error"><Delete fontSize="small" /></Button>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Container Logs */}
      {selectedContainer && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Article /> Container Logs
              </Typography>
              <Button startIcon={<Close />} onClick={() => setSelectedContainer(null)} size="small" variant="text">
                Close
              </Button>
            </Box>
            <Box sx={{
              backgroundColor: overlays.overlayDark,
              p: 2,
              borderRadius: 2,
              maxHeight: 300,
              overflowY: 'auto',
              fontFamily: 'monospace',
              fontSize: '0.8125rem',
              lineHeight: 1.6,
            }}>
              {selectedContainerLogs.length === 0 && (
                <Box sx={{ color: 'text.secondary' }}>No logs available for this container.</Box>
              )}
              {selectedContainerLogs.map((log, index) => (
                <Box key={index} sx={{ mb: 0.5, color: 'text.secondary' }}>{log}</Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}
    </Container>
  );
}
