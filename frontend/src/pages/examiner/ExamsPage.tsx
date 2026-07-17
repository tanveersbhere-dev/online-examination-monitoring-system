import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Button, TextField,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Chip, IconButton, InputAdornment, Tooltip, Stack, CircularProgress, Alert
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import BarChartIcon from '@mui/icons-material/BarChart';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';

const STATUS_CONFIG: Record<string, any> = {
  DRAFT: { label: 'Draft', color: 'default' },
  READY: { label: 'Ready', color: 'info' },
  RUNNING: { label: 'Running', color: 'success' },
  PAUSED: { label: 'Paused', color: 'warning' },
  COMPLETED: { label: 'Completed', color: 'default' },
  ARCHIVED: { label: 'Archived', color: 'default' }
};

const ExamsPage = () => {
  const navigate = useNavigate();
  const [exams, setExams] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);

  const fetchExams = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get('/workspace/exams');
      setExams(res.data);
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExams();
  }, []);

  const filteredExams = exams.filter(e => 
    e.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
    e.exam_code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" fontWeight={600}>Exam Repository</Typography>
        <Button 
          variant="contained" 
          startIcon={<AddIcon />} 
          sx={{ borderRadius: 2 }} 
          onClick={() => navigate('/examiner/exams/build')}
        >
          Create Exam
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Card elevation={1}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <TextField
              placeholder="Search by code or title..."
              size="small"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              sx={{ maxWidth: 280 }}
              InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> }}
            />
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Exam Code</TableCell>
                  <TableCell>Title</TableCell>
                  <TableCell>Subject</TableCell>
                  <TableCell>Date & Time</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={6} align="center"><CircularProgress size={24} sx={{ my: 2 }} /></TableCell></TableRow>
                ) : filteredExams.length === 0 ? (
                  <TableRow><TableCell colSpan={6} align="center"><Typography color="text.secondary">No exams found.</Typography></TableCell></TableRow>
                ) : filteredExams.map((exam) => {
                  const cfg = STATUS_CONFIG[exam.status] || STATUS_CONFIG['DRAFT'];
                  const startDate = exam.scheduled_start ? new Date(exam.scheduled_start) : null;
                  
                  return (
                    <TableRow key={exam.id} hover>
                      <TableCell>
                        <Chip label={exam.exam_code} size="small" variant="outlined" />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}>{exam.title}</Typography>
                      </TableCell>
                      <TableCell>{exam.subject || 'N/A'}</TableCell>
                      <TableCell>
                        {startDate ? (
                          <>
                            <Typography variant="body2">{startDate.toLocaleDateString()}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </Typography>
                          </>
                        ) : (
                          <Typography variant="body2" color="text.secondary">Unscheduled</Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip label={cfg.label} color={cfg.color} size="small" />
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                          {['DRAFT', 'READY'].includes(exam.status) && (
                            <Tooltip title="Edit Draft">
                              <IconButton size="small" onClick={() => navigate(`/examiner/exams/build?id=${exam.id}`)}>
                                <EditIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                          {exam.status === 'READY' && (
                            <Tooltip title="Start Live">
                              <IconButton size="small" sx={{ color: 'success.main' }}>
                                <PlayArrowIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                          {exam.status === 'COMPLETED' && (
                            <Tooltip title="View Report">
                              <IconButton size="small" sx={{ color: 'primary.main' }}>
                                <BarChartIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ExamsPage;
