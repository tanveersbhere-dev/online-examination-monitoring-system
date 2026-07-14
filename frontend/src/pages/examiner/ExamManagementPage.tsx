import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Button, TextField,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Chip, IconButton, InputAdornment, Tooltip, Stack, Dialog, DialogTitle,
  DialogContent, DialogActions, Alert, CircularProgress, MenuItem,
  List, ListItem, ListItemText, Checkbox
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import StopIcon from '@mui/icons-material/Stop';
import PeopleIcon from '@mui/icons-material/People';
import BarChartIcon from '@mui/icons-material/BarChart';
import MonitorIcon from '@mui/icons-material/Monitor';
import apiClient from '../../services/apiClient';

const STATUS_CONFIG: Record<string, { label: string; color: 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' }> = {
  DRAFT: { label: 'Draft', color: 'default' },
  SCHEDULED: { label: 'Scheduled', color: 'primary' },
  READY: { label: 'Ready', color: 'info' },
  RUNNING: { label: 'Running', color: 'success' },
  PAUSED: { label: 'Paused', color: 'warning' },
  COMPLETED: { label: 'Completed', color: 'default' },
  CANCELLED: { label: 'Cancelled', color: 'error' },
};

interface Exam {
  id: number;
  title: string;
  course_name: string;
  status: string;
  scheduled_start: string;
  scheduled_end: string;
  duration_minutes: number;
  assigned_students_count: number;
}

interface QuestionPaper {
  id: number;
  title: string;
  course_name: string;
}

interface Student {
  id: number;
  full_name: string;
  username: string;
}

const ExamManagementPage = () => {
  const navigate = useNavigate();
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [openCreate, setOpenCreate] = useState(false);
  const [openAssign, setOpenAssign] = useState(false);
  const [selectedExamId, setSelectedExamId] = useState<number | null>(null);

  // Create Form State
  const [papers, setPapers] = useState<QuestionPaper[]>([]);
  const [createData, setCreateData] = useState({
    title: '', course_name: '', question_paper_id: '',
    date: '', start_time: '', end_time: '', duration_minutes: 120
  });
  const [submitting, setSubmitting] = useState(false);

  // Assign Students State
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedStudentIds, setSelectedStudentIds] = useState<number[]>([]);
  const [assigning, setAssigning] = useState(false);

  const fetchExams = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get('/exams');
      setExams(res.data);
    } catch (err: any) {
      setError("Failed to fetch examinations.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExams();
  }, []);

  const handleStatusChange = async (examId: number, action: 'start' | 'pause' | 'resume' | 'complete') => {
    try {
      await apiClient.patch(`/exams/${examId}/${action}`);
      fetchExams();
    } catch (err: any) {
      alert(err.response?.data?.detail || `Failed to ${action} examination.`);
    }
  };

  // --- Create Modal Logic ---
  const handleOpenCreate = async () => {
    try {
      const res = await apiClient.get('/exams/question-papers');
      setPapers(res.data);
      setOpenCreate(true);
      setError(null);
    } catch (err) {
      alert("Failed to load question papers. Please ensure you have uploaded at least one.");
    }
  };

  const handleCreateSubmit = async () => {
    try {
      setSubmitting(true);
      setError(null);
      const startDateTime = new Date(`${createData.date}T${createData.start_time}:00`).toISOString();
      const endDateTime = new Date(`${createData.date}T${createData.end_time}:00`).toISOString();

      await apiClient.post('/exams', {
        title: createData.title,
        course_name: createData.course_name,
        question_paper_id: parseInt(createData.question_paper_id),
        scheduled_start: startDateTime,
        scheduled_end: endDateTime,
        duration_minutes: createData.duration_minutes
      });
      setOpenCreate(false);
      setCreateData({ title: '', course_name: '', question_paper_id: '', date: '', start_time: '', end_time: '', duration_minutes: 120 });
      fetchExams();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Validation failed or scheduling conflict occurred.");
    } finally {
      setSubmitting(false);
    }
  };

  // --- Assign Modal Logic ---
  const handleOpenAssign = async (examId: number) => {
    try {
      setSelectedExamId(examId);
      const res = await apiClient.get('/students');
      setStudents(res.data);
      setSelectedStudentIds([]);
      setOpenAssign(true);
      setError(null);
    } catch (err) {
      alert("Failed to fetch students.");
    }
  };

  const handleToggleStudent = (id: number) => {
    setSelectedStudentIds(prev => prev.includes(id) ? prev.filter(sId => sId !== id) : [...prev, id]);
  };

  const handleAssignSubmit = async () => {
    if (!selectedExamId || selectedStudentIds.length === 0) return;
    try {
      setAssigning(true);
      setError(null);
      await apiClient.post(`/exams/${selectedExamId}/students`, {
        student_ids: selectedStudentIds
      });
      setOpenAssign(false);
      fetchExams();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to assign students.");
    } finally {
      setAssigning(false);
    }
  };

  const filteredExams = exams.filter(e => 
    e.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
    e.course_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" fontWeight={600}>Exam Management</Typography>
        <Button variant="contained" startIcon={<AddIcon />} sx={{ borderRadius: 2 }} onClick={handleOpenCreate}>
          Create Exam
        </Button>
      </Box>

      {error && !openCreate && !openAssign && (
        <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>
      )}

      <Card elevation={1}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <TextField
              placeholder="Search exams..."
              size="small"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              sx={{ maxWidth: 280 }}
              InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> }}
            />
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Exam Name</TableCell>
                  <TableCell>Course</TableCell>
                  <TableCell>Date & Time</TableCell>
                  <TableCell>Students</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={6} align="center"><CircularProgress size={24} sx={{ my: 2 }} /></TableCell></TableRow>
                ) : filteredExams.length === 0 ? (
                  <TableRow><TableCell colSpan={6} align="center"><Typography color="text.secondary">No exams found.</Typography></TableCell></TableRow>
                ) : filteredExams.map((exam) => {
                  const cfg = STATUS_CONFIG[exam.status] || STATUS_CONFIG['DRAFT'];
                  const startDate = new Date(exam.scheduled_start);
                  const endDate = new Date(exam.scheduled_end);
                  
                  return (
                    <TableRow key={exam.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}>{exam.title}</Typography>
                      </TableCell>
                      <TableCell><Chip label={exam.course_name} size="small" variant="outlined" /></TableCell>
                      <TableCell>
                        <Typography variant="body2">{startDate.toLocaleDateString()}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} – {endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <PeopleIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                          <Typography variant="body2">{exam.assigned_students_count}</Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip label={cfg.label} color={cfg.color} size="small" />
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                          {['DRAFT', 'SCHEDULED'].includes(exam.status) && (
                            <Tooltip title="Assign Students">
                              <IconButton size="small" onClick={() => handleOpenAssign(exam.id)}><AddIcon fontSize="small" /></IconButton>
                            </Tooltip>
                          )}
                          {['DRAFT', 'SCHEDULED', 'READY'].includes(exam.status) && (
                            <Tooltip title="Start">
                              <IconButton size="small" sx={{ color: 'success.main' }} onClick={() => handleStatusChange(exam.id, 'start')}>
                                <PlayArrowIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                          {exam.status === 'RUNNING' && (
                            <Tooltip title="Pause">
                              <IconButton size="small" sx={{ color: 'warning.main' }} onClick={() => handleStatusChange(exam.id, 'pause')}>
                                <PauseIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                          {exam.status === 'PAUSED' && (
                            <Tooltip title="Resume">
                              <IconButton size="small" sx={{ color: 'success.main' }} onClick={() => handleStatusChange(exam.id, 'resume')}>
                                <PlayArrowIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                          {(exam.status === 'RUNNING' || exam.status === 'PAUSED') && (
                            <Tooltip title="End Exam">
                              <IconButton size="small" sx={{ color: 'error.main' }} onClick={() => handleStatusChange(exam.id, 'complete')}>
                                <StopIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                          {exam.status === 'RUNNING' && (
                            <Tooltip title="Monitor Live">
                              <IconButton size="small" sx={{ color: 'primary.main' }} onClick={() => navigate('/examiner/monitoring')}>
                                <MonitorIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                          {exam.status === 'COMPLETED' && (
                            <Tooltip title="View Report">
                              <IconButton size="small" sx={{ color: 'primary.main' }} onClick={() => navigate('/examiner/reports')}>
                                <BarChartIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Create Exam Modal */}
      <Dialog open={openCreate} onClose={() => !submitting && setOpenCreate(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Examination</DialogTitle>
        <DialogContent dividers>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <Stack spacing={3} sx={{ mt: 1 }}>
            <TextField label="Exam Name" value={createData.title} onChange={e => setCreateData({...createData, title: e.target.value})} disabled={submitting} required fullWidth />
            <Stack direction="row" spacing={2}>
              <TextField label="Course Name" value={createData.course_name} onChange={e => setCreateData({...createData, course_name: e.target.value})} disabled={submitting} required fullWidth />
            </Stack>
            <TextField select label="Question Paper *" value={createData.question_paper_id} onChange={e => setCreateData({...createData, question_paper_id: e.target.value})} disabled={submitting} fullWidth>
              <MenuItem value="">Select Paper...</MenuItem>
              {papers.map(p => <MenuItem key={p.id} value={p.id}>{p.title} ({p.course_name})</MenuItem>)}
            </TextField>
            <TextField label="Date" type="date" InputLabelProps={{ shrink: true }} value={createData.date} onChange={e => setCreateData({...createData, date: e.target.value})} disabled={submitting} required fullWidth />
            <Stack direction="row" spacing={2}>
              <TextField label="Start Time" type="time" InputLabelProps={{ shrink: true }} value={createData.start_time} onChange={e => setCreateData({...createData, start_time: e.target.value})} disabled={submitting} required fullWidth />
              <TextField label="End Time" type="time" InputLabelProps={{ shrink: true }} value={createData.end_time} onChange={e => setCreateData({...createData, end_time: e.target.value})} disabled={submitting} required fullWidth />
            </Stack>
            <TextField label="Duration (minutes)" type="number" value={createData.duration_minutes} onChange={e => setCreateData({...createData, duration_minutes: parseInt(e.target.value)})} disabled={submitting} required fullWidth />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCreate(false)} disabled={submitting}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateSubmit} disabled={submitting || !createData.title || !createData.date || !createData.start_time || !createData.question_paper_id}>
            {submitting ? 'Creating...' : 'Create Exam'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Assign Students Modal */}
      <Dialog open={openAssign} onClose={() => !assigning && setOpenAssign(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Assign Students to Exam</DialogTitle>
        <DialogContent dividers>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Select students to register for this examination. Duplicate assignments will be automatically ignored by the server.
          </Typography>
          <List sx={{ width: '100%', bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 1, maxHeight: 300, overflow: 'auto' }}>
            {students.map((student) => {
              const labelId = `checkbox-list-label-${student.id}`;
              return (
                <ListItem
                  key={student.id}
                  disablePadding
                  secondaryAction={<Typography variant="caption" color="text.secondary">{student.username}</Typography>}
                >
                  <Button
                    fullWidth
                    sx={{ justifyContent: 'flex-start', p: 1, color: 'text.primary', textTransform: 'none' }}
                    onClick={() => handleToggleStudent(student.id)}
                  >
                    <Checkbox
                      edge="start"
                      checked={selectedStudentIds.includes(student.id)}
                      tabIndex={-1}
                      disableRipple
                      inputProps={{ 'aria-labelledby': labelId }}
                    />
                    <ListItemText id={labelId} primary={student.full_name} />
                  </Button>
                </ListItem>
              );
            })}
            {students.length === 0 && <ListItem><ListItemText primary="No students found." /></ListItem>}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAssign(false)} disabled={assigning}>Cancel</Button>
          <Button variant="contained" onClick={handleAssignSubmit} disabled={assigning || selectedStudentIds.length === 0}>
            {assigning ? 'Assigning...' : `Assign ${selectedStudentIds.length} Students`}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ExamManagementPage;
