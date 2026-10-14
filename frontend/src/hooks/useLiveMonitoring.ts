import { useState, useEffect, useRef } from 'react';
import apiClient from '../services/apiClient';
import { WebSocketClient } from '../services/wsClient';
import { getErrorMessage } from '../utils/errorHandler';

export interface ViolationEvent {
  id?: number;
  type: string;
  time: string;
  severity: 'low' | 'medium' | 'high' | 'critical' | string;
  duration?: number;
  risk?: number;
}

export interface TimelineEvent {
  icon: string;
  text: string;
  time: string;
  severity?: string;
}

export interface DetectedObject {
  name: string;
  conf: number;
}

export interface LiveMonitoringState {
  riskScore: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  identityStatus: string;
  identityConfidence: number;
  gazeDirection: string;
  headPose: string;
  facesCount: number;
  detectedObjects: DetectedObject[];
  violations: ViolationEvent[];
  timeline: TimelineEvent[];
  liveFrameBase64: string | null;
  lastFrameTime: number;
  isCameraLive: boolean;
  isConnected: boolean;
  loading: boolean;
  error: string | null;
}

export function useLiveMonitoring(sessionId: number | string | null, enabled: boolean = true): LiveMonitoringState {
  const [riskScore, setRiskScore] = useState<number>(0);
  const [identityStatus, setIdentityStatus] = useState<string>('VERIFIED');
  const [identityConfidence, setIdentityConfidence] = useState<number>(98);
  const [gazeDirection, setGazeDirection] = useState<string>('CENTER');
  const [headPose, setHeadPose] = useState<string>('FORWARD');
  const [facesCount, setFacesCount] = useState<number>(1);
  const [detectedObjects, setDetectedObjects] = useState<DetectedObject[]>([]);
  const [violations, setViolations] = useState<ViolationEvent[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([
    { icon: '▶️', text: 'Exam session initialized & AI monitoring active', time: new Date().toLocaleTimeString() }
  ]);
  const [liveFrameBase64, setLiveFrameBase64] = useState<string | null>(null);
  const [lastFrameTime, setLastFrameTime] = useState<number>(Date.now());
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocketClient | null>(null);

  useEffect(() => {
    if (!enabled || !sessionId) {
      setLoading(false);
      return;
    }

    const numericSessionId = typeof sessionId === 'string' ? parseInt(sessionId, 10) : sessionId;
    if (isNaN(numericSessionId) || numericSessionId <= 0) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    // 1. Fetch initial snapshot from REST API
    const fetchInitialSnapshot = async () => {
      try {
        const res = await apiClient.get(`/monitoring/current?exam_session_id=${numericSessionId}`);
        if (res.data) {
          setRiskScore(res.data.current_risk_score || 0);
          setGazeDirection(res.data.current_gaze || 'CENTER');
          setHeadPose(res.data.current_head_pose || 'FORWARD');
          setIdentityStatus(res.data.current_face_status || 'VERIFIED');

          if (res.data.active_violations) {
            setViolations(res.data.active_violations.map((v: any) => ({
              id: v.id,
              type: v.violation_type,
              time: new Date(v.timestamp).toLocaleTimeString(),
              severity: (v.severity || 'medium').toLowerCase(),
              duration: v.duration_seconds || 0,
              risk: v.risk_score || 50
            })));
          }

          if (res.data.timeline_events && res.data.timeline_events.length > 0) {
            const mappedTimeline = res.data.timeline_events.map((e: any) => {
              let icon = 'ℹ️';
              if (e.severity === 'CRITICAL' || e.severity === 'HIGH') icon = '🔴';
              else if (e.event_type?.includes('FACE')) icon = '👀';
              else if (e.event_type?.includes('OBJECT') || e.event_type?.includes('PHONE')) icon = '📱';

              return {
                icon,
                text: e.description || e.event_type,
                time: new Date(e.timestamp).toLocaleTimeString(),
                severity: e.severity
              };
            });
            setTimeline(mappedTimeline);
          }
        }
      } catch (err: any) {
        console.warn('Initial monitoring snapshot query note:', getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    fetchInitialSnapshot();

    // 2. Connect to real-time Proctoring WebSocket
    try {
      const ws = new WebSocketClient(numericSessionId);
      wsRef.current = ws;
      setIsConnected(true);

      ws.onMessage((data: any) => {
        try {
          const timeStr = new Date().toLocaleTimeString();

          // Camera frame forwarding
          if (data.event === 'MONITORING_FRAME' && data.payload?.image_base64) {
            const rawB64 = data.payload.image_base64;
            const imgSrc = rawB64.startsWith('data:') ? rawB64 : `data:image/jpeg;base64,${rawB64}`;
            setLiveFrameBase64(imgSrc);
            setLastFrameTime(Date.now());
            return;
          }

          // Timeline event appending
          if (data.event && data.event !== 'HEARTBEAT') {
            let icon = 'ℹ️';
            let text = data.payload?.description || data.event;

            if (data.payload?.severity === 'CRITICAL' || data.payload?.severity === 'HIGH') icon = '🔴';
            else if (data.event.includes('FACE')) icon = '👀';
            else if (data.event.includes('OBJECT') || data.event.includes('PHONE')) icon = '📱';

            setTimeline((prev) => [{ icon, text, time: timeStr, severity: data.payload?.severity }, ...prev].slice(0, 50));
          }

          // Specific event payload processors
          switch (data.event) {
            case 'RISK_UPDATED':
              if (data.payload?.data?.risk_score !== undefined) {
                setRiskScore(data.payload.data.risk_score);
              }
              break;

            case 'VIOLATION_CREATED':
              setViolations((prev) => [{
                id: data.payload.violation_id,
                type: data.payload.violation_type || data.payload.description,
                time: timeStr,
                severity: (data.payload.severity || 'high').toLowerCase(),
                duration: data.payload.duration_seconds || 0,
                risk: data.payload.risk_score || 50
              }, ...prev]);
              break;

            case 'VIOLATION_UPDATED':
              setViolations((prev) => {
                const vId = data.payload.violation_id;
                const exists = prev.some((v) => v.id === vId);
                if (exists) {
                  return prev.map((v) => v.id === vId ? {
                    ...v,
                    duration: data.payload.duration_seconds,
                    risk: data.payload.risk_score,
                    severity: (data.payload.severity || v.severity).toLowerCase()
                  } : v);
                }
                return [{
                  id: vId,
                  type: data.payload.violation_type || data.payload.description,
                  time: timeStr,
                  severity: (data.payload.severity || 'high').toLowerCase(),
                  duration: data.payload.duration_seconds || 0,
                  risk: data.payload.risk_score || 50
                }, ...prev];
              });
              break;

            case 'FACE_STATUS_CHANGED':
              const faceData = data.payload?.data;
              if (faceData) {
                if (faceData.face_count !== undefined) setFacesCount(faceData.face_count);
                if (faceData.identity_verified !== undefined) {
                  setIdentityStatus(faceData.identity_verified ? 'VERIFIED' : 'MISMATCH DETECTED');
                  setIdentityConfidence(faceData.confidence || 0);
                }
                if (faceData.gaze_direction) setGazeDirection(faceData.gaze_direction);
                if (faceData.head_pose) setHeadPose(faceData.head_pose);
              }
              break;

            case 'LOOKING_AWAY':
              if (data.payload?.data?.attention_state) {
                setGazeDirection(data.payload.data.attention_state);
              } else {
                setGazeDirection('LOOKING_AWAY');
              }
              break;

            case 'NO_FACE':
              setFacesCount(0);
              setIdentityStatus('NO FACE DETECTED');
              setGazeDirection('NO_FACE');
              break;

            case 'OBJECT_STATUS_CHANGED':
              const objData = data.payload?.data;
              if (objData && objData.objects) {
                setDetectedObjects(objData.objects.map((o: any) => ({ name: o.label || o.name, conf: o.confidence || 0 })));
              }
              break;
          }
        } catch (e) {
          console.error('WebSocket message parsing error:', e);
        }
      });

      ws.connect();
    } catch (err: any) {
      console.error('Failed to establish live monitoring WebSocket:', err);
      setIsConnected(false);
      setError(getErrorMessage(err));
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
      }
      setIsConnected(false);
    };
  }, [sessionId, enabled]);

  // Compute derived state
  const isCameraLive = Date.now() - lastFrameTime < 8000;
  const riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' =
    riskScore >= 75 ? 'CRITICAL' : riskScore >= 50 ? 'HIGH' : riskScore >= 25 ? 'MEDIUM' : 'LOW';

  return {
    riskScore,
    riskLevel,
    identityStatus,
    identityConfidence,
    gazeDirection,
    headPose,
    facesCount,
    detectedObjects,
    violations,
    timeline,
    liveFrameBase64,
    lastFrameTime,
    isCameraLive,
    isConnected,
    loading,
    error
  };
}
