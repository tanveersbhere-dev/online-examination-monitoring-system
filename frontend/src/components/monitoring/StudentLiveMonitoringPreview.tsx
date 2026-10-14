import React, { useState } from 'react';
import {
  Box, Typography, Paper, Chip, LinearProgress, Divider, Stack,
  IconButton, Tooltip, Collapse, Alert, Badge
} from '@mui/material';
import VideocamIcon from '@mui/icons-material/Videocam';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import ShieldIcon from '@mui/icons-material/Shield';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import WifiIcon from '@mui/icons-material/Wifi';
import WifiOffIcon from '@mui/icons-material/WifiOff';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import ScienceIcon from '@mui/icons-material/Science';
import PersonOutlineIcon from '@mui/icons-material/PersonOutline';
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid';

import { useLiveMonitoring } from '../../hooks/useLiveMonitoring';

interface StudentLiveMonitoringPreviewProps {
  examSessionId: number | string | null;
}

export default function StudentLiveMonitoringPreview({ examSessionId }: StudentLiveMonitoringPreviewProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'stream' | 'violations' | 'timeline'>('stream');

  const {
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
    isCameraLive,
    isConnected,
    loading
  } = useLiveMonitoring(examSessionId, true);

  const riskColor =
    riskScore >= 75 ? '#DC2626' : riskScore >= 50 ? '#D97706' : riskScore >= 25 ? '#F59E0B' : '#059669';
  const riskBg =
    riskScore >= 75 ? '#FEE2E2' : riskScore >= 50 ? '#FEF3C7' : riskScore >= 25 ? '#FEF9C3' : '#D1FAE5';

  // Floating AI-monitoring badge is disabled in student UI until external monitoring integration is connected
  const ENABLE_STUDENT_FLOATING_BADGE = false;
  if (!ENABLE_STUDENT_FLOATING_BADGE) {
    return null;
  }

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 16,
        right: 16,
        zIndex: 1200,
        width: isExpanded ? { xs: 'calc(100vw - 32px)', sm: 380, md: 400 } : 'auto',
        maxWidth: '100vw',
        boxShadow: '0 12px 36px rgba(0, 0, 0, 0.25)',
        borderRadius: 3,
        overflow: 'hidden',
        border: '1px solid rgba(226, 232, 240, 0.9)',
        backgroundColor: '#FFFFFF',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      }}
    >
      {/* ── Top Header / Dev Badge Bar ───────────────────────────────── */}
      <Box
        sx={{
          px: 2,
          py: 1.25,
          background: 'linear-gradient(135deg, #1E293B 0%, #0F172A 100%)',
          color: '#FFFFFF',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          userSelect: 'none'
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ScienceIcon sx={{ fontSize: 18, color: '#38BDF8' }} />
          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, fontSize: '0.8rem', lineHeight: 1.2, letterSpacing: '-0.01em' }}>
              Examiner Monitoring Mirror
            </Typography>
            <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.65rem', display: 'block' }}>
              DEV/TEST PREVIEW • READ-ONLY
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {/* Live stream badge */}
          <Chip
            icon={<FiberManualRecordIcon sx={{ fontSize: '8px !important', color: isCameraLive ? '#22C55E !important' : '#EF4444 !important' }} />}
            label={isCameraLive ? 'LIVE' : 'IDLE'}
            size="small"
            sx={{
              height: 20,
              fontSize: '0.65rem',
              fontWeight: 700,
              backgroundColor: isCameraLive ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              color: isCameraLive ? '#4ADE80' : '#F87171',
              border: `1px solid ${isCameraLive ? 'rgba(74, 222, 128, 0.3)' : 'rgba(248, 113, 113, 0.3)'}`
            }}
          />

          {/* Risk Badge */}
          <Chip
            label={`Risk: ${Math.round(riskScore)}`}
            size="small"
            sx={{
              height: 20,
              fontSize: '0.65rem',
              fontWeight: 700,
              backgroundColor: riskBg,
              color: riskColor
            }}
          />

          <IconButton size="small" sx={{ color: '#E2E8F0', p: 0.25 }}>
            {isExpanded ? <KeyboardArrowDownIcon fontSize="small" /> : <KeyboardArrowUpIcon fontSize="small" />}
          </IconButton>
        </Box>
      </Box>

      {/* ── Collapsible Body ────────────────────────────────────────── */}
      <Collapse in={isExpanded} timeout="auto">
        <Box sx={{ maxHeight: 520, overflowY: 'auto', p: 2, bgcolor: '#F8FAFC' }}>
          {/* Informational Banner */}
          <Alert
            severity="info"
            icon={<ShieldIcon fontSize="inherit" />}
            sx={{
              mb: 2,
              py: 0.5,
              fontSize: '0.72rem',
              borderRadius: 2,
              '& .MuiAlert-message': { p: 0.25 }
            }}
          >
            This mirror displays the <strong>exact live AI monitoring stream</strong> visible to supervisors during your exam.
          </Alert>

          {/* Navigation Pill Tabs */}
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <Chip
              label="Live Feed & HUD"
              size="small"
              onClick={() => setActiveTab('stream')}
              color={activeTab === 'stream' ? 'primary' : 'default'}
              variant={activeTab === 'stream' ? 'filled' : 'outlined'}
              sx={{ fontWeight: 600, fontSize: '0.7rem' }}
            />
            <Chip
              label={`Violations (${violations.length})`}
              size="small"
              onClick={() => setActiveTab('violations')}
              color={activeTab === 'violations' ? 'error' : 'default'}
              variant={activeTab === 'violations' ? 'filled' : 'outlined'}
              sx={{ fontWeight: 600, fontSize: '0.7rem' }}
            />
            <Chip
              label="Event Timeline"
              size="small"
              onClick={() => setActiveTab('timeline')}
              color={activeTab === 'timeline' ? 'info' : 'default'}
              variant={activeTab === 'timeline' ? 'filled' : 'outlined'}
              sx={{ fontWeight: 600, fontSize: '0.7rem' }}
            />
          </Box>

          {/* ── TAB 1: STREAM & TELEMETRY HUD ───────────────────────────── */}
          {activeTab === 'stream' && (
            <Stack spacing={2}>
              {/* Video Frame Card */}
              <Paper
                elevation={0}
                sx={{
                  position: 'relative',
                  width: '100%',
                  aspectRatio: '4/3',
                  backgroundColor: '#0A0E1A',
                  borderRadius: 2.5,
                  overflow: 'hidden',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '1px solid #CBD5E1'
                }}
              >
                {liveFrameBase64 && isCameraLive ? (
                  <img
                    src={liveFrameBase64}
                    alt="Proctoring Feed"
                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                  />
                ) : (
                  <Box sx={{ textAlign: 'center', p: 2 }}>
                    <VideocamIcon sx={{ fontSize: 44, color: 'rgba(255,255,255,0.2)', mb: 0.5 }} />
                    <Typography variant="caption" sx={{ color: '#94A3B8', display: 'block', fontSize: '0.75rem' }}>
                      Streaming camera frame to AI engine...
                    </Typography>
                  </Box>
                )}

                {/* Identity Tag Overlay */}
                <Chip
                  label={`ID: ${identityStatus}`}
                  size="small"
                  sx={{
                    position: 'absolute',
                    top: 8,
                    left: 8,
                    height: 20,
                    fontSize: '0.625rem',
                    fontWeight: 700,
                    backgroundColor: identityStatus === 'VERIFIED' ? 'rgba(5, 150, 105, 0.9)' : 'rgba(220, 38, 38, 0.9)',
                    color: '#FFFFFF'
                  }}
                />

                {/* Faces count overlay */}
                <Chip
                  icon={<PersonOutlineIcon sx={{ fontSize: '12px !important', color: '#FFF !important' }} />}
                  label={`Faces: ${facesCount}`}
                  size="small"
                  sx={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    height: 20,
                    fontSize: '0.625rem',
                    fontWeight: 700,
                    backgroundColor: facesCount === 1 ? 'rgba(15, 23, 42, 0.85)' : 'rgba(220, 38, 38, 0.9)',
                    color: '#FFFFFF'
                  }}
                />

                {/* Gaze & Pose HUD Bottom Bar */}
                <Box
                  sx={{
                    position: 'absolute',
                    bottom: 8,
                    left: 8,
                    right: 8,
                    display: 'flex',
                    justifyContent: 'space-between',
                    backgroundColor: 'rgba(15, 23, 42, 0.85)',
                    px: 1.25,
                    py: 0.5,
                    borderRadius: 1.5,
                    backdropFilter: 'blur(4px)'
                  }}
                >
                  <Typography sx={{ color: '#E2E8F0', fontSize: '0.65rem', fontWeight: 600 }}>
                    Gaze: <span style={{ color: gazeDirection === 'CENTER' ? '#4ADE80' : '#F87171' }}>{gazeDirection}</span>
                  </Typography>
                  <Typography sx={{ color: '#E2E8F0', fontSize: '0.65rem', fontWeight: 600 }}>
                    Pose: <span style={{ color: headPose === 'FORWARD' || headPose === 'FRONTAL' ? '#4ADE80' : '#FBBF24' }}>{headPose}</span>
                  </Typography>
                </Box>
              </Paper>

              {/* Real-time Risk Score Meter */}
              <Paper variant="outlined" sx={{ p: 1.75, borderRadius: 2, bgcolor: '#FFFFFF' }}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.75}>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: '#64748B', letterSpacing: '0.04em' }}>
                    PROCTORING RISK LEVEL
                  </Typography>
                  <Typography variant="caption" sx={{ fontWeight: 800, color: riskColor }}>
                    {riskLevel} ({Math.round(riskScore)}%)
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(100, riskScore)}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    backgroundColor: '#F1F5F9',
                    '& .MuiLinearProgress-bar': { backgroundColor: riskColor, borderRadius: 4 }
                  }}
                />
              </Paper>

              {/* Detected Objects Checklist */}
              <Paper variant="outlined" sx={{ p: 1.75, borderRadius: 2, bgcolor: '#FFFFFF' }}>
                <Typography variant="caption" sx={{ fontWeight: 700, color: '#64748B', display: 'block', mb: 1 }}>
                  ENVIRONMENT & OBJECT DETECTIONS
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={0.75}>
                  <Chip
                    icon={<PhoneAndroidIcon sx={{ fontSize: '13px !important' }} />}
                    label={detectedObjects.some(o => o.name.toLowerCase().includes('phone') || o.name.toLowerCase().includes('cell')) ? "Phone Detected!" : "No Phone Detected"}
                    size="small"
                    color={detectedObjects.some(o => o.name.toLowerCase().includes('phone') || o.name.toLowerCase().includes('cell')) ? "error" : "success"}
                    variant="outlined"
                    sx={{ fontSize: '0.675rem', fontWeight: 600 }}
                  />
                  <Chip
                    icon={<PersonOutlineIcon sx={{ fontSize: '13px !important' }} />}
                    label={facesCount > 1 ? "Multiple Faces Detected" : facesCount === 0 ? "No Face Detected" : "Single Face (Normal)"}
                    size="small"
                    color={facesCount === 1 ? "success" : "warning"}
                    variant="outlined"
                    sx={{ fontSize: '0.675rem', fontWeight: 600 }}
                  />
                </Box>
              </Paper>
            </Stack>
          )}

          {/* ── TAB 2: ACTIVE VIOLATIONS ────────────────────────────────── */}
          {activeTab === 'violations' && (
            <Stack spacing={1.25}>
              {violations.length === 0 ? (
                <Paper variant="outlined" sx={{ p: 3, textAlign: 'center', bgcolor: '#F0FDF4', borderColor: '#BBF7D0', borderRadius: 2 }}>
                  <ShieldIcon sx={{ fontSize: 36, color: '#16A34A', mb: 0.5 }} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#15803D' }}>
                    Zero Compliance Violations
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#166534', display: 'block' }}>
                    Your session is in full compliance with examination rules.
                  </Typography>
                </Paper>
              ) : (
                violations.map((v, i) => (
                  <Paper
                    key={v.id || i}
                    variant="outlined"
                    sx={{
                      p: 1.5,
                      borderRadius: 2,
                      bgcolor: '#FFF5F5',
                      borderColor: '#FECACA',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 1.25
                    }}
                  >
                    <WarningAmberIcon sx={{ fontSize: 18, color: '#DC2626', mt: 0.25 }} />
                    <Box sx={{ flex: 1 }}>
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="body2" sx={{ fontWeight: 700, color: '#991B1B', fontSize: '0.75rem' }}>
                          {v.type}
                        </Typography>
                        <Chip
                          label={v.severity.toUpperCase()}
                          size="small"
                          sx={{
                            height: 18,
                            fontSize: '0.6rem',
                            fontWeight: 800,
                            bgcolor: '#FEE2E2',
                            color: '#DC2626'
                          }}
                        />
                      </Box>
                      <Typography variant="caption" sx={{ color: '#7F1D1D', display: 'block', mt: 0.25 }}>
                        Logged at {v.time} • Risk impact: +{v.risk || 20}
                      </Typography>
                    </Box>
                  </Paper>
                ))
              )}
            </Stack>
          )}

          {/* ── TAB 3: EVENT TIMELINE ──────────────────────────────────── */}
          {activeTab === 'timeline' && (
            <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2, bgcolor: '#FFFFFF', maxHeight: 260, overflowY: 'auto' }}>
              <Stack spacing={1}>
                {timeline.map((event, i) => (
                  <Box key={i} sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, pb: 0.75, borderBottom: i < timeline.length - 1 ? '1px solid #F1F5F9' : 'none' }}>
                    <Typography sx={{ fontSize: '0.85rem' }}>{event.icon}</Typography>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.72rem', color: '#1E293B' }}>
                        {event.text}
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#94A3B8', fontSize: '0.625rem' }}>
                        {event.time}
                      </Typography>
                    </Box>
                  </Box>
                ))}
              </Stack>
            </Paper>
          )}
        </Box>
      </Collapse>
    </Box>
  );
}
