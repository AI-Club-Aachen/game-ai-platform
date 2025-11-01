import { Link } from 'react-router-dom';
import { GAMES, getActiveGames } from '../config/games';
import './Games.css';

export function Games() {
  const activeGames = getActiveGames();
  const inactiveGames = GAMES.filter(game => !game.active);

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return '#10b981';
      case 'medium': return '#f59e0b';
      case 'hard': return '#ef4444';
      default: return '#888';
    }
  };

  return (
    <div className="games-page">
      <div className="games-header">
        <h1>🎮 Available Games</h1>
        <p>Choose a game to compete in with your AI agents</p>
      </div>

      <section className="games-section">
        <h2>Active Games</h2>
        <div className="games-grid">
          {activeGames.map((game) => (
            <div key={game.id} className="game-card active">
              <div className="game-icon">{game.icon}</div>
              <h3>{game.name}</h3>
              <p className="game-description">{game.description}</p>
              
              <div className="game-meta">
                <div className="meta-item">
                  <span className="meta-label">Players:</span>
                  <span className="meta-value">
                    {game.minPlayers === game.maxPlayers 
                      ? game.maxPlayers 
                      : `${game.minPlayers}-${game.maxPlayers}`}
                  </span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Category:</span>
                  <span className="meta-value">{game.category}</span>
                </div>
                <div className="meta-item">
                  <span className="meta-label">Difficulty:</span>
                  <span 
                    className="difficulty-badge"
                    style={{ backgroundColor: `${getDifficultyColor(game.difficulty)}22`, color: getDifficultyColor(game.difficulty) }}
                  >
                    {game.difficulty}
                  </span>
                </div>
              </div>

              <div className="game-actions">
                <Link to={`/leaderboard?game=${game.id}`} className="btn-secondary">
                  Leaderboard
                </Link>
                <Link to={`/games/live?game=${game.id}`} className="btn-primary">
                  Watch Live
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      {inactiveGames.length > 0 && (
        <section className="games-section">
          <h2>Coming Soon</h2>
          <div className="games-grid">
            {inactiveGames.map((game) => (
              <div key={game.id} className="game-card inactive">
                <div className="game-icon">{game.icon}</div>
                <h3>{game.name}</h3>
                <p className="game-description">{game.description}</p>
                
                <div className="game-meta">
                  <div className="meta-item">
                    <span className="meta-label">Players:</span>
                    <span className="meta-value">
                      {game.minPlayers === game.maxPlayers 
                        ? game.maxPlayers 
                        : `${game.minPlayers}-${game.maxPlayers}`}
                    </span>
                  </div>
                  <div className="meta-item">
                    <span className="meta-label">Category:</span>
                    <span className="meta-value">{game.category}</span>
                  </div>
                  <div className="meta-item">
                    <span className="meta-label">Difficulty:</span>
                    <span 
                      className="difficulty-badge"
                      style={{ backgroundColor: `${getDifficultyColor(game.difficulty)}22`, color: getDifficultyColor(game.difficulty) }}
                    >
                      {game.difficulty}
                    </span>
                  </div>
                </div>

                <div className="coming-soon-badge">
                  Coming Soon
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
