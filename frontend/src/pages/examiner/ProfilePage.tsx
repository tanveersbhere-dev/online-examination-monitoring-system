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
      // Update local storage user details
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
    <Box sx={{ p: { xs: 2, md: 4 } }}>
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 4 }}>My Profile</Typography>

      <Stack spacing={4} sx={{ maxWidth: 800 }}>
        
        {/* Basic Info Section */}
        <Paper sx={{ p: 3, borderRadius: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Basic Information</Typography>
          <Divider sx={{ mb: 3 }} />
          
          {profileMessage && (
            <Alert severity={profileMessage.type} sx={{ mb: 3 }}>{profileMessage.text}</Alert>
          )}

          <Stack spacing={3}>
            <TextField
              label="Full Name"
              value={profileData.full_name}
              onChange={(e) => setProfileData({ ...profileData, full_name: e.target.value })}
              InputProps={{ startAdornment: <InputAdornment position="start"><PersonIcon fontSize="small" /></InputAdornment> }}
            />
            <TextField
              label="Phone Number"
              value={profileData.phone_number}
              onChange={(e) => setProfileData({ ...profileData, phone_number: e.target.value })}
              InputProps={{ startAdornment: <InputAdornment position="start"><PhoneIcon fontSize="small" /></InputAdornment> }}
            />
            <Button 
              variant="contained" 
              onClick={handleProfileUpdate} 
              disabled={isUpdatingProfile}
              sx={{ width: 'fit-content' }}
            >
              {isUpdatingProfile ? <CircularProgress size={24} /> : 'Save Changes'}
            </Button>
          </Stack>
        </Paper>

        {/* Email Address Section */}
        <Paper sx={{ p: 3, borderRadius: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Email Address</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Current Email: <strong>{user?.email}</strong>
          </Typography>
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
                InputProps={{ startAdornment: <InputAdornment position="start"><EmailIcon fontSize="small" /></InputAdornment> }}
              />
              <Button variant="outlined" onClick={handleEmailRequest} disabled={!newEmail || isEmailLoading}>
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
              <Button variant="contained" onClick={handleEmailVerify} disabled={!emailOtp || isEmailLoading}>
                Verify & Update Email
              </Button>
            </Stack>
          )}
        </Paper>

        {/* Change Password Section */}
        <Paper sx={{ p: 3, borderRadius: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Change Password</Typography>
          <Divider sx={{ mb: 3 }} />

          {passwordMessage && (
            <Alert severity={passwordMessage.type} sx={{ mb: 3 }}>{passwordMessage.text}</Alert>
          )}

          <Stack spacing={3}>
            <TextField
              label="Current Password"
              type={showPassword ? 'text' : 'password'}
              value={passwordData.current_password}
              onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
              InputProps={{ startAdornment: <InputAdornment position="start"><LockIcon fontSize="small" /></InputAdornment> }}
            />
            <TextField
              label="New Password"
              type={showPassword ? 'text' : 'password'}
              value={passwordData.new_password}
              onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
              InputProps={{
                startAdornment: <InputAdornment position="start"><LockIcon fontSize="small" /></InputAdornment>,
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowPassword(!showPassword)} edge="end" size="small">
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
              InputProps={{ startAdornment: <InputAdornment position="start"><LockIcon fontSize="small" /></InputAdornment> }}
            />
            <Button 
              variant="contained" 
              onClick={handlePasswordChange} 
              disabled={isPasswordLoading}
              sx={{ width: 'fit-content' }}
            >
              {isPasswordLoading ? <CircularProgress size={24} /> : 'Update Password'}
            </Button>
          </Stack>
        </Paper>

      </Stack>
    </Box>
  );
};

export default ProfilePage;
