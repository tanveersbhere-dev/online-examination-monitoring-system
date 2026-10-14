import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';
import { useAuth } from '../../hooks/useAuth';
import {
  Box,
  Typography,
  TextField,
  Button,
  Stack,
  Alert,
  CircularProgress,
  Link
} from '@mui/material';
import ShieldIcon from '@mui/icons-material/Shield';
import MarkEmailReadIcon from '@mui/icons-material/MarkEmailRead';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import IconButton from '@mui/material/IconButton';

const OTPVerificationPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  
  const email = location.state?.email || '';
  const purpose = location.state?.purpose || 'REGISTRATION';
  
  const [otpCode, setOtpCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);

  useEffect(() => {
    if (!email) {
      navigate('/examiner/login');
    }
  }, [email, navigate]);

  const handleVerify = async () => {
    if (otpCode.length !== 6) {
      setError('Please enter a valid 6-digit verification code.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      if (purpose === 'REGISTRATION') {
        const response = await apiClient.post('/auth/verify-email', { email, otp_code: otpCode });
        const { access_token, refresh_token, user } = response.data;
        login(access_token, refresh_token, user);
        navigate('/examiner/dashboard', { replace: true });
      } else if (purpose === 'PASSWORD_RESET') {
        navigate('/examiner/reset-password', { state: { email, otp_code: otpCode } });
      }
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    setIsResending(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await apiClient.post('/auth/resend-otp', { email });
      setSuccess(response.data.message || 'Verification code resent successfully.');
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setIsResending(false);
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
          <MarkEmailReadIcon sx={{ fontSize: 28, color: '#2563EB' }} />
        </Box>

        <Typography variant="h5" sx={{ fontWeight: 800, textAlign: 'center', color: '#0F172A', letterSpacing: '-0.02em', mb: 0.75 }}>
          Verify Your Email
        </Typography>
        <Typography variant="body2" sx={{ color: '#64748B', textAlign: 'center', mb: 3.5, lineHeight: 1.6 }}>
          We sent a 6-digit verification code to <br />
          <Box component="span" sx={{ color: '#2563EB', fontWeight: 700 }}>{email}</Box>
          <br />
          <Typography component="span" variant="caption" sx={{ color: '#94A3B8' }}>
            The code will expire in 10 minutes.
          </Typography>
        </Typography>
        
        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
        {success && <Alert severity="success" sx={{ mb: 3 }}>{success}</Alert>}

        <Stack spacing={2.5}>
          <TextField
            label="6-Digit Verification Code"
            value={otpCode}
            onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            disabled={isLoading}
            autoFocus
            inputProps={{
              maxLength: 6,
              style: {
                textAlign: 'center',
                fontSize: '1.75rem',
                letterSpacing: '0.4rem',
                fontWeight: 700,
                color: '#0F172A'
              }
            }}
            placeholder="······"
          />

          <Button
            variant="contained"
            size="large"
            fullWidth
            onClick={handleVerify}
            disabled={isLoading || otpCode.length !== 6}
            startIcon={isLoading ? <CircularProgress size={18} color="inherit" /> : null}
            sx={{
              py: 1.4,
              fontSize: '0.9375rem',
              fontWeight: 700,
              background: 'linear-gradient(135deg, #2563EB 0%, #1E40AF 100%)',
            }}
          >
            {isLoading ? 'Verifying…' : 'Verify Code'}
          </Button>

          <Box sx={{ textAlign: 'center', mt: 1 }}>
            <Typography variant="body2" sx={{ color: '#64748B', fontSize: '0.875rem' }}>
              Didn't receive the code?{' '}
              <Link
                component="button"
                variant="body2"
                onClick={handleResend}
                disabled={isResending || isLoading}
                sx={{ fontWeight: 700, textDecoration: 'none', color: '#2563EB', '&:hover': { color: '#1E40AF' } }}
              >
                {isResending ? 'Sending…' : 'Resend Code'}
              </Link>
            </Typography>
          </Box>
        </Stack>
      </Box>
    </Box>
  );
};

export default OTPVerificationPage;
