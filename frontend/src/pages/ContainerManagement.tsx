import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Box, Container, Typography, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Card, CardContent, Chip } from '@mui/material';
import { Close, Refresh, PlayArrow, Stop, Delete, Lock, Storage, Article } from '@mui/icons-material';

interface Container {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'error';
  image: string;
  created: string;
  uptime: string;
  cpu: number;
  memory: number;
  agentName: string;
}

export function ContainerManagement() {
  const { isAdmin } = useAuth();
  const [selectedContainer, setSelectedContainer] = useState<string | null>(null);
  const [logs] = useState<string[]>([
    '[2025-11-01 12:45:23] Container started successfully',
    '[2025-11-01 12:45:24] Initializing AI agent...',
    '[2025-11-01 12:45:25] Loading model weights...',
    '[2025-11-01 12:45:26] Model loaded successfully',
    '[2025-11-01 12:45:27] Connecting to game server...',
    '[2025-11-01 12:45:28] Connection established',
    '[2025-11-01 12:45:30] Ready to process game states',
    '[2025-11-01 12:46:15] Processing game #12345',
    '[2025-11-01 12:46:16] Move calculated: (5, 7)',
    '[2025-11-01 12:46:17] Game #12345 completed - Victory!',
  ]);

  const containers: Container[] = [
    { id: 'cont_1', name: 'alphabot-v1-2', status: 'running', image: 'python:3.11-slim', created: '2025-11-01 10:30', uptime: '2h 15m', cpu: 45.2, memory: 512, agentName: 'AlphaBot v1.2' },
    { id: 'cont_2', name: 'betaai-v2-0', status: 'running', image: 'node:20-alpine', created: '2025-11-01 09:15', uptime: '3h 30m', cpu: 32.8, memory: 384, agentName: 'BetaAI v2.0' },
    { id: 'cont_3', name: 'gammanet-v1-5', status: 'running', image: 'python:3.11-slim', created: '2025-11-01 11:00', uptime: '1h 45m', cpu: 67.5, memory: 768, agentName: 'GammaNet v1.5' },
    { id: 'cont_4', name: 'deltabot-v1-0', status: 'stopped', image: 'python:3.10', created: '2025-10-31 14:20', uptime: '-', cpu: 0, memory: 0, agentName: 'DeltaBot v1.0' },
    { id: 'cont_5', name: 'epsilonai-v3-1', status: 'error', image: 'node:18-alpine', created: '2025-11-01 12:00', uptime: '-', cpu: 0, memory: 0, agentName: 'EpsilonAI v3.1' },
  ];

  const getStatusColor = (status: Container['status']) => {
    const colors = { running: 'success' as const, stopped: 'default' as const, error: 'error' as const };
    return colors[status];
  };

  if (!isAdmin) {
    return (
      <Container maxWidth="lg" sx={{ py: 8, textAlign: 'center' }}>
        <Lock sx={{ fontSize: 64, mb: 2, color: 'error.main' }} />
        <Typography variant="h4" gutterBottom>Access Denied</Typography>
        <Typography color="text.secondary">You need admin privileges to access this page</Typography>
      </Container>
    );
  }

  const runningCount = containers.filter(c => c.status === 'running').length;
  const stoppedCount = containers.filter(c => c.status === 'stopped').length;
  const errorCount = containers.filter(c => c.status === 'error').length;

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Storage /> Container Management
        </Typography>
        <Typography color="text.secondary">Monitor and manage Docker containers for AI agents</Typography>
      </Box>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' }, gap: 2, mb: 4 }}>
        <Card><CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}><Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#10b981' }} /><Box><Typography variant="h4">{runningCount}</Typography><Typography variant="body2" color="text.secondary">Running</Typography></Box></CardContent></Card>
        <Card><CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}><Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#888' }} /><Box><Typography variant="h4">{stoppedCount}</Typography><Typography variant="body2" color="text.secondary">Stopped</Typography></Box></CardContent></Card>
        <Card><CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}><Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#ef4444' }} /><Box><Typography variant="h4">{errorCount}</Typography><Typography variant="body2" color="text.secondary">Error</Typography></Box></CardContent></Card>
      </Box>
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Active Containers</Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow><TableCell>Status</TableCell><TableCell>Container Name</TableCell><TableCell>Agent</TableCell><TableCell>Image</TableCell><TableCell>Created</TableCell><TableCell>Uptime</TableCell><TableCell>CPU %</TableCell><TableCell>Memory (MB)</TableCell><TableCell>Actions</TableCell></TableRow>
              </TableHead>
              <TableBody>
                {containers.map((container) => (
                  <TableRow key={container.id}>
                    <TableCell><Chip label={container.status} color={getStatusColor(container.status)} size="small" sx={{ borderRadius: 0 }} /></TableCell>
                    <TableCell><Typography component="code" sx={{ fontSize: '0.875rem', backgroundColor: '#333', px: 1, py: 0.5, borderRadius: 0 }}>{container.name}</Typography></TableCell>
                    <TableCell>{container.agentName}</TableCell>
                    <TableCell><Typography component="code" sx={{ fontSize: '0.875rem', backgroundColor: '#333', px: 1, py: 0.5, borderRadius: 0 }}>{container.image}</Typography></TableCell>
                    <TableCell>{container.created}</TableCell>
                    <TableCell>{container.uptime}</TableCell>
                    <TableCell><Typography color={container.cpu > 50 ? 'error' : 'inherit'}>{container.cpu}%</Typography></TableCell>
                    <TableCell><Typography color={container.memory > 500 ? 'error' : 'inherit'}>{container.memory}</Typography></TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Button variant="gradientBorder" size="small" onClick={() => setSelectedContainer(container.id)}>Logs</Button>
                        {container.status === 'running' && <><Button variant="gradientBorder" size="small"><Refresh fontSize="small" /></Button><Button variant="gradientBorder" size="small" color="error"><Stop fontSize="small" /></Button></>}
                        {container.status === 'stopped' && <Button variant="gradientBorder" size="small" color="success"><PlayArrow fontSize="small" /></Button>}
                        {container.status === 'error' && <Button variant="gradientBorder" size="small" color="error"><Delete fontSize="small" /></Button>}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
      {selectedContainer && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Article /> Container Logs
              </Typography>
              <Button startIcon={<Close />} onClick={() => setSelectedContainer(null)} size="small">Close</Button>
            </Box>
            <Box sx={{ backgroundColor: '#0a0a0a', p: 2, borderRadius: 0, maxHeight: 300, overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.875rem' }}>
              {logs.map((log, index) => (
                <Box key={index} sx={{ mb: 0.5 }}>{log}</Box>
              ))}
            </Box>
            <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
              <Button variant="gradientBorder" size="small">Download Logs</Button>
              <Button variant="gradientBorder" size="small">Clear</Button>
              <Button variant="gradientBorder" size="small">Refresh</Button>
            </Box>
          </CardContent>
        </Card>
      )}
    </Container>
  );
}
