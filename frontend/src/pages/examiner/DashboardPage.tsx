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
  scheduled_date: string;
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
      <Box sx={{ p: 2 }}>
        <Skeleton variant="text" width={250} height={40} />
        <Skeleton variant="text" width={150} height={20} sx={{ mb: 4 }} />
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {[...Array(4)].map((_, i) => (
            <Grid item xs={12} sm={6} md={3} key={i}>
              <Skeleton variant="rectangular" height={140} sx={{ borderRadius: 2 }} />
            </Grid>
          ))}
        </Grid>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Skeleton variant="rectangular" height={300} sx={{ borderRadius: 2 }} />
          </Grid>
          <Grid item xs={12} md={6}>
            <Skeleton variant="rectangular" height={300} sx={{ borderRadius: 2 }} />
          </Grid>
        </Grid>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
        <Button variant="outlined" onClick={() => window.location.reload()}>Retry</Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Greeting */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={600}>
          {greeting}, {user?.full_name || 'Examiner'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
        </Typography>
      </Box>

      {/* Stat Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {summary?.stats.map((card) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={card.label}>
            <Card
              elevation={1}
              sx={{
                borderLeft: `4px solid ${card.accent_color}`,
                cursor: card.path ? 'pointer' : 'default',
                transition: 'all 0.2s',
                '&:hover': card.path ? { boxShadow: 3, transform: 'translateY(-2px)' } : {},
              }}
              onClick={() => card.path && navigate(card.path)}
            >
              <CardContent sx={{ p: '20px !important' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                  <Box sx={{ color: card.accent_color, opacity: 0.8 }}>
                    {getIconByName(card.icon_name)}
                  </Box>
                </Box>
                <Typography variant="h4" fontWeight={700} sx={{ color: card.label === 'Critical Alerts' && card.value !== '0' ? 'error.main' : 'text.primary' }}>
                  {card.value}
                </Typography>
                <Typography variant="caption" fontWeight={600} display="block" gutterBottom>
                  {card.label}
                </Typography>
                <Typography variant="caption" color="text.secondary">{card.sub}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Bottom Row */}
      <Grid container spacing={3}>
        
        {/* Upcoming / Active Exams */}
        <Grid item xs={12} md={7}>
          <Card elevation={1} sx={{ height: '100%' }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="subtitle1" fontWeight={600} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <MonitorIcon fontSize="small" color="primary" />
                  Upcoming & Active Exams
                </Typography>
                <Button size="small" onClick={() => navigate('/examiner/exams')}>View All</Button>
              </Box>
              <Divider sx={{ mb: 2 }} />
              {summary?.upcoming_exams.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
                  <AssignmentIcon sx={{ fontSize: 48, mb: 1, opacity: 0.3 }} />
                  <Typography variant="body2">No upcoming exams found.</Typography>
                </Box>
              ) : (
                <List disablePadding>
                  {summary?.upcoming_exams.map((exam, idx) => (
                    <Box key={exam.id}>
                      <ListItem disablePadding sx={{ py: 1.5 }}>
                        <ListItemText
                          primary={<Typography variant="body2" fontWeight={600}>{exam.name}</Typography>}
                          secondary={`${new Date(exam.scheduled_date).toLocaleString()}`}
                        />
                        <ListItemSecondaryAction>
                          <Button
                            size="small"
                            endIcon={<OpenInNewIcon fontSize="small" />}
                            onClick={() => navigate(`/examiner/exams`)}
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
          <Card elevation={1} sx={{ height: '100%' }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="subtitle1" fontWeight={600} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <EventNoteIcon fontSize="small" color="secondary" />
                  Recent Activity
                </Typography>
              </Box>
              <Divider sx={{ mb: 2 }} />
              {summary?.recent_activities.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4, backgroundColor: '#f8fafc', borderRadius: 2 }}>
                  <Typography variant="body2" color="text.secondary">No recent activities.</Typography>
                </Box>
              ) : (
                <List disablePadding>
                  {summary?.recent_activities.map((act, idx) => (
                    <Box key={act.id}>
                      <ListItem disablePadding sx={{ py: 1.5 }}>
                        <ListItemText
                          primary={<Typography variant="body2" fontWeight={500}>{act.description}</Typography>}
                          secondary={new Date(act.created_at).toLocaleString()}
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
