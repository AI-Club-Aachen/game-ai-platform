import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { AuthProvider } from './context/AuthContext';
import { Layout } from './components/layout/Layout';
import { Home } from './pages/Home';
import { Games } from './pages/Games';
import { Dashboard } from './pages/Dashboard';
import { Tournaments } from './pages/Tournaments';
import { ContainerManagement } from './pages/ContainerManagement';
import { UserManagement } from './pages/UserManagement';
import { Profile } from './pages/Profile';
import { Leaderboard } from './pages/Leaderboard';
import { LiveGames } from './pages/LiveGames';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { VerifyEmail } from './pages/VerifyEmail';
import theme from './theme';
import './App.css';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes - no layout */}
            <Route index element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/verify-email" element={<VerifyEmail />} />
            
            {/* Protected routes - with layout */}
            <Route path="/" element={<Layout />}>
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="games" element={<Games />} />
              <Route path="games/live" element={<LiveGames />} />
              <Route path="leaderboard" element={<Leaderboard />} />
              <Route path="tournaments" element={<Tournaments />} />
              <Route path="profile" element={<Profile />} />
              <Route path="users" element={<UserManagement />} />
              <Route path="containers" element={<ContainerManagement />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
