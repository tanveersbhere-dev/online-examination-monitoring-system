import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Button,
  Stepper,
  Step,
  StepLabel,
  useTheme,
  useMediaQuery,
  Tooltip,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ShieldIcon from '@mui/icons-material/Shield';
import LogoutIcon from '@mui/icons-material/Logout';
import { useAuth } from '../hooks/useAuth';

const STEPS = [
  { label: 'Instructions', path: '/student/instructions' },
  { label: 'Device Check', path: '/student/device-check' },
  { label: 'Verification', path: '/student/identity' },
  { label: 'Examination', path: '/student/exam' },
];

const PAGES_WITHOUT_STEPPER = ['/', '/student', '/student/login', '/student/submitted'];

const StudentLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const { user, isAuthenticated, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    navigate('/student/login');
  };

  const showStepper = !PAGES_WITHOUT_STEPPER.includes(location.pathname);
  const activeStep = STEPS.findIndex((s) => location.pathname.startsWith(s.path));

  const getPageTitle = () => {
    const titles: Record<string, string> = {
      '/student': "Today's Examinations",
      '/student/login': 'Student Login',
      '/student/instructions': 'Exam Instructions',
      '/student/device-check': 'Device Check',
      '/student/identity': 'Identity Verification',
      '/student/exam': 'Examination',
      '/student/submitted': 'Submission Complete',
    };
    return titles[location.pathname] ?? 'ExamShield';
  };

  const getBackPath = () => {
    const backMap: Record<string, string> = {
      '/student': '/',
      '/student/login': '/',
      '/student/instructions': '/student',
      '/student/device-check': '/student/instructions',
      '/student/identity': '/student/device-check',
    };
    return backMap[location.pathname] ?? null;
  };

  const backPath = getBackPath();
  const isExamPage = location.pathname === '/student/exam';
  const isSubmittedPage = location.pathname === '/student/submitted';

  if (isExamPage) {
    // Exam page has its own full-screen layout — render with no chrome
    return (
      <Box sx={{ minHeight: '100vh', backgroundColor: '#F8FAFC' }}>
        <Outlet />
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: '#F8FAFC' }}>
      {/* ── Top App Bar ──────────────────────────────────────────────────── */}
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          backgroundColor: '#FFFFFF',
          color: '#0F172A',
          borderBottom: '1px solid #E2E8F0',
        }}
      >
        <Toolbar sx={{ minHeight: '60px !important', px: 2, gap: 1 }}>
          {/* Left — Back button or logo */}
          {backPath && !isSubmittedPage ? (
            <IconButton
              edge="start"
              onClick={() => navigate(backPath)}
              size="small"
              sx={{
                mr: 1,
                color: '#64748B',
                backgroundColor: '#F1F5F9',
                borderRadius: '8px',
                width: 36, height: 36,
                '&:hover': { backgroundColor: '#E2E8F0', color: '#0F172A' },
              }}
            >
              <ArrowBackIcon fontSize="small" />
            </IconButton>
          ) : (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mr: 1 }}>
              <Box sx={{
                width: 32, height: 32, borderRadius: '9px',
                background: 'linear-gradient(135deg, #0EA5E9, #059669)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 2px 8px rgba(14,165,233,0.3)',
              }}>
                <ShieldIcon sx={{ color: 'white', fontSize: 18 }} />
              </Box>
            </Box>
          )}

          {/* Centre — Page title */}
          <Typography
            variant="h6"
            sx={{
              flexGrow: 1,
              fontSize: '0.9375rem',
              fontWeight: 700,
              color: '#0F172A',
              letterSpacing: '-0.01em',
            }}
          >
            {getPageTitle()}
          </Typography>

          {/* Right — User profile & Logout */}
          {isAuthenticated ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box sx={{ display: { xs: 'none', sm: 'flex' }, flexDirection: 'column', alignItems: 'flex-end' }}>
                <Typography variant="body2" sx={{ fontWeight: 600, color: '#0F172A', fontSize: '0.8125rem', lineHeight: 1.2 }}>
                  {user?.full_name || user?.email}
                </Typography>
                <Typography variant="caption" sx={{ color: '#64748B', fontSize: '0.7rem' }}>
                  Student
                </Typography>
              </Box>
              <Tooltip title="Log Out">
                <Button
                  variant="outlined"
                  color="error"
                  size="small"
                  startIcon={<LogoutIcon fontSize="small" />}
                  onClick={handleLogout}
                  sx={{
                    borderRadius: '8px',
                    textTransform: 'none',
                    fontWeight: 600,
                    fontSize: '0.8125rem',
                    py: 0.5,
                    px: 1.5,
                  }}
                >
                  Logout
                </Button>
              </Tooltip>
            </Box>
          ) : (
            location.pathname !== '/student/login' && (
              <Button
                variant="contained"
                size="small"
                onClick={() => navigate('/student/login')}
                sx={{
                  borderRadius: '8px',
                  textTransform: 'none',
                  fontWeight: 600,
                  fontSize: '0.8125rem',
                  background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
                }}
              >
                Login
              </Button>
            )
          )}
        </Toolbar>
      </AppBar>

      {/* ── Step Indicator ───────────────────────────────────────────────── */}
      {showStepper && (
        <Box
          sx={{
            backgroundColor: '#FFFFFF',
            borderBottom: '1px solid #E2E8F0',
            py: 2,
            px: { xs: 2, md: 6 },
          }}
        >
          <Stepper
            activeStep={activeStep}
            alternativeLabel={isMobile}
            sx={{ maxWidth: 680, mx: 'auto' }}
          >
            {STEPS.map((step) => (
              <Step key={step.label}>
                <StepLabel
                  sx={{
                    '& .MuiStepLabel-label': {
                      fontSize: '0.75rem',
                      display: { xs: 'none', sm: 'block' },
                    },
                  }}
                >
                  {step.label}
                </StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>
      )}

      {/* ── Page Content ─────────────────────────────────────────────────── */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          maxWidth: showStepper ? '880px' : '100%',
          width: '100%',
          mx: 'auto',
          px: { xs: 2, md: 6 },
          py: { xs: 3, md: 4 },
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
};

export default StudentLayout;
