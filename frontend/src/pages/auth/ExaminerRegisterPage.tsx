import { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';
import {
  Box,
  Typography,
  TextField,
  Button,
  InputAdornment,
  IconButton,
  Divider,
  Stack,
  Alert,
  CircularProgress,
  Link
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import EmailIcon from '@mui/icons-material/Email';
import LockIcon from '@mui/icons-material/Lock';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import ShieldIcon from '@mui/icons-material/Shield';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import BarChartIcon from '@mui/icons-material/BarChart';
import PeopleIcon from '@mui/icons-material/People';

const ExaminerRegisterPage = () => {
  const navigate = useNavigate();
  
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: '',
    confirm_password: ''
  });
  
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleRegister = async () => {
    const { full_name, email, password, confirm_password } = formData;
    
    if (!full_name || !email || !password || !confirm_password) {
      setError('Please fill in all required fields.');
      return;
    }

    if (password !== confirm_password) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      await apiClient.post('/auth/register', formData);
      navigate('/examiner/verify-otp', { state: { email, purpose: 'REGISTRATION' } });
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
        <Typography variant="h3" sx={{ fontWeight: 700, mb: 0.35 }} gutterBottom>Join ExamShield</Typography>
        <Typography variant="body1" sx={{ opacity: 0.8, mb: 4 }}>
          Create an examiner account to oversee and monitor examinations securely.
        </Typography>
        <Divider sx={{ borderColor: 'rgba(255,255,255,0.2)', mb: 4 }} />

        <Stack spacing={2}>
          {[
            { icon: <CalendarMonthIcon />, label: 'Easy Scheduling', value: 'Manage exams efficiently' },
            { icon: <PeopleIcon />, label: 'Student Monitoring', value: 'AI-powered tracking' },
            { icon: <BarChartIcon />, label: 'Detailed Analytics', value: 'Generate comprehensive reports' },
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

          <Typography variant="h4" sx={{ fontWeight: 600 }} gutterBottom>Create Account</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
            Enter your details to register as an examiner.
          </Typography>
          
          {error && (
            <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
              {error}
            </Alert>
          )}

          <Stack spacing={2.5}>
            <TextField
              label="Full Name"
              name="full_name"
              variant="outlined"
              value={formData.full_name}
              onChange={handleChange}
              disabled={isLoading}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <PersonIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                  </InputAdornment>
                ),
              }}
            />
            <TextField
              label="Email Address"
              name="email"
              type="email"
              variant="outlined"
              value={formData.email}
              onChange={handleChange}
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
              name="password"
              type={showPassword ? 'text' : 'password'}
              variant="outlined"
              value={formData.password}
              onChange={handleChange}
              disabled={isLoading}
              helperText="Minimum 8 characters, include upper, lower, number, and special character."
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
            <TextField
              label="Confirm Password"
              name="confirm_password"
              type={showPassword ? 'text' : 'password'}
              variant="outlined"
              value={formData.confirm_password}
              onChange={handleChange}
              disabled={isLoading}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <LockIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                  </InputAdornment>
                ),
              }}
            />
            <Button
              variant="contained"
              size="large"
              fullWidth
              onClick={handleRegister}
              disabled={isLoading}
              startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : null}
              sx={{ py: 1.5, fontSize: '1rem', borderRadius: 2, mt: 1 }}
            >
              {isLoading ? 'Creating Account...' : 'Register'}
            </Button>
            <Box sx={{ textAlign: 'center', mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Already have an account?{' '}
                <Link component={RouterLink} to="/examiner/login" sx={{ fontWeight: 600, textDecoration: 'none' }}>
                  Log in
                </Link>
              </Typography>
            </Box>
          </Stack>
        </Box>
      </Box>
    </Box>
  );
};

export default ExaminerRegisterPage;
