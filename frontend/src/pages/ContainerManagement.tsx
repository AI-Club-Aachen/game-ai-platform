import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import './ContainerManagement.css';

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
  const [logs, setLogs] = useState<string[]>([]);

  // Mock container data
  const containers: Container[] = [
    {
      id: 'cont_1',
      name: 'alphabot-v1-2',
      status: 'running',
      image: 'python:3.11-slim',
      created: '2025-11-01 10:30',
      uptime: '2h 15m',
      cpu: 45.2,
      memory: 512,
      agentName: 'AlphaBot v1.2',
    },
    {
      id: 'cont_2',
      name: 'betaai-v2-0',
      status: 'running',
      image: 'node:20-alpine',
      created: '2025-11-01 09:15',
      uptime: '3h 30m',
      cpu: 32.8,
      memory: 384,
      agentName: 'BetaAI v2.0',
    },
    {
      id: 'cont_3',
      name: 'gammanet-v1-5',
      status: 'running',
      image: 'python:3.11-slim',
      created: '2025-11-01 11:00',
      uptime: '1h 45m',
      cpu: 67.5,
      memory: 768,
      agentName: 'GammaNet v1.5',
    },
    {
      id: 'cont_4',
      name: 'deltabot-v1-0',
      status: 'stopped',
      image: 'python:3.10',
      created: '2025-10-31 14:20',
      uptime: '-',
      cpu: 0,
      memory: 0,
      agentName: 'DeltaBot v1.0',
    },
    {
      id: 'cont_5',
      name: 'epsilonai-v3-1',
      status: 'error',
      image: 'node:18-alpine',
      created: '2025-11-01 12:00',
      uptime: '-',
      cpu: 0,
      memory: 0,
      agentName: 'EpsilonAI v3.1',
    },
  ];

  // Mock logs
  const mockLogs = [
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
  ];

  const handleViewLogs = (containerId: string) => {
    setSelectedContainer(containerId);
    setLogs(mockLogs);
  };

  const getStatusColor = (status: Container['status']) => {
    const colors = {
      running: '#10b981',
      stopped: '#888',
      error: '#ef4444',
    };
    return colors[status];
  };

  if (!isAdmin) {
    return (
      <div className="container-management">
        <div className="access-denied">
          <h2>🔒 Access Denied</h2>
          <p>You need admin privileges to access this page</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container-management">
      <div className="page-header">
        <h1>🐳 Container Management</h1>
        <p>Monitor and manage Docker containers for AI agents</p>
      </div>

      <div className="container-stats">
        <div className="stat-card">
          <div className="stat-icon running">●</div>
          <div className="stat-info">
            <div className="stat-value">3</div>
            <div className="stat-label">Running</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon stopped">●</div>
          <div className="stat-info">
            <div className="stat-value">1</div>
            <div className="stat-label">Stopped</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon error">●</div>
          <div className="stat-info">
            <div className="stat-value">1</div>
            <div className="stat-label">Error</div>
          </div>
        </div>
      </div>

      <div className="containers-table-section">
        <h2>Active Containers</h2>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Container Name</th>
                <th>Agent</th>
                <th>Image</th>
                <th>Created</th>
                <th>Uptime</th>
                <th>CPU %</th>
                <th>Memory (MB)</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {containers.map((container) => (
                <tr key={container.id}>
                  <td>
                    <span
                      className="status-indicator"
                      style={{ color: getStatusColor(container.status) }}
                    >
                      ● {container.status}
                    </span>
                  </td>
                  <td>
                    <code>{container.name}</code>
                  </td>
                  <td>{container.agentName}</td>
                  <td>
                    <code className="image-tag">{container.image}</code>
                  </td>
                  <td>{container.created}</td>
                  <td>{container.uptime}</td>
                  <td>
                    <span className={container.cpu > 50 ? 'high-usage' : ''}>
                      {container.cpu}%
                    </span>
                  </td>
                  <td>
                    <span className={container.memory > 500 ? 'high-usage' : ''}>
                      {container.memory}
                    </span>
                  </td>
                  <td>
                    <div className="action-buttons">
                      <button
                        className="btn-small btn-logs"
                        onClick={() => handleViewLogs(container.id)}
                      >
                        Logs
                      </button>
                      {container.status === 'running' && (
                        <>
                          <button className="btn-small btn-restart">↻</button>
                          <button className="btn-small btn-stop">■</button>
                        </>
                      )}
                      {container.status === 'stopped' && (
                        <button className="btn-small btn-start">▶</button>
                      )}
                      {container.status === 'error' && (
                        <button className="btn-small btn-delete">×</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selectedContainer && (
        <div className="logs-section">
          <div className="logs-header">
            <h2>📋 Container Logs</h2>
            <button
              className="btn-close"
              onClick={() => setSelectedContainer(null)}
            >
              ×
            </button>
          </div>
          <div className="logs-container">
            {logs.map((log, index) => (
              <div key={index} className="log-entry">
                {log}
              </div>
            ))}
          </div>
          <div className="logs-actions">
            <button className="btn-secondary">Download Logs</button>
            <button className="btn-secondary">Clear</button>
            <button className="btn-secondary">Refresh</button>
          </div>
        </div>
      )}
    </div>
  );
}
