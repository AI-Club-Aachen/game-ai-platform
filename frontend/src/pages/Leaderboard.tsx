import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getGameById, getActiveGames } from '../config/games';
import './Leaderboard.css';

interface LeaderboardEntry {
  rank: number;
  username: string;
  agentName: string;
  score: number;
  wins: number;
  losses: number;
  winRate: number;
  language: string;
  gameId: string;
}

export function Leaderboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedGame, setSelectedGame] = useState<string>(searchParams.get('game') || 'chess');
  const activeGames = getActiveGames();

  useEffect(() => {
    const gameParam = searchParams.get('game');
    if (gameParam) {
      setSelectedGame(gameParam);
    }
  }, [searchParams]);

  const handleGameChange = (gameId: string) => {
    setSelectedGame(gameId);
    setSearchParams({ game: gameId });
  };

  // Mock leaderboard data - would be filtered by game in real implementation
  // Mock leaderboard data - would be filtered by game in real implementation
  const entries: LeaderboardEntry[] = [
    { rank: 1, username: 'AImaster', agentName: 'GammaNet', score: 2450, wins: 52, losses: 8, winRate: 86.7, language: 'Python', gameId: selectedGame },
    { rank: 2, username: 'BotBuilder', agentName: 'DeepMind', score: 2380, wins: 48, losses: 10, winRate: 82.8, language: 'Python', gameId: selectedGame },
    { rank: 3, username: 'demo_user', agentName: 'AlphaBot', score: 2250, wins: 45, losses: 12, winRate: 78.9, language: 'Python', gameId: selectedGame },
    { rank: 4, username: 'CodeNinja', agentName: 'SwiftAI', score: 2180, wins: 42, losses: 15, winRate: 73.7, language: 'JavaScript', gameId: selectedGame },
    { rank: 5, username: 'MLEngineer', agentName: 'TensorBot', score: 2140, wins: 40, losses: 16, winRate: 71.4, language: 'Python', gameId: selectedGame },
    { rank: 6, username: 'GameDev', agentName: 'StrategyX', score: 2090, wins: 39, losses: 18, winRate: 68.4, language: 'TypeScript', gameId: selectedGame },
    { rank: 7, username: 'RoboticsExpert', agentName: 'BetaAI', score: 2020, wins: 38, losses: 19, winRate: 66.7, language: 'JavaScript', gameId: selectedGame },
    { rank: 8, username: 'Competitor', agentName: 'AlgoMaster', score: 1980, wins: 35, losses: 20, winRate: 63.6, language: 'Python', gameId: selectedGame },
    { rank: 9, username: 'NewPlayer', agentName: 'FirstBot', score: 1920, wins: 32, losses: 23, winRate: 58.2, language: 'JavaScript', gameId: selectedGame },
    { rank: 10, username: 'Learner', agentName: 'BasicAI', score: 1850, wins: 28, losses: 27, winRate: 50.9, language: 'Python', gameId: selectedGame },
  ];

  const getRankBadge = (rank: number) => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return `#${rank}`;
  };

  const currentGame = getGameById(selectedGame);

  return (
    <div className="leaderboard-page">
      <div className="leaderboard-header">
        <h1>🏆 Leaderboard</h1>
        <p>Top performing AI agents for {currentGame?.name || 'this game'}</p>
      </div>

      <div className="game-selector">
        <label>Select Game:</label>
        <div className="game-tabs">
          {activeGames.map((game) => (
            <button
              key={game.id}
              className={selectedGame === game.id ? 'active' : ''}
              onClick={() => handleGameChange(game.id)}
            >
              {game.icon} {game.name}
            </button>
          ))}
        </div>
      </div>

      <div className="leaderboard-table-container">
        <table className="leaderboard-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>User</th>
              <th>Agent</th>
              <th>Language</th>
              <th>Score</th>
              <th>Wins</th>
              <th>Losses</th>
              <th>Win Rate</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.rank} className={entry.rank <= 3 ? 'top-three' : ''}>
                <td>
                  <span className="rank-badge">{getRankBadge(entry.rank)}</span>
                </td>
                <td>
                  <strong>{entry.username}</strong>
                </td>
                <td>
                  <span className="agent-name">{entry.agentName}</span>
                </td>
                <td>
                  <span className="language-tag">{entry.language}</span>
                </td>
                <td>
                  <span className="score">{entry.score}</span>
                </td>
                <td className="wins">{entry.wins}</td>
                <td className="losses">{entry.losses}</td>
                <td>
                  <div className="win-rate">
                    <div className="win-rate-bar">
                      <div
                        className="win-rate-fill"
                        style={{ width: `${entry.winRate}%` }}
                      ></div>
                    </div>
                    <span>{entry.winRate.toFixed(1)}%</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
