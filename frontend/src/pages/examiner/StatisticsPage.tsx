import { useState, useEffect } from 'react';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';
import {
  Box, Typography, Card, CardContent, Grid, Chip, Divider,
  Stack, Button, LinearProgress, FormControl, InputLabel, Select, MenuItem, CircularProgress, Alert
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import AssignmentIcon from '@mui/icons-material/Assignment';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid';
import FaceIcon from '@mui/icons-material/Face';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import HeadphonesIcon from '@mui/icons-material/Headphones';
import PeopleAltIcon from '@mui/icons-material/PeopleAlt';
import CameraAltIcon from '@mui/icons-material/CameraAlt';

interface ReportSummary {
  exam_session_id: number;
  exam_name: string;
  student_name: string;
}

const StatisticsPage = () => {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | ''>('');
  const [reportDetail, setReportDetail] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReports();
  }, []);

  useEffect(() => {
    if (selectedSessionId) {
      fetchReportDetail(selectedSessionId as number);
    } else {
      setReportDetail(null);
    }
  }, [selectedSessionId]);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/reports');
      setReports(res.data);
      if (res.data.length > 0) {
        setSelectedSessionId(res.data[0].exam_session_id);
      }
    } catch (err: any) {
      console.error(err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const fetchReportDetail = async (id: number) => {
    setLoading(true);
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

  const handleExportCSV = () => {
    if (reports.length === 0) return;
    
    const headers = ["Session ID", "Student Name", "Exam Name", "Date", "Duration (mins)", "Final Risk Score", "Total Violations"];
    const rows = reports.map((r: any) => [
      r.exam_session_id,
      `"${r.student_name}"`,
      `"${r.exam_name}"`,
      r.date ? new Date(r.date).toLocaleString() : 'N/A',
      r.duration_minutes ? r.duration_minutes.toFixed(1) : 0,
      r.final_risk_score ? r.final_risk_score.toFixed(1) : 0,
      r.total_violations || 0
    ]);
    
    const csvContent = "data:text/csv;charset=utf-8," 
      + headers.join(",") + "\n" 
      + rows.map(e => e.join(",")).join("\n");
      
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "exam_statistics_report.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading && !reportDetail && reports.length === 0) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
  }

  const stats = reportDetail?.statistics;
  const total = stats?.total_violations || 1; // avoid div by 0

  const KPI_CARDS = stats ? [
    { label: 'Highest Risk Score', value: stats.highest_risk_score.toFixed(1), icon: <AssignmentIcon />, color: '#B00020' },
    { label: 'Total Evidence Captured', value: stats.total_snapshots, icon: <CameraAltIcon />, color: '#1976D2' },
    { label: 'Total Violations', value: stats.total_violations, icon: <WarningAmberIcon />, color: '#E65100' },
    { label: 'Avg Risk Score', value: stats.average_risk_score.toFixed(1), icon: <TrendingUpIcon />, color: '#2E7D32' },
  ] : [];

  const VIOLATION_CATEGORIES = stats ? [
    { label: 'Identity', count: stats.total_identity_events, color: '#B00020', percent: (stats.total_identity_events / total) * 100 },
    { label: 'Attention', count: stats.total_looking_away, color: '#E65100', percent: (stats.total_looking_away / total) * 100 },
    { label: 'Unauthorized Objects', count: stats.total_phone_detections, color: '#1565C0', percent: (stats.total_phone_detections / total) * 100 },
    { label: 'Communication / Audio', count: stats.total_earphone_events, color: '#2E7D32', percent: (stats.total_earphone_events / total) * 100 },
    { label: 'Absence / Multiple Persons', count: stats.total_face_absence + stats.total_multiple_person, color: '#546E7A', percent: ((stats.total_face_absence + stats.total_multiple_person) / total) * 100 },
  ].sort((a, b) => b.count - a.count) : [];

  const VIOLATION_STATS = stats ? [
    { icon: <FaceIcon />, label: 'Identity Mismatch', count: stats.total_identity_events },
    { icon: <VisibilityOffIcon />, label: 'Gaze / Attention', count: stats.total_looking_away },
    { icon: <PhoneAndroidIcon />, label: 'Phone Detected', count: stats.total_phone_detections },
    { icon: <HeadphonesIcon />, label: 'Earphones / Audio Events', count: stats.total_earphone_events },
    { icon: <PeopleAltIcon />, label: 'Multiple Persons', count: stats.total_multiple_person },
    { icon: <WarningAmberIcon />, label: 'Face Absent', count: stats.total_face_absence },
  ] : [];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" fontWeight={600}>Statistics</Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 250, backgroundColor: 'white' }}>
            <InputLabel>Select Exam Session</InputLabel>
            <Select
              value={selectedSessionId}
              label="Select Exam Session"
              onChange={(e) => setSelectedSessionId(e.target.value as number)}
            >
              {reports.map(r => (
                <MenuItem key={r.exam_session_id} value={r.exam_session_id}>
                  Session {r.exam_session_id} - {r.student_name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button variant="outlined" size="medium" startIcon={<DownloadIcon />} onClick={handleExportCSV}>Export CSV</Button>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
      
      {!selectedSessionId && !loading && (
        <Alert severity="info" sx={{ mb: 3 }}>Please select an exam session from the dropdown to view statistics.</Alert>
      )}

      {loading && selectedSessionId && (
         <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>
      )}

      {stats && !loading && (
        <>
          {/* KPI Cards */}
          <Grid container spacing={3} sx={{ mb: 4 }}>
            {KPI_CARDS.map((card) => (
              <Grid item xs={12} sm={6} md={3} key={card.label}>
                <Card elevation={1} sx={{ borderLeft: `4px solid ${card.color}` }}>
                  <CardContent sx={{ p: 2.5 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Box sx={{ color: card.color, opacity: 0.8 }}>{card.icon}</Box>
                    </Box>
                    <Typography variant="h3" fontWeight={700}>{card.value}</Typography>
                    <Typography variant="caption" color="text.secondary">{card.label}</Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          <Grid container spacing={3}>
            {/* Violation Categories */}
            <Grid item xs={12} md={6}>
              <Card elevation={1}>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>Violation Categories Breakdown</Typography>
                  <Divider sx={{ mb: 3 }} />
                  <Stack spacing={2}>
                    {VIOLATION_CATEGORIES.map((cat) => (
                      <Box key={cat.label}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                          <Typography variant="body2">{cat.label}</Typography>
                          <Typography variant="body2" fontWeight={600}>{cat.count}</Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={stats.total_violations === 0 ? 0 : cat.percent}
                          sx={{
                            height: 8, borderRadius: 4,
                            backgroundColor: '#ECEFF1',
                            '& .MuiLinearProgress-bar': { backgroundColor: cat.color, borderRadius: 4 },
                          }}
                        />
                      </Box>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            {/* Violation Stats Table */}
            <Grid item xs={12} md={6}>
              <Card elevation={1}>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>Detailed Metrics</Typography>
                  <Divider sx={{ mb: 2 }} />
                  <Stack spacing={0}>
                    {VIOLATION_STATS.map((stat, idx) => (
                      <Box key={stat.label}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 1.5 }}>
                          <Box sx={{ color: 'primary.main', display: 'flex' }}>{stat.icon}</Box>
                          <Typography variant="body2" sx={{ flexGrow: 1 }}>{stat.label}</Typography>
                          <Chip label={stat.count} size="small" sx={{ backgroundColor: 'primary.light', color: 'white', fontWeight: 700 }} />
                        </Box>
                        {idx < VIOLATION_STATS.length - 1 && <Divider />}
                      </Box>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  );
};

export default StatisticsPage;
