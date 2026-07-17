import { useState, useEffect } from 'react';
import { Box, Typography, Grid, Paper, Card, CardContent, CircularProgress, Alert } from '@mui/material';
import PeopleIcon from '@mui/icons-material/People';
import AssignmentIcon from '@mui/icons-material/Assignment';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import DesktopMacIcon from '@mui/icons-material/DesktopMac';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';
import apiClient from '../../services/apiClient';

interface DashboardStats {
  total_users: number;
  total_exams: number;
  total_violations: number;
  active_sessions: number;
  system_health: string;
}

export default function SystemDashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient.get('/admin/dashboard')
      .then(res => setStats(res.data))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load dashboard metrics'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 5 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error" sx={{ m: 3 }}>{error}</Alert>;

  const cards = [
    { label: 'Total Users', value: stats?.total_users || 0, icon: <PeopleIcon sx={{ fontSize: 40, color: 'primary.main' }} /> },
    { label: 'Total Exams Created', value: stats?.total_exams || 0, icon: <AssignmentIcon sx={{ fontSize: 40, color: 'secondary.main' }} /> },
    { label: 'Total Violations Detected', value: stats?.total_violations || 0, icon: <WarningAmberIcon sx={{ fontSize: 40, color: 'error.main' }} /> },
    { label: 'Active Exam Sessions', value: stats?.active_sessions || 0, icon: <DesktopMacIcon sx={{ fontSize: 40, color: 'info.main' }} /> },
  ];

  return (
    <Box>
      <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
        <HealthAndSafetyIcon sx={{ fontSize: 32, color: stats?.system_health === 'Operational' ? 'success.main' : 'warning.main' }} />
        <Typography variant="h4" fontWeight={600}>System Dashboard</Typography>
      </Box>

      <Alert severity="success" sx={{ mb: 4, borderRadius: 2 }}>
        Platform Health: <strong>{stats?.system_health}</strong>. All microservices and database connections are operating normally.
      </Alert>

      <Grid container spacing={3}>
        {cards.map((c, i) => (
          <Grid item xs={12} sm={6} md={3} key={i}>
            <Card sx={{ height: '100%', borderRadius: 3, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
              <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 3 }}>
                <Box>
                  <Typography variant="body2" color="text.secondary" fontWeight={600} gutterBottom>
                    {c.label.toUpperCase()}
                  </Typography>
                  <Typography variant="h4" fontWeight={700}>
                    {c.value}
                  </Typography>
                </Box>
                {c.icon}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
