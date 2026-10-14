import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Checkbox,
  FormControlLabel,
  Divider,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Grid,
  Chip,
  Paper,
  Stack,
  CircularProgress,
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import BlockIcon from '@mui/icons-material/Block';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import HeadphonesIcon from '@mui/icons-material/Headphones';
import PeopleIcon from '@mui/icons-material/People';
import DesktopWindowsIcon from '@mui/icons-material/DesktopWindows';
import WebcamIcon from '@mui/icons-material/Videocam';
import MouseIcon from '@mui/icons-material/Mouse';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import ShieldIcon from '@mui/icons-material/Shield';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import TabIcon from '@mui/icons-material/Tab';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';

const RULES = [
  'You must be alone in the room throughout the examination.',
  'Your face must remain clearly visible in the camera at all times.',
  'Identity verification is continuous — face mismatch will be flagged.',
  'Do not navigate away from the examination tab or window.',
  'No electronic devices other than the examination device are permitted.',
  'Do not communicate with anyone during the examination.',
  'All activity is recorded and reviewed by the examiner.',
  'Violation of any rule may result in automatic disqualification.',
];

const PROHIBITED = [
  { icon: <PhoneAndroidIcon />, label: 'Mobile Phone' },
  { icon: <MenuBookIcon />, label: 'Books or Notes' },
  { icon: <HeadphonesIcon />, label: 'Earphones / Headphones' },
  { icon: <PeopleIcon />, label: 'Other Persons' },
  { icon: <DesktopWindowsIcon />, label: 'Second Screen' },
  { icon: <BlockIcon />, label: 'Communication Apps' },
];

const ALLOWED = [
  { icon: <DesktopWindowsIcon />, label: 'Examination Device' },
  { icon: <WebcamIcon />, label: 'Webcam' },
  { icon: <MouseIcon />, label: 'Mouse & Keyboard' },
];

interface ExamDetails {
  id: number;
  title: string;
  course_name: string;
  duration_minutes?: number;
  paper_duration_minutes?: number;
  scheduled_start?: string;
  scheduled_end?: string;
}

const ExamInstructionsPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const examId = searchParams.get('exam_id');
  
  const [accepted, setAccepted] = useState(false);
  const [exam, setExam] = useState<ExamDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleProceed = async () => {
    if (!examId) return;
    setLoading(true);
    setError(null);
    try {
      const policyRes = await apiClient.get('/runtime/verification-policy', {
        params: { exam_id: examId }
      });
      const { requires_verification, can_proceed, message } = policyRes.data;

      if (requires_verification && !can_proceed) {
        setError(message || "This exam requires identity verification, but no approved reference image is available for your account. Please contact your examiner.");
        return;
      }

      if (!requires_verification) {
        // Exam does NOT require identity verification, proceed to device check -> direct to exam
        navigate(`/student/device-check?exam_id=${examId}&skip_identity=true`);
      } else {
        navigate(`/student/device-check?exam_id=${examId}`);
      }
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!examId) {
      setError("No examination specified. Please return to your dashboard.");
      setLoading(false);
      return;
    }

    const fetchExam = async () => {
      try {
        const response = await apiClient.get(`/exams/${examId}`);
        const examData = response.data;
        try {
          const timeRes = await apiClient.get(`/runtime/effective-time?exam_id=${examId}`);
          if (timeRes.data?.paper_duration_seconds) {
            const paperMins = Math.round(timeRes.data.paper_duration_seconds / 60);
            if (paperMins > 0) {
              examData.paper_duration_minutes = paperMins;
            }
          }
        } catch (e) {}
        setExam(examData);
      } catch (err: any) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    fetchExam();
  }, [examId]);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}><CircularProgress /></Box>;
  
  if (error) return (
    <Box sx={{ maxWidth: 600, mx: 'auto', mt: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={600} gutterBottom>
          Examination Instructions & Regulations
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Please review the rules carefully before proceeding to your examination.
        </Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
      <Button variant="outlined" sx={{ mt: 2 }} onClick={() => navigate('/student')}>Back to Dashboard</Button>
    </Box>
  );

  const startDate = exam?.scheduled_start ? new Date(exam.scheduled_start) : null;
  const endDate = exam?.scheduled_end ? new Date(exam.scheduled_end) : null;
  let duration = exam?.paper_duration_minutes || exam?.duration_minutes || 0;
  if (!duration && startDate && endDate && !isNaN(startDate.getTime()) && !isNaN(endDate.getTime())) {
    duration = Math.max(0, Math.round((endDate.getTime() - startDate.getTime()) / 60000));
  }
  const startTimeFormatted = startDate && !isNaN(startDate.getTime())
    ? startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : 'N/A';

  return (
    <Box>
      {/* Exam Info Card */}
      <Card elevation={0} sx={{ mb: 4, backgroundColor: 'primary.light', border: '1px solid', borderColor: '#BBDEFB' }}>
        <CardContent sx={{ p: 3 }}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                Examination
              </Typography>
              <Typography variant="h5" fontWeight={600} sx={{ mt: 0.5 }}>
                {exam?.title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {exam?.course_name}
              </Typography>
            </Grid>
            <Divider orientation="vertical" flexItem sx={{ mx: 1, display: { xs: 'none', md: 'block' } }} />
            <Grid item xs={12} md={5}>
              <Stack spacing={1}>
                <Box sx={{ display: 'flex', gap: 4 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Duration</Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {duration > 0 ? `${duration} Minutes` : 'N/A'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Start Time</Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {startTimeFormatted}
                    </Typography>
                  </Box>
                </Box>
                <Chip label="AI-Monitored Examination" size="small" sx={{ backgroundColor: 'primary.main', color: 'white', width: 'fit-content' }} />
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Typography variant="h6" fontWeight={600} gutterBottom>
        Instructions & Rules
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Please read all instructions carefully. By continuing, you agree to comply with all rules and acknowledge that AI-based proctoring will be active during this examination.
      </Typography>

      {/* ===== Controlled Examination Environment Warning ===== */}
      <Paper
        elevation={0}
        sx={{
          mb: 3,
          border: '1.5px solid',
          borderColor: 'warning.main',
          borderRadius: 2,
          overflow: 'hidden',
        }}
      >
        {/* Warning header */}
        <Box
          sx={{
            px: 2.5,
            py: 1.5,
            bgcolor: '#FFF3E0',
            display: 'flex',
            alignItems: 'center',
            gap: 1.5,
            borderBottom: '1px solid',
            borderColor: 'warning.light',
          }}
        >
          <WarningAmberIcon sx={{ color: 'warning.dark', fontSize: 22 }} />
          <Typography variant="subtitle1" fontWeight={700} color="warning.dark">
            Controlled Examination Environment
          </Typography>
        </Box>

        {/* Warning body */}
        <Box sx={{ px: 2.5, py: 2 }}>
          <Typography variant="body2" color="text.primary" sx={{ mb: 1.5, lineHeight: 1.7 }}>
            You are about to start a <strong>monitored examination</strong>. Once the examination
            begins, you will be placed in <strong>fullscreen mode</strong>.
          </Typography>

          {/* Two key requirements as chips */}
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} sx={{ mb: 2 }}>
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                p: 1,
                borderRadius: 1,
                bgcolor: '#FFF8E1',
                border: '1px solid',
                borderColor: 'warning.light',
                flex: 1,
              }}
            >
              <FullscreenIcon sx={{ color: 'warning.dark', fontSize: 20 }} />
              <Box>
                <Typography variant="caption" fontWeight={700} color="warning.dark" display="block">
                  Stay in Fullscreen
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Exiting fullscreen is recorded as a HIGH-RISK violation
                </Typography>
              </Box>
            </Box>

            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                p: 1,
                borderRadius: 1,
                bgcolor: '#FFF8E1',
                border: '1px solid',
                borderColor: 'warning.light',
                flex: 1,
              }}
            >
              <TabIcon sx={{ color: 'warning.dark', fontSize: 20 }} />
              <Box>
                <Typography variant="caption" fontWeight={700} color="warning.dark" display="block">
                  No Tab Switching
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Switching tabs or windows is recorded as a HIGH-RISK violation
                </Typography>
              </Box>
            </Box>
          </Stack>

          <Alert
            severity="error"
            icon={<ShieldIcon fontSize="small" />}
            sx={{ borderRadius: 1.5, py: 0.5 }}
          >
            <Typography variant="caption" fontWeight={600}>
              Both violations are logged with timestamp and duration, and are immediately visible
              to the examiner. Repeated violations may result in disqualification.
            </Typography>
          </Alert>
        </Box>
      </Paper>
      {/* ===== End Controlled Examination Environment Warning ===== */}

      <Grid container spacing={4} sx={{ mb: 4 }}>
        {/* Rules List */}
        <Grid item xs={12} lg={8}>
          <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <List sx={{ py: 0 }}>
              {RULES.map((rule, idx) => (
                <Box key={idx}>
                  <ListItem sx={{ py: 2 }}>
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      <CheckCircleIcon color="primary" fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary={rule} primaryTypographyProps={{ variant: 'body2' }} />
                  </ListItem>
                  {idx < RULES.length - 1 && <Divider component="li" />}
                </Box>
              ))}
            </List>
          </Paper>
        </Grid>

        {/* Allowed / Prohibited */}
        <Grid item xs={12} lg={4}>
          <Stack spacing={3}>
            {/* Prohibited Items */}
            <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'error.main', borderRadius: 2, overflow: 'hidden' }}>
              <Box sx={{ bgcolor: '#FFEBEE', px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
                <WarningAmberIcon color="error" fontSize="small" />
                <Typography variant="subtitle2" color="error.dark">Prohibited Items</Typography>
              </Box>
              <Grid container sx={{ p: 2 }}>
                {PROHIBITED.map((item, idx) => (
                  <Grid item xs={6} key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                    <Box sx={{ color: 'text.secondary', display: 'flex' }}>{item.icon}</Box>
                    <Typography variant="caption">{item.label}</Typography>
                  </Grid>
                ))}
              </Grid>
            </Paper>

            {/* Allowed Items */}
            <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'success.main', borderRadius: 2, overflow: 'hidden' }}>
              <Box sx={{ bgcolor: '#E8F5E9', px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
                <InfoIcon color="success" fontSize="small" />
                <Typography variant="subtitle2" color="success.dark">Allowed Items</Typography>
              </Box>
              <Grid container sx={{ p: 2 }}>
                {ALLOWED.map((item, idx) => (
                  <Grid item xs={12} key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                    <Box sx={{ color: 'text.secondary', display: 'flex' }}>{item.icon}</Box>
                    <Typography variant="caption">{item.label}</Typography>
                  </Grid>
                ))}
              </Grid>
            </Paper>
          </Stack>
        </Grid>
      </Grid>

      {/* Acceptance & Action */}
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 6, p: 4, bgcolor: 'background.paper', borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
        <FormControlLabel
          control={<Checkbox checked={accepted} onChange={(e) => setAccepted(e.target.checked)} />}
          label={<Typography variant="body2" fontWeight={500}>I have read and understood all the rules, and I consent to video monitoring.</Typography>}
          sx={{ mb: 3 }}
        />
        <Button
          variant="contained"
          size="large"
          disabled={!accepted || loading}
          endIcon={loading ? <CircularProgress size={20} /> : <ArrowForwardIcon />}
          onClick={handleProceed}
          sx={{ px: 6, py: 1.5, borderRadius: 999 }}
        >
          {loading ? 'Checking Policy...' : 'Proceed to Device Check'}
        </Button>
      </Box>
    </Box>
  );
};

export default ExamInstructionsPage;
