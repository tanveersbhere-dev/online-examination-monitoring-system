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
import EditIcon from '@mui/icons-material/Edit';
import apiClient from '../../services/apiClient';
import { getErrorMessage } from '../../utils/errorHandler';

interface QuestionPaper {
  id: number;
  title: string;
  course_name: string;
  description: string;
  uploaded_by: number;
  file_path: string;
  file_size_bytes: number;
  mime_type: string;
  revision: number;
  status: string;
  created_at: string;
}

const STATUS_CONFIG: Record<string, any> = {
  DRAFT: { label: 'Draft', color: 'default' },
  READY: { label: 'Ready', color: 'info' },
  LOCKED: { label: 'Locked', color: 'success' },
  ARCHIVED: { label: 'Archived', color: 'default' }
};

const QuestionPapersPage = () => {
  const [papers, setPapers] = useState<QuestionPaper[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Modal state
  const [openModal, setOpenModal] = useState(false);
  const [updateMode, setUpdateMode] = useState<number | null>(null);
  
  const [title, setTitle] = useState('');
  const [course, setCourse] = useState('');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchPapers = async () => {
    try {
      setLoading(true);
      const res = await apiClient.get('/question-papers');
      setPapers(res.data);
    } catch (err: any) {
      console.error(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPapers();
  }, []);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleOpenUpload = () => {
    setUpdateMode(null);
    setTitle('');
    setCourse('');
    setDescription('');
    setFile(null);
    setOpenModal(true);
  };

  const handleOpenUpdate = (paper: QuestionPaper) => {
    setUpdateMode(paper.id);
    setTitle(paper.title);
    setCourse(paper.course_name);
    setDescription(paper.description || '');
    setFile(null);
    setOpenModal(true);
  };

  const handlePreview = (id: number) => {
    const token = localStorage.getItem('access_token');
    // Using simple fetch to handle binary and pop open a blob url, since direct window.open lacks Auth headers
    fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/question-papers/${id}/download?preview=true`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(response => response.blob())
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank');
    })
    .catch(err => alert("Error loading preview."));
  };

  const handleSave = async () => {
    setUploading(true);
    setError(null);

    try {
      if (updateMode) {
        // Update Metadata
        await apiClient.put(`/question-papers/${updateMode}`, { title, course_name: course, description });
        // Update File if selected
        if (file) {
          const fileData = new FormData();
          fileData.append('file', file);
          await apiClient.put(`/question-papers/${updateMode}/file`, fileData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
        }
      } else {
        if (!title || !course || !file) {
          setError("Please fill out all required fields and select a file.");
          setUploading(false);
          return;
        }
        const formData = new FormData();
        formData.append('title', title);
        formData.append('course_name', course);
        if (description) formData.append('description', description);
        formData.append('file', file);

        await apiClient.post('/question-papers', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      }

      setOpenModal(false);
      fetchPapers();
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this question paper?")) return;
    try {
      await apiClient.delete(`/question-papers/${id}`);
      fetchPapers();
    } catch (err: any) {
      alert(getErrorMessage(err));
    }
  };

  const filteredPapers = papers.filter(p => 
    p.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
    p.course_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" fontWeight={600}>Assessment Repository</Typography>
        <Button variant="contained" startIcon={<UploadFileIcon />} sx={{ borderRadius: 2 }} onClick={handleOpenUpload}>
          Upload Assessment
        </Button>
      </Box>

      <Card elevation={1}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <TextField
              placeholder="Search by title or course..."
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
                  <TableCell>Revision</TableCell>
                  <TableCell>Size</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={6} align="center"><CircularProgress size={24} sx={{ my: 2 }} /></TableCell></TableRow>
                ) : filteredPapers.length === 0 ? (
                  <TableRow><TableCell colSpan={6} align="center"><Typography color="text.secondary">No assessments found.</Typography></TableCell></TableRow>
                ) : filteredPapers.map((paper) => {
                  const cfg = STATUS_CONFIG[paper.status] || STATUS_CONFIG['DRAFT'];
                  return (
                    <TableRow key={paper.id} hover>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                          <DescriptionIcon sx={{ color: 'primary.main', fontSize: 20 }} />
                          <Box>
                            <Typography variant="body2" fontWeight={600}>{paper.title}</Typography>
                            <Typography variant="caption" color="text.secondary">{new Date(paper.created_at).toLocaleDateString()}</Typography>
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell><Chip label={paper.course_name} size="small" variant="outlined" /></TableCell>
                      <TableCell><Typography variant="body2">v{paper.revision}</Typography></TableCell>
                      <TableCell><Typography variant="body2" color="text.secondary">{formatBytes(paper.file_size_bytes)}</Typography></TableCell>
                      <TableCell><Chip label={cfg.label} color={cfg.color} size="small" /></TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                          <Tooltip title="Preview PDF"><IconButton size="small" onClick={() => handlePreview(paper.id)}><VisibilityIcon fontSize="small" /></IconButton></Tooltip>
                          {paper.status !== 'LOCKED' && (
                            <>
                              <Tooltip title="Edit Metadata & File"><IconButton size="small" color="primary" onClick={() => handleOpenUpdate(paper)}><EditIcon fontSize="small" /></IconButton></Tooltip>
                              <Tooltip title="Delete"><IconButton size="small" sx={{ color: 'error.main' }} onClick={() => handleDelete(paper.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                            </>
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

      {/* Upload/Edit Modal */}
      <Dialog open={openModal} onClose={() => !uploading && setOpenModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{updateMode ? 'Edit Assessment' : 'Upload Assessment'}</DialogTitle>
        <DialogContent dividers>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <Stack spacing={3} sx={{ mt: 1 }}>
            <TextField label="Assessment Title" value={title} onChange={(e) => setTitle(e.target.value)} disabled={uploading} fullWidth required />
            <TextField label="Course Name" value={course} onChange={(e) => setCourse(e.target.value)} disabled={uploading} fullWidth required />
            <TextField label="Description" value={description} onChange={(e) => setDescription(e.target.value)} disabled={uploading} fullWidth multiline rows={2} />
            <Box>
              <Typography variant="subtitle2" gutterBottom>Document {updateMode ? '(Optional: Select to replace current revision)' : '*'}</Typography>
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
          <Button variant="contained" onClick={handleSave} disabled={uploading || (!updateMode && (!title || !course || !file))}>
            {uploading ? 'Saving...' : updateMode ? 'Save Changes' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default QuestionPapersPage;
