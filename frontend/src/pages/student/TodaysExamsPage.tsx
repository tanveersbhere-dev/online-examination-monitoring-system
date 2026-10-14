import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  TextField,
  Chip,
  Divider,
  Stack,
  InputAdornment,
  Grid,
  CircularProgress,
  Alert,
  AlertTitle,
  Tabs,
  Tab
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import TimerIcon from '@mui/icons-material/Timer';
import LoginIcon from '@mui/icons-material/Login';
import EventBusyIcon from '@mui/icons-material/EventBusy';
import RefreshIcon from '@mui/icons-material/Refresh';
import GradeIcon from '@mui/icons-material/Grade';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import { useState, useEffect } from 'react';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';

interface Exam {
  id: number;
  title: string;
  course_name: string | null;
  status: 'DRAFT' | 'SCHEDULED' | 'READY' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'CANCELLED';
  scheduled_start: string;
  scheduled_end: string;
  duration_minutes?: number;
  paper_duration_minutes?: number;
  session_id?: number;
  session_status?: string;
  evaluation_status?: 'PENDING' | 'EVALUATED' | 'IN_REVIEW' | 'NOT_STARTED' | string;
  total_score?: number | null;
  objective_score?: number | null;
  subjective_score?: number | null;
  total_marks?: number;
  passing_marks?: number;
  evaluated_at?: string | null;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  DRAFT: { label: 'Draft', color: '#546E7A', bg: '#ECEFF1' },
  SCHEDULED: { label: 'Scheduled', color: '#E65100', bg: '#FFF3E0' },
  READY: { label: 'Ready', color: '#E65100', bg: '#FFF3E0' },
  RUNNING: { label: 'Running', color: '#1565C0', bg: '#E3F2FD' },
  PAUSED: { label: 'Paused', color: '#F57C00', bg: '#FFF3E0' },
  COMPLETED: { label: 'Completed', color: '#2E7D32', bg: '#E8F5E9' },
  CANCELLED: { label: 'Cancelled', color: '#C62828', bg: '#FFEBEE' },
};

const isScheduledForToday = (exam: Exam): boolean => {
  if (!exam?.scheduled_start) return false;
  const startDate = new Date(exam.scheduled_start);
  if (isNaN(startDate.getTime())) return false;

  const today = new Date();
  
  const isSameLocalDate =
    startDate.getFullYear() === today.getFullYear() &&
    startDate.getMonth() === today.getMonth() &&
    startDate.getDate() === today.getDate();

  const isSameUTCDate =
    startDate.getUTCFullYear() === today.getUTCFullYear() &&
    startDate.getUTCMonth() === today.getUTCMonth() &&
    startDate.getUTCDate() === today.getUTCDate();

  return isSameLocalDate || isSameUTCDate;
};

const TodaysExamsPage = () => {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [allExams, setAllExams] = useState<Exam[]>([]);
  const [activeTab, setActiveTab] = useState<'today' | 'history'>('today');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchExams = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/students/me/exams');
      const rawExams: Exam[] = Array.isArray(response.data) ? response.data : [];
      setAllExams(rawExams);

      // Hydrate authoritative paper academic duration
      try {
        const enriched = await Promise.all(
          rawExams.map(async (ex) => {
            try {
              const timeRes = await apiClient.get(`/runtime/effective-time?exam_id=${ex.id}`);
              if (timeRes.data?.paper_duration_seconds) {
                const paperMins = Math.round(timeRes.data.paper_duration_seconds / 60);
                if (paperMins > 0) {
                  return { ...ex, paper_duration_minutes: paperMins };
                }
              }
            } catch (e) {}
            return ex;
          })
        );
        setAllExams(enriched);
      } catch (e) {}
    } catch (err: any) {
      console.error("Failed to fetch examinations", getErrorMessage(err));
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExams();
  }, []);

  const searchLower = (search || '').toLowerCase().trim();
  
  // Filter by tab and search
  const tabFiltered = allExams.filter((exam) => {
    if (activeTab === 'today') {
      return isScheduledForToday(exam);
    }
    // History tab shows all completed, past, or general exams
    return true;
  });

  const filtered = tabFiltered.filter((exam) => {
    const titleMatch = (exam?.title || '').toLowerCase().includes(searchLower);
    const courseMatch = (exam?.course_name || '').toLowerCase().includes(searchLower);
    return titleMatch || courseMatch;
  });

  return (
    <Box sx={{ pb: 6 }}>
      {/* ── Page Header ──────────────────────────────────────────────────── */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" fontWeight={800} sx={{ color: '#0F172A', letterSpacing: '-0.02em', mb: 0.5 }}>
          Student Examination Portal
        </Typography>
        <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.75, px: 1.5, py: 0.5, borderRadius: '8px', backgroundColor: '#EFF6FF' }}>
          <CalendarTodayIcon sx={{ fontSize: 13, color: '#2563EB' }} />
          <Typography variant="caption" sx={{ color: '#2563EB', fontWeight: 600, fontSize: '0.75rem' }}>
            {new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
          </Typography>
        </Box>
      </Box>

      {/* Tabs for switching between Today's Schedule & History */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, val) => setActiveTab(val)}>
          <Tab
            value="today"
            label="Today's Examinations"
            sx={{ textTransform: 'none', fontWeight: 700, fontSize: '0.9rem' }}
          />
          <Tab
            value="history"
            label="Exam History & Paper Evaluation"
            sx={{ textTransform: 'none', fontWeight: 700, fontSize: '0.9rem' }}
          />
        </Tabs>
      </Box>

      {/* Search & Refresh */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <TextField
          placeholder="Search by exam name or course..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          size="small"
          sx={{ maxWidth: 380, width: '100%', backgroundColor: '#FFFFFF', borderRadius: 2 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" sx={{ color: '#94A3B8' }} />
              </InputAdornment>
            ),
          }}
        />
        <Button
          startIcon={<RefreshIcon />}
          onClick={fetchExams}
          variant="outlined"
          size="small"
          sx={{ textTransform: 'none', fontWeight: 600, borderRadius: 2 }}
        >
          Refresh Status
        </Button>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
          <CircularProgress size={40} />
        </Box>
      ) : error ? (
        <Box sx={{ maxWidth: 600, mx: 'auto', py: 6 }}>
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" startIcon={<RefreshIcon />} onClick={fetchExams}>
                Retry
              </Button>
            }
          >
            <AlertTitle>Error Loading Examinations</AlertTitle>
            {error}
          </Alert>
        </Box>
      ) : filtered.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 10 }}>
          <Box sx={{
            width: 72, height: 72, borderRadius: '20px',
            backgroundColor: '#F1F5F9',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            mx: 'auto', mb: 2.5,
          }}>
            <EventBusyIcon sx={{ fontSize: 36, color: '#CBD5E1' }} />
          </Box>
          <Typography variant="h5" sx={{ color: '#475569', fontWeight: 700 }} gutterBottom>
            No Examinations Found
          </Typography>
          <Typography variant="body2" sx={{ color: '#94A3B8' }}>
            {search
              ? `No examinations match "${search}". Try clearing your search.`
              : activeTab === 'today'
              ? 'You have no examinations scheduled for today. Check the "Exam History" tab for previous papers.'
              : 'No past examinations found in your account.'}
          </Typography>
        </Box>
      ) : (
        <Grid container spacing={3}>
          {filtered.map((exam) => {
            const statusKey = exam?.status || 'DRAFT';
            const isCompleted = statusKey === 'COMPLETED' || exam?.session_status === 'COMPLETED';
            const isEvaluated = exam?.evaluation_status === 'EVALUATED' || (exam?.total_score !== null && exam?.total_score !== undefined && isCompleted);
            const isEvaluationAwaited = isCompleted && !isEvaluated;

            const cfg = STATUS_CONFIG[statusKey] || STATUS_CONFIG['DRAFT'];
            
            const startDate = exam?.scheduled_start ? new Date(exam.scheduled_start) : null;
            const endDate = exam?.scheduled_end ? new Date(exam.scheduled_end) : null;
            
            const startTimeFormatted = startDate && !isNaN(startDate.getTime())
              ? startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : 'N/A';
            const endTimeFormatted = endDate && !isNaN(endDate.getTime())
              ? endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              : 'N/A';

            // Allow entry if exam status is SCHEDULED, READY, RUNNING, or PAUSED
            const canEnter = ['SCHEDULED', 'READY', 'RUNNING', 'PAUSED'].includes(statusKey) && !isCompleted;
            const courseDisplayName = exam?.course_name ? exam.course_name : 'Course information unavailable';
            const examTitle = exam?.title ? exam.title : 'Untitled Examination';
            let duration = exam?.paper_duration_minutes || exam?.duration_minutes || 0;
            if (!duration && startDate && endDate && !isNaN(startDate.getTime()) && !isNaN(endDate.getTime())) {
              duration = Math.max(0, Math.round((endDate.getTime() - startDate.getTime()) / 60000));
            }
            const totalScore = exam?.total_score ?? 0;
            const maxMarks = exam?.total_marks ?? 100;
            const passMarks = exam?.passing_marks ?? 50;
            const hasPassed = totalScore >= passMarks;

            return (
              <Grid item xs={12} sm={6} lg={4} key={exam.id}>
                <Card
                  elevation={0}
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    border: '1px solid #E2E8F0',
                    borderRadius: 3,
                    overflow: 'hidden',
                    backgroundColor: '#FFFFFF',
                    transition: 'all 0.2s ease',
                    position: 'relative',
                    '&:hover': {
                      boxShadow: '0 8px 24px rgba(15,23,42,0.08)',
                      transform: 'translateY(-3px)',
                      borderColor: '#CBD5E1',
                    },
                    '&::before': {
                      content: '""',
                      position: 'absolute',
                      top: 0, left: 0, right: 0,
                      height: '4px',
                      backgroundColor: isEvaluated ? '#10B981' : isEvaluationAwaited ? '#F59E0B' : cfg.color,
                    },
                  }}
                >
                  <CardContent sx={{ flexGrow: 1, p: '24px !important', pt: '28px !important' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Chip
                        label={isEvaluated ? 'Evaluated' : isEvaluationAwaited ? 'Evaluation Awaited' : cfg.label}
                        size="small"
                        sx={{
                          backgroundColor: isEvaluated ? '#ECFDF5' : isEvaluationAwaited ? '#FFFBEB' : cfg.bg,
                          color: isEvaluated ? '#059669' : isEvaluationAwaited ? '#D97706' : cfg.color,
                          fontWeight: 700, fontSize: '0.72rem',
                          height: 24, letterSpacing: '0.02em',
                          border: `1px solid ${isEvaluated ? '#A7F3D0' : isEvaluationAwaited ? '#FDE68A' : 'transparent'}`
                        }}
                      />
                      <Box sx={{
                        display: 'flex', alignItems: 'center', gap: 0.5,
                        px: 1, py: 0.375, borderRadius: '7px',
                        backgroundColor: '#F1F5F9',
                      }}>
                        <AccessTimeIcon sx={{ fontSize: 12, color: '#64748B' }} />
                        <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600, fontSize: '0.7rem' }}>
                          {startTimeFormatted}
                        </Typography>
                      </Box>
                    </Box>

                    <Typography variant="h6" fontWeight={800} sx={{ color: '#0F172A', mb: 0.5, lineHeight: 1.3 }}>
                      {examTitle}
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        color: exam?.course_name ? '#64748B' : '#94A3B8',
                        fontStyle: exam?.course_name ? 'normal' : 'italic',
                        fontSize: '0.8125rem',
                        mb: 2
                      }}
                    >
                      {courseDisplayName}
                    </Typography>

                    {/* Paper Evaluation Status & Marks Section */}
                    {isEvaluated ? (
                      <Box sx={{
                        p: 2,
                        mb: 2,
                        borderRadius: 2.5,
                        backgroundColor: '#F0FDF4',
                        border: '1px solid #BBF7D0',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 1
                      }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Typography variant="caption" sx={{ color: '#166534', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <CheckCircleOutlineIcon sx={{ fontSize: 16 }} /> Paper Evaluated
                          </Typography>
                          <Chip
                            label={hasPassed ? 'Passed' : 'Needs Review'}
                            size="small"
                            color={hasPassed ? 'success' : 'warning'}
                            sx={{ height: 20, fontSize: '0.65rem', fontWeight: 800 }}
                          />
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
                          <Typography variant="h5" fontWeight={900} sx={{ color: '#15803D' }}>
                            {totalScore}
                          </Typography>
                          <Typography variant="body2" sx={{ color: '#166534', fontWeight: 600 }}>
                            / {maxMarks} marks ({Math.round((totalScore / (maxMarks || 1)) * 100)}%)
                          </Typography>
                        </Box>
                        {exam?.evaluated_at && (
                          <Typography variant="caption" sx={{ color: '#15803D', fontSize: '0.68rem' }}>
                            Graded on {new Date(exam.evaluated_at).toLocaleDateString()}
                          </Typography>
                        )}
                      </Box>
                    ) : isEvaluationAwaited ? (
                      <Box sx={{
                        p: 2,
                        mb: 2,
                        borderRadius: 2.5,
                        backgroundColor: '#FFFBEB',
                        border: '1px solid #FDE68A',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1.5
                      }}>
                        <HourglassEmptyIcon sx={{ color: '#D97706', fontSize: 28 }} />
                        <Box>
                          <Typography variant="subtitle2" fontWeight={700} sx={{ color: '#92400E' }}>
                            Evaluation Awaits
                          </Typography>
                          <Typography variant="caption" sx={{ color: '#B45309', display: 'block', lineHeight: 1.3 }}>
                            Your paper has been submitted. Examiner is reviewing your responses.
                          </Typography>
                        </Box>
                      </Box>
                    ) : null}

                    <Divider sx={{ my: 1.5 }} />

                    <Stack spacing={1}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
                        <Box sx={{
                          width: 24, height: 24, borderRadius: '6px',
                          backgroundColor: '#F1F5F9',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                        }}>
                          <TimerIcon sx={{ fontSize: 14, color: '#64748B' }} />
                        </Box>
                        <Typography variant="body2" sx={{ color: '#475569', fontSize: '0.8125rem' }}>
                          {duration} minutes
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
                        <Box sx={{
                          width: 24, height: 24, borderRadius: '6px',
                          backgroundColor: '#F1F5F9',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                        }}>
                          <CalendarTodayIcon sx={{ fontSize: 14, color: '#64748B' }} />
                        </Box>
                        <Typography variant="body2" sx={{ color: '#475569', fontSize: '0.8125rem' }}>
                          {startTimeFormatted} – {endTimeFormatted}
                        </Typography>
                      </Box>
                    </Stack>
                  </CardContent>

                  <Box sx={{ px: 3, pb: 3 }}>
                    <Button
                      variant={canEnter ? 'contained' : 'outlined'}
                      fullWidth
                      disabled={!canEnter}
                      startIcon={canEnter ? <LoginIcon /> : isEvaluated ? <GradeIcon /> : <HourglassEmptyIcon />}
                      onClick={() => navigate(`/student/instructions?exam_id=${exam.id}`)}
                      color={canEnter ? 'secondary' : 'inherit'}
                      sx={{
                        fontWeight: 700,
                        py: 1,
                        borderRadius: 2,
                        ...(canEnter && {
                          background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
                          '&:hover': { background: 'linear-gradient(135deg, #38BDF8 0%, #0EA5E9 100%)' },
                        }),
                      }}
                    >
                      {canEnter ? 'Enter Exam' : isEvaluated ? 'Exam Graded' : isEvaluationAwaited ? 'Evaluation Awaits' : 'Not Available'}
                    </Button>
                  </Box>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}
    </Box>
  );
};

export default TodaysExamsPage;
