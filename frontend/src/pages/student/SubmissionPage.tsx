import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Divider,
  Stack,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import TimerIcon from '@mui/icons-material/Timer';
import QuizIcon from '@mui/icons-material/Quiz';
import ShieldIcon from '@mui/icons-material/Shield';
import LogoutIcon from '@mui/icons-material/Logout';

const SubmissionPage = () => {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(160deg, #FAFAFA 60%, #E8F5E9 100%)',
        px: 3,
      }}
    >
      {/* Success Animation Area */}
      <Box
        sx={{
          width: 96, height: 96,
          borderRadius: '50%',
          backgroundColor: 'success.light',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          mb: 3,
          boxShadow: '0 0 0 12px rgba(46,125,50,0.08)',
        }}
      >
        <CheckCircleIcon sx={{ fontSize: 56, color: 'success.main' }} />
      </Box>

      <Typography variant="h3" fontWeight={700} color="success.main" gutterBottom textAlign="center">
        Examination Submitted
      </Typography>
      <Typography variant="body1" color="text.secondary" textAlign="center" sx={{ mb: 4, maxWidth: 440 }}>
        Your responses have been securely recorded. Thank you for completing your examination.
      </Typography>

      {/* Submission Details Card */}
      <Card elevation={1} sx={{ width: '100%', maxWidth: 440, mb: 4 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom color="primary.main">
            Submission Summary
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Stack spacing={2}>
            {[
              { icon: <AccessTimeIcon fontSize="small" />, label: 'Submission Time', value: '10:47:32 AM, 13 July 2026' },
              { icon: <TimerIcon fontSize="small" />, label: 'Duration', value: '1 hour, 47 minutes' },
              { icon: <QuizIcon fontSize="small" />, label: 'Questions Answered', value: '8 of 10' },
              { icon: <ShieldIcon fontSize="small" />, label: 'Monitoring Status', value: 'Session Complete' },
            ].map((row) => (
              <Box key={row.label} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'text.secondary' }}>
                  {row.icon}
                  <Typography variant="body2" color="text.secondary">{row.label}</Typography>
                </Box>
                <Typography variant="body2" fontWeight={600}>{row.value}</Typography>
              </Box>
            ))}
          </Stack>
        </CardContent>
      </Card>

      <Typography variant="body2" color="text.secondary" textAlign="center" sx={{ mb: 4, maxWidth: 400 }}>
        Your session and monitoring logs have been securely saved. You may now safely close this window.
      </Typography>

      <Button
        variant="outlined"
        size="large"
        startIcon={<LogoutIcon />}
        onClick={() => navigate('/')}
        sx={{ borderRadius: 2, px: 4 }}
      >
        End Session & Logout
      </Button>
    </Box>
  );
};

export default SubmissionPage;
