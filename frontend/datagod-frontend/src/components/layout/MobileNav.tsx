'use client';

import React, { useState } from 'react';
import {
    Drawer,
    Box,
    List,
    ListItem,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    IconButton,
    Typography,
    Divider,
    Avatar,
    useTheme,
    alpha,
} from '@mui/material';
import {
    Close as CloseIcon,
    Dashboard as DashboardIcon,
    Search as SearchIcon,
    Description as RecordsIcon,
    Favorite as FavoriteIcon,
    Bookmark as SavedIcon,
    AccountTree as NetworkIcon,
    Map as MapIcon,
    Settings as SettingsIcon,
    ExitToApp as LogoutIcon,
    Person as PersonIcon,
    AdminPanelSettings as AdminIcon,
    DarkMode as DarkModeIcon,
    LightMode as LightModeIcon,
} from '@mui/icons-material';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '../../context/AuthContext';
import { useThemeMode } from '../../context/ThemeContext';

// =============================================================================
// TYPES
// =============================================================================

interface NavItem {
    label: string;
    path: string;
    icon: React.ReactNode;
    requiresAuth?: boolean;
    adminOnly?: boolean;
}

interface MobileNavProps {
    open: boolean;
    onClose: () => void;
}

// =============================================================================
// NAV ITEMS
// =============================================================================

const navItems: NavItem[] = [
    { label: 'Dashboard', path: '/dashboard', icon: <DashboardIcon />, requiresAuth: true },
    { label: 'Search', path: '/search', icon: <SearchIcon /> },
    { label: 'Records', path: '/records', icon: <RecordsIcon /> },
    { label: 'Jurisdictions', path: '/jurisdictions', icon: <MapIcon /> },
    { label: 'Network', path: '/network', icon: <NetworkIcon />, requiresAuth: true },
    { label: 'Favorites', path: '/favorites', icon: <FavoriteIcon />, requiresAuth: true },
    { label: 'Saved Searches', path: '/saved', icon: <SavedIcon />, requiresAuth: true },
];

const adminItems: NavItem[] = [
    { label: 'Admin Panel', path: '/admin', icon: <AdminIcon />, adminOnly: true },
    { label: 'Coverage', path: '/admin/coverage', icon: <MapIcon />, adminOnly: true },
];

// =============================================================================
// COMPONENT
// =============================================================================

export default function MobileNav({ open, onClose }: MobileNavProps) {
    const theme = useTheme();
    const router = useRouter();
    const pathname = usePathname();
    const { user, isAuthenticated, logout } = useAuth();
    const { mode, toggleTheme } = useThemeMode();

    const handleNavigate = (path: string) => {
        router.push(path);
        onClose();
    };

    const handleLogout = () => {
        logout();
        onClose();
        router.push('/login');
    };

    const isActive = (path: string) => pathname === path;

    // Filter nav items based on auth state
    const visibleNavItems = navItems.filter(item => {
        if (item.requiresAuth && !isAuthenticated) return false;
        return true;
    });

    const visibleAdminItems = isAuthenticated && user?.roles?.includes('admin')
        ? adminItems
        : [];

    return (
        <Drawer
            anchor="left"
            open={open}
            onClose={onClose}
            PaperProps={{
                sx: {
                    width: 280,
                    background: theme.palette.mode === 'dark'
                        ? 'linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)'
                        : 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
                },
            }}
        >
            {/* Header */}
            <Box
                sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    p: 2,
                    borderBottom: `1px solid ${theme.palette.divider}`,
                }}
            >
                <Typography
                    variant="h6"
                    sx={{
                        fontWeight: 700,
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        backgroundClip: 'text',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                    }}
                >
                    DataGod
                </Typography>
                <IconButton onClick={onClose} size="small">
                    <CloseIcon />
                </IconButton>
            </Box>

            {/* User Info */}
            {isAuthenticated && user && (
                <Box
                    sx={{
                        p: 2,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 2,
                        backgroundColor: alpha(theme.palette.primary.main, 0.05),
                    }}
                >
                    <Avatar
                        sx={{
                            bgcolor: theme.palette.primary.main,
                            width: 40,
                            height: 40,
                        }}
                    >
                        {user.full_name?.[0] || user.email?.[0] || 'U'}
                    </Avatar>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="subtitle2" noWrap fontWeight={600}>
                            {user.full_name || 'User'}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" noWrap>
                            {user.email}
                        </Typography>
                    </Box>
                </Box>
            )}

            <Divider />

            {/* Navigation */}
            <Box sx={{ flex: 1, overflowY: 'auto', py: 1 }}>
                <List disablePadding>
                    {visibleNavItems.map((item) => (
                        <ListItem key={item.path} disablePadding>
                            <ListItemButton
                                onClick={() => handleNavigate(item.path)}
                                selected={isActive(item.path)}
                                sx={{
                                    mx: 1,
                                    borderRadius: 2,
                                    mb: 0.5,
                                    '&.Mui-selected': {
                                        backgroundColor: alpha(theme.palette.primary.main, 0.1),
                                        '&:hover': {
                                            backgroundColor: alpha(theme.palette.primary.main, 0.15),
                                        },
                                    },
                                }}
                            >
                                <ListItemIcon
                                    sx={{
                                        minWidth: 40,
                                        color: isActive(item.path)
                                            ? theme.palette.primary.main
                                            : 'inherit',
                                    }}
                                >
                                    {item.icon}
                                </ListItemIcon>
                                <ListItemText
                                    primary={item.label}
                                    primaryTypographyProps={{
                                        fontWeight: isActive(item.path) ? 600 : 400,
                                    }}
                                />
                            </ListItemButton>
                        </ListItem>
                    ))}
                </List>

                {/* Admin Section */}
                {visibleAdminItems.length > 0 && (
                    <>
                        <Divider sx={{ my: 1 }} />
                        <Typography
                            variant="overline"
                            color="text.secondary"
                            sx={{ px: 3, py: 1, display: 'block' }}
                        >
                            Admin
                        </Typography>
                        <List disablePadding>
                            {visibleAdminItems.map((item) => (
                                <ListItem key={item.path} disablePadding>
                                    <ListItemButton
                                        onClick={() => handleNavigate(item.path)}
                                        selected={isActive(item.path)}
                                        sx={{
                                            mx: 1,
                                            borderRadius: 2,
                                            mb: 0.5,
                                        }}
                                    >
                                        <ListItemIcon sx={{ minWidth: 40 }}>
                                            {item.icon}
                                        </ListItemIcon>
                                        <ListItemText primary={item.label} />
                                    </ListItemButton>
                                </ListItem>
                            ))}
                        </List>
                    </>
                )}
            </Box>

            <Divider />

            {/* Footer Actions */}
            <Box sx={{ p: 1 }}>
                {/* Theme Toggle */}
                <ListItemButton
                    onClick={toggleTheme}
                    sx={{ borderRadius: 2, mb: 0.5 }}
                >
                    <ListItemIcon sx={{ minWidth: 40 }}>
                        {mode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
                    </ListItemIcon>
                    <ListItemText primary={mode === 'dark' ? 'Light Mode' : 'Dark Mode'} />
                </ListItemButton>

                {/* Settings */}
                {isAuthenticated && (
                    <ListItemButton
                        onClick={() => handleNavigate('/settings')}
                        sx={{ borderRadius: 2, mb: 0.5 }}
                    >
                        <ListItemIcon sx={{ minWidth: 40 }}>
                            <SettingsIcon />
                        </ListItemIcon>
                        <ListItemText primary="Settings" />
                    </ListItemButton>
                )}

                {/* Login/Logout */}
                {isAuthenticated ? (
                    <ListItemButton
                        onClick={handleLogout}
                        sx={{
                            borderRadius: 2,
                            color: theme.palette.error.main,
                        }}
                    >
                        <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
                            <LogoutIcon />
                        </ListItemIcon>
                        <ListItemText primary="Logout" />
                    </ListItemButton>
                ) : (
                    <ListItemButton
                        onClick={() => handleNavigate('/login')}
                        sx={{ borderRadius: 2 }}
                    >
                        <ListItemIcon sx={{ minWidth: 40 }}>
                            <PersonIcon />
                        </ListItemIcon>
                        <ListItemText primary="Login" />
                    </ListItemButton>
                )}
            </Box>
        </Drawer>
    );
}
