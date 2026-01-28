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
    useTheme,
    alpha,
    ToggleButton,
    ToggleButtonGroup,
    Divider,
} from '@mui/material';
import {
    TrendingUp as TrendingUpIcon,
    TrendingDown as TrendingDownIcon,
    Refresh as RefreshIcon,
    People as UsersIcon,
    Search as SearchIcon,
    Storage as RecordsIcon,
    AttachMoney as RevenueIcon,
    Timeline as TimelineIcon,
    BarChart as ChartIcon,
    Speed as SpeedIcon,
    QueryStats as QueryIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';

// =============================================================================
// TYPES
// =============================================================================

export interface TimeSeriesDataPoint {
    date: string;
    value: number;
}

export interface MetricCard {
    id: string;
    label: string;
    value: number;
    previousValue: number;
    format: 'number' | 'currency' | 'percent';
    icon: React.ReactNode;
    color: string;
    trend: TimeSeriesDataPoint[];
}

export interface TopItem {
    id: string;
    name: string;
    value: number;
    change: number;
}

export interface AnalyticsData {
    metrics: MetricCard[];
    topSearches: TopItem[];
    topRecordTypes: TopItem[];
    topJurisdictions: TopItem[];
    userActivity: TimeSeriesDataPoint[];
}

type TimeRange = '24h' | '7d' | '30d' | '90d';

interface AnalyticsDashboardProps {
    onMetricClick?: (metric: MetricCard) => void;
}

// =============================================================================
// MOCK DATA
// =============================================================================

const generateTrendData = (baseValue: number, days: number, variance: number): TimeSeriesDataPoint[] => {
    const data: TimeSeriesDataPoint[] = [];
    let value = baseValue;
    for (let i = days; i >= 0; i--) {
        const date = new Date(Date.now() - i * 86400000);
        value = value + (Math.random() - 0.5) * variance;
        data.push({ date: date.toISOString().split('T')[0], value: Math.max(0, Math.round(value)) });
    }
    return data;
};

const mockAnalyticsData: AnalyticsData = {
    metrics: [
        {
            id: 'active-users',
            label: 'Active Users',
            value: 12847,
            previousValue: 11523,
            format: 'number',
            icon: <UsersIcon />,
            color: '#2196f3',
            trend: generateTrendData(12000, 7, 500),
        },
        {
            id: 'daily-searches',
            label: 'Daily Searches',
            value: 45623,
            previousValue: 42100,
            format: 'number',
            icon: <SearchIcon />,
            color: '#4caf50',
            trend: generateTrendData(44000, 7, 2000),
        },
        {
            id: 'records-accessed',
            label: 'Records Accessed',
            value: 892456,
            previousValue: 845000,
            format: 'number',
            icon: <RecordsIcon />,
            color: '#ff9800',
            trend: generateTrendData(870000, 7, 15000),
        },
        {
            id: 'monthly-revenue',
            label: 'Monthly Revenue',
            value: 127500,
            previousValue: 118200,
            format: 'currency',
            icon: <RevenueIcon />,
            color: '#9c27b0',
            trend: generateTrendData(120000, 7, 5000),
        },
        {
            id: 'avg-response-time',
            label: 'Avg Response Time',
            value: 245,
            previousValue: 280,
            format: 'number',
            icon: <SpeedIcon />,
            color: '#00bcd4',
            trend: generateTrendData(260, 7, 20),
        },
        {
            id: 'api-calls',
            label: 'API Calls (24h)',
            value: 2340000,
            previousValue: 2180000,
            format: 'number',
            icon: <QueryIcon />,
            color: '#f44336',
            trend: generateTrendData(2200000, 7, 100000),
        },
    ],
    topSearches: [
        { id: '1', name: 'Property Records', value: 15234, change: 12 },
        { id: '2', name: 'Deed Transfers', value: 12456, change: 8 },
        { id: '3', name: 'Mortgage Records', value: 9876, change: -3 },
        { id: '4', name: 'Lien Search', value: 8543, change: 15 },
        { id: '5', name: 'Owner Lookup', value: 7234, change: 5 },
    ],
    topRecordTypes: [
        { id: '1', name: 'Property Deeds', value: 234567, change: 8 },
        { id: '2', name: 'Mortgages', value: 189456, change: 12 },
        { id: '3', name: 'Tax Records', value: 156789, change: 3 },
        { id: '4', name: 'Liens', value: 98765, change: -5 },
        { id: '5', name: 'Court Records', value: 87654, change: 7 },
    ],
    topJurisdictions: [
        { id: '1', name: 'Miami-Dade County', value: 456789, change: 10 },
        { id: '2', name: 'Palm Beach County', value: 345678, change: 8 },
        { id: '3', name: 'Broward County', value: 298765, change: 5 },
        { id: '4', name: 'Orange County', value: 234567, change: 12 },
        { id: '5', name: 'Hillsborough County', value: 198765, change: 3 },
    ],
    userActivity: generateTrendData(10000, 30, 1500),
};

// =============================================================================
// MINI CHART COMPONENT
// =============================================================================

interface MiniChartProps {
    data: TimeSeriesDataPoint[];
    color: string;
    height?: number;
}

function MiniChart({ data, color, height = 40 }: MiniChartProps) {
    const theme = useTheme();
    if (data.length < 2) return null;

    const values = data.map((d) => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    const width = 100;
    const points = data.map((d, i) => {
        const x = (i / (data.length - 1)) * width;
        const y = height - ((d.value - min) / range) * height;
        return `${x},${y}`;
    }).join(' ');

    return (
        <svg width={width} height={height} style={{ display: 'block' }}>
            <polyline
                points={points}
                fill="none"
                stroke={color}
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
            />
            <linearGradient id={`gradient-${color}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
            <polygon
                points={`0,${height} ${points} ${width},${height}`}
                fill={`url(#gradient-${color})`}
            />
        </svg>
    );
}

// =============================================================================
// METRIC CARD COMPONENT
// =============================================================================

interface MetricCardComponentProps {
    metric: MetricCard;
    onClick?: () => void;
}

function MetricCardComponent({ metric, onClick }: MetricCardComponentProps) {
    const theme = useTheme();
    const change = ((metric.value - metric.previousValue) / metric.previousValue) * 100;
    const isPositive = change >= 0;
    const isResponseTime = metric.id === 'avg-response-time';
    const displayPositive = isResponseTime ? !isPositive : isPositive;

    const formatValue = (val: number, format: string) => {
        if (format === 'currency') return `$${val.toLocaleString()}`;
        if (format === 'percent') return `${val}%`;
        if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
        if (val >= 1000) return `${(val / 1000).toFixed(1)}K`;
        return val.toLocaleString();
    };

    return (
        <Card
            onClick={onClick}
            sx={{
                cursor: onClick ? 'pointer' : 'default',
                transition: 'all 0.2s ease',
                '&:hover': onClick ? {
                    boxShadow: theme.shadows[4],
                    transform: 'translateY(-2px)',
                } : {},
            }}
        >
            <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                    <Box
                        sx={{
                            p: 1,
                            borderRadius: 1.5,
                            backgroundColor: alpha(metric.color, 0.1),
                            color: metric.color,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}
                    >
                        {metric.icon}
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        {displayPositive ? (
                            <TrendingUpIcon fontSize="small" color="success" />
                        ) : (
                            <TrendingDownIcon fontSize="small" color="error" />
                        )}
                        <Typography
                            variant="body2"
                            fontWeight={600}
                            sx={{ color: displayPositive ? 'success.main' : 'error.main' }}
                        >
                            {isPositive ? '+' : ''}{change.toFixed(1)}%
                        </Typography>
                    </Box>
                </Box>

                <Typography variant="h4" fontWeight={700} sx={{ mb: 0.5 }}>
                    {formatValue(metric.value, metric.format)}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {metric.label}
                </Typography>

                <MiniChart data={metric.trend} color={metric.color} />
            </CardContent>
        </Card>
    );
}

// =============================================================================
// TOP LIST COMPONENT
// =============================================================================

interface TopListProps {
    title: string;
    items: TopItem[];
    valueLabel?: string;
}

function TopList({ title, items, valueLabel = 'Count' }: TopListProps) {
    const theme = useTheme();

    return (
        <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" fontWeight={600} gutterBottom>
                {title}
            </Typography>
            <Box>
                {items.map((item, index) => (
                    <Box
                        key={item.id}
                        sx={{
                            display: 'flex',
                            alignItems: 'center',
                            py: 1.5,
                            borderBottom: index < items.length - 1 ? `1px solid ${theme.palette.divider}` : 'none',
                        }}
                    >
                        <Typography
                            variant="body2"
                            sx={{
                                width: 24,
                                height: 24,
                                borderRadius: '50%',
                                backgroundColor: alpha(theme.palette.primary.main, 0.1),
                                color: 'primary.main',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontWeight: 600,
                                mr: 1.5,
                            }}
                        >
                            {index + 1}
                        </Typography>
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                            <Typography variant="body2" fontWeight={500} noWrap>
                                {item.name}
                            </Typography>
                        </Box>
                        <Box sx={{ textAlign: 'right' }}>
                            <Typography variant="body2" fontWeight={600}>
                                {item.value.toLocaleString()}
                            </Typography>
                            <Typography
                                variant="caption"
                                sx={{ color: item.change >= 0 ? 'success.main' : 'error.main' }}
                            >
                                {item.change >= 0 ? '+' : ''}{item.change}%
                            </Typography>
                        </Box>
                    </Box>
                ))}
            </Box>
        </Paper>
    );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function AnalyticsDashboard({
    onMetricClick,
}: AnalyticsDashboardProps) {
    const theme = useTheme();
    const [timeRange, setTimeRange] = useState<TimeRange>('7d');

    // Fetch analytics data
    const { data: analytics = mockAnalyticsData, refetch, isLoading } = useQuery<AnalyticsData>({
        queryKey: ['analytics', timeRange],
        queryFn: async () => {
            try {
                const response = await apiService.get(`/analytics?range=${timeRange}`);
                return response.data;
            } catch {
                return mockAnalyticsData;
            }
        },
    });

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
                        Analytics Dashboard
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Platform usage metrics and performance insights
                    </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <ToggleButtonGroup
                        value={timeRange}
                        exclusive
                        onChange={(_, v) => v && setTimeRange(v)}
                        size="small"
                    >
                        <ToggleButton value="24h">24h</ToggleButton>
                        <ToggleButton value="7d">7d</ToggleButton>
                        <ToggleButton value="30d">30d</ToggleButton>
                        <ToggleButton value="90d">90d</ToggleButton>
                    </ToggleButtonGroup>
                    <Tooltip title="Refresh">
                        <IconButton onClick={() => refetch()} disabled={isLoading}>
                            <RefreshIcon />
                        </IconButton>
                    </Tooltip>
                </Box>
            </Box>

            {/* Metrics Grid */}
            <Grid container spacing={2} sx={{ mb: 4 }}>
                {analytics.metrics.map((metric) => (
                    <Grid item xs={12} sm={6} md={4} lg={2} key={metric.id}>
                        <MetricCardComponent
                            metric={metric}
                            onClick={onMetricClick ? () => onMetricClick(metric) : undefined}
                        />
                    </Grid>
                ))}
            </Grid>

            {/* Top Lists */}
            <Grid container spacing={3}>
                <Grid item xs={12} md={4}>
                    <TopList title="Top Searches" items={analytics.topSearches} />
                </Grid>
                <Grid item xs={12} md={4}>
                    <TopList title="Top Record Types" items={analytics.topRecordTypes} />
                </Grid>
                <Grid item xs={12} md={4}>
                    <TopList title="Top Jurisdictions" items={analytics.topJurisdictions} />
                </Grid>
            </Grid>
        </Paper>
    );
}
