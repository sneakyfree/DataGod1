'use client';

import React, { useState } from 'react';
import {
    Box,
    Container,
    Typography,
    Tabs,
    Tab,
    Grid,
    Paper,
    useTheme,
    alpha,
    Breadcrumbs,
    Link,
    Chip,
} from '@mui/material';
import {
    SmartToy as AgentIcon,
    Assignment as ApprovalIcon,
    Analytics as AnalyticsIcon,
    Settings as SettingsIcon,
    Speed as SpeedIcon,
    Home as HomeIcon,
} from '@mui/icons-material';
import { Header } from '../../../components/layout/Header';
import AgentStatusDashboard from '../../../components/agent/AgentStatusDashboard';
import HITLApprovalQueue from '../../../components/agent/HITLApprovalQueue';
import ConfidenceScore from '../../../components/agent/ConfidenceScore';

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
            id={`agent-tabpanel-${index}`}
            aria-labelledby={`agent-tab-${index}`}
            sx={{ py: 3 }}
        >
            {value === index && children}
        </Box>
    );
}

// =============================================================================
// ANALYTICS PANEL
// =============================================================================

function AgentAnalyticsPanel() {
    const theme = useTheme();

    // Mock analytics data
    const analyticsData = {
        totalDecisions: 15847,
        avgConfidence: 0.89,
        approvalRate: 0.94,
        avgResponseTime: 2.3,
        activeWorkflows: 12,
        pendingApprovals: 7,
    };

    const confidenceBreakdown = [
        { factor: 'Data Quality', score: 0.92, weight: 1.5, description: 'Source data completeness and accuracy' },
        { factor: 'Entity Matching', score: 0.87, weight: 1.2, description: 'Confidence in entity resolution' },
        { factor: 'Historical Accuracy', score: 0.91, weight: 1.0, description: 'Past decision accuracy rate' },
        { factor: 'Cross-Validation', score: 0.85, weight: 0.8, description: 'Agreement across multiple sources' },
    ];

    return (
        <Box>
            <Typography variant="h5" fontWeight={700} gutterBottom>
                Agent Analytics
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Performance metrics and confidence analysis for the agent crew
            </Typography>

            {/* Quick Stats */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
                <Grid item xs={6} sm={4} md={2}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="h4" fontWeight={700} color="primary">
                            {analyticsData.totalDecisions.toLocaleString()}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Total Decisions
                        </Typography>
                    </Paper>
                </Grid>
                <Grid item xs={6} sm={4} md={2}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="h4" fontWeight={700} color="success.main">
                            {Math.round(analyticsData.approvalRate * 100)}%
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Approval Rate
                        </Typography>
                    </Paper>
                </Grid>
                <Grid item xs={6} sm={4} md={2}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="h4" fontWeight={700} color="info.main">
                            {analyticsData.avgResponseTime}s
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Avg Response
                        </Typography>
                    </Paper>
                </Grid>
                <Grid item xs={6} sm={4} md={2}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="h4" fontWeight={700} color="warning.main">
                            {analyticsData.activeWorkflows}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Active Workflows
                        </Typography>
                    </Paper>
                </Grid>
                <Grid item xs={6} sm={4} md={2}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="h4" fontWeight={700} color="error.main">
                            {analyticsData.pendingApprovals}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Pending Reviews
                        </Typography>
                    </Paper>
                </Grid>
                <Grid item xs={6} sm={4} md={2}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                            <ConfidenceScore
                                score={analyticsData.avgConfidence}
                                breakdown={confidenceBreakdown}
                                variant="circular"
                                size="medium"
                                showLabel={false}
                            />
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                            Avg Confidence
                        </Typography>
                    </Paper>
                </Grid>
            </Grid>

            {/* Confidence Breakdown */}
            <Paper sx={{ p: 3 }}>
                <Typography variant="h6" fontWeight={600} gutterBottom>
                    Confidence Score Breakdown
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Factors contributing to overall agent confidence
                </Typography>

                <Grid container spacing={3}>
                    {confidenceBreakdown.map((item) => (
                        <Grid item xs={12} sm={6} key={item.factor}>
                            <Box>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                    <Typography variant="subtitle2">{item.factor}</Typography>
                                    <Chip
                                        size="small"
                                        label={`Weight: ${item.weight}x`}
                                        variant="outlined"
                                    />
                                </Box>
                                <ConfidenceScore
                                    score={item.score}
                                    variant="linear"
                                    size="medium"
                                    showIcon={false}
                                />
                                <Typography variant="caption" color="text.secondary">
                                    {item.description}
                                </Typography>
                            </Box>
                        </Grid>
                    ))}
                </Grid>

                {/* Confidence Variants Demo */}
                <Box sx={{ mt: 4, pt: 3, borderTop: `1px solid ${theme.palette.divider}` }}>
                    <Typography variant="h6" fontWeight={600} gutterBottom>
                        Confidence Display Variants
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
                        <Box>
                            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                                Linear
                            </Typography>
                            <Box sx={{ width: 150 }}>
                                <ConfidenceScore score={0.89} variant="linear" size="small" />
                            </Box>
                        </Box>
                        <Box>
                            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                                Circular
                            </Typography>
                            <ConfidenceScore score={0.89} variant="circular" size="medium" />
                        </Box>
                        <Box>
                            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                                Chip
                            </Typography>
                            <ConfidenceScore score={0.89} variant="chip" />
                        </Box>
                        <Box>
                            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                                Badge
                            </Typography>
                            <ConfidenceScore score={0.89} variant="badge" />
                        </Box>
                    </Box>
                </Box>
            </Paper>
        </Box>
    );
}

// =============================================================================
// SETTINGS PANEL
// =============================================================================

function AgentSettingsPanel() {
    return (
        <Box>
            <Typography variant="h5" fontWeight={700} gutterBottom>
                Agent Settings
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Configure agent behavior and approval thresholds
            </Typography>

            <Paper sx={{ p: 3 }}>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Coming Soon
                </Typography>
                <Typography variant="body2" color="text.secondary">
                    Agent configuration settings including:
                </Typography>
                <Box component="ul" sx={{ mt: 2, pl: 2 }}>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Auto-approval confidence thresholds
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Agent priority weights
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Notification preferences
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Workflow automation rules
                    </Typography>
                    <Typography component="li" variant="body2" color="text.secondary">
                        Data source priorities
                    </Typography>
                </Box>
            </Paper>
        </Box>
    );
}

// =============================================================================
// MAIN PAGE
// =============================================================================

export default function AgentAdminPage() {
    const theme = useTheme();
    const [currentTab, setCurrentTab] = useState(0);

    const tabs = [
        { label: 'Agent Status', icon: <AgentIcon /> },
        { label: 'Approval Queue', icon: <ApprovalIcon /> },
        { label: 'Analytics', icon: <AnalyticsIcon /> },
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
                            <AgentIcon fontSize="small" />
                            Agents
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
                                <AgentIcon sx={{ color: 'white', fontSize: 28 }} />
                            </Box>
                            <Box>
                                <Typography variant="h4" fontWeight={700}>
                                    Agent Control Center
                                </Typography>
                                <Typography variant="body1" color="text.secondary">
                                    Monitor, manage, and configure the DataGod agentic system
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
                                <AgentStatusDashboard />
                            </TabPanel>
                            <TabPanel value={currentTab} index={1}>
                                <HITLApprovalQueue />
                            </TabPanel>
                            <TabPanel value={currentTab} index={2}>
                                <AgentAnalyticsPanel />
                            </TabPanel>
                            <TabPanel value={currentTab} index={3}>
                                <AgentSettingsPanel />
                            </TabPanel>
                        </Box>
                    </Paper>
                </Container>
            </Box>
        </>
    );
}
