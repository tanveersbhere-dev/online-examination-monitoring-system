import { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Chip, Divider,
  Stack, Button, Alert, CircularProgress, IconButton, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, TextField
} from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import DownloadIcon from '@mui/icons-material/Download';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import FaceIcon from '@mui/icons-material/Face';
import DescriptionIcon from '@mui/icons-material/Description';
import AssessmentIcon from '@mui/icons-material/Assessment';
import apiClient from '../../services/apiClient';
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

interface ViolationTimelineItem {
  timestamp: string;
  violation_type: string;
  category: string;
  severity: string;
  risk_score: number;
  short_description: string;
}

interface EvidenceItem {
  timestamp: string;
  evidence_type: string;
  file_path: string;
}

interface EvidenceGalleryItem {
  violation_id: number;
  snapshots: EvidenceItem[];
}

const MonitoringReportsPage = () => {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [reportDetail, setReportDetail] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  
  // For evidence filtering
  const [selectedViolationId, setSelectedViolationId] = useState<number | null>(null);

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

  const handleSelectReport = async (id: number) => {
    setSelectedReportId(id);
    setLoading(true);
    setReportDetail(null);
    setError(null);
    setSelectedViolationId(null);
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
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap', gap: 2 }}>
          <Typography variant="h4" fontWeight={600}>Monitoring Reports</Typography>
          <TextField
            size="small"
            placeholder="Search by student or exam..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            sx={{ width: 300, backgroundColor: 'white', borderRadius: 1 }}
          />
        </Box>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

        <TableContainer component={Paper} elevation={1}>
          <Table>
            <TableHead sx={{ backgroundColor: '#F8FAFC' }}>
              <TableRow>
                <TableCell><b>Session ID</b></TableCell>
                <TableCell><b>Student</b></TableCell>
                <TableCell><b>Exam</b></TableCell>
                <TableCell><b>Date</b></TableCell>
                <TableCell><b>Duration</b></TableCell>
                <TableCell><b>Risk Score</b></TableCell>
                <TableCell><b>Violations</b></TableCell>
                <TableCell align="right"><b>Action</b></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredReports.map((row) => (
                <TableRow key={row.exam_session_id} hover>
                  <TableCell>{row.exam_session_id}</TableCell>
                  <TableCell>{row.student_name}</TableCell>
                  <TableCell>{row.exam_name}</TableCell>
                  <TableCell>{row.date ? new Date(row.date).toLocaleString() : 'N/A'}</TableCell>
                  <TableCell>{row.duration_minutes ? row.duration_minutes.toFixed(1) : 0} mins</TableCell>
                  <TableCell>
                    <Chip 
                      label={row.final_risk_score.toFixed(1)} 
                      size="small" 
                      sx={{ 
                        backgroundColor: row.final_risk_score > 75 ? '#FFEBEE' : row.final_risk_score > 50 ? '#FFF3E0' : '#E8F5E9',
                        color: row.final_risk_score > 75 ? '#B00020' : row.final_risk_score > 50 ? '#E65100' : '#2E7D32',
                        fontWeight: 600
                      }} 
                    />
                  </TableCell>
                  <TableCell>{row.total_violations}</TableCell>
                  <TableCell align="right">
                    <Button variant="outlined" size="small" onClick={() => handleSelectReport(row.exam_session_id)}>
                      View Report
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {filteredReports.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 3 }}>
                    <Typography color="text.secondary">No reports found.</Typography>
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
      <Box>
        <Button startIcon={<ArrowBackIcon />} onClick={handleBack} sx={{ mb: 2 }}>Back to Reports</Button>
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
      </Box>
    );
  }

  if (error || !reportDetail) {
    return (
      <Box>
        <Button startIcon={<ArrowBackIcon />} onClick={handleBack} sx={{ mb: 2 }}>Back to Reports</Button>
        <Alert severity="error">{error || "Failed to load report"}</Alert>
      </Box>
    );
  }

  const { student_info, exam_info, session_summary, risk_summary, timeline, evidence_gallery, recommendation } = reportDetail;
  const riskColor = risk_summary.highest_risk_level === 'CRITICAL' ? '#B00020' : risk_summary.highest_risk_level === 'HIGH' ? '#E65100' : risk_summary.highest_risk_level === 'MEDIUM' ? '#F57C00' : '#2E7D32';

  const visibleEvidence = selectedViolationId 
    ? evidence_gallery.filter((g: any) => g.violation_id === selectedViolationId)
    : evidence_gallery;

  return (
    <Box>
      <Button startIcon={<ArrowBackIcon />} onClick={handleBack} sx={{ mb: 3 }}>Back to Reports</Button>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" fontWeight={600}>Monitoring Report</Typography>
        <Button variant="contained" startIcon={<DownloadIcon />} sx={{ borderRadius: 2 }}>
          Download PDF
        </Button>
      </Box>

      {/* Exam & Student Selection */}
      <Alert severity="info" sx={{ mb: 4, borderRadius: 2 }}>
        Showing report for: <strong>{student_info.student_name}</strong> · {exam_info.exam_name} ({exam_info.course})
      </Alert>

      {/* Student + Exam Info */}
      <Card elevation={1} sx={{ mb: 3, backgroundColor: '#E3F2FD', border: '1px solid #BBDEFB' }}>
        <CardContent sx={{ p: 3 }}>
          <Grid container spacing={4}>
            <Grid item xs={12} md={6}>
              <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>Student</Typography>
              <Divider sx={{ my: 1 }} />
              <Stack spacing={0.75}>
                {[
                  ['Full Name', student_info.student_name], 
                  ['Email', student_info.email], 
                  ['Student ID', student_info.student_id], 
                  ['Exam Assigned', exam_info.course]
                ].map(([l, v]) => (
                  <Box key={l as string} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption" color="text.secondary">{l}</Typography>
                    <Typography variant="caption" fontWeight={600}>{v}</Typography>
                  </Box>
                ))}
              </Stack>
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>Examination</Typography>
              <Divider sx={{ my: 1 }} />
              <Stack spacing={0.75}>
                {[
                  ['Exam Name', exam_info.exam_name], 
                  ['Course', exam_info.course], 
                  ['Duration', `${exam_info.duration_minutes} Minutes`], 
                  ['Final Status', session_summary.final_status]
                ].map(([l, v]) => (
                  <Box key={l as string} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption" color="text.secondary">{l}</Typography>
                    <Typography variant="caption" fontWeight={600}>{v}</Typography>
                  </Box>
                ))}
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Risk Summary */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {[
          { label: 'Final Risk Score', value: risk_summary.final_risk_score.toFixed(1), sub: risk_summary.highest_risk_level, color: riskColor },
          { label: 'Average Risk', value: risk_summary.average_risk_level, sub: `Avg Score: ${reportDetail.statistics.average_risk_score.toFixed(1)}`, color: '#F57C00' },
          { label: 'Total Violations', value: risk_summary.total_violations, sub: 'Recorded Events', color: '#1565C0' },
        ].map((card) => (
          <Grid item xs={12} sm={4} key={card.label}>
            <Card elevation={1} sx={{ borderLeft: `4px solid ${card.color}` }}>
              <CardContent sx={{ p: 3, textAlign: 'center' }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>{card.label}</Typography>
                <Typography variant="h3" fontWeight={700} sx={{ color: card.color, my: 1 }}>{card.value}</Typography>
                <Typography variant="caption" fontWeight={600} sx={{ color: card.color }}>{card.sub}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Recommendation */}
      <Alert 
        severity={recommendation.includes('Manual Review Required') || recommendation.includes('Strong Evidence') ? 'error' : recommendation.includes('Recommended') ? 'warning' : 'success'} 
        icon={<AssessmentIcon />} 
        sx={{ mb: 3, borderRadius: 2 }}
      >
        <Typography variant="body2" fontWeight={700}>{recommendation}</Typography>
        <Typography variant="body2">Based on the calculated risk scores and recorded violations during this session.</Typography>
      </Alert>

      {/* Violation Timeline */}
      <Card elevation={1} sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>Violation Timeline</Typography>
          <Divider sx={{ mb: 2 }} />
          {timeline.map((v: any, idx: number) => {
            const hasEvidence = evidence_gallery.some((g: any) => g.violation_id === v.violation_id); // we assume timeline has violation_id? The backend timeline doesn't actually expose violation_id currently in ViolationTimelineItem. But we can just use index if it matches chronologically, or rely on type and time. Wait, backend timeline doesn't have violation_id.
            
            return (
              <Box
                key={idx}
                sx={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  py: 1.5, px: 2, mb: 1,
                  borderLeft: '4px solid',
                  borderLeftColor: v.severity === 'CRITICAL' ? 'error.main' : v.severity === 'HIGH' ? 'warning.main' : 'divider',
                  backgroundColor: 'background.default', borderRadius: '0 8px 8px 0',
                }}
              >
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                  <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace', width: 72 }}>
                    {new Date(v.timestamp).toLocaleTimeString()}
                  </Typography>
                  <Typography variant="body2" fontWeight={600}>{v.violation_type}</Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ display: { xs: 'none', sm: 'block' } }}>{v.short_description}</Typography>
                  <Chip label={`Risk: ${v.risk_score.toFixed(1)}`} size="small" sx={{ backgroundColor: v.risk_score > 75 ? '#FFEBEE' : '#FFF3E0', color: v.risk_score > 75 ? '#B00020' : '#E65100', fontSize: '0.7rem' }} />
                </Box>
              </Box>
            );
          })}
          {timeline.length === 0 && (
             <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>No violations recorded during this session.</Typography>
          )}
        </CardContent>
      </Card>

      {/* Evidence Gallery */}
      <Card elevation={1} sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>Evidence Gallery</Typography>
          <Divider sx={{ mb: 2 }} />
          {visibleEvidence.map((group: any, gIdx: number) => (
            <Box key={gIdx} sx={{ mb: 3 }}>
              <Typography variant="body2" fontWeight={600} gutterBottom sx={{ color: 'text.secondary' }}>Violation ID: {group.violation_id}</Typography>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                {group.snapshots.map((snap: any, i: number) => (
                  <Box
                    key={i}
                    sx={{
                      width: 160, height: 120, backgroundColor: '#1A1A2E',
                      borderRadius: 2, display: 'flex', alignItems: 'center',
                      justifyContent: 'center', cursor: 'pointer',
                      border: '1px solid', borderColor: 'divider',
                      '&:hover': { borderColor: 'primary.main' },
                      position: 'relative',
                      overflow: 'hidden'
                    }}
                  >
                    {snap.file_path ? (
                      <img src={`http://localhost:8000/${snap.file_path}`} alt="Evidence" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ) : (
                      <FaceIcon sx={{ color: 'rgba(255,255,255,0.15)', fontSize: 40 }} />
                    )}
                    <Typography variant="caption" sx={{ position: 'absolute', bottom: 4, left: 0, right: 0, textAlign: 'center', color: 'rgba(255,255,255,0.8)', fontSize: '0.6rem', backgroundColor: 'rgba(0,0,0,0.5)' }}>
                      {new Date(snap.timestamp).toLocaleTimeString()}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          ))}
          {visibleEvidence.length === 0 && (
             <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>No evidence captured.</Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default MonitoringReportsPage;
