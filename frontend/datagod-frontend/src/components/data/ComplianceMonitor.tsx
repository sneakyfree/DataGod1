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
    Button,
    Divider,
    Avatar,
    useTheme,
    alpha,
    Collapse,
    Badge,
} from '@mui/material';
import {
    CheckCircle as PassIcon,
    Warning as WarningIcon,
    Error as FailIcon,
    Refresh as RefreshIcon,
    Security as SecurityIcon,
    VerifiedUser as ComplianceIcon,
    Policy as PolicyIcon,
    Gavel as LegalIcon,
    Schedule as ScheduleIcon,
    ExpandMore as ExpandIcon,
    ExpandLess as CollapseIcon,
    PlayArrow as RunIcon,
    Description as ReportIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';

// =============================================================================
// TYPES
// =============================================================================

export type ComplianceStatus = 'pass' | 'warning' | 'fail' | 'pending' | 'not_applicable';

export interface ComplianceCheck {
    id: string;
    name: string;
    description: string;
    status: ComplianceStatus;
    lastChecked: string;
    nextCheck: string;
    score: number;
    findings: string[];
    remediations: string[];
}

export interface ComplianceFramework {
    id: string;
    name: string;
    abbreviation: string;
    description: string;
    overallStatus: ComplianceStatus;
    overallScore: number;
    checks: ComplianceCheck[];
    lastAudit: string;
    nextAudit: string;
}

interface ComplianceMonitorProps {
    onFrameworkSelect?: (framework: ComplianceFramework) => void;
}

// =============================================================================
// HELPERS
// =============================================================================

const statusConfig: Record<ComplianceStatus, { color: string; label: string; icon: React.ReactNode }> = {
    pass: { color: '#4caf50', label: 'Compliant', icon: <PassIcon /> },
    warning: { color: '#ff9800', label: 'Needs Attention', icon: <WarningIcon /> },
    fail: { color: '#f44336', label: 'Non-Compliant', icon: <FailIcon /> },
    pending: { color: '#9e9e9e', label: 'Pending', icon: <ScheduleIcon /> },
    not_applicable: { color: '#9e9e9e', label: 'N/A', icon: <PolicyIcon /> },
};

// =============================================================================
// MOCK DATA
// =============================================================================

const mockFrameworks: ComplianceFramework[] = [
    {
        id: 'fw-1',
        name: 'CCPA - California Consumer Privacy Act',
        abbreviation: 'CCPA',
        description: 'California privacy law protecting consumer data rights',
        overallStatus: 'pass',
        overallScore: 98,
        lastAudit: new Date(Date.now() - 86400000 * 30).toISOString(),
        nextAudit: new Date(Date.now() + 86400000 * 60).toISOString(),
        checks: [
            { id: 'c1', name: 'Data Subject Rights', description: 'Right to access, delete, and opt-out', status: 'pass', lastChecked: new Date().toISOString(), nextCheck: new Date(Date.now() + 86400000).toISOString(), score: 100, findings: [], remediations: [] },
            { id: 'c2', name: 'Privacy Notice', description: 'Clear disclosure of data practices', status: 'pass', lastChecked: new Date().toISOString(), nextCheck: new Date(Date.now() + 86400000).toISOString(), score: 100, findings: [], remediations: [] },
            { id: 'c3', name: 'Data Retention', description: 'Appropriate data retention policies', status: 'warning', lastChecked: new Date().toISOString(), nextCheck: new Date(Date.now() + 86400000).toISOString(), score: 85, findings: ['Some records exceed retention policy'], remediations: ['Implement automated purge for stale records'] },
        ],
    },
    {
        id: 'fw-2',
        name: 'SOC 2 Type II',
        abbreviation: 'SOC2',
        description: 'Service Organization Control security and availability',
        overallStatus: 'pass',
        overallScore: 95,
        lastAudit: new Date(Date.now() - 86400000 * 90).toISOString(),
        nextAudit: new Date(Date.now() + 86400000 * 275).toISOString(),
        checks: [
            { id: 'c4', name: 'Access Controls', description: 'Role-based access and authentication', status: 'pass', lastChecked: new Date().toISOString(), nextCheck: new Date(Date.now() + 86400000).toISOString(), score: 98, findings: [], remediations: [] },
            { id: 'c5', name: 'Encryption', description: 'Data encryption at rest and in transit', status: 'pass', lastChecked: new Date().toISOString(), nextCheck: new Date(Date.now() + 86400000).toISOString(), score: 100, findings: [], remediations: [] },
            { id: 'c6', name: 'Audit Logging', description: 'Comprehensive activity logging', status: 'pass', lastChecked: new Date().toISOString(), nextCheck: new Date(Date.now() + 86400000).toISOString(), score: 95, findings: [], remediations: [] },
            { id: 'c7', name: 'Incident Response', description: 'Security incident handling procedures', status: 'warning', lastChecked: new Date().toISOString(), nextCheck: new Date(Date.now() + 86400000).toISOString(), score: 88, findings: ['Incident response drill overdue'], remediations: ['Schedule quarterly IR drill'] },
        ],
    },
    {
        id: 'fw-3',
        name: 'FCRA - Fair Credit Reporting Act',
        abbreviation: 'FCRA',
        description: 'Federal law regulating consumer credit information',
        overallStatus: 'warning',
        overallScore: 87,
        lastAudit: new Date(Date.now() - 86400000 * 60).toISOString(),
        nextAudit: new Date(Date.now() + 86400000 * 30).toISOString(),
        checks: [
            { id: 'c8', name: 'Permissible Purpose', description: 'Valid purpose for data access', status: 'pass', lastChecked: new Date().toISOString(), nextCheck: new Date(Date.now() + 86400000).toISOString(), score: 100, findings: [], remediations: [] },
            { id: 'c9', name: 'Dispute Resolution', description: 'Consumer dispute handling process', status: 'warning', lastChecked: new Date().toISOString(), nextCheck: new Date(Date.now() + 86400000).toISOString(), score: 82, findings: ['Dispute resolution SLA occasionally exceeded'], remediations: ['Add automated escalation for pending disputes'] },
            { id: 'c10', name: 'Accuracy', description: 'Data accuracy and correction procedures', status: 'warning', lastChecked: new Date().toISOString(), nextCheck: new Date(Date.now() + 86400000).toISOString(), score: 79, findings: ['Data accuracy verification backlog'], remediations: ['Increase verification staffing', 'Implement ML-assisted verification'] },
        ],
    },
];

// =============================================================================
// FRAMEWORK CARD
// =============================================================================

interface FrameworkCardProps {
    framework: ComplianceFramework;
    expanded: boolean;
    onToggle: () => void;
}

function FrameworkCard({ framework, expanded, onToggle }: FrameworkCardProps) {
    const theme = useTheme();
    const status = statusConfig[framework.overallStatus];

    const passCount = framework.checks.filter((c) => c.status === 'pass').length;
    const warningCount = framework.checks.filter((c) => c.status === 'warning').length;
    const failCount = framework.checks.filter((c) => c.status === 'fail').length;

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
            {/* Status bar */}
            <Box
                sx={{
                    height: 4,
                    backgroundColor: status.color,
                }}
            />

            <CardContent>
                {/* Header */}
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 2 }}>
                    <Avatar
                        sx={{
                            bgcolor: alpha(status.color, 0.1),
                            color: status.color,
                        }}
                    >
                        {status.icon}
                    </Avatar>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="h6" fontWeight={600}>
                                {framework.abbreviation}
                            </Typography>
                            <Chip
                                size="small"
                                label={status.label}
                                sx={{
                                    backgroundColor: alpha(status.color, 0.1),
                                    color: status.color,
                                }}
                            />
                        </Box>
                        <Typography variant="body2" color="text.secondary">
                            {framework.name}
                        </Typography>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: status.color }}>
                            {framework.overallScore}%
                        </Typography>
                    </Box>
                </Box>

                {/* Check counts */}
                <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                    <Chip
                        size="small"
                        icon={<PassIcon sx={{ fontSize: '1rem !important' }} />}
                        label={`${passCount} Pass`}
                        sx={{ backgroundColor: alpha('#4caf50', 0.1), color: '#4caf50' }}
                    />
                    {warningCount > 0 && (
                        <Chip
                            size="small"
                            icon={<WarningIcon sx={{ fontSize: '1rem !important' }} />}
                            label={`${warningCount} Warning`}
                            sx={{ backgroundColor: alpha('#ff9800', 0.1), color: '#ff9800' }}
                        />
                    )}
                    {failCount > 0 && (
                        <Chip
                            size="small"
                            icon={<FailIcon sx={{ fontSize: '1rem !important' }} />}
                            label={`${failCount} Fail`}
                            sx={{ backgroundColor: alpha('#f44336', 0.1), color: '#f44336' }}
                        />
                    )}
                </Box>

                {/* Audit dates */}
                <Typography variant="caption" color="text.secondary">
                    Last audit: {new Date(framework.lastAudit).toLocaleDateString()} •
                    Next audit: {new Date(framework.nextAudit).toLocaleDateString()}
                </Typography>

                {/* Expand button */}
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1 }}>
                    <Button
                        size="small"
                        onClick={onToggle}
                        endIcon={expanded ? <CollapseIcon /> : <ExpandIcon />}
                    >
                        {expanded ? 'Less Details' : 'View Checks'}
                    </Button>
                </Box>

                {/* Expanded checks */}
                <Collapse in={expanded}>
                    <Divider sx={{ my: 2 }} />
                    <List dense disablePadding>
                        {framework.checks.map((check) => {
                            const checkStatus = statusConfig[check.status];
                            return (
                                <ListItem
                                    key={check.id}
                                    sx={{
                                        borderRadius: 1,
                                        mb: 1,
                                        backgroundColor: alpha(checkStatus.color, 0.05),
                                        border: `1px solid ${alpha(checkStatus.color, 0.2)}`,
                                    }}
                                >
                                    <ListItemIcon sx={{ minWidth: 36 }}>
                                        <Avatar
                                            sx={{
                                                width: 28,
                                                height: 28,
                                                backgroundColor: alpha(checkStatus.color, 0.1),
                                                color: checkStatus.color,
                                            }}
                                        >
                                            {checkStatus.icon}
                                        </Avatar>
                                    </ListItemIcon>
                                    <ListItemText
                                        primary={
                                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                                <Typography variant="body2" fontWeight={500}>
                                                    {check.name}
                                                </Typography>
                                                <Typography variant="body2" fontWeight={600} sx={{ color: checkStatus.color }}>
                                                    {check.score}%
                                                </Typography>
                                            </Box>
                                        }
                                        secondary={check.description}
                                    />
                                </ListItem>
                            );
                        })}
                    </List>
                </Collapse>
            </CardContent>
        </Card>
    );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function ComplianceMonitor({
    onFrameworkSelect,
}: ComplianceMonitorProps) {
    const theme = useTheme();
    const [expandedFrameworks, setExpandedFrameworks] = useState<Set<string>>(new Set());

    // Fetch frameworks
    const { data: frameworks = mockFrameworks, refetch, isLoading } = useQuery<ComplianceFramework[]>({
        queryKey: ['compliance-frameworks'],
        queryFn: async () => {
            try {
                const response = await apiService.get('/compliance/frameworks');
                return response.data;
            } catch {
                return mockFrameworks;
            }
        },
    });

    const toggleExpanded = (id: string) => {
        setExpandedFrameworks((prev) => {
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
    const compliantCount = frameworks.filter((f) => f.overallStatus === 'pass').length;
    const warningCount = frameworks.filter((f) => f.overallStatus === 'warning').length;
    const failCount = frameworks.filter((f) => f.overallStatus === 'fail').length;
    const avgScore = Math.round(frameworks.reduce((sum, f) => sum + f.overallScore, 0) / frameworks.length);

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
                        Compliance Monitor
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Track regulatory compliance across frameworks
                    </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button variant="outlined" startIcon={<ReportIcon />} size="small">
                        Generate Report
                    </Button>
                    <Tooltip title="Refresh">
                        <IconButton onClick={() => refetch()} disabled={isLoading}>
                            <RefreshIcon />
                        </IconButton>
                    </Tooltip>
                </Box>
            </Box>

            {/* Quick stats */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha(theme.palette.primary.main, 0.05) }}>
                        <Typography variant="h4" fontWeight={700} color="primary">
                            {frameworks.length}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Frameworks
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#4caf50', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#4caf50' }}>
                            {compliantCount}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Compliant
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#ff9800', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#ff9800' }}>
                            {warningCount}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Warnings
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#2196f3', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#2196f3' }}>
                            {avgScore}%
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Avg Score
                        </Typography>
                    </Box>
                </Grid>
            </Grid>

            {/* Framework cards */}
            <Grid container spacing={2}>
                {frameworks.map((framework) => (
                    <Grid item xs={12} md={6} key={framework.id}>
                        <FrameworkCard
                            framework={framework}
                            expanded={expandedFrameworks.has(framework.id)}
                            onToggle={() => toggleExpanded(framework.id)}
                        />
                    </Grid>
                ))}
            </Grid>
        </Paper>
    );
}
