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
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    CircularProgress,
    Alert,
    Chip,
    IconButton,
    Tooltip,
    Button,
    LinearProgress,
} from '@mui/material';
import {
    BuildCircle,
    CheckCircle,
    Error as ErrorIcon,
    PlayArrow,
    Refresh,
    Schedule,
    Storage,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../../../services/api';
import { ProtectedRoute } from '../../../context/AuthContext';

const stateNames: Record<string, string> = {
    AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California',
    CO: 'Colorado', CT: 'Connecticut', DE: 'Delaware', FL: 'Florida', GA: 'Georgia',
    HI: 'Hawaii', ID: 'Idaho', IL: 'Illinois', IN: 'Indiana', IA: 'Iowa',
    KS: 'Kansas', KY: 'Kentucky', LA: 'Louisiana', ME: 'Maine', MD: 'Maryland',
    MA: 'Massachusetts', MI: 'Michigan', MN: 'Minnesota', MS: 'Mississippi', MO: 'Missouri',
    MT: 'Montana', NE: 'Nebraska', NV: 'Nevada', NH: 'New Hampshire', NJ: 'New Jersey',
    NM: 'New Mexico', NY: 'New York', NC: 'North Carolina', ND: 'North Dakota', OH: 'Ohio',
    OK: 'Oklahoma', OR: 'Oregon', PA: 'Pennsylvania', RI: 'Rhode Island', SC: 'South Carolina',
    SD: 'South Dakota', TN: 'Tennessee', TX: 'Texas', UT: 'Utah', VT: 'Vermont',
    VA: 'Virginia', WA: 'Washington', WV: 'West Virginia', WI: 'Wisconsin', WY: 'Wyoming',
    DC: 'District of Columbia',
};

function statusChip(s: string) {
    switch (s?.toLowerCase()) {
        case 'active':
        case 'healthy':
            return <Chip label={s} size="small" color="success" />;
        case 'error':
        case 'failed':
            return <Chip label={s} size="small" color="error" />;
        case 'running':
            return <Chip label={s} size="small" color="info" />;
        case 'scheduled':
        case 'pending':
            return <Chip label={s} size="small" color="warning" />;
        default:
            return <Chip label={s || 'unknown'} size="small" variant="outlined" />;
    }
}

function ScrapersContent() {
    const queryClient = useQueryClient();

    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['admin-scrapers-status'],
        queryFn: () => apiService.get('/admin/scrapers/status').then((res: any) => res.data),
        staleTime: 30 * 1000,
        refetchInterval: 30 * 1000, // Auto-refresh every 30s
    });

    const runScraper = useMutation({
        mutationFn: (stateCode: string) =>
            apiService.post('/integrate/scraper', { state_code: stateCode }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['admin-scrapers-status'] });
        },
    });

    const scrapers = data?.scrapers || data || [];
    const activeCount = scrapers.filter((s: any) => s.status === 'active' || s.status === 'healthy').length;
    const errorCount = scrapers.filter((s: any) => s.status === 'error' || s.status === 'failed').length;
    const runningCount = scrapers.filter((s: any) => s.status === 'running').length;

    return (
        <Container maxWidth="xl" sx={{ py: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
                <Box>
                    <Typography variant="h4" component="h1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <BuildCircle color="primary" /> Scraper Monitoring
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                        Monitor and manage state-by-state scraper health
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
                    Scraper monitoring API may not be active.
                </Alert>
            )}

            {/* Summary Cards */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
                {[
                    { label: 'Total Scrapers', value: scrapers.length, icon: <Storage />, color: '#1976d2' },
                    { label: 'Active', value: activeCount, icon: <CheckCircle />, color: '#2e7d32' },
                    { label: 'Running', value: runningCount, icon: <Schedule />, color: '#ed6c02' },
                    { label: 'Errors', value: errorCount, icon: <ErrorIcon />, color: '#d32f2f' },
                ].map((stat) => (
                    <Grid item xs={6} sm={3} key={stat.label}>
                        <Card elevation={1}>
                            <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                <Box sx={{ color: stat.color, display: 'flex' }}>{stat.icon}</Box>
                                <Box>
                                    <Typography variant="h5" fontWeight={600}>{isLoading ? '—' : stat.value}</Typography>
                                    <Typography variant="body2" color="text.secondary">{stat.label}</Typography>
                                </Box>
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            {/* Scraper Table */}
            <Paper>
                <TableContainer>
                    <Table size="small">
                        <TableHead>
                            <TableRow>
                                <TableCell>State</TableCell>
                                <TableCell>Status</TableCell>
                                <TableCell>Records</TableCell>
                                <TableCell>Last Run</TableCell>
                                <TableCell>Duration</TableCell>
                                <TableCell>Success Rate</TableCell>
                                <TableCell>Actions</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {isLoading ? (
                                <TableRow>
                                    <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                                        <CircularProgress />
                                    </TableCell>
                                </TableRow>
                            ) : scrapers.length > 0 ? (
                                scrapers.map((scraper: any) => (
                                    <TableRow key={scraper.state_code || scraper.id} hover>
                                        <TableCell>
                                            <Box>
                                                <Typography variant="body2" fontWeight={500}>
                                                    {stateNames[scraper.state_code] || scraper.state_code}
                                                </Typography>
                                                <Typography variant="caption" color="text.disabled">
                                                    {scraper.state_code}
                                                </Typography>
                                            </Box>
                                        </TableCell>
                                        <TableCell>{statusChip(scraper.status)}</TableCell>
                                        <TableCell>{(scraper.record_count || 0).toLocaleString()}</TableCell>
                                        <TableCell>
                                            <Typography variant="caption">
                                                {scraper.last_run ? new Date(scraper.last_run).toLocaleString() : 'Never'}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="caption">
                                                {scraper.duration_ms ? `${(scraper.duration_ms / 1000).toFixed(1)}s` : '—'}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                <LinearProgress
                                                    variant="determinate"
                                                    value={scraper.success_rate ?? 0}
                                                    sx={{ width: 60, height: 6, borderRadius: 3 }}
                                                    color={
                                                        (scraper.success_rate ?? 0) >= 80
                                                            ? 'success'
                                                            : (scraper.success_rate ?? 0) >= 50
                                                                ? 'warning'
                                                                : 'error'
                                                    }
                                                />
                                                <Typography variant="caption">
                                                    {scraper.success_rate ?? 0}%
                                                </Typography>
                                            </Box>
                                        </TableCell>
                                        <TableCell>
                                            <Tooltip title="Run Now">
                                                <IconButton
                                                    size="small"
                                                    color="primary"
                                                    onClick={() => runScraper.mutate(scraper.state_code)}
                                                    disabled={scraper.status === 'running' || runScraper.isPending}
                                                >
                                                    <PlayArrow fontSize="small" />
                                                </IconButton>
                                            </Tooltip>
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                                        <BuildCircle sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} />
                                        <Typography color="text.secondary">No scraper data available</Typography>
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>
            </Paper>
        </Container>
    );
}

export default function ScrapersPage() {
    return (
        <ProtectedRoute>
            <ScrapersContent />
        </ProtectedRoute>
    );
}
