import { useState } from 'react';
import { useNavigate, useLocation, Link as RouterLink } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';
import {
  Box,
  Typography,
  TextField,
  Button,
  Checkbox,
  FormControlLabel,
  InputAdornment,
  IconButton,
  Divider,
  Stack,
  Alert,
  CircularProgress,
  Link
} from '@mui/material';
import EmailIcon from '@mui/icons-material/Email';
import LockIcon from '@mui/icons-material/Lock';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import ShieldIcon from '@mui/icons-material/Shield';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import BarChartIcon from '@mui/icons-material/BarChart';
import PeopleIcon from '@mui/icons-material/People';

const ExaminerLoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      setError('Please enter both email and password.');
      return;
    }

    if (!/\S+@\S+\.\S+/.test(email)) {
      setError('Please enter a valid email address.');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.post('/auth/login', {
        email,
        password
      });
      
      const { access_token, refresh_token, user } = response.data;
      
      if (user.role.name !== 'EXAMINER' && user.role.name !== 'ADMIN') {
        setError('Unauthorized role. You must be an examiner to access this portal.');
        setIsLoading(false);
        return;
      }
      
      login(access_token, refresh_token, user);
      
      const from = location.state?.from?.pathname || '/examiner/dashboard';
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', backgroundColor: 'background.default' }}>
      {/* Left Panel */}
      <Box
        sx={{
          width: { xs: 0, md: '42%' },
          display: { xs: 'none', md: 'flex' },
          flexDirection: 'column',
          justifyContent: 'center',
          px: 6,
          background: 'linear-gradient(160deg, #0D47A1 0%, #1565C0 60%, #1976D2 100%)',
          color: 'white',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 6 }}>
          <ShieldIcon sx={{ fontSize: 36 }} />
          <Typography variant="h6" sx={{ fontWeight: 700 }}>ExamShield</Typography>
        </Box>
        <Typography variant="h3" sx={{ fontWeight: 700, mb: 0.35 }} gutterBottom>Examiner Portal</Typography>
        <Typography variant="body1" sx={{ opacity: 0.8, mb: 4 }}>
          Monitor examinations in real-time. Review violations. Generate detailed reports.
        </Typography>
        <Divider sx={{ borderColor: 'rgba(255,255,255,0.2)', mb: 4 }} />

        {/* Today's stats */}
        <Stack spacing={2}>
          {[
            { icon: <CalendarMonthIcon />, label: "Today's Schedule", value: '7 Examinations' },
            { icon: <PeopleIcon />, label: 'Registered Students', value: '142 Total' },
            { icon: <BarChartIcon />, label: 'Active Sessions', value: '3 Running' },
          ].map((stat) => (
            <Box key={stat.label} sx={{ display: 'flex', alignItems: 'center', gap: 2, opacity: 0.9 }}>
              <Box sx={{ opacity: 0.8 }}>{stat.icon}</Box>
              <Box>
                <Typography variant="caption" sx={{ opacity: 0.7 }}>{stat.label}</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>{stat.value}</Typography>
              </Box>
            </Box>
          ))}
        </Stack>
      </Box>

      {/* Right Panel */}
      <Box
        sx={{
          flexGrow: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          px: { xs: 3, md: 8 },
          py: 6,
        }}
      >
        <Box sx={{ width: '100%', maxWidth: 400 }}>
          <Box sx={{ display: { xs: 'flex', md: 'none' }, alignItems: 'center', gap: 1, mb: 4 }}>
            <ShieldIcon sx={{ color: 'primary.main', fontSize: 28 }} />
            <Typography variant="h6" sx={{ fontWeight: 700 }} color="primary.main">ExamShield</Typography>
          </Box>

          <Typography variant="h4" sx={{ fontWeight: 600 }} gutterBottom>Examiner Login</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
            Sign in to access the examination dashboard.
          </Typography>
          
          {error && (
            <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
              {error}
            </Alert>
          )}

          <Stack spacing={2.5}>
            <TextField
              label="Email Address"
              type="email"
              variant="outlined"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <EmailIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                  </InputAdornment>
                ),
              }}
            />
            <TextField
              label="Password"
              type={showPassword ? 'text' : 'password'}
              variant="outlined"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <LockIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowPassword(!showPassword)} edge="end" size="small" disabled={isLoading}>
                      {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <FormControlLabel
                control={<Checkbox disabled={isLoading} />}
                label={<Typography variant="body2">Remember me</Typography>}
              />
              <Link component={RouterLink} to="/examiner/forgot-password" variant="body2" sx={{ fontWeight: 500, textDecoration: 'none' }}>
                Forgot password?
              </Link>
            </Box>
            <Button
              variant="contained"
              size="large"
              fullWidth
              onClick={handleLogin}
              disabled={isLoading}
              startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : null}
              sx={{ py: 1.5, fontSize: '1rem', borderRadius: 2 }}
            >
              {isLoading ? 'Authenticating...' : 'Login to Dashboard'}
            </Button>
            <Box sx={{ textAlign: 'center', mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Don't have an account?{' '}
                <Link component={RouterLink} to="/examiner/register" sx={{ fontWeight: 600, textDecoration: 'none' }}>
                  Create one now
                </Link>
              </Typography>
            </Box>
          </Stack>
        </Box>
      </Box>
    </Box>
  );
};

export default ExaminerLoginPage;
