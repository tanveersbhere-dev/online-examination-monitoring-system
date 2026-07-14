import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Box, CircularProgress, Typography } from '@mui/material';

interface ProtectedRouteProps {
  allowedRoles?: string[];
  redirectPath?: string;
}

const ProtectedRoute = ({ allowedRoles, redirectPath }: ProtectedRouteProps) => {
  const { isAuthenticated, user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <CircularProgress />
        <Typography variant="body2" sx={{ mt: 2, color: 'text.secondary' }}>Verifying session...</Typography>
      </Box>
    );
  }

  if (!isAuthenticated || !user) {
    // If not authenticated, redirect based on current path prefix
    const isExaminer = location.pathname.startsWith('/examiner');
    return <Navigate to={redirectPath || (isExaminer ? '/examiner/login' : '/student/login')} replace state={{ from: location }} />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role.name)) {
    // If authenticated but wrong role, send to root which will redirect appropriately
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
};

export default ProtectedRoute;
