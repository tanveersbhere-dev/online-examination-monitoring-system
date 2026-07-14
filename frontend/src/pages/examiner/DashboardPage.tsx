import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActionArea,
  Grid,
  Button,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Chip,
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

const STAT_CARDS = [
  { label: 'Running Exams', value: '3', sub: 'Currently active', icon: <PlayArrowIcon />, accent: '#2E7D32', path: '/examiner/monitoring' },
  { label: "Today's Exams", value: '7', sub: 'Scheduled today', icon: <CalendarTodayIcon />, accent: '#1565C0', path: '/examiner/exams' },
  { label: 'Registered Students', value: '142', sub: 'Total registered', icon: <PeopleIcon />, accent: '#1976D2', path: '/examiner/students' },
  { label: "Today's Violations", value: '12', sub: 'Since midnight', icon: <WarningAmberIcon />, accent: '#E65100', path: '/examiner/reports' },
  { label: 'Critical Alerts', value: '2', sub: 'Require attention', icon: <NotificationsActiveIcon />, accent: '#B00020', path: '/examiner/monitoring' },
  { label: 'System Health', value: 'Online', sub: 'All services running', icon: <HealthAndSafetyIcon />, accent: '#2E7D32', path: null },
];

const RUNNING_EXAMS = [
  { name: 'Data Structures & Algorithms', course: 'CS-301', students: 24 },
  { name: 'Database Management Systems', course: 'CS-302', students: 18 },
  { name: 'Operating Systems', course: 'CS-303', students: 31 },
];

const ALERTS = [
  { student: 'Ahmed Raza', violation: 'Identity Mismatch', time: '2 min ago', severity: 'critical' },
  { student: 'Sara Malik', violation: 'Phone Detected', time: '5 min ago', severity: 'high' },
];

const DashboardPage = () => {
  const navigate = useNavigate();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  return (
    <Box>
      {/* Greeting */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight={600}>
          {greeting}, Examiner
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
        </Typography>
      </Box>

      {/* Stat Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {STAT_CARDS.map((card) => (
          <Grid item xs={12} sm={6} md={4} lg={2} key={card.label}>
            <Card
              elevation={1}
              sx={{
                borderLeft: `4px solid ${card.accent}`,
                cursor: card.path ? 'pointer' : 'default',
                transition: 'all 0.2s',
                '&:hover': card.path ? { boxShadow: 3, transform: 'translateY(-2px)' } : {},
              }}
              onClick={() => card.path && navigate(card.path)}
            >
              <CardContent sx={{ p: '20px !important' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                  <Box sx={{ color: card.accent, opacity: 0.8 }}>{card.icon}</Box>
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
        {/* Running Exams */}
        <Grid item xs={12} md={7}>
          <Card elevation={1}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="subtitle1" fontWeight={600} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <MonitorIcon fontSize="small" color="primary" />
                  Active Examinations
                </Typography>
                <Chip label="● Live" size="small" sx={{ backgroundColor: '#E8F5E9', color: '#2E7D32', fontWeight: 600, fontSize: '0.7rem' }} />
              </Box>
              <Divider sx={{ mb: 2 }} />
              {RUNNING_EXAMS.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
                  <AssignmentIcon sx={{ fontSize: 48, mb: 1, opacity: 0.3 }} />
                  <Typography variant="body2">No exams currently running.</Typography>
                </Box>
              ) : (
                <List disablePadding>
                  {RUNNING_EXAMS.map((exam, idx) => (
                    <Box key={idx}>
                      <ListItem disablePadding sx={{ py: 1.5 }}>
                        <ListItemText
                          primary={<Typography variant="body2" fontWeight={600}>{exam.name}</Typography>}
                          secondary={`${exam.course} · ${exam.students} students`}
                        />
                        <ListItemSecondaryAction>
                          <Button
                            size="small"
                            endIcon={<OpenInNewIcon fontSize="small" />}
                            onClick={() => navigate('/examiner/monitoring')}
                          >
                            View Live
                          </Button>
                        </ListItemSecondaryAction>
                      </ListItem>
                      {idx < RUNNING_EXAMS.length - 1 && <Divider />}
                    </Box>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Alerts */}
        <Grid item xs={12} md={5}>
          <Card elevation={1}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="subtitle1" fontWeight={600} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <NotificationsActiveIcon fontSize="small" color="error" />
                  Recent Alerts
                </Typography>
              </Box>
              <Divider sx={{ mb: 2 }} />
              {ALERTS.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4, backgroundColor: '#E8F5E9', borderRadius: 2 }}>
                  <HealthAndSafetyIcon sx={{ fontSize: 48, color: '#2E7D32', mb: 1 }} />
                  <Typography variant="body2" color="success.main" fontWeight={600}>No active alerts</Typography>
                </Box>
              ) : (
                <List disablePadding>
                  {ALERTS.map((alert, idx) => (
                    <Box key={idx}>
                      <ListItem disablePadding sx={{ py: 1.5 }}>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                              <Typography variant="body2" fontWeight={600}>{alert.student}</Typography>
                              <Chip
                                label={alert.violation}
                                size="small"
                                sx={{
                                  backgroundColor: alert.severity === 'critical' ? '#FFEBEE' : '#FFF3E0',
                                  color: alert.severity === 'critical' ? '#B00020' : '#E65100',
                                  fontSize: '0.7rem',
                                  height: 20,
                                }}
                              />
                            </Box>
                          }
                          secondary={alert.time}
                        />
                        <ListItemSecondaryAction>
                          <Button size="small" onClick={() => navigate('/examiner/reports')}>View</Button>
                        </ListItemSecondaryAction>
                      </ListItem>
                      {idx < ALERTS.length - 1 && <Divider />}
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
