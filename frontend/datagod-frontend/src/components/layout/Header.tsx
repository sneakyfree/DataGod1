'use client';

import { AppBar, Toolbar, Typography, IconButton, Box, Button, Avatar, Menu, MenuItem } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

interface HeaderProps {
  onMenuClick: () => void;
}

export const Header = ({ onMenuClick }: HeaderProps) => {
  const router = useRouter();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    router.push('/login');
    handleMenuClose();
  };

  return (
    <AppBar
      position="fixed"
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
        width: { sm: `calc(100% - 240px)` },
        ml: { sm: `240px` },
      }}
    >
      <Toolbar>
        <IconButton
          edge="start"
          color="inherit"
          aria-label="open drawer"
          onClick={onMenuClick}
          sx={{
            mr: 2,
            display: { sm: 'none' }  // Only show on mobile
          }}
        >
          <MenuIcon />
        </IconButton>
        <Typography
          variant="h6"
          component="div"
          sx={{
            flexGrow: 1,
            fontSize: { xs: '1rem', sm: '1.25rem' }
          }}
        >
          DataGod
        </Typography>
        {/* Navigation buttons - hidden on mobile, visible on tablet+ */}
        <Box sx={{
          display: { xs: 'none', md: 'flex' },
          gap: 1,
          mr: 2
        }}>
          <Button color="inherit" onClick={() => router.push('/dashboard')}>
            Dashboard
          </Button>
          <Button color="inherit" onClick={() => router.push('/search')}>
            Search
          </Button>
          <Button color="inherit" onClick={() => router.push('/records')}>
            Records
          </Button>
        </Box>
        {/* User menu */}
        <IconButton
          color="inherit"
          aria-label="user menu"
          onClick={handleMenuOpen}
          sx={{ ml: 1 }}
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
        >
          <MenuItem onClick={() => { router.push('/settings'); handleMenuClose(); }}>
            Settings
          </MenuItem>
          <MenuItem onClick={handleLogout}>
            Logout
          </MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
};
