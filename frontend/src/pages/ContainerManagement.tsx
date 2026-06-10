import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Box, Container, Typography, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination, Card, CardContent } from '@mui/material';
import { Close, Refresh, Lock, Storage, Article } from '@mui/icons-material';
import { palette, overlays } from '../theme';
import { containersApi } from '../services/api';
import { PrimarySecondaryCell, SmallBadge } from '../components/common/TableCells';
import { StatusIndicator } from '../components/common/StatusIndicator';

interface ContainerInfo {
  id: string;
  containerId: string;
  matchId: string | null;
  agentId: string;
  name: string;
  status: ContainerStatus;
  rawStatus: string;
  image: string;
  created: string;
  updated: string;
  updatedTitle: string;
  uptime: string;
  cpu: number;
  memory: number;
  agentName: string | null;
  logs: string;
}

type ContainerStatus = 'running' | 'stopped' | 'error';

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

const formatShortDateTime = (isoDate: string): string => {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return '-';
  }

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const normalizeStatus = (status: string): ContainerStatus => {
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

const formatStatusLabel = (status: string) => status
  .replace(/[_-]+/g, ' ')
  .replace(/\b\w/g, char => char.toUpperCase());

const isExceptionalStatus = (status: string) => {
  const normalized = status.toLowerCase();
  return ['error', 'failed', 'dead', 'restarting'].includes(normalized);
};

const shortId = (id?: string | null, length = 8) => {
  if (!id) return '—';
  return id.length > length ? `${id.slice(0, length)}…` : id;
};

export function ContainerManagement() {
  const { isAdmin } = useAuth();
  const [selectedContainer, setSelectedContainer] = useState<string | null>(null);
  const [containers, setContainers] = useState<ContainerInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Server-side pagination. The backend caps `limit` at 100 (SECURITY.md M-4)
  // and returns a paginated envelope; `total` and `statusCounts` cover the whole
  // fleet so the summary cards stay global while the table pages.
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [totalContainers, setTotalContainers] = useState(0);
  const [statusCounts, setStatusCounts] = useState<Record<string, number>>({});

  const loadContainers = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const response = await containersApi.getContainers({ skip: page * rowsPerPage, limit: rowsPerPage });
      setTotalContainers(response.total ?? 0);
      setStatusCounts(response.status_counts ?? {});
      const mapped: ContainerInfo[] = (response.data ?? []).map((item) => ({
        id: item.id,
        containerId: item.container_id,
        matchId: item.match_id,
        agentId: item.agent_id,
        name: item.name || shortId(item.container_id, 12),
        status: normalizeStatus(item.status.toLowerCase()),
        rawStatus: item.status,
        image: item.image,
        created: formatCreated(item.created_at),
        updated: formatShortDateTime(item.updated_at),
        updatedTitle: formatCreated(item.updated_at),
        uptime: formatUptime(item.uptime_seconds),
        cpu: Number(item.cpu_percent || 0),
        memory: Number(item.memory_mb || 0),
        agentName: item.agent_name,
        logs: item.logs || '',
      }));
      setContainers(mapped);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load containers';
      setFetchError(message);
    } finally {
      setIsLoading(false);
    }
  }, [page, rowsPerPage]);

  useEffect(() => {
    void loadContainers();
    const id = window.setInterval(() => {
      void loadContainers();
    }, 5000);

    return () => window.clearInterval(id);
  }, [loadContainers]);

  const handleChangePage = (_event: unknown, newPage: number) => setPage(newPage);

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Bucket the global per-status tallies into running/stopped/error using the
  // same mapping as the table, so the cards reflect the whole fleet, not the page.
  const { runningCount, stoppedCount, errorCount } = useMemo(() => {
    const totals = { runningCount: 0, stoppedCount: 0, errorCount: 0 };
    for (const [status, count] of Object.entries(statusCounts ?? {})) {
      const bucket = normalizeStatus(status.toLowerCase());
      if (bucket === 'running') totals.runningCount += count;
      else if (bucket === 'stopped') totals.stoppedCount += count;
      else totals.errorCount += count;
    }
    return totals;
  }, [statusCounts]);
  const selectedContainerEntry = useMemo(
    () => containers.find((container) => container.id === selectedContainer) || null,
    [containers, selectedContainer],
  );
  const selectedContainerLogs = useMemo(
    () => (selectedContainerEntry?.logs ? selectedContainerEntry.logs.split(/\r?\n/) : []),
    [selectedContainerEntry],
  );

  if (!isAdmin) {
    return (
      <Container maxWidth="lg" sx={{ py: 8, textAlign: 'center' }}>
        <Lock sx={{ fontSize: 56, mb: 2, color: 'error.main' }} />
        <Typography variant="h4" gutterBottom>Access Denied</Typography>
        <Typography color="text.secondary">You need admin privileges to access this page</Typography>
      </Container>
    );
  }

  const statusDotColor = (color: string) => ({
    width: 10,
    height: 10,
    borderRadius: '50%',
    backgroundColor: color,
    flexShrink: 0,
  });

  return (
    <Box sx={{ py: 4, width: '100%' }}>
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
          <TableContainer sx={{ overflowX: 'auto' }}>
            <Table sx={{ minWidth: 1180 }}>
              <TableHead>
                <TableRow>
                  <TableCell>Container</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Agent</TableCell>
                  <TableCell>Match</TableCell>
                  <TableCell>Image</TableCell>
                  <TableCell>Runtime</TableCell>
                  <TableCell>Resources</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {containers.map((container) => {
                  const cpuText = `${container.cpu.toFixed(1)}% CPU`;
                  const memoryText = `${Math.round(container.memory)} MB`;
                  const resourceWarning = container.cpu > 50 || container.memory > 500;

                  return (
                    <TableRow key={container.id}>
                      <TableCell>
                        <PrimarySecondaryCell
                          primary={container.name}
                          secondary={shortId(container.containerId, 12)}
                          badge={isExceptionalStatus(container.rawStatus) ? <SmallBadge label={formatStatusLabel(container.rawStatus)} color="error" /> : undefined}
                          title={container.containerId}
                        />
                      </TableCell>
                      <TableCell>
                        <StatusIndicator status={container.rawStatus} />
                      </TableCell>
                      <TableCell>
                        {container.agentName ? (
                          <PrimarySecondaryCell
                            primary={container.agentName}
                            secondary={shortId(container.agentId)}
                            title={container.agentId}
                          />
                        ) : (
                          <Typography
                            variant="body2"
                            title={container.agentId}
                            sx={{ fontFamily: 'monospace', color: 'text.secondary', whiteSpace: 'nowrap' }}
                          >
                            {shortId(container.agentId)}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          title={container.matchId ?? undefined}
                          sx={{ fontFamily: 'monospace', color: container.matchId ? 'text.secondary' : 'text.disabled', whiteSpace: 'nowrap' }}
                        >
                          {shortId(container.matchId)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography
                          component="code"
                          variant="body2"
                          title={container.image}
                          sx={{ display: 'block', maxWidth: 220, fontFamily: 'monospace', color: 'text.secondary', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                        >
                          {container.image}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <PrimarySecondaryCell
                          primary={container.uptime}
                          secondary={`Updated ${container.updated}`}
                          title={`Created: ${container.created}\nUpdated: ${container.updatedTitle}`}
                        />
                      </TableCell>
                      <TableCell>
                        <PrimarySecondaryCell
                          primary={
                            <Box component="span" sx={{ color: resourceWarning ? 'error.main' : 'text.primary' }}>
                              {cpuText} · {memoryText}
                            </Box>
                          }
                          secondary={resourceWarning ? 'High usage' : undefined}
                        />
                      </TableCell>
                      <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                        <Box sx={{ display: 'inline-flex', gap: 1 }}>
                          {container.status === 'running' && (
                            <Button
                              variant="outlined"
                              size="small"
                              color="error"
                              disabled
                              title="Stopping containers is not wired to an API endpoint yet"
                            >
                              Stop
                            </Button>
                          )}
                          <Button
                            variant="outlined"
                            size="small"
                            onClick={() => setSelectedContainer(container.id)}
                            disabled={!container.logs}
                          >
                            Logs
                          </Button>
                        </Box>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={totalContainers}
            page={page}
            onPageChange={handleChangePage}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={handleChangeRowsPerPage}
            rowsPerPageOptions={[5, 10, 25, 50, 100]}
          />
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
    </Box>
  );
}
