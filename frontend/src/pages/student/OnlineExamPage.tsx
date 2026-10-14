import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Radio,
  RadioGroup,
  Checkbox,
  FormGroup,
  FormControlLabel,
  FormControl,
  TextField,
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
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Stack,
  Snackbar
} from '@mui/material';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import FlagIcon from '@mui/icons-material/Flag';
import SendIcon from '@mui/icons-material/Send';
import TimerIcon from '@mui/icons-material/Timer';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import VideocamOffIcon from '@mui/icons-material/VideocamOff';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CloudDoneIcon from '@mui/icons-material/CloudDone';
import SyncIcon from '@mui/icons-material/Sync';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import RefreshIcon from '@mui/icons-material/Refresh';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import WifiOffIcon from '@mui/icons-material/WifiOff';
import WifiIcon from '@mui/icons-material/Wifi';
import LockIcon from '@mui/icons-material/Lock';
import HistoryEduIcon from '@mui/icons-material/HistoryEdu';

import apiClient from '../../services/apiClient';
import { WebSocketClient } from '../../services/wsClient';
import { useAuth } from '../../hooks/useAuth';
import { ExamEnvironmentMonitor } from '../../services/ExamEnvironmentMonitor';
import type { EnvViolationRecord } from '../../services/ExamEnvironmentMonitor';

interface Question {
  id: string;
  question_index: number;
  question_type: string;
  text: string;
  options: string[];
  marks?: number;
  image_url?: string;
  explanation?: string;
}

interface Section {
  id: string;
  section_index: number;
  section_name: string;
  section_type: string;
  section_duration_minutes?: number;
  navigation_policy?: string;
  allow_return_to_previous?: boolean;
  lock_after_timeout?: boolean;
  randomize_questions?: boolean;
  require_completion_before_next?: boolean;
  section_weight?: number;
  instructions?: string;
  questions: Question[];
}

interface AnswerData {
  selected?: number; // Single-choice MCQ
  selected_options?: number[]; // Multi-select MCQ
  text?: string; // Subjective / Essay / Short Answer
}

type SaveStatus = 'idle' | 'saving' | 'saved' | 'offline' | 'syncing' | 'error';

interface OfflineQueueItem {
  secIdx: number;
  qIdx: number;
  ansData: AnswerData;
  isFlagged: boolean;
}

interface TabLockClaim {
  tabId: string;
  userId: number | string;
  examId: string;
  timestamp: number;
}

type CameraVideoRole = 'identity' | 'monitoring';

interface VideoDiagnosticBinding {
  timer: ReturnType<typeof setInterval>;
  cleanup: () => void;
}

const OnlineExamPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const examId = searchParams.get('exam_id') || '1';
  const { user } = useAuth();
  const userId = user?.id || 'guest';

  const [sections, setSections] = useState<Section[]>([]);
  const [mode, setMode] = useState<string>('STRUCTURED');
  const [fileUrl, setFileUrl] = useState<string>('');
  const [examTitle, setExamTitle] = useState<string>('Online Examination');
  
  const [loading, setLoading] = useState(true);
  const [isAlreadySubmitted, setIsAlreadySubmitted] = useState(false);
  const [submissionCompletedMessage, setSubmissionCompletedMessage] = useState<string>('');
  
  const [permissionError, setPermissionError] = useState<string | null>(null);
  
  const [currentSectionIdx, setCurrentSectionIdx] = useState(0);
  const [currentQ, setCurrentQ] = useState(0);
  const [completedSections, setCompletedSections] = useState<Set<number>>(new Set());
  const [lockedSections, setLockedSections] = useState<Set<number>>(new Set());
  const [navigationError, setNavigationError] = useState<string | null>(null);
  const [sectionSubmitDialogOpen, setSectionSubmitDialogOpen] = useState<boolean>(false);
  const [submittingSection, setSubmittingSection] = useState<boolean>(false);
  
  // Hydrated CandidateAnswer state mapping key `${secIdx}_${qIdx}` -> AnswerData
  const [answers, setAnswers] = useState<Record<string, AnswerData>>({});
  // Status indicator per question `${secIdx}_${qIdx}` -> SaveStatus
  const [saveStatuses, setSaveStatuses] = useState<Record<string, SaveStatus>>({});
  // Flagged for review set of `${secIdx}_${qIdx}`
  const [flagged, setFlagged] = useState<Set<string>>(new Set());
  
  const [submitOpen, setSubmitOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [timeLeft, setTimeLeft] = useState(7200);

  // Network & Resilience State
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [isSuspended, setIsSuspended] = useState<boolean>(false);
  const [isSecondaryTab, setIsSecondaryTab] = useState<boolean>(false);
  const [recoveredDraftNotice, setRecoveredDraftNotice] = useState<string | null>(null);

  const monitoringVideoRef = useRef<HTMLVideoElement | null>(null);
  const wsRef = useRef<WebSocketClient | null>(null);

  // ─── Exam Environment Monitor (independent from AI engine) ───────────────
  const envMonitorRef = useRef<ExamEnvironmentMonitor>(new ExamEnvironmentMonitor());
  const [fullscreenReady, setFullscreenReady] = useState<boolean>(false);
  const [fullscreenError, setFullscreenError] = useState<string | null>(null);
  const [fullscreenRecoveryRequired, setFullscreenRecoveryRequired] = useState<boolean>(false);
  const [envViolations, setEnvViolations] = useState<EnvViolationRecord[]>([]);
  const [showViolationWarning, setShowViolationWarning] = useState<boolean>(false);
  // ─────────────────────────────────────────────────────────────────────────
  const [cameraActive, setCameraActive] = useState(false);
  const examSessionIdRef = useRef<number | null>(null);
  const [activeExamSessionId, setActiveExamSessionId] = useState<number | null>(null);

  // Refs for debouncing, offline queue, and multi-tab management
  const debounceTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const offlineQueueRef = useRef<OfflineQueueItem[]>([]);
  const tabIdRef = useRef<string>(Math.random().toString(36).substring(2, 9));
  const broadcastChannelRef = useRef<BroadcastChannel | null>(null);

  // Local Storage Cache Keys (Scoped by student userId + examId)
  const LOCAL_CACHE_KEY = `exam_drafts_${userId}_${examId}`;
  const LOCAL_FLAGGED_KEY = `exam_flagged_${userId}_${examId}`;
  const TAB_CLAIM_KEY = `exam_active_tab_${userId}_${examId}`;
  const BROADCAST_CHANNEL_NAME = `exam_runtime_channel_${userId}_${examId}`;

  const releaseTabLock = () => {
    try {
      const currentTabId = tabIdRef.current;
      const rawClaim = localStorage.getItem(TAB_CLAIM_KEY);
      if (rawClaim) {
        const claim: TabLockClaim = JSON.parse(rawClaim);
        if (claim.tabId === currentTabId) {
          localStorage.removeItem(TAB_CLAIM_KEY);
        }
      }
    } catch (e) {
      localStorage.removeItem(TAB_CLAIM_KEY);
    }
  };

  // 1. Multi-Tab Lock Protection (Phase 10)
  useEffect(() => {
    const currentTabId = tabIdRef.current;
    const STALE_THRESHOLD_MS = 12000; // 12-second TTL for stale lock recovery

    const checkAndClaimLock = (): boolean => {
      const now = Date.now();
      const rawClaim = localStorage.getItem(TAB_CLAIM_KEY);

      if (rawClaim) {
        try {
          const claim: TabLockClaim = JSON.parse(rawClaim);
          const isStale = now - claim.timestamp > STALE_THRESHOLD_MS;

          // If an active (non-stale) claim exists from ANOTHER tab for the SAME student and exam
          if (claim.tabId !== currentTabId && !isStale) {
            setIsSecondaryTab(true);
            return false;
          }
        } catch (e) {
          // Unparseable/legacy value - replace with fresh claim
        }
      }

      // Claim or refresh ownership timestamp for this tab
      const newClaim: TabLockClaim = {
        tabId: currentTabId,
        userId,
        examId,
        timestamp: now,
      };
      localStorage.setItem(TAB_CLAIM_KEY, JSON.stringify(newClaim));
      setIsSecondaryTab(false);
      return true;
    };

    // Initial check and claim
    const hasLock = checkAndClaimLock();

    // Heartbeat: periodically refresh timestamp to prevent lock from becoming stale while tab is active
    const lockHeartbeat = setInterval(() => {
      checkAndClaimLock();
    }, 3000);

    // Setup BroadcastChannel for instantaneous cross-tab lock notification
    try {
      const channel = new BroadcastChannel(BROADCAST_CHANNEL_NAME);
      broadcastChannelRef.current = channel;

      channel.onmessage = (event) => {
        if (event.data?.type === 'CLAIM_TAB' && event.data?.tabId !== currentTabId && event.data?.userId === userId) {
          setIsSecondaryTab(true);
        }
      };

      if (hasLock) {
        channel.postMessage({ type: 'CLAIM_TAB', tabId: currentTabId, userId, examId });
      }
    } catch (e) {
      console.warn("BroadcastChannel not supported, falling back to window storage events", e);
    }

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === TAB_CLAIM_KEY && e.newValue) {
        try {
          const claim: TabLockClaim = JSON.parse(e.newValue);
          if (claim.tabId !== currentTabId && claim.userId === userId) {
            setIsSecondaryTab(true);
          }
        } catch (err) {}
      }
    };

    // Failsafe unload listeners for browser close, refresh, navigation
    const handlePageUnload = () => {
      releaseTabLock();
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('beforeunload', handlePageUnload);
    window.addEventListener('pagehide', handlePageUnload);

    return () => {
      clearInterval(lockHeartbeat);
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('beforeunload', handlePageUnload);
      window.removeEventListener('pagehide', handlePageUnload);

      releaseTabLock();

      if (broadcastChannelRef.current) {
        broadcastChannelRef.current.close();
      }
    };
  }, [examId, userId]);

  // 2. Network Interruption & Offline Sync Listener (Phase 4)
  useEffect(() => {
    const handleOnline = async () => {
      setIsOnline(true);
      await flushOfflineQueue();
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [examId]);

  // The page owns exactly one browser stream. Video elements are consumers only.
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const streamRequestRef = useRef<Promise<MediaStream> | null>(null);
  const pendingStreamCleanupRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const videoDiagnosticsRef = useRef<Map<HTMLVideoElement, VideoDiagnosticBinding>>(new Map());

  const logCameraDiagnostic = useCallback((event: string, details: Record<string, unknown> = {}) => {
    console.info('[camera-runtime]', {
      event,
      at: new Date().toISOString(),
      ...details,
    });
  }, []);

  const describeStream = useCallback((activeStream: MediaStream | null) => ({
    streamActive: activeStream?.active ?? false,
    trackCount: activeStream?.getTracks().length ?? 0,
    tracks: activeStream?.getTracks().map((track) => ({
      kind: track.kind,
      label: track.label,
      readyState: track.readyState,
      enabled: track.enabled,
      muted: track.muted,
    })) ?? [],
  }), []);

  const describeVideo = useCallback((video: HTMLVideoElement) => ({
    readyState: video.readyState,
    paused: video.paused,
    currentTime: video.currentTime,
    videoWidth: video.videoWidth,
    videoHeight: video.videoHeight,
    clientWidth: video.clientWidth,
    clientHeight: video.clientHeight,
    srcObjectAttached: video.srcObject !== null,
  }), []);

  const removeVideoDiagnostics = useCallback((video: HTMLVideoElement) => {
    const binding = videoDiagnosticsRef.current.get(video);
    if (binding) {
      clearInterval(binding.timer);
      binding.cleanup();
      videoDiagnosticsRef.current.delete(video);
    }
  }, []);

  const installVideoDiagnostics = useCallback((video: HTMLVideoElement, role: CameraVideoRole) => {
    if (videoDiagnosticsRef.current.has(video)) return;

    let firstFrameReported = false;
    let samples = 0;
    const report = (event: string, extra: Record<string, unknown> = {}) => {
      logCameraDiagnostic(event, { role, ...describeVideo(video), ...extra });
    };
    const onLoadedMetadata = () => report('loadedmetadata');
    const onLoadedData = () => report('loadeddata');
    const onCanPlay = () => report('canplay');
    const onPlaying = () => report('playing');
    const onError = () => report('video-error', { mediaError: video.error ? { code: video.error.code, message: video.error.message } : null });

    video.addEventListener('loadedmetadata', onLoadedMetadata);
    video.addEventListener('loadeddata', onLoadedData);
    video.addEventListener('canplay', onCanPlay);
    video.addEventListener('playing', onPlaying);
    video.addEventListener('error', onError);

    const requestFrame = (video as HTMLVideoElement & { requestVideoFrameCallback?: (callback: (now: number, metadata: unknown) => void) => number }).requestVideoFrameCallback;
    if (requestFrame) {
      requestFrame.call(video, (now) => {
        if (!firstFrameReported) {
          firstFrameReported = true;
          report('first-rendered-frame', { elapsedMilliseconds: Math.round(now) });
        }
      });
    }

    const timer = setInterval(() => {
      samples += 1;
      if (!firstFrameReported && video.currentTime > 0 && video.videoWidth > 0 && video.videoHeight > 0) {
        firstFrameReported = true;
        report('first-rendered-frame', { source: 'playback-sample' });
      }
      report('playback-sample', { sample: samples });
      if (samples >= 8) clearInterval(timer);
    }, 1000);

    videoDiagnosticsRef.current.set(video, {
      timer,
      cleanup: () => {
        video.removeEventListener('loadedmetadata', onLoadedMetadata);
        video.removeEventListener('loadeddata', onLoadedData);
        video.removeEventListener('canplay', onCanPlay);
        video.removeEventListener('playing', onPlaying);
        video.removeEventListener('error', onError);
      },
    });
  }, [describeVideo, logCameraDiagnostic]);

  const attachStreamToVideo = useCallback(async (video: HTMLVideoElement, role: CameraVideoRole) => {
    const activeStream = mediaStreamRef.current;
    if (!activeStream) {
      logCameraDiagnostic('video-awaiting-stream', { role });
      return;
    }

    installVideoDiagnostics(video, role);
    video.muted = true;
    video.defaultMuted = true;
    video.playsInline = true;
    video.autoplay = true;

    if (video.srcObject !== activeStream) {
      video.srcObject = activeStream;
      logCameraDiagnostic('srcObject-assigned', { role, ...describeStream(activeStream), ...describeVideo(video) });
    }

    try {
      logCameraDiagnostic('play-called', { role, ...describeVideo(video) });
      await video.play();
      logCameraDiagnostic('play-resolved', { role, ...describeVideo(video) });
    } catch (error) {
      logCameraDiagnostic('play-rejected', {
        role,
        error: error instanceof Error ? { name: error.name, message: error.message } : String(error),
        ...describeVideo(video),
      });
      console.error('Camera video playback failed', error);
    }
  }, [describeStream, describeVideo, installVideoDiagnostics, logCameraDiagnostic]);

  const attachMonitoringVideo = useCallback((video: HTMLVideoElement | null) => {
    const previousVideo = monitoringVideoRef.current;
    if (previousVideo && previousVideo !== video) removeVideoDiagnostics(previousVideo);
    monitoringVideoRef.current = video;
    if (video) {
      logCameraDiagnostic('video-mounted', { role: 'monitoring' });
      void attachStreamToVideo(video, 'monitoring');
    } else {
      logCameraDiagnostic('video-unmounted', { role: 'monitoring' });
    }
  }, [attachStreamToVideo, logCameraDiagnostic, removeVideoDiagnostics]);

  // 3. Initial Camera & Exam Session Setup
  useEffect(() => {
    let effectActive = true;
    if (pendingStreamCleanupRef.current) {
      clearTimeout(pendingStreamCleanupRef.current);
      pendingStreamCleanupRef.current = null;
    }

    const initCameraAndPolicy = async () => {
      // React StrictMode replays effects in development. Reuse the same pending request
      // and stream so the replay cannot create a competing camera session.
      if (mediaStreamRef.current && mediaStreamRef.current.getVideoTracks().some(t => t.readyState === 'live')) {
        logCameraDiagnostic('stream-reused', describeStream(mediaStreamRef.current));
        setCameraActive(true);
        await startExamSession();
        setLoading(false);
        return;
      }

      try {
        if (!streamRequestRef.current) {
          logCameraDiagnostic('stream-requested');
          streamRequestRef.current = navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        }
        const st = await streamRequestRef.current;
        if (!effectActive) return;
        mediaStreamRef.current = st;
        logCameraDiagnostic('stream-created', describeStream(st));
        setCameraActive(true);
        await startExamSession();
      } catch (camErr: any) {
        console.error("Camera access failed:", camErr);
        let msg = "Failed to access camera. Please verify your camera device and try again.";
        const errorName = camErr?.name || '';
        
        if (errorName === 'NotAllowedError' || errorName === 'PermissionDeniedError') {
          msg = "Camera permission was denied. Please allow camera access in your browser settings and refresh the page.";
        } else if (errorName === 'NotReadableError' || errorName === 'TrackStartError') {
          msg = "Camera is currently in use by another application. Please close other camera applications and click Retry.";
        } else if (errorName === 'NotFoundError' || errorName === 'DevicesNotFoundError') {
          msg = "No camera hardware detected on your device. Please connect a working camera and click Retry.";
        } else if (errorName === 'AbortError') {
          msg = "Camera initialization was aborted. Please click Retry to attempt camera access again.";
        } else if (errorName === 'OverconstrainedError') {
          msg = "Camera constraints cannot be satisfied by your video device. Please check your camera settings and retry.";
        }
        setPermissionError(msg);
      } finally {
        setLoading(false);
      }
    };

    initCameraAndPolicy();
    return () => {
      effectActive = false;
      // Deferring one task lets StrictMode's immediate effect replay cancel this cleanup.
      // A real unmount still releases the one owned stream.
      const outstandingRequest = streamRequestRef.current;
      pendingStreamCleanupRef.current = setTimeout(async () => {
        const activeStream = mediaStreamRef.current;
        if (activeStream) {
          logCameraDiagnostic('stream-stopped-on-unmount', describeStream(activeStream));
          activeStream.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        } else if (outstandingRequest) {
          // If an actual unmount happens while permission is pending, release the
          // stream as soon as the browser resolves the pending request.
          try {
            const pendingStream = await outstandingRequest;
            logCameraDiagnostic('pending-stream-stopped-on-unmount', describeStream(pendingStream));
            pendingStream.getTracks().forEach((track) => track.stop());
          } catch {
            // The original acquisition path already reports permission failures.
          }
        }
        streamRequestRef.current = null;
        videoDiagnosticsRef.current.forEach((binding, video) => {
          clearInterval(binding.timer);
          binding.cleanup();
          videoDiagnosticsRef.current.delete(video);
        });
      }, 0);
    };
  }, [describeStream, examId, logCameraDiagnostic]);

  /**
   * Request fullscreen after the exam session starts.
   * Called by startExamSession after the backend session is established.
   * Sets fullscreenReady=true on success, fullscreenError on failure.
   */
  const requestFullscreenAndActivateMonitor = async (sessionId: number) => {
    try {
      await document.documentElement.requestFullscreen();
      setFullscreenReady(true);
      setFullscreenError(null);
      setFullscreenRecoveryRequired(false);

      // Start the independent env monitor now that fullscreen is active
      const monitor = envMonitorRef.current;

      // Provide live camera snapshot capture
      monitor.setSnapshotProvider(() => {
        try {
          const video = monitoringVideoRef.current;
          if (video && video.videoWidth > 0 && video.videoHeight > 0) {
            const canvas = document.createElement('canvas');
            canvas.width = 640;
            canvas.height = 480;
            const ctx = canvas.getContext('2d');
            if (ctx) {
              ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
              return canvas.toDataURL('image/jpeg', 0.6);
            }
          }
        } catch (e) {
          console.warn('Snapshot capture warning:', e);
        }
        return null;
      });

      monitor.onViolationDetected((v: EnvViolationRecord) => {
        setEnvViolations(prev => [v, ...prev]);
      });

      monitor.onViolationResolved((v: EnvViolationRecord) => {
        // Update duration in existing record
        setEnvViolations(prev =>
          prev.map(ev =>
            ev.id === v.id || (ev.id <= 0 && ev.startedAt === v.startedAt)
              ? { ...ev, endedAt: v.endedAt, durationSeconds: v.durationSeconds, status: 'PENDING' as const }
              : ev
          )
        );
        // Show the "violation recorded" warning banner when student returns
        setShowViolationWarning(true);
      });

      // Show blocking recovery overlay when student returns without fullscreen
      monitor.onFullscreenRequired(() => {
        if (!isAlreadySubmitted) {
          setFullscreenRecoveryRequired(true);
        }
      });

      monitor.startMonitoring(examId, sessionId);

    } catch {
      setFullscreenError(
        'Fullscreen mode is required to start this examination. ' +
        'Please click the button below to enable fullscreen and begin.'
      );
      setFullscreenReady(false);
    }
  };

  const startExamSession = async () => {
    try {
      setLoading(true);
      const res = await apiClient.post(`/runtime/start?exam_id=${examId}`);
      const data = res.data;
      
      if (data.session) {
        examSessionIdRef.current = data.session.id;
        setActiveExamSessionId(data.session.id);
        if (data.session.status === 'COMPLETED') {
          setIsAlreadySubmitted(true);
          setSubmissionCompletedMessage("This examination attempt has already been completed and submitted.");
          setLoading(false);
          return;
        }
      }
      
      setMode(data.mode || 'STRUCTURED');
      if (data.exam_config && data.exam_config.title) {
        setExamTitle(data.exam_config.title);
      }
      
      localStorage.setItem('last_active_exam_id', String(examId));

      if (data.mode === 'FILE') {
        setFileUrl(data.file_url || '');
      } else {
        setSections(data.sections || []);
      }
      
      setTimeLeft(data.time_left_seconds || 7200);
      
      // Dual-Layer Hydration & Long Essay Recovery Engine (Phase 1 & Phase 3)
      try {
        const stateRes = await apiClient.get(`/runtime/state?exam_id=${examId}`);
        if (stateRes.data) {
          if (stateRes.data.current_question_index !== undefined) {
            setCurrentQ(stateRes.data.current_question_index);
          }
          if (stateRes.data.current_section_index !== undefined) {
            setCurrentSectionIdx(stateRes.data.current_section_index);
          }
          if (stateRes.data.completed_sections) {
            setCompletedSections(new Set(stateRes.data.completed_sections));
          }
          if (stateRes.data.locked_sections) {
            setLockedSections(new Set(stateRes.data.locked_sections));
          }
        }
        
        const ansRes = await apiClient.get(`/runtime/answers?exam_id=${examId}`);
        const serverAnswers: Record<string, AnswerData> = {};
        const flaggedSet = new Set<string>();

        if (ansRes.data && Array.isArray(ansRes.data)) {
          ansRes.data.forEach((a: any) => {
            const qKey = `${a.section_index}_${a.question_index}`;
            serverAnswers[qKey] = a.answer_data || {};
            if (a.answer_status === 'MARKED_FOR_REVIEW') {
              flaggedSet.add(qKey);
            }
          });
        }

        // Layer 2: Read Local Cache Drafts
        let localDraftsRaw = localStorage.getItem(LOCAL_CACHE_KEY);
        let localDrafts: Record<string, { answer_data: AnswerData; timestamp: number }> = {};
        if (localDraftsRaw) {
          try {
            localDrafts = JSON.parse(localDraftsRaw);
          } catch (e) {
            console.warn("Failed to parse local draft cache", e);
          }
        }

        let localFlaggedRaw = localStorage.getItem(LOCAL_FLAGGED_KEY);
        if (localFlaggedRaw) {
          try {
            const localFlaggedList: string[] = JSON.parse(localFlaggedRaw);
            localFlaggedList.forEach(k => flaggedSet.add(k));
          } catch (e) {}
        }

        // Conflict Resolution: Prefer Local Draft if text is longer or newer
        let hasRecoveredDraft = false;
        const mergedAnswers: Record<string, AnswerData> = { ...serverAnswers };

        Object.keys(localDrafts).forEach((qKey) => {
          const localItem = localDrafts[qKey];
          const serverItem = serverAnswers[qKey];

          if (localItem && localItem.answer_data) {
            const localText = localItem.answer_data.text || '';
            const serverText = serverItem?.text || '';

            if (localText.length > serverText.length) {
              mergedAnswers[qKey] = localItem.answer_data;
              hasRecoveredDraft = true;
              // Push recovered draft to sync queue
              const parts = qKey.split('_');
              if (parts.length === 2) {
                const sIdx = parseInt(parts[0]);
                const qIdx = parseInt(parts[1]);
                offlineQueueRef.current.push({
                  secIdx: sIdx,
                  qIdx,
                  ansData: localItem.answer_data,
                  isFlagged: flaggedSet.has(qKey)
                });
              }
            }
          }
        });

        setAnswers(mergedAnswers);
        setFlagged(flaggedSet);

        if (hasRecoveredDraft) {
          setRecoveredDraftNotice("Local Draft Restored: Unsaved typing from your previous session was recovered successfully.");
          // Sync recovered local drafts immediately
          await flushOfflineQueue();
        }
      } catch (e) {
        console.warn("Failed to hydrate runtime state or answers", e);
      }
      
      // Connect WebSocket for live AI monitoring feedback
      const ws = new WebSocketClient(parseInt(examId));
      wsRef.current = ws;
      ws.connect();

      // Request fullscreen + activate Exam Environment Monitor
      // Must be done here (inside startExamSession) so it's triggered
      // by the same user-interaction call chain that the browser allows
      // for fullscreen requests.
      const sessionId = examSessionIdRef.current;
      if (sessionId) {
        await requestFullscreenAndActivateMonitor(sessionId);
      }

    } catch (err: any) {
      console.error("Failed to initialize exam runtime:", err);
      const detail = err.response?.data?.detail || err.message;
      if (detail && detail.includes("already completed")) {
        setIsAlreadySubmitted(true);
        setSubmissionCompletedMessage(detail);
      } else {
        alert("Failed to initialize examination: " + detail);
      }
    } finally {
      setLoading(false);
    }
  };

  // 4. Timers and Heartbeats (only when active)
  useEffect(() => {
    if (isAlreadySubmitted || isSecondaryTab) return;

    const timer = setInterval(() => {
      if (isSuspended || !isOnline) return; // Freeze timer during suspension

      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          handleSubmit();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    const syncEffectiveTime = async () => {
      try {
        const res = await apiClient.get(`/runtime/effective-time?exam_id=${examId}`);
        if (res.data) {
          if (res.data.status === 'SUSPENDED') {
            setIsSuspended(true);
          } else if (res.data.status === 'RUNNING' && isSuspended) {
            setIsSuspended(false);
          }
          if (res.data.effective_remaining_seconds !== undefined) {
            setTimeLeft(res.data.effective_remaining_seconds);
          }
        }
      } catch (e) {
        console.warn("Failed to sync backend server time", e);
      }
    };

    const heartbeat = setInterval(async () => {
      if (!isOnline) return;
      try {
        await apiClient.post(`/runtime/heartbeat?exam_id=${examId}`);
        await syncEffectiveTime();
      } catch (e) {
        console.warn("Heartbeat missed. Triggering session suspension check", e);
        try {
          await apiClient.post('/runtime/suspend', { exam_id: Number(examId), reason: "Heartbeat miss threshold exceeded" });
          setIsSuspended(true);
        } catch (sErr) {
          setIsSuspended(true);
        }
      }
    }, 15000);

    return () => {
      clearInterval(timer);
      clearInterval(heartbeat);
      if (wsRef.current) wsRef.current.disconnect();
    };
  }, [isAlreadySubmitted, isSecondaryTab, examId, isSuspended, isOnline]);

  // Auto-reconnection loop when offline or suspended
  useEffect(() => {
    if (isAlreadySubmitted) return;

    if (!isOnline || isSuspended) {
      const reconInterval = setInterval(async () => {
        if (!navigator.onLine) return;
        try {
          const res = await apiClient.post('/runtime/resume', {
            exam_id: Number(examId)
          });
          if (res.data && res.data.status === 'RUNNING') {
            setIsSuspended(false);
            if (res.data.effective_time?.effective_remaining_seconds !== undefined) {
              setTimeLeft(res.data.effective_time.effective_remaining_seconds);
            }
          }
        } catch (err) {
          console.warn("Reconnection attempt pending...", err);
        }
      }, 4000);

      return () => clearInterval(reconInterval);
    }
  }, [isAlreadySubmitted, isOnline, isSuspended, examId]);

  // 5. Layer 2 Local Draft Persistence Helper
  const persistLocalDraft = (qKey: string, ansData: AnswerData, isFlagged: boolean) => {
    try {
      let localDraftsRaw = localStorage.getItem(LOCAL_CACHE_KEY);
      let localDrafts: Record<string, { answer_data: AnswerData; timestamp: number }> = {};
      if (localDraftsRaw) {
        localDrafts = JSON.parse(localDraftsRaw);
      }
      localDrafts[qKey] = { answer_data: ansData, timestamp: Date.now() };
      localStorage.setItem(LOCAL_CACHE_KEY, JSON.stringify(localDrafts));

      const flaggedList = Array.from(flagged);
      if (isFlagged && !flaggedList.includes(qKey)) {
        flaggedList.push(qKey);
      } else if (!isFlagged && flaggedList.includes(qKey)) {
        const idx = flaggedList.indexOf(qKey);
        flaggedList.splice(idx, 1);
      }
      localStorage.setItem(LOCAL_FLAGGED_KEY, JSON.stringify(flaggedList));
    } catch (e) {
      console.warn("Failed to persist local draft to storage", e);
    }
  };

  // 6. Offline Queue Flush Helper (Phase 4 Exponential Retry)
  const flushOfflineQueue = async () => {
    if (offlineQueueRef.current.length === 0) return;
    
    const itemsToProcess = [...offlineQueueRef.current];
    offlineQueueRef.current = [];

    for (const item of itemsToProcess) {
      const qKey = `${item.secIdx}_${item.qIdx}`;
      setSaveStatuses(prev => ({ ...prev, [qKey]: 'syncing' }));

      let attempts = 0;
      let success = false;
      
      while (attempts < 3 && !success) {
        try {
          let status = 'NOT_ANSWERED';
          if (item.isFlagged) {
            status = 'MARKED_FOR_REVIEW';
          } else if (
            item.ansData.selected !== undefined ||
            (item.ansData.selected_options && item.ansData.selected_options.length > 0) ||
            (item.ansData.text && item.ansData.text.trim().length > 0)
          ) {
            status = 'ANSWERED';
          }

          await apiClient.post(`/runtime/answers/${item.secIdx}/${item.qIdx}?exam_id=${examId}`, {
            answer_data: item.ansData,
            answer_status: status,
            is_submitted: false
          });

          success = true;
          setSaveStatuses(prev => ({ ...prev, [qKey]: 'saved' }));
          setTimeout(() => {
            setSaveStatuses(prev => ({ ...prev, [qKey]: 'idle' }));
          }, 2000);
        } catch (e) {
          attempts++;
          await new Promise(r => setTimeout(r, 1000 * Math.pow(2, attempts)));
        }
      }

      if (!success) {
        offlineQueueRef.current.push(item);
        setSaveStatuses(prev => ({ ...prev, [qKey]: 'error' }));
      }
    }
  };

  // 7. Dual-Layer Autosave Core Engine
  const saveCandidateAnswer = async (
    secIdx: number,
    qIdx: number,
    ansData: AnswerData,
    isFlagged?: boolean
  ) => {
    const qKey = `${secIdx}_${qIdx}`;
    const flaggedState = isFlagged !== undefined ? isFlagged : flagged.has(qKey);

    // Layer 2: Save locally first
    persistLocalDraft(qKey, ansData, flaggedState);

    // Check Network Availability
    if (!navigator.onLine) {
      setSaveStatuses(prev => ({ ...prev, [qKey]: 'offline' }));
      offlineQueueRef.current.push({ secIdx, qIdx, ansData, isFlagged: flaggedState });
      return;
    }

    // Layer 1: Save to Server
    setSaveStatuses(prev => ({ ...prev, [qKey]: 'saving' }));

    let status = 'NOT_ANSWERED';
    if (flaggedState) {
      status = 'MARKED_FOR_REVIEW';
    } else if (
      ansData.selected !== undefined ||
      (ansData.selected_options && ansData.selected_options.length > 0) ||
      (ansData.text && ansData.text.trim().length > 0)
    ) {
      status = 'ANSWERED';
    }

    try {
      await apiClient.post(`/runtime/answers/${secIdx}/${qIdx}?exam_id=${examId}`, {
        answer_data: ansData,
        answer_status: status,
        is_submitted: false
      });

      setSaveStatuses(prev => ({ ...prev, [qKey]: 'saved' }));
      setTimeout(() => {
        setSaveStatuses(prev => ({ ...prev, [qKey]: 'idle' }));
      }, 2500);
    } catch (err: any) {
      console.error(`Server autosave failed for question [${secIdx}, ${qIdx}]:`, err);
      setSaveStatuses(prev => ({ ...prev, [qKey]: 'offline' }));
      // Push to offline queue for automatic retry
      offlineQueueRef.current.push({ secIdx, qIdx, ansData, isFlagged: flaggedState });
    }
  };

  // Immediate Autosave handler for Single-Choice MCQ
  const handleSingleChoiceAnswer = (secIdx: number, qIdx: number, optionIdx: number) => {
    const qKey = `${secIdx}_${qIdx}`;
    const newAnsData: AnswerData = { ...answers[qKey], selected: optionIdx };
    setAnswers(prev => ({ ...prev, [qKey]: newAnsData }));
    saveCandidateAnswer(secIdx, qIdx, newAnsData, flagged.has(qKey));
  };

  // Immediate Autosave handler for Multiple-Choice Checkboxes
  const handleMultiChoiceAnswer = (secIdx: number, qIdx: number, optionIdx: number) => {
    const qKey = `${secIdx}_${qIdx}`;
    const currentList = answers[qKey]?.selected_options || [];
    let updatedList: number[];
    if (currentList.includes(optionIdx)) {
      updatedList = currentList.filter(i => i !== optionIdx);
    } else {
      updatedList = [...currentList, optionIdx].sort((a, b) => a - b);
    }
    const newAnsData: AnswerData = { ...answers[qKey], selected_options: updatedList };
    setAnswers(prev => ({ ...prev, [qKey]: newAnsData }));
    saveCandidateAnswer(secIdx, qIdx, newAnsData, flagged.has(qKey));
  };

  // Debounced Autosave handler for Subjective / Long Essay Questions (Phase 3)
  const handleTextAnswer = (secIdx: number, qIdx: number, textVal: string) => {
    const qKey = `${secIdx}_${qIdx}`;
    const newAnsData: AnswerData = { ...answers[qKey], text: textVal };
    
    // Update local state and Layer 2 draft immediately
    setAnswers(prev => ({ ...prev, [qKey]: newAnsData }));
    persistLocalDraft(qKey, newAnsData, flagged.has(qKey));
    setSaveStatuses(prev => ({ ...prev, [qKey]: 'saving' }));

    // Clear existing debounce timer
    if (debounceTimers.current[qKey]) {
      clearTimeout(debounceTimers.current[qKey]);
    }

    // Schedule debounced Layer 1 server save (750ms)
    debounceTimers.current[qKey] = setTimeout(() => {
      saveCandidateAnswer(secIdx, qIdx, newAnsData, flagged.has(qKey));
    }, 750);
  };

  // Toggle Flag / Mark for Review
  const toggleFlag = (secIdx: number, qIdx: number) => {
    const qKey = `${secIdx}_${qIdx}`;
    const isCurrentlyFlagged = flagged.has(qKey);
    const nextFlagged = new Set(flagged);
    
    if (isCurrentlyFlagged) {
      nextFlagged.delete(qKey);
    } else {
      nextFlagged.add(qKey);
    }
    setFlagged(nextFlagged);

    const currentAns = answers[qKey] || {};
    saveCandidateAnswer(secIdx, qIdx, currentAns, !isCurrentlyFlagged);
  };

  const handleNavigation = async (targetSecIdx: number, targetQIdx: number) => {
    // If target section is locked, block immediately
    if (lockedSections.has(targetSecIdx)) {
      const secName = sections[targetSecIdx]?.section_name || `Section ${targetSecIdx + 1}`;
      setNavigationError(`'${secName}' has been completed and locked.`);
      return;
    }

    // If navigating to a future section and current section requires completion, block
    if (targetSecIdx > currentSectionIdx) {
      const curSec = sections[currentSectionIdx];
      if (curSec && (curSec.require_completion_before_next || curSec.navigation_policy === 'SEQUENTIAL')) {
        if (!completedSections.has(currentSectionIdx)) {
          setNavigationError(`Please submit and complete '${curSec.section_name || `Section ${currentSectionIdx + 1}`}' before proceeding to the next section.`);
          setSectionSubmitDialogOpen(true);
          return;
        }
      }
    }

    try {
      const res = await apiClient.put(`/runtime/state/position?exam_id=${examId}&section_index=${targetSecIdx}&question_index=${targetQIdx}`);
      if (res.data) {
        if (res.data.completed_sections) setCompletedSections(new Set(res.data.completed_sections));
        if (res.data.locked_sections) setLockedSections(new Set(res.data.locked_sections));
      }
      setCurrentSectionIdx(targetSecIdx);
      setCurrentQ(targetQIdx);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || "Navigation not permitted.";
      console.warn("Navigation rejected:", detail);
      setNavigationError(detail);
    }
  };

  const handleCompleteSection = async () => {
    if (submittingSection) return;
    try {
      setSubmittingSection(true);
      // Flush debounce timers
      Object.keys(debounceTimers.current).forEach((qKey) => {
        if (debounceTimers.current[qKey]) {
          clearTimeout(debounceTimers.current[qKey]);
        }
      });
      await flushOfflineQueue();

      const res = await apiClient.post(`/runtime/sections/${currentSectionIdx}/complete?exam_id=${examId}`);
      if (res.data) {
        if (res.data.completed_sections) setCompletedSections(new Set(res.data.completed_sections));
        if (res.data.locked_sections) setLockedSections(new Set(res.data.locked_sections));
        if (res.data.current_section_index !== undefined) {
          setCurrentSectionIdx(res.data.current_section_index);
        }
        if (res.data.current_question_index !== undefined) {
          setCurrentQ(res.data.current_question_index);
        }
      }
      setSectionSubmitDialogOpen(false);
    } catch (err: any) {
      console.error("Failed to complete section:", err);
      const detail = err.response?.data?.detail || err.message || "Failed to complete section.";
      setNavigationError(detail);
    } finally {
      setSubmittingSection(false);
    }
  };

  // Idempotent Submission Safety (Phase 8)
  const handleSubmit = async () => {
    if (submitting) return;
    try {
      setSubmitting(true);

      // 1. Flush all pending debounce timers
      Object.keys(debounceTimers.current).forEach((qKey) => {
        if (debounceTimers.current[qKey]) {
          clearTimeout(debounceTimers.current[qKey]);
        }
      });

      // 2. Flush offline queue to server before final submission
      await flushOfflineQueue();

      // ── CRITICAL: Stop exam environment monitor BEFORE submitting ──────
      // This prevents the normal fullscreen exit that occurs after submission
      // from being recorded as a false cheating violation.
      setFullscreenRecoveryRequired(false);
      envMonitorRef.current.stopMonitoring();
      // ──────────────────────────────────────────────────────────────────

      // 3. Submit Exam Session
      const res = await apiClient.post(`/runtime/submit?exam_id=${examId}`);
      const summary = res.data?.summary;

      // 4. Clear Local Cache Drafts & Tab Lock upon successful submission
      localStorage.removeItem(LOCAL_CACHE_KEY);
      localStorage.removeItem(LOCAL_FLAGGED_KEY);
      releaseTabLock();

      // 5. Exit fullscreen gracefully (monitoring already stopped)
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
      }

      setSubmitOpen(false);
      navigate(`/student/submitted?exam_id=${examId}`, { state: { summary } });
    } catch (err: any) {
      console.error("Failed to submit exam:", err);
      navigate(`/student/submitted?exam_id=${examId}`);
    } finally {
      setSubmitting(false);
    }
  };

  // Formatting & Badge Calculation Helpers
  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', bgcolor: '#F8FAFC' }}>
        <CircularProgress size={40} />
        <Typography sx={{ ml: 2, fontWeight: 600, color: 'text.secondary' }}>
          Initializing Examination Environment...
        </Typography>
      </Box>
    );
  }

  // Render Multi-Tab Lock Guard (Phase 10)
  if (isSecondaryTab) {
    return (
      <Box sx={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', bgcolor: '#F8FAFC', p: 3 }}>
        <Card elevation={3} sx={{ maxWidth: 520, width: '100%', borderRadius: 3, textAlign: 'center', p: 3 }}>
          <CardContent>
            <LockIcon sx={{ fontSize: 64, color: 'warning.main', mb: 2 }} />
            <Typography variant="h5" fontWeight={700} color="text.primary" gutterBottom>
              Secondary Tab Lock
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3, lineHeight: 1.6 }}>
              An active examination session is already open in another window or tab. To prevent response loss and state conflicts, secondary tabs are locked.
            </Typography>
            <Button variant="contained" color="primary" onClick={() => window.close()} sx={{ borderRadius: 2, fontWeight: 700 }}>
              Close Secondary Tab
            </Button>
          </CardContent>
        </Card>
      </Box>
    );
  }

  // Render Already Submitted Guard Screen
  if (isAlreadySubmitted) {
    return (
      <Box sx={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', bgcolor: '#F8FAFC', p: 3 }}>
        <Card elevation={2} sx={{ maxWidth: 500, width: '100%', borderRadius: 3, textAlign: 'center', p: 2 }}>
          <CardContent>
            <CheckCircleIcon sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
            <Typography variant="h5" fontWeight={700} color="text.primary" gutterBottom>
              Attempt Already Completed
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              {submissionCompletedMessage || "You have already completed and submitted this examination session. Further entries or modifications are locked."}
            </Typography>
            <Stack direction="row" spacing={2} justifyContent="center">
              <Button variant="outlined" startIcon={<ArrowBackIcon />} onClick={() => navigate('/student/dashboard')}>
                Student Dashboard
              </Button>
              <Button variant="contained" color="primary" onClick={() => navigate('/student/submitted')}>
                View Submission Summary
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Box>
    );
  }

  if (permissionError) {
    return (
      <Box sx={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', bgcolor: '#F8FAFC', p: 3 }}>
        <Paper elevation={2} sx={{ p: 4, textAlign: 'center', maxWidth: 520, borderRadius: 3 }}>
          <ErrorOutlineIcon color="error" sx={{ fontSize: 56, mb: 1 }} />
          <Typography color="error" variant="h6" fontWeight={700} gutterBottom>
            Camera Access Required
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3, lineHeight: 1.6 }}>
            {permissionError}
          </Typography>
          <Button variant="contained" startIcon={<RefreshIcon />} onClick={() => window.location.reload()} size="large">
            Retry Camera Access
          </Button>
        </Paper>
      </Box>
    );
  }

  // Render Fullscreen Required / Failed screen
  if (!fullscreenReady && fullscreenError) {
    return (
      <Box sx={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', bgcolor: '#F8FAFC', p: 3 }}>
        <Paper elevation={3} sx={{ p: 4, textAlign: 'center', maxWidth: 520, borderRadius: 3 }}>
          <Box sx={{ fontSize: 56, mb: 1 }}>⛶</Box>
          <Typography variant="h6" fontWeight={700} gutterBottom color="warning.dark">
            Fullscreen Mode Required
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3, lineHeight: 1.6 }}>
            {fullscreenError}
          </Typography>
          <Alert severity="warning" sx={{ mb: 3, textAlign: 'left' }}>
            <Typography variant="caption" fontWeight={600}>
              This examination requires fullscreen mode. You cannot begin until fullscreen is enabled.
              Once active, do not exit fullscreen or switch tabs — both are recorded as HIGH-RISK violations.
            </Typography>
          </Alert>
          <Button
            variant="contained"
            color="warning"
            size="large"
            onClick={async () => {
              if (examSessionIdRef.current) {
                await requestFullscreenAndActivateMonitor(examSessionIdRef.current);
              }
            }}
            sx={{ px: 4, py: 1.2, fontWeight: 700, borderRadius: 2 }}
          >
            Enable Fullscreen &amp; Start Examination
          </Button>
        </Paper>
      </Box>
    );
  }

  if (mode === 'STRUCTURED' && sections.length === 0) {
    return (
      <Box sx={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', bgcolor: '#F8FAFC' }}>
        <Typography color="error" fontWeight={600}>Failed to load exam sections. Please contact your examination supervisor.</Typography>
      </Box>
    );
  }

  const currentSection = sections.length > 0 ? sections[currentSectionIdx] : null;
  const question = currentSection && currentSection.questions.length > 0 ? currentSection.questions[currentQ] : null;

  // Calculate overall palette stats
  let totalQuestions = 0;
  let answeredCount = 0;
  let flaggedCount = flagged.size;

  if (mode === 'STRUCTURED') {
    sections.forEach((sec, sIdx) => {
      sec.questions.forEach((_, qIdx) => {
        totalQuestions++;
        const qKey = `${sIdx}_${qIdx}`;
        const ans = answers[qKey];
        if (
          ans &&
          (ans.selected !== undefined ||
           (ans.selected_options && ans.selected_options.length > 0) ||
           (ans.text && ans.text.trim().length > 0))
        ) {
          answeredCount++;
        }
      });
    });
  }
  const remainingCount = mode === 'STRUCTURED' ? Math.max(0, totalQuestions - answeredCount) : 0;

  const currentQKey = `${currentSectionIdx}_${currentQ}`;
  const currentSaveStatus = saveStatuses[currentQKey] || 'idle';

  const isFirst = currentSectionIdx === 0 && currentQ === 0;
  const isLast = mode === 'STRUCTURED' && currentSectionIdx === sections.length - 1 && currentSection && currentQ === currentSection.questions.length - 1;

  const goNext = () => {
    if (mode !== 'STRUCTURED' || !currentSection) return;
    if (currentQ < currentSection.questions.length - 1) {
      handleNavigation(currentSectionIdx, currentQ + 1);
    } else if (currentSectionIdx < sections.length - 1) {
      if (currentSection.require_completion_before_next || currentSection.navigation_policy === 'SEQUENTIAL') {
        setSectionSubmitDialogOpen(true);
      } else {
        handleNavigation(currentSectionIdx + 1, 0);
      }
    }
  };

  const goPrev = () => {
    if (mode !== 'STRUCTURED' || !currentSection) return;
    if (currentQ > 0) {
      if (currentSection.navigation_policy === 'SEQUENTIAL' && currentSection.allow_return_to_previous === false) {
        setNavigationError("Sequential question policy is enforced. You cannot return to previous questions in this section.");
        return;
      }
      handleNavigation(currentSectionIdx, currentQ - 1);
    } else if (currentSectionIdx > 0) {
      if (currentSection.allow_return_to_previous === false || lockedSections.has(currentSectionIdx - 1)) {
        setNavigationError("Previous section is locked and cannot be reopened.");
        return;
      }
      const prevSec = sections[currentSectionIdx - 1];
      handleNavigation(currentSectionIdx - 1, prevSec.questions.length - 1);
    }
  };

  const getQuestionButtonSx = (sIdx: number, qIdx: number, isDisabled?: boolean) => {
    const qKey = `${sIdx}_${qIdx}`;
    const isCurrent = currentSectionIdx === sIdx && currentQ === qIdx;
    const ans = answers[qKey];
    const isAns = ans && (
      ans.selected !== undefined ||
      (ans.selected_options && ans.selected_options.length > 0) ||
      (ans.text && ans.text.trim().length > 0)
    );
    const isFlg = flagged.has(qKey);

    return {
      width: 40, height: 40, minWidth: 40, p: 0,
      borderRadius: 1.5,
      fontSize: '0.85rem',
      fontWeight: 700,
      opacity: isDisabled ? 0.4 : 1,
      border: isCurrent ? '2px solid' : '1px solid',
      borderColor: isCurrent ? 'primary.main' : isFlg ? 'warning.main' : isAns ? 'success.main' : 'divider',
      backgroundColor: isCurrent ? 'primary.main' : isFlg ? '#FFF3E0' : isAns ? '#E8F5E9' : isDisabled ? '#F1F5F9' : 'background.paper',
      color: isCurrent ? 'white' : isFlg ? 'warning.dark' : isAns ? 'success.dark' : 'text.secondary',
      boxShadow: isCurrent ? '0 2px 6px rgba(37,99,235,0.25)' : 'none',
      '&:hover': { backgroundColor: isCurrent ? 'primary.dark' : isDisabled ? '#F1F5F9' : 'action.hover' },
    };
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', bgcolor: '#F8FAFC' }}>
      {/* Recovery Toast Banner */}
      <Snackbar
        open={Boolean(recoveredDraftNotice)}
        autoHideDuration={6000}
        onClose={() => setRecoveredDraftNotice(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert severity="info" icon={<HistoryEduIcon />} onClose={() => setRecoveredDraftNotice(null)} sx={{ borderRadius: 2, fontWeight: 600 }}>
          {recoveredDraftNotice}
        </Alert>
      </Snackbar>

      {/* Navigation Error / Restriction Toast */}
      <Snackbar
        open={Boolean(navigationError)}
        autoHideDuration={5000}
        onClose={() => setNavigationError(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert severity="warning" onClose={() => setNavigationError(null)} sx={{ borderRadius: 2, fontWeight: 700 }}>
          {navigationError}
        </Alert>
      </Snackbar>

      {/* Exam Top Bar */}
      <AppBar position="sticky" elevation={1} sx={{ backgroundColor: '#0F172A', color: 'white' }}>
        <Toolbar sx={{ gap: 2 }}>
          <Typography variant="subtitle1" fontWeight={700} sx={{ flexGrow: 0, mr: 2, display: { xs: 'none', sm: 'block' } }}>
            {examTitle}
          </Typography>
          <Box sx={{ flexGrow: 1, textAlign: 'center' }}>
            <Typography variant="body2" sx={{ opacity: 0.85, fontWeight: 500 }}>
              {mode === 'STRUCTURED' ? `Section: ${currentSection?.section_name || 'General'} | Question ${currentQ + 1} of ${currentSection?.questions.length || 1}` : 'FILE Examination Mode'}
            </Typography>
          </Box>

          {/* Network Status Badge */}
          {!isOnline && (
            <Chip
              icon={<WifiOffIcon sx={{ color: 'white !important' }} />}
              label="Offline (Saved Locally)"
              color="warning"
              size="small"
              sx={{ fontWeight: 700 }}
            />
          )}

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2, py: 0.5, borderRadius: 2, bgcolor: timeLeft < 300 ? 'rgba(239,68,68,0.2)' : 'rgba(255,255,255,0.08)' }}>
            <TimerIcon fontSize="small" sx={{ color: timeLeft < 300 ? '#EF4444' : '#60A5FA' }} />
            <Typography variant="subtitle1" fontWeight={700} sx={{ fontFamily: 'monospace', color: timeLeft < 300 ? '#EF4444' : 'white' }}>
              {formatTime(timeLeft)}
            </Typography>
          </Box>
        </Toolbar>
        {mode === 'STRUCTURED' && totalQuestions > 0 && (
          <LinearProgress
            variant="determinate"
            value={(answeredCount / totalQuestions) * 100}
            sx={{ height: 3, backgroundColor: 'rgba(255,255,255,0.15)', '& .MuiLinearProgress-bar': { backgroundColor: '#3B82F6' } }}
          />
        )}
      </AppBar>

      <Box sx={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
        {/* Left Navigation Palette */}
        <Paper
          elevation={0}
          sx={{
            width: 280, flexShrink: 0,
            borderRight: '1px solid', borderColor: 'divider',
            borderRadius: 0,
            backgroundColor: '#FFFFFF',
            display: { xs: 'none', md: 'flex' },
            flexDirection: 'column',
            p: 2.5,
            overflowY: 'auto',
          }}
        >
          {mode === 'STRUCTURED' ? (
            <>
              <Typography variant="caption" fontWeight={700} color="text.secondary" sx={{ mb: 2, textTransform: 'uppercase', letterSpacing: 1.1 }}>
                Question Palette
              </Typography>
              
              {sections.map((sec, sIdx) => {
                const isSectionLocked = lockedSections.has(sIdx);
                const isFutureLocked = sIdx > currentSectionIdx && (sec.require_completion_before_next || sections[currentSectionIdx]?.require_completion_before_next || sec.navigation_policy === 'SEQUENTIAL');
                const isSectionInaccessible = isSectionLocked || isFutureLocked;

                return (
                  <Box key={sec.id || sIdx} sx={{ mb: 2.5, opacity: isSectionInaccessible && sIdx !== currentSectionIdx ? 0.65 : 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.2 }}>
                      <Typography variant="body2" fontWeight={700} sx={{ color: sIdx === currentSectionIdx ? 'primary.main' : '#1E293B', fontSize: '0.825rem' }}>
                        {sec.section_name}
                      </Typography>
                      {isSectionLocked && (
                        <Chip
                          icon={<LockIcon sx={{ fontSize: '11px !important', color: '#DC2626 !important' }} />}
                          label="Locked"
                          size="small"
                          sx={{ height: 18, fontSize: '0.6rem', fontWeight: 700, bgcolor: '#FEE2E2', color: '#DC2626' }}
                        />
                      )}
                      {isFutureLocked && !isSectionLocked && (
                        <Chip
                          icon={<LockIcon sx={{ fontSize: '11px !important', color: '#64748B !important' }} />}
                          label="Upcoming"
                          size="small"
                          sx={{ height: 18, fontSize: '0.6rem', fontWeight: 700, bgcolor: '#F1F5F9', color: '#64748B' }}
                        />
                      )}
                    </Box>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {sec.questions.map((q, qIdx) => {
                        const isButtonDisabled = isSectionInaccessible && sIdx !== currentSectionIdx;
                        return (
                          <Button
                            key={q.id || qIdx}
                            disabled={isButtonDisabled}
                            onClick={() => handleNavigation(sIdx, qIdx)}
                            sx={getQuestionButtonSx(sIdx, qIdx, isButtonDisabled)}
                          >
                            {qIdx + 1}
                          </Button>
                        );
                      })}
                    </Box>
                  </Box>
                );
              })}

              <Divider sx={{ mb: 2.5 }} />

              {/* Real-time CandidateAnswer Status Breakdown */}
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 3, bgcolor: '#F8FAFC', p: 1.5, borderRadius: 2, border: '1px solid #E2E8F0' }}>
                <Typography variant="caption" sx={{ color: 'success.dark', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 0.8 }}>
                  ● Answered: {answeredCount}
                </Typography>
                <Typography variant="caption" sx={{ color: 'warning.dark', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 0.8 }}>
                  ⚑ Marked for Review: {flaggedCount}
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 0.8 }}>
                  ○ Unanswered: {remainingCount}
                </Typography>
              </Box>
            </>
          ) : (
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="caption" fontWeight={700} color="text.secondary" sx={{ mb: 1.5, textTransform: 'uppercase', letterSpacing: 1 }}>
                File Examination Mode
              </Typography>
              <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary', lineHeight: 1.6 }}>
                Review the assigned examination document and submit your responses according to supervisor instructions.
              </Typography>
            </Box>
          )}

          <Box sx={{ flexGrow: 1 }} />

          {/* Background Camera Lifecycle (Student preview hidden) */}
          <video
            ref={attachMonitoringVideo}
            autoPlay
            playsInline
            muted
            style={{ display: 'none' }}
            aria-hidden="true"
          />
        </Paper>

        {/* Dynamic Question Content Panel */}
        <Box sx={{ flexGrow: 1, overflow: 'auto', p: { xs: 2, md: 4 } }}>
          {mode === 'FILE' ? (
            <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
              <iframe 
                src={`${apiClient.defaults.baseURL}${fileUrl}`} 
                style={{ width: '100%', flexGrow: 1, border: 'none', borderRadius: '12px', minHeight: '600px' }}
                title="Examination Document"
              />
            </Box>
          ) : question && (
            <Box sx={{ maxWidth: 780, mx: 'auto' }}>
              {/* Question Header & Dual-Layer Save Status Indicator (Phase 12) */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="caption" color="text.secondary" fontWeight={700} sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                  Section: {currentSection?.section_name} | Question {currentQ + 1}
                </Typography>
                
                {/* Save Status Indicators */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8 }}>
                  {currentSaveStatus === 'saving' && (
                    <Chip
                      icon={<SyncIcon sx={{ animation: 'spin 1.2s linear infinite', '@keyframes spin': { '0%': { transform: 'rotate(0deg)' }, '100%': { transform: 'rotate(360deg)' } } }} />}
                      label="Saving response..."
                      size="small"
                      variant="outlined"
                      color="info"
                    />
                  )}
                  {currentSaveStatus === 'syncing' && (
                    <Chip
                      icon={<SyncIcon sx={{ animation: 'spin 1.2s linear infinite', '@keyframes spin': { '0%': { transform: 'rotate(0deg)' }, '100%': { transform: 'rotate(360deg)' } } }} />}
                      label="Reconnecting & Syncing..."
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  )}
                  {currentSaveStatus === 'saved' && (
                    <Chip
                      icon={<CloudDoneIcon />}
                      label="Saved"
                      size="small"
                      color="success"
                      variant="outlined"
                      sx={{ fontWeight: 600 }}
                    />
                  )}
                  {currentSaveStatus === 'offline' && (
                    <Chip
                      icon={<WifiOffIcon />}
                      label="Offline (Saved Locally)"
                      size="small"
                      color="warning"
                      variant="outlined"
                      sx={{ fontWeight: 600 }}
                    />
                  )}
                  {currentSaveStatus === 'error' && (
                    <Button
                      size="small"
                      color="error"
                      variant="outlined"
                      startIcon={<ErrorOutlineIcon />}
                      onClick={() => {
                        const currentAns = answers[currentQKey] || {};
                        saveCandidateAnswer(currentSectionIdx, currentQ, currentAns, flagged.has(currentQKey));
                      }}
                    >
                      Autosave failed (Retry)
                    </Button>
                  )}
                </Box>
              </Box>

              <Card variant="outlined" sx={{ borderRadius: 3, p: 3, mb: 3, borderColor: '#CBD5E1', bgcolor: '#FFFFFF' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Typography variant="h6" fontWeight={600} sx={{ color: '#0F172A', lineHeight: 1.5 }}>
                    {question.text}
                  </Typography>
                  {question.marks !== undefined && (
                    <Chip label={`${question.marks} Marks`} size="small" color="primary" variant="outlined" sx={{ fontWeight: 700, ml: 2, flexShrink: 0 }} />
                  )}
                </Box>

                {/* Optional Question Image Attachment */}
                {question.image_url && (
                  <Box sx={{ my: 2, borderRadius: 2, overflow: 'hidden', maxWidth: '100%', border: '1px solid #E2E8F0' }}>
                    <img src={question.image_url} alt="Question Diagram" style={{ maxWidth: '100%', height: 'auto', display: 'block' }} />
                  </Box>
                )}

                {/* DYNAMIC QUESTION RENDERER ENGINE */}
                
                {/* 1. Single-Choice MCQ (Radio Buttons) */}
                {(question.question_type === 'MCQ' || question.question_type === 'SINGLE_CHOICE') && (
                  <FormControl fullWidth sx={{ mt: 2 }}>
                    <RadioGroup
                      value={answers[currentQKey]?.selected !== undefined ? String(answers[currentQKey].selected) : ''}
                      onChange={(e) => handleSingleChoiceAnswer(currentSectionIdx, currentQ, parseInt(e.target.value))}
                    >
                      {question.options.map((optText, optIdx) => (
                        <Paper
                          key={optIdx}
                          elevation={0}
                          sx={{
                            mb: 1.5,
                            border: '1.5px solid',
                            borderColor: answers[currentQKey]?.selected === optIdx ? 'primary.main' : '#E2E8F0',
                            backgroundColor: answers[currentQKey]?.selected === optIdx ? '#EFF6FF' : '#FFFFFF',
                            borderRadius: 2.5,
                            transition: 'all 0.15s ease-in-out',
                            '&:hover': { borderColor: 'primary.light', backgroundColor: '#F8FAFC' },
                          }}
                        >
                          <FormControlLabel
                            value={String(optIdx)}
                            control={<Radio size="small" color="primary" />}
                            label={<Typography variant="body1" sx={{ fontWeight: answers[currentQKey]?.selected === optIdx ? 600 : 400, color: '#1E293B' }}>{optText}</Typography>}
                            sx={{ px: 2, py: 1.2, width: '100%', m: 0 }}
                          />
                        </Paper>
                      ))}
                    </RadioGroup>
                  </FormControl>
                )}

                {/* 2. Multiple-Choice Checkboxes */}
                {question.question_type === 'MULTIPLE_CHOICE' && (
                  <FormControl fullWidth sx={{ mt: 2 }}>
                    <FormGroup>
                      {question.options.map((optText, optIdx) => {
                        const selectedList = answers[currentQKey]?.selected_options || [];
                        const isChecked = selectedList.includes(optIdx);
                        return (
                          <Paper
                            key={optIdx}
                            elevation={0}
                            sx={{
                              mb: 1.5,
                              border: '1.5px solid',
                              borderColor: isChecked ? 'primary.main' : '#E2E8F0',
                              backgroundColor: isChecked ? '#EFF6FF' : '#FFFFFF',
                              borderRadius: 2.5,
                              transition: 'all 0.15s ease-in-out',
                              '&:hover': { borderColor: 'primary.light', backgroundColor: '#F8FAFC' },
                            }}
                          >
                            <FormControlLabel
                              control={
                                <Checkbox
                                  checked={isChecked}
                                  onChange={() => handleMultiChoiceAnswer(currentSectionIdx, currentQ, optIdx)}
                                  size="small"
                                  color="primary"
                                />
                              }
                              label={<Typography variant="body1" sx={{ fontWeight: isChecked ? 600 : 400, color: '#1E293B' }}>{optText}</Typography>}
                              sx={{ px: 2, py: 1.2, width: '100%', m: 0 }}
                            />
                          </Paper>
                        );
                      })}
                    </FormGroup>
                  </FormControl>
                )}

                {/* 3. Subjective / Short Answer / Essay (Multiline Textarea with Dual-Layer Persistence) */}
                {(question.question_type === 'SUBJECTIVE' || question.question_type === 'SHORT_ANSWER' || question.question_type === 'ESSAY') && (
                  <Box sx={{ mt: 2 }}>
                    <TextField
                      multiline
                      rows={7}
                      fullWidth
                      placeholder="Type your response explanation here..."
                      variant="outlined"
                      value={answers[currentQKey]?.text || ''}
                      onChange={(e) => handleTextAnswer(currentSectionIdx, currentQ, e.target.value)}
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          borderRadius: 2.5,
                          bgcolor: '#FFFFFF',
                          fontFamily: 'inherit',
                        }
                      }}
                    />
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, textAlign: 'right' }}>
                      Word count: {(answers[currentQKey]?.text || '').trim().split(/\s+/).filter(Boolean).length}
                    </Typography>
                  </Box>
                )}
              </Card>

              {/* Question Action Controls */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Button
                  size="small"
                  startIcon={<FlagIcon />}
                  onClick={() => toggleFlag(currentSectionIdx, currentQ)}
                  sx={{
                    color: flagged.has(currentQKey) ? 'warning.dark' : 'text.secondary',
                    borderColor: flagged.has(currentQKey) ? 'warning.main' : '#CBD5E1',
                    bgcolor: flagged.has(currentQKey) ? '#FFF3E0' : 'transparent',
                    '&:hover': { bgcolor: '#FFE0B2' }
                  }}
                  variant="outlined"
                >
                  {flagged.has(currentQKey) ? 'Unmark Review' : 'Mark for Review'}
                </Button>

                {/* Section Step Controls */}
                <Stack direction="row" spacing={2}>
                  <Button
                    variant="outlined"
                    startIcon={<NavigateBeforeIcon />}
                    disabled={isFirst || (currentSection?.navigation_policy === 'SEQUENTIAL' && currentSection?.allow_return_to_previous === false && currentQ === 0)}
                    onClick={goPrev}
                  >
                    Previous
                  </Button>
                  {currentQ === currentSection.questions.length - 1 && currentSectionIdx < sections.length - 1 && (currentSection.require_completion_before_next || currentSection.navigation_policy === 'SEQUENTIAL') ? (
                    <Button
                      variant="contained"
                      color="primary"
                      endIcon={<NavigateNextIcon />}
                      onClick={() => setSectionSubmitDialogOpen(true)}
                      sx={{ fontWeight: 700 }}
                    >
                      Complete Session & Proceed
                    </Button>
                  ) : !isLast ? (
                    <Button
                      variant="contained"
                      endIcon={<NavigateNextIcon />}
                      onClick={goNext}
                    >
                      Next Question
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
                </Stack>
              </Box>
            </Box>
          )}
        </Box>
      </Box>

      {/* Floating Submit FAB Button */}
      <Tooltip title="Submit Examination" placement="left">
        <Button
          variant="contained"
          color="primary"
          onClick={() => setSubmitOpen(true)}
          startIcon={<SendIcon />}
          sx={{
            position: 'fixed', bottom: 28, right: 28,
            boxShadow: '0 4px 14px rgba(37,99,235,0.35)', zIndex: 999,
            borderRadius: 3, px: 3, py: 1.2, fontWeight: 700,
            display: { xs: 'none', md: 'flex' },
          }}
        >
          Submit Exam
        </Button>
      </Tooltip>

      {/* Section / Session Completion Confirmation Dialog */}
      <Dialog
        open={sectionSubmitDialogOpen}
        onClose={() => !submittingSection && setSectionSubmitDialogOpen(false)}
        maxWidth="xs"
        fullWidth
        PaperProps={{ sx: { borderRadius: 3, p: 1 } }}
      >
        <DialogTitle fontWeight={700}>
          Complete & Lock {currentSection?.section_name || `Session ${currentSectionIdx + 1}`}?
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ color: 'text.secondary', fontSize: '0.9rem', lineHeight: 1.6 }}>
            You are about to complete and lock <strong>{currentSection?.section_name || `Session ${currentSectionIdx + 1}`}</strong>.
            <br /><br />
            Once submitted, your answers for this session will be finalized and locked. You will immediately proceed to <strong>{sections[currentSectionIdx + 1]?.section_name || `Session ${currentSectionIdx + 2}`}</strong>.
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setSectionSubmitDialogOpen(false)}
            disabled={submittingSection}
            sx={{ fontWeight: 600 }}
          >
            Review Session
          </Button>
          <Button
            variant="contained"
            color="primary"
            disabled={submittingSection}
            onClick={handleCompleteSection}
            sx={{ borderRadius: 2, fontWeight: 700 }}
          >
            {submittingSection ? "Locking & Advancing..." : "Submit Session & Proceed"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Submit Confirmation Dialog */}
      <Dialog open={submitOpen} onClose={() => setSubmitOpen(false)} maxWidth="xs" fullWidth PaperProps={{ sx: { borderRadius: 3, p: 1 } }}>
        <DialogTitle fontWeight={700}>Submit Examination?</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, my: 1 }}>
            {mode === 'STRUCTURED' && (
              <>
                <Chip label={`✓ Answered: ${answeredCount} of ${totalQuestions}`} color="success" variant="outlined" sx={{ fontWeight: 600 }} />
                <Chip label={`⚑ Marked for Review: ${flaggedCount} questions`} color="warning" variant="outlined" sx={{ fontWeight: 600 }} />
                <Chip label={`○ Unanswered: ${remainingCount} questions`} color="default" variant="outlined" sx={{ fontWeight: 600 }} />
              </>
            )}
            <DialogContentText sx={{ mt: 1, fontSize: '0.9rem' }}>
              Are you sure you want to finalize and submit your examination? Once submitted, no further changes can be made.
            </DialogContentText>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setSubmitOpen(false)} disabled={submitting} sx={{ fontWeight: 600 }}>Cancel</Button>
          <Button variant="contained" color="primary" disabled={submitting} onClick={handleSubmit} sx={{ borderRadius: 2, fontWeight: 700 }}>
            {submitting ? "Submitting..." : "Yes, Submit Exam"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Full-Screen Session Suspension Overlay */}
      {(isSuspended || !isOnline) && (
        <Box
          sx={{
            position: 'fixed',
            top: 0, left: 0, right: 0, bottom: 0,
            zIndex: 999999,
            bgcolor: '#0F172A',
            color: '#FFFFFF',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            p: 4,
            textAlign: 'center'
          }}
        >
          <Paper
            elevation={24}
            sx={{
              p: 5,
              maxWidth: 600,
              borderRadius: 3,
              bgcolor: '#1E293B',
              color: '#FFFFFF',
              border: '1px solid #334155',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 2.5
            }}
          >
            <LockIcon sx={{ fontSize: 72, color: '#EF4444' }} />
            <Typography variant="h5" fontWeight={800} sx={{ color: '#F8FAFC' }}>
              Examination Temporarily Suspended
            </Typography>
            <Typography variant="body1" sx={{ color: '#94A3B8', lineHeight: 1.7, fontSize: '0.95rem' }}>
              Connection with the examination server has been lost.
              The examination has been locked to preserve academic integrity.
              The timer has been paused.
              Your answers have been saved.
              The examination will automatically resume once monitoring and server connectivity are restored.
            </Typography>
            <Alert severity="warning" icon={<SyncIcon sx={{ animation: 'spin 1.5s linear infinite' }} />} sx={{ width: '100%', mt: 1, bgcolor: 'rgba(245, 158, 11, 0.15)', color: '#FCD34D', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
              Please do not refresh or close this page. Automatic reconnection in progress...
            </Alert>
            <CircularProgress size={32} sx={{ color: '#60A5FA', mt: 1 }} />
          </Paper>
        </Box>
      )}

      {/* ─── Exam Environment Violation Warning Snackbar ──────────────────── */}
      {/* Shown when student returns to exam after a tab switch / fullscreen exit */}
      {showViolationWarning && (
        <Box
          sx={{
            position: 'fixed',
            bottom: 24,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 99998,
            maxWidth: 540,
            width: '90vw',
          }}
        >
          <Alert
            severity="error"
            onClose={() => setShowViolationWarning(false)}
            sx={{
              boxShadow: '0 8px 32px rgba(239,68,68,0.35)',
              borderRadius: 2,
              border: '1.5px solid',
              borderColor: 'error.main',
              '& .MuiAlert-message': { width: '100%' }
            }}
          >
            <Typography variant="subtitle2" fontWeight={700} gutterBottom>
              ⚠ High-Risk Violation Recorded
            </Typography>
            <Typography variant="caption" display="block" sx={{ lineHeight: 1.5 }}>
              You left the controlled examination environment. This event has been recorded
              with its duration and is immediately visible to the examiner. Please remain
              in fullscreen and do not switch tabs for the remainder of the examination.
            </Typography>
          </Alert>
        </Box>
      )}

      {/* ─── Fullscreen Recovery Blocking Overlay (Issue 2) ────────────────── */}
      {fullscreenReady && !isAlreadySubmitted && fullscreenRecoveryRequired && (
        <Box
          sx={{
            position: 'fixed',
            top: 0, left: 0, right: 0, bottom: 0,
            zIndex: 999999,
            bgcolor: 'rgba(15, 23, 42, 0.96)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            p: 3,
            textAlign: 'center'
          }}
        >
          <Paper
            elevation={24}
            sx={{
              p: 4.5,
              maxWidth: 540,
              borderRadius: 3,
              bgcolor: '#1E293B',
              color: '#FFFFFF',
              border: '2px solid #EF4444',
              boxShadow: '0 25px 50px -12px rgba(239, 68, 68, 0.25)'
            }}
          >
            <LockIcon sx={{ fontSize: 64, color: '#EF4444', mb: 2 }} />
            <Typography variant="h5" fontWeight={800} gutterBottom sx={{ color: '#F8FAFC' }}>
              Fullscreen Mode Required
            </Typography>
            <Typography variant="body1" sx={{ color: '#94A3B8', mb: 2.5, lineHeight: 1.6, fontSize: '0.95rem' }}>
              You have returned to the examination, but fullscreen mode is no longer active.
              You must return to fullscreen before continuing the examination.
            </Typography>
            <Alert
              severity="error"
              sx={{
                mb: 3,
                bgcolor: 'rgba(239, 68, 68, 0.15)',
                color: '#FCA5A5',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                textAlign: 'left'
              }}
            >
              <Typography variant="caption" fontWeight={600}>
                This event has already been recorded as a HIGH-RISK exam-environment violation.
                Your answers remain safe. Click below to re-enter fullscreen and resume.
              </Typography>
            </Alert>
            <Button
              variant="contained"
              color="error"
              size="large"
              onClick={async () => {
                try {
                  await document.documentElement.requestFullscreen();
                  setFullscreenRecoveryRequired(false);
                  setFullscreenReady(true);
                  envMonitorRef.current.resolveIncidentIfEnvironmentRestored();
                } catch (err) {
                  console.warn("Fullscreen recovery click rejected:", err);
                }
              }}
              sx={{
                px: 4,
                py: 1.5,
                fontWeight: 800,
                borderRadius: 2,
                fontSize: '1rem',
                textTransform: 'none',
                bgcolor: '#EF4444',
                '&:hover': { bgcolor: '#DC2626' }
              }}
            >
              Return to Fullscreen &amp; Continue Examination
            </Button>
          </Paper>
        </Box>
      )}
    </Box>
  );
};

export default OnlineExamPage;

