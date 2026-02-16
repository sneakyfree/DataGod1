'use client';

import { useState } from 'react';
import {
    Box,
    Typography,
    Container,
    Paper,
    Grid,
    Card,
    CardContent,
    CircularProgress,
    Alert,
    Chip,
    Tabs,
    Tab,
    LinearProgress,
    IconButton,
    Tooltip,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
} from '@mui/material';
import {
    Analytics as AnalyticsIcon,
    Speed,
    Storage,
    TrendingUp,
    Refresh,
    People,
    Description,
    Public,
    Timeline,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';
import { ProtectedRoute } from '../../context/AuthContext';
import { featureFlag } from '../../config/featureFlags';

interface TabPanelProps {
    children?: React.ReactNode;
    value: number;
    index: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
    return value === index ? <Box sx={{ pt: 3 }}>{children}</Box> : null;
}

function AnalyticsContent() {
    const [tab, setTab] = useState(0);

    const { data: platformStats, isLoading, error, refetch } = useQuery({
        queryKey: ['analytics-platform-stats'],
        queryFn: () => apiService.get('/analytics/platform-stats').then((res: any) => res.data),
        staleTime: 60 * 1000,
    });

    const { data: topJurisdictions } = useQuery({
        queryKey: ['analytics-top-jurisdictions'],
        queryFn: () => apiService.get('/analytics/top-jurisdictions').then((res: any) => res.data),
        staleTime: 5 * 60 * 1000,
    });

    const { data: recentActivity } = useQuery({
        queryKey: ['analytics-recent-activity'],
        queryFn: () => apiService.get('/analytics/recent-activity').then((res: any) => res.data),
        staleTime: 30 * 1000,
    });

    const stats = platformStats || {};
    const jurisdictions = topJurisdictions?.jurisdictions || topJurisdictions || [];
    const activity = recentActivity?.activities || recentActivity || [];

    return (
        <Container maxWidth="xl" sx={{ py: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
                <Box>
                    <Typography variant="h4" component="h1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <AnalyticsIcon color="primary" /> Analytics Dashboard
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                        Platform-wide analytics, data coverage, and usage metrics
                    </Typography>
                </Box>
                <Tooltip title="Refresh all data">
                    <IconButton onClick={() => refetch()}>
                        <Refresh />
                    </IconButton>
                </Tooltip>
            </Box>

            {error && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                    Some analytics data may be unavailable. Showing cached data where possible.
                </Alert>
            )}

            {/* Summary Stat Cards */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
                {[
                    { label: 'Total Records', value: stats.total_records ?? '—', icon: <Description />, color: '#1976d2' },
                    { label: 'Total Entities', value: stats.total_entities ?? '—', icon: <People />, color: '#9c27b0' },
                    { label: 'Jurisdictions', value: stats.total_jurisdictions ?? '—', icon: <Public />, color: '#2e7d32' },
                    { label: 'Data Sources', value: stats.total_data_sources ?? '—', icon: <Storage />, color: '#ed6c02' },
                    { label: 'Active Users', value: stats.active_users ?? '—', icon: <People />, color: '#d32f2f' },
                    { label: 'API Requests (24h)', value: stats.api_requests_24h ?? '—', icon: <Speed />, color: '#0288d1' },
                ].map((stat) => (
                    <Grid item xs={6} sm={4} md={2} key={stat.label}>
                        <Card elevation={1}>
                            <CardContent sx={{ textAlign: 'center', py: 2 }}>
                                <Box sx={{ color: stat.color, mb: 1 }}>{stat.icon}</Box>
                                <Typography variant="h5" fontWeight={600}>
                                    {isLoading ? <CircularProgress size={20} /> : typeof stat.value === 'number' ? stat.value.toLocaleString() : stat.value}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">{stat.label}</Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            {/* Tabbed Content */}
            <Paper>
                <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
                    <Tab label="Data Coverage" />
                    <Tab label="Usage Trends" />
                    <Tab label="Recent Activity" />
                </Tabs>

                <TabPanel value={tab} index={0}>
                    <Box sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Top Jurisdictions by Record Count</Typography>
                        <TableContainer>
                            <Table size="small">
                                <TableHead>
                                    <TableRow>
                                        <TableCell>Jurisdiction</TableCell>
                                        <TableCell>State</TableCell>
                                        <TableCell>Records</TableCell>
                                        <TableCell>Coverage</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {jurisdictions.length > 0 ? (
                                        jurisdictions.slice(0, 20).map((j: any, idx: number) => (
                                            <TableRow key={j.id || idx} hover>
                                                <TableCell>{j.name || j.jurisdiction_name}</TableCell>
                                                <TableCell><Chip label={j.state || '—'} size="small" variant="outlined" /></TableCell>
                                                <TableCell>{(j.record_count || 0).toLocaleString()}</TableCell>
                                                <TableCell>
                                                    <LinearProgress
                                                        variant="determinate"
                                                        value={Math.min((j.record_count || 0) / 100, 100)}
                                                        sx={{ width: 80, height: 6, borderRadius: 3 }}
                                                    />
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    ) : (
                                        <TableRow>
                                            <TableCell colSpan={4} align="center" sx={{ py: 3 }}>
                                                <Typography color="text.secondary">No jurisdiction data available</Typography>
                                            </TableCell>
                                        </TableRow>
                                    )}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    </Box>
                </TabPanel>

                <TabPanel value={tab} index={1}>
                    <Box sx={{ p: 2, textAlign: 'center' }}>
                        <Timeline sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
                        <Typography color="text.secondary">
                            Usage trend charts will be displayed here when sufficient data is available.
                        </Typography>
                        <Typography variant="caption" color="text.disabled">
                            Tracks searches per day, records accessed, exports, and API usage over time
                        </Typography>
                    </Box>
                </TabPanel>

                <TabPanel value={tab} index={2}>
                    <Box sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Recent Platform Activity</Typography>
                        {activity.length > 0 ? (
                            <TableContainer>
                                <Table size="small">
                                    <TableHead>
                                        <TableRow>
                                            <TableCell>Time</TableCell>
                                            <TableCell>Action</TableCell>
                                            <TableCell>User</TableCell>
                                            <TableCell>Details</TableCell>
                                        </TableRow>
                                    </TableHead>
                                    <TableBody>
                                        {activity.slice(0, 30).map((a: any, idx: number) => (
                                            <TableRow key={a.id || idx} hover>
                                                <TableCell>
                                                    <Typography variant="caption">
                                                        {a.timestamp ? new Date(a.timestamp).toLocaleString() : '—'}
                                                    </Typography>
                                                </TableCell>
                                                <TableCell><Chip label={a.action || a.activity_type} size="small" /></TableCell>
                                                <TableCell>{a.username || a.user_id || '—'}</TableCell>
                                                <TableCell>
                                                    <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                                                        {a.details || a.description || '—'}
                                                    </Typography>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </TableContainer>
                        ) : (
                            <Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
                                No recent activity data available
                            </Typography>
                        )}
                    </Box>
                </TabPanel>
            </Paper>
        </Container>
    );
}

export default function AnalyticsPage() {
    if (!featureFlag('analytics')) {
        return (
            <Container maxWidth="md" sx={{ py: 8, textAlign: 'center' }}>
                <Typography variant="h5" color="text.secondary">
                    Analytics Dashboard is coming soon
                </Typography>
            </Container>
        );
    }

    return (
        <ProtectedRoute>
            <AnalyticsContent />
        </ProtectedRoute>
    );
}
