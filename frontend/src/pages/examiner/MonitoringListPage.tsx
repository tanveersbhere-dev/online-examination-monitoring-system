import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';
import {
  Box, Typography, Grid, Card, CardContent, Chip, Button,
  Stack, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Paper, IconButton, Tooltip, CircularProgress, Alert
} from '@mui/material';
import VideocamIcon from '@mui/icons-material/Videocam';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import ShieldIcon from '@mui/icons-material/Shield';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import RefreshIcon from '@mui/icons-material/Refresh';
import PersonIcon from '@mui/icons-material/Person';
import SchoolIcon from '@mui/icons-material/School';

interface ActiveSession {
  session_id: number;
  exam_id: number;
  exam_title: string;
  student_id: number;
  student_name: string;
  student_reg_no: string;
  start_time: string | null;
  session_status: string;
  monitoring_status: string;
  current_risk: number;
  risk_level: string;
  active_violations_count: number;
  total_violations_count: number;
  latest_event: string | null;
  camera_status: string;
}

const MonitoringListPage = () => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchActiveSessions = async () => {
    try {
      const res = await apiClient.get<ActiveSession[]>('/monitoring/active-sessions');
      setSessions(res.data || []);
      setError(null);
    } catch (err: any) {
      console.error('Failed to fetch active monitoring sessions', getErrorMessage(err));
      setError('Unable to load active sessions. Please verify your connection.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActiveSessions();
    const interval = setInterval(fetchActiveSessions, 4000);
    return () => clearInterval(interval);
  }, []);

  const getRiskColor = (level: string) => {
    switch (level?.toUpperCase()) {
      case 'CRITICAL': return { bg: '#FEE2E2', text: '#DC2626', border: '#FCA5A5' };
      case 'HIGH': return { bg: '#FEF3C7', text: '#D97706', border: '#FCD34D' };
      case 'MEDIUM': return { bg: '#FEF9C3', text: '#CA8A04', border: '#FDE047' };
      default: return { bg: '#D1FAE5', text: '#059669', border: '#A7F3D0' };
    }
  };

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" fontWeight={800} sx={{ color: '#0F172A', letterSpacing: '-0.02em', mb: 0.5 }}>
            Live Candidate Monitoring
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748B' }}>
            Real-time proctoring feeds and AI compliance status for active examination attempts
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box sx={{
            display: 'flex', alignItems: 'center', gap: 0.75,
            px: 1.5, py: 0.5, borderRadius: '999px',
            backgroundColor: '#D1FAE5', border: '1px solid #A7F3D0',
          }}>
            <FiberManualRecordIcon sx={{ fontSize: 8, color: '#059669' }} />
            <Typography variant="caption" sx={{ color: '#059669', fontWeight: 700, fontSize: '0.75rem' }}>
              {sessions.length} ACTIVE {sessions.length === 1 ? 'SESSION' : 'SESSIONS'}
            </Typography>
          </Box>

          <Button
            variant="outlined"
            size="small"
            startIcon={<RefreshIcon />}
            onClick={fetchActiveSessions}
            sx={{ fontWeight: 600, borderColor: '#E2E8F0', color: '#475569' }}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 10 }}>
          <CircularProgress size={36} />
        </Box>
      ) : sessions.length === 0 ? (
        <Paper
          elevation={0}
          sx={{
            p: 6,
            textAlign: 'center',
            borderRadius: 3,
            border: '1px dashed #CBD5E1',
            backgroundColor: '#F8FAFC'
          }}
        >
          <VideocamIcon sx={{ fontSize: 48, color: '#94A3B8', mb: 1.5 }} />
          <Typography variant="h6" fontWeight={700} sx={{ color: '#1E293B', mb: 0.5 }}>
            No Monitored Exams Currently In Progress
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748B', maxWidth: 460, mx: 'auto' }}>
            When registered students enter their scheduled examinations and grant camera access, their AI telemetry and video feeds will appear here automatically.
          </Typography>
        </Paper>
      ) : (
        <Grid container spacing={2.5}>
          {sessions.map((session) => {
            const riskStyles = getRiskColor(session.risk_level);
            return (
              <Grid item xs={12} sm={6} lg={4} key={session.session_id}>
                <Card
                  elevation={0}
                  sx={{
                    border: '1px solid #E2E8F0',
                    borderRadius: 3,
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      boxShadow: '0 8px 24px rgba(15,23,42,0.08)',
                      borderColor: '#94A3B8'
                    }
                  }}
                >
                  <CardContent sx={{ p: 2.5 }}>
                    {/* Top Row: Reg No & Risk Badge */}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
                      <Box>
                        <Typography variant="h6" fontWeight={700} sx={{ color: '#0F172A', fontSize: '1rem', mb: 0.25 }}>
                          {session.student_name}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600 }}>
                          {session.student_reg_no || `Student #${session.student_id}`}
                        </Typography>
                      </Box>
                      <Chip
                        label={`${session.risk_level} RISK`}
                        size="small"
                        sx={{
                          backgroundColor: riskStyles.bg,
                          color: riskStyles.text,
                          border: `1px solid ${riskStyles.border}`,
                          fontWeight: 700,
                          fontSize: '0.675rem'
                        }}
                      />
                    </Box>

                    {/* Exam Name */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5, p: 1, backgroundColor: '#F8FAFC', borderRadius: 1.5 }}>
                      <SchoolIcon sx={{ fontSize: 18, color: '#64748B' }} />
                      <Typography variant="body2" fontWeight={600} noWrap sx={{ color: '#334155', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {session.exam_title}
                      </Typography>
                    </Box>

                    {/* Telemetry Stats Grid */}
                    <Grid container spacing={1} sx={{ mb: 2 }}>
                      <Grid item xs={6}>
                        <Box sx={{ p: 1, border: '1px solid #F1F5F9', borderRadius: 1.5 }}>
                          <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', fontSize: '0.65rem' }}>
                            CAMERA STATUS
                          </Typography>
                          <Typography variant="body2" fontWeight={700} sx={{ color: session.camera_status === 'CONNECTED' ? '#059669' : '#DC2626' }}>
                            ● {session.camera_status}
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6}>
                        <Box sx={{ p: 1, border: '1px solid #F1F5F9', borderRadius: 1.5 }}>
                          <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', fontSize: '0.65rem' }}>
                            ACTIVE ALERTS
                          </Typography>
                          <Typography variant="body2" fontWeight={700} sx={{ color: session.active_violations_count > 0 ? '#DC2626' : '#059669' }}>
                            {session.active_violations_count} {session.active_violations_count === 1 ? 'alert' : 'alerts'}
                          </Typography>
                        </Box>
                      </Grid>
                    </Grid>

                    {/* Latest Event summary */}
                    <Box sx={{ mb: 2, minHeight: 36 }}>
                      <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', fontSize: '0.65rem', mb: 0.25 }}>
                        LATEST AI EVENT
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#475569', fontWeight: 500, lineHeight: 1.3, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {session.latest_event || 'No active infractions reported.'}
                      </Typography>
                    </Box>

                    {/* Action Button */}
                    <Button
                      variant="contained"
                      fullWidth
                      endIcon={<ArrowForwardIcon />}
                      onClick={() => navigate(`/examiner/monitoring/${session.session_id}`)}
                      sx={{
                        fontWeight: 700,
                        textTransform: 'none',
                        borderRadius: 2,
                        py: 1,
                        backgroundColor: '#0F172A',
                        '&:hover': { backgroundColor: '#1E293B' }
                      }}
                    >
                      Open Live Feed & AI Panel
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}
    </Box>
  );
};

export default MonitoringListPage;
