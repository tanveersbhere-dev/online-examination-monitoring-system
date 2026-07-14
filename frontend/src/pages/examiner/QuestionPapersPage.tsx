import { useState, useEffect, useRef } from 'react';
import {
  Box, Typography, Card, CardContent, Button, TextField,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Chip, IconButton, InputAdornment, Tooltip, Stack, Dialog, DialogTitle,
  DialogContent, DialogActions, Alert, CircularProgress
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DeleteIcon from '@mui/icons-material/Delete';
import DescriptionIcon from '@mui/icons-material/Description';
import apiClient from '../../services/apiClient';

interface QuestionPaper {
  id: number;
  title: string;
  course_name: string;
  uploaded_by: number;
  file_path: string;
  created_at: string;
}

const QuestionPapersPage = () => {
  const [papers, setPapers] = useState<QuestionPaper[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Modal state
  const [openModal, setOpenModal] = useState(false);
  const [title, setTitle] = useState('');
  const [course, setCourse] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchPapers = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get('/exams/question-papers');
      setPapers(res.data);
    } catch (err) {
      console.error('Failed to fetch question papers', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPapers();
  }, []);

  const handleUpload = async () => {
    if (!title || !course || !file) {
      setError("Please fill out all fields and select a file.");
      return;
    }

    setUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append('title', title);
    formData.append('course_name', course);
    formData.append('file', file);

    try {
      await apiClient.post('/exams/question-paper', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setOpenModal(false);
      setTitle('');
      setCourse('');
      setFile(null);
      fetchPapers();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to upload question paper.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this question paper?")) return;
    try {
      await apiClient.delete(`/exams/question-paper/${id}`);
      fetchPapers();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to delete question paper.");
    }
  };

  const filteredPapers = papers.filter(p => 
    p.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
    p.course_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" fontWeight={600}>Question Papers</Typography>
        <Button variant="contained" startIcon={<UploadFileIcon />} sx={{ borderRadius: 2 }} onClick={() => setOpenModal(true)}>
          Upload Paper
        </Button>
      </Box>

      <Card elevation={1}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <TextField
              placeholder="Search papers..."
              size="small"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              sx={{ maxWidth: 320 }}
              InputProps={{
                startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment>,
              }}
            />
          </Box>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Title</TableCell>
                  <TableCell>Course</TableCell>
                  <TableCell>Date Uploaded</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={4} align="center"><CircularProgress size={24} sx={{ my: 2 }} /></TableCell></TableRow>
                ) : filteredPapers.length === 0 ? (
                  <TableRow><TableCell colSpan={4} align="center"><Typography color="text.secondary">No question papers found.</Typography></TableCell></TableRow>
                ) : filteredPapers.map((paper) => (
                  <TableRow key={paper.id} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                        <DescriptionIcon sx={{ color: 'primary.main', fontSize: 20 }} />
                        <Typography variant="body2" fontWeight={600}>{paper.title}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell><Chip label={paper.course_name} size="small" variant="outlined" /></TableCell>
                    <TableCell><Typography variant="body2" color="text.secondary">{new Date(paper.created_at).toLocaleDateString()}</Typography></TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                        <Tooltip title="Preview"><IconButton size="small"><VisibilityIcon fontSize="small" /></IconButton></Tooltip>
                        <Tooltip title="Delete"><IconButton size="small" sx={{ color: 'error.main' }} onClick={() => handleDelete(paper.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Upload Modal */}
      <Dialog open={openModal} onClose={() => !uploading && setOpenModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload Question Paper</DialogTitle>
        <DialogContent dividers>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <Stack spacing={3} sx={{ mt: 1 }}>
            <TextField label="Paper Title" value={title} onChange={(e) => setTitle(e.target.value)} disabled={uploading} fullWidth required />
            <TextField label="Course Name" value={course} onChange={(e) => setCourse(e.target.value)} disabled={uploading} fullWidth required />
            <Box>
              <Typography variant="subtitle2" gutterBottom>PDF Document *</Typography>
              <input type="file" accept=".pdf,.docx,.txt" ref={fileInputRef} style={{ display: 'none' }} onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)} />
              <Box 
                sx={{ 
                  border: '1px dashed', borderColor: 'divider', borderRadius: 1, p: 2, 
                  textAlign: 'center', cursor: 'pointer',
                  bgcolor: file ? 'primary.light' : 'transparent',
                  color: file ? 'primary.main' : 'text.secondary'
                }}
                onClick={() => fileInputRef.current?.click()}
              >
                {file ? file.name : 'Click to select a file (PDF, DOCX, TXT)'}
              </Box>
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenModal(false)} disabled={uploading}>Cancel</Button>
          <Button variant="contained" onClick={handleUpload} disabled={uploading || !title || !course || !file}>
            {uploading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default QuestionPapersPage;
