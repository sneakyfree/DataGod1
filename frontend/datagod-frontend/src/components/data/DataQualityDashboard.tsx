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
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    useTheme,
    alpha,
    Avatar,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    Button,
    Divider,
} from '@mui/material';
import {
    CheckCircle as GoodIcon,
    Warning as WarningIcon,
    Error as ErrorIcon,
    Refresh as RefreshIcon,
    TrendingUp as TrendingUpIcon,
    TrendingDown as TrendingDownIcon,
    Storage as DataIcon,
    VerifiedUser as ValidIcon,
    BugReport as IssueIcon,
    Schedule as TimeIcon,
    FilterList as FilterIcon,
    Assessment as ReportIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';

// =============================================================================
// TYPES
// =============================================================================

export type QualityLevel = 'excellent' | 'good' | 'fair' | 'poor' | 'critical';

export interface QualityMetric {
    name: string;
    score: number;
    previousScore: number;
    description: string;
    issueCount: number;
    lastChecked: string;
}

export interface DataSource {
    id: string;
    name: string;
    type: 'county' | 'state' | 'federal' | 'commercial';
    overallQuality: QualityLevel;
    overallScore: number;
    recordCount: number;
    lastUpdated: string;
    metrics: QualityMetric[];
}

export interface QualityIssue {
    id: string;
    sourceId: string;
    sourceName: string;
    type: 'missing' | 'invalid' | 'duplicate' | 'stale' | 'inconsistent';
    severity: 'low' | 'medium' | 'high' | 'critical';
    field: string;
    description: string;
    affectedRecords: number;
    detectedAt: string;
    resolved: boolean;
}

interface DataQualityDashboardProps {
    onSourceSelect?: (source: DataSource) => void;
    onIssueSelect?: (issue: QualityIssue) => void;
}

// =============================================================================
// HELPERS
// =============================================================================

const qualityConfig: Record<QualityLevel, { color: string; label: string }> = {
    excellent: { color: '#4caf50', label: 'Excellent' },
    good: { color: '#8bc34a', label: 'Good' },
    fair: { color: '#ff9800', label: 'Fair' },
    poor: { color: '#f44336', label: 'Poor' },
    critical: { color: '#b71c1c', label: 'Critical' },
};

const getQualityLevel = (score: number): QualityLevel => {
    if (score >= 95) return 'excellent';
    if (score >= 85) return 'good';
    if (score >= 70) return 'fair';
    if (score >= 50) return 'poor';
    return 'critical';
};

const severityColors = {
    low: '#9e9e9e',
    medium: '#ff9800',
    high: '#f44336',
    critical: '#b71c1c',
};

const issueTypeIcons = {
    missing: <ErrorIcon />,
    invalid: <WarningIcon />,
    duplicate: <IssueIcon />,
    stale: <TimeIcon />,
    inconsistent: <FilterIcon />,
};

// =============================================================================
// MOCK DATA
// =============================================================================

const mockDataSources: DataSource[] = [
    {
        id: 'source-1',
        name: 'Miami-Dade County',
        type: 'county',
        overallQuality: 'good',
        overallScore: 92,
        recordCount: 2450000,
        lastUpdated: new Date(Date.now() - 3600000).toISOString(),
        metrics: [
            { name: 'Completeness', score: 94, previousScore: 92, description: 'Required fields populated', issueCount: 145, lastChecked: new Date().toISOString() },
            { name: 'Accuracy', score: 91, previousScore: 91, description: 'Data matches source', issueCount: 234, lastChecked: new Date().toISOString() },
            { name: 'Consistency', score: 89, previousScore: 87, description: 'Values match expected formats', issueCount: 312, lastChecked: new Date().toISOString() },
            { name: 'Freshness', score: 96, previousScore: 95, description: 'Data is up to date', issueCount: 45, lastChecked: new Date().toISOString() },
        ],
    },
    {
        id: 'source-2',
        name: 'Palm Beach County',
        type: 'county',
        overallQuality: 'excellent',
        overallScore: 96,
        recordCount: 1850000,
        lastUpdated: new Date(Date.now() - 7200000).toISOString(),
        metrics: [
            { name: 'Completeness', score: 98, previousScore: 97, description: 'Required fields populated', issueCount: 23, lastChecked: new Date().toISOString() },
            { name: 'Accuracy', score: 95, previousScore: 94, description: 'Data matches source', issueCount: 78, lastChecked: new Date().toISOString() },
            { name: 'Consistency', score: 94, previousScore: 93, description: 'Values match expected formats', issueCount: 112, lastChecked: new Date().toISOString() },
            { name: 'Freshness', score: 97, previousScore: 96, description: 'Data is up to date', issueCount: 18, lastChecked: new Date().toISOString() },
        ],
    },
    {
        id: 'source-3',
        name: 'Broward County',
        type: 'county',
        overallQuality: 'fair',
        overallScore: 74,
        recordCount: 2100000,
        lastUpdated: new Date(Date.now() - 86400000).toISOString(),
        metrics: [
            { name: 'Completeness', score: 78, previousScore: 80, description: 'Required fields populated', issueCount: 456, lastChecked: new Date().toISOString() },
            { name: 'Accuracy', score: 72, previousScore: 74, description: 'Data matches source', issueCount: 678, lastChecked: new Date().toISOString() },
            { name: 'Consistency', score: 71, previousScore: 69, description: 'Values match expected formats', issueCount: 789, lastChecked: new Date().toISOString() },
            { name: 'Freshness', score: 75, previousScore: 82, description: 'Data is up to date', issueCount: 234, lastChecked: new Date().toISOString() },
        ],
    },
    {
        id: 'source-4',
        name: 'Florida State Records',
        type: 'state',
        overallQuality: 'good',
        overallScore: 88,
        recordCount: 12500000,
        lastUpdated: new Date(Date.now() - 43200000).toISOString(),
        metrics: [
            { name: 'Completeness', score: 90, previousScore: 89, description: 'Required fields populated', issueCount: 567, lastChecked: new Date().toISOString() },
            { name: 'Accuracy', score: 87, previousScore: 86, description: 'Data matches source', issueCount: 890, lastChecked: new Date().toISOString() },
            { name: 'Consistency', score: 86, previousScore: 85, description: 'Values match expected formats', issueCount: 1023, lastChecked: new Date().toISOString() },
            { name: 'Freshness', score: 89, previousScore: 88, description: 'Data is up to date', issueCount: 234, lastChecked: new Date().toISOString() },
        ],
    },
];

const mockIssues: QualityIssue[] = [
    { id: 'issue-1', sourceId: 'source-3', sourceName: 'Broward County', type: 'stale', severity: 'high', field: 'last_sale_date', description: 'Records not updated in 30+ days', affectedRecords: 12500, detectedAt: new Date(Date.now() - 3600000).toISOString(), resolved: false },
    { id: 'issue-2', sourceId: 'source-3', sourceName: 'Broward County', type: 'missing', severity: 'medium', field: 'owner_address', description: 'Missing mailing address for owners', affectedRecords: 8900, detectedAt: new Date(Date.now() - 7200000).toISOString(), resolved: false },
    { id: 'issue-3', sourceId: 'source-1', sourceName: 'Miami-Dade County', type: 'duplicate', severity: 'low', field: 'parcel_id', description: 'Potential duplicate parcel records', affectedRecords: 234, detectedAt: new Date(Date.now() - 86400000).toISOString(), resolved: false },
    { id: 'issue-4', sourceId: 'source-4', sourceName: 'Florida State Records', type: 'inconsistent', severity: 'medium', field: 'entity_name', description: 'Name format inconsistencies across records', affectedRecords: 4567, detectedAt: new Date(Date.now() - 172800000).toISOString(), resolved: false },
];

// =============================================================================
// SOURCE CARD COMPONENT
// =============================================================================

interface SourceCardProps {
    source: DataSource;
    selected: boolean;
    onClick: () => void;
}

function SourceCard({ source, selected, onClick }: SourceCardProps) {
    const theme = useTheme();
    const quality = qualityConfig[source.overallQuality];

    return (
        <Card
            onClick={onClick}
            sx={{
                cursor: 'pointer',
                border: selected
                    ? `2px solid ${theme.palette.primary.main}`
                    : `1px solid ${theme.palette.divider}`,
                transition: 'all 0.2s ease',
                '&:hover': {
                    boxShadow: theme.shadows[4],
                    borderColor: theme.palette.primary.light,
                },
            }}
        >
            <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 2 }}>
                    <Avatar
                        sx={{
                            bgcolor: alpha(quality.color, 0.1),
                            color: quality.color,
                        }}
                    >
                        <DataIcon />
                    </Avatar>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="subtitle1" fontWeight={600} noWrap>
                            {source.name}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                            <Chip size="small" label={source.type} variant="outlined" />
                            <Chip
                                size="small"
                                label={quality.label}
                                sx={{
                                    backgroundColor: alpha(quality.color, 0.1),
                                    color: quality.color,
                                }}
                            />
                        </Box>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                        <Typography variant="h5" fontWeight={700} sx={{ color: quality.color }}>
                            {source.overallScore}%
                        </Typography>
                    </Box>
                </Box>

                <Typography variant="caption" color="text.secondary">
                    {source.recordCount.toLocaleString()} records • Updated {new Date(source.lastUpdated).toLocaleString()}
                </Typography>
            </CardContent>
        </Card>
    );
}

// =============================================================================
// METRICS DETAIL
// =============================================================================

interface MetricsDetailProps {
    source: DataSource;
}

function MetricsDetail({ source }: MetricsDetailProps) {
    const theme = useTheme();

    return (
        <Paper sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight={600} gutterBottom>
                {source.name} - Quality Metrics
            </Typography>

            <Grid container spacing={2} sx={{ mb: 3 }}>
                {source.metrics.map((metric) => {
                    const trend = metric.score - metric.previousScore;
                    const level = getQualityLevel(metric.score);
                    const config = qualityConfig[level];

                    return (
                        <Grid item xs={12} sm={6} key={metric.name}>
                            <Box
                                sx={{
                                    p: 2,
                                    borderRadius: 2,
                                    border: `1px solid ${theme.palette.divider}`,
                                }}
                            >
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                    <Typography variant="subtitle2">{metric.name}</Typography>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                        {trend > 0 ? (
                                            <TrendingUpIcon fontSize="small" color="success" />
                                        ) : trend < 0 ? (
                                            <TrendingDownIcon fontSize="small" color="error" />
                                        ) : null}
                                        <Typography
                                            variant="caption"
                                            sx={{ color: trend > 0 ? 'success.main' : trend < 0 ? 'error.main' : 'text.secondary' }}
                                        >
                                            {trend > 0 ? '+' : ''}{trend}%
                                        </Typography>
                                    </Box>
                                </Box>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                                    <Typography variant="h4" fontWeight={700} sx={{ color: config.color }}>
                                        {metric.score}%
                                    </Typography>
                                    <LinearProgress
                                        variant="determinate"
                                        value={metric.score}
                                        sx={{
                                            flex: 1,
                                            height: 8,
                                            borderRadius: 4,
                                            backgroundColor: alpha(config.color, 0.1),
                                            '& .MuiLinearProgress-bar': {
                                                backgroundColor: config.color,
                                            },
                                        }}
                                    />
                                </Box>
                                <Typography variant="caption" color="text.secondary">
                                    {metric.description} • {metric.issueCount} issues
                                </Typography>
                            </Box>
                        </Grid>
                    );
                })}
            </Grid>
        </Paper>
    );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function DataQualityDashboard({
    onSourceSelect,
    onIssueSelect,
}: DataQualityDashboardProps) {
    const theme = useTheme();
    const [selectedSource, setSelectedSource] = useState<DataSource | null>(mockDataSources[0]);
    const [filterType, setFilterType] = useState<string>('all');
    const [filterSeverity, setFilterSeverity] = useState<string>('all');

    // Fetch data
    const { data: sources = mockDataSources, refetch: refetchSources } = useQuery<DataSource[]>({
        queryKey: ['data-sources'],
        queryFn: async () => {
            try {
                const response = await apiService.get('/data-quality/sources');
                return response.data;
            } catch {
                return mockDataSources;
            }
        },
    });

    const { data: issues = mockIssues } = useQuery<QualityIssue[]>({
        queryKey: ['quality-issues'],
        queryFn: async () => {
            try {
                const response = await apiService.get('/data-quality/issues');
                return response.data;
            } catch {
                return mockIssues;
            }
        },
    });

    // Filter issues
    const filteredIssues = issues.filter((i) => {
        if (filterType !== 'all' && i.type !== filterType) return false;
        if (filterSeverity !== 'all' && i.severity !== filterSeverity) return false;
        if (selectedSource && i.sourceId !== selectedSource.id) return false;
        return true;
    });

    // Calculate stats
    const avgQuality = Math.round(sources.reduce((sum, s) => sum + s.overallScore, 0) / sources.length);
    const totalRecords = sources.reduce((sum, s) => sum + s.recordCount, 0);
    const criticalIssues = issues.filter((i) => i.severity === 'critical' || i.severity === 'high').length;

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
                        Data Quality Dashboard
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Monitor data source quality and track issues
                    </Typography>
                </Box>
                <Tooltip title="Refresh">
                    <IconButton onClick={() => refetchSources()}>
                        <RefreshIcon />
                    </IconButton>
                </Tooltip>
            </Box>

            {/* Quick stats */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha(theme.palette.primary.main, 0.05) }}>
                        <Typography variant="h4" fontWeight={700} color="primary">
                            {sources.length}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Data Sources
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#4caf50', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#4caf50' }}>
                            {avgQuality}%
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Avg Quality
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#2196f3', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#2196f3' }}>
                            {(totalRecords / 1000000).toFixed(1)}M
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Total Records
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#f44336', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#f44336' }}>
                            {criticalIssues}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Critical Issues
                        </Typography>
                    </Box>
                </Grid>
            </Grid>

            {/* Sources + Detail */}
            <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} md={5}>
                    <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                        Data Sources
                    </Typography>
                    <Grid container spacing={2}>
                        {sources.map((source) => (
                            <Grid item xs={12} key={source.id}>
                                <SourceCard
                                    source={source}
                                    selected={selectedSource?.id === source.id}
                                    onClick={() => {
                                        setSelectedSource(source);
                                        onSourceSelect?.(source);
                                    }}
                                />
                            </Grid>
                        ))}
                    </Grid>
                </Grid>
                <Grid item xs={12} md={7}>
                    {selectedSource && <MetricsDetail source={selectedSource} />}
                </Grid>
            </Grid>

            {/* Issues Section */}
            <Divider sx={{ my: 3 }} />
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6" fontWeight={600}>
                    Quality Issues
                </Typography>
                <Box sx={{ display: 'flex', gap: 2 }}>
                    <FormControl size="small" sx={{ minWidth: 120 }}>
                        <InputLabel>Type</InputLabel>
                        <Select value={filterType} label="Type" onChange={(e) => setFilterType(e.target.value)}>
                            <MenuItem value="all">All Types</MenuItem>
                            <MenuItem value="missing">Missing</MenuItem>
                            <MenuItem value="invalid">Invalid</MenuItem>
                            <MenuItem value="duplicate">Duplicate</MenuItem>
                            <MenuItem value="stale">Stale</MenuItem>
                            <MenuItem value="inconsistent">Inconsistent</MenuItem>
                        </Select>
                    </FormControl>
                    <FormControl size="small" sx={{ minWidth: 120 }}>
                        <InputLabel>Severity</InputLabel>
                        <Select value={filterSeverity} label="Severity" onChange={(e) => setFilterSeverity(e.target.value)}>
                            <MenuItem value="all">All</MenuItem>
                            <MenuItem value="critical">Critical</MenuItem>
                            <MenuItem value="high">High</MenuItem>
                            <MenuItem value="medium">Medium</MenuItem>
                            <MenuItem value="low">Low</MenuItem>
                        </Select>
                    </FormControl>
                </Box>
            </Box>

            <TableContainer>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Source</TableCell>
                            <TableCell>Type</TableCell>
                            <TableCell>Severity</TableCell>
                            <TableCell>Field</TableCell>
                            <TableCell>Description</TableCell>
                            <TableCell align="right">Affected</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {filteredIssues.map((issue) => (
                            <TableRow
                                key={issue.id}
                                hover
                                onClick={() => onIssueSelect?.(issue)}
                                sx={{ cursor: 'pointer' }}
                            >
                                <TableCell>{issue.sourceName}</TableCell>
                                <TableCell>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                        {issueTypeIcons[issue.type]}
                                        {issue.type}
                                    </Box>
                                </TableCell>
                                <TableCell>
                                    <Chip
                                        size="small"
                                        label={issue.severity}
                                        sx={{
                                            backgroundColor: alpha(severityColors[issue.severity], 0.1),
                                            color: severityColors[issue.severity],
                                        }}
                                    />
                                </TableCell>
                                <TableCell><code>{issue.field}</code></TableCell>
                                <TableCell>{issue.description}</TableCell>
                                <TableCell align="right">{issue.affectedRecords.toLocaleString()}</TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
        </Paper>
    );
}
