import { useState } from 'react';
import './Tournaments.css';

interface Tournament {
  id: string;
  name: string;
  status: 'upcoming' | 'active' | 'completed';
  participants: number;
  maxParticipants: number;
  prizePool: string;
  startDate: string;
  endDate: string;
  format: string;
}

export function Tournaments() {
  const [filter, setFilter] = useState<'all' | 'upcoming' | 'active' | 'completed'>('all');

  // Mock tournament data
  const tournaments: Tournament[] = [
    {
      id: '1',
      name: 'Fall Championship 2025',
      status: 'active',
      participants: 48,
      maxParticipants: 64,
      prizePool: '$5,000',
      startDate: '2025-11-01',
      endDate: '2025-11-15',
      format: 'Single Elimination',
    },
    {
      id: '2',
      name: 'Winter League Qualifiers',
      status: 'upcoming',
      participants: 32,
      maxParticipants: 128,
      prizePool: '$10,000',
      startDate: '2025-12-01',
      endDate: '2025-12-20',
      format: 'Round Robin',
    },
    {
      id: '3',
      name: 'Quick Match Tournament',
      status: 'upcoming',
      participants: 12,
      maxParticipants: 32,
      prizePool: '$1,000',
      startDate: '2025-11-10',
      endDate: '2025-11-11',
      format: 'Double Elimination',
    },
    {
      id: '4',
      name: 'October Masters',
      status: 'completed',
      participants: 64,
      maxParticipants: 64,
      prizePool: '$3,000',
      startDate: '2025-10-01',
      endDate: '2025-10-20',
      format: 'Swiss System',
    },
    {
      id: '5',
      name: 'Summer Championship',
      status: 'completed',
      participants: 128,
      maxParticipants: 128,
      prizePool: '$15,000',
      startDate: '2025-08-01',
      endDate: '2025-08-31',
      format: 'Single Elimination',
    },
  ];

  const filteredTournaments = tournaments.filter(
    t => filter === 'all' || t.status === filter
  );

  const getStatusBadge = (status: Tournament['status']) => {
    const badges = {
      upcoming: { emoji: '📅', class: 'status-upcoming' },
      active: { emoji: '🔴', class: 'status-active' },
      completed: { emoji: '✅', class: 'status-completed' },
    };
    return badges[status];
  };

  return (
    <div className="tournaments-page">
      <div className="tournaments-header">
        <h1>🏆 Tournaments</h1>
        <p>Compete with the best AI agents in competitive tournaments</p>
      </div>

      <div className="tournaments-controls">
        <div className="filter-buttons">
          <button
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All Tournaments
          </button>
          <button
            className={filter === 'upcoming' ? 'active' : ''}
            onClick={() => setFilter('upcoming')}
          >
            Upcoming
          </button>
          <button
            className={filter === 'active' ? 'active' : ''}
            onClick={() => setFilter('active')}
          >
            Active
          </button>
          <button
            className={filter === 'completed' ? 'active' : ''}
            onClick={() => setFilter('completed')}
          >
            Completed
          </button>
        </div>
      </div>

      <div className="tournaments-grid">
        {filteredTournaments.map((tournament) => {
          const badge = getStatusBadge(tournament.status);
          const participationRate = (tournament.participants / tournament.maxParticipants) * 100;

          return (
            <div key={tournament.id} className="tournament-card">
              <div className="tournament-header">
                <h3>{tournament.name}</h3>
                <span className={`status-badge ${badge.class}`}>
                  {badge.emoji} {tournament.status}
                </span>
              </div>

              <div className="tournament-details">
                <div className="detail-row">
                  <span className="label">Format:</span>
                  <span className="value">{tournament.format}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Prize Pool:</span>
                  <span className="value prize">{tournament.prizePool}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Dates:</span>
                  <span className="value">
                    {tournament.startDate} - {tournament.endDate}
                  </span>
                </div>
              </div>

              <div className="participants-section">
                <div className="participants-header">
                  <span>Participants</span>
                  <span>
                    {tournament.participants} / {tournament.maxParticipants}
                  </span>
                </div>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${participationRate}%` }}
                  ></div>
                </div>
              </div>

              <div className="tournament-actions">
                {tournament.status === 'upcoming' && (
                  <button className="btn-primary">Register</button>
                )}
                {tournament.status === 'active' && (
                  <button className="btn-secondary">View Bracket</button>
                )}
                {tournament.status === 'completed' && (
                  <button className="btn-secondary">View Results</button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
