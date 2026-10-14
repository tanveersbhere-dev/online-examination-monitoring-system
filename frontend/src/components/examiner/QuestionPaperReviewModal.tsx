import React, { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography, Box,
  Chip, Stack, Card, CardContent, Divider, CircularProgress, Alert, Grid
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import TimerIcon from '@mui/icons-material/Timer';
import QuizIcon from '@mui/icons-material/Quiz';
import CalculateIcon from '@mui/icons-material/Calculate';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';

interface Props {
  paperId: number | null;
  open: boolean;
  onClose: () => void;
}

const QuestionPaperReviewModal: React.FC<Props> = ({ paperId, open, onClose }) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [paper, setPaper] = useState<any>(null);

  useEffect(() => {
    if (open && paperId) {
      fetchFullPaper(paperId);
    } else {
      setPaper(null);
      setError(null);
    }
  }, [open, paperId]);

  const fetchFullPaper = async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(`/question-paper-builder/${id}/full`);
      setPaper(res.data);
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ m: 0, p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#f8fafc' }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <VisibilityIcon color="primary" />
          <Typography variant="h6" fontWeight={700}>
            Academic Question Paper Review
          </Typography>
        </Stack>
        <Chip label="Read-Only Mode" color="info" variant="outlined" size="small" />
      </DialogTitle>

      <DialogContent dividers sx={{ p: 3, backgroundColor: '#f8fafc' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Alert severity="error">{error}</Alert>
        ) : !paper ? (
          <Typography color="text.secondary">No paper data available.</Typography>
        ) : (
          <Stack spacing={3}>
            {/* Header Paper Summary Card */}
            <Card elevation={1} sx={{ borderRadius: 2, border: '1px solid #e2e8f0' }}>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>
                      {paper.course_name}
                    </Typography>
                    <Typography variant="h5" fontWeight={700} color="primary.main">
                      {paper.title}
                    </Typography>
                    {paper.description && (
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                        {paper.description}
                      </Typography>
                    )}
                  </Box>
                  <Chip label={paper.status} color={paper.status === 'READY' ? 'success' : 'default'} size="small" />
                </Box>

                <Divider sx={{ my: 2 }} />

                {(() => {
                  const paperTotalMarks = paper.section_rules?.length
                    ? paper.section_rules.reduce((acc: number, sec: any) => {
                        const sMarks = sec.question_rules?.length 
                          ? sec.question_rules.reduce((qSum: number, q: any) => qSum + (Number(q.marks) || Number(q.calculated_marks) || 1), 0)
                          : (sec.total_section_marks ?? sec.section_weight ?? 0);
                        return acc + sMarks;
                      }, 0)
                    : (paper.total_marks || 0);

                  const paperTotalQuestions = paper.section_rules?.length
                    ? paper.section_rules.reduce((acc: number, sec: any) => acc + (sec.question_rules?.length || 0), 0)
                    : (paper.total_questions || 0);

                  return (
                    <Grid container spacing={2}>
                      <Grid item xs={6} sm={3}>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <CalculateIcon color="primary" fontSize="small" />
                          <Box>
                            <Typography variant="caption" color="text.secondary">Total Marks</Typography>
                            <Typography variant="body1" fontWeight={700}>{paperTotalMarks} pts</Typography>
                          </Box>
                        </Stack>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <TimerIcon color="secondary" fontSize="small" />
                          <Box>
                            <Typography variant="caption" color="text.secondary">Paper Academic Duration</Typography>
                            <Typography variant="body1" fontWeight={700}>{paper.paper_academic_duration_minutes || 50} mins</Typography>
                          </Box>
                        </Stack>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <QuizIcon color="action" fontSize="small" />
                          <Box>
                            <Typography variant="caption" color="text.secondary">Sections</Typography>
                            <Typography variant="body1" fontWeight={700}>{paper.section_rules?.length || 0}</Typography>
                          </Box>
                        </Stack>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <QuizIcon color="action" fontSize="small" />
                          <Box>
                            <Typography variant="caption" color="text.secondary">Total Questions</Typography>
                            <Typography variant="body1" fontWeight={700}>{paperTotalQuestions}</Typography>
                          </Box>
                        </Stack>
                      </Grid>
                    </Grid>
                  );
                })()}
              </CardContent>
            </Card>

            {/* Sections & Questions */}
            {paper.section_rules?.map((sec: any, secIdx: number) => {
              const qCount = sec.question_rules?.length || 0;
              const secMarks = sec.question_rules?.length
                ? sec.question_rules.reduce((qSum: number, q: any) => qSum + (Number(q.marks) || Number(q.calculated_marks) || 1), 0)
                : (sec.total_section_marks ?? sec.section_weight ?? 0);
              const calcWeight = qCount > 0 ? (secMarks / qCount).toFixed(2) : '0';

              return (
                <Card key={sec.id || secIdx} elevation={1} sx={{ borderRadius: 2, border: '1px solid #cbd5e1' }}>
                  <CardContent sx={{ p: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="h6" fontWeight={700}>
                        Section {secIdx + 1}: {sec.section_name}
                      </Typography>
                      <Chip label={sec.section_type || 'MCQ'} size="small" color="primary" variant="outlined" />
                    </Box>

                    {sec.instructions && (
                      <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', mb: 2 }}>
                        Instructions: {sec.instructions}
                      </Typography>
                    )}

                    <Stack direction="row" spacing={2} sx={{ mb: 3, p: 1.5, backgroundColor: '#f1f5f9', borderRadius: 1.5, flexWrap: 'wrap' }}>
                      <Typography variant="body2" fontWeight={600}>Section Marks: {secMarks} pts</Typography>
                      <Typography variant="body2" color="text.secondary">|</Typography>
                      <Typography variant="body2" fontWeight={600}>Questions: {qCount}</Typography>
                      <Typography variant="body2" color="text.secondary">|</Typography>
                      <Typography variant="body2" fontWeight={700} color="primary.main">
                        Avg Marks / Question: {calcWeight} pts
                      </Typography>
                    </Stack>

                    {/* Questions List */}
                    <Stack spacing={2}>
                      {sec.question_rules?.map((q: any, qIdx: number) => (
                        <Box key={q.id || qIdx} sx={{ p: 2, border: '1px solid #e2e8f0', borderRadius: 1.5, backgroundColor: '#ffffff' }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                            <Typography variant="body1" fontWeight={700}>
                              Q{qIdx + 1}. {q.question_text || 'Untitled Question'}
                            </Typography>
                            <Chip label={`${q.marks ?? q.calculated_marks ?? calcWeight} pts`} size="small" color="primary" sx={{ fontWeight: 700 }} />
                          </Box>

                          {/* MCQ Options */}
                          {q.options && q.options.length > 0 && (
                            <Stack spacing={0.5} sx={{ mt: 1.5, pl: 1 }}>
                              {q.options.map((opt: any, optIdx: number) => (
                                <Box 
                                  key={opt.id || optIdx} 
                                  sx={{ 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    justify: 'space-between',
                                    p: 1, 
                                    borderRadius: 1, 
                                    backgroundColor: opt.is_correct ? '#ecfdf5' : '#f8fafc',
                                    border: opt.is_correct ? '1px solid #6ee7b7' : '1px solid #f1f5f9'
                                  }}
                                >
                                  <Typography variant="body2" color={opt.is_correct ? 'success.dark' : 'text.primary'} fontWeight={opt.is_correct ? 600 : 400}>
                                    {String.fromCharCode(65 + optIdx)}. {opt.option_text}
                                  </Typography>
                                  {opt.is_correct && (
                                    <Chip icon={<CheckCircleIcon fontSize="small" />} label="Correct Answer" color="success" size="small" />
                                  )}
                                </Box>
                              ))}
                            </Stack>
                          )}
                        </Box>
                      ))}
                    </Stack>
                  </CardContent>
                </Card>
              );
            })}

            {/* Footer Metrics */}
            <Box sx={{ p: 2, backgroundColor: '#e2e8f0', borderRadius: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="body2" fontWeight={600}>
                Total Paper Marks: {paper.section_rules?.length
                  ? paper.section_rules.reduce((acc: number, sec: any) => {
                      const sMarks = sec.question_rules?.length 
                        ? sec.question_rules.reduce((qSum: number, q: any) => qSum + (Number(q.marks) || Number(q.calculated_marks) || 1), 0)
                        : (sec.total_section_marks ?? sec.section_weight ?? 0);
                      return acc + sMarks;
                    }, 0)
                  : (paper.total_marks || 0)} pts
              </Typography>
              <Typography variant="body2" fontWeight={600}>Academic Duration: {paper.paper_academic_duration_minutes || 50} mins</Typography>
              <Typography variant="body2" fontWeight={600}>Estimated Time: {paper.paper_academic_duration_minutes || 50} mins</Typography>
            </Box>
          </Stack>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 2, backgroundColor: '#f8fafc' }}>
        <Button onClick={onClose} variant="contained">
          Close Review
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default QuestionPaperReviewModal;
