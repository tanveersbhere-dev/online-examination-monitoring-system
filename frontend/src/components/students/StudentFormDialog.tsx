import { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  TextField, Grid, MenuItem, Typography
} from '@mui/material';

interface StudentFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: any) => Promise<void>;
  initialData?: any;
}

export default function StudentFormDialog({ open, onClose, onSubmit, initialData }: StudentFormDialogProps) {
  const [formData, setFormData] = useState({
    registration_number: '',
    full_name: '',
    email: '',
    phone: '',
    status: 'ACTIVE',
    department: '',
    program: '',
    semester: '',
    batch: ''
  });
  
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (initialData) {
      setFormData({
        ...formData,
        ...initialData,
        semester: initialData.semester?.toString() || ''
      });
    } else {
      setFormData({
        registration_number: '', full_name: '', email: '', phone: '',
        status: 'ACTIVE', department: '', program: '', semester: '', batch: ''
      });
    }
  }, [initialData, open]);

  const handleChange = (e: any) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await onSubmit({
        ...formData,
        semester: formData.semester ? parseInt(formData.semester) : null
      });
      onClose();
    } catch (err) {
      console.error(err);
      // Let parent handle errors usually, or show inline
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{initialData ? 'Edit Student' : 'Add New Student'}</DialogTitle>
      <DialogContent dividers>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Typography variant="subtitle2" color="primary">Identity Information</Typography>
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField fullWidth label="Registration Number" name="registration_number" value={formData.registration_number} onChange={handleChange} required />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField fullWidth label="Full Name" name="full_name" value={formData.full_name} onChange={handleChange} required />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField fullWidth label="Email" type="email" name="email" value={formData.email} onChange={handleChange} required />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField fullWidth label="Phone" name="phone" value={formData.phone} onChange={handleChange} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField select fullWidth label="Status" name="status" value={formData.status} onChange={handleChange}>
              <MenuItem value="ACTIVE">Active</MenuItem>
              <MenuItem value="PENDING">Pending</MenuItem>
              <MenuItem value="SUSPENDED">Suspended</MenuItem>
              <MenuItem value="ARCHIVED">Archived</MenuItem>
            </TextField>
          </Grid>

          <Grid item xs={12} sx={{ mt: 2 }}>
            <Typography variant="subtitle2" color="primary">Academic Information</Typography>
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField fullWidth label="Department" name="department" value={formData.department} onChange={handleChange} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField fullWidth label="Program" name="program" value={formData.program} onChange={handleChange} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField fullWidth label="Batch" name="batch" value={formData.batch} onChange={handleChange} />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField fullWidth label="Semester" name="semester" type="number" value={formData.semester} onChange={handleChange} />
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="inherit" disabled={loading}>Cancel</Button>
        <Button onClick={handleSubmit} variant="contained" disabled={loading}>
          {loading ? 'Saving...' : 'Save Student'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
