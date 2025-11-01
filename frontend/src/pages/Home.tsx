import { Link } from 'react-router-dom';
import './Home.css';

export function Home() {
  return (
    <div className="home-page">
      <section className="hero">
        <h1 className="hero-title">🎮 Game AI Platform</h1>
        <p className="hero-subtitle">
          Build, train, and compete with intelligent AI agents
        </p>
        <div className="hero-actions">
          <Link to="/dashboard" className="btn-primary-large">
            Get Started
          </Link>
          <Link to="/leaderboard" className="btn-secondary-large">
            View Leaderboard
          </Link>
        </div>
      </section>

      <section className="features">
        <div className="feature-grid">
          <div className="feature-card">
            <div className="feature-icon">🤖</div>
            <h3>Build AI Agents</h3>
            <p>Create and submit your AI agents using Python, JavaScript, or TypeScript</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🏆</div>
            <h3>Compete in Tournaments</h3>
            <p>Join tournaments and climb the leaderboard to prove your AI's superiority</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Track Performance</h3>
            <p>Monitor your agent's stats, win rates, and rankings in real-time</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔴</div>
            <h3>Watch Live Games</h3>
            <p>Spectate live matches and replay past games to learn strategies</p>
          </div>
        </div>
      </section>
    </div>
  );
}
