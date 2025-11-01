import { useAuth } from '../context/AuthContext';
import './Dashboard.css';

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

  if (!user) {
    return (
      <div className="dashboard">
        <div className="not-logged-in">
          <h2>Please log in to view your dashboard</h2>
          <p>Use the login buttons in the navigation to continue</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>{isAdmin ? '👑 Admin Dashboard' : '📊 User Dashboard'}</h1>
        <p>Welcome back, {user.username}!</p>
      </div>

      <div className="dashboard-grid">
        {/* Submissions Section */}
        <section className="dashboard-card">
          <h2>📤 Recent Submissions</h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Agent Name</th>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Submitted</th>
                  <th>Score</th>
                  {isAdmin && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {submissions.map(sub => (
                  <tr key={sub.id}>
                    <td>{sub.agentName}</td>
                    <td><code>{sub.version}</code></td>
                    <td>
                      <span className={`status status-${sub.status}`}>
                        {sub.status}
                      </span>
                    </td>
                    <td>{sub.submittedAt}</td>
                    <td>{sub.score || '-'}</td>
                    {isAdmin && (
                      <td>
                        <button className="btn-small">Review</button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button className="btn-primary">+ New Submission</button>
        </section>

        {/* Agent Tracking Section */}
        <section className="dashboard-card">
          <h2>🤖 Agent Tracking</h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Language</th>
                  <th>W/L</th>
                  <th>Rank</th>
                  <th>Last Active</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {agents.map(agent => (
                  <tr key={agent.id}>
                    <td><strong>{agent.name}</strong></td>
                    <td>{agent.language}</td>
                    <td>
                      <span className="win-loss">
                        {agent.wins}W / {agent.losses}L
                      </span>
                    </td>
                    <td>
                      <span className="rank">#{agent.rank}</span>
                    </td>
                    <td>{agent.lastActive}</td>
                    <td>
                      <button className="btn-small">View</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Stats Overview */}
        <section className="dashboard-card stats-card">
          <h2>📈 Quick Stats</h2>
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-value">3</div>
              <div className="stat-label">Active Agents</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">135</div>
              <div className="stat-label">Total Games</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">68%</div>
              <div className="stat-label">Win Rate</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">#3</div>
              <div className="stat-label">Best Rank</div>
            </div>
          </div>
        </section>

        {/* Admin Only Section */}
        {isAdmin && (
          <section className="dashboard-card admin-section">
            <h2>⚙️ Admin Controls</h2>
            <div className="admin-actions">
              <button className="btn-admin">Manage Users</button>
              <button className="btn-admin">Review Submissions</button>
              <button className="btn-admin">View System Logs</button>
              <button className="btn-admin">Configure Tournaments</button>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
