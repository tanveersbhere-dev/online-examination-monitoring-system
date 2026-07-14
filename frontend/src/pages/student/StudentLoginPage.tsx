import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import apiClient from '../../services/apiClient';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Checkbox,
  FormControlLabel,
  InputAdornment,
  IconButton,
  Divider,
  Alert,
  Stack,
  CircularProgress
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import LockIcon from '@mui/icons-material/Lock';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import ShieldIcon from '@mui/icons-material/Shield';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import EmailIcon from '@mui/icons-material/Email';

const StudentLoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      setError('Please enter both email and password.');
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
      
      if (user.role.name !== 'STUDENT') {
        setError('Unauthorized role. You must be a student to access this portal.');
        setIsLoading(false);
        return;
      }
      
      login(access_token, refresh_token, user);
      
      const from = location.state?.from?.pathname || '/student';
      navigate(from, { replace: true });
    } catch (err: any) {
      if (err.response?.status === 401 || err.response?.status === 403) {
        setError(err.response.data.detail || 'Invalid email or password.');
      } else if (err.code === 'ERR_NETWORK') {
        setError('Cannot connect to server. Please ensure backend is running.');
      } else {
        setError('An unexpected error occurred. Please try again later.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        backgroundColor: 'background.default',
      }}
    >
      {/* Left Panel */}
      <Box
        sx={{
          width: { xs: 0, md: '40%' },
          display: { xs: 'none', md: 'flex' },
          flexDirection: 'column',
          justifyContent: 'center',
          px: 6,
          background: 'linear-gradient(160deg, #1565C0 0%, #0D47A1 100%)',
          color: 'white',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 6 }}>
          <ShieldIcon sx={{ fontSize: 36 }} />
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            ExamShield
          </Typography>
        </Box>

        <Typography variant="h3" sx={{ fontWeight: 700 }} gutterBottom>
          Secure Exam Login
        </Typography>
        <Divider sx={{ borderColor: 'rgba(255,255,255,0.25)', my: 3, width: 80 }} />

        {/* Exam Context Card */}
        <Paper
          elevation={0}
          sx={{
            backgroundColor: 'rgba(255,255,255,0.12)',
            color: 'white',
            p: 3,
            borderRadius: 3,
            mb: 4,
          }}
        >
          <Typography variant="caption" sx={{ opacity: 0.7, display: 'block', mb: 1 }}>
            You are logging in to:
          </Typography>
          <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom>
            Data Structures & Algorithms
          </Typography>
          <Typography variant="body2" sx={{ opacity: 0.8 }} gutterBottom>
            CS-301
          </Typography>
          <Typography variant="caption" sx={{ opacity: 0.7 }}>
            09:00 AM – 11:00 AM Today
          </Typography>
        </Paper>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, opacity: 0.7 }}>
          <LockIcon fontSize="small" />
          <Typography variant="caption">Your session is encrypted and monitored.</Typography>
        </Box>
      </Box>

      {/* Right Panel — Form */}
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
          {/* Mobile logo */}
          <Box sx={{ display: { xs: 'flex', md: 'none' }, alignItems: 'center', gap: 1, mb: 4 }}>
            <ShieldIcon sx={{ color: 'primary.main', fontSize: 28 }} />
            <Typography variant="h6" sx={{ fontWeight: 700 }} color="primary.main">
              ExamShield
            </Typography>
          </Box>

          <Typography variant="h4" sx={{ fontWeight: 600 }} gutterBottom>
            Student Login
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
            Enter your credentials to begin the examination.
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
              {error}
            </Alert>
          )}

          <Stack spacing={2.5}>
            <TextField
              label="Email Address"
              placeholder="e.g. ahmed.raza@university.edu"
              variant="outlined"
              type="email"
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

            <FormControlLabel
              control={<Checkbox checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} disabled={isLoading} />}
              label={<Typography variant="body2">Remember me on this device</Typography>}
            />

            <Button
              variant="contained"
              size="large"
              fullWidth
              onClick={handleLogin}
              disabled={isLoading}
              startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : null}
              sx={{ py: 1.5, fontSize: '1rem', borderRadius: 2 }}
            >
              {isLoading ? 'Authenticating...' : 'Login'}
            </Button>
          </Stack>

          <Box sx={{ textAlign: 'center', mt: 3 }}>
            <Button
              startIcon={<ArrowBackIcon fontSize="small" />}
              onClick={() => navigate('/student')}
              sx={{ color: 'text.secondary' }}
              disabled={isLoading}
            >
              Back to Today's Exams
            </Button>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default StudentLoginPage;
