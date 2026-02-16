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
    LinearProgress,
    IconButton,
    Tooltip,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Tabs,
    Tab,
} from '@mui/material';
import {
    VerifiedUser,
    Warning,
    CheckCircle,
    Error as ErrorIcon,
    Refresh,
    DataUsage,
    Storage,
    Speed,
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

function qualityColor(score: number): 'success' | 'warning' | 'error' {
    if (score >= 80) return 'success';
    if (score >= 50) return 'warning';
    return 'error';
}

function DataQualityContent() {
    const [tab, setTab] = useState(0);

    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['data-quality'],
        queryFn: () => apiService.get('/data-quality/report').then((res: any) => res.data),
        staleTime: 5 * 60 * 1000,
    });

    const report = data || {};
    const overallScore = report.overall_score || 0;
    const dimensions = report.dimensions || [];
    const issues = report.issues || [];

    return (
        <Container maxWidth="xl" sx={{ py: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
                <Box>
                    <Typography variant="h4" component="h1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <VerifiedUser color="primary" /> Data Quality
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                        Monitor data completeness, accuracy, and freshness across all sources
                    </Typography>
                </Box>
                <Tooltip title="Refresh">
                    <IconButton onClick={() => refetch()}>
                        <Refresh />
                    </IconButton>
                </Tooltip>
            </Box>

            {error && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                    Quality report API may not be active. Showing placeholder data.
                </Alert>
            )}

            {/* Overall Score */}
            <Paper sx={{ p: 3, mb: 3, textAlign: 'center' }}>
                <Box sx={{ position: 'relative', display: 'inline-flex', mb: 2 }}>
                    <CircularProgress
                        variant="determinate"
                        value={overallScore}
                        size={120}
                        thickness={4}
                        color={qualityColor(overallScore)}
                    />
                    <Box sx={{
                        position: 'absolute', top: 0, left: 0, bottom: 0, right: 0,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                        <Typography variant="h4" fontWeight={700}>
                            {isLoading ? '—' : `${overallScore}%`}
                        </Typography>
                    </Box>
                </Box>
                <Typography variant="h6">Overall Data Quality Score</Typography>
                <Typography variant="body2" color="text.secondary">
                    Based on completeness, accuracy, freshness, and consistency
                </Typography>
            </Paper>

            {/* Dimension Cards */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
                {[
                    { label: 'Completeness', icon: <DataUsage />, value: report.completeness || 0, desc: 'Fields filled vs required' },
                    { label: 'Accuracy', icon: <CheckCircle />, value: report.accuracy || 0, desc: 'Valid data patterns' },
                    { label: 'Freshness', icon: <Speed />, value: report.freshness || 0, desc: 'Data age & update frequency' },
                    { label: 'Consistency', icon: <Storage />, value: report.consistency || 0, desc: 'Cross-source agreement' },
                ].map((dim) => (
                    <Grid item xs={12} sm={6} md={3} key={dim.label}>
                        <Card elevation={1}>
                            <CardContent>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                    {dim.icon}
                                    <Typography variant="subtitle2">{dim.label}</Typography>
                                </Box>
                                <Typography variant="h5" fontWeight={600} color={`${qualityColor(dim.value)}.main`}>
                                    {dim.value}%
                                </Typography>
                                <LinearProgress variant="determinate" value={dim.value} color={qualityColor(dim.value)} sx={{ mt: 1, height: 6, borderRadius: 3 }} />
                                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>{dim.desc}</Typography>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            {/* Tabs */}
            <Paper>
                <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
                    <Tab label="Issues" />
                    <Tab label="By Source" />
                </Tabs>

                <TabPanel value={tab} index={0}>
                    <TableContainer sx={{ px: 2, pb: 2 }}>
                        <Table size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Severity</TableCell>
                                    <TableCell>Category</TableCell>
                                    <TableCell>Description</TableCell>
                                    <TableCell>Affected Records</TableCell>
                                    <TableCell>Status</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {issues.length > 0 ? (
                                    issues.map((issue: any, idx: number) => (
                                        <TableRow key={issue.id || idx} hover>
                                            <TableCell>
                                                <Chip
                                                    label={issue.severity || 'medium'}
                                                    size="small"
                                                    color={issue.severity === 'critical' ? 'error' : issue.severity === 'high' ? 'warning' : 'info'}
                                                />
                                            </TableCell>
                                            <TableCell>{issue.category || '—'}</TableCell>
                                            <TableCell>
                                                <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                                                    {issue.description || '—'}
                                                </Typography>
                                            </TableCell>
                                            <TableCell>{(issue.affected_count || 0).toLocaleString()}</TableCell>
                                            <TableCell>
                                                <Chip label={issue.status || 'open'} size="small" variant="outlined" />
                                            </TableCell>
                                        </TableRow>
                                    ))
                                ) : (
                                    <TableRow>
                                        <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                                            <CheckCircle color="success" sx={{ fontSize: 40, mb: 1 }} />
                                            <Typography color="text.secondary">No quality issues detected</Typography>
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </TabPanel>

                <TabPanel value={tab} index={1}>
                    <Box sx={{ p: 2, textAlign: 'center' }}>
                        <Storage sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
                        <Typography color="text.secondary">
                            Per-source quality breakdown will appear when data sources are configured
                        </Typography>
                    </Box>
                </TabPanel>
            </Paper>
        </Container>
    );
}

export default function DataQualityPage() {
    if (!featureFlag('data_quality')) {
        return (
            <Container maxWidth="md" sx={{ py: 8, textAlign: 'center' }}>
                <Typography variant="h5" color="text.secondary">
                    Data Quality Dashboard is coming soon
                </Typography>
            </Container>
        );
    }

    return (
        <ProtectedRoute>
            <DataQualityContent />
        </ProtectedRoute>
    );
}
