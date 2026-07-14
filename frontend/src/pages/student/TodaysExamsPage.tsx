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
  CircularProgress
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import TimerIcon from '@mui/icons-material/Timer';
import LoginIcon from '@mui/icons-material/Login';
import EventBusyIcon from '@mui/icons-material/EventBusy';
import { useState, useEffect } from 'react';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';

interface Exam {
  id: number;
  title: string;
  course_name: string;
  status: 'DRAFT' | 'SCHEDULED' | 'READY' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'CANCELLED';
  scheduled_start: string;
  scheduled_end: string;
  duration_minutes: number;
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

const TodaysExamsPage = () => {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchExams = async () => {
      try {
        const response = await apiClient.get('/students/me/exams');
        // Filter for exams scheduled for today
        const todayStr = new Date().toISOString().split('T')[0];
        const todaysExams = response.data.filter((exam: Exam) => {
          return exam.scheduled_start.startsWith(todayStr);
        });
        setExams(todaysExams);
      } catch (error: any) {
        console.error("Failed to fetch today's exams", getErrorMessage(error));
      } finally {
        setLoading(false);
      }
    };
    fetchExams();
  }, []);

  const filtered = exams.filter((exam) => {
    return exam.title.toLowerCase().includes(search.toLowerCase()) ||
           exam.course_name.toLowerCase().includes(search.toLowerCase());
  });

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={600} gutterBottom>
          Today's Examinations
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Showing examinations scheduled for{' '}
          {new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
        </Typography>
      </Box>

      <Box sx={{ display: 'flex', mb: 4 }}>
        <TextField
          placeholder="Search by exam name or course..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          size="small"
          sx={{ maxWidth: 360, width: '100%' }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" sx={{ color: 'text.secondary' }} />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
          <CircularProgress />
        </Box>
      ) : filtered.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 10 }}>
          <EventBusyIcon sx={{ fontSize: 80, color: 'action.disabled', mb: 2 }} />
          <Typography variant="h5" color="text.secondary" fontWeight={600} gutterBottom>
            No Examinations Found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            You have no examinations scheduled for today.
          </Typography>
        </Box>
      ) : (
        <Grid container spacing={3}>
          {filtered.map((exam) => {
            const cfg = STATUS_CONFIG[exam.status] || STATUS_CONFIG['DRAFT'];
            const startDate = new Date(exam.scheduled_start);
            const endDate = new Date(exam.scheduled_end);
            
            // Allow entry if exam is scheduled, ready, running, or paused
            const canEnter = ['SCHEDULED', 'READY', 'RUNNING', 'PAUSED'].includes(exam.status);

            return (
              <Grid item xs={12} sm={6} lg={4} key={exam.id}>
                <Card
                  elevation={1}
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    transition: 'all 0.2s',
                    '&:hover': { boxShadow: 3, transform: 'translateY(-2px)' },
                  }}
                >
                  <CardContent sx={{ flexGrow: 1, p: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Chip
                        label={cfg.label}
                        size="small"
                        sx={{ backgroundColor: cfg.bg, color: cfg.color, fontWeight: 600, fontSize: '0.75rem' }}
                      />
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <AccessTimeIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                        <Typography variant="caption" color="text.secondary">
                          {startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </Typography>
                      </Box>
                    </Box>

                    <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                      {exam.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      {exam.course_name}
                    </Typography>

                    <Divider sx={{ my: 2 }} />

                    <Stack spacing={0.5}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <TimerIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                        <Typography variant="body2" color="text.secondary">
                          {exam.duration_minutes} Minutes
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <CalendarTodayIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                        <Typography variant="body2" color="text.secondary">
                          {startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </Typography>
                      </Box>
                    </Stack>
                  </CardContent>

                  <Box sx={{ px: 3, pb: 3 }}>
                    <Button
                      variant="contained"
                      fullWidth
                      disabled={!canEnter}
                      startIcon={<LoginIcon />}
                      onClick={() => navigate(`/student/instructions?exam_id=${exam.id}`)}
                      sx={{ borderRadius: 2 }}
                    >
                      {canEnter ? 'Enter Exam' : 'Not Available'}
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
