import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
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
  InputAdornment,
  IconButton
} from '@mui/material';
import ShieldIcon from '@mui/icons-material/Shield';
import LockIcon from '@mui/icons-material/Lock';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';

const ResetPasswordPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const email = location.state?.email || '';
  const otpCode = location.state?.otp_code || '';
  
  const [showPassword, setShowPassword] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!email || !otpCode) {
      navigate('/examiner/login');
    }
  }, [email, otpCode, navigate]);

  const handleReset = async () => {
    if (!newPassword || !confirmPassword) {
      setError('Please fill in both password fields.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      await apiClient.post('/auth/reset-password', {
        email,
        otp_code: otpCode,
        new_password: newPassword,
        confirm_password: confirmPassword
      });
      // Assuming success redirects to login
      navigate('/examiner/login', { state: { message: 'Password reset successfully. Please log in with your new password.' } });
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

        <Typography variant="h5" sx={{ fontWeight: 600, textAlign: 'center' }} gutterBottom>Reset Password</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4, textAlign: 'center' }}>
          Please enter your new password below. Make sure it is secure.
        </Typography>
        
        {error && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            {error}
          </Alert>
        )}

        <Stack spacing={3}>
          <TextField
            label="New Password"
            type={showPassword ? 'text' : 'password'}
            variant="outlined"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
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
            label="Confirm New Password"
            type={showPassword ? 'text' : 'password'}
            variant="outlined"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
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
            onClick={handleReset}
            disabled={isLoading}
            startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : null}
            sx={{ py: 1.5, fontSize: '1rem', borderRadius: 2 }}
          >
            {isLoading ? 'Resetting Password...' : 'Reset Password'}
          </Button>
        </Stack>
      </Box>
    </Box>
  );
};

export default ResetPasswordPage;
