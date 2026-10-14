import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import apiClient from '../../services/apiClient';
import { WebSocketClient } from '../../services/wsClient';
import {
  Box, Typography, Button, Stack, IconButton, Chip, Dialog,
  DialogTitle, DialogContent, DialogActions, DialogContentText,
  CircularProgress, Card, CardContent, Grid, Paper, Divider, Alert
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import PauseIcon from '@mui/icons-material/Pause';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import VideocamIcon from '@mui/icons-material/Videocam';
import ShieldIcon from '@mui/icons-material/Shield';
import PersonIcon from '@mui/icons-material/Person';
import TimelineIcon from '@mui/icons-material/Timeline';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import AssessmentIcon from '@mui/icons-material/Assessment';

interface StudentMetadata {
  name: string;
  email: string;
  regNo: string;
  studentId: number;
  examTitle: string;
  examId: number;
  sessionStatus: string;
}

const LiveMonitoringPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId?: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const activeSessionId = sessionId || searchParams.get('session_id') || searchParams.get('exam_id') || '1';

  const [studentInfo, setStudentInfo] = useState<StudentMetadata | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [liveFrameBase64, setLiveFrameBase64] = useState<string | null>(null);
  const [connected, setConnected] = useState<boolean>(false);
  const [events, setEvents] = useState<any[]>([]);
  const [riskScore, setRiskScore] = useState<number>(0);

  // Actions Dialog
  const [actionDialog, setActionDialog] = useState<'pause' | 'resume' | 'end' | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    const fetchMetadata = async () => {
      setLoading(true);
      try {
        const reviewRes = await apiClient.get(`/exam-sessions/${activeSessionId}/review`);
        if (reviewRes.data?.summary && isMounted) {
          const s = reviewRes.data.summary;
          setStudentInfo({
            name: s.student_name || 'Candidate',
            email: s.student_email || '',
            regNo: s.registration_number || `ID: #${s.student_id}`,
            studentId: s.student_id,
            examTitle: s.exam_title || 'Examination Session',
            examId: s.exam_id,
            sessionStatus: s.status || 'RUNNING'
          });
        }
      } catch (err) {
        console.warn('Session metadata load error:', err);
      }

      try {
        const currentRes = await apiClient.get(`/monitoring/current?exam_session_id=${activeSessionId}`);
        if (currentRes.data && isMounted) {
          setRiskScore(currentRes.data.current_risk_score || 0);
          if (Array.isArray(currentRes.data.timeline_events)) {
            setEvents(currentRes.data.timeline_events);
          }
        }
      } catch (err) {
        console.warn('Monitoring current status load error:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchMetadata();
    return () => { isMounted = false; };
  }, [activeSessionId]);

  useEffect(() => {
    const ws = new WebSocketClient(parseInt(activeSessionId));

    ws.onMessage((data: any) => {
      setConnected(true);
      if (data.event === 'MONITORING_FRAME' && data.payload?.image_base64) {
        const rawB64 = data.payload.image_base64;
        const imgSrc = rawB64.startsWith('data:') ? rawB64 : `data:image/jpeg;base64,${rawB64}`;
        setLiveFrameBase64(imgSrc);
      }

      if (data.event === 'VIOLATION_CREATED' || data.event === 'VIOLATION_UPDATED') {
        const payload = data.payload || {};
        setEvents(prev => [
          {
            event_type: payload.violation_type || 'VIOLATION',
            severity: payload.severity || 'HIGH',
            description: payload.description || 'Violation detected',
            timestamp: new Date().toISOString()
          },
          ...prev.slice(0, 49)
        ]);
      }
    });

    return () => {
      ws.disconnect();
    };
  }, [activeSessionId]);

  const handleProctorAction = async (action: 'pause' | 'resume' | 'end') => {
    setActionLoading(true);
    try {
      if (action === 'pause') {
        await apiClient.post(`/runtime/suspend`, { exam_id: studentInfo?.examId || 1, reason: 'Proctor Paused' });
      } else if (action === 'resume') {
        await apiClient.post(`/runtime/resume`, { exam_id: studentInfo?.examId || 1 });
      } else if (action === 'end') {
        await apiClient.post(`/runtime/submit`, null, { params: { exam_id: studentInfo?.examId || 1 } });
      }
      setActionDialog(null);
    } catch (err) {
      console.error('Proctor action failed:', err);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ pb: 6 }}>
      {/* Header Bar */}
      <Card elevation={1} sx={{ p: 2.5, mb: 3, borderRadius: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <IconButton onClick={() => navigate(-1)} sx={{ border: '1px solid #cbd5e1' }}>
              <ArrowBackIcon />
            </IconButton>
            <Box>
              <Typography variant="h5" fontWeight={700} color="primary.main">
                Live Monitoring: {studentInfo?.name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {studentInfo?.examTitle} · {studentInfo?.regNo}
              </Typography>
            </Box>
          </Stack>

          <Stack direction="row" spacing={1.5} alignItems="center">
            <Chip
              icon={<FiberManualRecordIcon style={{ color: connected ? '#22c55e' : '#f59e0b', fontSize: 12 }} />}
              label={connected ? 'Stream Active' : 'Connecting...'}
              size="small"
              variant="outlined"
            />
            <Button
              variant="outlined"
              color="warning"
              size="small"
              startIcon={<PauseIcon />}
              onClick={() => setActionDialog('pause')}
            >
              Pause Session
            </Button>
            <Button
              variant="contained"
              color="error"
              size="small"
              startIcon={<StopIcon />}
              onClick={() => setActionDialog('end')}
            >
              Terminate
            </Button>
          </Stack>
        </Box>
      </Card>

      <Grid container spacing={3}>
        {/* Left Column: Live Feed / Placeholder */}
        <Grid item xs={12} md={7}>
          <Card elevation={1} sx={{ borderRadius: 2, overflow: 'hidden' }}>
            <Box sx={{ bgcolor: '#0f172a', height: 420, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
              {liveFrameBase64 ? (
                <img
                  src={liveFrameBase64}
                  alt="Candidate Live Feed"
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                />
              ) : (
                <Box sx={{ textAlign: 'center', color: '#94a3b8', p: 4 }}>
                  <VideocamIcon sx={{ fontSize: 64, mb: 1, opacity: 0.6 }} />
                  <Typography variant="subtitle1" fontWeight={600}>
                    Live Camera Stream
                  </Typography>
                  <Typography variant="caption" display="block">
                    Independent Monitoring Unit Integration Boundary
                  </Typography>
                </Box>
              )}
            </Box>
            <CardContent sx={{ p: 2.5 }}>
              <Grid container spacing={2}>
                <Grid item xs={6} sm={4}>
                  <Typography variant="caption" color="text.secondary">Candidate</Typography>
                  <Typography variant="body2" fontWeight={700}>{studentInfo?.name}</Typography>
                </Grid>
                <Grid item xs={6} sm={4}>
                  <Typography variant="caption" color="text.secondary">Status</Typography>
                  <Typography variant="body2" fontWeight={700}>{studentInfo?.sessionStatus}</Typography>
                </Grid>
                <Grid item xs={6} sm={4}>
                  <Typography variant="caption" color="text.secondary">Risk Score</Typography>
                  <Typography variant="body2" fontWeight={700} color={riskScore > 50 ? 'error.main' : 'success.main'}>
                    {riskScore} / 100
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Right Column: Recent Events & Proctor Controls */}
        <Grid item xs={12} md={5}>
          <Card elevation={1} sx={{ borderRadius: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ p: 3, flexGrow: 1 }}>
              <Typography variant="h6" fontWeight={700} color="primary.main" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TimelineIcon fontSize="small" /> Real-Time Telemetry & Events
              </Typography>
              <Divider sx={{ my: 1.5 }} />

              {events.length === 0 ? (
                <Box sx={{ py: 6, textAlign: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    No active events or violations recorded for this session.
                  </Typography>
                </Box>
              ) : (
                <Stack spacing={1.5} sx={{ maxHeight: 420, overflowY: 'auto' }}>
                  {events.map((evt, idx) => (
                    <Paper key={idx} variant="outlined" sx={{ p: 1.5, borderRadius: 1.5 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                        <Typography variant="caption" fontWeight={700} color="text.primary">
                          {evt.event_type || 'EVENT'}
                        </Typography>
                        <Chip
                          label={evt.severity || 'INFO'}
                          size="small"
                          color={evt.severity === 'CRITICAL' ? 'error' : evt.severity === 'HIGH' ? 'warning' : 'default'}
                          sx={{ fontSize: '0.65rem', height: 20 }}
                        />
                      </Box>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {evt.description || 'System event'}
                      </Typography>
                    </Paper>
                  ))}
                </Stack>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Action Dialog */}
      <Dialog open={Boolean(actionDialog)} onClose={() => !actionLoading && setActionDialog(null)}>
        <DialogTitle fontWeight={700}>
          {actionDialog === 'pause' ? 'Pause Examination' : actionDialog === 'resume' ? 'Resume Examination' : 'Terminate Examination'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {actionDialog === 'pause'
              ? 'Pausing will temporarily halt candidate progression.'
              : actionDialog === 'resume'
              ? 'Resumes the candidate exam session.'
              : 'Terminating will immediately conclude the session.'}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setActionDialog(null)} disabled={actionLoading}>Cancel</Button>
          <Button
            onClick={() => actionDialog && handleProctorAction(actionDialog)}
            variant="contained"
            color={actionDialog === 'end' ? 'error' : 'warning'}
            disabled={actionLoading}
          >
            {actionLoading ? <CircularProgress size={20} color="inherit" /> : 'Confirm'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LiveMonitoringPage;
