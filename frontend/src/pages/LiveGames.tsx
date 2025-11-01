import { useState } from 'react';
import './LiveGames.css';

interface LiveGame {
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
  gameType: string;
  startedAt: string;
  viewers: number;
  round: number;
  maxRounds: number;
}

export function LiveGames() {
  const [selectedGame, setSelectedGame] = useState<string | null>(null);

  // Mock live games data
  const liveGames: LiveGame[] = [
    {
      id: 'game_1',
      player1: { name: 'AImaster', agent: 'GammaNet v1.5', score: 45 },
      player2: { name: 'BotBuilder', agent: 'DeepMind v2.0', score: 42 },
      gameType: 'Chess AI',
      startedAt: '10 min ago',
      viewers: 127,
      round: 15,
      maxRounds: 50,
    },
    {
      id: 'game_2',
      player1: { name: 'demo_user', agent: 'AlphaBot v1.2', score: 38 },
      player2: { name: 'CodeNinja', agent: 'SwiftAI v3.0', score: 35 },
      gameType: 'Strategy Game',
      startedAt: '5 min ago',
      viewers: 89,
      round: 22,
      maxRounds: 100,
    },
    {
      id: 'game_3',
      player1: { name: 'MLEngineer', agent: 'TensorBot v1.0', score: 15 },
      player2: { name: 'GameDev', agent: 'StrategyX v2.1', score: 18 },
      gameType: 'RTS Battle',
      startedAt: '2 min ago',
      viewers: 52,
      round: 8,
      maxRounds: 30,
    },
  ];

  const selectedGameData = liveGames.find(g => g.id === selectedGame);

  return (
    <div className="live-games-page">
      <div className="page-header">
        <h1>🔴 Live Games</h1>
        <p>Watch AI agents compete in real-time</p>
      </div>

      {!selectedGame ? (
        <>
          <div className="live-indicator">
            <span className="pulse"></span>
            <span>{liveGames.length} games currently in progress</span>
          </div>

          <div className="games-grid">
            {liveGames.map((game) => (
              <div key={game.id} className="game-card">
                <div className="game-header">
                  <span className="game-type">{game.gameType}</span>
                  <span className="viewers">👁️ {game.viewers}</span>
                </div>

                <div className="players-section">
                  <div className="player player1">
                    <div className="player-info">
                      <div className="player-name">{game.player1.name}</div>
                      <div className="agent-name">{game.player1.agent}</div>
                    </div>
                    <div className="player-score">{game.player1.score}</div>
                  </div>

                  <div className="vs-divider">VS</div>

                  <div className="player player2">
                    <div className="player-score">{game.player2.score}</div>
                    <div className="player-info">
                      <div className="player-name">{game.player2.name}</div>
                      <div className="agent-name">{game.player2.agent}</div>
                    </div>
                  </div>
                </div>

                <div className="game-progress">
                  <div className="progress-info">
                    <span>Round {game.round} / {game.maxRounds}</span>
                    <span>{game.startedAt}</span>
                  </div>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${(game.round / game.maxRounds) * 100}%` }}
                    ></div>
                  </div>
                </div>

                <button
                  className="btn-watch"
                  onClick={() => setSelectedGame(game.id)}
                >
                  Watch Game
                </button>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="spectator-view">
          <button
            className="btn-back"
            onClick={() => setSelectedGame(null)}
          >
            ← Back to Live Games
          </button>

          <div className="game-viewer">
            <div className="viewer-header">
              <div className="player-info-header">
                <div className="player-details">
                  <h3>{selectedGameData?.player1.name}</h3>
                  <p>{selectedGameData?.player1.agent}</p>
                  <div className="score-large">{selectedGameData?.player1.score}</div>
                </div>
                <div className="vs-large">VS</div>
                <div className="player-details">
                  <h3>{selectedGameData?.player2.name}</h3>
                  <p>{selectedGameData?.player2.agent}</p>
                  <div className="score-large">{selectedGameData?.player2.score}</div>
                </div>
              </div>
            </div>

            <div className="game-canvas">
              <div className="canvas-placeholder">
                <div className="game-board">
                  <div className="board-message">
                    <h2>🎮 Game Visualization</h2>
                    <p>Round {selectedGameData?.round} of {selectedGameData?.maxRounds}</p>
                    <p className="live-badge">🔴 LIVE</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="game-stats">
              <div className="stat-box">
                <div className="stat-label">Game Type</div>
                <div className="stat-value">{selectedGameData?.gameType}</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">Started</div>
                <div className="stat-value">{selectedGameData?.startedAt}</div>
              </div>
              <div className="stat-box">
                <div className="stat-label">Viewers</div>
                <div className="stat-value">👁️ {selectedGameData?.viewers}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
