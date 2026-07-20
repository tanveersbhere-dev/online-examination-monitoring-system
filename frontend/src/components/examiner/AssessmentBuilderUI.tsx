import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Stack, Card, CardContent, TextField, IconButton, Divider, CircularProgress, Alert, Switch, FormControlLabel } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddCircleIcon from '@mui/icons-material/AddCircle';
import SaveIcon from '@mui/icons-material/Save';
import apiClient from '../../services/apiClient';

interface Props {
  paperId: number;
  onClose: () => void;
}

const AssessmentBuilderUI: React.FC<Props> = ({ paperId, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [groups, setGroups] = useState<any[]>([]);

  useEffect(() => {
    fetchPaper();
  }, [paperId]);

  const fetchPaper = async () => {
    try {
      const res = await apiClient.get(`/question-paper-builder/${paperId}/full`);
      setGroups(res.data.section_rules || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load paper details');
    } finally {
      setLoading(false);
    }
  };

  const addGroup = () => {
    setGroups([...groups, {
      section_index: groups.length + 1,
      section_name: `Group ${groups.length + 1}`,
      section_type: 'MCQ',
      section_duration_minutes: null,
      question_rules: []
    }]);
  };

  const addQuestion = (gIndex: number) => {
    const updated = [...groups];
    updated[gIndex].question_rules.push({
      question_index: updated[gIndex].question_rules.length + 1,
      question_type: 'MCQ',
      marks: 1,
      is_required: true,
      question_text: '',
      options: [
        { option_text: 'Option A', is_correct: true },
        { option_text: 'Option B', is_correct: false }
      ]
    });
    setGroups(updated);
  };

  const updateQuestionText = (gIndex: number, qIndex: number, val: string) => {
    const updated = [...groups];
    updated[gIndex].question_rules[qIndex].question_text = val;
    setGroups(updated);
  };

  const saveAll = async () => {
    setSaving(true);
    try {
      for (const group of groups) {
        let groupId = group.id;
        if (!groupId) {
          const res = await apiClient.post(`/question-paper-builder/${paperId}/groups`, group);
          groupId = res.data.id;
          group.id = groupId;
        } else {
          await apiClient.put(`/question-paper-builder/${paperId}/groups/${groupId}`, group);
        }
        
        for (const q of group.question_rules) {
          if (!q.id) {
            await apiClient.post(`/question-paper-builder/${paperId}/groups/${groupId}/questions`, q);
          } else {
            await apiClient.put(`/question-paper-builder/${paperId}/groups/${groupId}/questions/${q.id}`, q);
          }
        }
      }
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Box sx={{ p: 4, textAlign: 'center' }}><CircularProgress /></Box>;

  return (
    <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h5">Assessment Builder</Typography>
        <Button variant="contained" startIcon={<SaveIcon />} onClick={saveAll} disabled={saving}>
          {saving ? 'Saving...' : 'Save Assessment'}
        </Button>
      </Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      
      <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
        {groups.map((g, gIndex) => (
          <Card key={gIndex} sx={{ mb: 3, border: '1px solid #ddd' }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <TextField 
                  label="Group Name" 
                  value={g.section_name} 
                  onChange={e => {
                    const upd = [...groups];
                    upd[gIndex].section_name = e.target.value;
                    setGroups(upd);
                  }}
                  size="small"
                />
                <Button size="small" startIcon={<AddCircleIcon />} onClick={() => addQuestion(gIndex)}>Add Question</Button>
              </Box>
              
              <Divider sx={{ my: 2 }} />
              
              <Stack spacing={2}>
                {g.question_rules.map((q: any, qIndex: number) => (
                  <Card key={qIndex} variant="outlined" sx={{ p: 2 }}>
                    <Box sx={{ display: 'flex', gap: 2 }}>
                      <TextField 
                        fullWidth 
                        multiline 
                        minRows={2} 
                        label={`Question ${qIndex + 1} Text`} 
                        value={q.question_text} 
                        onChange={e => updateQuestionText(gIndex, qIndex, e.target.value)}
                      />
                      <Box>
                        <TextField 
                          label="Marks" 
                          type="number" 
                          size="small" 
                          sx={{ width: 80 }} 
                          value={q.marks}
                          onChange={e => {
                            const upd = [...groups];
                            upd[gIndex].question_rules[qIndex].marks = parseInt(e.target.value) || 1;
                            setGroups(upd);
                          }}
                        />
                      </Box>
                    </Box>
                    
                    {q.options && q.options.length > 0 && (
                      <Box sx={{ mt: 2, pl: 2 }}>
                        <Typography variant="caption" color="text.secondary">Options (Correct Answer marked with toggle)</Typography>
                        {q.options.map((opt: any, oIndex: number) => (
                          <Box key={oIndex} sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                            <Switch 
                              checked={opt.is_correct} 
                              onChange={e => {
                                const upd = [...groups];
                                upd[gIndex].question_rules[qIndex].options[oIndex].is_correct = e.target.checked;
                                setGroups(upd);
                              }}
                              size="small"
                            />
                            <TextField 
                              size="small" 
                              value={opt.option_text}
                              onChange={e => {
                                const upd = [...groups];
                                upd[gIndex].question_rules[qIndex].options[oIndex].option_text = e.target.value;
                                setGroups(upd);
                              }}
                              fullWidth
                            />
                            <IconButton color="error" size="small" onClick={() => {
                                const upd = [...groups];
                                upd[gIndex].question_rules[qIndex].options.splice(oIndex, 1);
                                setGroups(upd);
                            }}><DeleteIcon fontSize="small" /></IconButton>
                          </Box>
                        ))}
                        <Button size="small" sx={{ mt: 1 }} onClick={() => {
                          const upd = [...groups];
                          upd[gIndex].question_rules[qIndex].options.push({ option_text: '', is_correct: false });
                          setGroups(upd);
                        }}>Add Option</Button>
                      </Box>
                    )}
                  </Card>
                ))}
              </Stack>
            </CardContent>
          </Card>
        ))}
        
        <Button variant="outlined" startIcon={<AddCircleIcon />} onClick={addGroup} fullWidth>
          Add Question Group
        </Button>
      </Box>
    </Box>
  );
};

export default AssessmentBuilderUI;
