import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './Navigation.css';

export function Navigation() {
  const { user, isAdmin, login, logout } = useAuth();

  return (
    <nav className="navigation">
      <div className="nav-container">
        <Link to="/" className="nav-logo">
          <h2>🎮 Game AI Platform</h2>
        </Link>
        
        <div className="nav-links">
          <Link to="/games">Games</Link>
          <Link to="/leaderboard">Leaderboard</Link>
          <Link to="/tournaments">Tournaments</Link>
          <Link to="/games/live">Live Games</Link>
          <Link to="/games/past">Past Games</Link>
          
          {user && (
            <>
              {isAdmin && (
                <div className="admin-dropdown">
                  <button className="admin-dropdown-trigger">
                    Administration <span className="dropdown-arrow">▼</span>
                  </button>
                  <div className="admin-dropdown-menu">
                    <Link to="/dashboard">
                      Dashboard
                    </Link>
                    <Link to="/containers">
                      Container Management
                    </Link>
                  </div>
                </div>
              )}
              {!isAdmin && <Link to="/dashboard">Dashboard</Link>}
            </>
          )}
        </div>

        <div className="nav-auth">
          {user ? (
            <div className="user-info">
              <span className="username">
                {user.username}
              </span>
              <button onClick={logout} className="btn-secondary">
                Logout
              </button>
            </div>
          ) : (
            <div className="login-buttons">
              <button onClick={() => login('demo_user', 'user')} className="btn-primary">
                Login as User
              </button>
              <button onClick={() => login('admin', 'admin')} className="btn-admin">
                Login as Admin
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
