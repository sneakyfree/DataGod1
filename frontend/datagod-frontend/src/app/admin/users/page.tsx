'use client';

import React, { useState } from 'react';
import {
    Box,
    Container,
    Typography,
    Tabs,
    Tab,
    Paper,
    useTheme,
    alpha,
    Breadcrumbs,
    Link,
} from '@mui/material';
import {
    People as UsersIcon,
    History as AuditIcon,
    Security as SecurityIcon,
    Settings as SettingsIcon,
    Home as HomeIcon,
} from '@mui/icons-material';
import { Header } from '../../../components/layout/Header';
import UserManagementDashboard from '../../../components/admin/UserManagementDashboard';
import AuditLogViewer from '../../../components/admin/AuditLogViewer';

// =============================================================================
// TYPES
// =============================================================================

interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
}

// =============================================================================
// TAB PANEL
// =============================================================================

function TabPanel({ children, value, index }: TabPanelProps) {
    return (
        <Box
            role="tabpanel"
            hidden={value !== index}
            id={`users-tabpanel-${index}`}
            aria-labelledby={`users-tab-${index}`}
            sx={{ py: 3 }}
        >
            {value === index && children}
        </Box>
    );
}

// =============================================================================
// SECURITY SETTINGS PANEL
// =============================================================================

function SecuritySettingsPanel() {
    return (
        <Box>
            <Typography variant="h5" fontWeight={700} gutterBottom>
                Security Settings
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Configure authentication, access policies, and security controls
            </Typography>

            <Paper sx={{ p: 3 }}>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Coming Soon
                </Typography>
                <Typography variant="body2" color="text.secondary">
                    Security settings including:
                </Typography>
                <Box component="ul" sx={{ mt: 2, pl: 2 }}>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Password policy configuration
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        MFA enforcement settings
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Session timeout policies
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        IP allowlist management
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        SSO/SAML configuration
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        API key management
                    </Typography>
                </Box>
            </Paper>
        </Box>
    );
}

// =============================================================================
// MAIN PAGE
// =============================================================================

export default function UsersAdminPage() {
    const theme = useTheme();
    const [currentTab, setCurrentTab] = useState(0);

    const tabs = [
        { label: 'Users', icon: <UsersIcon /> },
        { label: 'Audit Log', icon: <AuditIcon /> },
        { label: 'Security', icon: <SecurityIcon /> },
    ];

    return (
        <>
            <Header />
            <Box
                component="main"
                sx={{
                    flexGrow: 1,
                    pt: { xs: 8, sm: 9 },
                    pb: 4,
                    minHeight: '100vh',
                    backgroundColor: theme.palette.mode === 'dark'
                        ? alpha(theme.palette.background.default, 0.95)
                        : theme.palette.grey[50],
                }}
            >
                <Container maxWidth="xl">
                    {/* Breadcrumbs */}
                    <Breadcrumbs sx={{ mb: 2 }}>
                        <Link
                            href="/dashboard"
                            underline="hover"
                            color="inherit"
                            sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
                        >
                            <HomeIcon fontSize="small" />
                            Dashboard
                        </Link>
                        <Link href="/admin" underline="hover" color="inherit">
                            Admin
                        </Link>
                        <Typography color="text.primary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <UsersIcon fontSize="small" />
                            Users
                        </Typography>
                    </Breadcrumbs>

                    {/* Page Header */}
                    <Box sx={{ mb: 4 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                            <Box
                                sx={{
                                    p: 1.5,
                                    borderRadius: 2,
                                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
                                <UsersIcon sx={{ color: 'white', fontSize: 28 }} />
                            </Box>
                            <Box>
                                <Typography variant="h4" fontWeight={700}>
                                    User & Access Management
                                </Typography>
                                <Typography variant="body1" color="text.secondary">
                                    Manage users, review audit logs, and configure security settings
                                </Typography>
                            </Box>
                        </Box>
                    </Box>

                    {/* Tabs */}
                    <Paper
                        elevation={0}
                        sx={{
                            borderRadius: 2,
                            border: `1px solid ${theme.palette.divider}`,
                            overflow: 'hidden',
                        }}
                    >
                        <Box
                            sx={{
                                borderBottom: 1,
                                borderColor: 'divider',
                                backgroundColor: alpha(theme.palette.background.paper, 0.8),
                            }}
                        >
                            <Tabs
                                value={currentTab}
                                onChange={(_, v) => setCurrentTab(v)}
                                variant="scrollable"
                                scrollButtons="auto"
                                sx={{
                                    '& .MuiTab-root': {
                                        minHeight: 64,
                                        textTransform: 'none',
                                        fontWeight: 500,
                                    },
                                }}
                            >
                                {tabs.map((tab, idx) => (
                                    <Tab
                                        key={idx}
                                        label={tab.label}
                                        icon={tab.icon}
                                        iconPosition="start"
                                    />
                                ))}
                            </Tabs>
                        </Box>

                        <Box sx={{ p: 3 }}>
                            <TabPanel value={currentTab} index={0}>
                                <UserManagementDashboard />
                            </TabPanel>
                            <TabPanel value={currentTab} index={1}>
                                <AuditLogViewer />
                            </TabPanel>
                            <TabPanel value={currentTab} index={2}>
                                <SecuritySettingsPanel />
                            </TabPanel>
                        </Box>
                    </Paper>
                </Container>
            </Box>
        </>
    );
}
