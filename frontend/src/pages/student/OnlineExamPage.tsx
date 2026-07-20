import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  Divider,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  LinearProgress,
  Tooltip,
  AppBar,
  Toolbar,
  CircularProgress
} from '@mui/material';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import FlagIcon from '@mui/icons-material/Flag';
import SendIcon from '@mui/icons-material/Send';
import TimerIcon from '@mui/icons-material/Timer';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import VideocamIcon from '@mui/icons-material/Videocam';
import VideocamOffIcon from '@mui/icons-material/VideocamOff';
import apiClient from '../../services/apiClient';
import { WebSocketClient } from '../../services/wsClient';

interface Question {
  id: string;
  question_index: number;
  question_type: string;
  text: string;
  options: string[];
}

interface Section {
  id: string;
  section_index: number;
  section_name: string;
  section_type: string;
  questions: Question[];
}

const OnlineExamPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const examId = searchParams.get('exam_id') || '1';

  const [sections, setSections] = useState<Section[]>([]);
  const [mode, setMode] = useState<string>('STRUCTURED');
  const [fileUrl, setFileUrl] = useState<string>('');
  
  const [loading, setLoading] = useState(true);
  const [identityVerified, setIdentityVerified] = useState(false);
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [identityError, setIdentityError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  
  const [currentSectionIdx, setCurrentSectionIdx] = useState(0);
  const [currentQ, setCurrentQ] = useState(0);
  
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [flagged, setFlagged] = useState<Set<string>>(new Set());
  const [submitOpen, setSubmitOpen] = useState(false);
  const [saved, setSaved] = useState(false);
  
  const [timeLeft, setTimeLeft] = useState(7200); // 2 hours default
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const wsRef = useRef<WebSocketClient | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const examSessionIdRef = useRef<number | null>(null);

  // 1. Initial Camera Request
  useEffect(() => {
    let localStream: MediaStream | null = null;
    const initCamera = async () => {
      try {
        const st = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        localStream = st;
        setStream(st);
        setCameraActive(true);
        setLoading(false);
      } catch (camErr) {
        console.error("Camera access denied", camErr);
        setPermissionError("Camera permission is mandatory to start the exam. Please allow camera access and refresh the page.");
        setLoading(false);
      }
    };
    initCamera();
    
    return () => {
      if (localStream) {
        localStream.getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  const handleVerifyIdentity = async () => {
    if (!videoRef.current) return;
    setVerifying(true);
    setIdentityError(null);
    try {
      const canvas = document.createElement('canvas');
      canvas.width = 640;
      canvas.height = 480;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
        const base64Frame = canvas.toDataURL('image/jpeg', 0.8);
        
        const res = await apiClient.post(`/runtime/verify-identity`, {
          exam_id: parseInt(examId),
          image_base64: base64Frame
        });
        
        if (res.data.verified) {
          setIdentityVerified(true);
          startExamSession();
        } else {
          setIdentityError("Identity mismatch. Please ensure your face is clearly visible and matches your enrolled profile.");
        }
      }
    } catch (e: any) {
      setIdentityError(e.response?.data?.detail || "Failed to verify identity. Please try again.");
    } finally {
      setVerifying(false);
    }
  };

  const startExamSession = async () => {
    try {
      setLoading(true);
      const res = await apiClient.post(`/runtime/start?exam_id=${examId}`);
      const data = res.data;
      
      examSessionIdRef.current = data.session.id;
      setMode(data.mode || 'STRUCTURED');
      if (data.mode === 'FILE') {
        setFileUrl(data.file_url || '');
      } else {
        setSections(data.sections || []);
      }
      
      setTimeLeft(data.time_left_seconds || 7200);
      
      try {
        const stateRes = await apiClient.get(`/runtime/state?exam_id=${examId}`);
        if (stateRes.data && stateRes.data.current_question_index !== undefined) {
           setCurrentQ(stateRes.data.current_question_index);
           setCurrentSectionIdx(stateRes.data.current_section_index !== undefined ? stateRes.data.current_section_index : 0);
        }
        const ansRes = await apiClient.get(`/runtime/answers?exam_id=${examId}`);
        if (ansRes.data && Array.isArray(ansRes.data)) {
           const ansMap: Record<string, number> = {};
           ansRes.data.forEach((a: any) => {
              let qId = null;
              if (data.sections) {
                for (const s of data.sections) {
                  if (s.section_index === a.section_index) {
                    const q = s.questions.find((q: Question) => q.question_index === a.question_index);
                    if (q) qId = q.id;
                  }
                }
              }
              if (qId && a.answer_data && a.answer_data.selected !== undefined) {
                ansMap[qId] = a.answer_data.selected;
              }
           });
           setAnswers(ansMap);
        }
      } catch(e) {
        console.warn("Failed to hydrate state or answers", e);
      }
      
      const ws = new WebSocketClient(parseInt(examId));
      wsRef.current = ws;
      ws.connect();
      
    } catch (err) {
      console.error("Failed to initialize exam", err);
    } finally {
      setLoading(false);
    }
  };

  // 3. Timers and Heartbeats (only when identity verified)
  useEffect(() => {
    if (!identityVerified) return;

    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          handleSubmit();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    const heartbeat = setInterval(async () => {
      try {
        await apiClient.post(`/runtime/heartbeat?exam_id=${examId}`);
      } catch (e) {
        console.error("Heartbeat failed", e);
      }
    }, 60000);

    const frameCapture = setInterval(() => {
      if (videoRef.current && videoRef.current.readyState === videoRef.current.HAVE_ENOUGH_DATA) {
        try {
          const canvas = document.createElement('canvas');
          canvas.width = 320;
          canvas.height = 240;
          const ctx = canvas.getContext('2d');
          if (ctx) {
            ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
            const base64Frame = canvas.toDataURL('image/jpeg', 0.5);
            
            if (examSessionIdRef.current) {
              apiClient.post(`/runtime/frame?exam_id=${examId}`, {
                image_base64: base64Frame
              }).catch(() => {});
            }
          }
        } catch (e) {
          console.error("Frame capture failed", e);
        }
      }
    }, 2000); // Send frame every 2 seconds

    return () => {
      clearInterval(timer);
      clearInterval(heartbeat);
      clearInterval(frameCapture);
      if (wsRef.current) wsRef.current.disconnect();
    };
  }, [identityVerified, examId]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center' }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>{identityVerified ? "Initializing Examination Environment..." : "Requesting Camera Access..."}</Typography>
      </Box>
    );
  }

  if (permissionError) {
    return (
      <Box sx={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
        <Typography color="error" variant="h6" gutterBottom>{permissionError}</Typography>
        <Button variant="contained" onClick={() => window.location.reload()}>Retry</Button>
      </Box>
    );
  }

  if (!identityVerified) {
    return (
      <Box sx={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
        <Paper elevation={3} sx={{ p: 4, textAlign: 'center', maxWidth: 600, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <Typography variant="h5" gutterBottom>Identity Verification</Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Please position your face clearly in the camera to verify your identity before starting the exam.
          </Typography>
          <Box
            sx={{
              width: 320, height: 240,
              backgroundColor: '#0A0A0A',
              borderRadius: 2,
              mb: 3,
              overflow: 'hidden',
              position: 'relative'
            }}
          >
            <video
              ref={(el) => {
                if (el && stream) {
                  el.srcObject = stream;
                }
                // @ts-ignore
                videoRef.current = el;
              }}
              autoPlay
              playsInline
              muted
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          </Box>
          {identityError && (
            <Typography color="error" sx={{ mb: 2 }}>{identityError}</Typography>
          )}
          <Button 
            variant="contained" 
            size="large" 
            onClick={handleVerifyIdentity} 
            disabled={verifying}
          >
            {verifying ? <CircularProgress size={24} color="inherit" /> : "Verify Identity & Start Exam"}
          </Button>
        </Paper>
      </Box>
    );
  }

  if (mode === 'STRUCTURED' && sections.length === 0) {
    return (
      <Box sx={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center' }}>
        <Typography color="error">Failed to load exam sections. Please contact administrator.</Typography>
      </Box>
    );
  }

  let totalQuestions = 0;
  if (mode === 'STRUCTURED') {
    totalQuestions = sections.reduce((acc, sec) => acc + sec.questions.length, 0);
  }

  const answeredCount = Object.keys(answers).length;
  const flaggedCount = flagged.size;
  const remaining = mode === 'STRUCTURED' ? totalQuestions - answeredCount : 0;

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleNavigation = async (targetSecIdx: number, targetQIdx: number) => {
    try {
      await apiClient.put(`/runtime/state/position?exam_id=${examId}&section_index=${targetSecIdx}&question_index=${targetQIdx}`);
      setCurrentSectionIdx(targetSecIdx);
      setCurrentQ(targetQIdx);
    } catch (err: any) {
      alert("Navigation blocked: " + (err.response?.data?.detail || err.message));
    }
  };

  const currentSection = sections.length > 0 ? sections[currentSectionIdx] : null;
  const question = currentSection && currentSection.questions.length > 0 ? currentSection.questions[currentQ] : null;

  const handleAnswer = async (value: string) => {
    if (!question) return;
    const numericVal = parseInt(value);
    try {
      await apiClient.post(`/runtime/answers/${currentSectionIdx}/${currentQ}?exam_id=${examId}`, {
        answer_data: { selected: numericVal },
        is_submitted: false
      });
      setAnswers((prev) => ({ ...prev, [question.id]: numericVal }));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err: any) {
      alert("Failed to save answer: " + (err.response?.data?.detail || err.message));
    }
  };

  const toggleFlag = () => {
    if (!question) return;
    setFlagged((prev) => {
      const next = new Set(prev);
      next.has(question.id) ? next.delete(question.id) : next.add(question.id);
      return next;
    });
  };

  const handleSubmit = async () => {
    try {
      await apiClient.post(`/runtime/submit?exam_id=${examId}`);
      setSubmitOpen(false);
      navigate('/student/submitted');
    } catch (err) {
      console.error("Failed to submit exam", err);
      navigate('/student/submitted');
    }
  };

  const getQuestionButtonSx = (qId: string, isCurrent: boolean) => {
    const isAnswered = answers[qId] !== undefined;
    const isFlagged = flagged.has(qId);
    return {
      width: 40, height: 40, minWidth: 40, p: 0,
      borderRadius: 1.5,
      fontSize: '0.8rem',
      fontWeight: 600,
      border: isCurrent ? '2px solid' : '1px solid',
      borderColor: isCurrent ? 'primary.main' : isAnswered ? 'primary.main' : isFlagged ? 'warning.main' : 'divider',
      backgroundColor: isCurrent ? 'primary.main' : isAnswered ? '#E3F2FD' : isFlagged ? '#FFF3E0' : 'background.paper',
      color: isCurrent ? 'white' : isAnswered ? 'primary.main' : isFlagged ? 'warning.main' : 'text.secondary',
      '&:hover': { backgroundColor: isCurrent ? 'primary.dark' : 'action.hover' },
    };
  };

  const goNext = () => {
    if (mode !== 'STRUCTURED' || !currentSection) return;
    if (currentQ < currentSection.questions.length - 1) {
      handleNavigation(currentSectionIdx, currentQ + 1);
    } else if (currentSectionIdx < sections.length - 1) {
      handleNavigation(currentSectionIdx + 1, 0);
    }
  };

  const goPrev = () => {
    if (mode !== 'STRUCTURED' || !currentSection) return;
    if (currentQ > 0) {
      handleNavigation(currentSectionIdx, currentQ - 1);
    } else if (currentSectionIdx > 0) {
      const prevSec = sections[currentSectionIdx - 1];
      handleNavigation(currentSectionIdx - 1, prevSec.questions.length - 1);
    }
  };

  const isFirst = currentSectionIdx === 0 && currentQ === 0;
  const isLast = mode === 'STRUCTURED' && currentSectionIdx === sections.length - 1 && currentSection && currentQ === currentSection.questions.length - 1;

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Exam Top Bar */}
      <AppBar position="sticky" elevation={0} sx={{ backgroundColor: 'primary.dark', color: 'white' }}>
        <Toolbar sx={{ gap: 2 }}>
          <Typography variant="subtitle1" fontWeight={600} sx={{ flexGrow: 0, mr: 2, display: { xs: 'none', sm: 'block' } }}>
            Online Examination (ID: {examId})
          </Typography>
          <Box sx={{ flexGrow: 1, textAlign: 'center' }}>
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              {mode === 'STRUCTURED' ? `Section: ${currentSection?.section_name} | Q${currentQ + 1}` : 'FILE Mode'}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <TimerIcon fontSize="small" sx={{ color: timeLeft < 300 ? 'error.main' : 'inherit' }} />
            <Typography variant="subtitle1" fontWeight={700} sx={{ fontFamily: 'monospace', color: timeLeft < 300 ? 'error.main' : 'inherit' }}>
              {formatTime(timeLeft)}
            </Typography>
          </Box>
        </Toolbar>
        {mode === 'STRUCTURED' && totalQuestions > 0 && (
          <LinearProgress
            variant="determinate"
            value={(answeredCount / totalQuestions) * 100}
            sx={{ height: 2, backgroundColor: 'rgba(255,255,255,0.2)', '& .MuiLinearProgress-bar': { backgroundColor: 'rgba(255,255,255,0.7)' } }}
          />
        )}
      </AppBar>

      <Box sx={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
        {/* Left Navigation Panel */}
        <Paper
          elevation={0}
          sx={{
            width: 260, flexShrink: 0,
            borderRight: '1px solid', borderColor: 'divider',
            borderRadius: 0,
            backgroundColor: '#F8FAFC',
            display: { xs: 'none', md: 'flex' },
            flexDirection: 'column',
            p: 2,
            overflowY: 'auto',
          }}
        >
          {mode === 'STRUCTURED' ? (
            <>
              <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1.5, textTransform: 'uppercase', letterSpacing: 1 }}>
                Sections & Questions
              </Typography>
              
              {sections.map((sec, sIdx) => (
                <Box key={sec.id} sx={{ mb: 2 }}>
                  <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
                    {sec.section_name}
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {sec.questions.map((q, qIdx) => {
                      const isCurrent = currentSectionIdx === sIdx && currentQ === qIdx;
                      return (
                        <Button
                          key={q.id}
                          onClick={() => handleNavigation(sIdx, qIdx)}
                          sx={getQuestionButtonSx(q.id, isCurrent)}
                        >
                          {q.question_index + 1}
                        </Button>
                      );
                    })}
                  </Box>
                </Box>
              ))}

              <Divider sx={{ mb: 2 }} />

              {/* Stats */}
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75, mb: 3 }}>
                <Typography variant="caption" sx={{ color: 'success.main', fontWeight: 600 }}>
                  ✓ Answered: {answeredCount}
                </Typography>
                <Typography variant="caption" sx={{ color: 'warning.main', fontWeight: 600 }}>
                  ⚑ Flagged: {flaggedCount}
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600 }}>
                  ○ Remaining: {remaining}
                </Typography>
              </Box>
            </>
          ) : (
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1.5, textTransform: 'uppercase', letterSpacing: 1 }}>
                Examination File
              </Typography>
              <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                Please review the document and submit your answers according to the provided instructions.
              </Typography>
            </Box>
          )}

          <Box sx={{ flexGrow: 1 }} />

          {/* Camera Preview */}
          <Box>
            <Divider sx={{ mb: 1.5 }} />
            <Box
              sx={{
                width: '100%', height: 110,
                backgroundColor: '#0A0A0A',
                borderRadius: 2,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              <video
                ref={(el) => {
                  if (el && stream) {
                    el.srcObject = stream;
                  }
                  // @ts-ignore
                  videoRef.current = el;
                }}
                autoPlay
                playsInline
                muted
                style={{ width: '100%', height: '100%', objectFit: 'cover', display: cameraActive ? 'block' : 'none' }}
              />
              {!cameraActive && <VideocamOffIcon sx={{ color: 'rgba(255,255,255,0.15)', fontSize: 40 }} />}
              <Box sx={{ position: 'absolute', top: 6, right: 6, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <FiberManualRecordIcon sx={{ color: '#F44336', fontSize: 8 }} />
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.6rem' }}>LIVE</Typography>
              </Box>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: 0.5 }}>
              ● Monitored By AI
            </Typography>
          </Box>
        </Paper>

        {/* Content Panel */}
        <Box sx={{ flexGrow: 1, overflow: 'auto', p: { xs: 2, md: 4 } }}>
          {mode === 'FILE' ? (
            <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
              <iframe 
                src={`${apiClient.defaults.baseURL}${fileUrl}`} 
                style={{ width: '100%', flexGrow: 1, border: 'none', borderRadius: '8px' }}
                title="Examination Document"
              />
            </Box>
          ) : question && (
            <Box sx={{ maxWidth: 720, mx: 'auto' }}>
              {/* Auto-save indicator */}
              <Box sx={{ textAlign: 'right', mb: 1, minHeight: 20 }}>
                {saved && (
                  <Typography variant="caption" sx={{ color: 'success.main', fontWeight: 600 }}>
                    ✓ Saved
                  </Typography>
                )}
              </Box>

              <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                Section: {currentSection?.section_name} | Q {question.question_index + 1}
              </Typography>
              <Typography variant="h6" fontWeight={500} sx={{ mt: 1, mb: 3, lineHeight: 1.6 }}>
                {question.text}
              </Typography>

              {/* Options */}
              <FormControl fullWidth>
                <RadioGroup
                  value={answers[question.id] !== undefined ? String(answers[question.id]) : ''}
                  onChange={(e) => handleAnswer(e.target.value)}
                >
                  {question.options.map((opt, idx) => (
                    <Paper
                      key={idx}
                      elevation={0}
                      sx={{
                        mb: 1.5,
                        border: '1px solid',
                        borderColor: answers[question.id] === idx ? 'primary.main' : 'divider',
                        backgroundColor: answers[question.id] === idx ? 'primary.light' : 'background.paper',
                        borderRadius: 2,
                        transition: 'all 0.15s',
                        '&:hover': { borderColor: 'primary.light', backgroundColor: '#F5FAFF' },
                      }}
                    >
                      <FormControlLabel
                        value={String(idx)}
                        control={<Radio size="small" />}
                        label={<Typography variant="body1">{opt}</Typography>}
                        sx={{ px: 2, py: 1, width: '100%', m: 0 }}
                      />
                    </Paper>
                  ))}
                </RadioGroup>
              </FormControl>

              {/* Flag button */}
              <Button
                size="small"
                startIcon={<FlagIcon />}
                onClick={toggleFlag}
                sx={{
                  mt: 2,
                  color: flagged.has(question.id) ? 'warning.main' : 'text.secondary',
                  borderColor: flagged.has(question.id) ? 'warning.main' : 'divider',
                }}
                variant="outlined"
              >
                {flagged.has(question.id) ? 'Unflag Question' : 'Flag Question'}
              </Button>

              {/* Navigation */}
              <Divider sx={{ my: 3 }} />
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Button
                  variant="outlined"
                  startIcon={<NavigateBeforeIcon />}
                  disabled={isFirst}
                  onClick={goPrev}
                >
                  Previous
                </Button>
                {!isLast ? (
                  <Button
                    variant="contained"
                    endIcon={<NavigateNextIcon />}
                    onClick={goNext}
                  >
                    Next
                  </Button>
                ) : (
                  <Button
                    variant="contained"
                    color="success"
                    endIcon={<SendIcon />}
                    onClick={() => setSubmitOpen(true)}
                  >
                    Review & Submit
                  </Button>
                )}
              </Box>
            </Box>
          )}
        </Box>
      </Box>

      {/* Submit FAB */}
      <Tooltip title="Submit Exam" placement="left">
        <Button
          variant="contained"
          onClick={() => setSubmitOpen(true)}
          startIcon={<SendIcon />}
          sx={{
            position: 'fixed', bottom: 24, right: 24,
            boxShadow: 4, zIndex: 999,
            display: { xs: 'none', md: 'flex' },
          }}
        >
          Submit Exam
        </Button>
      </Tooltip>

      {/* Submit Confirmation Dialog */}
      <Dialog open={submitOpen} onClose={() => setSubmitOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle fontWeight={600}>Submit Examination?</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            {mode === 'STRUCTURED' && (
              <>
                <Chip label={`✓ Answered: ${answeredCount} of ${totalQuestions}`} color="success" variant="outlined" />
                <Chip label={`⚑ Flagged: ${flaggedCount} questions`} color="warning" variant="outlined" />
                <Chip label={`○ Unanswered: ${remaining}`} variant="outlined" />
              </>
            )}
            {mode === 'FILE' && (
               <Chip label="File Exam Complete" color="success" variant="outlined" />
            )}
          </Box>
          <DialogContentText sx={{ mt: 2 }}>
            Unanswered questions will be submitted as-is. This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2, gap: 1 }}>
          <Button onClick={() => setSubmitOpen(false)} variant="outlined">
            Cancel
          </Button>
          <Button onClick={handleSubmit} variant="contained" color="error">
            Submit Examination
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default OnlineExamPage;
