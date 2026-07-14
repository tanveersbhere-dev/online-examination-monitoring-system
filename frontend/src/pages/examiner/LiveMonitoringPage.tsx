import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Box, Typography, Grid, Card, CardContent, Chip, LinearProgress,
  Divider, Stack, Button, List, ListItem, ListItemText, Paper,
} from '@mui/material';
import VideocamIcon from '@mui/icons-material/Videocam';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import ShieldIcon from '@mui/icons-material/Shield';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import PauseIcon from '@mui/icons-material/Pause';
import StopIcon from '@mui/icons-material/Stop';
import WifiIcon from '@mui/icons-material/Wifi';
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid';
import FaceIcon from '@mui/icons-material/Face';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import PersonOutlineIcon from '@mui/icons-material/PersonOutline';
import axios from 'axios';

interface ViolationEvent {
  type: string;
  time: string;
  severity: string;
}

interface TimelineEvent {
  icon: string;
  text: string;
  time: string;
}

const LiveMonitoringPage = () => {
  const [searchParams] = useSearchParams();
  const examId = searchParams.get('exam_id') || '1';

  const [riskScore, setRiskScore] = useState(0);
  const [identityStatus, setIdentityStatus] = useState('VERIFIED');
  const [identityConfidence, setIdentityConfidence] = useState(100);
  const [facesCount, setFacesCount] = useState(1);
  const [violations, setViolations] = useState<ViolationEvent[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([
    { icon: '▶️', text: 'Exam session started', time: new Date().toLocaleTimeString() }
  ]);
  const [detectedObjects, setDetectedObjects] = useState<{name: string, conf: number}[]>([]);
  
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Attempt to load current status first
    const fetchStatus = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await axios.get(`http://localhost:8000/api/v1/monitoring/current?exam_session_id=${examId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.data) {
          setRiskScore(res.data.current_risk_score || 0);
          setViolations(res.data.active_violations?.map((v: any) => ({
            type: v.violation_type,
            time: new Date().toLocaleTimeString(),
            severity: v.severity.toLowerCase()
          })) || []);
        }
      } catch (err) {
        console.error("Could not fetch initial status", err);
      }
    };
    
    fetchStatus();

    // Connect WebSocket
    const ws = new WebSocket(`ws://localhost:8000/ws/monitoring/${examId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const timeStr = new Date().toLocaleTimeString();
        
        // Always add to timeline if it's an event
        if (data.event) {
            let icon = 'ℹ️';
            let text = data.payload?.description || data.event;
            
            if (data.payload?.severity === 'CRITICAL' || data.payload?.severity === 'HIGH') icon = '🔴';
            else if (data.event.includes('FACE')) icon = '👀';
            else if (data.event.includes('OBJECT')) icon = '📱';
            
            setTimeline(prev => [{ icon, text, time: timeStr }, ...prev].slice(0, 50));
        }

        // Specific event handling
        switch (data.event) {
          case 'RISK_UPDATED':
            setRiskScore(data.payload.data?.risk_score || 0);
            break;
            
          case 'VIOLATION_CREATED':
            setViolations(prev => [{
              type: data.payload.description,
              time: timeStr,
              severity: data.payload.severity.toLowerCase()
            }, ...prev]);
            break;
            
          case 'FACE_STATUS_CHANGED':
            const faceData = data.payload.data;
            if (faceData) {
              setFacesCount(faceData.face_count !== undefined ? faceData.face_count : facesCount);
              if (faceData.identity_verified !== undefined) {
                setIdentityStatus(faceData.identity_verified ? 'VERIFIED' : 'MISMATCH DETECTED');
                setIdentityConfidence(faceData.confidence || 0);
              }
            }
            break;
            
          case 'OBJECT_STATUS_CHANGED':
             const objData = data.payload.data;
             if (objData && objData.objects) {
                 setDetectedObjects(objData.objects.map((o: any) => ({ name: o.label, conf: o.confidence })));
             }
             break;
        }
      } catch (e) {
        console.error("WS Parse Error", e);
      }
    };

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [examId]);

  const riskLabel = riskScore > 75 ? 'CRITICAL' : riskScore > 50 ? 'HIGH' : riskScore > 25 ? 'MEDIUM' : 'LOW';
  const riskColor = riskScore > 75 ? '#B00020' : riskScore > 50 ? '#E65100' : riskScore > 25 ? '#F57C00' : '#2E7D32';

  return (
    <Box>
      {/* Page Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" fontWeight={600}>Live Monitoring</Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
            <FiberManualRecordIcon sx={{ fontSize: 10, color: 'success.main' }} />
            <Typography variant="body2" color="success.main" fontWeight={600}>Live</Typography>
          </Box>
          <Chip label={`Exam Session — ${examId}`} variant="outlined" size="small" />
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* LEFT — Camera Feed */}
        <Grid item xs={12} md={4}>
          <Stack spacing={2}>
            {/* Camera */}
            <Card elevation={1}>
              <CardContent sx={{ p: 0, pb: '0 !important' }}>
                <Box
                  sx={{
                    width: '100%', aspectRatio: '4/3',
                    backgroundColor: '#0A0A0A', position: 'relative',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    borderRadius: '12px 12px 0 0',
                  }}
                >
                  <VideocamIcon sx={{ fontSize: 60, color: 'rgba(255,255,255,0.1)' }} />
                  {/* Face bbox simulation based on face count */}
                  {facesCount > 0 && <Box sx={{ position: 'absolute', width: 140, height: 180, border: '2px solid #F44336', borderRadius: 2 }} />}
                  {/* Recording dot */}
                  <Box sx={{ position: 'absolute', top: 10, right: 10, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <FiberManualRecordIcon sx={{ color: '#F44336', fontSize: 10 }} />
                    <Typography variant="caption" sx={{ color: 'white', fontSize: '0.65rem' }}>REC</Typography>
                  </Box>
                  {/* Face count */}
                  <Chip label={`${facesCount} Face(s)`} size="small" sx={{ position: 'absolute', top: 10, left: 10, backgroundColor: 'rgba(0,0,0,0.6)', color: 'white', fontSize: '0.65rem' }} />
                  {/* Identity confidence bar */}
                  <Box sx={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 4, backgroundColor: 'rgba(255,255,255,0.1)' }}>
                    <Box sx={{ width: `${Math.min(100, identityConfidence * 100)}%`, height: '100%', backgroundColor: identityStatus === 'VERIFIED' ? '#2E7D32' : '#F44336' }} />
                  </Box>
                </Box>
                <Box sx={{ p: 2, display: 'flex', gap: 2 }}>
                  <Button variant="outlined" color="warning" size="small" startIcon={<PauseIcon />} fullWidth>
                    Pause Exam
                  </Button>
                  <Button variant="outlined" color="error" size="small" startIcon={<StopIcon />} fullWidth>
                    End Exam
                  </Button>
                </Box>
              </CardContent>
            </Card>

            {/* Session Info */}
            <Card elevation={1}>
              <CardContent sx={{ p: 2 }}>
                <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>Session Info</Typography>
                <Divider sx={{ my: 1 }} />
                <Stack spacing={0.75}>
                  {[
                    { label: 'Student ID', value: `Active Session ${examId}` },
                    { label: 'Exam', value: `ID: ${examId}` },
                    { label: 'Status', value: 'Running' },
                  ].map((r) => (
                    <Box key={r.label} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="caption" color="text.secondary">{r.label}</Typography>
                      <Typography variant="caption" fontWeight={600}>{r.value}</Typography>
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </Stack>
        </Grid>

        {/* CENTRE — Monitoring Status */}
        <Grid item xs={12} md={4}>
          <Stack spacing={2}>
            {/* Risk Score */}
            <Card elevation={1}>
              <CardContent sx={{ p: 3, textAlign: 'center' }}>
                <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>Current Risk Score</Typography>
                <Box sx={{ my: 2 }}>
                  <Typography variant="h1" fontWeight={700} sx={{ color: riskColor, fontSize: '4rem' }}>
                    {Math.round(riskScore)}
                  </Typography>
                  <Typography variant="h6" fontWeight={700} sx={{ color: riskColor }}>
                    {riskLabel} RISK
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(100, riskScore)}
                  sx={{
                    height: 8, borderRadius: 4,
                    backgroundColor: '#ECEFF1',
                    '& .MuiLinearProgress-bar': { backgroundColor: riskColor },
                  }}
                />
              </CardContent>
            </Card>

            {/* Identity Status */}
            <Card elevation={1} sx={{ borderLeft: `4px solid ${identityStatus === 'VERIFIED' ? '#2E7D32' : '#B00020'}` }}>
              <CardContent sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                  <ShieldIcon sx={{ color: identityStatus === 'VERIFIED' ? 'success.main' : 'error.main', fontSize: 32 }} />
                  <Box>
                    <Typography variant="caption" color="text.secondary">Identity Status</Typography>
                    <Typography variant="subtitle1" fontWeight={700} color={identityStatus === 'VERIFIED' ? 'success.main' : 'error.main'}>{identityStatus}</Typography>
                    <Typography variant="caption" color="text.secondary">Confidence: {(identityConfidence * 100).toFixed(1)}%</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>

            {/* Violations */}
            <Card elevation={1}>
              <CardContent sx={{ p: 2 }}>
                <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                  Violations ({violations.length})
                </Typography>
                <Divider sx={{ my: 1 }} />
                <Box sx={{ maxHeight: 200, overflowY: 'auto' }}>
                  {violations.map((v, idx) => (
                    <Box key={idx} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 0.75, borderLeft: '3px solid', borderLeftColor: v.severity === 'critical' ? 'error.main' : v.severity === 'high' ? 'warning.main' : 'divider', pl: 1, mb: 0.5 }}>
                      <Typography variant="body2">{v.type}</Typography>
                      <Typography variant="caption" color="text.secondary">{v.time}</Typography>
                    </Box>
                  ))}
                  {violations.length === 0 && (
                    <Typography variant="body2" color="text.secondary" sx={{ py: 1, textAlign: 'center' }}>No violations recorded</Typography>
                  )}
                </Box>
              </CardContent>
            </Card>

            {/* Detected Objects */}
            <Card elevation={1}>
              <CardContent sx={{ p: 2 }}>
                <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>Detected Objects</Typography>
                <Divider sx={{ my: 1 }} />
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {detectedObjects.length > 0 ? detectedObjects.map((obj, i) => (
                    <Chip key={i} icon={obj.name.toLowerCase().includes('phone') ? <PhoneAndroidIcon /> : <PersonOutlineIcon />} label={`${obj.name} (${(obj.conf*100).toFixed(0)}%)`} size="small" sx={{ backgroundColor: obj.name.toLowerCase().includes('phone') ? '#FFEBEE' : '#E3F2FD', color: obj.name.toLowerCase().includes('phone') ? '#B00020' : '#1565C0' }} />
                  )) : (
                    <Typography variant="body2" color="text.secondary">No notable objects detected</Typography>
                  )}
                </Box>
              </CardContent>
            </Card>
          </Stack>
        </Grid>

        {/* RIGHT — Timeline */}
        <Grid item xs={12} md={4}>
          <Card elevation={1} sx={{ height: '100%' }}>
            <CardContent sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                  Live Timeline
                </Typography>
                <Chip label="● Live" size="small" sx={{ backgroundColor: '#E8F5E9', color: '#2E7D32', fontSize: '0.65rem', height: 20 }} />
              </Box>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
                <List disablePadding>
                  {timeline.map((event, idx) => (
                    <ListItem key={idx} disablePadding sx={{ py: 1, alignItems: 'flex-start' }}>
                      <Box sx={{ mr: 1.5, fontSize: '1rem', mt: 0.25 }}>{event.icon}</Box>
                      <ListItemText
                        primary={<Typography variant="body2">{event.text}</Typography>}
                        secondary={<Typography variant="caption" color="text.secondary">{event.time}</Typography>}
                      />
                    </ListItem>
                  ))}
                </List>
              </Box>

              <Divider sx={{ mt: 2, mb: 2 }} />
              <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1, mb: 1.5, display: 'block' }}>
                Critical Alerts
              </Typography>
              {violations.filter(v => v.severity === 'critical' || v.severity === 'high').map((v, i) => (
                <Paper key={i} sx={{ p: 1.5, backgroundColor: '#FFEBEE', borderRadius: 2, mb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <WarningAmberIcon sx={{ color: 'error.main', fontSize: 18 }} />
                    <Typography variant="caption" color="error.main" fontWeight={600}>
                      {v.type}
                    </Typography>
                  </Box>
                </Paper>
              ))}
              {violations.filter(v => v.severity === 'critical' || v.severity === 'high').length === 0 && (
                <Typography variant="caption" color="text.secondary">No critical alerts</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default LiveMonitoringPage;
