import { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';
import {
  Box,
  Typography,
  TextField,
  Button,
  Stack,
  Alert,
  CircularProgress,
  Link,
  InputAdornment,
  IconButton
} from '@mui/material';
import ShieldIcon from '@mui/icons-material/Shield';
import EmailIcon from '@mui/icons-material/Email';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import LockResetIcon from '@mui/icons-material/LockReset';

const ForgotPasswordPage = () => {
  const navigate = useNavigate();
  
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleRequestReset = async () => {
    if (!email) {
      setError('Please enter your email address.');
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      await apiClient.post('/auth/forgot-password', { email });
      // Redirect to OTP verification with purpose PASSWORD_RESET
      navigate('/examiner/verify-otp', { state: { email, purpose: 'PASSWORD_RESET' } });
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#F8FAFC',
        backgroundImage: 'radial-gradient(circle at 50% 10%, rgba(37,99,235,0.06) 0%, transparent 60%)',
        px: 2,
        py: 4,
        position: 'relative',
      }}
    >
      {/* Top-left back button */}
      <IconButton
        onClick={() => navigate('/examiner/login')}
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
        title="Back to Login"
      >
        <ArrowBackIcon fontSize="small" />
      </IconButton>

      {/* Main card */}
      <Box
        sx={{
          width: '100%',
          maxWidth: 440,
          px: { xs: 3, sm: 5 },
          py: { xs: 4, sm: 5 },
          backgroundColor: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: 3,
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.02)',
        }}
      >
        {/* Logo */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1.25, mb: 3.5 }}>
          <Box sx={{
            width: 38, height: 38, borderRadius: '10px',
            background: 'linear-gradient(135deg, #2563EB, #0EA5E9)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(37,99,235,0.3)',
          }}>
            <ShieldIcon sx={{ fontSize: 22, color: 'white' }} />
          </Box>
          <Typography variant="h6" sx={{ fontWeight: 800, color: '#0F172A', letterSpacing: '-0.01em' }}>
            ExamShield
          </Typography>
        </Box>

        {/* Icon */}
        <Box sx={{
          width: 56, height: 56, borderRadius: '50%',
          background: 'rgba(37,99,235,0.08)',
          border: '1px solid rgba(37,99,235,0.15)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          mx: 'auto', mb: 2.5,
        }}>
          <LockResetIcon sx={{ fontSize: 28, color: '#2563EB' }} />
        </Box>

        <Typography variant="h5" sx={{ fontWeight: 800, textAlign: 'center', color: '#0F172A', letterSpacing: '-0.02em', mb: 0.75 }}>
          Forgot Password?
        </Typography>
        <Typography variant="body2" sx={{ color: '#64748B', textAlign: 'center', mb: 3.5, lineHeight: 1.6 }}>
          Enter your registered email address and we'll send you a 6-digit recovery code.
        </Typography>
        
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Stack spacing={2.5}>
          <TextField
            label="Email Address"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isLoading}
            onKeyDown={(e) => e.key === 'Enter' && handleRequestReset()}
            placeholder="you@institution.edu"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <EmailIcon fontSize="small" sx={{ color: '#94A3B8' }} />
                </InputAdornment>
              ),
            }}
          />
          <Button
            variant="contained"
            size="large"
            fullWidth
            onClick={handleRequestReset}
            disabled={isLoading || !email}
            startIcon={isLoading ? <CircularProgress size={18} color="inherit" /> : null}
            sx={{
              py: 1.4,
              fontSize: '0.9375rem',
              fontWeight: 700,
              background: 'linear-gradient(135deg, #2563EB 0%, #1E40AF 100%)',
            }}
          >
            {isLoading ? 'Sending Request…' : 'Send Verification Code'}
          </Button>
          <Box sx={{ textAlign: 'center', mt: 1 }}>
            <Link
              component={RouterLink}
              to="/examiner/login"
              sx={{
                display: 'inline-flex', alignItems: 'center', gap: 0.5,
                fontWeight: 600, textDecoration: 'none',
                color: '#64748B', fontSize: '0.875rem',
                transition: 'color 0.15s',
                '&:hover': { color: '#2563EB' },
              }}
            >
              <ArrowBackIcon fontSize="small" /> Back to Login
            </Link>
          </Box>
        </Stack>
      </Box>
    </Box>
  );
};

export default ForgotPasswordPage;
