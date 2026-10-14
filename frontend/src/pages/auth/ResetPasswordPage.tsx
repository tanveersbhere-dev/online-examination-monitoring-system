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
import LockResetIcon from '@mui/icons-material/LockReset';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

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
      navigate('/examiner/login', { state: { message: 'Password reset successfully. Please log in with your new password.' } });
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
          background: 'rgba(5,150,105,0.08)',
          border: '1px solid rgba(5,150,105,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          mx: 'auto', mb: 2.5,
        }}>
          <LockResetIcon sx={{ fontSize: 28, color: '#059669' }} />
        </Box>

        <Typography variant="h5" sx={{ fontWeight: 800, textAlign: 'center', color: '#0F172A', letterSpacing: '-0.02em', mb: 0.75 }}>
          Set New Password
        </Typography>
        <Typography variant="body2" sx={{ color: '#64748B', textAlign: 'center', mb: 3.5, lineHeight: 1.6 }}>
          Create a strong password for <br />
          <Box component="span" sx={{ color: '#0F172A', fontWeight: 700 }}>{email}</Box>
        </Typography>
        
        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

        <Stack spacing={2.5}>
          <TextField
            label="New Password"
            type={showPassword ? 'text' : 'password'}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            disabled={isLoading}
            helperText="Min 8 characters — upper, lower, number & special char."
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
            label="Confirm New Password"
            type={showPassword ? 'text' : 'password'}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
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
            onClick={handleReset}
            disabled={isLoading}
            startIcon={isLoading ? <CircularProgress size={18} color="inherit" /> : null}
            sx={{
              py: 1.4,
              fontSize: '0.9375rem',
              fontWeight: 700,
              background: 'linear-gradient(135deg, #2563EB 0%, #1E40AF 100%)',
              mt: 0.5,
            }}
          >
            {isLoading ? 'Resetting Password…' : 'Set New Password'}
          </Button>
        </Stack>
      </Box>
    </Box>
  );
};

export default ResetPasswordPage;
