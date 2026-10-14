import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Button, TextField,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Chip, IconButton, Tooltip, Stack, CircularProgress, Alert, Grid, Tabs, Tab,
  Divider, MenuItem, InputAdornment, Dialog, DialogTitle, DialogContent, DialogActions,
  LinearProgress, TablePagination, FormControlLabel, Radio, RadioGroup, Paper
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SearchIcon from '@mui/icons-material/Search';
import AssessmentIcon from '@mui/icons-material/Assessment';
import PeopleIcon from '@mui/icons-material/People';
import TimerIcon from '@mui/icons-material/Timer';
import SettingsIcon from '@mui/icons-material/Settings';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import VisibilityIcon from '@mui/icons-material/Visibility';
import RefreshIcon from '@mui/icons-material/Refresh';
import SortIcon from '@mui/icons-material/Sort';
import DownloadIcon from '@mui/icons-material/Download';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import PendingIcon from '@mui/icons-material/Pending';
import EditNoteIcon from '@mui/icons-material/EditNote';
import ClassIcon from '@mui/icons-material/Class';
import AssignmentIcon from '@mui/icons-material/Assignment';
import SecurityIcon from '@mui/icons-material/Security';

import apiClient from '../../services/apiClient';
import { WebSocketClient } from '../../services/wsClient';
import { getErrorMessage } from '../../utils/errorHandler';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';

const STATUS_CHIP_CONFIG: Record<string, { label: string; color: 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' }> = {
  DRAFT: { label: 'Draft', color: 'default' },
  READY: { label: 'Ready', color: 'info' },
  RUNNING: { label: 'Running', color: 'success' },
  PAUSED: { label: 'Paused', color: 'warning' },
  COMPLETED: { label: 'Submitted / Completed', color: 'success' },
  SUBMITTED: { label: 'Submitted', color: 'success' },
  EXPIRED: { label: 'Auto Submitted', color: 'warning' },
  AUTO_SUBMITTED: { label: 'Auto Submitted', color: 'warning' },
  MANUAL_SUBMITTED: { label: 'Manual Submitted', color: 'success' },
  ABSENT: { label: 'Absent', color: 'error' },
  FINALIZED: { label: 'Finalized', color: 'success' },
  PENDING: { label: 'Pending Evaluation', color: 'error' },
  DRAFT_EVAL: { label: 'Draft Evaluation', color: 'warning' }
};

const ExamDetailsWorkspacePage: React.FC = () => {
  const { examId } = useParams<{ examId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const initialTab = searchParams.get('tab') ? parseInt(searchParams.get('tab') || '0') : 0;
  const [activeTab, setActiveTab] = useState<number>(initialTab);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [exam, setExam] = useState<any>(null);

  // Attempts State & Dashboard (Phases 2, 3, 4, 5, 6, 7, 18)
  const [attempts, setAttempts] = useState<any[]>([]);
  const [dashboardStats, setDashboardStats] = useState<any>(null);
  const [allMatchingSessionIds, setAllMatchingSessionIds] = useState<number[]>([]);
  const [attemptsLoading, setAttemptsLoading] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [evalFilter, setEvalFilter] = useState<string>('ALL');
  const [specialFilter, setSpecialFilter] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<string>('reg_num');
  const [sortOrder, setSortOrder] = useState<string>('asc');
  const [page, setPage] = useState<number>(0);
  const [rowsPerPage, setRowsPerPage] = useState<number>(25);
  const [totalCount, setTotalCount] = useState<number>(0);

  // Result Export Dialog (Phases 13 & 14)
  const [exportOpen, setExportOpen] = useState<boolean>(false);
  const [exportFormat, setExportFormat] = useState<string>('csv');
  const [exportScope, setExportScope] = useState<string>('filtered');
  const [exporting, setExporting] = useState<boolean>(false);

  // Assigned Students State
  const [assignedStudents, setAssignedStudents] = useState<any[]>([]);
  const [studentsLoading, setStudentsLoading] = useState<boolean>(false);

  useEffect(() => {
    if (examId) {
      fetchExamDetails(parseInt(examId));
    }
  }, [examId]);

  useEffect(() => {
    if (examId && (activeTab === 2 || activeTab === 3)) {
      fetchAttempts(parseInt(examId));
    } else if (examId && activeTab === 1) {
      fetchAssignedStudents(parseInt(examId));
    }
  }, [examId, activeTab, searchQuery, statusFilter, evalFilter, specialFilter, sortBy, sortOrder, page, rowsPerPage]);

  // Real-Time WebSocket Auto-Update Subscription for Live Monitoring Command Center (Phase 3 & 4)
  useEffect(() => {
    if (!examId || activeTab !== 3) return;

    let ws: WebSocketClient | null = null;
    try {
      ws = new WebSocketClient(parseInt(examId));
      ws.onMessage((data: any) => {
        if (data && data.exam_session_id) {
          setAttempts(prev => prev.map(att => {
            if (att.session_id === data.exam_session_id || att.id === data.exam_session_id) {
              const newRisk = data.payload?.data?.risk_score !== undefined ? data.payload.data.risk_score : att.final_risk_score;
              const newSeverity = data.payload?.severity || att.risk_level;
              return { ...att, final_risk_score: newRisk, risk_level: newSeverity };
            }
            return att;
          }));
        }
      });
    } catch (err) {
      console.error("Failed to connect WebSocket in Live Command Center", err);
    }

    return () => {
      if (ws) ws.disconnect();
    };
  }, [examId, activeTab]);

  const fetchExamDetails = async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(`/workspace/exams/${id}`);
      setExam(res.data);
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const fetchAttempts = async (id: number) => {
    setAttemptsLoading(true);
    try {
      const params = new URLSearchParams({
        search: searchQuery,
        status_filter: statusFilter,
        eval_filter: evalFilter,
        special_filter: specialFilter,
        sort_by: sortBy,
        sort_order: sortOrder,
        page: (page + 1).toString(),
        page_size: rowsPerPage.toString()
      });
      const res = await apiClient.get(`/workspace/exams/${id}/attempts?${params.toString()}`);
      setAttempts(res.data.attempts || []);
      setDashboardStats(res.data.dashboard || null);
      setAllMatchingSessionIds(res.data.all_matching_session_ids || []);
      setTotalCount(res.data.total_count || 0);
    } catch (err: any) {
      console.error(getErrorMessage(err));
    } finally {
      setAttemptsLoading(false);
    }
  };

  const fetchAssignedStudents = async (id: number) => {
    setStudentsLoading(true);
    try {
      const res = await apiClient.get(`/workspace/exams/${id}/students`);
      setAssignedStudents(res.data);
      if (Array.isArray(res.data)) {
        setExam(prev => prev ? { ...prev, assigned_students_count: res.data.length } : prev);
      }
    } catch (err: any) {
      console.error(getErrorMessage(err));
    } finally {
      setStudentsLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
    setSearchParams({ tab: newValue.toString() });
  };

  const handleExportDownload = async () => {
    if (!examId) return;
    setExporting(true);
    try {
      const params = new URLSearchParams({
        export_format: exportFormat,
        search: exportScope === 'filtered' ? searchQuery : '',
        status_filter: exportScope === 'filtered' ? statusFilter : (exportScope === 'submitted' ? 'SUBMITTED' : 'ALL'),
        eval_filter: exportScope === 'filtered' ? evalFilter : (exportScope === 'finalized' ? 'FINALIZED' : (exportScope === 'draft' ? 'DRAFT' : (exportScope === 'pending' ? 'PENDING_EVALUATION' : 'ALL'))),
        special_filter: exportScope === 'filtered' ? specialFilter : 'ALL',
        sort_by: sortBy,
        sort_order: sortOrder
      });

      const res = await apiClient.get(`/workspace/exams/${examId}/export-results?${params.toString()}`);
      
      if (exportFormat === 'csv' && res.data.content) {
        const blob = new Blob([res.data.content], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', res.data.filename || `Exam_${examId}_Results.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else {
        const blob = new Blob([JSON.stringify(res.data.rows, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', res.data.filename || `Exam_${examId}_Results.json`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
      setExportOpen(false);
    } catch (err: any) {
      alert(getErrorMessage(err));
    } finally {
      setExporting(false);
    }
  };

  const handleNavigateToReview = (sessionId: number, tab: 'paper' | 'monitoring' = 'paper') => {
    // Pass search/filter/sort context and ordered session IDs in state
    const params = new URLSearchParams({
      tab,
      search: searchQuery,
      status_filter: statusFilter,
      eval_filter: evalFilter,
      special_filter: specialFilter,
      sort_by: sortBy,
      sort_order: sortOrder
    });
    navigate(`/examiner/attempts/${sessionId}/review?${params.toString()}`, {
      state: {
        allMatchingSessionIds,
        examId: exam.id
      }
    });
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !exam) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>{error || 'Exam not found.'}</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/examiner/exams')}>
          Back to Exam Repository
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ pb: 6 }}>
      {/* Header Workspace Bar */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <IconButton onClick={() => navigate('/examiner/exams')} sx={{ bgcolor: '#fff', border: '1px solid #cbd5e1' }}>
            <ArrowBackIcon />
          </IconButton>
          <Box>
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>
                {exam.course_name}
              </Typography>
              <Chip label={exam.status} color={STATUS_CHIP_CONFIG[exam.status]?.color || 'default'} size="small" />
            </Stack>
            <Typography variant="h4" fontWeight={700} color="primary.main">
              {exam.title}
            </Typography>
          </Box>
        </Stack>

        <Stack direction="row" spacing={1.5}>
          <Button variant="outlined" startIcon={<DownloadIcon />} onClick={() => setExportOpen(true)}>
            Export Results
          </Button>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => fetchExamDetails(exam.id)}>
            Refresh
          </Button>
          {['DRAFT', 'READY'].includes(exam.status) && (
            <Button variant="contained" onClick={() => navigate(`/examiner/exams/build?id=${exam.id}`)}>
              Edit Config
            </Button>
          )}
        </Stack>
      </Box>

      {/* Tabs Bar */}
      <Card elevation={1} sx={{ borderRadius: 2, mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="scrollable"
          scrollButtons="auto"
          sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}
        >
          <Tab icon={<AssessmentIcon fontSize="small" />} iconPosition="start" label="Overview" />
          <Tab icon={<PeopleIcon fontSize="small" />} iconPosition="start" label={`Students (${exam.assigned_students_count || 0})`} />
          <Tab icon={<VisibilityIcon fontSize="small" />} iconPosition="start" label="Attempts & Evaluation Workspace" />
          <Tab icon={<VisibilityIcon fontSize="small" color="success" />} iconPosition="start" label="Live Monitoring Command Center" />
          <Tab icon={<TimerIcon fontSize="small" />} iconPosition="start" label="Schedule" />
          <Tab icon={<SettingsIcon fontSize="small" />} iconPosition="start" label="Settings" />
          <Tab icon={<AnalyticsIcon fontSize="small" />} iconPosition="start" label="Analytics" disabled />
        </Tabs>

        {/* Tab 0: Overview */}
        {activeTab === 0 && (
          <CardContent sx={{ p: 4 }}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={8}>
                <Typography variant="h6" fontWeight={700} gutterBottom>Examination Overview</Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  {exam.description || 'No detailed description provided.'}
                </Typography>
                <Divider sx={{ my: 2 }} />

                <Grid container spacing={2}>
                  <Grid item xs={6} sm={4}>
                    <Typography variant="caption" color="text.secondary">Course Code</Typography>
                    <Typography variant="body1" fontWeight={700}>{exam.course_name}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={4}>
                    <Typography variant="caption" color="text.secondary">Subject</Typography>
                    <Typography variant="body1" fontWeight={700}>{exam.subject || 'N/A'}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={4}>
                    <Typography variant="caption" color="text.secondary">Total Marks</Typography>
                    <Typography variant="body1" fontWeight={700}>{exam.total_marks || 100} pts</Typography>
                  </Grid>
                  <Grid item xs={6} sm={4}>
                    <Typography variant="caption" color="text.secondary">Paper Academic Duration</Typography>
                    <Typography variant="body1" fontWeight={700}>{exam.duration_minutes} minutes</Typography>
                  </Grid>
                  <Grid item xs={6} sm={4}>
                    <Typography variant="caption" color="text.secondary">Question Paper ID</Typography>
                    <Typography variant="body1" fontWeight={700}>Paper #{exam.question_paper_id || 'N/A'}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={4}>
                    <Typography variant="caption" color="text.secondary">Assigned Candidates</Typography>
                    <Typography variant="body1" fontWeight={700}>{exam.assigned_students_count || 0}</Typography>
                  </Grid>
                </Grid>
              </Grid>

              <Grid item xs={12} md={4}>
                <Card variant="outlined" sx={{ p: 2.5, bgcolor: '#f8fafc', borderRadius: 2 }}>
                  <Typography variant="subtitle2" fontWeight={700} color="primary.main" gutterBottom>
                    Execution Controls
                  </Typography>
                  <Stack spacing={1.5} sx={{ mt: 2 }}>
                    <Typography variant="caption" color="text.secondary">
                      Current Status: <strong>{exam.status}</strong>
                    </Typography>
                    <Button variant="contained" fullWidth size="small" onClick={() => setActiveTab(2)}>
                      Open Evaluation Workspace
                    </Button>
                  </Stack>
                </Card>
              </Grid>
            </Grid>
          </CardContent>
        )}

        {/* Tab 1: Students */}
        {activeTab === 1 && (
          <CardContent sx={{ p: 4 }}>
            <Typography variant="h6" fontWeight={700} gutterBottom>Assigned Candidates</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Students permitted to enter this examination session.
            </Typography>
            {studentsLoading ? (
              <CircularProgress size={24} />
            ) : (
              <TableContainer component={Box} sx={{ border: '1px solid #e2e8f0', borderRadius: 1 }}>
                <Table size="small">
                  <TableHead sx={{ bgcolor: '#f8fafc' }}>
                    <TableRow>
                      <TableCell>Student ID</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {assignedStudents.length === 0 ? (
                      <TableRow><TableCell colSpan={2} align="center">No candidates assigned yet.</TableCell></TableRow>
                    ) : (
                      assignedStudents.map((sId: number) => (
                        <TableRow key={sId}>
                          <TableCell>Student #{sId}</TableCell>
                          <TableCell><Chip label="Assigned" color="success" size="small" /></TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        )}

        {/* Tab 2: Attempts & Evaluation Workspace (Phases 2, 3, 4, 5, 6, 7, 8, 18) */}
        {activeTab === 2 && (
          <CardContent sx={{ p: 3 }}>
            {/* PHASE 2 & 3: EVALUATION DASHBOARD & PROGRESS CARDS */}
            {dashboardStats && (
              <Box sx={{ mb: 4 }}>
                <Typography variant="h6" fontWeight={700} color="primary.main" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <AssessmentIcon fontSize="small" /> Evaluation Analytics Dashboard
                </Typography>

                {/* Overall Evaluation Linear Progress Bar */}
                <Paper variant="outlined" sx={{ p: 2.5, mb: 3, bgcolor: '#f8fafc', borderRadius: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="subtitle2" fontWeight={700}>
                      Overall Evaluation Completion
                    </Typography>
                    <Typography variant="subtitle2" fontWeight={800} color="primary.main">
                      {dashboardStats.finalized_count} / {dashboardStats.total_students} Finalized ({dashboardStats.progress_percentage}%)
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={dashboardStats.progress_percentage}
                    sx={{ height: 10, borderRadius: 5, bgcolor: '#e2e8f0' }}
                    color={dashboardStats.progress_percentage === 100 ? 'success' : 'primary'}
                  />
                  <Stack direction="row" spacing={3} sx={{ mt: 1.5 }}>
                    <Typography variant="caption" color="text.secondary">
                      <strong style={{ color: '#16a34a' }}>● Finalized:</strong> {dashboardStats.finalized_count}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      <strong style={{ color: '#ca8a04' }}>● Draft:</strong> {dashboardStats.draft_count}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      <strong style={{ color: '#dc2626' }}>● Pending:</strong> {dashboardStats.pending_count}
                    </Typography>
                  </Stack>
                </Paper>

                {/* Dashboard Metrics Grid */}
                <Grid container spacing={2}>
                  <Grid item xs={6} sm={4} md={2}>
                    <Paper variant="outlined" sx={{ p: 2, textAlign: 'center', bgcolor: '#ffffff' }}>
                      <Typography variant="caption" color="text.secondary">Total Cohort</Typography>
                      <Typography variant="h5" fontWeight={800} color="primary.main">{dashboardStats.total_students}</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} sm={4} md={2}>
                    <Paper variant="outlined" sx={{ p: 2, textAlign: 'center', bgcolor: '#ffffff' }}>
                      <Typography variant="caption" color="text.secondary">Submitted</Typography>
                      <Typography variant="h5" fontWeight={800} color="success.main">{dashboardStats.submitted_count}</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} sm={4} md={2}>
                    <Paper variant="outlined" sx={{ p: 2, textAlign: 'center', bgcolor: '#ffffff' }}>
                      <Typography variant="caption" color="text.secondary">Absent</Typography>
                      <Typography variant="h5" fontWeight={800} color="error.main">{dashboardStats.absent_count}</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} sm={4} md={2}>
                    <Paper variant="outlined" sx={{ p: 2, textAlign: 'center', bgcolor: '#ffffff' }}>
                      <Typography variant="caption" color="text.secondary">Avg Score</Typography>
                      <Typography variant="h5" fontWeight={800} color="info.main">{dashboardStats.average_score} pts</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} sm={4} md={2}>
                    <Paper variant="outlined" sx={{ p: 2, textAlign: 'center', bgcolor: '#ffffff' }}>
                      <Typography variant="caption" color="text.secondary">Highest Score</Typography>
                      <Typography variant="h5" fontWeight={800} color="success.main">{dashboardStats.highest_score} pts</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} sm={4} md={2}>
                    <Paper variant="outlined" sx={{ p: 2, textAlign: 'center', bgcolor: '#ffffff' }}>
                      <Typography variant="caption" color="text.secondary">Lowest Score</Typography>
                      <Typography variant="h5" fontWeight={800} color="warning.main">{dashboardStats.lowest_score} pts</Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </Box>
            )}

            {/* SEARCH, FILTERS & SORTING CONTROLS (Phases 5, 6, 7) */}
            <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap', alignItems: 'center' }}>
              <TextField
                placeholder="Search name, reg #, dept, or program..."
                size="small"
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setPage(0); }}
                sx={{ minWidth: 280 }}
                InputProps={{
                  startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment>
                }}
              />

              <TextField
                select
                size="small"
                label="Attempt Status"
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
                sx={{ minWidth: 160 }}
              >
                <MenuItem value="ALL">All Attempt Statuses</MenuItem>
                <MenuItem value="RUNNING">Running</MenuItem>
                <MenuItem value="SUBMITTED">Submitted</MenuItem>
                <MenuItem value="EXPIRED">Auto Submitted</MenuItem>
                <MenuItem value="ABSENT">Absent</MenuItem>
              </TextField>

              <TextField
                select
                size="small"
                label="Evaluation Status"
                value={evalFilter}
                onChange={(e) => { setEvalFilter(e.target.value); setPage(0); }}
                sx={{ minWidth: 170 }}
              >
                <MenuItem value="ALL">All Evaluation States</MenuItem>
                <MenuItem value="FINALIZED">Finalized</MenuItem>
                <MenuItem value="DRAFT">Draft Evaluation</MenuItem>
                <MenuItem value="PENDING_EVALUATION">Pending Evaluation</MenuItem>
              </TextField>

              <TextField
                select
                size="small"
                label="Cohort Filter"
                value={specialFilter}
                onChange={(e) => { setSpecialFilter(e.target.value); setPage(0); }}
                sx={{ minWidth: 170 }}
              >
                <MenuItem value="ALL">All Cohort Filters</MenuItem>
                <MenuItem value="HIGH_SCORE">High Score (&ge; 80%)</MenuItem>
                <MenuItem value="LOW_SCORE">Low Score (&lt; 50%)</MenuItem>
                <MenuItem value="MANUAL_SUBMISSION">Manual Submission</MenuItem>
                <MenuItem value="AUTO_SUBMISSION">Auto Time Expiry</MenuItem>
                <MenuItem value="RECOVERY_EVENTS">With Recovery Events</MenuItem>
              </TextField>

              <TextField
                select
                size="small"
                label="Sort By"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                sx={{ minWidth: 160 }}
              >
                <MenuItem value="reg_num">Registration Number</MenuItem>
                <MenuItem value="time">Submission Time</MenuItem>
                <MenuItem value="final_score">Final Score</MenuItem>
                <MenuItem value="objective_score">Objective Score</MenuItem>
                <MenuItem value="subjective_score">Subjective Score</MenuItem>
                <MenuItem value="percentage">Percentage (%)</MenuItem>
                <MenuItem value="duration">Duration Used</MenuItem>
                <MenuItem value="name">Alphabetically (Name)</MenuItem>
              </TextField>

              <Button
                variant="outlined"
                size="small"
                onClick={() => setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')}
                startIcon={<SortIcon />}
              >
                {sortOrder.toUpperCase()}
              </Button>
            </Box>

            {/* ATTEMPTS TABLE WITH QUICK BADGES (Phase 4 & 8) */}
            <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
              <Table size="small">
                <TableHead sx={{ bgcolor: '#f8fafc' }}>
                  <TableRow>
                    <TableCell>Candidate Name</TableCell>
                    <TableCell>Reg Number</TableCell>
                    <TableCell>Program / Dept</TableCell>
                    <TableCell>Attempt Status</TableCell>
                    <TableCell>Evaluation Status</TableCell>
                    <TableCell>Objective Score</TableCell>
                    <TableCell>Subjective Score</TableCell>
                    <TableCell>Final Score</TableCell>
                    <TableCell>Recoveries</TableCell>
                    <TableCell align="right">Action</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {attemptsLoading ? (
                    <TableRow><TableCell colSpan={10} align="center"><CircularProgress size={24} sx={{ my: 3 }} /></TableCell></TableRow>
                  ) : attempts.length === 0 ? (
                    <TableRow><TableCell colSpan={10} align="center"><Typography color="text.secondary" sx={{ py: 3 }}>No student attempts found matching selected filters.</Typography></TableCell></TableRow>
                  ) : (
                    attempts.map((att: any) => {
                      const cfg = STATUS_CHIP_CONFIG[att.status] || STATUS_CHIP_CONFIG['DRAFT'];
                      const evalCfg = STATUS_CHIP_CONFIG[att.evaluation_status] || STATUS_CHIP_CONFIG['PENDING'];

                      return (
                        <TableRow key={att.session_id} hover>
                          <TableCell>
                            <Typography variant="body2" fontWeight={700}>{att.student_name}</Typography>
                          </TableCell>
                          <TableCell>
                            <Chip label={att.registration_number} size="small" variant="outlined" />
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption" display="block" fontWeight={600}>{att.program}</Typography>
                            <Typography variant="caption" color="text.secondary">{att.department}</Typography>
                          </TableCell>
                          <TableCell>
                            <Chip label={cfg.label} color={cfg.color} size="small" />
                          </TableCell>
                          <TableCell>
                            <Chip label={evalCfg.label} color={evalCfg.color} size="small" />
                          </TableCell>
                          {/* Quick Review Score Badges (Phase 8) */}
                          <TableCell>
                            <Typography variant="body2" fontWeight={600} color="text.secondary">
                              {att.objective_score} Marks
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" fontWeight={600} color={att.evaluation_status === 'PENDING' ? 'warning.main' : 'text.primary'}>
                              {att.evaluation_status === 'PENDING' ? 'Pending' : `${att.subjective_score} Marks`}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" fontWeight={700} color="primary.main">
                              {att.current_score} / {att.total_marks} Marks ({att.percentage}%)
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip label={`${att.recovery_count}`} color={att.recovery_count > 0 ? 'warning' : 'default'} size="small" variant="outlined" />
                          </TableCell>
                          <TableCell align="right">
                            {(() => {
                              const isReviewable = ['SUBMITTED', 'EXPIRED', 'AUTO_SUBMITTED', 'COMPLETED', 'TERMINATED', 'EVALUATED', 'FINALIZED', 'RUNNING', 'PAUSED'].includes((att.status || '').toUpperCase());
                              return (
                                <Tooltip title={isReviewable ? "" : "No submitted attempt available."}>
                                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                                    <Button
                                      variant="contained"
                                      size="small"
                                      disabled={!isReviewable}
                                      startIcon={<AssignmentIcon fontSize="small" />}
                                      onClick={() => handleNavigateToReview(att.session_id, 'paper')}
                                      sx={{ textTransform: 'none', fontWeight: 600, fontSize: '0.75rem', py: 0.5 }}
                                    >
                                      Paper Review
                                    </Button>
                                    <Button
                                      variant="outlined"
                                      color="secondary"
                                      size="small"
                                      disabled={!isReviewable}
                                      startIcon={<SecurityIcon fontSize="small" />}
                                      onClick={() => handleNavigateToReview(att.session_id, 'monitoring')}
                                      sx={{ textTransform: 'none', fontWeight: 600, fontSize: '0.75rem', py: 0.5 }}
                                    >
                                      Monitoring Review
                                    </Button>
                                  </Stack>
                                </Tooltip>
                              );
                            })()}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>

              {/* SERVER-SIDE PAGINATION CONTROLS (Phase 18) */}
              <TablePagination
                component="div"
                count={totalCount}
                page={page}
                onPageChange={(e, newPage) => setPage(newPage)}
                rowsPerPage={rowsPerPage}
                onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
                rowsPerPageOptions={[10, 25, 50, 100]}
              />
            </TableContainer>
          </CardContent>
        )}

        {/* Tab 3: Live Monitoring Command Center */}
        {activeTab === 3 && (
          <CardContent sx={{ p: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Box>
                <Typography variant="h6" fontWeight={700} color="primary.main" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <VisibilityIcon /> Real-Time Live Monitoring Command Center
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Supervise active candidates in real time. Continuous risk updates, candidate behavior, and immediate evidence preview.
                </Typography>
              </Box>
              <Stack direction="row" spacing={1} alignItems="center">
                <Chip
                  icon={<FiberManualRecordIcon style={{ color: '#22c55e', fontSize: 12 }} />}
                  label="Real-Time WebSocket Feed Active"
                  color="success"
                  variant="outlined"
                  size="small"
                  sx={{ fontWeight: 700, borderColor: '#22c55e', color: '#15803d', bgcolor: '#f0fdf4' }}
                />
              </Stack>
            </Box>

            {/* Metric Cards */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} sm={3}>
                <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, bgcolor: '#f8fafc' }}>
                  <Typography variant="caption" color="text.secondary">Active Candidates</Typography>
                  <Typography variant="h5" fontWeight={700} color="primary.main">
                    {attempts.filter(a => ['RUNNING', 'ACTIVE', 'IN_PROGRESS'].includes(a.status)).length} / {attempts.length}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} sm={3}>
                <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, bgcolor: '#fff5f5', borderColor: '#feb2b2' }}>
                  <Typography variant="caption" color="text.secondary">High / Critical Risk Candidates</Typography>
                  <Typography variant="h5" fontWeight={700} color="error.main">
                    {attempts.filter(a => ['HIGH', 'CRITICAL'].includes(a.risk_level)).length}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} sm={3}>
                <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, bgcolor: '#f0fdf4', borderColor: '#86efac' }}>
                  <Typography variant="caption" color="text.secondary">Compliant Candidates</Typography>
                  <Typography variant="h5" fontWeight={700} color="success.main">
                    {attempts.filter(a => a.risk_level === 'LOW' || !a.risk_level).length}
                  </Typography>
                </Paper>
              </Grid>
              <Grid item xs={12} sm={3}>
                <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, bgcolor: '#eff6ff', borderColor: '#93c5fd' }}>
                  <Typography variant="caption" color="text.secondary">Total Candidate Attempts</Typography>
                  <Typography variant="h5" fontWeight={700} color="info.main">
                    {attempts.length}
                  </Typography>
                </Paper>
              </Grid>
            </Grid>

            {/* Live Candidate Cards */}
            {attempts.length === 0 ? (
              <Alert severity="info">No candidate attempts recorded for this examination session.</Alert>
            ) : (
              <Grid container spacing={2}>
                {attempts.map((att) => (
                  <Grid item xs={12} md={6} lg={4} key={att.session_id || att.id}>
                    <Card variant="outlined" sx={{ borderRadius: 2, borderColor: att.risk_level === 'CRITICAL' ? '#f87171' : '#e2e8f0' }}>
                      <CardContent sx={{ p: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="subtitle2" fontWeight={700}>
                            {att.student_name}
                          </Typography>
                          <Chip
                            label={`Risk: ${(att.final_risk_score ? (att.final_risk_score <= 1.0 ? att.final_risk_score * 100 : att.final_risk_score) : 0).toFixed(0)}% (${att.risk_level || 'LOW'})`}
                            size="small"
                            color={att.risk_level === 'CRITICAL' || att.risk_level === 'HIGH' ? 'error' : att.risk_level === 'MEDIUM' ? 'warning' : 'success'}
                            sx={{ fontWeight: 700, fontSize: '0.7rem' }}
                          />
                        </Box>
                        <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                          Reg #: {att.registration_number || att.student_id} | Status: {att.status}
                        </Typography>

                        <Divider sx={{ my: 1 }} />

                        <Stack spacing={0.5} sx={{ mb: 1.5 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="caption" color="text.secondary">Media Owner:</Typography>
                            <Typography variant="caption" fontWeight={600} color="success.main">● Browser (Camera Decoupled)</Typography>
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="caption" color="text.secondary">Total Violations:</Typography>
                            <Typography variant="caption" fontWeight={600}>{att.total_violations || 0} recorded</Typography>
                          </Box>
                          {att.latest_violation && (
                            <Box sx={{ bgcolor: '#fff1f2', p: 1, borderRadius: 1, mt: 0.5 }}>
                              <Typography variant="caption" fontWeight={700} color="error.main" display="block">
                                Latest: {att.latest_violation.violation_type} ({att.latest_violation.severity})
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {att.latest_violation.description}
                              </Typography>
                            </Box>
                          )}
                        </Stack>

                        {(() => {
                          const isReviewable = ['SUBMITTED', 'EXPIRED', 'AUTO_SUBMITTED', 'COMPLETED', 'TERMINATED', 'EVALUATED', 'FINALIZED', 'RUNNING', 'PAUSED'].includes((att.status || '').toUpperCase());
                          return (
                            <Tooltip title={isReviewable ? "" : "No submitted attempt available."}>
                              <span>
                                <Button
                                  fullWidth
                                  variant="outlined"
                                  size="small"
                                  disabled={!isReviewable}
                                  startIcon={<VisibilityIcon />}
                                  onClick={() => handleNavigateToReview(att.session_id || att.id)}
                                >
                                  Review Candidate Attempt
                                </Button>
                              </span>
                            </Tooltip>
                          );
                        })()}
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </CardContent>
        )}

        {/* Tab 4: Schedule */}
        {activeTab === 4 && (
          <CardContent sx={{ p: 4 }}>
            <Typography variant="h6" fontWeight={700} gutterBottom>Schedule Details</Typography>
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12} sm={4}>
                <Typography variant="caption" color="text.secondary">Scheduled Start</Typography>
                <Typography variant="body1" fontWeight={700}>{new Date(exam.scheduled_start).toLocaleString()}</Typography>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Typography variant="caption" color="text.secondary">Scheduled End</Typography>
                <Typography variant="body1" fontWeight={700}>{new Date(exam.scheduled_end).toLocaleString()}</Typography>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Typography variant="caption" color="text.secondary">Paper Academic Duration</Typography>
                <Typography variant="body1" fontWeight={700}>{exam.duration_minutes} mins</Typography>
              </Grid>
            </Grid>
          </CardContent>
        )}

        {/* Tab 5: Settings */}
        {activeTab === 5 && (
          <CardContent sx={{ p: 4 }}>
            <Typography variant="h6" fontWeight={700} gutterBottom>Proctoring & Security Rules</Typography>
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" fontWeight={600}>Camera Required: {exam.monitoring_config?.camera_required ? 'Yes' : 'No'}</Typography>
                <Typography variant="body2" fontWeight={600}>Microphone Required: {exam.monitoring_config?.microphone_required ? 'Yes' : 'No'}</Typography>
                <Typography variant="body2" fontWeight={600}>Fullscreen Enforced: {exam.monitoring_config?.fullscreen_required ? 'Yes' : 'No'}</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" fontWeight={600}>Copy/Paste Disabled: {exam.browser_rules?.disable_copy_paste ? 'Yes' : 'No'}</Typography>
                <Typography variant="body2" fontWeight={600}>Right Click Disabled: {exam.browser_rules?.disable_right_click ? 'Yes' : 'No'}</Typography>
              </Grid>
            </Grid>
          </CardContent>
        )}
      </Card>

      {/* RESULT EXPORT DIALOG (Phases 13 & 14) */}
      <Dialog open={exportOpen} onClose={() => setExportOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Export Examination Results</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" paragraph>
            Export evaluation results for <strong>{exam.title}</strong> into a structured file format.
          </Typography>

          <Typography variant="subtitle2" fontWeight={700} sx={{ mt: 2, mb: 1 }}>File Format:</Typography>
          <RadioGroup row value={exportFormat} onChange={(e) => setExportFormat(e.target.value)}>
            <FormControlLabel value="csv" control={<Radio />} label="CSV Document (.csv)" />
            <FormControlLabel value="excel" control={<Radio />} label="Excel JSON Dataset (.json)" />
          </RadioGroup>

          <Typography variant="subtitle2" fontWeight={700} sx={{ mt: 2, mb: 1 }}>Export Scope Validation:</Typography>
          <RadioGroup value={exportScope} onChange={(e) => setExportScope(e.target.value)}>
            <FormControlLabel value="filtered" control={<Radio />} label={`Active Filtered Scope (${totalCount} Rows)`} />
            <FormControlLabel value="all" control={<Radio />} label={`Entire Class (${dashboardStats?.total_students || 0} Students)`} />
            <FormControlLabel value="finalized" control={<Radio />} label={`Only Finalized Attempts (${dashboardStats?.finalized_count || 0})`} />
            <FormControlLabel value="submitted" control={<Radio />} label={`Only Submitted Attempts (${dashboardStats?.submitted_count || 0})`} />
          </RadioGroup>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setExportOpen(false)} disabled={exporting}>Cancel</Button>
          <Button
            variant="contained"
            startIcon={<DownloadIcon />}
            onClick={handleExportDownload}
            disabled={exporting}
          >
            {exporting ? 'Generating Export...' : 'Download Export'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ExamDetailsWorkspacePage;
