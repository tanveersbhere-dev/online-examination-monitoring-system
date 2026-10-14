import React, { useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  Stepper, Step, StepLabel, Typography, Box, Alert, CircularProgress,
  List, ListItem, ListItemText, Chip, IconButton, Paper, Stack,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tooltip, Divider
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DownloadIcon from '@mui/icons-material/Download';
import CloseIcon from '@mui/icons-material/Close';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
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
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDownloadTemplate = () => {
    const csvHeader = "registration_number,full_name,email,phone,roll_number,department,program,semester,batch,section\n";
    const sampleRow1 = "FA21-BCS-001,John Doe,john.doe@university.edu,+1234567890,001,Computer Science,BS CS,6,2021,A\n";
    const sampleRow2 = "FA21-BCS-002,Jane Smith,jane.smith@university.edu,+1987654321,002,Software Engineering,BS SE,6,2021,B\n";
    const csvContent = "data:text/csv;charset=utf-8," + encodeURIComponent(csvHeader + sampleRow1 + sampleRow2);
    
    const link = document.createElement("a");
    link.setAttribute("href", csvContent);
    link.setAttribute("download", "student_import_template.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleFileChange = (selectedFile: File | null) => {
    if (!selectedFile) return;
    if (!selectedFile.name.toLowerCase().endsWith('.csv')) {
      setError("Please select a valid CSV (.csv) file.");
      setFile(null);
      return;
    }
    setError(null);
    setFile(selectedFile);
  };

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
        const errorDetail = err.response?.data?.detail;
        setError(typeof errorDetail === 'string' ? errorDetail : 'Failed to validate CSV file. Please verify column formatting.');
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
        handleClose();
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Student import failed.');
      } finally {
        setLoading(false);
      }
    }
  };

  const handleBack = () => {
    setError(null);
    setActiveStep((prev) => Math.max(0, prev - 1));
  };

  const handleClose = () => {
    setActiveStep(0);
    setFile(null);
    setPreviewData(null);
    setError(null);
    setIsDragOver(false);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ m: 0, p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h6" fontWeight="bold">Import Students</Typography>
          <Typography variant="caption" color="text.secondary">
            Bulk upload student records via standard CSV file
          </Typography>
        </Box>
        <IconButton aria-label="close" onClick={handleClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers sx={{ minHeight: 440, px: 3, py: 2.5 }}>
        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert 
            severity="error" 
            sx={{ mb: 2.5, whiteSpace: 'pre-line' }} 
            icon={<ErrorOutlineIcon fontSize="inherit" />}
            onClose={() => setError(null)}
          >
            {error}
          </Alert>
        )}

        {/* STEP 0: UPLOAD CSV ONLY */}
        {activeStep === 0 && (
          <Stack spacing={2.5}>
            {/* Header Action Bar with Template Download */}
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Typography variant="subtitle2" color="text.secondary">
                Upload your class or batch CSV file below.
              </Typography>
              <Button
                variant="outlined"
                color="primary"
                size="small"
                startIcon={<DownloadIcon />}
                onClick={handleDownloadTemplate}
              >
                Download CSV Template
              </Button>
            </Box>

            {/* CSV Required Columns Reference */}
            <Paper variant="outlined" sx={{ p: 2, bgcolor: '#f8fafc', borderRadius: 2 }}>
              <Typography variant="subtitle2" fontWeight="bold" color="primary.main" gutterBottom>
                📋 Required & Optional CSV Columns Format:
              </Typography>
              <Stack spacing={1} sx={{ mt: 1 }}>
                <Box display="flex" alignItems="center" flexWrap="wrap" gap={0.8}>
                  <Typography variant="body2" fontWeight="600" color="text.primary" sx={{ minWidth: 120 }}>
                    Required Columns:
                  </Typography>
                  <Chip label="[registration_number]" size="small" color="primary" variant="outlined" sx={{ fontWeight: 600 }} />
                  <Chip label="[full_name]" size="small" color="primary" variant="outlined" sx={{ fontWeight: 600 }} />
                  <Chip label="[email]" size="small" color="primary" variant="outlined" sx={{ fontWeight: 600 }} />
                </Box>
                <Box display="flex" alignItems="center" flexWrap="wrap" gap={0.8}>
                  <Typography variant="body2" fontWeight="600" color="text.secondary" sx={{ minWidth: 120 }}>
                    Optional Columns:
                  </Typography>
                  <Chip label="[phone]" size="small" variant="outlined" />
                  <Chip label="[roll_number]" size="small" variant="outlined" />
                  <Chip label="[department]" size="small" variant="outlined" />
                  <Chip label="[program]" size="small" variant="outlined" />
                  <Chip label="[semester]" size="small" variant="outlined" />
                  <Chip label="[batch]" size="small" variant="outlined" />
                  <Chip label="[section]" size="small" variant="outlined" />
                </Box>
              </Stack>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
                ⚠️ <em>Note: Any additional or unrecognized columns in the file will be flagged during validation.</em>
              </Typography>
            </Paper>

            {/* Photos Notice Callout */}
            <Alert severity="info" icon={<InfoOutlinedIcon />} sx={{ borderRadius: 2, bgcolor: '#eff6ff' }}>
              <Typography variant="subtitle2" fontWeight="bold">
                Student Photos Notice
              </Typography>
              <Typography variant="body2" color="text.secondary">
                CSV files contain text information only and cannot embed photo images. All students imported via CSV will initially be enrolled with <strong>No Photo (Face Registration Pending)</strong>. Biometric face photos can be captured during exam identity verification or uploaded individually in each student's profile later.
              </Typography>
            </Alert>

            {/* Drag and Drop / Upload Box */}
            {!file ? (
              <Box
                onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragOver(false);
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    handleFileChange(e.dataTransfer.files[0]);
                  }
                }}
                sx={{
                  textAlign: 'center',
                  py: 4,
                  px: 2,
                  border: '2px dashed',
                  borderColor: isDragOver ? 'primary.main' : '#cbd5e1',
                  bgcolor: isDragOver ? '#f0fdf4' : '#fafafa',
                  borderRadius: 2,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease-in-out',
                  '&:hover': {
                    borderColor: 'primary.main',
                    bgcolor: '#f8fafc'
                  }
                }}
                component="label"
              >
                <CloudUploadIcon color="primary" sx={{ fontSize: 56, mb: 1 }} />
                <Typography variant="subtitle1" fontWeight="bold">
                  Click to Browse or Drag & Drop CSV File
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Supports UTF-8 encoded .csv files
                </Typography>
                <Button variant="contained" component="span" size="small">
                  Select CSV File
                </Button>
                <input
                  type="file"
                  hidden
                  accept=".csv,text/csv"
                  onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
                />
              </Box>
            ) : (
              <Paper variant="outlined" sx={{ p: 2.5, bgcolor: '#f0fdf4', borderColor: '#86efac', borderRadius: 2 }}>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box display="flex" alignItems="center" gap={1.5}>
                    <InsertDriveFileIcon color="success" sx={{ fontSize: 36 }} />
                    <Box>
                      <Typography variant="subtitle2" fontWeight="bold" color="success.dark">
                        {file.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {(file.size / 1024).toFixed(1)} KB • Ready for preview & verification
                      </Typography>
                    </Box>
                  </Box>
                  <Tooltip title="Remove and select different file">
                    <IconButton size="small" color="error" onClick={() => setFile(null)}>
                      <DeleteOutlineIcon />
                    </IconButton>
                  </Tooltip>
                </Box>
              </Paper>
            )}
          </Stack>
        )}

        {/* STEP 1: PREVIEW & CONFLICT DETECTION */}
        {activeStep === 1 && previewData && (
          <Stack spacing={2.5}>
            <Box display="flex" gap={2} flexWrap="wrap">
              <Paper variant="outlined" sx={{ p: 1.5, flex: 1, minWidth: 160, textAlign: 'center' }}>
                <Typography variant="caption" color="text.secondary">Total Rows in File</Typography>
                <Typography variant="h6" fontWeight="bold">{previewData.total_rows}</Typography>
              </Paper>
              <Paper variant="outlined" sx={{ p: 1.5, flex: 1, minWidth: 160, textAlign: 'center', bgcolor: '#f0fdf4', borderColor: '#86efac' }}>
                <Typography variant="caption" color="success.dark">Valid Students</Typography>
                <Typography variant="h6" fontWeight="bold" color="success.dark">{previewData.valid_rows}</Typography>
              </Paper>
              <Paper variant="outlined" sx={{ p: 1.5, flex: 1, minWidth: 160, textAlign: 'center', bgcolor: previewData.conflicts.length > 0 ? '#fff1f2' : '#f8fafc', borderColor: previewData.conflicts.length > 0 ? '#fca5a5' : '#e2e8f0' }}>
                <Typography variant="caption" color={previewData.conflicts.length > 0 ? "error.dark" : "text.secondary"}>Duplicates / Conflicts</Typography>
                <Typography variant="h6" fontWeight="bold" color={previewData.conflicts.length > 0 ? "error.dark" : "text.secondary"}>
                  {previewData.conflicts.length}
                </Typography>
              </Paper>
            </Box>

            {/* Conflicts Breakdown */}
            {previewData.conflicts.length > 0 && (
              <Box>
                <Typography variant="subtitle2" color="error.dark" fontWeight="bold" gutterBottom>
                  ⚠️ Conflicts & Duplicate Records (These will be skipped):
                </Typography>
                <Paper variant="outlined" sx={{ maxHeight: 150, overflow: 'auto', p: 1, bgcolor: '#fff5f5' }}>
                  <List dense disablePadding>
                    {previewData.conflicts.map((c: any, i: number) => (
                      <ListItem key={i} sx={{ borderBottom: '1px solid #fee2e2', py: 0.5 }}>
                        <ListItemText
                          primary={<Typography variant="body2" fontWeight="600">Row {c.row_index}: {c.registration_number}</Typography>}
                          secondary={<Typography variant="caption" color="error.main">{c.reason} • {c.suggested_resolution}</Typography>}
                        />
                        <Chip label="Skipped" size="small" color="error" variant="outlined" />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              </Box>
            )}

            {/* Valid Data Preview Table */}
            <Box>
              <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                Valid Student Records Preview (First 5 of {previewData.valid_rows}):
              </Typography>
              {previewData.valid_data.length === 0 ? (
                <Alert severity="warning">No valid student rows found in the CSV. Please check the file contents and format.</Alert>
              ) : (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead sx={{ bgcolor: '#f8fafc' }}>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>Registration No</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Full Name</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Email</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Department</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Photo Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {previewData.valid_data.slice(0, 5).map((row: any, i: number) => (
                        <TableRow key={i} hover>
                          <TableCell sx={{ fontWeight: 500 }}>{row.registration_number}</TableCell>
                          <TableCell>{row.full_name}</TableCell>
                          <TableCell>{row.email}</TableCell>
                          <TableCell>{row.department || row.program || '-'}</TableCell>
                          <TableCell>
                            <Chip label="Pending Photo" size="small" variant="outlined" color="default" />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          </Stack>
        )}

        {/* STEP 2: CONFIRM IMPORT */}
        {activeStep === 2 && previewData && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <CheckCircleOutlineIcon color="success" sx={{ fontSize: 64, mb: 2 }} />
            <Typography variant="h6" fontWeight="bold" gutterBottom>
              Ready to Import Students
            </Typography>
            <Typography variant="body1" color="text.primary" sx={{ maxWidth: 500, mx: 'auto', mb: 2 }}>
              You are about to import <strong>{previewData.valid_rows}</strong> valid student records into your repository.
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {previewData.conflicts.length > 0 ? `${previewData.conflicts.length} duplicate/invalid rows will be excluded. ` : ''}
              Imported students will immediately appear in your repository with pending face registration status.
            </Typography>
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2, justifyContent: 'space-between' }}>
        {activeStep === 0 ? (
          <Button onClick={handleClose} disabled={loading} color="inherit">
            Cancel
          </Button>
        ) : (
          <Button onClick={handleBack} disabled={loading}>
            Back
          </Button>
        )}

        <Button
          variant="contained"
          onClick={handleNext}
          disabled={(activeStep === 0 && !file) || (activeStep === 1 && previewData?.valid_rows === 0) || loading}
        >
          {loading ? (
            <CircularProgress size={24} color="inherit" />
          ) : activeStep === 0 ? (
            'Next: Preview & Verify'
          ) : activeStep === 1 ? (
            'Next: Confirm Import'
          ) : (
            `Confirm Import (${previewData?.valid_rows || 0} Students)`
          )}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
