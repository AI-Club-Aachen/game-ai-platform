import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { AppThemeProvider } from './context/ThemeContext';
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
import { Matches } from './pages/Matches';
import { LiveMatch } from './pages/LiveMatch';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { VerifyEmail } from './pages/VerifyEmail';
import { NewSubmission } from './pages/NewSubmission';
import { AgentDetails } from './pages/AgentDetails';
import { SubmissionDetails } from './pages/SubmissionDetails';
import { TournamentDetails } from './pages/TournamentDetails';
import { GameDetails } from './pages/GameDetails';
import './App.css';

function App() {
  return (
    <AppThemeProvider>
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
            <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="games" element={<Games />} />
              <Route path="games/:gameId" element={<GameDetails />} />
              <Route path="games/matches" element={<Matches />} />
              <Route path="games/live/:matchId" element={<LiveMatch />} />
              <Route path="leaderboard" element={<Leaderboard />} />
              <Route path="tournaments" element={<Tournaments />} />
              <Route path="tournaments/:id" element={<TournamentDetails />} />
              <Route path="profile" element={<Profile />} />
              <Route path="users" element={<UserManagement />} />
              <Route path="containers" element={<ContainerManagement />} />
              <Route path="submissions/new" element={<NewSubmission />} />
              <Route path="submissions/:id" element={<SubmissionDetails />} />
              <Route path="agents/:id" element={<AgentDetails />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </AppThemeProvider>
  );
}

export default App;
