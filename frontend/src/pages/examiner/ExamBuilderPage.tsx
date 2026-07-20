import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Button, Stepper, Step, StepLabel,
  TextField, Stack, Alert, CircularProgress, FormControlLabel, Switch, Divider, Grid,
  List, ListItem, ListItemText, Checkbox, IconButton
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';

const steps = [
  'Basic Information',
  'Schedule',
  'Monitoring Rules',
  'Students',
  'Review & Publish'
];

const ExamBuilderPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const examId = searchParams.get('id');

  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Draft State
  const [exam, setExam] = useState<any>({
    title: '',
    description: '',
    subject: '',
    semester: '',
    passing_marks: 50,
    total_marks: 100,
    scheduled_start: '',
    scheduled_end: '',
    duration_minutes: 120,
    timezone: 'UTC',
    question_paper_id: '',
    monitoring_config: {
      camera_required: true,
      microphone_required: true,
      fullscreen_required: true
    },
    browser_rules: {
      disable_copy_paste: true,
      disable_right_click: true
    }
  });

  const [availableStudents, setAvailableStudents] = useState<any[]>([]);
  const [selectedStudentIds, setSelectedStudentIds] = useState<number[]>([]);
  const [questionPapers, setQuestionPapers] = useState<any[]>([]);

  useEffect(() => {
    if (examId) {
      fetchExam(parseInt(examId));
    }
    fetchQuestionPapers();
  }, [examId]);

  useEffect(() => {
    if (activeStep === 3) {
      fetchRepositoryStudents();
    }
  }, [activeStep]);

  const fetchQuestionPapers = async () => {
    try {
      const res = await apiClient.get('/question-papers');
      setQuestionPapers(res.data);
    } catch (err: any) {
      console.error(getErrorMessage(err));
    }
  };

  const fetchExam = async (id: number) => {
    setLoading(true);
    try {
      const res = await apiClient.get(`/workspace/exams/${id}`);
      setExam({
        ...res.data,
        question_paper_id: res.data.question_paper_id || ''
      });
      const studentsRes = await apiClient.get(`/workspace/exams/${id}/students`);
      setSelectedStudentIds(studentsRes.data);
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const fetchRepositoryStudents = async () => {
    try {
      const res = await apiClient.get('/workspace/students');
      setAvailableStudents(res.data.items || res.data); // Support paginated or list
    } catch (err: any) {
      setError(getErrorMessage(err));
    }
  };

  const handleNext = async () => {
    setError(null);
    if (activeStep === 0 && !exam.title) {
      setError("Title is required.");
      return;
    }

    if (activeStep === 0 && !examId) {
      // Create draft
      setSaving(true);
      try {
        const payload = { ...exam };
        if (!payload.question_paper_id) delete payload.question_paper_id;
        if (!payload.scheduled_start) payload.scheduled_start = null;
        if (!payload.scheduled_end) payload.scheduled_end = null;
        const res = await apiClient.post('/workspace/exams', payload);
        navigate(`/examiner/exams/build?id=${res.data.id}`, { replace: true });
      } catch (err) {
        setError(getErrorMessage(err));
        setSaving(false);
        return;
      }
      setSaving(false);
    } else if (examId) {
      // Update draft
      setSaving(true);
      try {
        if (activeStep === 3) {
          // Assign students
          await apiClient.post(`/workspace/exams/${examId}/students`, { student_ids: selectedStudentIds });
        } else {
          // Update details
          const payload = { ...exam };
          if (!payload.question_paper_id) delete payload.question_paper_id;
          if (!payload.scheduled_start) payload.scheduled_start = null;
          if (!payload.scheduled_end) payload.scheduled_end = null;
          await apiClient.put(`/workspace/exams/${examId}`, payload);
        }
      } catch (err) {
        setError(getErrorMessage(err));
        setSaving(false);
        return;
      }
      setSaving(false);
    }

    if (activeStep === steps.length - 1) {
      handlePublish();
    } else {
      setActiveStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  const handlePublish = async () => {
    if (!examId) return;
    setSaving(true);
    try {
      await apiClient.post(`/workspace/exams/${examId}/publish`);
      navigate('/examiner/exams');
    } catch (err) {
      setError(getErrorMessage(err));
      setSaving(false);
    }
  };

  const handleToggleStudent = (id: number) => {
    setSelectedStudentIds(prev => prev.includes(id) ? prev.filter(sId => sId !== id) : [...prev, id]);
  };

  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 5 }}><CircularProgress /></Box>;
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 4, gap: 2 }}>
        <IconButton onClick={() => navigate('/examiner/exams')}>
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" fontWeight={600}>
          {examId ? 'Edit Exam Draft' : 'Create New Exam'}
        </Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Card elevation={1}>
        <CardContent sx={{ p: 4 }}>
          <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 5 }}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          <Box sx={{ minHeight: 300, py: 2 }}>
            {activeStep === 0 && (
              <Stack spacing={3} maxWidth="md" mx="auto">
                <TextField label="Exam Title *" value={exam.title} onChange={e => setExam({ ...exam, title: e.target.value })} fullWidth />
                <TextField label="Description" multiline rows={3} value={exam.description} onChange={e => setExam({ ...exam, description: e.target.value })} fullWidth />
                <Grid container spacing={2}>
                  <Grid item xs={6}><TextField label="Subject" value={exam.subject} onChange={e => setExam({ ...exam, subject: e.target.value })} fullWidth /></Grid>
                  <Grid item xs={6}><TextField label="Semester" type="number" value={exam.semester} onChange={e => setExam({ ...exam, semester: parseInt(e.target.value) || '' })} fullWidth /></Grid>
                </Grid>
                <Grid container spacing={2}>
                  <Grid item xs={6}><TextField label="Total Marks" type="number" value={exam.total_marks} onChange={e => setExam({ ...exam, total_marks: parseInt(e.target.value) || 0 })} fullWidth /></Grid>
                  <Grid item xs={6}><TextField label="Passing Marks" type="number" value={exam.passing_marks} onChange={e => setExam({ ...exam, passing_marks: parseInt(e.target.value) || 0 })} fullWidth /></Grid>
                </Grid>
                
                <Typography variant="h6" sx={{ mt: 2 }}>Assessment Selection</Typography>
                <Divider />
                <TextField 
                  select 
                  SelectProps={{ native: true }}
                  label="Select Question Paper" 
                  value={exam.question_paper_id} 
                  onChange={e => setExam({ ...exam, question_paper_id: parseInt(e.target.value) || '' })} 
                  fullWidth
                >
                  <option value=""></option>
                  {questionPapers.filter(qp => qp.status === 'READY' || qp.status === 'LOCKED').map(qp => (
                    <option key={qp.id} value={qp.id}>{qp.title} (v{qp.revision})</option>
                  ))}
                </TextField>
                <Typography variant="caption" color="text.secondary">Only READY or LOCKED assessments appear here.</Typography>
              </Stack>
            )}

            {activeStep === 1 && (
              <Stack spacing={3} maxWidth="md" mx="auto">
                <Alert severity="info">All times are based on the server timezone: {exam.timezone}</Alert>
                <TextField label="Scheduled Start Time" type="datetime-local" InputLabelProps={{ shrink: true }} value={exam.scheduled_start ? new Date(exam.scheduled_start).toISOString().slice(0, 16) : ''} onChange={e => setExam({ ...exam, scheduled_start: e.target.value ? new Date(e.target.value).toISOString() : null })} fullWidth />
                <TextField label="Scheduled End Time" type="datetime-local" InputLabelProps={{ shrink: true }} value={exam.scheduled_end ? new Date(exam.scheduled_end).toISOString().slice(0, 16) : ''} onChange={e => setExam({ ...exam, scheduled_end: e.target.value ? new Date(e.target.value).toISOString() : null })} fullWidth />
                <TextField label="Duration (Minutes)" type="number" value={exam.duration_minutes} onChange={e => setExam({ ...exam, duration_minutes: parseInt(e.target.value) || 120 })} fullWidth />
              </Stack>
            )}

            {activeStep === 2 && (
              <Stack spacing={3} maxWidth="md" mx="auto">
                <Typography variant="h6">AI Monitoring Configuration</Typography>
                <Divider />
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <FormControlLabel control={<Switch checked={exam.monitoring_config.camera_required} onChange={e => setExam({ ...exam, monitoring_config: { ...exam.monitoring_config, camera_required: e.target.checked } })} />} label="Require Camera" />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControlLabel control={<Switch checked={exam.monitoring_config.microphone_required} onChange={e => setExam({ ...exam, monitoring_config: { ...exam.monitoring_config, microphone_required: e.target.checked } })} />} label="Require Microphone" />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControlLabel control={<Switch checked={exam.monitoring_config.fullscreen_required} onChange={e => setExam({ ...exam, monitoring_config: { ...exam.monitoring_config, fullscreen_required: e.target.checked } })} />} label="Enforce Fullscreen" />
                  </Grid>
                </Grid>

                <Typography variant="h6" sx={{ mt: 3 }}>Browser Rules</Typography>
                <Divider />
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <FormControlLabel control={<Switch checked={exam.browser_rules.disable_copy_paste} onChange={e => setExam({ ...exam, browser_rules: { ...exam.browser_rules, disable_copy_paste: e.target.checked } })} />} label="Disable Copy/Paste" />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControlLabel control={<Switch checked={exam.browser_rules.disable_right_click} onChange={e => setExam({ ...exam, browser_rules: { ...exam.browser_rules, disable_right_click: e.target.checked } })} />} label="Disable Right Click" />
                  </Grid>
                </Grid>
              </Stack>
            )}

            {activeStep === 3 && (
              <Stack spacing={3} maxWidth="md" mx="auto">
                <Typography variant="h6">Assign Students from Repository</Typography>
                <Typography variant="body2" color="text.secondary">Select the students that will be permitted to take this exam.</Typography>
                <List sx={{ width: '100%', bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 1, maxHeight: 400, overflow: 'auto' }}>
                  {availableStudents.map((student) => {
                    const labelId = `checkbox-list-label-${student.id}`;
                    return (
                      <ListItem key={student.id} disablePadding>
                        <Button fullWidth sx={{ justifyContent: 'flex-start', p: 1, color: 'text.primary', textTransform: 'none' }} onClick={() => handleToggleStudent(student.id)}>
                          <Checkbox edge="start" checked={selectedStudentIds.includes(student.id)} tabIndex={-1} disableRipple inputProps={{ 'aria-labelledby': labelId }} />
                          <ListItemText id={labelId} primary={`${student.first_name} ${student.last_name}`} secondary={student.registration_number} />
                        </Button>
                      </ListItem>
                    );
                  })}
                  {availableStudents.length === 0 && <ListItem><ListItemText primary="No students found in your repository." /></ListItem>}
                </List>
              </Stack>
            )}

            {activeStep === 4 && (
              <Stack spacing={3} maxWidth="md" mx="auto">
                <Typography variant="h6">Review & Publish</Typography>
                <Divider />
                <Typography variant="body1"><strong>Title:</strong> {exam.title}</Typography>
                <Typography variant="body1"><strong>Duration:</strong> {exam.duration_minutes} minutes</Typography>
                <Typography variant="body1"><strong>Students Assigned:</strong> {selectedStudentIds.length}</Typography>
                <Alert severity="warning">Publishing this exam will change its status from DRAFT to READY. Make sure you have uploaded a Question Paper (Skipped in this UI demo).</Alert>
              </Stack>
            )}
          </Box>

          <Box sx={{ display: 'flex', flexDirection: 'row', pt: 2 }}>
            <Button color="inherit" disabled={activeStep === 0 || saving} onClick={handleBack} sx={{ mr: 1 }}>Back</Button>
            <Box sx={{ flex: '1 1 auto' }} />
            <Button variant="contained" onClick={handleNext} disabled={saving}>
              {saving ? <CircularProgress size={24} color="inherit" /> : activeStep === steps.length - 1 ? 'Publish' : 'Save & Next'}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ExamBuilderPage;
