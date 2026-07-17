import { Drawer, Box, Typography, Divider, IconButton, Chip, Grid, CircularProgress, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { useState, useEffect } from 'react';
import apiClient from '../../services/apiClient';

interface StudentProfileDrawerProps {
  open: boolean;
  onClose: () => void;
  student: any;
}

export default function StudentProfileDrawer({ open, onClose, student }: StudentProfileDrawerProps) {
  const [analytics, setAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (student && open) {
      setLoading(true);
      apiClient.get(`/reports/student/${student.id}`)
        .then(res => setAnalytics(res.data))
        .catch(err => console.error("Failed to fetch student analytics", err))
        .finally(() => setLoading(false));
    } else {
      setAnalytics(null);
    }
  }, [student, open]);

  if (!student) return null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE': return 'success';
      case 'PENDING': return 'warning';
      case 'ARCHIVED': return 'default';
      case 'SUSPENDED': return 'error';
      default: return 'default';
    }
  };

  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 500 } } }}>
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6" fontWeight="bold">Student Profile</Typography>
        <IconButton onClick={onClose}><CloseIcon /></IconButton>
      </Box>
      <Divider />
      
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 4, textAlign: 'center' }}>
          <Box sx={{ width: 80, height: 80, borderRadius: '50%', bgcolor: 'primary.light', color: 'primary.contrastText', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 32, mx: 'auto', mb: 2 }}>
            {student.full_name.substring(0, 2).toUpperCase()}
          </Box>
          <Typography variant="h5" fontWeight="bold">{student.full_name}</Typography>
          <Typography color="text.secondary">{student.registration_number}</Typography>
          <Chip label={student.status} color={getStatusColor(student.status)} size="small" sx={{ mt: 1 }} />
        </Box>

        {/* Identity Information */}
        <Typography variant="overline" color="primary" fontWeight="bold">Identity Information</Typography>
        <Grid container spacing={2} sx={{ mb: 3, mt: 1 }}>
          <Grid item xs={12}>
            <Typography variant="caption" color="text.secondary">Email Address</Typography>
            <Typography variant="body2">{student.email}</Typography>
          </Grid>
          <Grid item xs={12}>
            <Typography variant="caption" color="text.secondary">Phone Number</Typography>
            <Typography variant="body2">{student.phone || 'N/A'}</Typography>
          </Grid>
        </Grid>

        <Divider sx={{ mb: 2 }} />

        {/* Academic Information */}
        <Typography variant="overline" color="primary" fontWeight="bold">Academic Information</Typography>
        <Grid container spacing={2} sx={{ mb: 3, mt: 1 }}>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Department</Typography>
            <Typography variant="body2">{student.department || 'N/A'}</Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Program</Typography>
            <Typography variant="body2">{student.program || 'N/A'}</Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Batch / Semester</Typography>
            <Typography variant="body2">{student.batch || 'N/A'} / {student.semester || 'N/A'}</Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="caption" color="text.secondary">Section</Typography>
            <Typography variant="body2">{student.section || 'N/A'}</Typography>
          </Grid>
        </Grid>

        <Divider sx={{ mb: 2 }} />

        <Typography variant="overline" color="primary" fontWeight="bold">Student Analytics</Typography>
        {loading ? (
           <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress size={24} /></Box>
        ) : analytics ? (
           <Box sx={{ mt: 1 }}>
             <Grid container spacing={2} sx={{ mb: 3 }}>
               <Grid item xs={4}>
                 <Typography variant="caption" color="text.secondary">Total Exams</Typography>
                 <Typography variant="body1" fontWeight={600}>{analytics.total_exams_taken}</Typography>
               </Grid>
               <Grid item xs={4}>
                 <Typography variant="caption" color="text.secondary">Avg Risk Score</Typography>
                 <Typography variant="body1" fontWeight={600} color={analytics.average_risk_score > 50 ? 'error' : 'success.main'}>
                    {analytics.average_risk_score.toFixed(1)}
                 </Typography>
               </Grid>
               <Grid item xs={4}>
                 <Typography variant="caption" color="text.secondary">Total Violations</Typography>
                 <Typography variant="body1" fontWeight={600}>{analytics.total_violations_across_exams}</Typography>
               </Grid>
             </Grid>

             <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ display: 'block', mb: 1 }}>Exam History</Typography>
             {analytics.exam_history.length > 0 ? (
               <TableContainer component={Paper} variant="outlined" sx={{ boxShadow: 'none' }}>
                 <Table size="small">
                   <TableHead sx={{ bgcolor: '#f8fafc' }}>
                     <TableRow>
                       <TableCell>Exam Name</TableCell>
                       <TableCell>Date</TableCell>
                       <TableCell align="right">Risk</TableCell>
                     </TableRow>
                   </TableHead>
                   <TableBody>
                     {analytics.exam_history.map((h: any) => (
                       <TableRow key={h.exam_session_id}>
                         <TableCell sx={{ fontSize: '0.8rem' }}>{h.exam_name}</TableCell>
                         <TableCell sx={{ fontSize: '0.8rem' }}>{h.date ? new Date(h.date).toLocaleDateString() : 'N/A'}</TableCell>
                         <TableCell align="right" sx={{ fontSize: '0.8rem', color: h.highest_risk_score > 50 ? 'error.main' : 'success.main', fontWeight: 600 }}>
                           {h.highest_risk_score.toFixed(1)}
                         </TableCell>
                       </TableRow>
                     ))}
                   </TableBody>
                 </Table>
               </TableContainer>
             ) : (
               <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2, bgcolor: '#f8fafc', borderRadius: 1 }}>No completed exams found.</Typography>
             )}
           </Box>
        ) : (
           <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>Analytics not available.</Typography>
        )}

      </Box>
    </Drawer>
  );
}
