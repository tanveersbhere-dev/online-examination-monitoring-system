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
    <Box sx={{ minHeight: '100vh', display: 'flex', backgroundColor: 'background.default', alignItems: 'center', justifyContent: 'center' }}>
      <Box sx={{ width: '100%', maxWidth: 450, px: 4, py: 6, bgcolor: 'background.paper', borderRadius: 3, boxShadow: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1, mb: 4 }}>
          <ShieldIcon sx={{ color: 'primary.main', fontSize: 32 }} />
          <Typography variant="h5" sx={{ fontWeight: 700 }} color="primary.main">ExamShield</Typography>
        </Box>

        <Typography variant="h5" sx={{ fontWeight: 600, textAlign: 'center' }} gutterBottom>Verify Your Email</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4, textAlign: 'center' }}>
          We've sent a 6-digit verification code to <strong>{email}</strong>.
          It will expire in 10 minutes.
        </Typography>
        
        {error && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 3, borderRadius: 2 }}>
            {success}
          </Alert>
        )}

        <Stack spacing={3}>
          <TextField
            label="6-Digit Code"
            variant="outlined"
            value={otpCode}
            onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            disabled={isLoading}
            autoFocus
            inputProps={{ style: { textAlign: 'center', fontSize: '1.5rem', letterSpacing: '0.25rem' } }}
          />
          <Button
            variant="contained"
            size="large"
            fullWidth
            onClick={handleVerify}
            disabled={isLoading || otpCode.length !== 6}
            startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : null}
            sx={{ py: 1.5, fontSize: '1rem', borderRadius: 2 }}
          >
            {isLoading ? 'Verifying...' : 'Verify Code'}
          </Button>
          <Box sx={{ textAlign: 'center', mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Didn't receive the code?{' '}
              <Link 
                component="button" 
                variant="body2" 
                onClick={handleResend} 
                disabled={isResending || isLoading}
                sx={{ fontWeight: 600, textDecoration: 'none' }}
              >
                {isResending ? 'Sending...' : 'Resend Code'}
              </Link>
            </Typography>
          </Box>
        </Stack>
      </Box>
    </Box>
  );
};

export default OTPVerificationPage;
