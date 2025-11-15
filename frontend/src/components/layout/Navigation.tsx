import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { SportsEsports } from '@mui/icons-material';
import './Navigation.css';

export function Navigation() {
  const { user, isAdmin, login, logout } = useAuth();

  return (
    <nav className="navigation">
      <div className="nav-container">
        <Link to="/home" className="nav-logo" style={{ 
          background: 'linear-gradient(90deg, #00D98B 0%, #00A6FF 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <SportsEsports style={{ fontSize: '2rem', color: '#00A6FF' }} />
          <h2>AICA Game Platform</h2>
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
