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
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

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
    <Box sx={{ minHeight: '100vh', display: 'flex' }}>
      {/* ── Left Panel — Brand / Info ─────────────────────────────────────── */}
      <Box
        sx={{
          width: { xs: 0, md: '42%' },
          display: { xs: 'none', md: 'flex' },
          flexDirection: 'column',
          justifyContent: 'center',
          px: { md: 6, lg: 8 },
          position: 'relative',
          overflow: 'hidden',
          background: 'linear-gradient(160deg, #0F1E3C 0%, #0B2D5C 50%, #0C1A40 100%)',
          color: 'white',
        }}
      >
        {/* Background orbs */}
        <Box sx={{
          position: 'absolute', top: '-15%', right: '-20%',
          width: 400, height: 400, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(37,99,235,0.25) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />
        <Box sx={{
          position: 'absolute', bottom: '-10%', left: '-15%',
          width: 320, height: 320, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(14,165,233,0.18) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />
        <Box sx={{
          position: 'absolute', inset: 0, pointerEvents: 'none',
          backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.04) 1px, transparent 0)',
          backgroundSize: '28px 28px',
        }} />

        <Box sx={{ position: 'relative', zIndex: 1 }}>
          {/* Brand */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 6 }}>
            <Box sx={{
              width: 42, height: 42, borderRadius: '12px',
              background: 'linear-gradient(135deg, #2563EB, #0EA5E9)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 4px 16px rgba(37,99,235,0.4)',
            }}>
              <ShieldIcon sx={{ fontSize: 24, color: 'white' }} />
            </Box>
            <Typography variant="h6" sx={{ fontWeight: 800, letterSpacing: '-0.01em' }}>
              ExamShield
            </Typography>
          </Box>

          <Typography
            component="div"
            sx={{
              fontSize: '0.75rem', fontWeight: 600, letterSpacing: '0.1em',
              textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', mb: 1.5,
            }}
          >
            New Examiner Account
          </Typography>
          <Typography variant="h3" sx={{ fontWeight: 800, mb: 1.5, letterSpacing: '-0.02em', lineHeight: 1.1 }}>
            Join the<br />platform.
          </Typography>
          <Typography variant="body1" sx={{ opacity: 0.6, mb: 5, lineHeight: 1.7, maxWidth: 320 }}>
            Create your examiner account to start scheduling, monitoring, and reporting on examinations.
          </Typography>

          <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)', mb: 4 }} />

          {/* Feature list */}
          <Stack spacing={3}>
            {[
              { icon: <CalendarMonthIcon sx={{ fontSize: 18 }} />, label: 'Easy Scheduling', value: 'Manage exams efficiently' },
              { icon: <PeopleIcon sx={{ fontSize: 18 }} />, label: 'Student Monitoring', value: 'AI-powered tracking' },
              { icon: <BarChartIcon sx={{ fontSize: 18 }} />, label: 'Detailed Analytics', value: 'Comprehensive reports' },
            ].map((feat) => (
              <Box key={feat.label} sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box sx={{
                  width: 36, height: 36, borderRadius: '10px',
                  background: 'rgba(255,255,255,0.08)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#93C5FD', flexShrink: 0,
                }}>
                  {feat.icon}
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ opacity: 0.45, display: 'block', lineHeight: 1.3 }}>
                    {feat.label}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>
                    {feat.value}
                  </Typography>
                </Box>
              </Box>
            ))}
          </Stack>
        </Box>
      </Box>

      {/* ── Right Panel — Form ────────────────────────────────────────────── */}
      <Box
        sx={{
          flexGrow: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          px: { xs: 3, sm: 5, md: 7, lg: 10 },
          py: 6,
          backgroundColor: '#F8FAFC',
          // Subtle side-panel texture
          backgroundImage: 'radial-gradient(circle at 90% 10%, rgba(37,99,235,0.04) 0%, transparent 60%)',
        }}
      >
        {/* Top-left back button matching student portal */}
        <IconButton
          onClick={() => navigate('/')}
          size="small"
          sx={{
            position: 'absolute',
            top: { xs: 16, sm: 24 },
            left: { xs: 16, sm: 24 },
            color: '#64748B',
            backgroundColor: '#FFFFFF',
            border: '1px solid #E2E8F0',
            borderRadius: '8px',
            width: 36,
            height: 36,
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            '&:hover': { backgroundColor: '#F1F5F9', color: '#0F172A' },
          }}
          title="Back to Home"
        >
          <ArrowBackIcon fontSize="small" />
        </IconButton>

        <Box sx={{ width: '100%', maxWidth: 420, py: 2 }}>
          {/* Mobile logo */}
          <Box sx={{ display: { xs: 'flex', md: 'none' }, alignItems: 'center', gap: 1.25, mb: 3 }}>
            <Box sx={{
              width: 36, height: 36, borderRadius: '10px',
              background: 'linear-gradient(135deg, #2563EB, #0EA5E9)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(37,99,235,0.3)',
            }}>
              <ShieldIcon sx={{ fontSize: 20, color: 'white' }} />
            </Box>
            <Typography variant="h6" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.01em' }}>
              ExamShield
            </Typography>
          </Box>

          <Typography variant="overline" sx={{ color: '#2563EB', fontWeight: 600, letterSpacing: '0.08em', mb: 0.75, display: 'block' }}>
            Examiner Portal
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.02em', mb: 0.75 }}>
            Create Account
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mb: 4, lineHeight: 1.6 }}>
            Enter your details to register as an examiner.
          </Typography>
          
          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          <Stack spacing={2.5}>
            <TextField
              label="Full Name"
              name="full_name"
              value={formData.full_name}
              onChange={handleChange}
              disabled={isLoading}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <PersonIcon fontSize="small" sx={{ color: '#94A3B8' }} />
                  </InputAdornment>
                ),
              }}
            />
            <TextField
              label="Email Address"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              disabled={isLoading}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <EmailIcon fontSize="small" sx={{ color: '#94A3B8' }} />
                  </InputAdornment>
                ),
              }}
            />
            <TextField
              label="Password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              value={formData.password}
              onChange={handleChange}
              disabled={isLoading}
              helperText="Minimum 8 characters — include upper, lower, number, and special character."
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <LockIcon fontSize="small" sx={{ color: '#94A3B8' }} />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowPassword(!showPassword)} edge="end" size="small" disabled={isLoading} sx={{ color: '#94A3B8' }}>
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
              value={formData.confirm_password}
              onChange={handleChange}
              disabled={isLoading}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <LockIcon fontSize="small" sx={{ color: '#94A3B8' }} />
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
              startIcon={isLoading ? <CircularProgress size={18} color="inherit" /> : null}
              sx={{ py: 1.5, fontSize: '0.9375rem', mt: 0.5 }}
            >
              {isLoading ? 'Creating Account…' : 'Create Examiner Account'}
            </Button>

            <Divider sx={{ my: 0.5 }}>
              <Typography variant="caption" sx={{ color: '#94A3B8', px: 1 }}>OR</Typography>
            </Divider>

            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="body2" sx={{ color: '#64748B' }}>
                Already have an account?{' '}
                <Link
                  component={RouterLink}
                  to="/examiner/login"
                  sx={{ fontWeight: 700, textDecoration: 'none', color: '#2563EB', '&:hover': { color: '#1E40AF' } }}
                >
                  Sign in
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
