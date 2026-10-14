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
  Menu,
  MenuItem,
  Breadcrumbs,
  Link,
  InputBase,
  Paper,
  Popover,
  alpha,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import SearchIcon from '@mui/icons-material/Search';
import NotificationsIcon from '@mui/icons-material/Notifications';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ShieldIcon from '@mui/icons-material/Shield';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import LogoutIcon from '@mui/icons-material/Logout';
import PersonIcon from '@mui/icons-material/Person';
import SettingsIcon from '@mui/icons-material/Settings';

import { resourceRegistry } from '../registry/resourceRegistry';
import { useAuth } from '../hooks/useAuth';

const DRAWER_WIDTH = 260;
const DRAWER_COLLAPSED = 72;

// ─── Dark sidebar color tokens ─────────────────────────────────────────────────
const SIDEBAR_BG = '#0F172A';           // deep slate
const SIDEBAR_BORDER = '#1E293B';       // subtle border
const SIDEBAR_TEXT = 'rgba(255,255,255,0.75)';
const SIDEBAR_TEXT_MUTED = 'rgba(255,255,255,0.35)';
const SIDEBAR_HOVER = 'rgba(255,255,255,0.06)';
const SIDEBAR_ACTIVE_BG = 'rgba(37,99,235,0.18)';
const SIDEBAR_ACTIVE_BORDER = '#2563EB';
const SIDEBAR_ACTIVE_TEXT = '#FFFFFF';
const SIDEBAR_ACTIVE_ICON = '#93C5FD';

const ExaminerLayout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { user, logout } = useAuth();
  
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  // User Menu State
  const [anchorElUser, setAnchorElUser] = useState<null | HTMLElement>(null);
  
  // Notification Popover State
  const [anchorElNotif, setAnchorElNotif] = useState<null | HTMLElement>(null);

  const drawerWidth = collapsed && !isMobile ? DRAWER_COLLAPSED : DRAWER_WIDTH;

  const isActive = (path: string) => location.pathname.startsWith(path);

  const currentResource = resourceRegistry.find((r) => location.pathname === r.route) || resourceRegistry.find((r) => location.pathname.startsWith(r.route));
  const pageTitle = currentResource ? currentResource.name : 'Dashboard';

  const navItems = resourceRegistry.filter(
    (r) => r.navVisibility && r.permissions.includes(user?.role?.name || 'Examiner')
  );

  const handleOpenUserMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElUser(event.currentTarget);
  };
  const handleCloseUserMenu = () => {
    setAnchorElUser(null);
  };

  const handleOpenNotifMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElNotif(event.currentTarget);
  };
  const handleCloseNotifMenu = () => {
    setAnchorElNotif(null);
  };

  const handleLogout = () => {
    handleCloseUserMenu();
    logout();
    navigate('/examiner/login');
  };

  const DrawerContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: SIDEBAR_BG }}>
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
          borderBottom: `1px solid ${SIDEBAR_BORDER}`,
        }}
      >
        <Box sx={{
          width: 34, height: 34, borderRadius: '10px', flexShrink: 0,
          background: 'linear-gradient(135deg, #2563EB, #0EA5E9)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 2px 8px rgba(37,99,235,0.4)',
        }}>
          <ShieldIcon sx={{ color: 'white', fontSize: 20 }} />
        </Box>
        {(!collapsed || isMobile) && (
          <Typography variant="subtitle1" fontWeight={800} noWrap sx={{ color: '#FFFFFF', letterSpacing: '-0.01em' }}>
            ExamShield
          </Typography>
        )}
      </Box>

      {/* User Profile Summary */}
      {(!collapsed || isMobile) && (
        <Box sx={{ px: 2, py: 2, borderBottom: `1px solid ${SIDEBAR_BORDER}` }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Avatar
              src={user?.profile_picture_url || ''}
              sx={{
                width: 36, height: 36,
                background: 'linear-gradient(135deg, #2563EB, #0EA5E9)',
                fontSize: '0.8rem', fontWeight: 700,
                border: '2px solid rgba(37,99,235,0.4)',
              }}
            >
              {user?.full_name?.substring(0, 2).toUpperCase() || 'EX'}
            </Avatar>
            <Box sx={{ overflow: 'hidden', flex: 1 }}>
              <Typography variant="body2" fontWeight={600} noWrap sx={{ color: '#FFFFFF', fontSize: '0.8125rem' }}>
                {user?.full_name || 'Examiner'}
              </Typography>
              <Typography variant="caption" noWrap sx={{ color: SIDEBAR_TEXT_MUTED, fontSize: '0.7rem' }}>
                {user?.email || 'admin@examshield.com'}
              </Typography>
            </Box>
          </Box>
        </Box>
      )}

      {/* Collapsed avatar */}
      {collapsed && !isMobile && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 1.5, borderBottom: `1px solid ${SIDEBAR_BORDER}` }}>
          <Avatar
            src={user?.profile_picture_url || ''}
            sx={{
              width: 32, height: 32,
              background: 'linear-gradient(135deg, #2563EB, #0EA5E9)',
              fontSize: '0.75rem', fontWeight: 700,
            }}
          >
            {user?.full_name?.substring(0, 2).toUpperCase() || 'EX'}
          </Avatar>
        </Box>
      )}

      {/* Dynamic Navigation Items */}
      <List sx={{ flexGrow: 1, px: 1, py: 1.5, overflowY: 'auto' }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.route);
          return (
            <Tooltip
              key={item.route}
              title={collapsed && !isMobile ? item.name : ''}
              placement="right"
              arrow
            >
              <ListItemButton
                selected={active}
                onClick={() => {
                  navigate(item.route);
                  if (isMobile) setMobileOpen(false);
                }}
                sx={{
                  minHeight: 42,
                  borderRadius: '9px',
                  mb: 0.5,
                  justifyContent: collapsed && !isMobile ? 'center' : 'flex-start',
                  px: collapsed && !isMobile ? 1.5 : 1.75,
                  backgroundColor: active ? SIDEBAR_ACTIVE_BG : 'transparent',
                  borderLeft: active ? `3px solid ${SIDEBAR_ACTIVE_BORDER}` : '3px solid transparent',
                  color: active ? SIDEBAR_ACTIVE_TEXT : SIDEBAR_TEXT,
                  '&:hover': {
                    backgroundColor: active ? SIDEBAR_ACTIVE_BG : SIDEBAR_HOVER,
                    color: active ? SIDEBAR_ACTIVE_TEXT : '#FFFFFF',
                    '& .MuiListItemIcon-root': { color: active ? SIDEBAR_ACTIVE_ICON : 'rgba(255,255,255,0.75)' },
                  },
                  // Override MUI selected style
                  '&.Mui-selected': {
                    backgroundColor: SIDEBAR_ACTIVE_BG,
                    '&:hover': { backgroundColor: SIDEBAR_ACTIVE_BG },
                  },
                  transition: 'all 0.15s ease',
                  // Reset margin/width from theme override
                  margin: '2px 0',
                  width: '100%',
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: collapsed && !isMobile ? 'auto' : 36,
                    color: active ? SIDEBAR_ACTIVE_ICON : SIDEBAR_TEXT_MUTED,
                    transition: 'color 0.15s ease',
                  }}
                >
                  <Icon fontSize="small" />
                </ListItemIcon>
                {(!collapsed || isMobile) && (
                  <ListItemText
                    primary={item.name}
                    primaryTypographyProps={{
                      fontSize: '0.8375rem',
                      fontWeight: active ? 600 : 400,
                      color: active ? SIDEBAR_ACTIVE_TEXT : SIDEBAR_TEXT,
                    }}
                  />
                )}
              </ListItemButton>
            </Tooltip>
          );
        })}
      </List>

      {/* Sidebar Footer */}
      {(!collapsed || isMobile) && (
        <Box sx={{ p: 2, borderTop: `1px solid ${SIDEBAR_BORDER}` }}>
          <Typography variant="caption" sx={{ color: SIDEBAR_TEXT_MUTED, fontSize: '0.6875rem', letterSpacing: '0.03em' }}>
            © 2026 ExamShield · v{import.meta.env.VITE_APP_VERSION ?? '1.0.0'}
          </Typography>
        </Box>
      )}
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', backgroundColor: '#F8FAFC' }}>
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
              backgroundColor: SIDEBAR_BG,
              borderRight: `1px solid ${SIDEBAR_BORDER}`,
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
              backgroundColor: SIDEBAR_BG,
              border: 'none',
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
            backgroundColor: '#FFFFFF',
            color: '#0F172A',
            borderBottom: '1px solid #E2E8F0',
            zIndex: theme.zIndex.drawer - 1,
          }}
        >
          <Toolbar sx={{ gap: 2, minHeight: '64px !important' }}>
            {/* Hamburger — mobile */}
            {isMobile && (
              <IconButton edge="start" onClick={() => setMobileOpen(true)} size="small" sx={{ color: '#475569' }}>
                <MenuIcon fontSize="small" />
              </IconButton>
            )}

            {/* Collapse toggle — desktop */}
            {!isMobile && (
              <IconButton onClick={() => setCollapsed((c) => !c)} size="small" sx={{ color: '#475569', mr: 0.5 }}>
                {collapsed ? <MenuIcon fontSize="small" /> : <ChevronLeftIcon fontSize="small" />}
              </IconButton>
            )}

            {/* Breadcrumbs */}
            <Box sx={{ flexGrow: 1, display: { xs: 'none', sm: 'block' } }}>
              <Breadcrumbs separator={<NavigateNextIcon fontSize="small" sx={{ color: '#CBD5E1' }} />} aria-label="breadcrumb">
                <Link
                  underline="hover"
                  onClick={() => navigate('/examiner/dashboard')}
                  sx={{
                    cursor: 'pointer', display: 'flex', alignItems: 'center',
                    fontSize: '0.8125rem', color: '#64748B', fontWeight: 500,
                    '&:hover': { color: '#2563EB' },
                    textDecoration: 'none',
                  }}
                >
                  Workspace
                </Link>
                <Typography sx={{ fontSize: '0.8125rem', fontWeight: 600, color: '#0F172A' }}>
                  {pageTitle}
                </Typography>
              </Breadcrumbs>
            </Box>

            {/* Global Search */}
            <Paper
              component="form"
              sx={{
                p: '3px 8px',
                display: 'flex',
                alignItems: 'center',
                width: { xs: 140, sm: 240 },
                borderRadius: '9px',
                bgcolor: '#F1F5F9',
                boxShadow: 'none',
                border: '1px solid #E2E8F0',
                '&:focus-within': {
                  border: '1px solid #2563EB',
                  bgcolor: '#FFFFFF',
                  boxShadow: '0 0 0 3px rgba(37,99,235,0.1)',
                },
                transition: 'all 0.15s ease',
              }}
            >
              <IconButton sx={{ p: '4px', color: '#94A3B8' }} aria-label="search" disabled>
                <SearchIcon sx={{ fontSize: 16 }} />
              </IconButton>
              <InputBase
                sx={{ ml: 0.5, flex: 1, fontSize: '0.8125rem', color: '#475569' }}
                placeholder="Search workspace…"
                inputProps={{ 'aria-label': 'search workspace' }}
              />
            </Paper>

            {/* Notifications */}
            <IconButton size="small" onClick={handleOpenNotifMenu} sx={{ color: '#64748B' }}>
              <Badge badgeContent={0} color="error">
                <NotificationsIcon fontSize="small" />
              </Badge>
            </IconButton>
            <Popover
              open={Boolean(anchorElNotif)}
              anchorEl={anchorElNotif}
              onClose={handleCloseNotifMenu}
              anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
              transformOrigin={{ vertical: 'top', horizontal: 'right' }}
            >
              <Box sx={{ p: 2.5, minWidth: 280 }}>
                <Typography variant="subtitle2" fontWeight={700} sx={{ color: '#0F172A', mb: 1 }}>Notifications</Typography>
                <Divider sx={{ mb: 1.5 }} />
                <Box sx={{ py: 3, textAlign: 'center' }}>
                  <Typography variant="body2" sx={{ color: '#94A3B8' }}>No new notifications</Typography>
                </Box>
              </Box>
            </Popover>

            {/* Avatar & User Menu */}
            <Tooltip title="Account" arrow>
              <IconButton onClick={handleOpenUserMenu} sx={{ p: 0.5 }}>
                <Avatar
                  src={user?.profile_picture_url || ''}
                  sx={{
                    width: 32, height: 32,
                    background: 'linear-gradient(135deg, #2563EB, #0EA5E9)',
                    fontSize: '0.75rem', fontWeight: 700,
                    border: '2px solid #E2E8F0',
                  }}
                >
                  {user?.full_name?.substring(0, 2).toUpperCase() || 'EX'}
                </Avatar>
              </IconButton>
            </Tooltip>
            <Menu
              sx={{ mt: '8px' }}
              id="menu-appbar"
              anchorEl={anchorElUser}
              anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
              keepMounted
              transformOrigin={{ vertical: 'top', horizontal: 'right' }}
              open={Boolean(anchorElUser)}
              onClose={handleCloseUserMenu}
            >
              {/* User info header */}
              <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid #F1F5F9', mb: 0.5 }}>
                <Typography variant="body2" fontWeight={700} sx={{ color: '#0F172A' }}>
                  {user?.full_name || 'Examiner'}
                </Typography>
                <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                  {user?.email || ''}
                </Typography>
              </Box>
              <MenuItem onClick={() => { handleCloseUserMenu(); navigate('/examiner/profile'); }}>
                <PersonIcon fontSize="small" sx={{ mr: 1.5, color: '#64748B' }} />
                <Typography variant="body2">Profile</Typography>
              </MenuItem>
              <MenuItem onClick={() => { handleCloseUserMenu(); navigate('/examiner/settings'); }}>
                <SettingsIcon fontSize="small" sx={{ mr: 1.5, color: '#64748B' }} />
                <Typography variant="body2">Settings</Typography>
              </MenuItem>
              <Divider sx={{ my: 0.5 }} />
              <MenuItem onClick={handleLogout} sx={{ color: '#DC2626' }}>
                <LogoutIcon fontSize="small" sx={{ mr: 1.5, color: '#DC2626' }} />
                <Typography variant="body2" color="error.main" fontWeight={600}>Logout</Typography>
              </MenuItem>
            </Menu>
          </Toolbar>
        </AppBar>

        {/* Page Content */}
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: { xs: 2, md: 3 },
            overflow: 'auto',
            backgroundColor: '#F8FAFC',
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
};

export default ExaminerLayout;
