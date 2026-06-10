import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Box, CircularProgress } from '@mui/material';

type Role = 'guest' | 'user' | 'admin';

const ROLE_RANK: Record<Role, number> = {
    guest: 0,
    user: 1,
    admin: 2,
};

interface ProtectedRouteProps {
    children?: React.ReactNode;
    /**
     * Minimum role required to render this route. Defaults to any
     * authenticated user. This is UX/defense-in-depth only — the backend
     * enforces the real RBAC.
     */
    requiredRole?: Role;
}

export function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
    const { isAuthenticated, isLoading, user } = useAuth();
    const location = useLocation();

    if (isLoading) {
        return (
            <Box
                sx={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    height: '100vh',
                    bgcolor: 'background.default'
                }}
            >
                <CircularProgress />
            </Box>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    if (requiredRole) {
        const userRank = ROLE_RANK[(user?.role ?? 'guest') as Role] ?? 0;
        if (userRank < ROLE_RANK[requiredRole]) {
            return <Navigate to="/dashboard" replace />;
        }
    }

    return children ? <>{children}</> : <Outlet />;
}
