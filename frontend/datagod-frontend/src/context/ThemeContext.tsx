'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { createTheme, Theme, PaletteMode } from '@mui/material';

// =============================================================================
// TYPES
// =============================================================================

interface ThemeContextType {
    mode: PaletteMode;
    toggleTheme: () => void;
    setMode: (mode: PaletteMode) => void;
    theme: Theme;
}

interface ThemeProviderProps {
    children: ReactNode;
}

// =============================================================================
// THEME DEFINITIONS
// =============================================================================

const getDesignTokens = (mode: PaletteMode) => ({
    palette: {
        mode,
        ...(mode === 'light'
            ? {
                // Light mode palette
                primary: {
                    main: '#2a96f2',
                    light: '#5eb8ff',
                    dark: '#0069bf',
                    contrastText: '#ffffff',
                },
                secondary: {
                    main: '#ee6fa7',
                    light: '#ff9fd8',
                    dark: '#b93d79',
                    contrastText: '#ffffff',
                },
                background: {
                    default: '#f5f5f5',
                    paper: '#ffffff',
                },
                text: {
                    primary: '#1a1a1a',
                    secondary: '#666666',
                },
                divider: 'rgba(0, 0, 0, 0.12)',
            }
            : {
                // Dark mode palette
                primary: {
                    main: '#5eb8ff',
                    light: '#90d4ff',
                    dark: '#2a96f2',
                    contrastText: '#000000',
                },
                secondary: {
                    main: '#ff9fd8',
                    light: '#ffd1ec',
                    dark: '#ee6fa7',
                    contrastText: '#000000',
                },
                background: {
                    default: '#121212',
                    paper: '#1e1e1e',
                },
                text: {
                    primary: '#ffffff',
                    secondary: '#b0b0b0',
                },
                divider: 'rgba(255, 255, 255, 0.12)',
            }),
        success: {
            main: mode === 'light' ? '#4caf50' : '#81c784',
            light: mode === 'light' ? '#80e27e' : '#a5d6a7',
            dark: mode === 'light' ? '#087f23' : '#4caf50',
        },
        warning: {
            main: mode === 'light' ? '#ff9800' : '#ffb74d',
            light: mode === 'light' ? '#ffc947' : '#ffd180',
            dark: mode === 'light' ? '#c66900' : '#ff9800',
        },
        error: {
            main: mode === 'light' ? '#f44336' : '#ef5350',
            light: mode === 'light' ? '#ff7961' : '#ff8a80',
            dark: mode === 'light' ? '#ba000d' : '#f44336',
        },
        info: {
            main: mode === 'light' ? '#2196f3' : '#64b5f6',
            light: mode === 'light' ? '#6ec6ff' : '#90caf9',
            dark: mode === 'light' ? '#0069c0' : '#2196f3',
        },
    },
    typography: {
        fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
        h1: { fontSize: '2.5rem', fontWeight: 700 },
        h2: { fontSize: '2rem', fontWeight: 600 },
        h3: { fontSize: '1.75rem', fontWeight: 600 },
        h4: { fontSize: '1.5rem', fontWeight: 600 },
        h5: { fontSize: '1.25rem', fontWeight: 600 },
        h6: { fontSize: '1rem', fontWeight: 600 },
    },
    breakpoints: {
        values: { xs: 0, sm: 600, md: 900, lg: 1200, xl: 1536 },
    },
    components: {
        MuiButton: {
            styleOverrides: {
                root: {
                    textTransform: 'none' as const,
                    borderRadius: 8,
                    minHeight: 44,
                    fontWeight: 500,
                },
            },
        },
        MuiIconButton: {
            styleOverrides: {
                root: { minWidth: 44, minHeight: 44 },
            },
        },
        MuiListItemButton: {
            styleOverrides: {
                root: { minHeight: 48, borderRadius: 8 },
            },
        },
        MuiTextField: {
            styleOverrides: {
                root: {
                    '& .MuiOutlinedInput-root': { borderRadius: 8 },
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    borderRadius: 12,
                    boxShadow: mode === 'light'
                        ? '0 2px 8px rgba(0,0,0,0.08)'
                        : '0 2px 8px rgba(0,0,0,0.4)',
                },
            },
        },
        MuiPaper: {
            styleOverrides: {
                root: { borderRadius: 12 },
            },
        },
        MuiAppBar: {
            styleOverrides: {
                root: {
                    backgroundColor: mode === 'light' ? '#ffffff' : '#1e1e1e',
                    color: mode === 'light' ? '#1a1a1a' : '#ffffff',
                },
            },
        },
        MuiDrawer: {
            styleOverrides: {
                paper: {
                    backgroundColor: mode === 'light' ? '#ffffff' : '#1e1e1e',
                },
            },
        },
    },
});

// =============================================================================
// CONTEXT
// =============================================================================

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const THEME_STORAGE_KEY = 'datagod-theme-mode';

// =============================================================================
// PROVIDER
// =============================================================================

export function DataGodThemeProvider({ children }: ThemeProviderProps) {
    const [mode, setModeState] = useState<PaletteMode>('light');
    const [mounted, setMounted] = useState(false);

    // Load saved theme preference on mount
    useEffect(() => {
        setMounted(true);
        const savedMode = localStorage.getItem(THEME_STORAGE_KEY) as PaletteMode | null;
        if (savedMode && (savedMode === 'light' || savedMode === 'dark')) {
            setModeState(savedMode);
        } else {
            // Check system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            setModeState(prefersDark ? 'dark' : 'light');
        }
    }, []);

    // Listen for system theme changes
    useEffect(() => {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        const handleChange = (e: MediaQueryListEvent) => {
            const savedMode = localStorage.getItem(THEME_STORAGE_KEY);
            // Only auto-switch if user hasn't manually set preference
            if (!savedMode) {
                setModeState(e.matches ? 'dark' : 'light');
            }
        };
        mediaQuery.addEventListener('change', handleChange);
        return () => mediaQuery.removeEventListener('change', handleChange);
    }, []);

    const toggleTheme = () => {
        setModeState((prevMode) => {
            const newMode = prevMode === 'light' ? 'dark' : 'light';
            localStorage.setItem(THEME_STORAGE_KEY, newMode);
            return newMode;
        });
    };

    const setMode = (newMode: PaletteMode) => {
        setModeState(newMode);
        localStorage.setItem(THEME_STORAGE_KEY, newMode);
    };

    const theme = React.useMemo(
        () => createTheme(getDesignTokens(mode)),
        [mode]
    );

    // Prevent flash of wrong theme
    if (!mounted) {
        return null;
    }

    return (
        <ThemeContext.Provider value={{ mode, toggleTheme, setMode, theme }}>
            {children}
        </ThemeContext.Provider>
    );
}

// =============================================================================
// HOOK
// =============================================================================

export function useThemeMode() {
    const context = useContext(ThemeContext);
    if (context === undefined) {
        throw new Error('useThemeMode must be used within a DataGodThemeProvider');
    }
    return context;
}

export default ThemeContext;
