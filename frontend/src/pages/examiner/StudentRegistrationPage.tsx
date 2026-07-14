import { useState, useEffect, useRef } from 'react';
import {
  Box, Typography, Card, CardContent, Button, TextField, Grid,
  Divider, Stack, InputAdornment, Paper, Alert, Stepper,
  Step, StepLabel, CircularProgress,
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import EmailIcon from '@mui/icons-material/Email';
import AssignmentIcon from '@mui/icons-material/Assignment';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import FaceIcon from '@mui/icons-material/Face';
import SendIcon from '@mui/icons-material/Send';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';

interface ExamOption {
  id: number;
  course_name: string;
  course_code: string;
}

interface RegistrationSuccessData {
  full_name: string;
  email: string;
  username: string;
  exam_name: string;
}

const StudentRegistrationPage = () => {
  const [fullName, setFullName] = useState('');
  const [fatherName, setFatherName] = useState('');
  const [email, setEmail] = useState('');
  const [exam, setExam] = useState('');
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  
  const [examsList, setExamsList] = useState<ExamOption[]>([]);
  const [isLoadingExams, setIsLoadingExams] = useState(true);
  
  const [submitting, setSubmitting] = useState(false);
  const [successData, setSuccessData] = useState<RegistrationSuccessData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [registrationStep, setRegistrationStep] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const fetchExams = async () => {
      try {
        const response = await apiClient.get('/exams');
        setExamsList(response.data);
      } catch (err: any) {
        console.error('Failed to fetch exams', err);
        setError(getErrorMessage(err));
      } finally {
        setIsLoadingExams(false);
      }
    };
    fetchExams();
  }, []);

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      
      // Validation
      if (!['image/jpeg', 'image/png', 'image/jpg'].includes(file.type)) {
        setError('Please upload a valid JPG or PNG image.');
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        setError('Image file size must be less than 5MB.');
        return;
      }
      
      setError(null);
      setPhoto(file);
      setPhotoPreview(URL.createObjectURL(file));
    }
  };

  const handleBoxClick = () => {
    if (!photo && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleSubmit = async () => {
    if (!fullName || !email || !exam || !photo) {
      setError('Please fill out all required fields.');
      return;
    }

    if (!/\S+@\S+\.\S+/.test(email)) {
      setError('Please enter a valid email address.');
      return;
    }

    setSubmitting(true);
    setError(null);
    setRegistrationStep(0); // Uploading & Processing

    const formData = new FormData();
    formData.append('full_name', fullName);
    formData.append('email', email);
    formData.append('exam_id', exam);
    if (fatherName) {
      formData.append('father_name', fatherName);
    }
    formData.append('face_image', photo);

    try {
      // The backend does processing synchronously, so we will step up as it goes
      setRegistrationStep(1); // Enrolling face
      const response = await apiClient.post('/students/register', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      setRegistrationStep(2); // Success/Emails sent

      const selectedExam = examsList.find(e => e.id.toString() === exam);
      setSuccessData({
        full_name: response.data.full_name,
        email: response.data.email,
        username: response.data.username,
        exam_name: selectedExam ? `${selectedExam.course_name} (${selectedExam.course_code})` : 'Unknown Exam'
      });
      
    } catch (err: any) {
      if (err.response?.status === 502) {
        setError('Student was registered, but email delivery failed. Please resend credentials manually.');
      } else {
        setError(getErrorMessage(err));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setSuccessData(null);
    setFullName('');
    setFatherName('');
    setEmail('');
    setExam('');
    setPhoto(null);
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhotoPreview(null);
    setRegistrationStep(0);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const PROCESS_STEPS = ['Uploading data', 'Processing face enrollment', 'Sending credentials by email'];

  if (successData) {
    return (
      <Box>
        <Typography variant="h4" fontWeight={600} sx={{ mb: 4 }}>Student Registration</Typography>
        <Card elevation={1} sx={{ maxWidth: 600 }}>
          <CardContent sx={{ p: 4, textAlign: 'center' }}>
            <CheckCircleIcon sx={{ fontSize: 72, color: 'success.main', mb: 2 }} />
            <Typography variant="h5" fontWeight={600} color="success.main" gutterBottom>
              Registration Complete
            </Typography>
            <Divider sx={{ my: 3 }} />
            <Stack spacing={1.5} sx={{ textAlign: 'left', mb: 3 }}>
              {[
                { label: 'Student', value: successData.full_name },
                { label: 'Username', value: successData.username },
                { label: 'Exam', value: successData.exam_name },
                { label: 'Credentials sent to', value: successData.email },
              ].map((row) => (
                <Box key={row.label} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">{row.label}</Typography>
                  <Typography variant="body2" fontWeight={600}>{row.value}</Typography>
                </Box>
              ))}
            </Stack>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
              <Button variant="outlined" onClick={handleReset} startIcon={<PersonAddIcon />}>
                Register Another Student
              </Button>
            </Box>
          </CardContent>
        </Card>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" fontWeight={600} sx={{ mb: 4 }}>Student Registration</Typography>

      <Grid container spacing={4}>
        {/* Form */}
        <Grid item xs={12} md={7}>
          <Card elevation={1}>
            <CardContent sx={{ p: 3 }}>
              
              {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  {error}
                </Alert>
              )}

              <Stack spacing={3}>
                <TextField
                  label="Full Name *"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  disabled={submitting}
                  InputProps={{ startAdornment: <InputAdornment position="start"><PersonIcon fontSize="small" sx={{ color: 'text.secondary' }} /></InputAdornment> }}
                />
                <TextField
                  label="Father Name"
                  value={fatherName}
                  onChange={(e) => setFatherName(e.target.value)}
                  disabled={submitting}
                  InputProps={{ startAdornment: <InputAdornment position="start"><PersonIcon fontSize="small" sx={{ color: 'text.secondary' }} /></InputAdornment> }}
                />
                <TextField
                  label="Email Address *"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={submitting}
                  InputProps={{ startAdornment: <InputAdornment position="start"><EmailIcon fontSize="small" sx={{ color: 'text.secondary' }} /></InputAdornment> }}
                />
                <TextField
                  label="Assign Examination *"
                  select
                  value={exam}
                  onChange={(e) => setExam(e.target.value)}
                  disabled={submitting || isLoadingExams}
                  SelectProps={{ native: true }}
                  InputProps={{ startAdornment: <InputAdornment position="start"><AssignmentIcon fontSize="small" sx={{ color: 'text.secondary' }} /></InputAdornment> }}
                >
                  <option value="">{isLoadingExams ? 'Loading exams...' : 'Select examination...'}</option>
                  {examsList.map((examOpt) => (
                    <option key={examOpt.id} value={examOpt.id}>
                      {examOpt.course_name} — {examOpt.course_code}
                    </option>
                  ))}
                </TextField>

                {/* Face Photo Upload */}
                <Box>
                  <Typography variant="body2" fontWeight={500} gutterBottom>
                    Passport Style Photo *
                  </Typography>
                  <input 
                    type="file" 
                    accept="image/jpeg, image/png, image/jpg" 
                    style={{ display: 'none' }} 
                    ref={fileInputRef} 
                    onChange={handlePhotoSelect}
                    disabled={submitting}
                  />
                  {!photoPreview ? (
                    <Box
                      sx={{
                        border: '2px dashed', borderColor: 'divider',
                        borderRadius: 2, p: 4, textAlign: 'center',
                        cursor: submitting ? 'not-allowed' : 'pointer', transition: 'all 0.2s',
                        '&:hover': { borderColor: submitting ? 'divider' : 'primary.main', backgroundColor: submitting ? 'transparent' : 'primary.light', opacity: submitting ? 1 : 0.05 },
                      }}
                      onClick={handleBoxClick}
                    >
                      <CloudUploadIcon sx={{ fontSize: 40, color: 'text.secondary', mb: 1 }} />
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        Click to upload a photo
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        JPG or PNG • Max 5MB • Passport-style (face clearly visible)
                      </Typography>
                    </Box>
                  ) : (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Box
                        sx={{
                          width: 80, height: 100, borderRadius: 2,
                          backgroundColor: '#E3F2FD',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          border: '1px solid', borderColor: 'primary.light',
                          overflow: 'hidden'
                        }}
                      >
                        <img src={photoPreview} alt="Preview" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      </Box>
                      <Box>
                        <Typography variant="body2" fontWeight={600}>{photo?.name}</Typography>
                        <Typography variant="caption" color="text.secondary">{(photo!.size / 1024).toFixed(1)} KB • Ready for enrollment</Typography>
                        <br />
                        <Button size="small" onClick={() => fileInputRef.current?.click()} sx={{ p: 0, mt: 0.5 }} disabled={submitting}>
                          Change Photo
                        </Button>
                      </Box>
                    </Box>
                  )}
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    Photo must clearly show the student's face. Remove glasses and hats if possible.
                  </Typography>
                </Box>

                {/* Registration progress steps */}
                {submitting && (
                  <Box>
                    <Stepper activeStep={registrationStep} orientation="vertical">
                      {PROCESS_STEPS.map((label, idx) => (
                        <Step key={label} completed={registrationStep > idx}>
                          <StepLabel
                            icon={registrationStep === idx ? <CircularProgress size={20} thickness={5} /> : undefined}
                          >
                            <Typography variant="body2">{label}...</Typography>
                          </StepLabel>
                        </Step>
                      ))}
                    </Stepper>
                  </Box>
                )}

                <Button
                  variant="contained"
                  size="large"
                  disabled={!fullName || !email || !exam || !photo || submitting}
                  onClick={handleSubmit}
                  startIcon={submitting ? <CircularProgress size={16} color="inherit" /> : <PersonAddIcon />}
                  sx={{ borderRadius: 2 }}
                >
                  {submitting ? 'Registering...' : 'Register Student'}
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Info Panel */}
        <Grid item xs={12} md={5}>
          <Card elevation={0} sx={{ backgroundColor: '#E3F2FD', border: '1px solid #BBDEFB' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                What happens after registration?
              </Typography>
              <Divider sx={{ mb: 3 }} />
              <Stack spacing={3}>
                {[
                  { icon: <VpnKeyIcon color="primary" />, step: '1', title: 'Credential Generation', desc: 'A unique username and secure password are automatically generated. Credentials are never stored in plain text.' },
                  { icon: <FaceIcon color="primary" />, step: '2', title: 'Face Enrollment', desc: 'The uploaded photo is processed to create a biometric reference used for continuous identity verification during the exam.' },
                  { icon: <SendIcon color="primary" />, step: '3', title: 'Email Delivery', desc: 'Login credentials are automatically sent to the student\'s email address. No manual action required.' },
                ].map((item) => (
                  <Box key={item.step} sx={{ display: 'flex', gap: 2 }}>
                    <Box
                      sx={{
                        width: 36, height: 36, borderRadius: '50%',
                        backgroundColor: 'primary.main', color: 'white',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontWeight: 700, fontSize: '0.875rem', flexShrink: 0,
                      }}
                    >
                      {item.step}
                    </Box>
                    <Box>
                      <Typography variant="body2" fontWeight={600} gutterBottom>{item.title}</Typography>
                      <Typography variant="body2" color="text.secondary">{item.desc}</Typography>
                    </Box>
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default StudentRegistrationPage;
