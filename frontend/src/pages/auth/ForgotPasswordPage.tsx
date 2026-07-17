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
  InputAdornment
} from '@mui/material';
import ShieldIcon from '@mui/icons-material/Shield';
import EmailIcon from '@mui/icons-material/Email';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

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
    <Box sx={{ minHeight: '100vh', display: 'flex', backgroundColor: 'background.default', alignItems: 'center', justifyContent: 'center' }}>
      <Box sx={{ width: '100%', maxWidth: 450, px: 4, py: 6, bgcolor: 'background.paper', borderRadius: 3, boxShadow: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1, mb: 4 }}>
          <ShieldIcon sx={{ color: 'primary.main', fontSize: 32 }} />
          <Typography variant="h5" sx={{ fontWeight: 700 }} color="primary.main">ExamShield</Typography>
        </Box>

        <Typography variant="h5" sx={{ fontWeight: 600, textAlign: 'center' }} gutterBottom>Forgot Password?</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4, textAlign: 'center' }}>
          Enter the email address associated with your account, and we'll send you a link to reset your password.
        </Typography>
        
        {error && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            {error}
          </Alert>
        )}

        <Stack spacing={3}>
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
          <Button
            variant="contained"
            size="large"
            fullWidth
            onClick={handleRequestReset}
            disabled={isLoading || !email}
            startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : null}
            sx={{ py: 1.5, fontSize: '1rem', borderRadius: 2 }}
          >
            {isLoading ? 'Sending Request...' : 'Send Reset Link'}
          </Button>
          <Box sx={{ textAlign: 'center', mt: 2 }}>
            <Link component={RouterLink} to="/examiner/login" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5, fontWeight: 600, textDecoration: 'none' }}>
              <ArrowBackIcon fontSize="small" /> Back to Login
            </Link>
          </Box>
        </Stack>
      </Box>
    </Box>
  );
};

export default ForgotPasswordPage;
