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
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    LinearProgress,
    IconButton,
    Tooltip,
    TextField,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
} from '@mui/material';
import {
    BugReport,
    TrendingUp,
    Warning,
    CheckCircle,
    Assessment,
    Refresh,
    Security,
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

function severityColor(severity: string) {
    switch (severity?.toLowerCase()) {
        case 'critical': return 'error';
        case 'high': return 'warning';
        case 'medium': return 'info';
        case 'low': return 'success';
        default: return 'default';
    }
}

function AnomaliesContent() {
    const [tab, setTab] = useState(0);
    const [severityFilter, setSeverityFilter] = useState<string>('');

    const { data: anomalies, isLoading, error, refetch } = useQuery({
        queryKey: ['anomalies', severityFilter],
        queryFn: () =>
            apiService.get('/anomalies', {
                params: { severity: severityFilter || undefined, limit: 100 },
            }).then((res: any) => res.data),
        staleTime: 30 * 1000,
    });

    const { data: stats } = useQuery({
        queryKey: ['anomaly-stats'],
        queryFn: () => apiService.get('/anomaly-stats').then((res: any) => res.data),
        staleTime: 60 * 1000,
    });

    const anomalyList = anomalies?.anomalies || anomalies || [];
    const anomalyStats = stats || {
        total: anomalyList.length,
        critical: 0,
        high: 0,
        medium: 0,
        low: 0,
        resolved: 0,
    };

    return (
        <Container maxWidth="xl" sx={{ py: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
                <Box>
                    <Typography variant="h4" component="h1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <BugReport color="error" /> Anomaly Detection
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                        ML-powered anomaly detection across records, entities, and data sources
                    </Typography>
                </Box>
                <Tooltip title="Refresh">
                    <IconButton onClick={() => refetch()}>
                        <Refresh />
                    </IconButton>
                </Tooltip>
            </Box>

            {/* Stats Cards */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
                {[
                    { label: 'Total Anomalies', value: anomalyStats.total, icon: <Assessment />, color: '#1976d2' },
                    { label: 'Critical', value: anomalyStats.critical, icon: <Warning />, color: '#d32f2f' },
                    { label: 'High', value: anomalyStats.high, icon: <TrendingUp />, color: '#ed6c02' },
                    { label: 'Resolved', value: anomalyStats.resolved, icon: <CheckCircle />, color: '#2e7d32' },
                ].map((stat) => (
                    <Grid item xs={12} sm={6} md={3} key={stat.label}>
                        <Card elevation={1}>
                            <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                <Box sx={{ color: stat.color, display: 'flex' }}>{stat.icon}</Box>
                                <Box>
                                    <Typography variant="h5" fontWeight={600}>{stat.value}</Typography>
                                    <Typography variant="body2" color="text.secondary">{stat.label}</Typography>
                                </Box>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                    Failed to load anomalies. The anomaly detection API may not be active.
                </Alert>
            )}

            {/* Tabs */}
            <Paper sx={{ mb: 3 }}>
                <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
                    <Tab label="All Anomalies" />
                    <Tab label="By Detection Method" />
                    <Tab label="Trends" />
                </Tabs>

                <TabPanel value={tab} index={0}>
                    <Box sx={{ px: 2, pb: 2 }}>
                        <FormControl size="small" sx={{ minWidth: 150, mb: 2 }}>
                            <InputLabel>Severity</InputLabel>
                            <Select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} label="Severity">
                                <MenuItem value="">All</MenuItem>
                                <MenuItem value="critical">Critical</MenuItem>
                                <MenuItem value="high">High</MenuItem>
                                <MenuItem value="medium">Medium</MenuItem>
                                <MenuItem value="low">Low</MenuItem>
                            </Select>
                        </FormControl>

                        <TableContainer>
                            <Table size="small">
                                <TableHead>
                                    <TableRow>
                                        <TableCell>ID</TableCell>
                                        <TableCell>Type</TableCell>
                                        <TableCell>Severity</TableCell>
                                        <TableCell>Confidence</TableCell>
                                        <TableCell>Description</TableCell>
                                        <TableCell>Detected</TableCell>
                                        <TableCell>Status</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {isLoading ? (
                                        <TableRow>
                                            <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                                                <CircularProgress />
                                            </TableCell>
                                        </TableRow>
                                    ) : anomalyList.length > 0 ? (
                                        anomalyList.map((anomaly: any) => (
                                            <TableRow key={anomaly.id} hover>
                                                <TableCell>{anomaly.id}</TableCell>
                                                <TableCell>
                                                    <Chip label={anomaly.anomaly_type || anomaly.type || 'unknown'} size="small" variant="outlined" />
                                                </TableCell>
                                                <TableCell>
                                                    <Chip
                                                        label={anomaly.severity || 'medium'}
                                                        size="small"
                                                        color={severityColor(anomaly.severity) as any}
                                                    />
                                                </TableCell>
                                                <TableCell>
                                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                        <LinearProgress
                                                            variant="determinate"
                                                            value={(anomaly.confidence || anomaly.confidence_score || 0) * 100}
                                                            sx={{ width: 60, height: 6, borderRadius: 3 }}
                                                        />
                                                        <Typography variant="caption">
                                                            {((anomaly.confidence || anomaly.confidence_score || 0) * 100).toFixed(0)}%
                                                        </Typography>
                                                    </Box>
                                                </TableCell>
                                                <TableCell>
                                                    <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                                                        {anomaly.description || anomaly.message || '—'}
                                                    </Typography>
                                                </TableCell>
                                                <TableCell>
                                                    <Typography variant="caption" color="text.secondary">
                                                        {anomaly.detected_at ? new Date(anomaly.detected_at).toLocaleDateString() : '—'}
                                                    </Typography>
                                                </TableCell>
                                                <TableCell>
                                                    <Chip
                                                        label={anomaly.status || 'open'}
                                                        size="small"
                                                        color={anomaly.status === 'resolved' ? 'success' : 'warning'}
                                                        variant="outlined"
                                                    />
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    ) : (
                                        <TableRow>
                                            <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                                                <CheckCircle color="success" sx={{ fontSize: 40, mb: 1 }} />
                                                <Typography color="text.secondary">No anomalies detected</Typography>
                                            </TableCell>
                                        </TableRow>
                                    )}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    </Box>
                </TabPanel>

                <TabPanel value={tab} index={1}>
                    <Box sx={{ p: 2 }}>
                        <Grid container spacing={2}>
                            {['statistical', 'isolation_forest', 'rule_based', 'temporal'].map((method) => (
                                <Grid item xs={12} sm={6} md={3} key={method}>
                                    <Card variant="outlined">
                                        <CardContent>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                                <Security color="primary" />
                                                <Typography variant="subtitle2" textTransform="capitalize">
                                                    {method.replace('_', ' ')}
                                                </Typography>
                                            </Box>
                                            <Typography variant="h4" fontWeight={600}>
                                                {anomalyList.filter((a: any) => a.detection_method === method).length}
                                            </Typography>
                                            <Typography variant="caption" color="text.secondary">anomalies detected</Typography>
                                        </CardContent>
                                    </Card>
                                </Grid>
                            ))}
                        </Grid>
                    </Box>
                </TabPanel>

                <TabPanel value={tab} index={2}>
                    <Box sx={{ p: 2, textAlign: 'center' }}>
                        <Timeline sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
                        <Typography color="text.secondary">
                            Anomaly trend charts will appear here when sufficient data is available.
                        </Typography>
                    </Box>
                </TabPanel>
            </Paper>
        </Container>
    );
}

export default function AnomaliesPage() {
    if (!featureFlag('ml_dashboard')) {
        return (
            <Container maxWidth="md" sx={{ py: 8, textAlign: 'center' }}>
                <Typography variant="h5" color="text.secondary">
                    Anomaly Detection is coming soon
                </Typography>
            </Container>
        );
    }

    return (
        <ProtectedRoute>
            <AnomaliesContent />
        </ProtectedRoute>
    );
}
