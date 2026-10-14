import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../services/apiClient';
import { useAuth } from '../../hooks/useAuth';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Chip,
  CircularProgress,
  Alert,
  Avatar,
  Stack,
  Skeleton
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import MonitorIcon from '@mui/icons-material/Monitor';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import PeopleIcon from '@mui/icons-material/People';
import AssignmentIcon from '@mui/icons-material/Assignment';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import EventNoteIcon from '@mui/icons-material/EventNote';
import DescriptionIcon from '@mui/icons-material/Description';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';

// Type definitions matching the backend schemas
interface StatCard {
  label: string;
  value: string;
  sub: string;
  icon_name: string;
  accent_color: string;
  path?: string;
}

interface UpcomingExam {
  id: number;
  name: string;
  course: string;
  scheduled_date?: string | null;
  students_count: number;
}

interface ActivityResponse {
  id: number;
  action_type: string;
  description: string;
  created_at: string;
}

interface NotificationResponse {
  id: number;
  title: string;
  message: string;
  severity: string;
  created_at: string;
}

interface DashboardSummary {
  stats: StatCard[];
  upcoming_exams: UpcomingExam[];
  recent_activities: ActivityResponse[];
  recent_notifications: NotificationResponse[];
  system_status: string;
}

const getIconByName = (name: string) => {
  switch (name) {
    case 'PlayArrowIcon': return <PlayArrowIcon />;
    case 'CalendarTodayIcon': return <CalendarTodayIcon />;
    case 'PeopleIcon': return <PeopleIcon />;
    case 'WarningAmberIcon': return <WarningAmberIcon />;
    case 'NotificationsActiveIcon': return <NotificationsActiveIcon />;
    case 'HealthAndSafetyIcon': return <HealthAndSafetyIcon />;
    case 'DescriptionIcon': return <DescriptionIcon />;
    default: return <AssignmentIcon />;
  }
};

const DashboardPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const response = await apiClient.get('/workspace/dashboard/summary');
        setSummary(response.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load dashboard data.');
      } finally {
        setLoading(false);
      }
    };
    fetchSummary();
  }, []);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  if (loading) {
    return (
      <Box sx={{ p: 0 }}>
        <Skeleton variant="text" width={280} height={44} sx={{ mb: 0.5 }} />
        <Skeleton variant="text" width={180} height={22} sx={{ mb: 4 }} />
        <Grid container spacing={2.5} sx={{ mb: 4 }}>
          {[...Array(4)].map((_, i) => (
            <Grid item xs={12} sm={6} md={3} key={i}>
              <Skeleton variant="rectangular" height={130} sx={{ borderRadius: 2 }} />
            </Grid>
          ))}
        </Grid>
        <Grid container spacing={2.5}>
          <Grid item xs={12} md={7}>
            <Skeleton variant="rectangular" height={320} sx={{ borderRadius: 2 }} />
          </Grid>
          <Grid item xs={12} md={5}>
            <Skeleton variant="rectangular" height={320} sx={{ borderRadius: 2 }} />
          </Grid>
        </Grid>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 0 }}>
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
        <Button variant="outlined" onClick={() => window.location.reload()}>Retry</Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* ── Greeting ─────────────────────────────────────────────────────── */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={800} sx={{ color: '#0F172A', letterSpacing: '-0.02em', mb: 0.5 }}>
          {greeting},{' '}
          <Box component="span" sx={{ color: '#2563EB' }}>
            {user?.full_name?.split(' ')[0] || 'Examiner'}
          </Box>
        </Typography>
        <Typography variant="body2" sx={{ color: '#64748B', fontWeight: 500 }}>
          {new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
        </Typography>
      </Box>

      {/* ── Stat Cards ───────────────────────────────────────────────────── */}
      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        {summary?.stats.map((card) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={card.label}>
            <Card
              elevation={0}
              sx={{
                border: '1px solid #F1F5F9',
                cursor: card.path ? 'pointer' : 'default',
                transition: 'all 0.2s ease',
                position: 'relative',
                overflow: 'hidden',
                '&:hover': card.path ? {
                  boxShadow: '0 8px 24px rgba(15,23,42,0.10)',
                  transform: 'translateY(-3px)',
                  borderColor: '#E2E8F0',
                } : {},
                // Top accent stripe
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0, left: 0, right: 0,
                  height: '3px',
                  backgroundColor: card.accent_color,
                  borderRadius: '12px 12px 0 0',
                },
              }}
              onClick={() => card.path && navigate(card.path)}
            >
              <CardContent sx={{ p: '20px !important' }}>
                <Box sx={{
                  width: 40, height: 40, borderRadius: '10px',
                  backgroundColor: `${card.accent_color}18`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: card.accent_color,
                  mb: 2,
                }}>
                  {getIconByName(card.icon_name)}
                </Box>
                <Typography variant="h4" fontWeight={800} sx={{
                  color: card.label === 'Critical Alerts' && card.value !== '0' ? '#DC2626' : '#0F172A',
                  letterSpacing: '-0.02em',
                  mb: 0.25,
                }}>
                  {card.value}
                </Typography>
                <Typography variant="caption" fontWeight={600} display="block" sx={{ color: '#1E293B', mb: 0.25, fontSize: '0.8rem' }}>
                  {card.label}
                </Typography>
                <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.7rem' }}>{card.sub}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* ── Bottom Row ───────────────────────────────────────────────────── */}
      <Grid container spacing={2.5}>
        
        {/* Upcoming / Active Exams */}
        <Grid item xs={12} md={7}>
          <Card elevation={0} sx={{ height: '100%', border: '1px solid #F1F5F9' }}>
            <CardContent sx={{ p: '24px !important' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
                  <Box sx={{
                    width: 32, height: 32, borderRadius: '8px',
                    background: 'rgba(37,99,235,0.1)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <MonitorIcon sx={{ fontSize: 18, color: '#2563EB' }} />
                  </Box>
                  <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#0F172A', fontSize: '0.9375rem' }}>
                    Upcoming &amp; Active Exams
                  </Typography>
                </Box>
                <Button
                  size="small"
                  onClick={() => navigate('/examiner/exams')}
                  endIcon={<ArrowForwardIcon fontSize="small" />}
                  sx={{ fontWeight: 600, fontSize: '0.8125rem' }}
                >
                  View All
                </Button>
              </Box>
              <Divider sx={{ mb: 2 }} />
              {summary?.upcoming_exams.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 5 }}>
                  <Box sx={{
                    width: 52, height: 52, borderRadius: '14px',
                    background: '#F1F5F9',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    mx: 'auto', mb: 2,
                  }}>
                    <AssignmentIcon sx={{ fontSize: 26, color: '#CBD5E1' }} />
                  </Box>
                  <Typography variant="body2" sx={{ color: '#94A3B8', fontWeight: 500 }}>
                    No upcoming exams scheduled.
                  </Typography>
                </Box>
              ) : (
                <List disablePadding>
                  {summary?.upcoming_exams.map((exam, idx) => (
                    <Box key={exam.id}>
                      <ListItem disablePadding sx={{ py: 1.5 }}>
                        <Box sx={{
                          width: 8, height: 8, borderRadius: '50%',
                          backgroundColor: '#2563EB', mr: 2, flexShrink: 0,
                        }} />
                        <ListItemText
                          primary={<Typography variant="body2" fontWeight={600} sx={{ color: '#0F172A' }}>{exam.name}</Typography>}
                          secondary={
                            <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                              {exam.scheduled_date ? new Date(exam.scheduled_date).toLocaleString() : 'Not Scheduled (Draft)'}
                            </Typography>
                          }
                        />
                        <ListItemSecondaryAction>
                          <Button
                            size="small"
                            variant="outlined"
                            endIcon={<OpenInNewIcon fontSize="small" />}
                            onClick={() => navigate('/examiner/exams')}
                            sx={{ fontSize: '0.75rem', py: 0.5, px: 1.5 }}
                          >
                            Details
                          </Button>
                        </ListItemSecondaryAction>
                      </ListItem>
                      {idx < summary.upcoming_exams.length - 1 && <Divider />}
                    </Box>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Activity Feed */}
        <Grid item xs={12} md={5}>
          <Card elevation={0} sx={{ height: '100%', border: '1px solid #F1F5F9' }}>
            <CardContent sx={{ p: '24px !important' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
                  <Box sx={{
                    width: 32, height: 32, borderRadius: '8px',
                    background: 'rgba(14,165,233,0.1)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <EventNoteIcon sx={{ fontSize: 18, color: '#0EA5E9' }} />
                  </Box>
                  <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#0F172A', fontSize: '0.9375rem' }}>
                    Recent Activity
                  </Typography>
                </Box>
              </Box>
              <Divider sx={{ mb: 2 }} />
              {summary?.recent_activities.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 5, borderRadius: 2, backgroundColor: '#F8FAFC' }}>
                  <Typography variant="body2" sx={{ color: '#94A3B8', fontWeight: 500 }}>
                    No recent activities.
                  </Typography>
                </Box>
              ) : (
                <List disablePadding>
                  {summary?.recent_activities.map((act, idx) => (
                    <Box key={act.id}>
                      <ListItem disablePadding sx={{ py: 1.5 }}>
                        <Box sx={{
                          width: 6, height: 6, borderRadius: '50%',
                          backgroundColor: '#0EA5E9', mr: 2, flexShrink: 0,
                        }} />
                        <ListItemText
                          primary={<Typography variant="body2" fontWeight={500} sx={{ color: '#1E293B' }}>{act.description}</Typography>}
                          secondary={
                            <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                              {new Date(act.created_at).toLocaleString()}
                            </Typography>
                          }
                        />
                      </ListItem>
                      {idx < summary.recent_activities.length - 1 && <Divider />}
                    </Box>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

      </Grid>
    </Box>
  );
};

export default DashboardPage;
