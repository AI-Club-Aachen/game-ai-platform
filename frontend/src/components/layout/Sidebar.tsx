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
  Menu as MenuIcon
} from '@mui/icons-material';
import './Sidebar.css';

interface SidebarProps {
  onToggle?: (collapsed: boolean) => void;
}

export function Sidebar({ onToggle }: SidebarProps) {
  const { user, isAdmin } = useAuth();
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

  return (
    <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <Link to="/dashboard" className="sidebar-logo">
          <SportsEsports style={{ fontSize: '2rem', color: '#00A6FF' }} />
          {!isCollapsed && <h2>AICA</h2>}
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
          </>
        )}
      </nav>

      <div className="sidebar-footer">
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
