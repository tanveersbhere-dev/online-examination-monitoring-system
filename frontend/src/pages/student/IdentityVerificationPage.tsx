import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  LinearProgress,
  Paper,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import FaceIcon from '@mui/icons-material/Face';
import ReplayIcon from '@mui/icons-material/Replay';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import TipsAndUpdatesIcon from '@mui/icons-material/TipsAndUpdates';

type VerificationState = 'IDLE' | 'DETECTING' | 'VERIFYING' | 'SUCCESS' | 'FAILED';

const IdentityVerificationPage = () => {
  const navigate = useNavigate();
  const [state, setState] = useState<VerificationState>('IDLE');
  const [attempts, setAttempts] = useState(0);

  const startVerification = () => {
    setAttempts((a) => a + 1);
    setState('DETECTING');
    setTimeout(() => setState('VERIFYING'), 1500);
    setTimeout(() => {
      // Simulate success for now
      setState('SUCCESS');
    }, 3500);
  };

  const handleRetry = () => {
    setState('IDLE');
    setTimeout(startVerification, 300);
  };

  const overlayColor =
    state === 'SUCCESS' ? 'rgba(46,125,50,0.12)'
    : state === 'FAILED' ? 'rgba(176,0,32,0.12)'
    : 'transparent';

  const ovalColor =
    state === 'SUCCESS' ? '#2E7D32'
    : state === 'FAILED' ? '#B00020'
    : state === 'DETECTING' || state === 'VERIFYING' ? '#1565C0'
    : '#CFD8DC';

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <Box sx={{ textAlign: 'center' }}>
        <Typography variant="h4" fontWeight={600} gutterBottom>
          Identity Verification
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Position your face clearly in the frame below.
        </Typography>
      </Box>

      {/* Camera Preview Area */}
      <Box
        sx={{
          width: { xs: '100%', sm: 480 },
          height: 360,
          borderRadius: 4,
          backgroundColor: '#0A0A0A',
          border: `4px solid ${ovalColor}`,
          position: 'relative',
          overflow: 'hidden',
          transition: 'border-color 0.4s',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* Overlay */}
        <Box
          sx={{
            position: 'absolute', inset: 0,
            backgroundColor: overlayColor,
            transition: 'background-color 0.4s',
            zIndex: 2,
          }}
        />

        {/* Face placeholder */}
        <FaceIcon sx={{ fontSize: 120, color: 'rgba(255,255,255,0.1)', position: 'relative', zIndex: 1 }} />

        {/* Oval guide */}
        <Box
          sx={{
            position: 'absolute',
            width: 200, height: 260,
            border: `3px ${state === 'IDLE' ? 'dashed' : 'solid'} ${ovalColor}`,
            borderRadius: '50%',
            zIndex: 3,
            transition: 'border-color 0.4s',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
          }}
        />

        {/* Status icon overlay */}
        {state === 'SUCCESS' && (
          <CheckCircleIcon
            sx={{
              position: 'absolute', fontSize: 64,
              color: 'success.main', zIndex: 4,
              filter: 'drop-shadow(0 0 12px rgba(46,125,50,0.5))',
            }}
          />
        )}
        {state === 'FAILED' && (
          <CancelIcon
            sx={{
              position: 'absolute', fontSize: 64,
              color: 'error.main', zIndex: 4,
            }}
          />
        )}

        {/* Recording dot */}
        {(state === 'DETECTING' || state === 'VERIFYING') && (
          <Box sx={{ position: 'absolute', top: 12, right: 12, display: 'flex', alignItems: 'center', gap: 0.5, zIndex: 4 }}>
            <FiberManualRecordIcon sx={{ color: '#F44336', fontSize: 10 }} />
            <Typography variant="caption" sx={{ color: 'white', fontSize: '0.65rem' }}>LIVE</Typography>
          </Box>
        )}

        {/* Guide text */}
        {state === 'IDLE' && (
          <Typography
            variant="caption"
            sx={{
              position: 'absolute', bottom: 16, color: 'rgba(255,255,255,0.6)',
              textAlign: 'center', px: 2, zIndex: 4,
            }}
          >
            Keep your face centred and still
          </Typography>
        )}
      </Box>

      {/* Progress bar */}
      {(state === 'DETECTING' || state === 'VERIFYING') && (
        <Box sx={{ width: { xs: '100%', sm: 360 } }}>
          <LinearProgress sx={{ height: 4, borderRadius: 2 }} />
        </Box>
      )}

      {/* Status message */}
      <Typography
        variant="h6"
        fontWeight={600}
        sx={{
          color: state === 'SUCCESS' ? 'success.main'
            : state === 'FAILED' ? 'error.main'
            : state === 'DETECTING' ? 'warning.main'
            : state === 'VERIFYING' ? 'primary.main'
            : 'text.secondary',
          minHeight: 32,
        }}
      >
        {state === 'IDLE' && 'Ready to verify'}
        {state === 'DETECTING' && 'Detecting face...'}
        {state === 'VERIFYING' && 'Verifying Identity...'}
        {state === 'SUCCESS' && '✓ Identity Verified'}
        {state === 'FAILED' && 'Identity Verification Failed'}
      </Typography>

      {/* Action buttons */}
      <Box sx={{ display: 'flex', gap: 2 }}>
        {state === 'IDLE' && (
          <Button variant="contained" size="large" onClick={startVerification} sx={{ minWidth: 200 }}>
            Start Verification
          </Button>
        )}
        {state === 'FAILED' && attempts < 3 && (
          <Button variant="outlined" startIcon={<ReplayIcon />} onClick={handleRetry}>
            Try Again
          </Button>
        )}
        {state === 'SUCCESS' && (
          <Button
            variant="contained"
            color="success"
            endIcon={<ArrowForwardIcon />}
            onClick={() => navigate(`/student/exam?exam_id=${new URLSearchParams(window.location.search).get('exam_id')}`)}
            sx={{ minWidth: 200 }}
          >
            Begin Examination
          </Button>
        )}
      </Box>

      {/* Failure guidance */}
      {state === 'FAILED' && (
        <Alert severity="warning" icon={<TipsAndUpdatesIcon />} sx={{ maxWidth: 480, borderRadius: 2 }}>
          <Typography variant="body2" fontWeight={600} gutterBottom>Tips for successful verification:</Typography>
          <List dense disablePadding>
            {['Ensure adequate lighting from the front.', 'Remove glasses or hat if possible.', 'Move closer to the camera.', 'Avoid bright light behind you.'].map((tip) => (
              <ListItem key={tip} disablePadding sx={{ py: 0.25 }}>
                <ListItemIcon sx={{ minWidth: 24 }}><FiberManualRecordIcon sx={{ fontSize: 8, color: 'warning.main' }} /></ListItemIcon>
                <ListItemText primary={tip} primaryTypographyProps={{ variant: 'body2' }} />
              </ListItem>
            ))}
          </List>
          {attempts >= 3 && (
            <Typography variant="body2" sx={{ mt: 1, color: 'error.main', fontWeight: 600 }}>
              Please contact your examiner for assistance.
            </Typography>
          )}
        </Alert>
      )}
    </Box>
  );
};

export default IdentityVerificationPage;
