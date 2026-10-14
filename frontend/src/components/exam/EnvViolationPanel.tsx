/**
 * EnvViolationPanel
 * =================
 * Read-only panel showing the student's own exam-environment violations
 * for the current session. Displayed inside OnlineExamPage's monitoring sidebar.
 *
 * The student can VIEW their violations but cannot:
 *   - edit, delete, or dismiss any violation
 *   - change severity or timestamps
 *   - delete evidence
 */

import React from 'react';
import {
  Box,
  Typography,
  Stack,
  Chip,
  Divider,
  Paper,
  Tooltip,
} from '@mui/material';
import ShieldIcon from '@mui/icons-material/Shield';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import FullscreenExitIcon from '@mui/icons-material/FullscreenExit';
import RadioButtonCheckedIcon from '@mui/icons-material/RadioButtonChecked';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import type { EnvViolationRecord } from '../../services/ExamEnvironmentMonitor';

interface Props {
  violations: EnvViolationRecord[];
  isMonitoringActive: boolean;
}

function formatDuration(seconds?: number): string {
  if (seconds === undefined || seconds === null) return '—';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

const ViolationTypeInfo: Record<string, { label: string; icon: React.ReactNode }> = {
  TAB_SWITCH: {
    label: 'Tab / Window Switching',
    icon: <VisibilityOffIcon fontSize="small" />,
  },
  FULLSCREEN_EXIT: {
    label: 'Fullscreen Exit',
    icon: <FullscreenExitIcon fontSize="small" />,
  },
};

const EnvViolationPanel: React.FC<Props> = ({ violations, isMonitoringActive }) => {
  const activeViolation = violations.find(v => v.status === 'ACTIVE');
  const resolvedViolations = violations.filter(v => v.status !== 'ACTIVE');
  const totalCount = violations.length;

  return (
    <Paper
      elevation={0}
      sx={{
        border: '1px solid',
        borderColor: totalCount > 0 ? 'error.main' : 'divider',
        borderRadius: 2,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: 2,
          py: 1.5,
          bgcolor: totalCount > 0 ? '#FFF3E0' : 'background.paper',
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          borderBottom: '1px solid',
          borderColor: totalCount > 0 ? 'warning.light' : 'divider',
        }}
      >
        <ShieldIcon
          fontSize="small"
          sx={{ color: totalCount > 0 ? 'error.main' : 'text.secondary' }}
        />
        <Typography variant="subtitle2" fontWeight={700} sx={{ flex: 1 }}>
          Exam Environment
        </Typography>

        {/* Status chip */}
        {isMonitoringActive ? (
          <Chip
            label="Monitoring Active"
            size="small"
            icon={<RadioButtonCheckedIcon sx={{ fontSize: '10px !important', color: 'success.main' }} />}
            sx={{
              bgcolor: '#E8F5E9',
              color: 'success.dark',
              fontWeight: 600,
              fontSize: '0.65rem',
              height: 20,
            }}
          />
        ) : (
          <Chip
            label="Inactive"
            size="small"
            sx={{ bgcolor: 'grey.100', color: 'text.secondary', fontSize: '0.65rem', height: 20 }}
          />
        )}

        {/* Violation count badge */}
        {totalCount > 0 && (
          <Chip
            label={`${totalCount} violation${totalCount > 1 ? 's' : ''}`}
            size="small"
            sx={{
              bgcolor: 'error.main',
              color: 'white',
              fontWeight: 700,
              fontSize: '0.65rem',
              height: 20,
            }}
          />
        )}
      </Box>

      {/* Content */}
      <Box sx={{ p: 2 }}>
        {violations.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 1.5, color: 'text.secondary' }}>
            <CheckCircleOutlineIcon sx={{ fontSize: 28, color: 'success.light', mb: 0.5 }} />
            <Typography variant="caption" display="block">
              No environment violations recorded
            </Typography>
          </Box>
        ) : (
          <Stack spacing={1.5}>
            {/* Active violation (highlighted) */}
            {activeViolation && (
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 1.5,
                  bgcolor: '#FFEBEE',
                  border: '1px solid',
                  borderColor: 'error.light',
                  animation: 'pulse 2s ease-in-out infinite',
                  '@keyframes pulse': {
                    '0%, 100%': { opacity: 1 },
                    '50%': { opacity: 0.75 },
                  },
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.5 }}>
                  <Chip
                    label="ACTIVE"
                    size="small"
                    sx={{
                      bgcolor: 'error.main',
                      color: 'white',
                      fontWeight: 700,
                      fontSize: '0.6rem',
                      height: 18,
                      borderRadius: 0.5,
                    }}
                  />
                  <Chip
                    label="HIGH RISK"
                    size="small"
                    sx={{
                      bgcolor: '#FF6F00',
                      color: 'white',
                      fontWeight: 700,
                      fontSize: '0.6rem',
                      height: 18,
                      borderRadius: 0.5,
                    }}
                  />
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'error.dark' }}>
                  {ViolationTypeInfo[activeViolation.type]?.icon}
                  <Typography variant="caption" fontWeight={700} color="error.dark">
                    {ViolationTypeInfo[activeViolation.type]?.label || activeViolation.type}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.25 }}>
                  Started: {formatTime(activeViolation.startedAt)}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ color: 'error.main', fontWeight: 600, display: 'block', mt: 0.25 }}
                >
                  ⚠ Being recorded — return to exam page immediately
                </Typography>
              </Box>
            )}

            {/* Resolved violations */}
            {resolvedViolations.map((v, idx) => {
              const typeInfo = ViolationTypeInfo[v.type] || { label: v.type, icon: null };
              return (
                <React.Fragment key={v.id > 0 ? v.id : `local-${idx}`}>
                  {idx > 0 && <Divider sx={{ opacity: 0.4 }} />}
                  <Box sx={{ py: 0.5 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.5 }}>
                      <Chip
                        label="HIGH RISK"
                        size="small"
                        sx={{
                          bgcolor: '#FF6F00',
                          color: 'white',
                          fontWeight: 700,
                          fontSize: '0.6rem',
                          height: 18,
                          borderRadius: 0.5,
                        }}
                      />
                      <Chip
                        label="RECORDED"
                        size="small"
                        sx={{
                          bgcolor: 'grey.200',
                          color: 'text.secondary',
                          fontWeight: 600,
                          fontSize: '0.6rem',
                          height: 18,
                          borderRadius: 0.5,
                        }}
                      />
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'text.primary' }}>
                      {typeInfo.icon}
                      <Typography variant="caption" fontWeight={600}>
                        {typeInfo.label}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        display: 'flex',
                        gap: 2,
                        mt: 0.5,
                        flexWrap: 'wrap',
                      }}
                    >
                      <Tooltip title="Time the violation started">
                        <Typography variant="caption" color="text.secondary">
                          At: <strong>{formatTime(v.startedAt)}</strong>
                        </Typography>
                      </Tooltip>
                      {v.durationSeconds !== undefined && (
                        <Tooltip title="How long you were away">
                          <Typography variant="caption" color="text.secondary">
                            Duration: <strong>{formatDuration(v.durationSeconds)}</strong>
                          </Typography>
                        </Tooltip>
                      )}
                    </Box>
                  </Box>
                </React.Fragment>
              );
            })}

            {/* Read-only notice */}
            <Typography
              variant="caption"
              color="text.disabled"
              sx={{ display: 'block', mt: 0.5, fontStyle: 'italic', textAlign: 'center' }}
            >
              This log is read-only and visible to the examiner.
            </Typography>
          </Stack>
        )}
      </Box>
    </Paper>
  );
};

export default EnvViolationPanel;
