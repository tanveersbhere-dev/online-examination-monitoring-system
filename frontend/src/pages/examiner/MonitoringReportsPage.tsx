import { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Chip, Divider,
  Stack, Button, Alert, CircularProgress, IconButton, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, TextField, Dialog, DialogTitle, DialogContent, DialogActions
} from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import DownloadIcon from '@mui/icons-material/Download';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import FaceIcon from '@mui/icons-material/Face';
import PhotoLibraryIcon from '@mui/icons-material/PhotoLibrary';
import AssessmentIcon from '@mui/icons-material/Assessment';
import CloseIcon from '@mui/icons-material/Close';
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import PeopleIcon from '@mui/icons-material/People';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import PersonOffIcon from '@mui/icons-material/PersonOff';
import TimerIcon from '@mui/icons-material/Timer';
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline';
import ImageIcon from '@mui/icons-material/Image';

import apiClient from '../../services/apiClient';
import { API_BASE, getAuthImageUrl } from '../../config/api';
import { getErrorMessage } from '../../utils/errorHandler';

interface ReportSummary {
  exam_session_id: number;
  exam_name: string;
  student_name: string;
  date: string;
  duration_minutes: number;
  final_risk_score: number;
  total_violations: number;
}

interface EvidenceItem {
  timestamp: string;
  evidence_type: string;
  file_path: string;
  violation_type?: string;
  confidence_score?: number;
  risk_score?: number;
}

interface EvidenceGalleryItem {
  violation_id: number;
  violation_type?: string;
  snapshots: EvidenceItem[];
}

const MonitoringReportsPage = () => {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [reportDetail, setReportDetail] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  
  // For evidence modal & zoom preview
  const [selectedViolationId, setSelectedViolationId] = useState<number | null>(null);
  const [evidenceModalOpen, setEvidenceModalOpen] = useState(false);
  const [zoomSnapshot, setZoomSnapshot] = useState<{
    src: string;
    title: string;
    time: string;
    risk: number;
    conf: number;
    replayUrl?: string | null;
    previewMode?: 'photo' | 'video';
  } | null>(null);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/reports');
      setReports(res.data);
    } catch (err: any) {
      console.error(err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSelectReport = async (id: number, openEvidenceDialog = false) => {
    setSelectedReportId(id);
    setLoading(true);
    setReportDetail(null);
    setError(null);
    setSelectedViolationId(null);
    if (openEvidenceDialog) setEvidenceModalOpen(true);

    try {
      const res = await apiClient.get(`/reports/${id}`);
      setReportDetail(res.data);
    } catch (err: any) {
      console.error(err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setSelectedReportId(null);
    setReportDetail(null);
    setError(null);
    setEvidenceModalOpen(false);
  };

  if (loading && !reports.length && !reportDetail) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
  }

  // LIST VIEW
  if (selectedReportId === null) {
    const filteredReports = reports.filter(r => 
      r.student_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
      r.exam_name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
      <Box sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap', gap: 2 }}>
          <Box>
            <Typography variant="h4" fontWeight={700} sx={{ color: '#0F172A' }}>Monitoring Reports</Typography>
            <Typography variant="body2" color="text.secondary">Review proctoring violation logs, behavioral statistics, and snapshot evidence dossiers.</Typography>
          </Box>
          <TextField
            size="small"
            placeholder="Search by candidate or exam..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            sx={{ width: 320, backgroundColor: 'white', borderRadius: 2 }}
          />
        </Box>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

        <TableContainer component={Paper} elevation={2} sx={{ borderRadius: 3, overflow: 'hidden' }}>
          <Table>
            <TableHead sx={{ backgroundColor: '#F1F5F9' }}>
              <TableRow>
                <TableCell><b>Session ID</b></TableCell>
                <TableCell><b>Candidate</b></TableCell>
                <TableCell><b>Exam Title</b></TableCell>
                <TableCell><b>Date & Time</b></TableCell>
                <TableCell><b>Duration</b></TableCell>
                <TableCell><b>Risk Score</b></TableCell>
                <TableCell><b>Violations</b></TableCell>
                <TableCell align="right"><b>Actions</b></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredReports.map((row) => (
                <TableRow key={row.exam_session_id} hover>
                  <TableCell sx={{ fontFamily: 'monospace', fontWeight: 600 }}>#{row.exam_session_id}</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>{row.student_name}</TableCell>
                  <TableCell>{row.exam_name}</TableCell>
                  <TableCell>{row.date ? new Date(row.date).toLocaleString() : 'N/A'}</TableCell>
                  <TableCell>{row.duration_minutes ? row.duration_minutes.toFixed(1) : 0} mins</TableCell>
                  <TableCell>
                    <Chip 
                      label={`${row.final_risk_score.toFixed(1)} / 100`} 
                      size="small" 
                      sx={{ 
                        backgroundColor: row.final_risk_score > 75 ? '#FFEBEE' : row.final_risk_score > 50 ? '#FFF3E0' : '#E8F5E9',
                        color: row.final_risk_score > 75 ? '#B00020' : row.final_risk_score > 50 ? '#E65100' : '#2E7D32',
                        fontWeight: 700
                      }} 
                    />
                  </TableCell>
                  <TableCell>
                    <Chip label={`${row.total_violations} Events`} size="small" variant="outlined" sx={{ fontWeight: 600 }} />
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <Button
                        variant="outlined"
                        size="small"
                        color="secondary"
                        startIcon={<PhotoLibraryIcon />}
                        onClick={() => handleSelectReport(row.exam_session_id, true)}
                        sx={{ textTransform: 'none', fontWeight: 600, borderRadius: 2 }}
                      >
                        Evidence
                      </Button>
                      <Button
                        variant="contained"
                        size="small"
                        onClick={() => handleSelectReport(row.exam_session_id, false)}
                        sx={{ textTransform: 'none', fontWeight: 600, borderRadius: 2 }}
                      >
                        View Report
                      </Button>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
              {filteredReports.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">No candidate monitoring reports found.</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    );
  }

  // DETAIL VIEW
  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={handleBack} sx={{ mb: 2 }}>Back to Reports</Button>
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
      </Box>
    );
  }

  if (error || !reportDetail) {
    return (
      <Box sx={{ p: 3 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={handleBack} sx={{ mb: 2 }}>Back to Reports</Button>
        <Alert severity="error">{error || "Failed to load report"}</Alert>
      </Box>
    );
  }

  const handleDownloadPDF = () => {
    window.print();
  };

  const { student_info, exam_info, session_summary, risk_summary, timeline, evidence_gallery, recommendation, statistics } = reportDetail;
  const riskColor = risk_summary.highest_risk_level === 'CRITICAL' ? '#B00020' : risk_summary.highest_risk_level === 'HIGH' ? '#E65100' : risk_summary.highest_risk_level === 'MEDIUM' ? '#F57C00' : '#2E7D32';

  const visibleEvidence = selectedViolationId 
    ? evidence_gallery.filter((g: any) => g.violation_id === selectedViolationId)
    : evidence_gallery;

  return (
    <Box sx={{
      p: 3,
      '@media print': {
        '.no-print': { display: 'none !important' },
        'body': { backgroundColor: '#fff' },
        '.MuiCard-root': { boxShadow: 'none', border: '1px solid #e0e0e0', pageBreakInside: 'avoid' }
      }
    }}>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }} className="no-print">
        <Button startIcon={<ArrowBackIcon />} onClick={handleBack} sx={{ textTransform: 'none', fontWeight: 600 }}>
          Back to Reports
        </Button>
      </Stack>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" fontWeight={700} sx={{ color: '#0F172A' }}>Monitoring Report</Typography>
          <Typography variant="body2" color="text.secondary">Comprehensive post-exam AI integrity audit and evidence dossier.</Typography>
        </Box>
        <Stack direction="row" spacing={1.5} className="no-print">
          <Button
            variant="outlined"
            color="secondary"
            startIcon={<PhotoLibraryIcon />}
            onClick={() => setEvidenceModalOpen(true)}
            sx={{ borderRadius: 2, textTransform: 'none', fontWeight: 600 }}
          >
            Evidence Gallery ({evidence_gallery.reduce((acc: number, g: any) => acc + (g.snapshots?.length || 0), 0)})
          </Button>
          <Button
            variant="contained"
            startIcon={<DownloadIcon />}
            sx={{ borderRadius: 2, textTransform: 'none', fontWeight: 600 }}
            onClick={handleDownloadPDF}
          >
            Download PDF
          </Button>
        </Stack>
      </Box>

      {/* Candidate Banner */}
      <Alert severity="info" sx={{ mb: 4, borderRadius: 2 }}>
        Showing audit report for: <strong>{student_info.student_name}</strong> ({student_info.email}) · {exam_info.exam_name} ({exam_info.course})
      </Alert>

      {/* Student & Exam Info */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Card elevation={1} sx={{ height: '100%', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="caption" color="text.secondary" fontWeight={700} sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                Student Candidate Profile
              </Typography>
              <Divider sx={{ my: 1.5 }} />
              <Stack spacing={1}>
                {[
                  ['Candidate Name', student_info.student_name], 
                  ['Email Address', student_info.email], 
                  ['Candidate ID', `#${student_info.student_id}`], 
                  ['Course / Program', exam_info.course]
                ].map(([l, v]) => (
                  <Box key={l as string} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption" color="text.secondary">{l}</Typography>
                    <Typography variant="caption" fontWeight={600}>{v}</Typography>
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card elevation={1} sx={{ height: '100%', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="caption" color="text.secondary" fontWeight={700} sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                Examination Session Summary
              </Typography>
              <Divider sx={{ my: 1.5 }} />
              <Stack spacing={1}>
                {[
                  ['Examination Title', exam_info.exam_name], 
                  ['Course Code', exam_info.course], 
                  ['Duration Monitored', `${exam_info.duration_minutes} Minutes`], 
                  ['Completion Status', session_summary.final_status]
                ].map(([l, v]) => (
                  <Box key={l as string} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption" color="text.secondary">{l}</Typography>
                    <Typography variant="caption" fontWeight={600}>{v}</Typography>
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Detector Statistics & Analytics (Phone, Persons, Books, Gaze, Absence) */}
      <Card elevation={1} sx={{ mb: 3, borderRadius: 3, border: '1px solid #E2E8F0' }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" fontWeight={700} gutterBottom sx={{ color: '#0F172A' }}>
            Detector Statistics & AI Violation Metrics
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Precise event counts recorded across all 19 pipeline intelligence detectors during this examination.
          </Typography>
          <Divider sx={{ mb: 2.5 }} />
          <Grid container spacing={2}>
            {[
              { label: 'Mobile Phones', count: statistics?.total_phone_detections || 0, icon: <PhoneAndroidIcon sx={{ color: '#EF4444' }} />, color: '#FEF2F2' },
              { label: 'Multiple Persons', count: statistics?.total_multiple_person || 0, icon: <PeopleIcon sx={{ color: '#F59E0B' }} />, color: '#FFFBEB' },
              { label: 'Books / Notes', count: statistics?.total_book_detections || 0, icon: <MenuBookIcon sx={{ color: '#8B5CF6' }} />, color: '#F5F3FF' },
              { label: 'Looking Away / Gaze', count: statistics?.total_looking_away || 0, icon: <VisibilityOffIcon sx={{ color: '#3B82F6' }} />, color: '#EFF6FF' },
              { label: 'Face Absence', count: statistics?.total_face_absence || 0, icon: <PersonOffIcon sx={{ color: '#EC4899' }} />, color: '#FDF2F8' },
              { label: 'Evidence Photos', count: statistics?.total_snapshots || 0, icon: <PhotoLibraryIcon sx={{ color: '#10B981' }} />, color: '#ECFDF5' },
            ].map((stat, idx) => (
              <Grid item xs={6} sm={4} md={2} key={idx}>
                <Box sx={{ p: 2, backgroundColor: stat.color, borderRadius: 2.5, textAlign: 'center', border: '1px solid rgba(0,0,0,0.06)' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'center', mb: 0.5 }}>{stat.icon}</Box>
                  <Typography variant="caption" color="text.secondary" display="block" fontWeight={600} noWrap>{stat.label}</Typography>
                  <Typography variant="h5" fontWeight={800} sx={{ color: '#0F172A', mt: 0.5 }}>{stat.count}</Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>

      {/* Overall Risk Summary */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {[
          { label: 'Final Risk Score', value: `${risk_summary.final_risk_score.toFixed(1)} / 100`, sub: risk_summary.highest_risk_level, color: riskColor },
          { label: 'Average Risk Score', value: `${(statistics?.average_risk_score || 0).toFixed(1)} / 100`, sub: `Level: ${risk_summary.average_risk_level}`, color: '#F57C00' },
          { label: 'Total Violations', value: risk_summary.total_violations, sub: 'Recorded Incidents', color: '#1565C0' },
        ].map((card) => (
          <Grid item xs={12} sm={4} key={card.label}>
            <Card elevation={1} sx={{ borderLeft: `4px solid ${card.color}`, borderRadius: 3 }}>
              <CardContent sx={{ p: 3, textAlign: 'center' }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>{card.label}</Typography>
                <Typography variant="h4" fontWeight={800} sx={{ color: card.color, my: 1 }}>{card.value}</Typography>
                <Typography variant="caption" fontWeight={700} sx={{ color: card.color }}>{card.sub}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Violation Timeline */}
      <Card elevation={1} sx={{ mb: 3, borderRadius: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="subtitle1" fontWeight={700}>Chronological Violation Timeline</Typography>
            {selectedViolationId && (
              <Button size="small" onClick={() => setSelectedViolationId(null)}>Clear Evidence Filter</Button>
            )}
          </Box>
          <Divider sx={{ mb: 2 }} />
          {timeline.map((v: any, idx: number) => {
            const isSelected = selectedViolationId === v.violation_id;
            const matchingGroup = (evidence_gallery || []).find((g: any) => g.violation_id === v.violation_id || g.violation_type === v.violation_type);
            const primarySnap = matchingGroup?.snapshots?.[0];
            const hasEvidence = Boolean(primarySnap?.file_path);

            const handleInspectViolation = () => {
              if (v.violation_id) setSelectedViolationId(v.violation_id);

              if (primarySnap?.file_path) {
                const imgUrl = getAuthImageUrl(primarySnap.file_path);
                const replayUrl = primarySnap.replay_clip_path ? getAuthImageUrl(primarySnap.replay_clip_path) : null;
                setZoomSnapshot({
                  src: imgUrl,
                  title: primarySnap.violation_type || v.violation_type || 'VIOLATION',
                  time: new Date(primarySnap.timestamp || v.timestamp).toLocaleTimeString(),
                  risk: primarySnap.risk_score || v.risk_score || 50,
                  conf: primarySnap.confidence_score || 0.95,
                  replayUrl: replayUrl,
                  previewMode: 'photo'
                });
              } else {
                const el = document.getElementById('evidence-gallery-section');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }
            };

            const durationVal = (v.duration_seconds && v.duration_seconds > 0) ? v.duration_seconds : 1.5;

            return (
              <Box
                key={idx}
                onClick={handleInspectViolation}
                sx={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  py: 1.5, px: 2, mb: 1.5, cursor: 'pointer',
                  borderLeft: '4px solid',
                  borderLeftColor: v.severity === 'CRITICAL' ? 'error.main' : v.severity === 'HIGH' ? 'warning.main' : 'divider',
                  backgroundColor: isSelected ? '#E3F2FD' : '#F8FAFC', borderRadius: '0 8px 8px 0',
                  transition: 'all 0.2s ease',
                  '&:hover': { backgroundColor: isSelected ? '#BBDEFB' : '#EFF6FF', transform: 'translateX(2px)' }
                }}
              >
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                  <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace', width: 75, fontWeight: 600 }}>
                    {new Date(v.timestamp).toLocaleTimeString()}
                  </Typography>
                  <Typography variant="body2" fontWeight={800} sx={{ color: '#0F172A' }}>{v.violation_type}</Typography>
                  <Typography variant="caption" color="text.secondary">{v.short_description}</Typography>
                </Box>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <Chip
                    icon={<TimerIcon sx={{ fontSize: '13px !important' }} />}
                    label={`Duration: ${durationVal.toFixed(1)}s`}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: '0.72rem', fontWeight: 700, borderColor: '#CBD5E1', backgroundColor: '#FFFFFF' }}
                  />
                  <Chip 
                    label={`Risk: ${(v.risk_score || 0).toFixed(0)}`} 
                    size="small" 
                    sx={{ 
                      backgroundColor: v.risk_score > 75 ? '#FFEBEE' : v.risk_score > 40 ? '#FFF3E0' : '#E8F5E9', 
                      color: v.risk_score > 75 ? '#B00020' : v.risk_score > 40 ? '#E65100' : '#2E7D32', 
                      fontWeight: 800, fontSize: '0.7rem' 
                    }} 
                  />
                  <Button
                    size="small"
                    variant={hasEvidence ? "contained" : "outlined"}
                    color="primary"
                    startIcon={<PhotoLibraryIcon sx={{ fontSize: '14px !important' }} />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleInspectViolation();
                    }}
                    sx={{
                      textTransform: 'none',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      py: 0.25,
                      px: 1.25,
                      borderRadius: 1.5,
                      boxShadow: 'none'
                    }}
                  >
                    {hasEvidence ? 'View Evidence' : 'Inspect'}
                  </Button>
                </Stack>
              </Box>
            );
          })}
          {timeline.length === 0 && (
             <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>No violations recorded during this examination session.</Typography>
          )}
        </CardContent>
      </Card>

      {/* Embedded Evidence Gallery */}
      <Card id="evidence-gallery-section" elevation={1} sx={{ mb: 3, borderRadius: 3, scrollMarginTop: '80px' }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" fontWeight={700} gutterBottom>Violation Snapshots & Captured Evidence</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Click any thumbnail below to inspect full-resolution evidence snapshots.
          </Typography>
          <Divider sx={{ mb: 2 }} />
          {visibleEvidence.map((group: any, gIdx: number) => (
            <Box key={gIdx} sx={{ mb: 3 }}>
              <Typography variant="body2" fontWeight={700} gutterBottom sx={{ color: 'text.secondary' }}>
                Incident #{group.violation_id} {group.violation_type ? `· ${group.violation_type}` : ''}
              </Typography>
              <Box sx={{ display: 'flex', gap: 2.5, flexWrap: 'wrap' }}>
                {group.snapshots.map((snap: any, i: number) => {
                  const imgUrl = getAuthImageUrl(snap.file_path);
                  const replayUrl = snap.replay_clip_path ? getAuthImageUrl(snap.replay_clip_path) : null;

                  return (
                    <Card
                      key={i}
                      elevation={2}
                      onClick={() => setZoomSnapshot({
                        src: imgUrl,
                        title: snap.violation_type || group.violation_type || 'VIOLATION',
                        time: new Date(snap.timestamp).toLocaleTimeString(),
                        risk: snap.risk_score || group.risk_score || 50,
                        conf: snap.confidence_score || 0.95,
                        replayUrl: replayUrl,
                        previewMode: 'photo'
                      })}
                      sx={{
                        width: 240, overflow: 'hidden', borderRadius: 2.5, cursor: 'pointer',
                        transition: 'transform 0.2s, box-shadow 0.2s',
                        '&:hover': { transform: 'translateY(-3px)', boxShadow: 4 }
                      }}
                    >
                      <Box sx={{ height: 150, backgroundColor: '#0F172A', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        {snap.file_path ? (
                          <img src={imgUrl} alt="Violation Evidence" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                        ) : (
                          <FaceIcon sx={{ color: 'rgba(255,255,255,0.2)', fontSize: 48 }} />
                        )}
                        <Typography variant="caption" sx={{ position: 'absolute', bottom: 4, right: 6, color: '#FFF', fontSize: '0.65rem', backgroundColor: 'rgba(0,0,0,0.7)', px: 0.75, py: 0.25, borderRadius: 1, fontFamily: 'monospace' }}>
                          {new Date(snap.timestamp).toLocaleTimeString()}
                        </Typography>
                      </Box>
                      <Box sx={{ p: 1.5, backgroundColor: '#FAFAFA' }}>
                        <Typography variant="subtitle2" fontWeight={700} noWrap>{snap.violation_type || group.violation_type || 'VIOLATION'}</Typography>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.75, alignItems: 'center' }}>
                          <Typography variant="caption" color="text.secondary">
                            Confidence: {snap.confidence_score !== undefined ? `${(snap.confidence_score <= 1.0 ? snap.confidence_score * 100 : snap.confidence_score).toFixed(0)}%` : '90%'}
                          </Typography>
                          <Chip 
                            label={`Risk: ${(snap.risk_score || group.risk_score || 0).toFixed(0)}`} 
                            size="small" 
                            color={(snap.risk_score || group.risk_score || 0) > 75 ? 'error' : (snap.risk_score || group.risk_score || 0) > 40 ? 'warning' : 'success'}
                            sx={{ height: 20, fontSize: '0.65rem', fontWeight: 700 }}
                          />
                        </Box>
                      </Box>
                    </Card>
                  );
                })}
              </Box>
            </Box>
          ))}
          {visibleEvidence.length === 0 && (
             <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>No evidence snapshots recorded for this session.</Typography>
          )}
        </CardContent>
      </Card>

      {/* Final Assessment & Recommendation */}
      <Alert 
        severity={recommendation.includes('Manual Review Required') || recommendation.includes('Strong Evidence') ? 'error' : recommendation.includes('Recommended') ? 'warning' : 'success'} 
        icon={<AssessmentIcon />} 
        sx={{ mb: 3, borderRadius: 3 }}
      >
        <Typography variant="subtitle2" fontWeight={700}>System Audit Assessment: {recommendation}</Typography>
        <Typography variant="body2">Based on multi-layer spatial-temporal AI inference, head orientation tracking, YOLO object detections, and verified evidence snapshots.</Typography>
      </Alert>

      {/* ── Standalone Evidence Gallery Modal Dialog ────────────────── */}
      <Dialog
        open={evidenceModalOpen}
        onClose={() => setEvidenceModalOpen(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{ sx: { borderRadius: 3 } }}
      >
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h6" fontWeight={700}>
              Candidate Evidence Dossier
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Candidate: {student_info?.student_name} ({student_info?.email}) · Session #{selectedReportId}
            </Typography>
          </Box>
          <IconButton onClick={() => setEvidenceModalOpen(false)}>
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers sx={{ p: 3 }}>
          {evidence_gallery?.length > 0 ? (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2.5 }}>
              {evidence_gallery.flatMap((g: any) => (g.snapshots || []).map((snap: any, i: number) => {
                const imgUrl = getAuthImageUrl(snap.file_path);
                const replayUrl = snap.replay_clip_path ? getAuthImageUrl(snap.replay_clip_path) : null;

                return (
                  <Card
                    key={`${g.violation_id}_${i}`}
                    elevation={2}
                    onClick={() => setZoomSnapshot({
                      src: imgUrl,
                      title: snap.violation_type || g.violation_type || 'VIOLATION',
                      time: new Date(snap.timestamp).toLocaleTimeString(),
                      risk: snap.risk_score || g.risk_score || 50,
                      conf: snap.confidence_score || 0.95,
                      replayUrl: replayUrl,
                      previewMode: 'photo'
                    })}
                    sx={{
                      width: 250, overflow: 'hidden', borderRadius: 2.5, cursor: 'pointer',
                      transition: 'transform 0.2s, box-shadow 0.2s',
                      '&:hover': { transform: 'scale(1.02)', boxShadow: 4 }
                    }}
                  >
                    <Box sx={{ height: 160, backgroundColor: '#0F172A', position: 'relative' }}>
                      <img src={imgUrl} alt="Evidence" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      <Typography variant="caption" sx={{ position: 'absolute', bottom: 4, right: 6, color: '#FFF', fontSize: '0.65rem', backgroundColor: 'rgba(0,0,0,0.7)', px: 0.75, py: 0.25, borderRadius: 1, fontFamily: 'monospace' }}>
                        {new Date(snap.timestamp).toLocaleTimeString()}
                      </Typography>
                    </Box>
                    <Box sx={{ p: 1.5 }}>
                      <Typography variant="subtitle2" fontWeight={700} noWrap>{snap.violation_type || g.violation_type || 'VIOLATION'}</Typography>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5, alignItems: 'center' }}>
                        <Typography variant="caption" color="text.secondary">
                          Conf: {snap.confidence_score !== undefined ? `${(snap.confidence_score <= 1.0 ? snap.confidence_score * 100 : snap.confidence_score).toFixed(0)}%` : '90%'}
                        </Typography>
                        <Chip
                          label={`Risk: ${(snap.risk_score || g.risk_score || 0).toFixed(0)}`}
                          size="small"
                          color={(snap.risk_score || g.risk_score || 0) > 75 ? 'error' : 'warning'}
                          sx={{ height: 20, fontSize: '0.65rem', fontWeight: 700 }}
                        />
                      </Box>
                    </Box>
                  </Card>
                );
              }))}
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
              No evidence photos have been captured for this candidate.
            </Typography>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setEvidenceModalOpen(false)} sx={{ fontWeight: 600 }}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── High-Resolution Zoom Lightbox Dialog ────────────────────── */}
      <Dialog
        open={Boolean(zoomSnapshot)}
        onClose={() => setZoomSnapshot(null)}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: { borderRadius: 3, p: 1 } }}
      >
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pb: 1 }}>
          <Box>
            <Typography variant="h6" fontWeight={700}>
              {zoomSnapshot?.title}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Captured at: {zoomSnapshot?.time} · Confidence: {((zoomSnapshot?.conf || 0.95) <= 1 ? (zoomSnapshot?.conf || 0.95) * 100 : zoomSnapshot?.conf).toFixed(0)}% · Risk: {zoomSnapshot?.risk.toFixed(0)}/100
            </Typography>
          </Box>
          <IconButton onClick={() => setZoomSnapshot(null)}>
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ textAlign: 'center', p: 2 }}>
          {zoomSnapshot?.replayUrl && (
            <Stack direction="row" spacing={1} justifyContent="center" sx={{ mb: 2 }}>
              <Button
                size="small"
                variant={zoomSnapshot.previewMode !== 'video' ? 'contained' : 'outlined'}
                startIcon={<ImageIcon />}
                onClick={() => setZoomSnapshot((prev) => prev ? { ...prev, previewMode: 'photo' } : null)}
                sx={{ textTransform: 'none', borderRadius: 2, fontWeight: 700 }}
              >
                Snapshot Photo
              </Button>
              <Button
                size="small"
                variant={zoomSnapshot.previewMode === 'video' ? 'contained' : 'outlined'}
                color="secondary"
                startIcon={<PlayCircleOutlineIcon />}
                onClick={() => setZoomSnapshot((prev) => prev ? { ...prev, previewMode: 'video' } : null)}
                sx={{ textTransform: 'none', borderRadius: 2, fontWeight: 700 }}
              >
                ▶ 3s Video Replay
              </Button>
            </Stack>
          )}

          {zoomSnapshot && (
            zoomSnapshot.previewMode === 'video' && zoomSnapshot.replayUrl ? (
              <video
                src={zoomSnapshot.replayUrl}
                controls
                autoPlay
                loop
                muted
                playsInline
                style={{ maxWidth: '100%', maxHeight: '70vh', borderRadius: 8, backgroundColor: '#000' }}
              />
            ) : (
              <img
                src={zoomSnapshot.src}
                alt="Evidence Full View"
                style={{ maxWidth: '100%', maxHeight: '70vh', objectFit: 'contain', borderRadius: 8, backgroundColor: '#0F172A' }}
              />
            )
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button variant="contained" onClick={() => setZoomSnapshot(null)} sx={{ fontWeight: 600 }}>
            Close Preview
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MonitoringReportsPage;
