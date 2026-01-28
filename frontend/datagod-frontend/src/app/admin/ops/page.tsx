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
    Dashboard as OpsIcon,
    Analytics as AnalyticsIcon,
    Monitor as HealthIcon,
    Settings as SettingsIcon,
    Home as HomeIcon,
} from '@mui/icons-material';
import { Header } from '../../../components/layout/Header';
import AnalyticsDashboard from '../../../components/analytics/AnalyticsDashboard';
import SystemHealthMonitor from '../../../components/system/SystemHealthMonitor';

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
            id={`ops-tabpanel-${index}`}
            aria-labelledby={`ops-tab-${index}`}
            sx={{ py: 3 }}
        >
            {value === index && children}
        </Box>
    );
}

// =============================================================================
// SETTINGS PANEL
// =============================================================================

function OpsSettingsPanel() {
    return (
        <Box>
            <Typography variant="h5" fontWeight={700} gutterBottom>
                Operations Settings
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Configure alerts, monitoring thresholds, and notifications
            </Typography>

            <Paper sx={{ p: 3 }}>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Coming Soon
                </Typography>
                <Typography variant="body2" color="text.secondary">
                    Operations settings including:
                </Typography>
                <Box component="ul" sx={{ mt: 2, pl: 2 }}>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Alert threshold configuration
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        PagerDuty / Slack integrations
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Uptime monitoring targets
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Auto-scaling policies
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Incident response runbooks
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Maintenance window scheduling
                    </Typography>
                </Box>
            </Paper>
        </Box>
    );
}

// =============================================================================
// MAIN PAGE
// =============================================================================

export default function OpsAdminPage() {
    const theme = useTheme();
    const [currentTab, setCurrentTab] = useState(0);

    const tabs = [
        { label: 'Analytics', icon: <AnalyticsIcon /> },
        { label: 'System Health', icon: <HealthIcon /> },
        { label: 'Settings', icon: <SettingsIcon /> },
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
                            <OpsIcon fontSize="small" />
                            Operations
                        </Typography>
                    </Breadcrumbs>

                    {/* Page Header */}
                    <Box sx={{ mb: 4 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                            <Box
                                sx={{
                                    p: 1.5,
                                    borderRadius: 2,
                                    background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
                                <OpsIcon sx={{ color: 'white', fontSize: 28 }} />
                            </Box>
                            <Box>
                                <Typography variant="h4" fontWeight={700}>
                                    Operations Center
                                </Typography>
                                <Typography variant="body1" color="text.secondary">
                                    Platform analytics, system health, and infrastructure monitoring
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
                                <AnalyticsDashboard />
                            </TabPanel>
                            <TabPanel value={currentTab} index={1}>
                                <SystemHealthMonitor />
                            </TabPanel>
                            <TabPanel value={currentTab} index={2}>
                                <OpsSettingsPanel />
                            </TabPanel>
                        </Box>
                    </Paper>
                </Container>
            </Box>
        </>
    );
}
