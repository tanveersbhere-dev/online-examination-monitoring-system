import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Divider,
  Stack,
  CircularProgress,
  Chip,
  Paper
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import TimerIcon from '@mui/icons-material/Timer';
import QuizIcon from '@mui/icons-material/Quiz';
import ShieldIcon from '@mui/icons-material/Shield';
import LogoutIcon from '@mui/icons-material/Logout';
import DashboardIcon from '@mui/icons-material/Dashboard';
import apiClient from '../../services/apiClient';

interface SubmissionSummary {
  session_id?: number;
  exam_id?: number;
  exam_title?: string;
  status?: string;
  submission_time?: string;
  start_time?: string;
  duration_seconds?: number;
  duration_formatted?: string;
  answered_count?: number;
  total_questions?: number;
  monitoring_status?: string;
}

const SubmissionPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const [summary, setSummary] = useState<SubmissionSummary | null>(location.state?.summary || null);
  const [loading, setLoading] = useState<boolean>(!location.state?.summary);

  useEffect(() => {
    if (summary) return;

    // Fallback: If page was reloaded or navigated directly, fetch the authoritative summary from backend
    const fetchSummary = async () => {
      const examId = searchParams.get('exam_id') || localStorage.getItem('last_active_exam_id');
      if (!examId) {
        setLoading(false);
        return;
      }

      try {
        const res = await apiClient.get(`/runtime/submission-summary?exam_id=${examId}`);
        if (res.data) {
          setSummary(res.data);
        }
      } catch (err) {
        console.warn('Could not fetch latest submission summary:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, [searchParams, summary]);

  // Formatted date string helper
  const formatSubmissionTime = (isoString?: string) => {
    if (!isoString) return new Date().toLocaleString();
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
        ', ' +
        date.toLocaleDateString([], { day: 'numeric', month: 'long', year: 'numeric' });
    } catch {
      return new Date().toLocaleString();
    }
  };

  const formattedSubmissionTime = formatSubmissionTime(summary?.submission_time);
  const formattedDuration = summary?.duration_formatted || (summary?.duration_seconds ? `${Math.floor(summary.duration_seconds / 60)} min, ${summary.duration_seconds % 60} sec` : 'Few moments');
  const answeredCountText = summary?.total_questions ? `${summary.answered_count || 0} of ${summary.total_questions}` : `${summary?.answered_count || 0} recorded`;

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(160deg, #F8FAFC 60%, #E8F5E9 100%)',
        px: 3,
        py: 5,
      }}
    >
      {/* Success Animation Area */}
      <Box
        sx={{
          width: 88,
          height: 88,
          borderRadius: '50%',
          backgroundColor: '#DCFCE7',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          mb: 2.5,
          boxShadow: '0 0 0 12px rgba(34, 197, 94, 0.12)',
        }}
      >
        <CheckCircleIcon sx={{ fontSize: 52, color: '#16A34A' }} />
      </Box>

      <Typography variant="h4" fontWeight={800} color="#15803D" gutterBottom textAlign="center" letterSpacing="-0.02em">
        Examination Submitted
      </Typography>
      <Typography variant="body1" color="text.secondary" textAlign="center" sx={{ mb: 3.5, maxWidth: 480, fontSize: '0.95rem', lineHeight: 1.6 }}>
        Your responses for <strong>{summary?.exam_title || 'your examination'}</strong> have been securely recorded and finalized.
      </Typography>

      {/* Submission Details Card */}
      <Card elevation={0} sx={{ width: '100%', maxWidth: 480, mb: 3.5, border: '1px solid #E2E8F0', borderRadius: 3, bgcolor: '#FFFFFF', boxShadow: '0 4px 20px rgba(0,0,0,0.04)' }}>
        <CardContent sx={{ p: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1.5}>
            <Typography variant="subtitle1" fontWeight={700} color="#0F172A">
              Submission Summary
            </Typography>
            <Chip
              label="Verified & Recorded"
              size="small"
              sx={{ bgcolor: '#DCFCE7', color: '#15803D', fontWeight: 700, fontSize: '0.65rem', height: 22 }}
            />
          </Box>
          <Divider sx={{ mb: 2.5 }} />

          {loading ? (
            <Box display="flex" justifyContent="center" py={3}>
              <CircularProgress size={28} />
            </Box>
          ) : (
            <Stack spacing={2}>
              {[
                {
                  icon: <AccessTimeIcon fontSize="small" sx={{ color: '#64748B' }} />,
                  label: 'Submission Time',
                  value: formattedSubmissionTime
                },
                {
                  icon: <TimerIcon fontSize="small" sx={{ color: '#64748B' }} />,
                  label: 'Duration',
                  value: formattedDuration
                },
                {
                  icon: <QuizIcon fontSize="small" sx={{ color: '#64748B' }} />,
                  label: 'Questions Answered',
                  value: answeredCountText
                },
                {
                  icon: <ShieldIcon fontSize="small" sx={{ color: '#16A34A' }} />,
                  label: 'Monitoring Status',
                  value: summary?.monitoring_status || 'Session Complete'
                },
              ].map((row) => (
                <Box key={row.label} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
                    {row.icon}
                    <Typography variant="body2" sx={{ color: '#64748B', fontWeight: 500 }}>
                      {row.label}
                    </Typography>
                  </Box>
                  <Typography variant="body2" fontWeight={700} color="#0F172A">
                    {row.value}
                  </Typography>
                </Box>
              ))}
            </Stack>
          )}
        </CardContent>
      </Card>

      <Typography variant="caption" color="#64748B" textAlign="center" sx={{ mb: 3.5, maxWidth: 420, display: 'block' }}>
        Your answers and proctoring telemetry logs have been securely encrypted and submitted. You may now safely return to your student dashboard or logout.
      </Typography>

      <Stack direction="row" spacing={2}>
        <Button
          variant="contained"
          size="medium"
          startIcon={<DashboardIcon />}
          onClick={() => navigate('/student/dashboard')}
          sx={{ borderRadius: 2, px: 3, fontWeight: 700, textTransform: 'none' }}
        >
          Return to Dashboard
        </Button>
        <Button
          variant="outlined"
          size="medium"
          startIcon={<LogoutIcon />}
          onClick={() => {
            localStorage.removeItem('access_token');
            navigate('/student/login');
          }}
          sx={{ borderRadius: 2, px: 3, fontWeight: 600, textTransform: 'none' }}
        >
          End Session & Logout
        </Button>
      </Stack>
    </Box>
  );
};

export default SubmissionPage;
