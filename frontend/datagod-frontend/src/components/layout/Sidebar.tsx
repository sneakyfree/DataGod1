'use client';

import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Box,
  Typography,
  Avatar,
  Chip,
} from '@mui/material';
import { useRouter, usePathname } from 'next/navigation';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SearchIcon from '@mui/icons-material/Search';
import DescriptionIcon from '@mui/icons-material/Description';
import SettingsIcon from '@mui/icons-material/Settings';
import LogoutIcon from '@mui/icons-material/Logout';
import LoginIcon from '@mui/icons-material/Login';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import MapIcon from '@mui/icons-material/Map';
import HubIcon from '@mui/icons-material/Hub';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import FavoriteIcon from '@mui/icons-material/Favorite';
import PaymentIcon from '@mui/icons-material/Payment';
import InfoIcon from '@mui/icons-material/Info';
import ContactMailIcon from '@mui/icons-material/ContactMail';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import AssessmentIcon from '@mui/icons-material/Assessment';
import { useAuth } from '../../context/AuthContext';

const drawerWidth = 260;

interface SidebarProps {
  mobileOpen: boolean;
  onDrawerToggle: () => void;
}

export const Sidebar = ({ mobileOpen, onDrawerToggle }: SidebarProps) => {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, logout } = useAuth();

  // Main navigation items (authenticated)
  const mainMenuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Search', icon: <SearchIcon />, path: '/search' },
    { text: 'Records', icon: <DescriptionIcon />, path: '/records' },
    { text: 'Entity Network', icon: <HubIcon />, path: '/network' },
    { text: 'Coverage Map', icon: <MapIcon />, path: '/jurisdictions' },
    { text: 'Saved Searches', icon: <BookmarkIcon />, path: '/saved' },
    { text: 'Favorites', icon: <FavoriteIcon />, path: '/favorites' },
  ];

  // Admin navigation items (for admin users)
  const adminMenuItems = [
    { text: 'Admin Dashboard', icon: <AdminPanelSettingsIcon />, path: '/admin' },
    { text: 'Coverage Admin', icon: <AssessmentIcon />, path: '/admin/coverage' },
  ];

  // Auth navigation items (not authenticated)
  const authMenuItems = [
    { text: 'Sign In', icon: <LoginIcon />, path: '/login' },
    { text: 'Sign Up', icon: <PersonAddIcon />, path: '/register' },
  ];

  // Secondary navigation items
  const secondaryMenuItems = [
    { text: 'Pricing', icon: <PaymentIcon />, path: '/pricing' },
    { text: 'About', icon: <InfoIcon />, path: '/about' },
    { text: 'Contact', icon: <ContactMailIcon />, path: '/contact' },
  ];

  // Settings menu item
  const settingsItem = { text: 'Settings', icon: <SettingsIcon />, path: '/settings' };

  const handleNavigation = (path: string) => {
    router.push(path);
    if (mobileOpen) {
      onDrawerToggle();
    }
  };

  const handleLogout = () => {
    logout();
    router.push('/login');
    if (mobileOpen) {
      onDrawerToggle();
    }
  };

  const isActive = (path: string) => pathname === path;

  const drawer = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Logo */}
      <Box sx={{ p: 2, textAlign: 'center', borderBottom: '1px solid', borderColor: 'divider' }}>
        <Typography
          variant="h5"
          component="div"
          sx={{
            fontWeight: 700,
            color: 'primary.main',
            cursor: 'pointer',
          }}
          onClick={() => handleNavigation('/')}
        >
          DataGod
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Public Records Database
        </Typography>
      </Box>

      {/* User Info (if authenticated) */}
      {isAuthenticated && user && (
        <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Avatar sx={{ width: 40, height: 40, bgcolor: 'primary.main' }}>
              {user.full_name?.charAt(0) || user.email?.charAt(0) || 'U'}
            </Avatar>
            <Box sx={{ overflow: 'hidden' }}>
              <Typography
                variant="subtitle2"
                sx={{
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {user.full_name || 'User'}
              </Typography>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: 'block',
                }}
              >
                {user.email}
              </Typography>
            </Box>
          </Box>
          {user.subscription_tier && (
            <Chip
              label={user.subscription_tier}
              size="small"
              color="primary"
              variant="outlined"
              sx={{ mt: 1, textTransform: 'capitalize' }}
            />
          )}
        </Box>
      )}

      {/* Main Navigation */}
      <Box sx={{ flex: 1, overflowY: 'auto' }}>
        {isAuthenticated ? (
          <>
            <List sx={{ py: 1 }}>
              {mainMenuItems.map((item) => (
                <ListItem key={item.text} disablePadding>
                  <ListItemButton
                    onClick={() => handleNavigation(item.path)}
                    selected={isActive(item.path)}
                    sx={{
                      mx: 1,
                      borderRadius: 1,
                      '&.Mui-selected': {
                        backgroundColor: 'primary.light',
                        '&:hover': {
                          backgroundColor: 'primary.light',
                        },
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
                    <ListItemText primary={item.text} />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
            <Divider sx={{ mx: 2 }} />
            <List sx={{ py: 1 }}>
              <ListItem disablePadding>
                <ListItemButton
                  onClick={() => handleNavigation(settingsItem.path)}
                  selected={isActive(settingsItem.path)}
                  sx={{
                    mx: 1,
                    borderRadius: 1,
                    '&.Mui-selected': {
                      backgroundColor: 'primary.light',
                      '&:hover': {
                        backgroundColor: 'primary.light',
                      },
                    },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 40 }}>{settingsItem.icon}</ListItemIcon>
                  <ListItemText primary={settingsItem.text} />
                </ListItemButton>
              </ListItem>
            </List>

            {/* Admin Section (for admin users) */}
            {user?.roles?.includes('admin') && (
              <>
                <Divider sx={{ mx: 2 }} />
                <Typography variant="overline" sx={{ px: 3, pt: 1, color: 'text.secondary' }}>
                  Admin
                </Typography>
                <List sx={{ py: 1 }}>
                  {adminMenuItems.map((item) => (
                    <ListItem key={item.text} disablePadding>
                      <ListItemButton
                        onClick={() => handleNavigation(item.path)}
                        selected={isActive(item.path)}
                        sx={{
                          mx: 1,
                          borderRadius: 1,
                          '&.Mui-selected': {
                            backgroundColor: 'warning.light',
                            '&:hover': {
                              backgroundColor: 'warning.light',
                            },
                          },
                        }}
                      >
                        <ListItemIcon sx={{ minWidth: 40, color: 'warning.main' }}>{item.icon}</ListItemIcon>
                        <ListItemText primary={item.text} />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              </>
            )}
          </>
        ) : (
          <List sx={{ py: 1 }}>
            {authMenuItems.map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton
                  onClick={() => handleNavigation(item.path)}
                  selected={isActive(item.path)}
                  sx={{
                    mx: 1,
                    borderRadius: 1,
                    '&.Mui-selected': {
                      backgroundColor: 'primary.light',
                      '&:hover': {
                        backgroundColor: 'primary.light',
                      },
                    },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        )}

        <Divider sx={{ mx: 2 }} />

        {/* Secondary Navigation */}
        <List sx={{ py: 1 }}>
          {secondaryMenuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                onClick={() => handleNavigation(item.path)}
                selected={isActive(item.path)}
                sx={{
                  mx: 1,
                  borderRadius: 1,
                  '&.Mui-selected': {
                    backgroundColor: 'primary.light',
                    '&:hover': {
                      backgroundColor: 'primary.light',
                    },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>

      {/* Logout Button (if authenticated) */}
      {isAuthenticated && (
        <Box sx={{ borderTop: '1px solid', borderColor: 'divider' }}>
          <List sx={{ py: 1 }}>
            <ListItem disablePadding>
              <ListItemButton
                onClick={handleLogout}
                sx={{
                  mx: 1,
                  borderRadius: 1,
                  color: 'error.main',
                  '&:hover': {
                    backgroundColor: 'error.light',
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
                  <LogoutIcon />
                </ListItemIcon>
                <ListItemText primary="Logout" />
              </ListItemButton>
            </ListItem>
          </List>
        </Box>
      )}
    </Box>
  );

  return (
    <Box
      component="nav"
      sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      aria-label="navigation menu"
    >
      {/* Mobile drawer */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onDrawerToggle}
        ModalProps={{
          keepMounted: true,
        }}
        sx={{
          display: { xs: 'block', sm: 'none' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: drawerWidth,
          },
        }}
      >
        {drawer}
      </Drawer>

      {/* Desktop drawer */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: 'none', sm: 'block' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: drawerWidth,
          },
        }}
        open
      >
        {drawer}
      </Drawer>
    </Box>
  );
};
