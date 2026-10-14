import React, { useState, useEffect } from 'react';
import { 
  Box, Typography, Button, Stack, Card, CardContent, TextField, IconButton, 
  Divider, CircularProgress, Alert, Switch, FormControlLabel, RadioGroup, Radio,
  FormControl, FormLabel, Paper, Grid, Tooltip, Chip, MenuItem, Select
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddCircleIcon from '@mui/icons-material/AddCircle';
import SaveIcon from '@mui/icons-material/Save';
import LayersIcon from '@mui/icons-material/Layers';
import QuizIcon from '@mui/icons-material/Quiz';
import TimerIcon from '@mui/icons-material/Timer';
import SecurityIcon from '@mui/icons-material/Security';
import CalculateIcon from '@mui/icons-material/Calculate';
import DescriptionIcon from '@mui/icons-material/Description';
import apiClient from '../../services/apiClient';

interface Props {
  paperId: number;
  onClose: () => void;
}

interface QuestionOption {
  id?: number;
  option_text: string;
  is_correct: boolean;
}

interface Question {
  id?: number;
  question_index: number;
  question_type: string; // 'MCQ' | 'SHORT_ANSWER' | 'LONG_ANSWER' | 'ESSAY'
  marks: number;
  is_required: boolean;
  question_text: string;
  instructions?: string;
  word_limit?: number | null;
  min_words?: number | null;
  options: QuestionOption[];
}

interface Section {
  id?: number;
  section_index: number;
  section_name: string;
  section_type: 'MCQ' | 'SUBJECTIVE';
  section_duration_minutes: number | null;
  navigation_policy: string;
  allow_return_to_previous: boolean;
  lock_after_timeout: boolean;
  randomize_questions: boolean;
  randomize_options?: boolean;
  require_completion_before_next: boolean;
  section_weight: number;
  instructions: string;
  presentation: 'SHOW_ENTIRE' | 'ONE_AT_A_TIME';
  question_count: number;
  question_rules: Question[];
}

const AssessmentBuilderUI: React.FC<Props> = ({ paperId, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Assessment Setup State
  const [assessmentType, setAssessmentType] = useState<'MCQ' | 'SUBJECTIVE' | 'MIXED'>('MCQ');
  const [deliveryMode, setDeliveryMode] = useState<'ENTIRE' | 'SECTION'>('ENTIRE');
  const [totalAssessmentTime, setTotalAssessmentTime] = useState<number | ''>(60);
  const [autoSubmitOnTimeout, setAutoSubmitOnTimeout] = useState<boolean>(true);

  // Sections State
  const [sections, setSections] = useState<Section[]>([]);

  useEffect(() => {
    fetchPaper();
  }, [paperId]);

  const generateDefaultOptions = () => [
    { option_text: 'Option A', is_correct: true },
    { option_text: 'Option B', is_correct: false },
    { option_text: 'Option C', is_correct: false },
    { option_text: 'Option D', is_correct: false }
  ];

  const fetchPaper = async () => {
    try {
      const res = await apiClient.get(`/question-paper-builder/${paperId}/full`);
      const rawRules = res.data.section_rules || [];
      
      let isSectionBased = false;
      let hasMCQ = false;
      let hasSubjective = false;

      const formattedSections: Section[] = rawRules.map((g: any, idx: number) => {
        if (g.section_duration_minutes && g.section_duration_minutes > 0) {
          isSectionBased = true;
        }

        const secType: 'MCQ' | 'SUBJECTIVE' = (g.section_type === 'SUBJECTIVE' || g.section_type === 'SHORT_ANSWER' || g.section_type === 'ESSAY') 
          ? 'SUBJECTIVE' 
          : 'MCQ';

        const questions: Question[] = (g.question_rules || []).map((q: any) => {
          if (q.question_type === 'MCQ') {
            hasMCQ = true;
          } else {
            hasSubjective = true;
          }

          let parsedInstructions = q.instructions || '';
          let parsedWordLimit: number | null = q.word_limit ?? null;

          if (q.explanation && q.explanation.includes('Word Limit:')) {
            const match = q.explanation.match(/Word Limit:\s*(\d+)/);
            if (match) parsedWordLimit = parseInt(match[1]);
          }

          return {
            id: q.id,
            question_index: q.question_index,
            question_type: q.question_type || (secType === 'MCQ' ? 'MCQ' : 'SHORT_ANSWER'),
            marks: q.marks ?? 1,
            is_required: q.is_required ?? true,
            question_text: q.question_text || '',
            instructions: parsedInstructions,
            word_limit: parsedWordLimit,
            min_words: null,
            options: (q.options && q.options.length > 0) 
              ? q.options 
              : (q.question_type === 'MCQ' || secType === 'MCQ' ? generateDefaultOptions() : [])
          };
        });

        if (secType === 'MCQ') hasMCQ = true;
        if (secType === 'SUBJECTIVE') hasSubjective = true;

        return {
          id: g.id,
          section_index: g.section_index || idx + 1,
          section_name: g.section_name || `Section ${String.fromCharCode(65 + idx)}`,
          section_type: secType,
          section_duration_minutes: g.section_duration_minutes ?? null,
          navigation_policy: g.navigation_policy || 'FREE',
          allow_return_to_previous: g.allow_return_to_previous ?? true,
          lock_after_timeout: g.lock_after_timeout ?? true,
          randomize_questions: g.randomize_questions ?? false,
          randomize_options: g.randomize_options ?? false,
          require_completion_before_next: g.require_completion_before_next ?? false,
          section_weight: g.section_weight ?? 1.0,
          instructions: g.instructions || '',
          presentation: g.navigation_policy === 'SEQUENTIAL' ? 'ONE_AT_A_TIME' : 'SHOW_ENTIRE',
          question_count: questions.length,
          question_rules: questions
        };
      });

      if (hasMCQ && hasSubjective) {
        setAssessmentType('MIXED');
      } else if (hasSubjective) {
        setAssessmentType('SUBJECTIVE');
      } else {
        setAssessmentType('MCQ');
      }

      if (formattedSections.length > 0 && isSectionBased) {
        setDeliveryMode('SECTION');
      }

      setSections(formattedSections);
    } catch (err: any) {
      setError(err.message || 'Failed to load assessment details');
    } finally {
      setLoading(false);
    }
  };

  const createDefaultQuestions = (count: number, secType: 'MCQ' | 'SUBJECTIVE'): Question[] => {
    const questions: Question[] = [];
    for (let i = 1; i <= count; i++) {
      questions.push({
        question_index: i,
        question_type: secType === 'MCQ' ? 'MCQ' : 'SHORT_ANSWER',
        marks: secType === 'MCQ' ? 1 : 5,
        is_required: true,
        question_text: '',
        instructions: '',
        word_limit: null,
        min_words: null,
        options: secType === 'MCQ' ? generateDefaultOptions() : []
      });
    }
    return questions;
  };

  const addSection = (defaultSecType?: 'MCQ' | 'SUBJECTIVE') => {
    const nextChar = String.fromCharCode(65 + sections.length);
    const defaultCount = 5;
    const initialSecType = defaultSecType || (assessmentType === 'SUBJECTIVE' ? 'SUBJECTIVE' : 'MCQ');

    setSections([...sections, {
      section_index: sections.length + 1,
      section_name: `Section ${nextChar}`,
      section_type: initialSecType,
      section_duration_minutes: deliveryMode === 'SECTION' ? 15 : null,
      navigation_policy: 'FREE',
      allow_return_to_previous: true,
      lock_after_timeout: autoSubmitOnTimeout,
      randomize_questions: false,
      randomize_options: false,
      require_completion_before_next: deliveryMode === 'SECTION',
      section_weight: 1.0,
      instructions: '',
      presentation: 'SHOW_ENTIRE',
      question_count: defaultCount,
      question_rules: createDefaultQuestions(defaultCount, initialSecType)
    }]);
  };

  const handleSectionTypeChange = (sIndex: number, newSecType: 'MCQ' | 'SUBJECTIVE') => {
    const updated = [...sections];
    updated[sIndex].section_type = newSecType;
    updated[sIndex].question_rules = updated[sIndex].question_rules.map(q => ({
      ...q,
      question_type: newSecType === 'MCQ' ? 'MCQ' : (q.question_type === 'MCQ' ? 'SHORT_ANSWER' : q.question_type),
      marks: newSecType === 'MCQ' ? 1 : (q.marks || 5),
      options: newSecType === 'MCQ' ? (q.options.length > 0 ? q.options : generateDefaultOptions()) : []
    }));
    setSections(updated);
  };

  const handleQuestionCountChange = (sIndex: number, newCount: number) => {
    const count = Math.max(1, Math.min(100, newCount || 1));
    const updated = [...sections];
    const currentQuestions = updated[sIndex].question_rules;
    const secType = updated[sIndex].section_type;
    
    if (count > currentQuestions.length) {
      const addedCount = count - currentQuestions.length;
      const newQuestions: Question[] = [];
      for (let i = 1; i <= addedCount; i++) {
        const qIndex = currentQuestions.length + i;
        newQuestions.push({
          question_index: qIndex,
          question_type: secType === 'MCQ' ? 'MCQ' : 'SHORT_ANSWER',
          marks: secType === 'MCQ' ? 1 : 5,
          is_required: true,
          question_text: '',
          instructions: '',
          word_limit: null,
          min_words: null,
          options: secType === 'MCQ' ? generateDefaultOptions() : []
        });
      }
      updated[sIndex].question_rules = [...currentQuestions, ...newQuestions];
    } else if (count < currentQuestions.length) {
      updated[sIndex].question_rules = currentQuestions.slice(0, count);
    }
    
    updated[sIndex].question_count = count;
    setSections(updated);
  };

  const addSingleQuestion = (sIndex: number) => {
    const updated = [...sections];
    const secType = updated[sIndex].section_type;
    const qCount = updated[sIndex].question_rules.length + 1;
    updated[sIndex].question_rules.push({
      question_index: qCount,
      question_type: secType === 'MCQ' ? 'MCQ' : 'SHORT_ANSWER',
      marks: secType === 'MCQ' ? 1 : 5,
      is_required: true,
      question_text: '',
      instructions: '',
      word_limit: null,
      min_words: null,
      options: secType === 'MCQ' ? generateDefaultOptions() : []
    });
    updated[sIndex].question_count = updated[sIndex].question_rules.length;
    setSections(updated);
  };

  const removeSection = (sIndex: number) => {
    const updated = sections.filter((_, idx) => idx !== sIndex);
    const reindexed = updated.map((sec, idx) => ({
      ...sec,
      section_index: idx + 1
    }));
    setSections(reindexed);
  };

  // Calculations for Marks
  const calculateSectionMarks = (sec: Section) => {
    return sec.question_rules.reduce((sum, q) => sum + (q.marks || 0), 0);
  };

  const calculateMarksBreakdown = () => {
    let mcqTotal = 0;
    let subjectiveTotal = 0;

    sections.forEach(sec => {
      const secMarks = calculateSectionMarks(sec);
      if (sec.section_type === 'MCQ') {
        mcqTotal += secMarks;
      } else {
        subjectiveTotal += secMarks;
      }
    });

    return { mcqTotal, subjectiveTotal, grandTotal: mcqTotal + subjectiveTotal };
  };

  const handleAssessmentTypeChange = (newType: 'MCQ' | 'SUBJECTIVE' | 'MIXED') => {
    setAssessmentType(newType);
    if (newType !== 'MIXED') {
      const targetSecType: 'MCQ' | 'SUBJECTIVE' = newType;
      const updated = sections.map(sec => ({
        ...sec,
        section_type: targetSecType,
        question_rules: sec.question_rules.map(q => ({
          ...q,
          question_type: targetSecType === 'MCQ' ? 'MCQ' : (q.question_type === 'MCQ' ? 'SHORT_ANSWER' : q.question_type),
          marks: targetSecType === 'MCQ' ? 1 : (q.marks || 5),
          options: targetSecType === 'MCQ' ? (q.options.length > 0 ? q.options : generateDefaultOptions()) : []
        }))
      }));
      setSections(updated);
    }
  };

  const saveAll = async () => {
    setSaving(true);
    setError(null);
    try {
      for (const section of sections) {
        if (section.section_duration_minutes !== null && section.section_duration_minutes !== undefined) {
          const dur = Number(section.section_duration_minutes);
          if (isNaN(dur) || dur <= 0 || !Number.isInteger(dur)) {
            throw new Error(`Invalid duration in ${section.section_name}. Duration must be a positive integer.`);
          }
        }
        if (section.section_weight !== null && section.section_weight !== undefined) {
          const w = Number(section.section_weight);
          if (isNaN(w) || w <= 0) {
            throw new Error(`Invalid weight in ${section.section_name}. Weight must be greater than 0.`);
          }
        }
        for (const q of section.question_rules) {
          const m = Number(q.marks);
          if (isNaN(m) || m < 1 || !Number.isInteger(m)) {
            throw new Error(`Invalid marks for Question #${q.question_index} in ${section.section_name}. Marks must be a positive integer (e.g. 1, 2, 5).`);
          }
        }
      }
      for (const section of sections) {
        let sectionId = section.id;

        const navPolicy = section.presentation === 'ONE_AT_A_TIME' ? 'SEQUENTIAL' : 'FREE';
        const sectionDuration = deliveryMode === 'SECTION' ? section.section_duration_minutes : null;

        const payload = {
          section_index: section.section_index,
          section_name: section.section_name,
          section_type: section.section_type,
          section_duration_minutes: sectionDuration,
          navigation_policy: navPolicy,
          allow_return_to_previous: true,
          randomize_questions: Boolean(section.randomize_questions),
          lock_after_timeout: deliveryMode === 'SECTION' ? autoSubmitOnTimeout : false,
          require_completion_before_next: deliveryMode === 'SECTION',
          section_weight: calculateSectionMarks(section) || 1.0,
          instructions: section.instructions || ''
        };

        if (!sectionId) {
          const res = await apiClient.post(`/question-paper-builder/${paperId}/groups`, payload);
          sectionId = res.data.id;
          section.id = sectionId;
        } else {
          await apiClient.put(`/question-paper-builder/${paperId}/groups/${sectionId}`, payload);
        }

        for (const q of section.question_rules) {
          let explanationStr = q.instructions || '';
          if (q.word_limit) {
            explanationStr += (explanationStr ? ' | ' : '') + `Word Limit: ${q.word_limit}`;
          }

          const isMcq = section.section_type === 'MCQ' || q.question_type === 'MCQ';

          const qPayload = {
            question_index: q.question_index,
            question_type: isMcq ? 'MCQ' : (q.question_type || 'SHORT_ANSWER'),
            marks: q.marks || 1,
            is_required: true,
            question_text: q.question_text || `Question ${q.question_index}`,
            explanation: explanationStr || null,
            options: isMcq ? q.options : []
          };

          if (!q.id) {
            await apiClient.post(`/question-paper-builder/${paperId}/groups/${sectionId}/questions`, qPayload);
          } else {
            await apiClient.put(`/question-paper-builder/${paperId}/groups/${sectionId}/questions/${q.id}`, qPayload);
          }
        }
      }
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save assessment');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Box sx={{ p: 4, textAlign: 'center' }}><CircularProgress /></Box>;

  const { mcqTotal, subjectiveTotal, grandTotal } = calculateMarksBreakdown();

  return (
    <Box sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column', bgcolor: '#f8fafc' }}>
      {/* Header */}
      <Paper elevation={0} sx={{ p: 2, mb: 3, border: '1px solid #e2e8f0', borderRadius: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', bgcolor: '#fff', flexWrap: 'wrap', gap: 2 }}>
        <Box display="flex" alignItems="center" gap={2} flexWrap="wrap">
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#0f172a' }}>
              Professional Assessment Authoring
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Configure CBT structure, delivery workflow, and section items
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', bgcolor: '#f1f5f9', px: 2, py: 1, borderRadius: 2, border: '1px solid #cbd5e1' }}>
            <Box sx={{ textAlign: 'center', px: 1 }}>
              <Typography variant="caption" color="text.secondary" fontWeight={700} display="block" sx={{ fontSize: '0.7rem', letterSpacing: 0.5 }}>
                TOTAL MARKS
              </Typography>
              <Typography variant="h6" fontWeight={800} color="primary.main" sx={{ lineHeight: 1.2 }}>
                {grandTotal} Marks
              </Typography>
            </Box>
            <Divider orientation="vertical" flexItem />
            <Box sx={{ textAlign: 'center', px: 1 }}>
              <Typography variant="caption" color="text.secondary" fontWeight={700} display="block" sx={{ fontSize: '0.7rem', letterSpacing: 0.5 }}>
                SECTIONS
              </Typography>
              <Typography variant="body1" fontWeight={700} sx={{ lineHeight: 1.2 }}>
                {sections.length}
              </Typography>
            </Box>
            <Divider orientation="vertical" flexItem />
            <Box sx={{ textAlign: 'center', px: 1 }}>
              <Typography variant="caption" color="text.secondary" fontWeight={700} display="block" sx={{ fontSize: '0.7rem', letterSpacing: 0.5 }}>
                QUESTIONS
              </Typography>
              <Typography variant="body1" fontWeight={700} sx={{ lineHeight: 1.2 }}>
                {sections.reduce((acc, s) => acc + (s.question_rules?.length || 0), 0)}
              </Typography>
            </Box>
            {assessmentType === 'MIXED' && (
              <>
                <Divider orientation="vertical" flexItem />
                <Stack spacing={0.2} sx={{ pl: 0.5 }}>
                  <Typography variant="caption" color="primary.dark" fontWeight={600} sx={{ fontSize: '0.7rem' }}>MCQ: {mcqTotal} M</Typography>
                  <Typography variant="caption" color="secondary.dark" fontWeight={600} sx={{ fontSize: '0.7rem' }}>Subj: {subjectiveTotal} M</Typography>
                </Stack>
              </>
            )}
          </Box>
        </Box>

        <Stack direction="row" spacing={2}>
          <Button variant="outlined" color="inherit" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button variant="contained" startIcon={<SaveIcon />} onClick={saveAll} disabled={saving} sx={{ bgcolor: '#2563eb', '&:hover': { bgcolor: '#1d4ed8' } }}>
            {saving ? 'Saving Assessment...' : 'Save Assessment'}
          </Button>
        </Stack>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Box sx={{ flexGrow: 1, overflowY: 'auto', pr: 1 }}>
        <Stack spacing={3}>
          {/* STEP 1 & 2: Assessment Setup Card */}
          <Card variant="outlined" sx={{ borderRadius: 2, borderColor: '#cbd5e1' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2, color: '#1e293b', display: 'flex', alignItems: 'center', gap: 1 }}>
                <LayersIcon color="primary" fontSize="small" />
                Assessment Setup & Delivery Strategy
              </Typography>
              <Grid container spacing={3}>
                {/* Step 1: Assessment Type */}
                <Grid item xs={12} md={6}>
                  <FormControl component="fieldset" fullWidth>
                    <FormLabel sx={{ fontWeight: 600, fontSize: '0.875rem', mb: 1, color: '#334155' }}>
                      STEP 1 — Assessment Type
                    </FormLabel>
                    <RadioGroup value={assessmentType} onChange={e => handleAssessmentTypeChange(e.target.value as 'MCQ' | 'SUBJECTIVE' | 'MIXED')}>
                      <Paper variant="outlined" sx={{ p: 1.5, mb: 1, borderColor: assessmentType === 'MCQ' ? '#2563eb' : '#e2e8f0', bgcolor: assessmentType === 'MCQ' ? '#eff6ff' : '#fff' }}>
                        <FormControlLabel 
                          value="MCQ" 
                          control={<Radio size="small" />} 
                          label={
                            <Box>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>MCQ Only</Typography>
                              <Typography variant="caption" color="text.secondary">Automated grading with multiple choice questions</Typography>
                            </Box>
                          } 
                        />
                      </Paper>

                      <Paper variant="outlined" sx={{ p: 1.5, mb: 1, borderColor: assessmentType === 'SUBJECTIVE' ? '#2563eb' : '#e2e8f0', bgcolor: assessmentType === 'SUBJECTIVE' ? '#eff6ff' : '#fff' }}>
                        <FormControlLabel 
                          value="SUBJECTIVE" 
                          control={<Radio size="small" />} 
                          label={
                            <Box display="flex" alignItems="center" gap={1}>
                              <Box>
                                <Typography variant="body2" sx={{ fontWeight: 600 }}>Subjective Only</Typography>
                                <Typography variant="caption" color="text.secondary">Short answer, long answer & essay questions</Typography>
                              </Box>
                            </Box>
                          } 
                        />
                      </Paper>

                      <Paper variant="outlined" sx={{ p: 1.5, borderColor: assessmentType === 'MIXED' ? '#2563eb' : '#e2e8f0', bgcolor: assessmentType === 'MIXED' ? '#eff6ff' : '#fff' }}>
                        <FormControlLabel 
                          value="MIXED" 
                          control={<Radio size="small" />} 
                          label={
                            <Box display="flex" alignItems="center" gap={1}>
                              <Box>
                                <Typography variant="body2" sx={{ fontWeight: 600 }}>Mixed Assessment</Typography>
                                <Typography variant="caption" color="text.secondary">Combine MCQ and Subjective sections in one assessment</Typography>
                              </Box>
                            </Box>
                          } 
                        />
                      </Paper>
                    </RadioGroup>
                  </FormControl>
                </Grid>

                {/* Step 2: Assessment Delivery */}
                <Grid item xs={12} md={6}>
                  <FormControl component="fieldset" fullWidth>
                    <FormLabel sx={{ fontWeight: 600, fontSize: '0.875rem', mb: 1, color: '#334155' }}>
                      STEP 2 — How should students attempt this assessment?
                    </FormLabel>
                    <RadioGroup 
                      value={deliveryMode} 
                      onChange={e => setDeliveryMode(e.target.value as 'ENTIRE' | 'SECTION')}
                    >
                      <Paper variant="outlined" sx={{ p: 1.5, mb: 1, borderColor: deliveryMode === 'ENTIRE' ? '#2563eb' : '#e2e8f0', bgcolor: deliveryMode === 'ENTIRE' ? '#eff6ff' : '#fff' }}>
                        <FormControlLabel 
                          value="ENTIRE" 
                          control={<Radio size="small" />} 
                          label={
                            <Box>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>Entire Assessment</Typography>
                              <Typography variant="caption" color="text.secondary">Single overall timer for the entire assessment</Typography>
                            </Box>
                          } 
                        />
                      </Paper>
                      <Paper variant="outlined" sx={{ p: 1.5, borderColor: deliveryMode === 'SECTION' ? '#2563eb' : '#e2e8f0', bgcolor: deliveryMode === 'SECTION' ? '#eff6ff' : '#fff' }}>
                        <FormControlLabel 
                          value="SECTION" 
                          control={<Radio size="small" />} 
                          label={
                            <Box>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>Section Based</Typography>
                              <Typography variant="caption" color="text.secondary">Independent timing & lock per section</Typography>
                            </Box>
                          } 
                        />
                      </Paper>
                    </RadioGroup>

                    {/* Delivery Timing Options */}
                    {deliveryMode === 'ENTIRE' && (
                      <Paper variant="outlined" sx={{ p: 2, mt: 2, bgcolor: '#f1f5f9' }}>
                        <Grid container spacing={2} alignItems="center">
                          <Grid item xs={12} sm={6}>
                            <TextField
                              fullWidth
                              size="small"
                              label="Total Assessment Time (minutes)"
                              type="number"
                              value={totalAssessmentTime}
                              onChange={e => setTotalAssessmentTime(e.target.value === '' ? '' : parseInt(e.target.value) || 0)}
                            />
                          </Grid>
                          <Grid item xs={12} sm={6}>
                            <FormControlLabel
                              control={
                                <Switch
                                  checked={autoSubmitOnTimeout}
                                  onChange={e => setAutoSubmitOnTimeout(e.target.checked)}
                                  size="small"
                                />
                              }
                              label={<Typography variant="body2">Auto Submit on Timeout</Typography>}
                            />
                          </Grid>
                        </Grid>
                      </Paper>
                    )}
                  </FormControl>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* STEP 3 - 8: Sections List */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 700, color: '#1e293b', display: 'flex', alignItems: 'center', gap: 1 }}>
              <QuizIcon color="primary" fontSize="small" />
              Assessment Sections ({sections.length})
            </Typography>
            <Button 
              variant="contained" 
              startIcon={<AddCircleIcon />} 
              onClick={() => addSection()}
              sx={{ bgcolor: '#0f172a', '&:hover': { bgcolor: '#334155' } }}
            >
              Add Section
            </Button>
          </Box>

          {sections.length === 0 && (
            <Paper variant="outlined" sx={{ p: 4, textAlign: 'center', borderColor: '#cbd5e1', bgcolor: '#fff' }}>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                No sections created yet. Click "Add Section" to create Section A.
              </Typography>
              <Button variant="outlined" startIcon={<AddCircleIcon />} onClick={() => addSection()}>
                Create Section A
              </Button>
            </Paper>
          )}

          {sections.map((sec, sIndex) => {
            const secMarks = calculateSectionMarks(sec);
            return (
              <Card key={sIndex} variant="outlined" sx={{ borderRadius: 2, borderColor: '#cbd5e1', bgcolor: '#fff' }}>
                <CardContent sx={{ p: 3 }}>
                  {/* Section Header Controls */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2.5, flexWrap: 'wrap', gap: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexGrow: 1, flexWrap: 'wrap' }}>
                      <Chip label={`Section ${String.fromCharCode(65 + sIndex)}`} color="primary" sx={{ fontWeight: 700 }} />
                      
                      <TextField
                        size="small"
                        label="Section Name"
                        value={sec.section_name}
                        onChange={e => {
                          const upd = [...sections];
                          upd[sIndex].section_name = e.target.value;
                          setSections(upd);
                        }}
                        sx={{ minWidth: 180 }}
                      />

                      {/* Section Type Selector for Mixed Mode */}
                      {assessmentType === 'MIXED' && (
                        <FormControl size="small" sx={{ minWidth: 160 }}>
                          <Select
                            value={sec.section_type}
                            onChange={e => handleSectionTypeChange(sIndex, e.target.value as 'MCQ' | 'SUBJECTIVE')}
                          >
                            <MenuItem value="MCQ">MCQ Section</MenuItem>
                            <MenuItem value="SUBJECTIVE">Subjective Section</MenuItem>
                          </Select>
                        </FormControl>
                      )}

                      <TextField
                        size="small"
                        label={sec.section_type === 'MCQ' ? 'Number of MCQs' : 'Number of Questions'}
                        type="number"
                        value={sec.question_count}
                        onChange={e => handleQuestionCountChange(sIndex, parseInt(e.target.value) || 0)}
                        sx={{ width: 170 }}
                        helperText="Generates items automatically"
                      />

                      <Chip 
                        icon={<DescriptionIcon fontSize="small" />} 
                        label={`Section Total: ${secMarks} Marks`} 
                        variant="outlined"
                        color={sec.section_type === 'MCQ' ? 'primary' : 'secondary'}
                        sx={{ fontWeight: 600 }}
                      />
                    </Box>
                    <IconButton color="error" onClick={() => removeSection(sIndex)}>
                      <DeleteIcon />
                    </IconButton>
                  </Box>

                  <Divider sx={{ my: 2 }} />

                  {/* Section Presentation & Anti-Cheating Settings */}
                  <Grid container spacing={2} sx={{ mb: 3, bgcolor: '#f8fafc', p: 2, borderRadius: 1.5, border: '1px solid #e2e8f0' }}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="body2" sx={{ fontWeight: 600, mb: 1, color: '#475569' }}>
                        STEP 5 — Question Presentation
                      </Typography>
                      <RadioGroup 
                        row 
                        value={sec.presentation} 
                        onChange={e => {
                          const upd = [...sections];
                          upd[sIndex].presentation = e.target.value as 'SHOW_ENTIRE' | 'ONE_AT_A_TIME';
                          setSections(upd);
                        }}
                      >
                        <FormControlLabel value="SHOW_ENTIRE" control={<Radio size="small" />} label={<Typography variant="body2">Show Entire Section</Typography>} />
                        <FormControlLabel value="ONE_AT_A_TIME" control={<Radio size="small" />} label={<Typography variant="body2">One Question At A Time</Typography>} />
                      </RadioGroup>
                    </Grid>

                    {/* Section Timing (If Section-Based Delivery) */}
                    {deliveryMode === 'SECTION' && (
                      <Grid item xs={12} md={6}>
                        <Typography variant="body2" sx={{ fontWeight: 600, mb: 1, color: '#475569', display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <TimerIcon fontSize="inherit" /> STEP 6 — Section Timing
                        </Typography>
                        <TextField
                          size="small"
                          label="Section Duration (minutes)"
                          type="number"
                          value={sec.section_duration_minutes ?? ''}
                          onChange={e => {
                            const upd = [...sections];
                            const val = e.target.value;
                            upd[sIndex].section_duration_minutes = val === '' ? null : parseInt(val) || null;
                            setSections(upd);
                          }}
                          sx={{ width: 220 }}
                        />
                      </Grid>
                    )}

                    {/* Anti-Cheating Options */}
                    <Grid item xs={12}>
                      <Typography variant="body2" sx={{ fontWeight: 600, mb: 1, color: '#475569', display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <SecurityIcon fontSize="inherit" /> STEP 7 — Anti-Cheating Options
                      </Typography>
                      <Stack direction="row" spacing={3}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={sec.randomize_questions}
                              onChange={e => {
                                const upd = [...sections];
                                upd[sIndex].randomize_questions = e.target.checked;
                                setSections(upd);
                              }}
                              size="small"
                            />
                          }
                          label={<Typography variant="body2">Randomize Question Order</Typography>}
                        />
                        {sec.section_type === 'MCQ' && (
                          <FormControlLabel
                            control={
                              <Switch
                                checked={Boolean(sec.randomize_options)}
                                onChange={e => {
                                  const upd = [...sections];
                                  upd[sIndex].randomize_options = e.target.checked;
                                  setSections(upd);
                                }}
                                size="small"
                              />
                            }
                            label={<Typography variant="body2">Randomize MCQ Options</Typography>}
                          />
                        )}
                      </Stack>
                    </Grid>
                  </Grid>

                  {/* STEP 8: Question Authoring - Orchestrates MCQ vs Subjective */}
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 2, color: '#334155' }}>
                    STEP 8 — Question Authoring ({sec.question_rules.length} {sec.section_type === 'MCQ' ? 'MCQs' : 'Questions'})
                  </Typography>

                  <Stack spacing={2}>
                    {sec.question_rules.map((q, qIndex) => (
                      <Paper key={qIndex} variant="outlined" sx={{ p: 2, borderColor: '#e2e8f0', bgcolor: '#fff' }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1.5, alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
                          <Typography variant="body2" sx={{ fontWeight: 700, color: sec.section_type === 'MCQ' ? '#2563eb' : '#7c3aed' }}>
                            {sec.section_type === 'MCQ' ? `MCQ ${qIndex + 1}` : `Question ${qIndex + 1}`}
                          </Typography>

                          <Box display="flex" alignItems="center" gap={2}>
                            {sec.section_type === 'SUBJECTIVE' && (
                              <FormControl size="small" sx={{ minWidth: 150 }}>
                                <Select
                                  value={q.question_type || 'SHORT_ANSWER'}
                                  onChange={e => {
                                    const upd = [...sections];
                                    upd[sIndex].question_rules[qIndex].question_type = e.target.value;
                                    setSections(upd);
                                  }}
                                >
                                  <MenuItem value="SHORT_ANSWER">Short Answer</MenuItem>
                                  <MenuItem value="LONG_ANSWER">Long Answer</MenuItem>
                                  <MenuItem value="ESSAY">Essay</MenuItem>
                                </Select>
                              </FormControl>
                            )}

                            <TextField
                              size="small"
                              label="Marks"
                              type="number"
                              value={q.marks ?? 1}
                              onChange={e => {
                                const upd = [...sections];
                                const val = parseInt(e.target.value);
                                upd[sIndex].question_rules[qIndex].marks = isNaN(val) ? 1 : Math.max(1, val);
                                setSections(upd);
                              }}
                              inputProps={{ min: 1 }}
                              sx={{ width: 100 }}
                            />
                          </Box>
                        </Box>

                        <TextField
                          fullWidth
                          multiline
                          minRows={2}
                          size="small"
                          label="Question Text"
                          placeholder={`Enter prompt for question ${qIndex + 1}...`}
                          value={q.question_text}
                          onChange={e => {
                            const upd = [...sections];
                            upd[sIndex].question_rules[qIndex].question_text = e.target.value;
                            setSections(upd);
                          }}
                          sx={{ mb: 2 }}
                        />

                        {/* Subjective Question Fields (Rendered if section_type === 'SUBJECTIVE') */}
                        {sec.section_type === 'SUBJECTIVE' && (
                          <Grid container spacing={2}>
                            <Grid item xs={12} md={6}>
                              <TextField
                                fullWidth
                                multiline
                                minRows={1}
                                size="small"
                                label="Instructions (Optional)"
                                placeholder="Special guidelines or formatting requirements..."
                                value={q.instructions || ''}
                                onChange={e => {
                                  const upd = [...sections];
                                  upd[sIndex].question_rules[qIndex].instructions = e.target.value;
                                  setSections(upd);
                                }}
                              />
                            </Grid>
                            <Grid item xs={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Word Limit (Optional)"
                                type="number"
                                value={q.word_limit ?? ''}
                                onChange={e => {
                                  const upd = [...sections];
                                  const val = e.target.value;
                                  upd[sIndex].question_rules[qIndex].word_limit = val === '' ? null : parseInt(val) || null;
                                  setSections(upd);
                                }}
                              />
                            </Grid>
                            <Grid item xs={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Minimum Words (Optional)"
                                type="number"
                                value={q.min_words ?? ''}
                                onChange={e => {
                                  const upd = [...sections];
                                  const val = e.target.value;
                                  upd[sIndex].question_rules[qIndex].min_words = val === '' ? null : parseInt(val) || null;
                                  setSections(upd);
                                }}
                              />
                            </Grid>
                          </Grid>
                        )}

                        {/* MCQ Options (Rendered if section_type === 'MCQ') */}
                        {sec.section_type === 'MCQ' && (
                          <Box sx={{ mt: 1 }}>
                            <Typography variant="caption" sx={{ fontWeight: 600, color: '#64748b', display: 'block', mb: 1 }}>
                              Options (Toggle switch marks the Correct Answer for automated grading)
                            </Typography>
                            
                            <Grid container spacing={1.5}>
                              {q.options.map((opt, oIndex) => (
                                <Grid item xs={12} sm={6} key={oIndex}>
                                  <Paper variant="outlined" sx={{ p: 1, display: 'flex', alignItems: 'center', gap: 1, borderColor: opt.is_correct ? '#22c55e' : '#e2e8f0', bgcolor: opt.is_correct ? '#f0fdf4' : '#fff' }}>
                                    <Tooltip title={opt.is_correct ? 'Correct Answer' : 'Mark as Correct Answer'}>
                                      <Switch
                                        size="small"
                                        color="success"
                                        checked={opt.is_correct}
                                        onChange={e => {
                                          const upd = [...sections];
                                          const currentOpts = upd[sIndex].question_rules[qIndex].options;
                                          currentOpts.forEach((o, idx) => {
                                            o.is_correct = idx === oIndex ? e.target.checked : false;
                                          });
                                          setSections(upd);
                                        }}
                                      />
                                    </Tooltip>
                                    <TextField
                                      size="small"
                                      fullWidth
                                      variant="standard"
                                      placeholder={`Option ${String.fromCharCode(65 + oIndex)}`}
                                      value={opt.option_text}
                                      onChange={e => {
                                        const upd = [...sections];
                                        upd[sIndex].question_rules[qIndex].options[oIndex].option_text = e.target.value;
                                        setSections(upd);
                                      }}
                                      InputProps={{ disableUnderline: true }}
                                    />
                                  </Paper>
                                </Grid>
                              ))}
                            </Grid>
                          </Box>
                        )}
                      </Paper>
                    ))}
                  </Stack>

                  <Button 
                    size="small" 
                    startIcon={<AddCircleIcon />} 
                    onClick={() => addSingleQuestion(sIndex)}
                    sx={{ mt: 2 }}
                  >
                    Add {sec.section_type === 'MCQ' ? 'MCQ' : 'Subjective'} Item
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </Stack>
      </Box>
    </Box>
  );
};

export default AssessmentBuilderUI;
