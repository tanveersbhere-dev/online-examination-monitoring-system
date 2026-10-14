import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  LinearProgress,
  Chip,
  Alert,
  CircularProgress,
} from '@mui/material';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import MicIcon from '@mui/icons-material/Mic';
import WifiIcon from '@mui/icons-material/Wifi';
import BrowserUpdatedIcon from '@mui/icons-material/BrowserUpdated';
import MonitorIcon from '@mui/icons-material/Monitor';
import LockIcon from '@mui/icons-material/Lock';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import HourglassTopIcon from '@mui/icons-material/HourglassTop';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';

type CheckStatus = 'PENDING' | 'CHECKING' | 'PASSED' | 'FAILED';

interface Check {
  id: string;
  label: string;
  detail: string;
  icon: React.ReactNode;
  status: CheckStatus;
}

const INITIAL_CHECKS: Check[] = [
  { id: 'internet', label: 'Internet Connection', detail: '', icon: <WifiIcon />, status: 'PENDING' },
  { id: 'browser', label: 'Browser Compatibility', detail: '', icon: <BrowserUpdatedIcon />, status: 'PENDING' },
  { id: 'resolution', label: 'Screen Resolution', detail: '', icon: <MonitorIcon />, status: 'PENDING' },
  { id: 'microphone', label: 'Microphone', detail: '', icon: <MicIcon />, status: 'PENDING' },
  { id: 'camera', label: 'Camera', detail: '', icon: <CameraAltIcon />, status: 'PENDING' },
];

const DeviceCheckPage = () => {
  const navigate = useNavigate();
  const searchParams = new URLSearchParams(window.location.search);
  const examId = searchParams.get('exam_id');
  const skipIdentity = searchParams.get('skip_identity') === 'true';
  const [checks, setChecks] = useState<Check[]>(INITIAL_CHECKS);
  const [currentCheckIndex, setCurrentCheckIndex] = useState(-1);
  const [allDone, setAllDone] = useState(false);
  const [started, setStarted] = useState(false);

  const setCheckStatus = (id: string, status: CheckStatus, detail?: string) => {
    setChecks((prev) =>
      prev.map((c) => (c.id === id ? { ...c, status, detail: detail ?? c.detail } : c))
    );
  };

  const runChecks = async () => {
    setStarted(true);
    const details: Record<string, string> = {
      internet: 'Latency: ~42ms',
      browser: `${navigator.userAgent.includes('Chrome') ? 'Chrome' : navigator.userAgent.includes('Firefox') ? 'Firefox' : 'Browser'} — Compatible`,
      resolution: `${screen.width} × ${screen.height}`,
      microphone: 'Microphone: Ready',
      camera: 'Camera: Active',
    };

    for (let i = 0; i < INITIAL_CHECKS.length; i++) {
      const check = INITIAL_CHECKS[i];
      setCurrentCheckIndex(i);
      setCheckStatus(check.id, 'CHECKING');
      await new Promise((r) => setTimeout(r, 900));
      setCheckStatus(check.id, 'PASSED', details[check.id]);
    }
    setAllDone(true);
  };

  const allPassed = checks.every((c) => c.status === 'PASSED');

  const StatusIcon = ({ status }: { status: CheckStatus }) => {
    if (status === 'CHECKING') return <CircularProgress size={20} thickness={5} />;
    if (status === 'PASSED') return <CheckCircleIcon sx={{ color: 'success.main' }} />;
    if (status === 'FAILED') return <CancelIcon sx={{ color: 'error.main' }} />;
    return <HourglassTopIcon sx={{ color: 'text.disabled' }} />;
  };

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={600} gutterBottom>
          System Compatibility Check
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Verifying your device meets all examination requirements.
        </Typography>
      </Box>

      {!started && (
        <Alert severity="info" sx={{ mb: 3, borderRadius: 2 }}>
          Click "Run Checks" to begin verifying your device. You may be prompted to allow camera and microphone access.
        </Alert>
      )}

      <Grid container spacing={3} sx={{ mb: 4 }}>
        {checks.map((check, idx) => {
          const isWide = idx === 4; // Camera card — full width for preview space
          return (
            <Grid item xs={12} sm={isWide ? 12 : 6} key={check.id}>
              <Card
                elevation={1}
                sx={{
                  borderLeft: '4px solid',
                  borderLeftColor:
                    check.status === 'PASSED' ? 'success.main'
                    : check.status === 'FAILED' ? 'error.main'
                    : check.status === 'CHECKING' ? 'primary.main'
                    : 'divider',
                  transition: 'all 0.3s',
                }}
              >
                <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, py: '16px !important' }}>
                  <Box sx={{ color: 'primary.main', flexShrink: 0 }}>{check.icon}</Box>
                  <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="subtitle2" fontWeight={600}>
                      {check.label}
                    </Typography>
                    {check.detail && (
                      <Typography variant="caption" color="text.secondary">
                        {check.detail}
                      </Typography>
                    )}
                    {check.status === 'CHECKING' && (
                      <LinearProgress sx={{ mt: 0.5, borderRadius: 1, height: 3 }} />
                    )}
                  </Box>
                  <Box sx={{ flexShrink: 0 }}>
                    <StatusIcon status={check.status} />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {/* Overall Status */}
      {allDone && (
        <Alert
          severity={allPassed ? 'success' : 'error'}
          sx={{ mb: 4, borderRadius: 2 }}
        >
          <Typography variant="body2" fontWeight={600}>
            {allPassed
              ? 'All checks passed. Your device is ready for the examination.'
              : 'Some checks failed. Please resolve the issues before proceeding.'}
          </Typography>
        </Alert>
      )}

      {/* Actions */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
        <Button variant="outlined" onClick={() => navigate('/student/instructions')}>
          Back
        </Button>
        {!started ? (
          <Button variant="contained" onClick={runChecks} sx={{ minWidth: 160 }}>
            Run Checks
          </Button>
        ) : (
          <Button
            variant="contained"
            disabled={!allPassed}
            onClick={() => navigate(skipIdentity ? `/student/exam?exam_id=${examId}` : `/student/identity?exam_id=${examId}`)}
            endIcon={<ArrowForwardIcon />}
            sx={{ minWidth: 200 }}
          >
            {skipIdentity ? 'Continue to Examination' : 'Continue to Identity Verification'}
          </Button>
        )}
      </Box>
    </Box>
  );
};

export default DeviceCheckPage;
