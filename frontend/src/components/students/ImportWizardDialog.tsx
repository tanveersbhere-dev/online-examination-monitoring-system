import { useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  Stepper, Step, StepLabel, Typography, Box, Alert, CircularProgress,
  List, ListItem, ListItemText, Chip
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import apiClient from '../../services/apiClient';

interface ImportWizardDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const steps = ['Upload CSV', 'Preview & Detect Duplicates', 'Confirm Import'];

export default function ImportWizardDialog({ open, onClose, onSuccess }: ImportWizardDialogProps) {
  const [activeStep, setActiveStep] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleNext = async () => {
    if (activeStep === 0) {
      if (!file) return;
      setLoading(true);
      setError(null);
      const formData = new FormData();
      formData.append('file', file);
      try {
        const res = await apiClient.post('/workspace/students/import/preview', formData);
        setPreviewData(res.data);
        setActiveStep(1);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to parse CSV file.');
      } finally {
        setLoading(false);
      }
    } else if (activeStep === 1) {
      setActiveStep(2);
    } else if (activeStep === 2) {
      setLoading(true);
      setError(null);
      try {
        await apiClient.post('/workspace/students/import/confirm', previewData.valid_data);
        onSuccess();
        onClose();
        handleReset();
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Import failed.');
      } finally {
        setLoading(false);
      }
    }
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  const handleReset = () => {
    setActiveStep(0);
    setFile(null);
    setPreviewData(null);
    setError(null);
  };

  return (
    <Dialog open={open} onClose={() => { handleReset(); onClose(); }} maxWidth="md" fullWidth>
      <DialogTitle>Import Students</DialogTitle>
      <DialogContent dividers sx={{ minHeight: 400 }}>
        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {activeStep === 0 && (
          <Box sx={{ textAlign: 'center', py: 6, border: '2px dashed #ccc', borderRadius: 2 }}>
            <CloudUploadIcon color="primary" sx={{ fontSize: 60, mb: 2 }} />
            <Typography variant="h6">Drag and drop your CSV here</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Must include columns: registration_number, full_name, email
            </Typography>
            <Button variant="outlined" component="label">
              Choose File
              <input type="file" hidden accept=".csv" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </Button>
            {file && <Typography sx={{ mt: 2, color: 'success.main' }}>Selected: {file.name}</Typography>}
          </Box>
        )}

        {activeStep === 1 && previewData && (
          <Box>
            <Alert severity="info" sx={{ mb: 2 }}>
              Found {previewData.valid_rows} valid students and {previewData.duplicates} duplicates/conflicts.
            </Alert>
            
            {previewData.conflicts.length > 0 && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle1" color="error" fontWeight="bold">Conflicts Detected</Typography>
                <List dense>
                  {previewData.conflicts.map((c: any, i: number) => (
                    <ListItem key={i} sx={{ bgcolor: '#fff5f5', mb: 1, borderRadius: 1 }}>
                      <ListItemText 
                        primary={`Row ${c.row_index}: ${c.registration_number || 'Missing Reg No'}`}
                        secondary={`${c.reason} - ${c.suggested_resolution}`}
                      />
                      <Chip label="Skipped" size="small" color="error" />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}

            <Typography variant="subtitle1" fontWeight="bold" sx={{ mt: 3 }}>Valid Data Preview (First 5)</Typography>
            <List dense>
              {previewData.valid_data.slice(0, 5).map((row: any, i: number) => (
                <ListItem key={i} divider>
                  <ListItemText primary={row.full_name} secondary={`${row.registration_number} | ${row.email}`} />
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {activeStep === 2 && previewData && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="h6" gutterBottom>Ready to Import</Typography>
            <Typography variant="body1">
              You are about to import <strong>{previewData.valid_rows}</strong> students into your repository.
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Conflicts and duplicates will be skipped.
            </Typography>
          </Box>
        )}

      </DialogContent>
      <DialogActions>
        <Button disabled={activeStep === 0 || loading} onClick={handleBack}>Back</Button>
        <Button
          variant="contained"
          onClick={handleNext}
          disabled={(activeStep === 0 && !file) || loading}
        >
          {loading ? <CircularProgress size={24} /> : activeStep === steps.length - 1 ? 'Confirm Import' : 'Next'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
