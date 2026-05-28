import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  SportsEsports,
  Dashboard as DashboardIcon,
  SportsEsportsOutlined,
  EmojiEvents,
  ManageAccounts,
  People,
  Person,
  ChevronLeft,
  Menu as MenuIcon,
  LightMode,
  DarkMode,
  Gavel,
  Policy,
  Cookie,
  Description
} from '@mui/icons-material';
import { useAppTheme } from '../../context/ThemeContext';
import './Sidebar.css';
import { legalLinks } from '../../pages/LegalPages';

interface SidebarProps {
  onToggle?: (collapsed: boolean) => void;
}

export function Sidebar({ onToggle }: SidebarProps) {
  const { user, isAdmin } = useAuth();
  const { mode, toggleTheme } = useAppTheme();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const toggleSidebar = () => {
    const newCollapsedState = !isCollapsed;
    setIsCollapsed(newCollapsedState);
    if (onToggle) {
      onToggle(newCollapsedState);
    }
  };

  useEffect(() => {
    if (onToggle) {
      onToggle(isCollapsed);
    }
  }, []);

  const legalIcons = [Gavel, Policy, Cookie, Description];

  return (
    <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <Link to="/dashboard" className="sidebar-logo">
          <img src="/favicon.svg" alt="AI Club Aachen logo" className="sidebar-logo-image" />
          {!isCollapsed && (
            <div className="sidebar-logo-text">
              <h2>Game AI Platform</h2>
            </div>
          )}
        </Link>
        <button className="sidebar-toggle" onClick={toggleSidebar}>
          {isCollapsed ? <MenuIcon /> : <ChevronLeft />}
        </button>
      </div>

      <nav className="sidebar-nav">
        <Link to="/dashboard" className="sidebar-link">
          <DashboardIcon />
          {!isCollapsed && <span>Dashboard</span>}
        </Link>

        <Link to="/games" className="sidebar-link">
          <SportsEsportsOutlined />
          {!isCollapsed && <span>Games</span>}
        </Link>

        <Link to="/tournaments" className="sidebar-link">
          <EmojiEvents />
          {!isCollapsed && <span>Tournaments</span>}
        </Link>

        {user && isAdmin && (
          <>
            <div className="sidebar-divider"></div>
            {!isCollapsed && <div className="sidebar-section-title">Administration</div>}
            <Link to="/users" className="sidebar-link">
              <People />
              {!isCollapsed && <span>User Management</span>}
            </Link>
            <Link to="/containers" className="sidebar-link">
              <ManageAccounts />
              {!isCollapsed && <span>Container Management</span>}
            </Link>
            <Link to="/matches-admin" className="sidebar-link">
              <SportsEsports />
              {!isCollapsed && <span>Match Management</span>}
            </Link>
          </>
        )}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-legal-links" aria-label="Legal">
          {legalLinks.map((link, index) => {
            const LegalIcon = legalIcons[index] ?? Description;
            return (
              <Link key={link.to} to={link.to} className="sidebar-link">
                <LegalIcon />
                {!isCollapsed && <span>{link.label}</span>}
              </Link>
            );
          })}
        </div>

        <button
          onClick={toggleTheme}
          className="sidebar-link"
          style={{ width: '100%', marginBottom: '1rem', border: 'none', background: 'transparent', cursor: 'pointer', textAlign: 'left', padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: isCollapsed ? 'center' : 'flex-start' }}
        >
          {mode === 'dark' ? <LightMode /> : <DarkMode />}
          {!isCollapsed && <span>{mode === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>}
        </button>

        {user ? (
          <>
            {!isCollapsed && (
              <div className="sidebar-user">
                <div className="sidebar-user-info">
                  <span className="sidebar-username">{user.username}</span>
                </div>
              </div>
            )}
            <Link to="/profile" className="sidebar-logout">
              <Person />
              {!isCollapsed && <span>Profile</span>}
            </Link>
          </>
        ) : (
          <div className="sidebar-auth">
            <Link to="/login" className="sidebar-btn-primary">
              {isCollapsed ? 'In' : 'Login'}
            </Link>
            <Link to="/register" className="sidebar-btn-secondary">
              {isCollapsed ? 'Up' : 'Register'}
            </Link>
          </div>
        )}
      </div>
    </aside>
  );
}
