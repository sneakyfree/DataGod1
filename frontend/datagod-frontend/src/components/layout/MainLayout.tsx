'use client';

import { useState } from 'react';
import { Box, CssBaseline, ThemeProvider, createTheme, Toolbar, useMediaQuery } from '@mui/material';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

const drawerWidth = 240;

const theme = createTheme({
  palette: {
    primary: {
      main: '#2a96f2',
    },
    secondary: {
      main: '#ee6fa7',
    },
  },
  breakpoints: {
    values: {
      xs: 0,
      sm: 600,
      md: 900,
      lg: 1200,
      xl: 1536,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          // Minimum touch target size for mobile (44px)
          minHeight: 44,
          '@media (max-width: 600px)': {
            padding: '8px 16px',
          },
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          // Minimum touch target size for mobile (44px)
          minWidth: 44,
          minHeight: 44,
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          // Minimum touch target size for mobile
          minHeight: 48,
        },
      },
    },
  },
});

export const MainLayout = ({ children }: { children: React.ReactNode }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ display: 'flex', minHeight: '100vh' }}>
        <CssBaseline />
        <Header onMenuClick={handleDrawerToggle} />
        <Sidebar mobileOpen={mobileOpen} onDrawerToggle={handleDrawerToggle} />
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: { xs: 2, sm: 3 },
            width: { xs: '100%', sm: `calc(100% - ${drawerWidth}px)` },
            ml: { xs: 0, sm: `${drawerWidth}px` },
            mt: { xs: 7, sm: 8 },
            overflow: 'auto',
          }}
        >
          <Toolbar sx={{ display: { sm: 'none' } }} />
          {children}
        </Box>
      </Box>
    </ThemeProvider>
  );
};
