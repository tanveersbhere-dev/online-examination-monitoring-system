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
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ShieldIcon from '@mui/icons-material/Shield';

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
      '/student/login': '/student',
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
      <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default' }}>
        <Outlet />
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'background.default' }}>
      {/* Top App Bar */}
      <AppBar
        position="sticky"
        elevation={1}
        sx={{
          backgroundColor: 'background.paper',
          color: 'text.primary',
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Toolbar sx={{ minHeight: '56px !important', px: 2, gap: 1 }}>
          {/* Left — Back button */}
          {backPath && !isSubmittedPage ? (
            <IconButton edge="start" onClick={() => navigate(backPath)} size="small" sx={{ mr: 1 }}>
              <ArrowBackIcon fontSize="small" />
            </IconButton>
          ) : (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mr: 1 }}>
              <ShieldIcon sx={{ color: 'primary.main', fontSize: 28 }} />
            </Box>
          )}

          {/* Centre — Page title */}
          <Typography variant="h6" sx={{ flexGrow: 1, fontSize: '1rem', fontWeight: 600, color: 'primary.main' }}>
            {getPageTitle()}
          </Typography>

          {/* Right — Today's date */}
          {!isSubmittedPage && (
            <Typography variant="caption" sx={{ color: 'text.secondary', display: { xs: 'none', sm: 'block' } }}>
              {new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
            </Typography>
          )}
        </Toolbar>
      </AppBar>

      {/* Step Indicator */}
      {showStepper && (
        <Box
          sx={{
            backgroundColor: 'background.paper',
            borderBottom: '1px solid',
            borderColor: 'divider',
            py: 1.5,
            px: { xs: 2, md: 6 },
          }}
        >
          <Stepper
            activeStep={activeStep}
            alternativeLabel={isMobile}
            sx={{ maxWidth: 700, mx: 'auto' }}
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

      {/* Page Content */}
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
