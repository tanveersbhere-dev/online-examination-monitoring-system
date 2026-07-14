




import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActionArea,
  Chip,
} from '@mui/material';
import ShieldIcon from '@mui/icons-material/Shield';
import SchoolIcon from '@mui/icons-material/School';
import BadgeIcon from '@mui/icons-material/Badge';

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(160deg, #FAFAFA 60%, #E3F2FD 100%)',
        px: 3,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Subtle background pattern */}
      <Box
        sx={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'radial-gradient(circle at 2px 2px, #CFD8DC 1px, transparent 0)',
          backgroundSize: '40px 40px',
          opacity: 0.3,
          pointerEvents: 'none',
        }}
      />

      {/* Brand Block */}
      <Box sx={{ textAlign: 'center', mb: 6, position: 'relative', zIndex: 1 }}>
        <Box
          sx={{
            width: 80,
            height: 80,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #1565C0, #1976D2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mx: 'auto',
            mb: 2.5,
            boxShadow: '0 8px 24px rgba(21,101,192,0.25)',
          }}
        >
          <ShieldIcon sx={{ color: 'white', fontSize: 44 }} />
        </Box>
        <Typography
          variant="h3"
          sx={{ fontWeight: 700, color: 'primary.main', mb: 1 }}
        >
          ExamShield
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          Secure. Monitored. Trusted.
        </Typography>
        <Chip
          label="Online Examination Monitoring System"
          size="small"
          sx={{ backgroundColor: 'primary.light', color: 'white', fontWeight: 500 }}
        />
      </Box>

      {/* Role Cards */}
      <Box
        sx={{
          display: 'flex',
          gap: { xs: 3, md: 6 },
          flexDirection: { xs: 'column', sm: 'row' },
          position: 'relative',
          zIndex: 1,
        }}
      >
        {/* Student Card */}
        <Card
          sx={{
            width: { xs: '90vw', sm: 280 },
            borderRadius: 4,
            transition: 'all 0.2s ease-out',
            '&:hover': {
              transform: 'translateY(-6px)',
              boxShadow: '0 16px 40px rgba(21,101,192,0.18)',
              '& .accent-line': { opacity: 1 },
            },
          }}
          elevation={1}
        >
          <CardActionArea onClick={() => navigate('/student')} sx={{ p: 0 }}>
            <CardContent sx={{ p: '32px !important', textAlign: 'center' }}>
              <Box
                sx={{
                  width: 96,
                  height: 96,
                  borderRadius: '50%',
                  backgroundColor: 'primary.light',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mx: 'auto',
                  mb: 2.5,
                  opacity: 0.9,
                }}
              >
                <SchoolIcon sx={{ fontSize: 52, color: 'white' }} />
              </Box>
              <Typography variant="h5" fontWeight={600} gutterBottom>
                Student
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Enter Today's Examinations
              </Typography>
            </CardContent>
            {/* Bottom accent line */}
            <Box
              className="accent-line"
              sx={{
                height: 3,
                backgroundColor: 'primary.main',
                opacity: 0,
                transition: 'opacity 0.2s',
                borderRadius: '0 0 4px 4px',
              }}
            />
          </CardActionArea>
        </Card>

        {/* Examiner Card */}
        <Card
          sx={{
            width: { xs: '90vw', sm: 280 },
            borderRadius: 4,
            transition: 'all 0.2s ease-out',
            '&:hover': {
              transform: 'translateY(-6px)',
              boxShadow: '0 16px 40px rgba(21,101,192,0.18)',
              '& .accent-line': { opacity: 1 },
            },
          }}
          elevation={1}
        >
          <CardActionArea onClick={() => navigate('/examiner/login')} sx={{ p: 0 }}>
            <CardContent sx={{ p: '32px !important', textAlign: 'center' }}>
              <Box
                sx={{
                  width: 96,
                  height: 96,
                  borderRadius: '50%',
                  backgroundColor: 'primary.main',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mx: 'auto',
                  mb: 2.5,
                }}
              >
                <BadgeIcon sx={{ fontSize: 52, color: 'white' }} />
              </Box>
              <Typography variant="h5" fontWeight={600} gutterBottom>
                Examiner
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Access the Dashboard
              </Typography>
            </CardContent>
            <Box
              className="accent-line"
              sx={{
                height: 3,
                backgroundColor: 'primary.main',
                opacity: 0,
                transition: 'opacity 0.2s',
                borderRadius: '0 0 4px 4px',
              }}
            />
          </CardActionArea>
        </Card>
      </Box>

      {/* Footer */}
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ mt: 8, position: 'relative', zIndex: 1 }}
      >
        © 2026 ExamShield &nbsp;·&nbsp; v{import.meta.env.VITE_APP_VERSION ?? '1.0.0'}
      </Typography>
    </Box>
  );
};

export default LandingPage;