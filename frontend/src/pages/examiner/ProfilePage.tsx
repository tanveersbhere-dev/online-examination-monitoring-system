import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
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
  Paper,
  Divider,
  InputAdornment,
  IconButton
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import EmailIcon from '@mui/icons-material/Email';
import PhoneIcon from '@mui/icons-material/Phone';
import LockIcon from '@mui/icons-material/Lock';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';

const ProfilePage = () => {
  const { user, login } = useAuth();
  
  // Profile Update State
  const [profileData, setProfileData] = useState({
    full_name: '',
    phone_number: '',
    profile_picture_url: ''
  });
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);
  const [profileMessage, setProfileMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  // Email Change State
  const [newEmail, setNewEmail] = useState('');
  const [emailOtp, setEmailOtp] = useState('');
  const [isEmailChangeRequested, setIsEmailChangeRequested] = useState(false);
  const [isEmailLoading, setIsEmailLoading] = useState(false);
  const [emailMessage, setEmailMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  // Password Change State
  const [showPassword, setShowPassword] = useState(false);
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [isPasswordLoading, setIsPasswordLoading] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  useEffect(() => {
    if (user) {
      setProfileData({
        full_name: user.full_name || '',
        phone_number: user.phone_number || '',
        profile_picture_url: user.profile_picture_url || ''
      });
    }
  }, [user]);

  const handleProfileUpdate = async () => {
    setIsUpdatingProfile(true);
    setProfileMessage(null);
    try {
      const response = await apiClient.put('/auth/profile', profileData);
      const token = localStorage.getItem('access_token') || '';
      const refresh = localStorage.getItem('refresh_token') || '';
      login(token, refresh, response.data);
      setProfileMessage({ type: 'success', text: 'Profile updated successfully.' });
    } catch (err: any) {
      setProfileMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const handleEmailRequest = async () => {
    if (!newEmail) return;
    setIsEmailLoading(true);
    setEmailMessage(null);
    try {
      await apiClient.post('/auth/profile/email', { new_email: newEmail });
      setIsEmailChangeRequested(true);
      setEmailMessage({ type: 'success', text: 'Verification code sent to your new email.' });
    } catch (err: any) {
      setEmailMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setIsEmailLoading(false);
    }
  };

  const handleEmailVerify = async () => {
    if (!emailOtp || emailOtp.length !== 6) return;
    setIsEmailLoading(true);
    setEmailMessage(null);
    try {
      const response = await apiClient.post('/auth/profile/email/verify', { email: newEmail, otp_code: emailOtp });
      const token = localStorage.getItem('access_token') || '';
      const refresh = localStorage.getItem('refresh_token') || '';
      login(token, refresh, response.data);
      setNewEmail('');
      setEmailOtp('');
      setIsEmailChangeRequested(false);
      setEmailMessage({ type: 'success', text: 'Email changed successfully.' });
    } catch (err: any) {
      setEmailMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setIsEmailLoading(false);
    }
  };

  const handlePasswordChange = async () => {
    if (!passwordData.current_password || !passwordData.new_password || !passwordData.confirm_password) {
      setPasswordMessage({ type: 'error', text: 'Please fill all password fields.' });
      return;
    }
    if (passwordData.new_password !== passwordData.confirm_password) {
      setPasswordMessage({ type: 'error', text: 'New passwords do not match.' });
      return;
    }
    setIsPasswordLoading(true);
    setPasswordMessage(null);
    try {
      const response = await apiClient.put('/auth/change-password', passwordData);
      setPasswordMessage({ type: 'success', text: response.data.message });
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
    } catch (err: any) {
      setPasswordMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setIsPasswordLoading(false);
    }
  };

  return (
    <Box>
      {/* Page Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={800} sx={{ color: '#0F172A', letterSpacing: '-0.02em', mb: 0.5 }}>My Profile</Typography>
        <Typography variant="body2" sx={{ color: '#64748B' }}>Manage your account settings and credentials.</Typography>
      </Box>

      <Stack spacing={3} sx={{ maxWidth: 740 }}>
        
        {/* Basic Info Section */}
        <Paper elevation={0} sx={{ p: 3, border: '1px solid #F1F5F9', borderRadius: '14px' }}>
          <Typography variant="overline" sx={{ color: '#64748B', fontSize: '0.65rem', letterSpacing: '0.08em', mb: 0.5, display: 'block' }}>Account</Typography>
          <Typography variant="h6" fontWeight={700} sx={{ color: '#0F172A', mb: 1.5 }}>Basic Information</Typography>
          <Divider sx={{ mb: 3 }} />
          
          {profileMessage && (
            <Alert severity={profileMessage.type} sx={{ mb: 3 }}>{profileMessage.text}</Alert>
          )}

          <Stack spacing={2.5}>
            <TextField
              label="Full Name"
              value={profileData.full_name}
              onChange={(e) => setProfileData({ ...profileData, full_name: e.target.value })}
              InputProps={{ startAdornment: <InputAdornment position="start"><PersonIcon fontSize="small" sx={{ color: '#94A3B8' }} /></InputAdornment> }}
            />
            <TextField
              label="Phone Number"
              value={profileData.phone_number}
              onChange={(e) => setProfileData({ ...profileData, phone_number: e.target.value })}
              InputProps={{ startAdornment: <InputAdornment position="start"><PhoneIcon fontSize="small" sx={{ color: '#94A3B8' }} /></InputAdornment> }}
            />
            <Button
              variant="contained"
              onClick={handleProfileUpdate}
              disabled={isUpdatingProfile}
              startIcon={isUpdatingProfile ? <CircularProgress size={16} color="inherit" /> : null}
              sx={{ width: 'fit-content', px: 3 }}
            >
              {isUpdatingProfile ? 'Saving…' : 'Save Changes'}
            </Button>
          </Stack>
        </Paper>

        {/* Email Address Section */}
        <Paper elevation={0} sx={{ p: 3, border: '1px solid #F1F5F9', borderRadius: '14px' }}>
          <Typography variant="overline" sx={{ color: '#64748B', fontSize: '0.65rem', letterSpacing: '0.08em', mb: 0.5, display: 'block' }}>Security</Typography>
          <Typography variant="h6" fontWeight={700} sx={{ color: '#0F172A', mb: 0.75 }}>Email Address</Typography>
          <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.75, px: 1.5, py: 0.5, borderRadius: '8px', backgroundColor: '#EFF6FF', mb: 1.5 }}>
            <EmailIcon sx={{ fontSize: 14, color: '#2563EB' }} />
            <Typography variant="caption" sx={{ color: '#2563EB', fontWeight: 600 }}>{user?.email}</Typography>
          </Box>
          <Divider sx={{ mb: 3 }} />

          {emailMessage && (
            <Alert severity={emailMessage.type} sx={{ mb: 3 }}>{emailMessage.text}</Alert>
          )}

          {!isEmailChangeRequested ? (
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField
                label="New Email Address"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                sx={{ flexGrow: 1 }}
                InputProps={{ startAdornment: <InputAdornment position="start"><EmailIcon fontSize="small" sx={{ color: '#94A3B8' }} /></InputAdornment> }}
              />
              <Button variant="outlined" onClick={handleEmailRequest} disabled={!newEmail || isEmailLoading} sx={{ flexShrink: 0 }}>
                Request Change
              </Button>
            </Stack>
          ) : (
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField
                label="6-Digit OTP Code"
                value={emailOtp}
                onChange={(e) => setEmailOtp(e.target.value)}
                sx={{ flexGrow: 1 }}
              />
              <Button variant="contained" onClick={handleEmailVerify} disabled={!emailOtp || isEmailLoading} sx={{ flexShrink: 0 }}>
                Verify & Update
              </Button>
            </Stack>
          )}
        </Paper>

        {/* Change Password Section */}
        <Paper elevation={0} sx={{ p: 3, border: '1px solid #F1F5F9', borderRadius: '14px' }}>
          <Typography variant="overline" sx={{ color: '#64748B', fontSize: '0.65rem', letterSpacing: '0.08em', mb: 0.5, display: 'block' }}>Security</Typography>
          <Typography variant="h6" fontWeight={700} sx={{ color: '#0F172A', mb: 1.5 }}>Change Password</Typography>
          <Divider sx={{ mb: 3 }} />

          {passwordMessage && (
            <Alert severity={passwordMessage.type} sx={{ mb: 3 }}>{passwordMessage.text}</Alert>
          )}

          <Stack spacing={2.5}>
            <TextField
              label="Current Password"
              type={showPassword ? 'text' : 'password'}
              value={passwordData.current_password}
              onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
              InputProps={{ startAdornment: <InputAdornment position="start"><LockIcon fontSize="small" sx={{ color: '#94A3B8' }} /></InputAdornment> }}
            />
            <TextField
              label="New Password"
              type={showPassword ? 'text' : 'password'}
              value={passwordData.new_password}
              onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
              InputProps={{
                startAdornment: <InputAdornment position="start"><LockIcon fontSize="small" sx={{ color: '#94A3B8' }} /></InputAdornment>,
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowPassword(!showPassword)} edge="end" size="small" sx={{ color: '#94A3B8' }}>
                      {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <TextField
              label="Confirm New Password"
              type={showPassword ? 'text' : 'password'}
              value={passwordData.confirm_password}
              onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
              InputProps={{ startAdornment: <InputAdornment position="start"><LockIcon fontSize="small" sx={{ color: '#94A3B8' }} /></InputAdornment> }}
            />
            <Button
              variant="contained"
              onClick={handlePasswordChange}
              disabled={isPasswordLoading}
              startIcon={isPasswordLoading ? <CircularProgress size={16} color="inherit" /> : null}
              sx={{ width: 'fit-content', px: 3 }}
            >
              {isPasswordLoading ? 'Updating…' : 'Update Password'}
            </Button>
          </Stack>
        </Paper>

      </Stack>
    </Box>
  );
};

export default ProfilePage;
