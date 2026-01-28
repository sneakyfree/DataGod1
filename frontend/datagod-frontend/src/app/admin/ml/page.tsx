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
    Psychology as MLIcon,
    Assessment as PerformanceIcon,
    Speed as TrainingIcon,
    Settings as SettingsIcon,
    Home as HomeIcon,
} from '@mui/icons-material';
import { Header } from '../../../components/layout/Header';
import ModelPerformanceDashboard from '../../../components/ml/ModelPerformanceDashboard';
import TrainingStatusMonitor from '../../../components/ml/TrainingStatusMonitor';

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
            id={`ml-tabpanel-${index}`}
            aria-labelledby={`ml-tab-${index}`}
            sx={{ py: 3 }}
        >
            {value === index && children}
        </Box>
    );
}

// =============================================================================
// SETTINGS PANEL
// =============================================================================

function MLSettingsPanel() {
    return (
        <Box>
            <Typography variant="h5" fontWeight={700} gutterBottom>
                ML Pipeline Settings
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Configure machine learning pipeline and model deployment
            </Typography>

            <Paper sx={{ p: 3 }}>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Coming Soon
                </Typography>
                <Typography variant="body2" color="text.secondary">
                    ML configuration settings including:
                </Typography>
                <Box component="ul" sx={{ mt: 2, pl: 2 }}>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Auto-retraining schedules
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Model deployment policies
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Performance thresholds
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        GPU resource allocation
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        A/B testing configuration
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Model versioning rules
                    </Typography>
                </Box>
            </Paper>
        </Box>
    );
}

// =============================================================================
// MAIN PAGE
// =============================================================================

export default function MLAdminPage() {
    const theme = useTheme();
    const [currentTab, setCurrentTab] = useState(0);

    const tabs = [
        { label: 'Model Performance', icon: <PerformanceIcon /> },
        { label: 'Training Monitor', icon: <TrainingIcon /> },
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
                            <MLIcon fontSize="small" />
                            ML Pipeline
                        </Typography>
                    </Breadcrumbs>

                    {/* Page Header */}
                    <Box sx={{ mb: 4 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                            <Box
                                sx={{
                                    p: 1.5,
                                    borderRadius: 2,
                                    background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
                                <MLIcon sx={{ color: 'white', fontSize: 28 }} />
                            </Box>
                            <Box>
                                <Typography variant="h4" fontWeight={700}>
                                    ML Pipeline Control Center
                                </Typography>
                                <Typography variant="body1" color="text.secondary">
                                    Monitor model performance, training jobs, and resource usage
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
                                <ModelPerformanceDashboard />
                            </TabPanel>
                            <TabPanel value={currentTab} index={1}>
                                <TrainingStatusMonitor />
                            </TabPanel>
                            <TabPanel value={currentTab} index={2}>
                                <MLSettingsPanel />
                            </TabPanel>
                        </Box>
                    </Paper>
                </Container>
            </Box>
        </>
    );
}
