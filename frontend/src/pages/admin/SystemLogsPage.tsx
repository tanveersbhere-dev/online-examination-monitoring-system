import { useState, useEffect } from 'react';
import { Box, Typography, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Chip, CircularProgress, Alert } from '@mui/material';
import AssignmentIcon from '@mui/icons-material/Assignment';
import apiClient from '../../services/apiClient';

interface SystemLog {
  id: number;
  level: string;
  message: string;
  source: string;
  timestamp: string;
}

export default function SystemLogsPage() {
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiClient.get('/admin/logs')
      .then(res => setLogs(res.data))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load system logs'))
      .finally(() => setLoading(false));
  }, []);

  const getLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR': return 'error';
      case 'WARNING': return 'warning';
      case 'INFO': return 'info';
      default: return 'default';
    }
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 5 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error" sx={{ m: 3 }}>{error}</Alert>;

  return (
    <Box>
      <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
        <AssignmentIcon sx={{ fontSize: 32, color: 'text.secondary' }} />
        <Typography variant="h4" fontWeight={600}>System Logs</Typography>
      </Box>

      <TableContainer component={Paper} sx={{ borderRadius: 2, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
        <Table>
          <TableHead sx={{ bgcolor: '#f8fafc' }}>
            <TableRow>
              <TableCell>Timestamp</TableCell>
              <TableCell>Level</TableCell>
              <TableCell>Source</TableCell>
              <TableCell>Message</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {logs.length > 0 ? (
              logs.map((log) => (
                <TableRow key={log.id} hover>
                  <TableCell sx={{ whiteSpace: 'nowrap', fontSize: '0.875rem' }}>
                    {new Date(log.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Chip label={log.level} color={getLevelColor(log.level)} size="small" />
                  </TableCell>
                  <TableCell sx={{ fontSize: '0.875rem', fontWeight: 600 }}>{log.source}</TableCell>
                  <TableCell sx={{ fontSize: '0.875rem' }}>{log.message}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={4} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                  No system logs found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
