import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Button, Stepper, Step, StepLabel,
  TextField, Stack, Alert, CircularProgress, FormControlLabel, Switch, Divider, Grid,
  List, ListItem, ListItemText, Checkbox, IconButton, Chip
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import VisibilityIcon from '@mui/icons-material/Visibility';
import QuestionPaperReviewModal from '../../components/examiner/QuestionPaperReviewModal';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';

const steps = [
  'Basic Information',
  'Schedule',
  'Monitoring Rules',
  'Students',
  'Review & Publish'
];

const toLocalISOString = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '';
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

const formatDurationHuman = (minutes: number): string => {
  if (minutes <= 0) return '0 minutes';
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hrs === 0) return `${mins} minute${mins === 1 ? '' : 's'}`;
  if (mins === 0) return `${hrs} hour${hrs === 1 ? '' : 's'}`;
  return `${hrs} hour${hrs === 1 ? '' : 's'} ${mins} minute${mins === 1 ? '' : 's'}`;
};

const getFormValidationErrors = (exam: any) => {
  const errors: Record<string, string> = {};

  if (!exam.title || !exam.title.trim()) {
    errors.title = "Exam Title cannot be empty or whitespace only.";
  }

  if (exam.semester !== undefined && exam.semester !== null && exam.semester !== '') {
    const semNum = Number(exam.semester);
    if (isNaN(semNum) || !Number.isInteger(semNum) || semNum < 1 || semNum > 12) {
      errors.semester = "Semester must be an integer between 1 and 12.";
    }
  }

  if (exam.total_marks === undefined || exam.total_marks === null || exam.total_marks === '') {
    errors.total_marks = "Total marks is required.";
  } else {
    const totNum = Number(exam.total_marks);
    if (isNaN(totNum) || !Number.isInteger(totNum) || totNum <= 0) {
      errors.total_marks = "Total marks must be a positive integer greater than 0.";
    }
  }

  if (exam.passing_marks === undefined || exam.passing_marks === null || exam.passing_marks === '') {
    errors.passing_marks = "Passing marks is required.";
  } else {
    const passNum = Number(exam.passing_marks);
    const totNum = Number(exam.total_marks);
    if (isNaN(passNum) || !Number.isInteger(passNum) || passNum < 0) {
      errors.passing_marks = "Passing marks must be a non-negative integer (>= 0).";
    } else if (!isNaN(totNum) && passNum > totNum) {
      errors.passing_marks = `Passing marks (${passNum}) cannot exceed Total marks (${totNum} pts).`;
    }
  }

  return errors;
};

const getScheduleValidationError = (startISO: string | null | undefined, endISO: string | null | undefined): string | null => {
  if (!startISO || !endISO) return null;
  const startDate = new Date(startISO);
  const endDate = new Date(endISO);
  const now = new Date();

  if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) return null;

  if (startDate.getTime() < now.getTime() - 60000) {
    return "Exam start time cannot be scheduled in the past.";
  }
  if (endDate.getTime() <= startDate.getTime()) {
    return "End time must be after the start time.";
  }
  const duration = Math.floor((endDate.getTime() - startDate.getTime()) / 60000);
  if (duration < 10) {
    return "Exam duration must be at least 10 minutes.";
  }
  if (duration > 300) {
    return "Exam duration cannot exceed 5 hours.";
  }
  return null;
};

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
  const [selectedPaperDetails, setSelectedPaperDetails] = useState<any>(null);
  const [reviewModalOpen, setReviewModalOpen] = useState(false);

  const fieldErrors = getFormValidationErrors(exam);

  useEffect(() => {
    if (examId) {
      fetchExam(parseInt(examId));
    }
    fetchQuestionPapers();
  }, [examId]);

  useEffect(() => {
    if (exam.question_paper_id) {
      fetchSelectedPaperDetails(exam.question_paper_id);
    } else {
      setSelectedPaperDetails(null);
    }
  }, [exam.question_paper_id]);

  useEffect(() => {
    if (activeStep === 3) {
      fetchRepositoryStudents();
    }
  }, [activeStep]);

  const fetchSelectedPaperDetails = async (paperId: number) => {
    try {
      const res = await apiClient.get(`/question-paper-builder/${paperId}/full`);
      setSelectedPaperDetails(res.data);
      if (res.data) {
        // Resiliently compute total marks from section rules
        let computedTotal = res.data.total_marks || 0;
        if (res.data.section_rules && res.data.section_rules.length > 0) {
          const rulesSum = res.data.section_rules.reduce((acc: number, sec: any) => {
            const secSum = sec.question_rules?.length
              ? sec.question_rules.reduce((qAcc: number, q: any) => qAcc + (Number(q.marks) || Number(q.calculated_marks) || 1), 0)
              : (sec.total_section_marks || sec.section_weight || 0);
            return acc + secSum;
          }, 0);
          if (rulesSum > 0) {
            computedTotal = rulesSum;
          }
        }

        const paperDuration = res.data.paper_academic_duration_minutes || (
          res.data.section_rules?.reduce((acc: number, sec: any) => acc + (sec.section_duration_minutes || 0), 0)
        ) || 50;

        setExam(prev => ({
          ...prev,
          total_marks: computedTotal,
          passing_marks: (prev.passing_marks && prev.passing_marks <= computedTotal) ? prev.passing_marks : Math.ceil(computedTotal * 0.4),
          title: prev.title || (res.data.title ? `${res.data.title} Examination` : ''),
          subject: prev.subject || res.data.course_name || '',
          duration_minutes: paperDuration
        }));
      }
    } catch (err: any) {
      console.warn("Could not fetch paper details", err);
    }
  };

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
    const errs = getFormValidationErrors(exam);
    if (activeStep === 0 && Object.keys(errs).length > 0) {
      setError(Object.values(errs)[0]);
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
                <Box>
                  <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1, color: '#0f172a' }}>
                    1. Select Question Paper *
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <TextField 
                      select 
                      SelectProps={{ native: true }}
                      InputLabelProps={{ shrink: true }}
                      label="Select Question Paper *" 
                      value={exam.question_paper_id} 
                      onChange={e => setExam({ ...exam, question_paper_id: parseInt(e.target.value) || '' })} 
                      fullWidth
                    >
                      <option value="">-- Choose an authored question paper --</option>
                      {questionPapers.filter(qp => qp.status === 'READY' || qp.status === 'LOCKED').map(qp => (
                        <option key={qp.id} value={qp.id}>{qp.title} (v{qp.revision})</option>
                      ))}
                    </TextField>
                    {exam.question_paper_id && (
                      <Button variant="outlined" startIcon={<VisibilityIcon />} onClick={() => setReviewModalOpen(true)} sx={{ minWidth: 160, py: 1.8 }}>
                        Preview Paper
                      </Button>
                    )}
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    Select a ready question paper first. Total marks, duration, and structure are automatically fetched.
                  </Typography>
                </Box>

                {selectedPaperDetails && (
                  <Card variant="outlined" sx={{ p: 2, bgcolor: '#f8fafc', borderColor: '#cbd5e1' }}>
                    <Typography variant="subtitle2" fontWeight={700} color="primary.main" gutterBottom>
                      Selected Paper Metrics
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary">Total Marks</Typography>
                        <Typography variant="body2" fontWeight={700}>
                          {selectedPaperDetails.section_rules?.length
                            ? selectedPaperDetails.section_rules.reduce((acc: number, sec: any) => {
                                const secSum = sec.question_rules?.length
                                  ? sec.question_rules.reduce((qAcc: number, q: any) => qAcc + (Number(q.marks) || Number(q.calculated_marks) || 1), 0)
                                  : (sec.total_section_marks || sec.section_weight || 0);
                                return acc + secSum;
                              }, 0)
                            : (selectedPaperDetails.total_marks || 0)} pts
                        </Typography>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary">Academic Duration</Typography>
                        <Typography variant="body2" fontWeight={700}>{selectedPaperDetails.paper_academic_duration_minutes || 50} mins</Typography>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary">Sections</Typography>
                        <Typography variant="body2" fontWeight={700}>{selectedPaperDetails.section_rules?.length || 0}</Typography>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary">Total Questions</Typography>
                        <Typography variant="body2" fontWeight={700}>{selectedPaperDetails.total_questions || 0}</Typography>
                      </Grid>
                    </Grid>
                  </Card>
                )}

                <Divider sx={{ my: 1 }} />
                <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#0f172a' }}>
                  2. Exam Details & Passing Criteria
                </Typography>

                <TextField
                  label="Exam Title *"
                  value={exam.title}
                  onChange={e => setExam({ ...exam, title: e.target.value })}
                  error={Boolean(fieldErrors.title)}
                  helperText={fieldErrors.title}
                  fullWidth
                />
                <TextField
                  label="Description"
                  multiline
                  rows={3}
                  value={exam.description}
                  onChange={e => setExam({ ...exam, description: e.target.value })}
                  fullWidth
                />
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <TextField
                      label="Subject"
                      placeholder="e.g. CS-301 or Data Structures"
                      helperText="Alphanumeric subject name or course code (e.g. CS-301)"
                      value={exam.subject || ''}
                      onChange={e => setExam({ ...exam, subject: e.target.value })}
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <TextField
                      label="Semester"
                      type="number"
                      value={exam.semester ?? ''}
                      onChange={e => {
                        const clean = e.target.value.replace(/[^0-9]/g, '');
                        setExam({ ...exam, semester: clean === '' ? '' : parseInt(clean, 10) });
                      }}
                      onKeyDown={e => {
                        if (['e', 'E', '+', '-', '.'].includes(e.key)) {
                          e.preventDefault();
                        }
                      }}
                      error={Boolean(fieldErrors.semester)}
                      helperText={fieldErrors.semester || "Allowed values: 1 - 12"}
                      inputProps={{ min: 1, max: 12 }}
                      fullWidth
                    />
                  </Grid>
                </Grid>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <TextField
                      label="Total Marks *"
                      type="number"
                      value={exam.total_marks}
                      disabled={Boolean(exam.question_paper_id)}
                      onChange={e => setExam({ ...exam, total_marks: e.target.value === '' ? '' : parseInt(e.target.value) })}
                      error={Boolean(fieldErrors.total_marks)}
                      helperText={exam.question_paper_id ? `Auto-populated from Question Paper (${exam.total_marks} pts)` : fieldErrors.total_marks}
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <TextField
                      label="Passing Marks *"
                      type="number"
                      value={exam.passing_marks}
                      onChange={e => setExam({ ...exam, passing_marks: e.target.value === '' ? '' : parseInt(e.target.value) })}
                      error={Boolean(fieldErrors.passing_marks)}
                      helperText={fieldErrors.passing_marks || `Minimum marks required to pass (<= ${exam.total_marks || 0})`}
                      inputProps={{ min: 0, max: exam.total_marks || 100 }}
                      fullWidth
                    />
                  </Grid>
                </Grid>
              </Stack>
            )}

            {activeStep === 1 && (() => {
              const paperAcademicDuration = selectedPaperDetails?.paper_academic_duration_minutes || (
                selectedPaperDetails?.section_rules?.reduce((acc: number, sec: any) => acc + (sec.section_duration_minutes || 0), 0)
              ) || 50;
              const baseError = getScheduleValidationError(exam.scheduled_start, exam.scheduled_end);
              const calculatedDuration = (exam.scheduled_start && exam.scheduled_end)
                ? Math.floor((new Date(exam.scheduled_end).getTime() - new Date(exam.scheduled_start).getTime()) / 60000)
                : 0;

              let scheduleError = baseError;
              if (!scheduleError && calculatedDuration > 0 && calculatedDuration < paperAcademicDuration) {
                scheduleError = `Scheduled exam runtime (${calculatedDuration} mins) cannot be less than the required paper academic duration (${paperAcademicDuration} mins).`;
              }

              const handleStartChange = (isoStr: string | null) => {
                const newStart = isoStr;
                setExam({ ...exam, scheduled_start: newStart, duration_minutes: paperAcademicDuration });
              };

              const handleEndChange = (isoStr: string | null) => {
                const newEnd = isoStr;
                setExam({ ...exam, scheduled_end: newEnd, duration_minutes: paperAcademicDuration });
              };

              const setPresetDuration = (targetMinutes: number) => {
                if (!exam.scheduled_start) return;
                const startDt = new Date(exam.scheduled_start);
                const endDt = new Date(startDt.getTime() + targetMinutes * 60000);
                setExam({
                  ...exam,
                  scheduled_end: endDt.toISOString(),
                  duration_minutes: paperAcademicDuration
                });
              };

              return (
                <Stack spacing={3} maxWidth="md" mx="auto">
                  <Alert severity="info">All times are based on your local timezone and stored in UTC.</Alert>
                  {scheduleError && <Alert severity="error">{scheduleError}</Alert>}

                  {/* Intelligent Schedule Panel */}
                  <Card variant="outlined" sx={{ p: 2.5, bgcolor: '#f8fafc', borderColor: '#cbd5e1' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="subtitle1" fontWeight={700} color="primary.main">
                        Intelligent Schedule Panel
                      </Typography>
                      {calculatedDuration > 0 && (
                        <Chip
                          label={
                            calculatedDuration < paperAcademicDuration
                              ? 'Invalid Schedule (Too Short)'
                              : calculatedDuration >= paperAcademicDuration + 10
                              ? 'Schedule Valid (With Buffer)'
                              : 'Recommended Adjustment (No Buffer)'
                          }
                          color={
                            calculatedDuration < paperAcademicDuration
                              ? 'error'
                              : calculatedDuration >= paperAcademicDuration + 10
                              ? 'success'
                              : 'warning'
                          }
                          size="small"
                          sx={{ fontWeight: 700 }}
                        />
                      )}
                    </Box>

                    <Grid container spacing={2} sx={{ mb: 2 }}>
                      <Grid item xs={4}>
                        <Typography variant="caption" color="text.secondary">Academic Paper Duration</Typography>
                        <Typography variant="body1" fontWeight={700}>{paperAcademicDuration} mins</Typography>
                      </Grid>
                      <Grid item xs={4}>
                        <Typography variant="caption" color="text.secondary">Recommended Buffer</Typography>
                        <Typography variant="body1" fontWeight={700}>10 mins</Typography>
                      </Grid>
                      <Grid item xs={4}>
                        <Typography variant="caption" color="text.secondary">Recommended Window</Typography>
                        <Typography variant="body1" fontWeight={700}>{paperAcademicDuration + 10} mins</Typography>
                      </Grid>
                    </Grid>

                    <Stack direction="row" spacing={1.5} flexWrap="wrap">
                      <Button size="small" variant="outlined" onClick={() => setPresetDuration(paperAcademicDuration)} disabled={!exam.scheduled_start}>
                        Use Paper Duration Only ({paperAcademicDuration}m)
                      </Button>
                      <Button size="small" variant="contained" color="primary" onClick={() => setPresetDuration(paperAcademicDuration + 10)} disabled={!exam.scheduled_start}>
                        Use Recommended Schedule ({paperAcademicDuration + 10}m)
                      </Button>
                    </Stack>
                  </Card>

                  <TextField 
                    label="Scheduled Start Time *" 
                    type="datetime-local" 
                    InputLabelProps={{ shrink: true }} 
                    value={toLocalISOString(exam.scheduled_start)} 
                    onChange={e => handleStartChange(e.target.value ? new Date(e.target.value).toISOString() : null)} 
                    fullWidth 
                  />
                  <TextField 
                    label="Scheduled End Time *" 
                    type="datetime-local" 
                    InputLabelProps={{ shrink: true }} 
                    value={toLocalISOString(exam.scheduled_end)} 
                    onChange={e => handleEndChange(e.target.value ? new Date(e.target.value).toISOString() : null)} 
                    fullWidth 
                  />
                  <TextField 
                    label="Scheduled Window (Calculated Automatically)" 
                    value={calculatedDuration > 0 ? formatDurationHuman(calculatedDuration) : 'Select start and end time'} 
                    disabled 
                    fullWidth 
                    helperText={`Scheduled window: ${calculatedDuration > 0 ? formatDurationHuman(calculatedDuration) : 'N/A'} (includes buffer). Actual paper duration: ${paperAcademicDuration} minutes.`}
                  />
                </Stack>
              );
            })()}

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
                    const displayName = student.full_name || student.name || `${student.first_name || ''} ${student.last_name || ''}`.trim() || `Student #${student.id}`;
                    const regNum = student.registration_number ? `(${student.registration_number})` : '';
                    return (
                      <ListItem key={student.id} disablePadding>
                        <Button fullWidth sx={{ justifyContent: 'flex-start', p: 1, color: 'text.primary', textTransform: 'none' }} onClick={() => handleToggleStudent(student.id)}>
                          <Checkbox edge="start" checked={selectedStudentIds.includes(student.id)} tabIndex={-1} disableRipple inputProps={{ 'aria-labelledby': labelId }} />
                          <ListItemText id={labelId} primary={`${displayName} ${regNum}`.trim()} />
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
                <Typography variant="h6" fontWeight={700}>Review & Publish</Typography>
                <Divider />
                <Card variant="outlined" sx={{ p: 2.5, bgcolor: '#f8fafc', borderColor: '#cbd5e1' }}>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" color="text.secondary">Exam Title</Typography>
                      <Typography variant="body1" fontWeight={700}>{exam.title}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" color="text.secondary">Course / Subject</Typography>
                      <Typography variant="body1" fontWeight={700}>{exam.subject || selectedPaperDetails?.course_name || 'N/A'}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" color="text.secondary">Question Paper</Typography>
                      <Typography variant="body1" fontWeight={600}>{selectedPaperDetails?.title || 'Selected Paper'}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" color="text.secondary">Duration</Typography>
                      <Typography variant="body1" fontWeight={600}>{exam.duration_minutes} minutes</Typography>
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="caption" color="text.secondary">Total Marks</Typography>
                      <Typography variant="body1" fontWeight={700} color="primary.main">{exam.total_marks || 0} pts</Typography>
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="caption" color="text.secondary">Passing Marks</Typography>
                      <Typography variant="body1" fontWeight={700} color="success.dark">{exam.passing_marks || 0} pts</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" color="text.secondary">Enrolled Students</Typography>
                      <Typography variant="body1" fontWeight={700}>{selectedStudentIds.length} Students Assigned</Typography>
                    </Grid>
                  </Grid>
                </Card>
                <Alert severity="info" sx={{ borderRadius: 2 }}>
                  Publishing this exam will finalize its configuration and change its status from <strong>DRAFT</strong> to <strong>READY</strong> for candidates.
                </Alert>
              </Stack>
            )}
          </Box>

          <Box sx={{ display: 'flex', flexDirection: 'row', pt: 2 }}>
            <Button color="inherit" disabled={activeStep === 0 || saving} onClick={handleBack} sx={{ mr: 1 }}>Back</Button>
            <Box sx={{ flex: '1 1 auto' }} />
            {(() => {
              const isStep0Invalid = activeStep === 0 && (!exam.title || !exam.question_paper_id || Object.keys(fieldErrors).length > 0);
              const isScheduleInvalid = activeStep === 1 && (!exam.scheduled_start || !exam.scheduled_end || getScheduleValidationError(exam.scheduled_start, exam.scheduled_end) !== null);
              return (
                <Button variant="contained" onClick={handleNext} disabled={saving || isStep0Invalid || isScheduleInvalid}>
                  {saving ? <CircularProgress size={24} color="inherit" /> : activeStep === steps.length - 1 ? 'Publish' : 'Save & Next'}
                </Button>
              );
            })()}
          </Box>
        </CardContent>
      </Card>

      {/* Read-Only Paper Review Modal */}
      <QuestionPaperReviewModal
        paperId={exam.question_paper_id ? parseInt(exam.question_paper_id) : null}
        open={reviewModalOpen}
        onClose={() => setReviewModalOpen(false)}
      />
    </Box>
  );
};

export default ExamBuilderPage;
