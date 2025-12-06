import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import './Layout.css';

export function Layout() {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  return (
    <div className="app-layout">
      <Sidebar onToggle={setIsSidebarCollapsed} />
      <main 
        className="main-content" 
        style={{ marginLeft: isSidebarCollapsed ? '70px' : '260px' }}
      >
        <Outlet />
      </main>
    </div>
  );
}
