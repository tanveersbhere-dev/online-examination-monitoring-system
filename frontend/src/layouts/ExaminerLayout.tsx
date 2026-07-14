import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Avatar,
  Tooltip,
  useTheme,
  useMediaQuery,
  Badge,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import DescriptionIcon from '@mui/icons-material/Description';
import AssignmentIcon from '@mui/icons-material/Assignment';
import MonitorIcon from '@mui/icons-material/Monitor';
import AssessmentIcon from '@mui/icons-material/Assessment';
import BarChartIcon from '@mui/icons-material/BarChart';
import LogoutIcon from '@mui/icons-material/Logout';
import ShieldIcon from '@mui/icons-material/Shield';
import NotificationsIcon from '@mui/icons-material/Notifications';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';

const DRAWER_WIDTH = 260;
const DRAWER_COLLAPSED = 72;

interface NavItem {
  label: string;
  icon: React.ReactNode;
  path: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', icon: <DashboardIcon />, path: '/examiner/dashboard' },
  { label: 'Student Registration', icon: <PersonAddIcon />, path: '/examiner/students' },
  { label: 'Question Papers', icon: <DescriptionIcon />, path: '/examiner/question-papers' },
  { label: 'Exam Management', icon: <AssignmentIcon />, path: '/examiner/exams' },
  { label: 'Live Monitoring', icon: <MonitorIcon />, path: '/examiner/monitoring' },
  { label: 'Monitoring Reports', icon: <AssessmentIcon />, path: '/examiner/reports' },
  { label: 'Statistics', icon: <BarChartIcon />, path: '/examiner/statistics' },
];

const ExaminerLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const drawerWidth = collapsed && !isMobile ? DRAWER_COLLAPSED : DRAWER_WIDTH;

  const isActive = (path: string) => location.pathname === path;

  const getPageTitle = () => {
    const found = NAV_ITEMS.find((n) => location.pathname === n.path);
    return found?.label ?? 'Dashboard';
  };

  const DrawerContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Brand Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          px: 2,
          py: 2,
          minHeight: 64,
          gap: 1.5,
          overflow: 'hidden',
        }}
      >
        <ShieldIcon sx={{ color: 'primary.main', fontSize: 32, flexShrink: 0 }} />
        {(!collapsed || isMobile) && (
          <Typography variant="subtitle1" fontWeight={700} color="primary.main" noWrap>
            ExamShield
          </Typography>
        )}
      </Box>

      <Divider />

      {/* User Profile */}
      {(!collapsed || isMobile) && (
        <Box sx={{ px: 2, py: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Avatar sx={{ width: 36, height: 36, bgcolor: 'primary.main', fontSize: '0.875rem' }}>
              EX
            </Avatar>
            <Box sx={{ overflow: 'hidden' }}>
              <Typography variant="body2" fontWeight={600} noWrap>
                Examiner
              </Typography>
              <Typography variant="caption" color="text.secondary" noWrap>
                admin@examshield.com
              </Typography>
            </Box>
          </Box>
        </Box>
      )}

      <Divider sx={{ mb: 1 }} />

      {/* Navigation Items */}
      <List sx={{ flexGrow: 1, px: 0 }}>
        {NAV_ITEMS.map((item) => (
          <Tooltip
            key={item.path}
            title={collapsed && !isMobile ? item.label : ''}
            placement="right"
          >
            <ListItemButton
              selected={isActive(item.path)}
              onClick={() => {
                navigate(item.path);
                if (isMobile) setMobileOpen(false);
              }}
              sx={{
                minHeight: 48,
                justifyContent: collapsed && !isMobile ? 'center' : 'flex-start',
                px: collapsed && !isMobile ? 1.5 : 2,
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: collapsed && !isMobile ? 'auto' : 40,
                  color: isActive(item.path) ? 'primary.main' : 'text.secondary',
                }}
              >
                {item.icon}
              </ListItemIcon>
              {(!collapsed || isMobile) && (
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: isActive(item.path) ? 600 : 400 }}
                />
              )}
            </ListItemButton>
          </Tooltip>
        ))}
      </List>

      <Divider />

      {/* Logout */}
      <List sx={{ pb: 1 }}>
        <Tooltip title={collapsed && !isMobile ? 'Logout' : ''} placement="right">
          <ListItemButton
            onClick={() => navigate('/examiner/login')}
            sx={{
              minHeight: 48,
              justifyContent: collapsed && !isMobile ? 'center' : 'flex-start',
              px: collapsed && !isMobile ? 1.5 : 2,
            }}
          >
            <ListItemIcon sx={{ minWidth: collapsed && !isMobile ? 'auto' : 40, color: 'error.main' }}>
              <LogoutIcon />
            </ListItemIcon>
            {(!collapsed || isMobile) && (
              <ListItemText
                primary="Logout"
                primaryTypographyProps={{ fontSize: '0.875rem', color: 'error.main', fontWeight: 500 }}
              />
            )}
          </ListItemButton>
        </Tooltip>
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', backgroundColor: 'background.default' }}>
      {/* Desktop Permanent Drawer */}
      {!isMobile && (
        <Drawer
          variant="permanent"
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            transition: theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              boxSizing: 'border-box',
              backgroundColor: '#F8FAFC',
              borderRight: '1px solid',
              borderColor: 'divider',
              transition: theme.transitions.create('width', {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.enteringScreen,
              }),
              overflowX: 'hidden',
            },
          }}
        >
          {DrawerContent}
        </Drawer>
      )}

      {/* Mobile Temporary Drawer */}
      {isMobile && (
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            '& .MuiDrawer-paper': {
              width: DRAWER_WIDTH,
              backgroundColor: '#F8FAFC',
            },
          }}
        >
          {DrawerContent}
        </Drawer>
      )}

      {/* Main Content Area */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Top App Bar */}
        <AppBar
          position="sticky"
          elevation={0}
          sx={{
            backgroundColor: 'background.paper',
            color: 'text.primary',
            borderBottom: '1px solid',
            borderColor: 'divider',
            zIndex: theme.zIndex.drawer - 1,
          }}
        >
          <Toolbar sx={{ gap: 1 }}>
            {/* Hamburger — mobile */}
            {isMobile && (
              <IconButton edge="start" onClick={() => setMobileOpen(true)}>
                <MenuIcon />
              </IconButton>
            )}

            {/* Collapse toggle — desktop */}
            {!isMobile && (
              <IconButton onClick={() => setCollapsed((c) => !c)} size="small" sx={{ mr: 1 }}>
                {collapsed ? <MenuIcon fontSize="small" /> : <ChevronLeftIcon fontSize="small" />}
              </IconButton>
            )}

            <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 600, fontSize: '1.125rem' }}>
              {getPageTitle()}
            </Typography>

            {/* Notifications */}
            <IconButton size="small">
              <Badge badgeContent={2} color="error">
                <NotificationsIcon fontSize="small" />
              </Badge>
            </IconButton>

            {/* Avatar */}
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: '0.8rem', cursor: 'pointer' }}>
              EX
            </Avatar>
          </Toolbar>
        </AppBar>

        {/* Page Content */}
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: { xs: 2, md: 3 },
            overflow: 'auto',
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
};

export default ExaminerLayout;
