import { useState, useEffect } from 'react';
import { Box, Typography, Paper, Grid, TextField, Button, CircularProgress, Alert, Switch, FormControlLabel } from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import apiClient from '../../services/apiClient';

interface SystemSetting {
  id: number;
  key: string;
  value: string;
  description: string;
  is_public: boolean;
}

export default function PlatformSettingsPage() {
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [savingKey, setSavingKey] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get('/admin/settings')
      .then(res => setSettings(res.data))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load settings'))
      .finally(() => setLoading(false));
  }, []);

  const handleUpdate = (key: string, value: string, isPublic: boolean) => {
    setSavingKey(key);
    apiClient.put(`/admin/settings/${key}`, { value, is_public: isPublic })
      .then(res => {
        setSettings(prev => prev.map(s => s.key === key ? { ...s, value: res.data.value, is_public: res.data.is_public } : s));
      })
      .catch(err => {
        alert(err.response?.data?.detail || 'Failed to save setting');
      })
      .finally(() => setSavingKey(null));
  };

  const handleCreate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const key = data.get('key') as string;
    const value = data.get('value') as string;
    const desc = data.get('description') as string;
    
    setSavingKey('new');
    apiClient.put(`/admin/settings/${key}`, { value, description: desc, is_public: false })
      .then(res => {
        setSettings([...settings, res.data]);
        e.currentTarget.reset();
      })
      .catch(err => alert(err.response?.data?.detail || 'Failed to create setting'))
      .finally(() => setSavingKey(null));
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 5 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error" sx={{ m: 3 }}>{error}</Alert>;

  return (
    <Box>
      <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
        <SettingsIcon sx={{ fontSize: 32, color: 'text.secondary' }} />
        <Typography variant="h4" fontWeight={600}>Platform Settings</Typography>
      </Box>

      <Typography variant="body1" sx={{ mb: 3 }}>
        Manage global configuration properties and feature toggles here.
      </Typography>

      <Grid container spacing={3}>
        {settings.map((setting) => (
          <Grid item xs={12} md={6} key={setting.key}>
            <Paper sx={{ p: 3, borderRadius: 2, height: '100%', border: '1px solid #eee' }} elevation={0}>
              <Typography variant="h6" fontWeight={600} gutterBottom>{setting.key}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{setting.description || 'No description provided.'}</Typography>
              
              <TextField 
                fullWidth 
                size="small" 
                label="Value" 
                defaultValue={setting.value} 
                sx={{ mb: 2 }}
                id={`val-${setting.key}`}
              />
              
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <FormControlLabel 
                  control={<Switch defaultChecked={setting.is_public} id={`pub-${setting.key}`} />} 
                  label="Publicly Accessible" 
                />
                <Button 
                  variant="contained" 
                  disabled={savingKey === setting.key}
                  onClick={() => {
                    const val = (document.getElementById(`val-${setting.key}`) as HTMLInputElement).value;
                    const pub = (document.getElementById(`pub-${setting.key}`) as HTMLInputElement).checked;
                    handleUpdate(setting.key, val, pub);
                  }}
                >
                  {savingKey === setting.key ? 'Saving...' : 'Save'}
                </Button>
              </Box>
            </Paper>
          </Grid>
        ))}

        {/* Add New Setting Form */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3, borderRadius: 2, border: '1px dashed #ccc', mt: 2 }} elevation={0}>
            <Typography variant="h6" fontWeight={600} gutterBottom>Add New Configuration Key</Typography>
            <Box component="form" onSubmit={handleCreate} sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mt: 2 }}>
              <TextField name="key" label="Setting Key (e.g., MAINTENANCE_MODE)" size="small" required sx={{ minWidth: 200 }} />
              <TextField name="value" label="Value" size="small" required sx={{ flexGrow: 1 }} />
              <TextField name="description" label="Description" size="small" sx={{ flexGrow: 2 }} />
              <Button type="submit" variant="outlined" disabled={savingKey === 'new'}>
                {savingKey === 'new' ? 'Adding...' : 'Add Config'}
              </Button>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
