import { useState, useEffect } from 'react';
import {
  Box, Typography, Button, Paper, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TablePagination,
  IconButton, TextField, Chip, Checkbox, Menu, MenuItem, Tooltip
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import SearchIcon from '@mui/icons-material/Search';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import ArchiveIcon from '@mui/icons-material/Archive';
import FileDownloadIcon from '@mui/icons-material/FileDownload';

import apiClient from '../../services/apiClient';
import StudentFormDialog from '../../components/students/StudentFormDialog';
import ImportWizardDialog from '../../components/students/ImportWizardDialog';
import StudentProfileDrawer from '../../components/students/StudentProfileDrawer';

export default function StudentRegistrationPage() {
  const [students, setStudents] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Selection
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  // Dialogs
  const [formOpen, setFormOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  
  // Current Student for Edit/View
  const [currentStudent, setCurrentStudent] = useState<any>(null);

  const fetchStudents = async () => {
    try {
      const res = await apiClient.get('/workspace/students', {
        params: {
          skip: page * rowsPerPage,
          limit: rowsPerPage,
          search: searchQuery || undefined
        }
      });
      setStudents(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      console.error("Failed to load students", err);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, [page, rowsPerPage, searchQuery]);

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      setSelectedIds(students.map(s => s.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectOne = (id: number) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const handleSaveStudent = async (data: any) => {
    if (currentStudent) {
      await apiClient.put(`/workspace/students/${currentStudent.id}`, data);
    } else {
      await apiClient.post('/workspace/students', data);
    }
    fetchStudents();
  };

  const handleArchive = async (id: number) => {
    if (window.confirm("Are you sure you want to archive this student?")) {
      await apiClient.delete(`/workspace/students/${id}`);
      fetchStudents();
    }
  };

  const handleBulkAction = async (action: string) => {
    if (selectedIds.length === 0) return;
    if (window.confirm(`Are you sure you want to ${action.toLowerCase()} ${selectedIds.length} students?`)) {
      await apiClient.post('/workspace/students/bulk-action', { student_ids: selectedIds, action });
      setSelectedIds([]);
      fetchStudents();
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" fontWeight="bold">Student Repository</Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" startIcon={<UploadFileIcon />} onClick={() => setImportOpen(true)}>
            Import CSV
          </Button>
          <Button variant="outlined" startIcon={<FileDownloadIcon />}>
            Export
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => { setCurrentStudent(null); setFormOpen(true); }}>
            Add Student
          </Button>
        </Box>
      </Box>

      <Paper sx={{ mb: 2, p: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
        <TextField
          size="small"
          placeholder="Search by name, reg no, email..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{ startAdornment: <SearchIcon color="action" sx={{ mr: 1 }} /> }}
          sx={{ width: 300 }}
        />
        {/* Future Filters could go here */}
        
        {selectedIds.length > 0 && (
          <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2" color="primary">{selectedIds.length} selected</Typography>
            <Button size="small" variant="contained" color="warning" onClick={() => handleBulkAction('ARCHIVE')}>
              Archive Selected
            </Button>
          </Box>
        )}
      </Paper>

      <TableContainer component={Paper}>
        <Table sx={{ minWidth: 650 }} size="small">
          <TableHead sx={{ bgcolor: 'grey.50' }}>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  indeterminate={selectedIds.length > 0 && selectedIds.length < students.length}
                  checked={students.length > 0 && selectedIds.length === students.length}
                  onChange={handleSelectAll}
                />
              </TableCell>
              <TableCell>Registration No</TableCell>
              <TableCell>Full Name</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Department</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {students.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                  <Typography variant="body2" color="text.secondary">No students found.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              students.map((row) => (
                <TableRow key={row.id} hover selected={selectedIds.includes(row.id)}>
                  <TableCell padding="checkbox">
                    <Checkbox checked={selectedIds.includes(row.id)} onChange={() => handleSelectOne(row.id)} />
                  </TableCell>
                  <TableCell>{row.registration_number}</TableCell>
                  <TableCell sx={{ fontWeight: 500 }}>{row.full_name}</TableCell>
                  <TableCell>{row.email}</TableCell>
                  <TableCell>{row.department || '-'}</TableCell>
                  <TableCell>
                    <Chip 
                      label={row.status} 
                      size="small" 
                      color={row.status === 'ACTIVE' ? 'success' : row.status === 'ARCHIVED' ? 'default' : 'warning'} 
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="View Profile">
                      <IconButton size="small" onClick={() => { setCurrentStudent(row); setProfileOpen(true); }}>
                        <VisibilityIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Edit">
                      <IconButton size="small" onClick={() => { setCurrentStudent(row); setFormOpen(true); }}>
                        <EditIcon fontSize="small" color="primary" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Archive">
                      <IconButton size="small" onClick={() => handleArchive(row.id)}>
                        <ArchiveIcon fontSize="small" color="error" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[10, 25, 50]}
          component="div"
          count={total}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
        />
      </TableContainer>

      {/* Dialogs */}
      <StudentFormDialog 
        open={formOpen} 
        onClose={() => setFormOpen(false)} 
        initialData={currentStudent}
        onSubmit={handleSaveStudent} 
      />
      
      <ImportWizardDialog 
        open={importOpen} 
        onClose={() => setImportOpen(false)} 
        onSuccess={fetchStudents} 
      />

      <StudentProfileDrawer 
        open={profileOpen} 
        onClose={() => setProfileOpen(false)} 
        student={currentStudent} 
      />
    </Box>
  );
}
