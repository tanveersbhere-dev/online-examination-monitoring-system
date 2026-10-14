import { useState } from 'react';
import { useNavigate, useLocation, Link as RouterLink } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  TextField,
  Button,
  Paper,
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
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import VerifiedUserIcon from '@mui/icons-material/VerifiedUser';
import TimerIcon from '@mui/icons-material/Timer';
import AssessmentIcon from '@mui/icons-material/Assessment';

const ExaminerLoginPage = () => {
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

    if (!/\S+@\S+\.\S+/.test(email)) {
      setError('Please enter a valid email address.');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.post('/auth/login', {
        email,
        password,
        portal_type: 'EXAMINER'
      });
      
      const { access_token, refresh_token, user } = response.data;
      
      const roleName = user.role?.name;
      if (roleName !== 'Examiner' && roleName !== 'Admin') {
        setError('You are not registered as an examiner.');
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
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#F8FAFC' }}>
      {/* ── Top App Bar matching Student Portal header ────────────────────── */}
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          backgroundColor: '#FFFFFF',
          color: '#0F172A',
          borderBottom: '1px solid #E2E8F0',
        }}
      >
        <Toolbar sx={{ minHeight: '60px !important', px: 2, gap: 1 }}>
          <IconButton
            edge="start"
            onClick={() => navigate('/')}
            size="small"
            sx={{
              mr: 1,
              color: '#64748B',
              backgroundColor: '#F1F5F9',
              borderRadius: '8px',
              width: 36,
              height: 36,
              '&:hover': { backgroundColor: '#E2E8F0', color: '#0F172A' },
            }}
          >
            <ArrowBackIcon fontSize="small" />
          </IconButton>

          <Typography
            variant="h6"
            sx={{
              flexGrow: 1,
              fontSize: '0.9375rem',
              fontWeight: 700,
              color: '#0F172A',
              letterSpacing: '-0.01em',
            }}
          >
            Examiner Login
          </Typography>
        </Toolbar>
      </AppBar>

      {/* ── Main Content Split Panel ─────────────────────────────────────── */}
      <Box sx={{ flexGrow: 1, display: 'flex' }}>
        {/* ── Left Panel — Examiner Brand (Matching Teal/Emerald Palette) ── */}
        <Box
          sx={{
            width: { xs: 0, md: '40%' },
            display: { xs: 'none', md: 'flex' },
            flexDirection: 'column',
            justifyContent: 'center',
            px: { md: 6, lg: 8 },
            position: 'relative',
            overflow: 'hidden',
            // Consistent teal/emerald gradient palette matching student portal
            background: 'linear-gradient(160deg, #0C2A3A 0%, #0B3549 50%, #073041 100%)',
            color: 'white',
          }}
        >
          {/* Background orbs — teal accent */}
          <Box sx={{
            position: 'absolute', top: '-15%', right: '-15%',
            width: 420, height: 420, borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(14,165,233,0.25) 0%, transparent 70%)',
            pointerEvents: 'none',
          }} />
          <Box sx={{
            position: 'absolute', bottom: '-10%', left: '-12%',
            width: 340, height: 340, borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(5,150,105,0.18) 0%, transparent 70%)',
            pointerEvents: 'none',
          }} />
          <Box sx={{
            position: 'absolute', inset: 0, pointerEvents: 'none',
            backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.04) 1px, transparent 0)',
            backgroundSize: '28px 28px',
          }} />

          <Box sx={{ position: 'relative', zIndex: 1 }}>
            {/* Brand Logo */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 6 }}>
              <Box sx={{
                width: 42, height: 42, borderRadius: '12px',
                background: 'linear-gradient(135deg, #0EA5E9, #059669)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 4px 16px rgba(14,165,233,0.4)',
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
              Examiner Portal
            </Typography>
            <Typography variant="h3" sx={{ fontWeight: 800, mb: 1.5, letterSpacing: '-0.02em', lineHeight: 1.1 }}>
              Monitor with<br />confidence.
            </Typography>
            <Typography variant="body1" sx={{ opacity: 0.6, mb: 5, lineHeight: 1.7, maxWidth: 320 }}>
              Real-time proctoring, AI-powered violation detection, and comprehensive reporting — all in one place.
            </Typography>

            <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)', mb: 4 }} />

            {/* Portal info card */}
            <Paper
              elevation={0}
              sx={{
                backgroundColor: 'rgba(255,255,255,0.07)',
                border: '1px solid rgba(255,255,255,0.1)',
                color: 'white',
                p: 3,
                borderRadius: '14px',
                mb: 4,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                <AssessmentIcon sx={{ fontSize: 16, opacity: 0.5 }} />
                <Typography variant="caption" sx={{ opacity: 0.5, letterSpacing: '0.05em', textTransform: 'uppercase', fontWeight: 600 }}>
                  Assessment Management
                </Typography>
              </Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 0.5 }}>
                Access Examiner Workspace
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.6 }}>
                Log in with your institutional credentials to manage exams, review submissions, and monitor live candidates.
              </Typography>
            </Paper>

            {/* Info badges */}
            <Stack spacing={2}>
              {[
                { icon: <VerifiedUserIcon sx={{ fontSize: 16 }} />, text: 'AI-monitored session' },
                { icon: <LockIcon sx={{ fontSize: 16 }} />, text: 'End-to-end encrypted' },
                { icon: <TimerIcon sx={{ fontSize: 16 }} />, text: 'Real-time violation analytics' },
              ].map((item) => (
                <Box key={item.text} sx={{ display: 'flex', alignItems: 'center', gap: 1.5, color: 'rgba(255,255,255,0.45)' }}>
                  {item.icon}
                  <Typography variant="caption">{item.text}</Typography>
                </Box>
              ))}
            </Stack>
          </Box>
        </Box>

        {/* ── Right Panel — Form (Matching Student Portal Layout & Design) ─ */}
        <Box
          sx={{
            flexGrow: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            px: { xs: 3, sm: 5, md: 7, lg: 10 },
            py: 6,
            backgroundColor: '#F8FAFC',
            backgroundImage: 'radial-gradient(circle at 90% 10%, rgba(14,165,233,0.05) 0%, transparent 60%)',
          }}
        >
          <Box sx={{ width: '100%', maxWidth: 400 }}>
            {/* Mobile logo */}
            <Box sx={{ display: { xs: 'flex', md: 'none' }, alignItems: 'center', gap: 1.25, mb: 5 }}>
              <Box sx={{
                width: 36, height: 36, borderRadius: '10px',
                background: 'linear-gradient(135deg, #0EA5E9, #059669)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 4px 12px rgba(14,165,233,0.3)',
              }}>
                <ShieldIcon sx={{ fontSize: 20, color: 'white' }} />
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.01em' }}>
                ExamShield
              </Typography>
            </Box>

            <Typography variant="overline" sx={{ color: '#0EA5E9', fontWeight: 600, letterSpacing: '0.08em', mb: 0.75, display: 'block' }}>
              Examiner Portal
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.02em', mb: 0.75 }}>
              Examiner Login
            </Typography>
            <Typography variant="body2" sx={{ color: '#64748B', mb: 4, lineHeight: 1.6 }}>
              Enter your credentials to access the examination monitoring dashboard.
            </Typography>

            {error && (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>
            )}

            <Stack spacing={2.5}>
              <TextField
                label="Email Address"
                placeholder="e.g. examiner@university.edu"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading}
                onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
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
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
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

              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: -0.5 }}>
                <FormControlLabel
                  control={<Checkbox checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} disabled={isLoading} size="small" />}
                  label={<Typography variant="body2" sx={{ color: '#475569' }}>Remember me on this device</Typography>}
                />
                <Link
                  component={RouterLink}
                  to="/examiner/forgot-password"
                  variant="body2"
                  sx={{ fontWeight: 600, textDecoration: 'none', color: '#0EA5E9', '&:hover': { color: '#0284C7' } }}
                >
                  Forgot password?
                </Link>
              </Box>

              <Button
                variant="contained"
                size="large"
                fullWidth
                onClick={handleLogin}
                disabled={isLoading}
                startIcon={isLoading ? <CircularProgress size={18} color="inherit" /> : null}
                sx={{
                  py: 1.5, fontSize: '0.9375rem',
                  background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
                  '&:hover': { background: 'linear-gradient(135deg, #38BDF8 0%, #0EA5E9 100%)' },
                }}
              >
                {isLoading ? 'Authenticating…' : 'Sign In to Dashboard'}
              </Button>

              <Divider sx={{ my: 0.5 }}>
                <Typography variant="caption" sx={{ color: '#94A3B8', px: 1 }}>OR</Typography>
              </Divider>

              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="body2" sx={{ color: '#64748B' }}>
                  Don't have an account?{' '}
                  <Link
                    component={RouterLink}
                    to="/examiner/register"
                    sx={{ fontWeight: 700, textDecoration: 'none', color: '#0EA5E9', '&:hover': { color: '#0284C7' } }}
                  >
                    Create one
                  </Link>
                </Typography>
              </Box>
            </Stack>

            <Box sx={{ textAlign: 'center', mt: 3 }}>
              <Button
                startIcon={<ArrowBackIcon fontSize="small" />}
                onClick={() => navigate('/')}
                sx={{ color: '#94A3B8', fontWeight: 500, '&:hover': { color: '#475569', backgroundColor: 'rgba(0,0,0,0.04)' } }}
                disabled={isLoading}
              >
                Back to Home
              </Button>
            </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default ExaminerLoginPage;
