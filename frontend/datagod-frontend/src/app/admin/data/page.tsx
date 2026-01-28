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
    Storage as DataIcon,
    Assessment as QualityIcon,
    VerifiedUser as ComplianceIcon,
    Settings as SettingsIcon,
    Home as HomeIcon,
} from '@mui/icons-material';
import { Header } from '../../../components/layout/Header';
import DataQualityDashboard from '../../../components/data/DataQualityDashboard';
import ComplianceMonitor from '../../../components/data/ComplianceMonitor';

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
            id={`data-tabpanel-${index}`}
            aria-labelledby={`data-tab-${index}`}
            sx={{ py: 3 }}
        >
            {value === index && children}
        </Box>
    );
}

// =============================================================================
// SETTINGS PANEL
// =============================================================================

function DataSettingsPanel() {
    return (
        <Box>
            <Typography variant="h5" fontWeight={700} gutterBottom>
                Data Management Settings
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Configure data quality rules and compliance automation
            </Typography>

            <Paper sx={{ p: 3 }}>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Coming Soon
                </Typography>
                <Typography variant="body2" color="text.secondary">
                    Data management settings including:
                </Typography>
                <Box component="ul" sx={{ mt: 2, pl: 2 }}>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Quality score thresholds
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Automated data validation rules
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Source refresh schedules
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Compliance check automation
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Notification preferences
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Data retention policies
                    </Typography>
                </Box>
            </Paper>
        </Box>
    );
}

// =============================================================================
// MAIN PAGE
// =============================================================================

export default function DataAdminPage() {
    const theme = useTheme();
    const [currentTab, setCurrentTab] = useState(0);

    const tabs = [
        { label: 'Data Quality', icon: <QualityIcon /> },
        { label: 'Compliance', icon: <ComplianceIcon /> },
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
                            <DataIcon fontSize="small" />
                            Data
                        </Typography>
                    </Breadcrumbs>

                    {/* Page Header */}
                    <Box sx={{ mb: 4 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                            <Box
                                sx={{
                                    p: 1.5,
                                    borderRadius: 2,
                                    background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
                                <DataIcon sx={{ color: 'white', fontSize: 28 }} />
                            </Box>
                            <Box>
                                <Typography variant="h4" fontWeight={700}>
                                    Data Management Center
                                </Typography>
                                <Typography variant="body1" color="text.secondary">
                                    Monitor data quality, track compliance, and manage data sources
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
                                <DataQualityDashboard />
                            </TabPanel>
                            <TabPanel value={currentTab} index={1}>
                                <ComplianceMonitor />
                            </TabPanel>
                            <TabPanel value={currentTab} index={2}>
                                <DataSettingsPanel />
                            </TabPanel>
                        </Box>
                    </Paper>
                </Container>
            </Box>
        </>
    );
}
