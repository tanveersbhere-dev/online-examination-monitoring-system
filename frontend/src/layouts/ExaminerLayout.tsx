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
  Popover
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import SearchIcon from '@mui/icons-material/Search';
import NotificationsIcon from '@mui/icons-material/Notifications';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ShieldIcon from '@mui/icons-material/Shield';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';

import { resourceRegistry } from '../registry/resourceRegistry';
import { useAuth } from '../hooks/useAuth';

const DRAWER_WIDTH = 260;
const DRAWER_COLLAPSED = 72;

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

      {/* User Profile Summary */}
      {(!collapsed || isMobile) && (
        <Box sx={{ px: 2, py: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Avatar 
              src={user?.profile_picture_url || ''} 
              sx={{ width: 36, height: 36, bgcolor: 'primary.main', fontSize: '0.875rem' }}
            >
              {user?.full_name?.substring(0, 2).toUpperCase() || 'EX'}
            </Avatar>
            <Box sx={{ overflow: 'hidden' }}>
              <Typography variant="body2" fontWeight={600} noWrap>
                {user?.full_name || 'Examiner'}
              </Typography>
              <Typography variant="caption" color="text.secondary" noWrap>
                {user?.email || 'admin@examshield.com'}
              </Typography>
            </Box>
          </Box>
        </Box>
      )}

      <Divider sx={{ mb: 1 }} />

      {/* Dynamic Navigation Items */}
      <List sx={{ flexGrow: 1, px: 0 }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Tooltip
              key={item.route}
              title={collapsed && !isMobile ? item.name : ''}
              placement="right"
            >
              <ListItemButton
                selected={isActive(item.route)}
                onClick={() => {
                  navigate(item.route);
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
                    color: isActive(item.route) ? 'primary.main' : 'text.secondary',
                  }}
                >
                  <Icon />
                </ListItemIcon>
                {(!collapsed || isMobile) && (
                  <ListItemText
                    primary={item.name}
                    primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: isActive(item.route) ? 600 : 400 }}
                  />
                )}
              </ListItemButton>
            </Tooltip>
          );
        })}
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
          <Toolbar sx={{ gap: 2 }}>
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

            {/* Breadcrumbs */}
            <Box sx={{ flexGrow: 1, display: { xs: 'none', sm: 'block' } }}>
              <Breadcrumbs separator={<NavigateNextIcon fontSize="small" />} aria-label="breadcrumb">
                <Link underline="hover" color="inherit" onClick={() => navigate('/examiner/dashboard')} sx={{ cursor: 'pointer', display: 'flex', alignItems: 'center', fontSize: '0.875rem' }}>
                  Workspace
                </Link>
                <Typography color="text.primary" sx={{ fontSize: '0.875rem', fontWeight: 600 }}>
                  {pageTitle}
                </Typography>
              </Breadcrumbs>
            </Box>

            {/* Global Search Foundation */}
            <Paper
              component="form"
              sx={{ p: '2px 4px', display: 'flex', alignItems: 'center', width: { xs: 150, sm: 250 }, borderRadius: 2, bgcolor: 'action.hover', boxShadow: 'none' }}
            >
              <IconButton sx={{ p: '5px' }} aria-label="search" disabled>
                <SearchIcon fontSize="small" />
              </IconButton>
              <InputBase
                sx={{ ml: 1, flex: 1, fontSize: '0.875rem' }}
                placeholder="Search everywhere..."
                inputProps={{ 'aria-label': 'search workspace' }}
              />
            </Paper>

            {/* Notifications */}
            <IconButton size="small" onClick={handleOpenNotifMenu}>
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
              <Box sx={{ p: 2, minWidth: 250 }}>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>Notifications</Typography>
                <Divider sx={{ mb: 1 }} />
                <Typography variant="body2" color="text.secondary" textAlign="center" py={2}>
                  No new notifications
                </Typography>
              </Box>
            </Popover>

            {/* Avatar & User Menu */}
            <IconButton onClick={handleOpenUserMenu} sx={{ p: 0 }}>
              <Avatar 
                src={user?.profile_picture_url || ''}
                sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: '0.8rem' }}
              >
                {user?.full_name?.substring(0, 2).toUpperCase() || 'EX'}
              </Avatar>
            </IconButton>
            <Menu
              sx={{ mt: '45px' }}
              id="menu-appbar"
              anchorEl={anchorElUser}
              anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
              keepMounted
              transformOrigin={{ vertical: 'top', horizontal: 'right' }}
              open={Boolean(anchorElUser)}
              onClose={handleCloseUserMenu}
            >
              <MenuItem onClick={() => { handleCloseUserMenu(); navigate('/examiner/profile'); }}>
                <Typography textAlign="center">Profile</Typography>
              </MenuItem>
              <MenuItem onClick={() => { handleCloseUserMenu(); navigate('/examiner/settings'); }}>
                <Typography textAlign="center">Settings</Typography>
              </MenuItem>
              <Divider />
              <MenuItem onClick={handleLogout}>
                <Typography textAlign="center" color="error.main">Logout</Typography>
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
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
};

export default ExaminerLayout;
