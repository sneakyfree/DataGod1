'use client';

import { useState } from 'react';
import { AppBar, Toolbar, Typography, IconButton, Box, Button, Menu, MenuItem, useMediaQuery, useTheme } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import { useRouter } from 'next/navigation';
import ThemeToggle from '../common/ThemeToggle';
import MobileNav from './MobileNav';
import { useAuth } from '../../context/AuthContext';

interface HeaderProps {
  onMenuClick?: () => void;
}

export const Header = ({ onMenuClick }: HeaderProps) => {
  const router = useRouter();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { user, isAuthenticated, logout } = useAuth();

  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleMobileNavToggle = () => {
    if (onMenuClick) {
      onMenuClick();
    } else {
      setMobileNavOpen(!mobileNavOpen);
    }
  };

  const handleLogout = () => {
    logout();
    router.push('/login');
    handleMenuClose();
  };

  return (
    <>
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          backdropFilter: 'blur(8px)',
          backgroundColor: theme.palette.mode === 'dark'
            ? 'rgba(26, 26, 46, 0.95)'
            : 'rgba(255, 255, 255, 0.95)',
          borderBottom: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Toolbar sx={{ minHeight: { xs: 56, sm: 64 } }}>
          {/* Mobile menu button */}
          <IconButton
            edge="start"
            color="inherit"
            aria-label="open drawer"
            onClick={handleMobileNavToggle}
            sx={{
              mr: 2,
              display: { md: 'none' },
              color: theme.palette.text.primary,
            }}
          >
            <MenuIcon />
          </IconButton>

          {/* Logo */}
          <Typography
            variant="h6"
            component="div"
            onClick={() => router.push('/')}
            sx={{
              fontWeight: 700,
              fontSize: { xs: '1.1rem', sm: '1.25rem' },
              cursor: 'pointer',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              '&:hover': {
                opacity: 0.8,
              },
            }}
          >
            DataGod
          </Typography>

          <Box sx={{ flexGrow: 1 }} />

          {/* Navigation buttons - desktop only */}
          <Box sx={{
            display: { xs: 'none', md: 'flex' },
            gap: 0.5,
            mr: 2
          }}>
            <Button
              color="inherit"
              onClick={() => router.push('/dashboard')}
              sx={{
                color: theme.palette.text.primary,
                '&:hover': { backgroundColor: theme.palette.action.hover }
              }}
            >
              Dashboard
            </Button>
            <Button
              color="inherit"
              onClick={() => router.push('/search')}
              sx={{
                color: theme.palette.text.primary,
                '&:hover': { backgroundColor: theme.palette.action.hover }
              }}
            >
              Search
            </Button>
            <Button
              color="inherit"
              onClick={() => router.push('/records')}
              sx={{
                color: theme.palette.text.primary,
                '&:hover': { backgroundColor: theme.palette.action.hover }
              }}
            >
              Records
            </Button>
            <Button
              color="inherit"
              onClick={() => router.push('/jurisdictions')}
              sx={{
                color: theme.palette.text.primary,
                '&:hover': { backgroundColor: theme.palette.action.hover }
              }}
            >
              Jurisdictions
            </Button>
          </Box>

          {/* Theme toggle button */}
          <ThemeToggle size="medium" />

          {/* User menu */}
          <IconButton
            color="inherit"
            aria-label="user menu"
            onClick={handleMenuOpen}
            sx={{
              ml: 1,
              color: theme.palette.text.primary,
            }}
          >
            <AccountCircleIcon />
          </IconButton>
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleMenuClose}
            anchorOrigin={{
              vertical: 'bottom',
              horizontal: 'right',
            }}
            transformOrigin={{
              vertical: 'top',
              horizontal: 'right',
            }}
            PaperProps={{
              sx: {
                mt: 1,
                minWidth: 180,
                boxShadow: theme.shadows[8],
              },
            }}
          >
            {isAuthenticated && user && (
              <Box sx={{ px: 2, py: 1, borderBottom: `1px solid ${theme.palette.divider}` }}>
                <Typography variant="subtitle2" fontWeight={600}>
                  {user.full_name || user.username}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {user.email}
                </Typography>
              </Box>
            )}
            {isAuthenticated ? (
              <>
                <MenuItem onClick={() => { router.push('/settings'); handleMenuClose(); }}>
                  Settings
                </MenuItem>
                <MenuItem onClick={handleLogout} sx={{ color: theme.palette.error.main }}>
                  Logout
                </MenuItem>
              </>
            ) : (
              <>
                <MenuItem onClick={() => { router.push('/login'); handleMenuClose(); }}>
                  Login
                </MenuItem>
                <MenuItem onClick={() => { router.push('/register'); handleMenuClose(); }}>
                  Register
                </MenuItem>
              </>
            )}
          </Menu>
        </Toolbar>
      </AppBar>

      {/* Mobile Navigation Drawer */}
      <MobileNav
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
      />
    </>
  );
};

export default Header;
