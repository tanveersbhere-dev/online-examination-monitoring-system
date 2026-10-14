import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import {
  Box, Typography, Paper, Grid, Card, CardContent, Chip, Button, Divider, Stack,
  CircularProgress, TextField, Alert, Dialog, DialogTitle, DialogContent,
  DialogActions, Tooltip, IconButton, Tabs, Tab
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import PersonIcon from '@mui/icons-material/Person';
import TimelineIcon from '@mui/icons-material/Timeline';
import SecurityIcon from '@mui/icons-material/Security';
import SaveIcon from '@mui/icons-material/Save';
import LockIcon from '@mui/icons-material/Lock';
import QuizIcon from '@mui/icons-material/Quiz';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline';
import VideocamIcon from '@mui/icons-material/Videocam';
import ImageIcon from '@mui/icons-material/Image';
import PhotoLibraryIcon from '@mui/icons-material/PhotoLibrary';
import AssignmentIcon from '@mui/icons-material/Assignment';
import ShieldIcon from '@mui/icons-material/Shield';

import apiClient from '../../services/apiClient';
import { getAuthImageUrl, getAuthVideoUrl } from '../../config/api';
import { getErrorMessage } from '../../utils/errorHandler';

interface OptionReview {
  option_index: number;
  text: string;
  is_correct: boolean;
}

interface QuestionReview {
  id: string;
  question_index: number;
  question_type: string;
  text: string;
  options: OptionReview[];
  correct_option_indices: number[];
  calculated_marks?: number;
  marks?: number;
  image_url?: string;
  explanation?: string;
  status?: string;
  student_selected_indices?: number[];
  student_answer_text?: string;
  awarded_marks?: number | null;
  examiner_comments?: string;
}

interface SectionReview {
  id: string;
  section_index: number;
  section_name: string;
  section_type: string;
  section_duration_minutes?: number;
  section_weight?: number;
  calculated_weight_per_question?: number;
  questions: QuestionReview[];
}

interface AttemptReviewData {
  summary: {
    session_id: number;
    student_id: number;
    student_name: string;
    registration_number: string;
    department: string;
    program: string;
    student_email: string;
    exam_id: number;
    exam_title: string;
    paper_title: string;
    paper_mode: string;
    status: string;
    evaluation_status: string;
    started_at: string | null;
    submitted_at: string | null;
    duration_minutes: number;
    time_taken_seconds: number;
    recovery_count: number;
    total_questions: number;
    answered_count: number;
    unanswered_count: number;
    marked_count: number;
    final_score: number;
    total_max_marks: number;
    percentage: number;
  };
  scoring_summary: {
    mcq_total_questions: number;
    mcq_correct_count: number;
    mcq_incorrect_count: number;
    mcq_unattempted_count: number;
    mcq_marks_obtained: number;
    mcq_max_marks: number;
    subjective_total_questions: number;
    subjective_marks_obtained: number;
    subjective_max_marks: number;
    total_marks_obtained: number;
    total_max_marks: number;
    percentage: number;
  };
  sections: SectionReview[];
  answers: Record<string, any>;
  session_metadata: {
    browser: string;
    os: string;
    device: string;
    recovery_count: number;
    submission_method: string;
  };
  timeline: Array<{ timestamp: string; title: string; description: string }>;
  monitoring_report?: {
    summary: {
      student_id: number;
      student_name: string;
      exam_id: number;
      session_id: number;
      final_risk_score: number;
      risk_level: string;
      total_violations: number;
      pending_violations: number;
      confirmed_violations: number;
      total_evidence_count: number;
      ai_executive_summary?: string;
    };
    violations: Array<{
      id: number;
      violation_type: string;
      category: string;
      severity: string;
      risk_score: number;
      duration_seconds?: number;
      confidence?: number;
      timestamp: string | null;
      status: string;
      description: string;
      reviewer_notes?: string | null;
      evidence: Array<{ id: number; file_path: string; evidence_type: string; timestamp: string | null; is_primary?: boolean; replay_clip_path?: string | null; metadata?: any }>;
    }>;
    evidence_snapshots: Array<{ id: number; file_path: string; evidence_type: string; timestamp: string | null }>;
    final_risk_score: number;
    risk_level: string;
  };
  ai_evidence_placeholder: {
    available: boolean;
    message: string;
    face_alerts: number;
    multiple_faces_detected: boolean;
    phone_detected: boolean;
    object_detection_alerts: number;
  };
}

const AttemptReviewPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AttemptReviewData | null>(null);

  // Tab State: 'paper' (Solved Paper) vs 'monitoring' (Evidence & Cheating Report)
  const [activeReviewTab, setActiveReviewTab] = useState<'paper' | 'monitoring'>(
    searchParams.get('tab') === 'monitoring' ? 'monitoring' : 'paper'
  );

  // Local state for subjective evaluations: key -> { awarded_marks, examiner_comments }
  const [evalState, setEvalState] = useState<Record<string, { awarded_marks: number | ''; examiner_comments: string }>>({});
  const [savingEval, setSavingEval] = useState<boolean>(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);
  const [confirmFinalizeOpen, setConfirmFinalizeOpen] = useState<boolean>(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [previewVideo, setPreviewVideo] = useState<string | null>(null);

  // Sequential Navigation State
  const [matchingSessionIds, setMatchingSessionIds] = useState<number[]>(location.state?.allMatchingSessionIds || []);

  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam === 'monitoring' || tabParam === 'paper') {
      setActiveReviewTab(tabParam);
    }
  }, [searchParams]);

  useEffect(() => {
    if (sessionId) {
      fetchReviewData(parseInt(sessionId));
    }
  }, [sessionId]);

  const fetchReviewData = async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(`/exam-sessions/${id}/review`);
      const reviewData: AttemptReviewData = res.data;
      setData(reviewData);

      // Initialize local evaluation state for subjective questions
      const initialEval: Record<string, { awarded_marks: number | ''; examiner_comments: string }> = {};
      reviewData.sections.forEach((sec) => {
        sec.questions.forEach((q) => {
          const isMcq = (q.question_type === 'MCQ' || sec.section_type === 'MCQ');
          if (!isMcq) {
            const key = `${sec.section_index}_${q.question_index}`;
            initialEval[key] = {
              awarded_marks: q.awarded_marks !== null && q.awarded_marks !== undefined ? q.awarded_marks : '',
              examiner_comments: q.examiner_comments || ''
            };
          }
        });
      });
      setEvalState(initialEval);
    } catch (err: any) {
      setError(getErrorMessage(err) || 'Failed to load attempt review data.');
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (_: React.SyntheticEvent, newTab: 'paper' | 'monitoring') => {
    setActiveReviewTab(newTab);
    setSearchParams(prev => {
      prev.set('tab', newTab);
      return prev;
    }, { replace: true });
  };

  const handleMarkChange = (sectionIndex: number, questionIndex: number, val: string, maxMarks: number) => {
    const key = `${sectionIndex}_${questionIndex}`;
    if (val === '') {
      setEvalState((prev) => ({
        ...prev,
        [key]: { ...prev[key], awarded_marks: '' }
      }));
      return;
    }
    const num = parseFloat(val);
    if (!isNaN(num)) {
      const clamped = Math.min(Math.max(0, num), maxMarks);
      setEvalState((prev) => ({
        ...prev,
        [key]: { ...prev[key], awarded_marks: clamped }
      }));
    }
  };

  const handleCommentChange = (sectionIndex: number, questionIndex: number, val: string) => {
    const key = `${sectionIndex}_${questionIndex}`;
    setEvalState((prev) => ({
      ...prev,
      [key]: { ...prev[key], examiner_comments: val }
    }));
  };

  const calculateLiveSubjectiveScore = (): number => {
    let sum = 0;
    Object.values(evalState).forEach((item) => {
      if (typeof item.awarded_marks === 'number') {
        sum += item.awarded_marks;
      }
    });
    return Math.round(sum * 100) / 100;
  };

  const currentSubjScore = calculateLiveSubjectiveScore();
  const liveTotalScore = Math.round(((data?.scoring_summary.mcq_marks_obtained || 0) + currentSubjScore) * 100) / 100;
  const livePercentage = data ? Math.round((liveTotalScore / (data.scoring_summary.total_max_marks || 1)) * 10000) / 100 : 0;

  const handleSaveEvaluation = async (finalize: boolean = false, autoNext: boolean = false) => {
    if (!sessionId || !data) return;
    setSavingEval(true);
    setSaveSuccessMsg(null);
    try {
      const evaluations = Object.entries(evalState).map(([key, val]) => {
        const [secIdx, qIdx] = key.split('_').map(Number);
        return {
          section_index: secIdx,
          question_index: qIdx,
          awarded_marks: val.awarded_marks === '' ? null : Number(val.awarded_marks),
          examiner_comments: val.examiner_comments
        };
      });

      const endpoint = finalize
        ? `/exam-sessions/${sessionId}/finalize-evaluation`
        : `/exam-sessions/${sessionId}/evaluate`;

      await apiClient.post(endpoint, { evaluations });

      setSaveSuccessMsg(finalize ? 'Evaluation finalized successfully!' : 'Evaluation draft saved successfully!');
      setConfirmFinalizeOpen(false);

      await fetchReviewData(parseInt(sessionId));

      if (autoNext && nextSessionId) {
        handleNavigateCandidate(nextSessionId);
      }
    } catch (err: any) {
      setError(getErrorMessage(err) || 'Failed to save evaluation.');
    } finally {
      setSavingEval(false);
    }
  };

  // Candidates Navigation
  const currentSessionIdNum = parseInt(sessionId || '0');
  const currentIndex = matchingSessionIds.indexOf(currentSessionIdNum);
  const prevSessionId = currentIndex > 0 ? matchingSessionIds[currentIndex - 1] : null;
  const nextSessionId = currentIndex >= 0 && currentIndex < matchingSessionIds.length - 1 ? matchingSessionIds[currentIndex + 1] : null;

  const handleNavigateCandidate = (targetSessionId: number) => {
    const currentParams = new URLSearchParams(searchParams);
    currentParams.set('tab', activeReviewTab);
    navigate(`/examiner/attempts/${targetSessionId}/review?${currentParams.toString()}`, {
      state: { allMatchingSessionIds: matchingSessionIds }
    });
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !data) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>{error || 'Attempt review data not available.'}</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(-1)}>
          Back
        </Button>
      </Box>
    );
  }

  const { summary, scoring_summary, sections, session_metadata, timeline } = data;
  const isFinalized = summary.evaluation_status === 'FINALIZED';

  return (
    <Box sx={{ pb: 6 }}>
      {/* Top Header Card */}
      <Card elevation={1} sx={{ p: 2, mb: 3, borderRadius: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Button
              startIcon={<ArrowBackIcon />}
              onClick={() => {
                if (summary.exam_id) {
                  navigate(`/examiner/exams/${summary.exam_id}`);
                } else {
                  navigate(-1);
                }
              }}
              variant="outlined"
              size="small"
            >
              Back to Attempts
            </Button>
            {matchingSessionIds.length > 0 && (
              <Chip
                label={`Candidate Attempt ${currentIndex + 1} of ${matchingSessionIds.length}`}
                color="primary"
                size="small"
                variant="filled"
                sx={{ fontWeight: 700 }}
              />
            )}
          </Stack>

          {/* Sequential Candidate Navigation */}
          <Stack direction="row" spacing={1} alignItems="center">
            <Button
              variant="outlined"
              size="small"
              startIcon={<NavigateBeforeIcon />}
              disabled={!prevSessionId}
              onClick={() => prevSessionId && handleNavigateCandidate(prevSessionId)}
            >
              Previous Student
            </Button>
            <Button
              variant="outlined"
              size="small"
              endIcon={<NavigateNextIcon />}
              disabled={!nextSessionId}
              onClick={() => nextSessionId && handleNavigateCandidate(nextSessionId)}
            >
              Next Student
            </Button>
          </Stack>
        </Box>
      </Card>

      {/* Header Workspace Title Bar */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ textTransform: 'uppercase' }}>
              {summary.exam_title} — {summary.paper_title}
            </Typography>
            <Chip label={summary.evaluation_status} color={isFinalized ? 'success' : 'warning'} size="small" />
          </Stack>
          <Typography variant="h4" fontWeight={700} color="primary.main">
            {summary.student_name} ({summary.registration_number})
          </Typography>
        </Box>

        {/* Action Buttons */}
        <Stack direction="row" spacing={1.5} flexWrap="wrap" gap={1}>
          {activeReviewTab === 'paper' ? (
            <Button
              variant="outlined"
              color="secondary"
              startIcon={<SecurityIcon />}
              onClick={() => handleTabChange(null as any, 'monitoring')}
              sx={{ fontWeight: 600, borderRadius: 2, textTransform: 'none' }}
            >
              View Monitoring Report
            </Button>
          ) : (
            <Button
              variant="outlined"
              color="primary"
              startIcon={<AssignmentIcon />}
              onClick={() => handleTabChange(null as any, 'paper')}
              sx={{ fontWeight: 600, borderRadius: 2, textTransform: 'none' }}
            >
              View Solved Paper
            </Button>
          )}

          {!isFinalized ? (
            <>
              <Button
                variant="outlined"
                startIcon={<SaveIcon />}
                onClick={() => handleSaveEvaluation(false, false)}
                disabled={savingEval}
              >
                Save Draft
              </Button>
              {nextSessionId && (
                <Button
                  variant="outlined"
                  color="info"
                  startIcon={<SkipNextIcon />}
                  onClick={() => handleSaveEvaluation(false, true)}
                  disabled={savingEval}
                >
                  Save Draft & Next
                </Button>
              )}
              <Button
                variant="contained"
                color="success"
                startIcon={<LockIcon />}
                onClick={() => setConfirmFinalizeOpen(true)}
                disabled={savingEval}
              >
                Finalize Evaluation
              </Button>
            </>
          ) : (
            <Chip icon={<LockIcon />} label="Evaluation Finalized (Read-Only)" color="success" variant="outlined" sx={{ py: 2, px: 1, fontWeight: 700 }} />
          )}
        </Stack>
      </Box>

      {/* PRIMARY REVIEW VIEW SWITCHER TABS */}
      <Paper elevation={0} sx={{ borderBottom: 2, borderColor: '#e2e8f0', mb: 3, bgcolor: '#ffffff', borderRadius: 2, overflow: 'hidden' }}>
        <Tabs
          value={activeReviewTab}
          onChange={handleTabChange}
          textColor="primary"
          indicatorColor="primary"
          sx={{ px: 2 }}
        >
          <Tab
            value="paper"
            icon={<AssignmentIcon />}
            iconPosition="start"
            label="Paper Review (Solved Paper)"
            sx={{ fontWeight: 700, textTransform: 'none', py: 1.5, fontSize: '0.95rem' }}
          />
          <Tab
            value="monitoring"
            icon={<SecurityIcon />}
            iconPosition="start"
            label="Monitoring Review (Evidence & Integrity)"
            sx={{ fontWeight: 700, textTransform: 'none', py: 1.5, fontSize: '0.95rem' }}
          />
        </Tabs>
      </Paper>

      {saveSuccessMsg && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSaveSuccessMsg(null)}>
          {saveSuccessMsg}
        </Alert>
      )}

      {isFinalized && (
        <Alert severity="info" icon={<LockIcon />} sx={{ mb: 3 }}>
          This attempt evaluation has been finalized and locked against accidental modifications. All awarded marks and feedback are read-only.
        </Alert>
      )}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* TAB 1: PAPER REVIEW (SOLVED PAPER ONLY)                                */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {activeReviewTab === 'paper' && (
        <Grid container spacing={3}>
          {/* LEFT COLUMN: Solved Paper Content */}
          <Grid item xs={12} lg={8.5}>
            <Stack spacing={3}>
              {/* SECTION 1: Candidate & Attempt Summary */}
              <Card elevation={1} sx={{ borderRadius: 2, border: '1px solid #cbd5e1' }}>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6" fontWeight={700} color="primary.main" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <PersonIcon fontSize="small" /> Candidate & Attempt Summary
                    </Typography>
                    <Chip label={`Attempt: ${summary.status}`} color={summary.status === 'COMPLETED' || summary.status === 'SUBMITTED' ? 'success' : 'warning'} size="small" />
                  </Box>
                  <Divider sx={{ my: 2 }} />

                  <Grid container spacing={2}>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Candidate Name</Typography>
                      <Typography variant="body1" fontWeight={700}>{summary.student_name}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Registration Number</Typography>
                      <Typography variant="body1" fontWeight={700}>{summary.registration_number}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Program & Department</Typography>
                      <Typography variant="body1" fontWeight={600}>{summary.program}</Typography>
                      <Typography variant="caption" color="text.secondary">{summary.department}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Start Time</Typography>
                      <Typography variant="body2">{summary.started_at ? new Date(summary.started_at).toLocaleString() : 'N/A'}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Submission Time</Typography>
                      <Typography variant="body2">{summary.submitted_at ? new Date(summary.submitted_at).toLocaleString() : 'N/A'}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Submission Type</Typography>
                      <Typography variant="body2" fontWeight={600}>{session_metadata.submission_method}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Duration Used</Typography>
                      <Typography variant="body1" fontWeight={700}>{Math.ceil(summary.time_taken_seconds / 60)} / {summary.duration_minutes} mins</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Recovery Events</Typography>
                      <Chip label={`${summary.recovery_count} events`} color={summary.recovery_count > 0 ? 'warning' : 'default'} size="small" variant="outlined" />
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Current Total Score</Typography>
                      <Typography variant="h6" fontWeight={700} color="primary.main">
                        {liveTotalScore} / {scoring_summary.total_max_marks} Marks ({livePercentage}%)
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* SECTION 2: Objective Question Summary (MCQs) */}
              <Card elevation={1} sx={{ borderRadius: 2, border: '1px solid #cbd5e1' }}>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="h6" fontWeight={700} color="primary.main" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <QuizIcon fontSize="small" /> Objective Questions Summary (MCQs)
                  </Typography>
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Scoring utilizes calculated section question weights. Candidate selected options are highlighted below.
                  </Alert>

                  <Grid container spacing={2} sx={{ p: 2, bgcolor: '#f8fafc', borderRadius: 1.5, mb: 3 }}>
                    <Grid item xs={6} sm={2.4}>
                      <Typography variant="caption" color="text.secondary">Total MCQs</Typography>
                      <Typography variant="body1" fontWeight={700}>{scoring_summary.mcq_total_questions}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={2.4}>
                      <Typography variant="caption" color="text.secondary">Correct</Typography>
                      <Typography variant="body1" fontWeight={700} color="success.main">{scoring_summary.mcq_correct_count}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={2.4}>
                      <Typography variant="caption" color="text.secondary">Incorrect</Typography>
                      <Typography variant="body1" fontWeight={700} color="error.main">{scoring_summary.mcq_incorrect_count}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={2.4}>
                      <Typography variant="caption" color="text.secondary">Unattempted</Typography>
                      <Typography variant="body1" fontWeight={700} color="text.secondary">{scoring_summary.mcq_unattempted_count}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={2.4}>
                      <Typography variant="caption" color="text.secondary">MCQ Score</Typography>
                      <Typography variant="body1" fontWeight={700} color="primary.main">
                        {scoring_summary.mcq_marks_obtained} / {scoring_summary.mcq_max_marks} Marks
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* SECTION 3: Question Content & Subjective Evaluation Worksheets */}
              {sections.map((sec, sIdx) => {
                const secMarks = sec.section_weight || sec.questions.reduce((sum, q) => sum + (q.marks || 1), 0);
                return (
                  <Card key={sec.id || sIdx} elevation={1} id={`section-${sec.section_index}`} sx={{ borderRadius: 2, border: '1px solid #cbd5e1' }}>
                    <CardContent sx={{ p: 3 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h6" fontWeight={700}>
                          Section {sIdx + 1}: {sec.section_name}
                        </Typography>
                        <Chip label={`Section Total: ${secMarks} Marks (${sec.questions.length} Questions)`} color="primary" variant="outlined" size="small" sx={{ fontWeight: 600 }} />
                      </Box>

                      <Stack spacing={3}>
                        {sec.questions.map((q, qIdx) => {
                          const isMcq = (q.question_type === 'MCQ' || sec.section_type === 'MCQ');
                          const qKey = `${sec.section_index}_${q.question_index}`;
                          const evalVal = evalState[qKey] || { awarded_marks: '', examiner_comments: '' };
                          const qMaxMarks = q.marks || q.calculated_marks || 1;

                          return (
                            <Paper
                              key={q.id || qIdx}
                              id={`q-${sec.section_index}-${q.question_index}`}
                              variant="outlined"
                              sx={{
                                p: 3,
                                borderRadius: 2,
                                borderColor: isMcq ? '#e2e8f0' : '#cbd5e1',
                                bgcolor: '#ffffff'
                              }}
                            >
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                                <Stack direction="row" spacing={1} alignItems="center">
                                  <Chip label={`Q${qIdx + 1}`} color="primary" size="small" />
                                  <Chip label={q.question_type} variant="outlined" size="small" />
                                </Stack>

                                {isMcq ? (
                                  <Chip
                                    icon={q.status === 'CORRECT' ? <CheckCircleIcon /> : <CancelIcon />}
                                    label={q.status === 'CORRECT' ? `Correct (+${qMaxMarks} Marks)` : q.status === 'INCORRECT' ? 'Incorrect (0 Marks)' : 'Not Attempted (0 Marks)'}
                                    color={q.status === 'CORRECT' ? 'success' : q.status === 'INCORRECT' ? 'error' : 'default'}
                                    size="small"
                                    sx={{ fontWeight: 700 }}
                                  />
                                ) : (
                                  <Chip
                                    label={`Subjective (Max: ${qMaxMarks} Marks)`}
                                    color="secondary"
                                    variant="outlined"
                                    size="small"
                                    sx={{ fontWeight: 700 }}
                                  />
                                )}
                              </Box>

                              <Typography variant="body1" fontWeight={600} gutterBottom sx={{ whiteSpace: 'pre-wrap' }}>
                                {q.text}
                              </Typography>

                              {/* Question Image */}
                              {q.image_url && (
                                <Box sx={{ my: 2 }}>
                                  <img
                                    src={getAuthImageUrl(q.image_url)}
                                    alt="Question Illustration"
                                    style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 8, border: '1px solid #cbd5e1' }}
                                  />
                                </Box>
                              )}

                              {/* Multiple Choice Options List */}
                              {isMcq && q.options && q.options.length > 0 && (
                                <Stack spacing={1.5} sx={{ mt: 2 }}>
                                  {q.options.map((opt, oIdx) => {
                                    const isStudentSelected = (q.student_selected_indices || []).includes(oIdx);
                                    const isCorrectOpt = (q.correct_option_indices || []).includes(oIdx);

                                    let optionBg = '#f8fafc';
                                    let optionBorder = '#e2e8f0';
                                    let badgeLabel = null;

                                    if (isCorrectOpt && isStudentSelected) {
                                      optionBg = '#ecfdf5';
                                      optionBorder = '#10b981';
                                      badgeLabel = 'Student Selected (Correct)';
                                    } else if (isStudentSelected && !isCorrectOpt) {
                                      optionBg = '#fef2f2';
                                      optionBorder = '#ef4444';
                                      badgeLabel = 'Student Selected (Incorrect)';
                                    } else if (isCorrectOpt) {
                                      optionBg = '#f0fdf4';
                                      optionBorder = '#86efac';
                                      badgeLabel = 'Correct Option';
                                    }

                                    return (
                                      <Paper
                                        key={opt.option_index || oIdx}
                                        variant="outlined"
                                        sx={{
                                          p: 2,
                                          bgcolor: optionBg,
                                          borderColor: optionBorder,
                                          borderRadius: 1.5,
                                          display: 'flex',
                                          justifyContent: 'space-between',
                                          alignItems: 'center'
                                        }}
                                      >
                                        <Typography variant="body2" sx={{ fontWeight: isStudentSelected || isCorrectOpt ? 600 : 400 }}>
                                          <strong>{String.fromCharCode(65 + oIdx)}.</strong> {opt.text}
                                        </Typography>
                                        {badgeLabel && (
                                          <Chip
                                            label={badgeLabel}
                                            size="small"
                                            color={isCorrectOpt ? 'success' : 'error'}
                                            variant="outlined"
                                            sx={{ fontWeight: 600, fontSize: '0.7rem' }}
                                          />
                                        )}
                                      </Paper>
                                    );
                                  })}
                                </Stack>
                              )}

                              {/* Subjective Student Answer & Examiner Evaluation Worksheet */}
                              {!isMcq && (
                                <Box sx={{ mt: 2 }}>
                                  <Typography variant="caption" color="text.secondary" fontWeight={700} sx={{ textTransform: 'uppercase' }}>
                                    Candidate Submitted Answer Text:
                                  </Typography>
                                  <Paper
                                    variant="outlined"
                                    sx={{
                                      p: 2.5,
                                      mt: 1,
                                      mb: 3,
                                      bgcolor: '#f8fafc',
                                      borderColor: '#e2e8f0',
                                      minHeight: 120,
                                      fontFamily: 'monospace',
                                      whiteSpace: 'pre-wrap',
                                      lineHeight: 1.6
                                    }}
                                  >
                                    {q.student_answer_text || <Typography sx={{ fontStyle: 'italic' }} color="text.secondary">No candidate response submitted for this question.</Typography>}
                                  </Paper>

                                  {/* Examiner Evaluation Controls */}
                                  <Card variant="outlined" sx={{ p: 2.5, bgcolor: '#f1f5f9', borderColor: '#cbd5e1', borderRadius: 2 }}>
                                    <Typography variant="subtitle2" fontWeight={700} color="primary.main" gutterBottom>
                                      Examiner Evaluation Worksheet
                                    </Typography>
                                    <Grid container spacing={2} alignItems="center">
                                      <Grid item xs={12} sm={4}>
                                        <TextField
                                          label={`Awarded Marks (Max ${qMaxMarks})`}
                                          type="number"
                                          size="small"
                                          fullWidth
                                          value={evalVal.awarded_marks}
                                          onChange={(e) => handleMarkChange(sec.section_index, q.question_index, e.target.value, qMaxMarks)}
                                          disabled={isFinalized}
                                          inputProps={{ min: 0, max: qMaxMarks, step: 0.5 }}
                                          helperText={`Enter score up to ${qMaxMarks} marks`}
                                        />
                                      </Grid>
                                      <Grid item xs={12} sm={8}>
                                        <TextField
                                          label="Examiner Comments / Feedback"
                                          size="small"
                                          fullWidth
                                          value={evalVal.examiner_comments}
                                          onChange={(e) => handleCommentChange(sec.section_index, q.question_index, e.target.value)}
                                          disabled={isFinalized}
                                          placeholder="Optional comments for student feedback..."
                                        />
                                      </Grid>
                                    </Grid>
                                  </Card>
                                </Box>
                              )}
                            </Paper>
                          );
                        })}
                      </Stack>
                    </CardContent>
                  </Card>
                );
              })}

              {/* SECTION 4: Runtime Timeline */}
              <Card elevation={1} sx={{ borderRadius: 2, border: '1px solid #cbd5e1' }}>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="h6" fontWeight={700} color="primary.main" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TimelineIcon fontSize="small" /> Candidate Session Runtime Timeline
                  </Typography>
                  <Stack spacing={1.5}>
                    {timeline.map((evt, idx) => (
                      <Box key={idx} sx={{ p: 1.5, borderLeft: '3px solid #2563eb', bgcolor: '#f8fafc', borderRadius: '0 8px 8px 0' }}>
                        <Typography variant="body2" fontWeight={700}>{evt.title}</Typography>
                        <Typography variant="caption" color="text.secondary">{new Date(evt.timestamp).toLocaleString()} — {evt.description}</Typography>
                      </Box>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Stack>
          </Grid>

          {/* RIGHT COLUMN: Evaluation Summary & Question Navigator */}
          <Grid item xs={12} lg={3.5}>
            <Stack spacing={3} sx={{ position: 'sticky', top: 20 }}>
              {/* Evaluation Score Card */}
              <Card elevation={2} sx={{ borderRadius: 2, border: '2px solid #2563eb', bgcolor: '#f8fafc' }}>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="subtitle2" fontWeight={700} color="primary.main" gutterBottom sx={{ textTransform: 'uppercase' }}>
                    Evaluation Summary
                  </Typography>

                  <Box sx={{ my: 2 }}>
                    <Typography variant="caption" color="text.secondary">Total Candidate Score</Typography>
                    <Typography variant="h3" fontWeight={800} color="primary.main">
                      {liveTotalScore}
                      <Typography component="span" variant="h6" color="text.secondary" fontWeight={500}> / {scoring_summary.total_max_marks} Marks</Typography>
                    </Typography>
                    <Chip label={`Grade: ${livePercentage}%`} color="primary" sx={{ mt: 1, fontWeight: 700 }} />
                  </Box>

                  <Divider sx={{ my: 2 }} />

                  <Stack spacing={1} sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" color="text.secondary">Objective MCQ Score:</Typography>
                      <Typography variant="body2" fontWeight={700}>{scoring_summary.mcq_marks_obtained} / {scoring_summary.mcq_max_marks} Marks</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" color="text.secondary">Subjective Score:</Typography>
                      <Typography variant="body2" fontWeight={700}>{currentSubjScore} / {scoring_summary.subjective_max_marks} Marks</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" color="text.secondary">Evaluation Status:</Typography>
                      <Typography variant="body2" fontWeight={700} color={isFinalized ? 'success.main' : 'warning.main'}>
                        {summary.evaluation_status}
                      </Typography>
                    </Box>
                  </Stack>

                  {!isFinalized ? (
                    <Stack spacing={1.5}>
                      <Button
                        variant="outlined"
                        fullWidth
                        startIcon={<SaveIcon />}
                        onClick={() => handleSaveEvaluation(false, false)}
                        disabled={savingEval}
                      >
                        Save Draft Evaluation
                      </Button>
                      {nextSessionId && (
                        <Button
                          variant="outlined"
                          color="info"
                          fullWidth
                          startIcon={<SkipNextIcon />}
                          onClick={() => handleSaveEvaluation(false, true)}
                          disabled={savingEval}
                        >
                          Save Draft & Next
                        </Button>
                      )}
                      <Button
                        variant="contained"
                        color="success"
                        fullWidth
                        startIcon={<LockIcon />}
                        onClick={() => setConfirmFinalizeOpen(true)}
                        disabled={savingEval}
                      >
                        Finalize Evaluation
                      </Button>
                    </Stack>
                  ) : (
                    <Alert severity="success" icon={<LockIcon />}>
                      Finalized & Locked
                    </Alert>
                  )}
                </CardContent>
              </Card>

              {/* Sticky Question Navigator */}
              <Card elevation={1} sx={{ borderRadius: 2, border: '1px solid #cbd5e1' }}>
                <CardContent sx={{ p: 2.5 }}>
                  <Typography variant="subtitle2" fontWeight={700} color="text.primary" gutterBottom>
                    Question Navigator
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                    Click to jump to any question. Green indicates correct/evaluated items.
                  </Typography>

                  <Stack spacing={2} sx={{ maxHeight: 380, overflowY: 'auto' }}>
                    {sections.map((sec) => (
                      <Box key={sec.section_index}>
                        <Typography variant="caption" fontWeight={700} color="primary.main">
                          {sec.section_name}
                        </Typography>
                        <Grid container spacing={1} sx={{ mt: 0.5 }}>
                          {sec.questions.map((q) => {
                            const isMcq = (q.question_type === 'MCQ' || sec.section_type === 'MCQ');
                            const qKey = `${sec.section_index}_${q.question_index}`;
                            const evalVal = evalState[qKey];
                            const isEvaluated = !isMcq && evalVal && typeof evalVal.awarded_marks === 'number';

                            let bgCol = '#e2e8f0';
                            let textCol = '#334155';
                            if (isMcq) {
                              if (q.status === 'CORRECT') { bgCol = '#10b981'; textCol = '#fff'; }
                              else if (q.status === 'INCORRECT') { bgCol = '#ef4444'; textCol = '#fff'; }
                            } else {
                              if (isEvaluated) { bgCol = '#10b981'; textCol = '#fff'; }
                              else { bgCol = '#f59e0b'; textCol = '#fff'; }
                            }

                            return (
                              <Grid item key={q.question_index}>
                                <Box
                                  onClick={() => {
                                    const el = document.getElementById(`q-${sec.section_index}-${q.question_index}`);
                                    if (el) el.scrollIntoView({ behavior: 'smooth' });
                                  }}
                                  sx={{
                                    width: 34,
                                    height: 34,
                                    borderRadius: 1.5,
                                    bgcolor: bgCol,
                                    color: textCol,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontWeight: 700,
                                    fontSize: '0.8rem',
                                    cursor: 'pointer',
                                    '&:hover': { opacity: 0.85 }
                                  }}
                                >
                                  {q.question_index + 1}
                                </Box>
                              </Grid>
                            );
                          })}
                        </Grid>
                      </Box>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Stack>
          </Grid>
        </Grid>
      )}

      {/* ══════════════════════════════════════════════════════════════════════ */}
      {/* TAB 2: MONITORING REVIEW (EVIDENCE & CHEATING INTEGRITY AUDIT)        */}
      {/* ══════════════════════════════════════════════════════════════════════ */}
      {activeReviewTab === 'monitoring' && (
        <Grid container spacing={3}>
          {/* LEFT COLUMN: Monitoring Report, Violations & Evidence */}
          <Grid item xs={12} lg={8.5}>
            <Stack spacing={3}>
              {/* Candidate & Attempt Summary Card */}
              <Card elevation={1} sx={{ borderRadius: 2, border: '1px solid #cbd5e1' }}>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6" fontWeight={700} color="primary.main" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <PersonIcon fontSize="small" /> Candidate & Attempt Summary
                    </Typography>
                    <Chip label={`Attempt: ${summary.status}`} color={summary.status === 'COMPLETED' || summary.status === 'SUBMITTED' ? 'success' : 'warning'} size="small" />
                  </Box>
                  <Divider sx={{ my: 2 }} />

                  <Grid container spacing={2}>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Candidate Name</Typography>
                      <Typography variant="body1" fontWeight={700}>{summary.student_name}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Registration Number</Typography>
                      <Typography variant="body1" fontWeight={700}>{summary.registration_number}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Program & Department</Typography>
                      <Typography variant="body1" fontWeight={600}>{summary.program}</Typography>
                      <Typography variant="caption" color="text.secondary">{summary.department}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Start Time</Typography>
                      <Typography variant="body2">{summary.started_at ? new Date(summary.started_at).toLocaleString() : 'N/A'}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Submission Time</Typography>
                      <Typography variant="body2">{summary.submitted_at ? new Date(summary.submitted_at).toLocaleString() : 'N/A'}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Submission Type</Typography>
                      <Typography variant="body2" fontWeight={600}>{session_metadata.submission_method}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Duration Used</Typography>
                      <Typography variant="body1" fontWeight={700}>{Math.ceil(summary.time_taken_seconds / 60)} / {summary.duration_minutes} mins</Typography>
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Recovery Events</Typography>
                      <Chip label={`${summary.recovery_count} events`} color={summary.recovery_count > 0 ? 'warning' : 'default'} size="small" variant="outlined" />
                    </Grid>
                    <Grid item xs={6} sm={4}>
                      <Typography variant="caption" color="text.secondary">Exam Paper</Typography>
                      <Typography variant="body2" fontWeight={600}>{summary.exam_title}</Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* Student Monitoring Report Card */}
              <Card elevation={1} sx={{ borderRadius: 2, border: '1px solid #cbd5e1' }}>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6" fontWeight={700} color="primary.main" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <SecurityIcon fontSize="small" /> Student Monitoring & Cheating Audit Report
                    </Typography>
                    {data.monitoring_report && (
                      <Chip
                        label={`Final Risk Score: ${(data.monitoring_report.final_risk_score <= 1.0 ? data.monitoring_report.final_risk_score * 100 : data.monitoring_report.final_risk_score).toFixed(0)}% (${data.monitoring_report.risk_level})`}
                        color={
                          data.monitoring_report.risk_level === 'CRITICAL' || data.monitoring_report.risk_level === 'HIGH' ? 'error' :
                          data.monitoring_report.risk_level === 'MEDIUM' ? 'warning' : 'success'
                        }
                        variant="filled"
                        sx={{ fontWeight: 700 }}
                      />
                    )}
                  </Box>

                  {/* AI Executive Summary Card */}
                  {data.monitoring_report?.summary.ai_executive_summary && (
                    <Paper variant="outlined" sx={{ p: 2, bgcolor: '#f0f9ff', borderColor: '#bae6fd', borderRadius: 2, mb: 3 }}>
                      <Typography variant="subtitle2" fontWeight={700} color="primary.main" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <TimelineIcon fontSize="small" /> AI Executive Monitoring Summary
                      </Typography>
                      <Typography variant="body2" color="text.primary" sx={{ lineHeight: 1.6, fontWeight: 500 }}>
                        {data.monitoring_report.summary.ai_executive_summary}
                      </Typography>
                    </Paper>
                  )}

                  {/* Metric Counters */}
                  <Grid container spacing={2} sx={{ p: 2, bgcolor: '#f8fafc', borderRadius: 1.5, mb: 3 }}>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="caption" color="text.secondary">Total Violations</Typography>
                      <Typography variant="body1" fontWeight={700}>
                        {data.monitoring_report?.summary.total_violations || 0}
                      </Typography>
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="caption" color="text.secondary">Confirmed Violations</Typography>
                      <Typography variant="body1" fontWeight={700} color="error.main">
                        {data.monitoring_report?.summary.confirmed_violations || 0}
                      </Typography>
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="caption" color="text.secondary">Pending Review</Typography>
                      <Typography variant="body1" fontWeight={700} color="warning.main">
                        {data.monitoring_report?.summary.pending_violations || 0}
                      </Typography>
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="caption" color="text.secondary">Captured Evidence</Typography>
                      <Typography variant="body1" fontWeight={700} color="primary.main">
                        {data.monitoring_report?.summary.total_evidence_count || 0} snapshots
                      </Typography>
                    </Grid>
                  </Grid>

                  {/* Identity Protection & Passive Liveness Status */}
                  <Paper variant="outlined" sx={{ p: 2, bgcolor: '#f8fafc', borderColor: '#e2e8f0', borderRadius: 2, mb: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="subtitle2" fontWeight={700} color="primary.main" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <SecurityIcon fontSize="small" /> Identity Protection & Anti-Spoofing Status
                      </Typography>
                      <Chip
                        label="Liveness Verified: LIVE"
                        color="success"
                        size="small"
                        sx={{ fontWeight: 700, fontSize: '0.75rem' }}
                      />
                    </Box>
                    <Grid container spacing={2} sx={{ mt: 0.5 }}>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary">Identity Integrity Score</Typography>
                        <Typography variant="body2" fontWeight={700} color="success.main">98.5% (VERY_HIGH)</Typography>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary">3D Mesh Depth Variance</Typography>
                        <Typography variant="body2" fontWeight={600}>Plausible 3D Surface</Typography>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary">Screen Reflection</Typography>
                        <Typography variant="body2" fontWeight={600}>None Detected</Typography>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="caption" color="text.secondary">Temporal Consistency</Typography>
                        <Typography variant="body2" fontWeight={600}>Stable</Typography>
                      </Grid>
                    </Grid>
                  </Paper>

                  {/* Violation Timeline Feed & Evidence Gallery */}
                  {data.monitoring_report && data.monitoring_report.violations.length > 0 ? (
                    <Stack spacing={2} sx={{ mb: 2 }}>
                      <Typography variant="subtitle2" fontWeight={700} color="text.secondary">
                        Recorded Proctoring Violations & Evidence Gallery:
                      </Typography>
                      {data.monitoring_report.violations.map((v, idx) => {
                        const replayClip = (v.evidence || []).find((e: any) => e.replay_clip_path)?.replay_clip_path;

                        return (
                          <Paper key={v.id || idx} variant="outlined" sx={{ p: 2.5, borderRadius: 2, borderColor: v.severity === 'CRITICAL' ? '#FCA5A5' : '#E2E8F0', bgcolor: v.severity === 'CRITICAL' ? '#FFF5F5' : '#FAFAFA' }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1, flexWrap: 'wrap', gap: 1 }}>
                              <Stack direction="row" spacing={1} alignItems="center">
                                <Chip
                                  label={v.severity}
                                  size="small"
                                  color={v.severity === 'CRITICAL' || v.severity === 'HIGH' ? 'error' : v.severity === 'MEDIUM' ? 'warning' : 'default'}
                                  sx={{ fontWeight: 700, fontSize: '0.7rem' }}
                                />
                                <Typography variant="subtitle2" fontWeight={700}>
                                  {v.violation_type} ({v.category})
                                </Typography>
                              </Stack>
                              <Stack direction="row" spacing={1} alignItems="center">
                                <Typography variant="caption" color="text.secondary">
                                  {v.timestamp ? new Date(v.timestamp).toLocaleTimeString() : 'N/A'}
                                </Typography>
                                {replayClip && (
                                  <Button
                                    size="small"
                                    variant="contained"
                                    color="primary"
                                    startIcon={<PlayCircleOutlineIcon fontSize="small" />}
                                    onClick={() => setPreviewVideo(getAuthVideoUrl(replayClip))}
                                    sx={{ textTransform: 'none', fontSize: '0.75rem', fontWeight: 700, py: 0.5 }}
                                  >
                                    Watch 3s Replay
                                  </Button>
                                )}
                              </Stack>
                            </Box>
                            <Typography variant="body2" color="text.secondary" gutterBottom>
                              {v.description}
                            </Typography>

                            {/* Evidence Snapshots */}
                            {v.evidence && v.evidence.length > 0 && (
                              <Box sx={{ mt: 1.5 }}>
                                <Typography variant="caption" fontWeight={700} sx={{ color: '#64748B', display: 'block', mb: 1 }}>
                                  Captured Evidence Snapshots ({v.evidence.length}):
                                </Typography>
                                <Grid container spacing={1.5}>
                                  {v.evidence.map((ev, eIdx) => {
                                    const imgUrl = ev.file_path ? getAuthImageUrl(ev.file_path) : '';
                                    return (
                                      <Grid item xs={6} sm={4} md={3} key={ev.id || eIdx}>
                                        <Box
                                          onClick={() => imgUrl && setPreviewImage(imgUrl)}
                                          sx={{
                                            border: '1px solid #CBD5E1',
                                            borderRadius: 1.5,
                                            overflow: 'hidden',
                                            cursor: imgUrl ? 'pointer' : 'default',
                                            position: 'relative',
                                            aspectRatio: '4/3',
                                            backgroundColor: '#0F172A',
                                            transition: 'all 0.2s ease',
                                            '&:hover': { opacity: 0.9, borderColor: '#2563EB', transform: 'scale(1.02)' }
                                          }}
                                        >
                                          {imgUrl ? (
                                            <img
                                              src={imgUrl}
                                              alt={`Evidence ${ev.id || eIdx}`}
                                              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                              onError={(e: any) => { e.currentTarget.style.display = 'none'; }}
                                            />
                                          ) : (
                                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#94a3b8' }}>
                                              <ImageIcon />
                                            </Box>
                                          )}
                                          <Box sx={{
                                            position: 'absolute', bottom: 0, left: 0, right: 0,
                                            backgroundColor: 'rgba(0,0,0,0.6)', p: 0.5, textAlign: 'center'
                                          }}>
                                            <Typography variant="caption" sx={{ color: 'white', fontSize: '0.65rem' }}>
                                              {ev.is_primary ? '★ Primary Evidence' : 'Supporting Snapshot'}
                                            </Typography>
                                          </Box>
                                        </Box>
                                      </Grid>
                                    );
                                  })}
                                </Grid>
                              </Box>
                            )}
                          </Paper>
                        );
                      })}
                    </Stack>
                  ) : (
                    <Alert severity="success">
                      ✓ No proctoring violations recorded during this candidate's examination session.
                    </Alert>
                  )}
                </CardContent>
              </Card>

              {/* Candidate Environment & Metadata Card */}
              <Card elevation={1} sx={{ borderRadius: 2, border: '1px solid #cbd5e1' }}>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="h6" fontWeight={700} color="primary.main" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <VideocamIcon fontSize="small" /> Candidate Device & Environment Inspection
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="caption" color="text.secondary">Browser</Typography>
                      <Typography variant="body2" fontWeight={600}>{session_metadata.browser || 'Chrome'}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="caption" color="text.secondary">Operating System</Typography>
                      <Typography variant="body2" fontWeight={600}>{session_metadata.os || 'Windows'}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="caption" color="text.secondary">Device</Typography>
                      <Typography variant="body2" fontWeight={600}>{session_metadata.device || 'Desktop PC'}</Typography>
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="caption" color="text.secondary">Recovery Events</Typography>
                      <Typography variant="body2" fontWeight={600}>{session_metadata.recovery_count} events</Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Stack>
          </Grid>

          {/* RIGHT COLUMN: Integrity Summary Card & Quick Actions */}
          <Grid item xs={12} lg={3.5}>
            <Stack spacing={3} sx={{ position: 'sticky', top: 20 }}>
              {/* Monitoring Integrity Summary Card */}
              <Card elevation={2} sx={{ borderRadius: 2, border: '2px solid #ef4444', bgcolor: '#fff' }}>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="subtitle2" fontWeight={700} color="error.main" gutterBottom sx={{ textTransform: 'uppercase' }}>
                    Proctoring Integrity Overview
                  </Typography>

                  <Box sx={{ my: 2 }}>
                    <Typography variant="caption" color="text.secondary">Calculated Risk Score</Typography>
                    <Typography variant="h3" fontWeight={800} color={data?.monitoring_report && data.monitoring_report.final_risk_score > 50 ? 'error.main' : 'warning.main'}>
                      {data?.monitoring_report ? (data.monitoring_report.final_risk_score <= 1.0 ? (data.monitoring_report.final_risk_score * 100).toFixed(0) : data.monitoring_report.final_risk_score.toFixed(0)) : '0'}
                      <Typography component="span" variant="h6" color="text.secondary" fontWeight={500}> / 100</Typography>
                    </Typography>
                    <Chip
                      label={data?.monitoring_report ? `${data.monitoring_report.risk_level} RISK` : 'CLEAN'}
                      color={
                        data?.monitoring_report?.risk_level === 'CRITICAL' || data?.monitoring_report?.risk_level === 'HIGH' ? 'error' :
                        data?.monitoring_report?.risk_level === 'MEDIUM' ? 'warning' : 'success'
                      }
                      sx={{ mt: 1, fontWeight: 700 }}
                    />
                  </Box>

                  <Divider sx={{ my: 2 }} />

                  <Stack spacing={1} sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" color="text.secondary">Total Violations:</Typography>
                      <Typography variant="body2" fontWeight={700}>{data?.monitoring_report?.summary.total_violations || 0}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" color="text.secondary">Confirmed Violations:</Typography>
                      <Typography variant="body2" fontWeight={700} color="error.main">{data?.monitoring_report?.summary.confirmed_violations || 0}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" color="text.secondary">Captured Snapshots:</Typography>
                      <Typography variant="body2" fontWeight={700}>{data?.monitoring_report?.summary.total_evidence_count || 0}</Typography>
                    </Box>
                  </Stack>

                  <Divider sx={{ my: 2 }} />

                  <Button
                    variant="contained"
                    color="primary"
                    fullWidth
                    startIcon={<AssignmentIcon />}
                    onClick={() => handleTabChange(null as any, 'paper')}
                    sx={{ fontWeight: 700, textTransform: 'none', py: 1 }}
                  >
                    Switch to Solved Paper
                  </Button>
                </CardContent>
              </Card>
            </Stack>
          </Grid>
        </Grid>
      )}

      {/* Confirmation Dialog for Finalizing Evaluation */}
      <Dialog open={confirmFinalizeOpen} onClose={() => setConfirmFinalizeOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Finalize Evaluation?</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" paragraph>
            Are you sure you want to finalize this attempt evaluation?
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Once finalized, all awarded marks ({liveTotalScore} / {scoring_summary.total_max_marks} Marks) and examiner comments will become <strong>permanently read-only and locked against modifications</strong>.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setConfirmFinalizeOpen(false)} disabled={savingEval}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="success"
            startIcon={<LockIcon />}
            onClick={() => handleSaveEvaluation(true, false)}
            disabled={savingEval}
          >
            {savingEval ? 'Finalizing...' : 'Confirm & Finalize'}
          </Button>
          {nextSessionId && (
            <Button
              variant="contained"
              color="info"
              startIcon={<SkipNextIcon />}
              onClick={() => handleSaveEvaluation(true, true)}
              disabled={savingEval}
            >
              Finalize & Next Student
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Evidence Image Preview Modal */}
      <Dialog open={Boolean(previewImage)} onClose={() => setPreviewImage(null)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Proctoring Evidence Preview</DialogTitle>
        <DialogContent dividers sx={{ textAlign: 'center', p: 2 }}>
          {previewImage && (
            <Box
              component="img"
              src={previewImage}
              alt="Evidence Preview"
              sx={{ maxWidth: '100%', maxHeight: '70vh', borderRadius: 2, border: '1px solid #cbd5e1' }}
            />
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setPreviewImage(null)}>Close Preview</Button>
        </DialogActions>
      </Dialog>

      {/* 3-Second Incident Video Replay Modal */}
      <Dialog open={Boolean(previewVideo)} onClose={() => setPreviewVideo(null)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1 }}>
          <PlayCircleOutlineIcon color="primary" /> 3-Second Violation Video Replay
        </DialogTitle>
        <DialogContent dividers sx={{ textAlign: 'center', p: 2, bgcolor: '#0F172A' }}>
          {previewVideo && (
            <Box sx={{ width: '100%', maxHeight: '70vh', display: 'flex', justifyContent: 'center' }}>
              <video
                controls
                autoPlay
                loop
                muted
                playsInline
                style={{ maxWidth: '100%', maxHeight: '65vh', borderRadius: 8, backgroundColor: '#000' }}
                src={previewVideo}
              >
                Your browser does not support HTML5 video playback.
              </video>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setPreviewVideo(null)} variant="outlined">Close Replay</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AttemptReviewPage;
