import { useState } from 'react';
import './PastGames.css';

interface PastGame {
  id: string;
  player1: {
    name: string;
    agent: string;
    score: number;
  };
  player2: {
    name: string;
    agent: string;
    score: number;
  };
  winner: string;
  gameType: string;
  playedAt: string;
  duration: string;
  rounds: number;
}

export function PastGames() {
  const [filter, setFilter] = useState<'all' | 'wins' | 'losses'>('all');
  const [selectedGame, setSelectedGame] = useState<string | null>(null);

  // Mock past games data
  const pastGames: PastGame[] = [
    {
      id: 'past_1',
      player1: { name: 'AImaster', agent: 'GammaNet v1.5', score: 50 },
      player2: { name: 'BotBuilder', agent: 'DeepMind v2.0', score: 45 },
      winner: 'AImaster',
      gameType: 'Chess AI',
      playedAt: '2025-11-01 10:30',
      duration: '15m 32s',
      rounds: 50,
    },
    {
      id: 'past_2',
      player1: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 42 },
      player2: { name: 'CodeNinja', agent: 'SwiftAI v3.0', score: 48 },
      winner: 'CodeNinja',
      gameType: 'Strategy Game',
      playedAt: '2025-11-01 09:15',
      duration: '22m 18s',
      rounds: 100,
    },
    {
      id: 'past_3',
      player1: { name: 'MLEngineer', agent: 'TensorBot v1.0', score: 25 },
      player2: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 28 },
      winner: 'demo_user',
      gameType: 'RTS Battle',
      playedAt: '2025-10-31 18:45',
      duration: '18m 05s',
      rounds: 30,
    },
    {
      id: 'past_4',
      player1: { name: 'GameDev', agent: 'StrategyX v2.1', score: 38 },
      player2: { name: 'demo_user', agent: 'AlphaBot v1.1', score: 35 },
      winner: 'GameDev',
      gameType: 'Strategy Game',
      playedAt: '2025-10-31 14:20',
      duration: '25m 42s',
      rounds: 100,
    },
    {
      id: 'past_5',
      player1: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 48 },
      player2: { name: 'Competitor', agent: 'AlgoMaster v1.0', score: 40 },
      winner: 'demo_user',
      gameType: 'Chess AI',
      playedAt: '2025-10-30 16:00',
      duration: '12m 55s',
      rounds: 50,
    },
  ];

  const filteredGames = pastGames.filter((game) => {
    if (filter === 'all') return true;
    if (filter === 'wins') return game.winner === 'demo_user';
    if (filter === 'losses') return game.winner !== 'demo_user';
    return true;
  });

  const selectedGameData = pastGames.find(g => g.id === selectedGame);

  return (
    <div className="past-games-page">
      <div className="page-header">
        <h1>📜 Past Games</h1>
        <p>Review and analyze previous matches</p>
      </div>

      {!selectedGame ? (
        <>
          <div className="filter-controls">
            <button
              className={filter === 'all' ? 'active' : ''}
              onClick={() => setFilter('all')}
            >
              All Games
            </button>
            <button
              className={filter === 'wins' ? 'active' : ''}
              onClick={() => setFilter('wins')}
            >
              My Wins
            </button>
            <button
              className={filter === 'losses' ? 'active' : ''}
              onClick={() => setFilter('losses')}
            >
              My Losses
            </button>
          </div>

          <div className="games-table-container">
            <table className="games-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Game Type</th>
                  <th>Player 1</th>
                  <th>Score</th>
                  <th>Player 2</th>
                  <th>Winner</th>
                  <th>Duration</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredGames.map((game) => (
                  <tr key={game.id}>
                    <td>{game.playedAt}</td>
                    <td>
                      <span className="game-type-tag">{game.gameType}</span>
                    </td>
                    <td>
                      <div className="player-cell">
                        <strong>{game.player1.name}</strong>
                        <div className="agent-name-small">{game.player1.agent}</div>
                      </div>
                    </td>
                    <td>
                      <span className="score-display">
                        {game.player1.score} - {game.player2.score}
                      </span>
                    </td>
                    <td>
                      <div className="player-cell">
                        <strong>{game.player2.name}</strong>
                        <div className="agent-name-small">{game.player2.agent}</div>
                      </div>
                    </td>
                    <td>
                      <span
                        className={`winner-badge ${
                          game.winner === 'demo_user' ? 'win' : 'loss'
                        }`}
                      >
                        {game.winner === 'demo_user' ? '🏆' : ''} {game.winner}
                      </span>
                    </td>
                    <td>{game.duration}</td>
                    <td>
                      <button
                        className="btn-replay"
                        onClick={() => setSelectedGame(game.id)}
                      >
                        Replay
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="replay-view">
          <button
            className="btn-back"
            onClick={() => setSelectedGame(null)}
          >
            ← Back to Past Games
          </button>

          <div className="replay-viewer">
            <div className="replay-header">
              <div className="replay-info">
                <h2>Game Replay</h2>
                <p>{selectedGameData?.gameType} - {selectedGameData?.playedAt}</p>
              </div>
              <div className="replay-result">
                <span className="winner-large">
                  Winner: {selectedGameData?.winner}
                </span>
                <span className="duration">
                  Duration: {selectedGameData?.duration}
                </span>
              </div>
            </div>

            <div className="replay-players">
              <div className="replay-player">
                <h3>{selectedGameData?.player1.name}</h3>
                <p>{selectedGameData?.player1.agent}</p>
                <div className="final-score">{selectedGameData?.player1.score}</div>
              </div>
              <div className="vs-divider">VS</div>
              <div className="replay-player">
                <h3>{selectedGameData?.player2.name}</h3>
                <p>{selectedGameData?.player2.agent}</p>
                <div className="final-score">{selectedGameData?.player2.score}</div>
              </div>
            </div>

            <div className="replay-canvas">
              <div className="canvas-placeholder">
                <div className="replay-message">
                  <h3>🎬 Game Replay</h3>
                  <p>Use controls below to navigate through the game</p>
                  <div className="replay-controls">
                    <button className="control-btn">⏮️</button>
                    <button className="control-btn play">▶️</button>
                    <button className="control-btn">⏭️</button>
                  </div>
                  <div className="timeline">
                    <input type="range" min="0" max={selectedGameData?.rounds} defaultValue="0" />
                    <div className="timeline-labels">
                      <span>Round 0</span>
                      <span>Round {selectedGameData?.rounds}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="replay-stats">
              <div className="stat-card">
                <div className="stat-title">Total Rounds</div>
                <div className="stat-number">{selectedGameData?.rounds}</div>
              </div>
              <div className="stat-card">
                <div className="stat-title">Final Score</div>
                <div className="stat-number">
                  {selectedGameData?.player1.score} - {selectedGameData?.player2.score}
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-title">Game Duration</div>
                <div className="stat-number">{selectedGameData?.duration}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
