'use client';

import React, { useState } from 'react';
import {
    Box,
    Paper,
    Typography,
    Grid,
    Card,
    CardContent,
    Chip,
    IconButton,
    Tooltip,
    LinearProgress,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    Avatar,
    Divider,
    useTheme,
    alpha,
    Badge,
    Collapse,
    Button,
} from '@mui/material';
import {
    CheckCircle as HealthyIcon,
    Warning as DegradedIcon,
    Error as DownIcon,
    Refresh as RefreshIcon,
    Memory as MemoryIcon,
    Storage as StorageIcon,
    Speed as CpuIcon,
    Dns as ServerIcon,
    Cloud as CloudIcon,
    Timer as UptimeIcon,
    ExpandMore as ExpandIcon,
    ExpandLess as CollapseIcon,
    History as HistoryIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';

// =============================================================================
// TYPES
// =============================================================================

export type ServiceStatus = 'healthy' | 'degraded' | 'down' | 'maintenance';

export interface ServiceMetrics {
    cpu: number;
    memory: number;
    disk: number;
    latency: number;
    requestsPerSecond: number;
    errorRate: number;
}

export interface ServiceIncident {
    id: string;
    title: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    startedAt: string;
    resolvedAt?: string;
}

export interface ServiceHealth {
    id: string;
    name: string;
    type: 'api' | 'database' | 'cache' | 'queue' | 'storage' | 'external';
    status: ServiceStatus;
    uptime: number;
    lastChecked: string;
    metrics: ServiceMetrics;
    recentIncidents: ServiceIncident[];
    dependencies: string[];
}

interface SystemHealthMonitorProps {
    onServiceSelect?: (service: ServiceHealth) => void;
}

// =============================================================================
// HELPERS
// =============================================================================

const statusConfig: Record<ServiceStatus, { color: string; label: string; icon: React.ReactNode }> = {
    healthy: { color: '#4caf50', label: 'Healthy', icon: <HealthyIcon /> },
    degraded: { color: '#ff9800', label: 'Degraded', icon: <DegradedIcon /> },
    down: { color: '#f44336', label: 'Down', icon: <DownIcon /> },
    maintenance: { color: '#9e9e9e', label: 'Maintenance', icon: <ServerIcon /> },
};

const typeIcons: Record<string, React.ReactNode> = {
    api: <CloudIcon />,
    database: <StorageIcon />,
    cache: <MemoryIcon />,
    queue: <HistoryIcon />,
    storage: <StorageIcon />,
    external: <CloudIcon />,
};

// =============================================================================
// MOCK DATA
// =============================================================================

const mockServices: ServiceHealth[] = [
    {
        id: 'api-gateway',
        name: 'API Gateway',
        type: 'api',
        status: 'healthy',
        uptime: 99.99,
        lastChecked: new Date().toISOString(),
        metrics: { cpu: 35, memory: 62, disk: 45, latency: 45, requestsPerSecond: 1250, errorRate: 0.02 },
        recentIncidents: [],
        dependencies: ['auth-service', 'postgres-primary'],
    },
    {
        id: 'auth-service',
        name: 'Auth Service',
        type: 'api',
        status: 'healthy',
        uptime: 99.98,
        lastChecked: new Date().toISOString(),
        metrics: { cpu: 28, memory: 45, disk: 30, latency: 25, requestsPerSecond: 890, errorRate: 0.01 },
        recentIncidents: [],
        dependencies: ['redis-cache', 'postgres-primary'],
    },
    {
        id: 'search-service',
        name: 'Search Service',
        type: 'api',
        status: 'degraded',
        uptime: 99.85,
        lastChecked: new Date().toISOString(),
        metrics: { cpu: 78, memory: 85, disk: 55, latency: 180, requestsPerSecond: 450, errorRate: 1.2 },
        recentIncidents: [
            { id: '1', title: 'Elevated response times', severity: 'medium', startedAt: new Date(Date.now() - 1800000).toISOString() },
        ],
        dependencies: ['elasticsearch', 'postgres-replica'],
    },
    {
        id: 'postgres-primary',
        name: 'PostgreSQL Primary',
        type: 'database',
        status: 'healthy',
        uptime: 99.995,
        lastChecked: new Date().toISOString(),
        metrics: { cpu: 42, memory: 75, disk: 68, latency: 5, requestsPerSecond: 5600, errorRate: 0.001 },
        recentIncidents: [],
        dependencies: [],
    },
    {
        id: 'redis-cache',
        name: 'Redis Cache',
        type: 'cache',
        status: 'healthy',
        uptime: 99.99,
        lastChecked: new Date().toISOString(),
        metrics: { cpu: 15, memory: 55, disk: 20, latency: 2, requestsPerSecond: 15000, errorRate: 0 },
        recentIncidents: [],
        dependencies: [],
    },
    {
        id: 'elasticsearch',
        name: 'Elasticsearch',
        type: 'database',
        status: 'degraded',
        uptime: 99.9,
        lastChecked: new Date().toISOString(),
        metrics: { cpu: 82, memory: 88, disk: 72, latency: 120, requestsPerSecond: 800, errorRate: 0.5 },
        recentIncidents: [
            { id: '2', title: 'High memory usage on node 2', severity: 'medium', startedAt: new Date(Date.now() - 3600000).toISOString() },
        ],
        dependencies: [],
    },
];

// =============================================================================
// METRIC BAR COMPONENT
// =============================================================================

interface MetricBarProps {
    label: string;
    value: number;
    unit?: string;
    warningThreshold?: number;
    criticalThreshold?: number;
}

function MetricBar({ label, value, unit = '%', warningThreshold = 70, criticalThreshold = 90 }: MetricBarProps) {
    const color = value >= criticalThreshold ? '#f44336' : value >= warningThreshold ? '#ff9800' : '#4caf50';

    return (
        <Box sx={{ mb: 1.5 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="caption" color="text.secondary">
                    {label}
                </Typography>
                <Typography variant="caption" fontWeight={600} sx={{ color }}>
                    {value}{unit}
                </Typography>
            </Box>
            <LinearProgress
                variant="determinate"
                value={Math.min(value, 100)}
                sx={{
                    height: 6,
                    borderRadius: 3,
                    backgroundColor: alpha(color, 0.1),
                    '& .MuiLinearProgress-bar': {
                        backgroundColor: color,
                        borderRadius: 3,
                    },
                }}
            />
        </Box>
    );
}

// =============================================================================
// SERVICE CARD COMPONENT
// =============================================================================

interface ServiceCardProps {
    service: ServiceHealth;
    expanded: boolean;
    onToggle: () => void;
}

function ServiceCard({ service, expanded, onToggle }: ServiceCardProps) {
    const theme = useTheme();
    const status = statusConfig[service.status];

    return (
        <Card
            sx={{
                border: `1px solid ${alpha(status.color, 0.3)}`,
                transition: 'all 0.2s ease',
                '&:hover': {
                    boxShadow: theme.shadows[4],
                },
            }}
        >
            <CardContent>
                {/* Header */}
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 2 }}>
                    <Badge
                        overlap="circular"
                        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                        badgeContent={
                            <Box
                                sx={{
                                    width: 12,
                                    height: 12,
                                    borderRadius: '50%',
                                    backgroundColor: status.color,
                                    border: `2px solid ${theme.palette.background.paper}`,
                                }}
                            />
                        }
                    >
                        <Avatar
                            sx={{
                                bgcolor: alpha(status.color, 0.1),
                                color: status.color,
                            }}
                        >
                            {typeIcons[service.type]}
                        </Avatar>
                    </Badge>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="subtitle1" fontWeight={600}>
                            {service.name}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                            <Chip size="small" label={service.type} variant="outlined" />
                            <Chip
                                size="small"
                                label={status.label}
                                sx={{
                                    backgroundColor: alpha(status.color, 0.1),
                                    color: status.color,
                                }}
                            />
                        </Box>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                        <Typography variant="h6" fontWeight={700} sx={{ color: status.color }}>
                            {service.uptime.toFixed(2)}%
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            uptime
                        </Typography>
                    </Box>
                </Box>

                {/* Quick metrics */}
                <Grid container spacing={1} sx={{ mb: 1 }}>
                    <Grid item xs={4}>
                        <MetricBar label="CPU" value={service.metrics.cpu} />
                    </Grid>
                    <Grid item xs={4}>
                        <MetricBar label="Memory" value={service.metrics.memory} />
                    </Grid>
                    <Grid item xs={4}>
                        <MetricBar label="Disk" value={service.metrics.disk} />
                    </Grid>
                </Grid>

                {/* Incidents badge */}
                {service.recentIncidents.length > 0 && (
                    <Chip
                        size="small"
                        icon={<DegradedIcon sx={{ fontSize: '1rem !important' }} />}
                        label={`${service.recentIncidents.length} Active Incident${service.recentIncidents.length > 1 ? 's' : ''}`}
                        sx={{
                            backgroundColor: alpha('#ff9800', 0.1),
                            color: '#ff9800',
                            mb: 1,
                        }}
                    />
                )}

                {/* Expand button */}
                <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <Button
                        size="small"
                        onClick={onToggle}
                        endIcon={expanded ? <CollapseIcon /> : <ExpandIcon />}
                    >
                        {expanded ? 'Less' : 'Details'}
                    </Button>
                </Box>

                {/* Expanded content */}
                <Collapse in={expanded}>
                    <Divider sx={{ my: 2 }} />

                    {/* Performance metrics */}
                    <Typography variant="subtitle2" gutterBottom>
                        Performance
                    </Typography>
                    <Grid container spacing={2} sx={{ mb: 2 }}>
                        <Grid item xs={4}>
                            <Typography variant="caption" color="text.secondary">Latency</Typography>
                            <Typography variant="body2" fontWeight={600}>{service.metrics.latency}ms</Typography>
                        </Grid>
                        <Grid item xs={4}>
                            <Typography variant="caption" color="text.secondary">Requests/s</Typography>
                            <Typography variant="body2" fontWeight={600}>{service.metrics.requestsPerSecond.toLocaleString()}</Typography>
                        </Grid>
                        <Grid item xs={4}>
                            <Typography variant="caption" color="text.secondary">Error Rate</Typography>
                            <Typography variant="body2" fontWeight={600}>{service.metrics.errorRate}%</Typography>
                        </Grid>
                    </Grid>

                    {/* Dependencies */}
                    {service.dependencies.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                            <Typography variant="subtitle2" gutterBottom>
                                Dependencies
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                                {service.dependencies.map((dep) => (
                                    <Chip key={dep} label={dep} size="small" variant="outlined" />
                                ))}
                            </Box>
                        </Box>
                    )}

                    {/* Recent incidents */}
                    {service.recentIncidents.length > 0 && (
                        <Box>
                            <Typography variant="subtitle2" gutterBottom>
                                Recent Incidents
                            </Typography>
                            <List dense disablePadding>
                                {service.recentIncidents.map((incident) => (
                                    <ListItem key={incident.id} disableGutters>
                                        <ListItemIcon sx={{ minWidth: 32 }}>
                                            <DegradedIcon fontSize="small" color="warning" />
                                        </ListItemIcon>
                                        <ListItemText
                                            primary={incident.title}
                                            secondary={`Started ${new Date(incident.startedAt).toLocaleTimeString()}`}
                                        />
                                    </ListItem>
                                ))}
                            </List>
                        </Box>
                    )}
                </Collapse>
            </CardContent>
        </Card>
    );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function SystemHealthMonitor({
    onServiceSelect,
}: SystemHealthMonitorProps) {
    const theme = useTheme();
    const [expandedServices, setExpandedServices] = useState<Set<string>>(new Set());

    // Fetch services
    const { data: services = mockServices, refetch, isLoading } = useQuery<ServiceHealth[]>({
        queryKey: ['system-health'],
        queryFn: async () => {
            try {
                const response = await apiService.get('/system/health');
                return response.data;
            } catch {
                return mockServices;
            }
        },
        refetchInterval: 10000, // Auto-refresh every 10 seconds
    });

    const toggleExpanded = (id: string) => {
        setExpandedServices((prev) => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    };

    // Calculate stats
    const healthyCount = services.filter((s) => s.status === 'healthy').length;
    const degradedCount = services.filter((s) => s.status === 'degraded').length;
    const downCount = services.filter((s) => s.status === 'down').length;
    const avgUptime = services.reduce((sum, s) => sum + s.uptime, 0) / services.length;

    return (
        <Paper
            elevation={0}
            sx={{
                p: 3,
                backgroundColor: theme.palette.mode === 'dark'
                    ? alpha(theme.palette.background.paper, 0.8)
                    : theme.palette.background.paper,
                borderRadius: 2,
            }}
        >
            {/* Header */}
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
                <Box>
                    <Typography variant="h5" fontWeight={700}>
                        System Health Monitor
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Real-time infrastructure and service status
                    </Typography>
                </Box>
                <Tooltip title="Refresh">
                    <IconButton onClick={() => refetch()} disabled={isLoading}>
                        <RefreshIcon />
                    </IconButton>
                </Tooltip>
            </Box>

            {/* Quick stats */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha(theme.palette.primary.main, 0.05) }}>
                        <Typography variant="h4" fontWeight={700} color="primary">
                            {services.length}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Services
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#4caf50', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#4caf50' }}>
                            {healthyCount}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Healthy
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#ff9800', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#ff9800' }}>
                            {degradedCount}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Degraded
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#2196f3', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#2196f3' }}>
                            {avgUptime.toFixed(2)}%
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Avg Uptime
                        </Typography>
                    </Box>
                </Grid>
            </Grid>

            {/* Service cards */}
            <Grid container spacing={2}>
                {services.map((service) => (
                    <Grid item xs={12} md={6} lg={4} key={service.id}>
                        <ServiceCard
                            service={service}
                            expanded={expandedServices.has(service.id)}
                            onToggle={() => toggleExpanded(service.id)}
                        />
                    </Grid>
                ))}
            </Grid>
        </Paper>
    );
}
