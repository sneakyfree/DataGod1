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
    LinearProgress,
    IconButton,
    Tooltip,
    Avatar,
    List,
    ListItem,
    ListItemAvatar,
    ListItemText,
    Divider,
    Badge,
    useTheme,
    alpha,
    Collapse,
    Button,
} from '@mui/material';
import {
    SmartToy as AgentIcon,
    CheckCircle as SuccessIcon,
    Error as ErrorIcon,
    HourglassEmpty as PendingIcon,
    Refresh as RefreshIcon,
    ExpandMore as ExpandIcon,
    ExpandLess as CollapseIcon,
    Speed as SpeedIcon,
    Memory as MemoryIcon,
    Schedule as ScheduleIcon,
    TrendingUp as TrendingUpIcon,
    Psychology as ThinkingIcon,
    Visibility as VisibilityIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';

// =============================================================================
// TYPES
// =============================================================================

export type AgentStatus = 'idle' | 'thinking' | 'executing' | 'success' | 'error' | 'waiting';

export interface AgentTask {
    id: string;
    name: string;
    status: AgentStatus;
    startedAt?: string;
    completedAt?: string;
    duration?: number;
    confidence?: number;
    output?: string;
}

export interface Agent {
    id: string;
    name: string;
    type: 'orchestrator' | 'specialist' | 'validator' | 'analyst';
    status: AgentStatus;
    description: string;
    currentTask?: AgentTask;
    recentTasks: AgentTask[];
    metrics: {
        totalTasks: number;
        successRate: number;
        avgResponseTime: number;
        avgConfidence: number;
    };
    capabilities: string[];
}

export interface CrewStatus {
    id: string;
    name: string;
    status: 'active' | 'paused' | 'idle' | 'error';
    agents: Agent[];
    currentWorkflow?: string;
    startedAt?: string;
    progress: number;
}

interface AgentStatusDashboardProps {
    crewId?: string;
    refreshInterval?: number;
    onAgentClick?: (agent: Agent) => void;
}

// =============================================================================
// STATUS HELPERS
// =============================================================================

const statusColors: Record<AgentStatus, string> = {
    idle: '#9e9e9e',
    thinking: '#2196f3',
    executing: '#ff9800',
    success: '#4caf50',
    error: '#f44336',
    waiting: '#9c27b0',
};

const statusLabels: Record<AgentStatus, string> = {
    idle: 'Idle',
    thinking: 'Thinking...',
    executing: 'Executing',
    success: 'Completed',
    error: 'Error',
    waiting: 'Waiting',
};

const getStatusIcon = (status: AgentStatus) => {
    switch (status) {
        case 'success':
            return <SuccessIcon />;
        case 'error':
            return <ErrorIcon />;
        case 'thinking':
            return <ThinkingIcon />;
        case 'executing':
            return <SpeedIcon />;
        case 'waiting':
            return <PendingIcon />;
        default:
            return <AgentIcon />;
    }
};

const getAgentTypeIcon = (type: string) => {
    switch (type) {
        case 'orchestrator':
            return '🎯';
        case 'specialist':
            return '🔬';
        case 'validator':
            return '✅';
        case 'analyst':
            return '📊';
        default:
            return '🤖';
    }
};

// =============================================================================
// MOCK DATA
// =============================================================================

const mockAgents: Agent[] = [
    {
        id: 'agent-1',
        name: 'Master Orchestrator',
        type: 'orchestrator',
        status: 'executing',
        description: 'Coordinates all agent activities and workflow execution',
        currentTask: {
            id: 'task-1',
            name: 'Processing batch #1247',
            status: 'executing',
            startedAt: new Date(Date.now() - 45000).toISOString(),
            confidence: 0.92,
        },
        recentTasks: [
            { id: 't1', name: 'Validate county records', status: 'success', duration: 2340, confidence: 0.95 },
            { id: 't2', name: 'Process ownership chain', status: 'success', duration: 4520, confidence: 0.88 },
        ],
        metrics: {
            totalTasks: 1247,
            successRate: 0.97,
            avgResponseTime: 2.3,
            avgConfidence: 0.91,
        },
        capabilities: ['Workflow orchestration', 'Task delegation', 'Error recovery', 'Priority management'],
    },
    {
        id: 'agent-2',
        name: 'Data Collector',
        type: 'specialist',
        status: 'thinking',
        description: 'Scrapes and collects public records from county sources',
        currentTask: {
            id: 'task-2',
            name: 'Scraping Miami-Dade records',
            status: 'thinking',
            startedAt: new Date(Date.now() - 12000).toISOString(),
            confidence: 0.78,
        },
        recentTasks: [
            { id: 't3', name: 'Collect Palm Beach data', status: 'success', duration: 8900, confidence: 0.92 },
        ],
        metrics: {
            totalTasks: 892,
            successRate: 0.94,
            avgResponseTime: 5.7,
            avgConfidence: 0.86,
        },
        capabilities: ['Web scraping', 'PDF extraction', 'API integration', 'Rate limiting'],
    },
    {
        id: 'agent-3',
        name: 'Entity Linker',
        type: 'analyst',
        status: 'idle',
        description: 'Identifies and links related entities across records',
        recentTasks: [
            { id: 't4', name: 'Link corporate owners', status: 'success', duration: 3200, confidence: 0.89 },
            { id: 't5', name: 'Resolve name variations', status: 'success', duration: 1800, confidence: 0.94 },
        ],
        metrics: {
            totalTasks: 2341,
            successRate: 0.91,
            avgResponseTime: 1.8,
            avgConfidence: 0.87,
        },
        capabilities: ['Entity resolution', 'Graph analysis', 'Pattern matching', 'Confidence scoring'],
    },
    {
        id: 'agent-4',
        name: 'Quality Validator',
        type: 'validator',
        status: 'success',
        description: 'Validates data quality and flags anomalies',
        recentTasks: [
            { id: 't6', name: 'Validate batch #1246', status: 'success', duration: 890, confidence: 0.99 },
            { id: 't7', name: 'Flag duplicate records', status: 'success', duration: 450, confidence: 0.96 },
        ],
        metrics: {
            totalTasks: 3892,
            successRate: 0.99,
            avgResponseTime: 0.8,
            avgConfidence: 0.94,
        },
        capabilities: ['Data validation', 'Anomaly detection', 'Duplicate checking', 'Schema validation'],
    },
];

// =============================================================================
// COMPONENTS
// =============================================================================

interface AgentCardProps {
    agent: Agent;
    expanded: boolean;
    onToggle: () => void;
    onClick?: () => void;
}

function AgentCard({ agent, expanded, onToggle, onClick }: AgentCardProps) {
    const theme = useTheme();
    const statusColor = statusColors[agent.status];

    return (
        <Card
            sx={{
                position: 'relative',
                overflow: 'visible',
                cursor: onClick ? 'pointer' : 'default',
                transition: 'all 0.2s ease',
                border: `1px solid ${alpha(statusColor, 0.3)}`,
                '&:hover': onClick ? {
                    boxShadow: theme.shadows[4],
                    borderColor: statusColor,
                } : {},
            }}
            onClick={onClick}
        >
            {/* Status indicator bar */}
            <Box
                sx={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: 4,
                    backgroundColor: statusColor,
                    borderRadius: '4px 4px 0 0',
                }}
            />

            <CardContent sx={{ pt: 3 }}>
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
                                    backgroundColor: statusColor,
                                    border: `2px solid ${theme.palette.background.paper}`,
                                    animation: agent.status === 'executing' || agent.status === 'thinking'
                                        ? 'pulse 1.5s infinite'
                                        : 'none',
                                    '@keyframes pulse': {
                                        '0%': { opacity: 1 },
                                        '50%': { opacity: 0.5 },
                                        '100%': { opacity: 1 },
                                    },
                                }}
                            />
                        }
                    >
                        <Avatar
                            sx={{
                                bgcolor: alpha(statusColor, 0.1),
                                color: statusColor,
                                width: 48,
                                height: 48,
                                fontSize: '1.5rem',
                            }}
                        >
                            {getAgentTypeIcon(agent.type)}
                        </Avatar>
                    </Badge>

                    <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="h6" fontWeight={600} noWrap>
                            {agent.name}
                        </Typography>
                        <Chip
                            size="small"
                            label={statusLabels[agent.status]}
                            icon={getStatusIcon(agent.status)}
                            sx={{
                                backgroundColor: alpha(statusColor, 0.1),
                                color: statusColor,
                                '& .MuiChip-icon': { color: statusColor },
                            }}
                        />
                    </Box>

                    <IconButton size="small" onClick={(e) => { e.stopPropagation(); onToggle(); }}>
                        {expanded ? <CollapseIcon /> : <ExpandIcon />}
                    </IconButton>
                </Box>

                {/* Current task */}
                {agent.currentTask && (
                    <Box
                        sx={{
                            p: 1.5,
                            mb: 2,
                            borderRadius: 1,
                            backgroundColor: alpha(statusColor, 0.05),
                            border: `1px solid ${alpha(statusColor, 0.2)}`,
                        }}
                    >
                        <Typography variant="caption" color="text.secondary">
                            Current Task
                        </Typography>
                        <Typography variant="body2" fontWeight={500}>
                            {agent.currentTask.name}
                        </Typography>
                        {agent.currentTask.confidence !== undefined && (
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                                <Typography variant="caption" color="text.secondary">
                                    Confidence:
                                </Typography>
                                <LinearProgress
                                    variant="determinate"
                                    value={agent.currentTask.confidence * 100}
                                    sx={{
                                        flex: 1,
                                        height: 6,
                                        borderRadius: 3,
                                        backgroundColor: alpha(statusColor, 0.2),
                                        '& .MuiLinearProgress-bar': {
                                            backgroundColor: statusColor,
                                        },
                                    }}
                                />
                                <Typography variant="caption" fontWeight={600}>
                                    {Math.round(agent.currentTask.confidence * 100)}%
                                </Typography>
                            </Box>
                        )}
                    </Box>
                )}

                {/* Description */}
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {agent.description}
                </Typography>

                {/* Metrics - Mini */}
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <TrendingUpIcon fontSize="small" color="action" />
                        <Typography variant="caption">
                            {Math.round(agent.metrics.successRate * 100)}% success
                        </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <ScheduleIcon fontSize="small" color="action" />
                        <Typography variant="caption">
                            {agent.metrics.avgResponseTime}s avg
                        </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <MemoryIcon fontSize="small" color="action" />
                        <Typography variant="caption">
                            {agent.metrics.totalTasks.toLocaleString()} tasks
                        </Typography>
                    </Box>
                </Box>

                {/* Expanded content */}
                <Collapse in={expanded}>
                    <Divider sx={{ my: 2 }} />

                    {/* Capabilities */}
                    <Typography variant="subtitle2" gutterBottom>
                        Capabilities
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 2 }}>
                        {agent.capabilities.map((cap) => (
                            <Chip key={cap} label={cap} size="small" variant="outlined" />
                        ))}
                    </Box>

                    {/* Recent tasks */}
                    <Typography variant="subtitle2" gutterBottom>
                        Recent Tasks
                    </Typography>
                    <List dense disablePadding>
                        {agent.recentTasks.slice(0, 3).map((task) => (
                            <ListItem key={task.id} disableGutters>
                                <ListItemAvatar sx={{ minWidth: 36 }}>
                                    <Avatar
                                        sx={{
                                            width: 24,
                                            height: 24,
                                            backgroundColor: alpha(statusColors[task.status], 0.1),
                                            color: statusColors[task.status],
                                        }}
                                    >
                                        {getStatusIcon(task.status)}
                                    </Avatar>
                                </ListItemAvatar>
                                <ListItemText
                                    primary={task.name}
                                    secondary={task.duration ? `${(task.duration / 1000).toFixed(1)}s` : undefined}
                                    primaryTypographyProps={{ variant: 'body2' }}
                                    secondaryTypographyProps={{ variant: 'caption' }}
                                />
                                {task.confidence && (
                                    <Chip
                                        size="small"
                                        label={`${Math.round(task.confidence * 100)}%`}
                                        sx={{ ml: 1 }}
                                    />
                                )}
                            </ListItem>
                        ))}
                    </List>
                </Collapse>
            </CardContent>
        </Card>
    );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function AgentStatusDashboard({
    crewId,
    refreshInterval = 5000,
    onAgentClick,
}: AgentStatusDashboardProps) {
    const theme = useTheme();
    const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set());

    // Fetch crew status
    const { data: crewStatus, isLoading, refetch } = useQuery<CrewStatus>({
        queryKey: ['crew-status', crewId],
        queryFn: async () => {
            try {
                const response = await apiService.get(`/agents/crew/${crewId || 'default'}/status`);
                return response.data;
            } catch {
                // Return mock data for demo
                return {
                    id: 'crew-1',
                    name: 'DataGod Core Crew',
                    status: 'active' as const,
                    agents: mockAgents,
                    currentWorkflow: 'Batch Processing #1247',
                    startedAt: new Date(Date.now() - 3600000).toISOString(),
                    progress: 68,
                };
            }
        },
        refetchInterval: refreshInterval,
    });

    const toggleExpanded = (agentId: string) => {
        setExpandedAgents((prev) => {
            const next = new Set(prev);
            if (next.has(agentId)) {
                next.delete(agentId);
            } else {
                next.add(agentId);
            }
            return next;
        });
    };

    const agents = crewStatus?.agents || mockAgents;
    const activeAgents = agents.filter((a) => a.status !== 'idle').length;
    const avgConfidence = agents.reduce((sum, a) => sum + a.metrics.avgConfidence, 0) / agents.length;

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
                        Agent Status Dashboard
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        {crewStatus?.name || 'DataGod Core Crew'} • {crewStatus?.currentWorkflow || 'Idle'}
                    </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                    <Tooltip title="Refresh">
                        <IconButton onClick={() => refetch()} disabled={isLoading}>
                            <RefreshIcon />
                        </IconButton>
                    </Tooltip>
                </Box>
            </Box>

            {/* Overall progress */}
            {crewStatus?.progress !== undefined && (
                <Box sx={{ mb: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2" color="text.secondary">
                            Workflow Progress
                        </Typography>
                        <Typography variant="body2" fontWeight={600}>
                            {crewStatus.progress}%
                        </Typography>
                    </Box>
                    <LinearProgress
                        variant="determinate"
                        value={crewStatus.progress}
                        sx={{
                            height: 8,
                            borderRadius: 4,
                            backgroundColor: alpha(theme.palette.primary.main, 0.1),
                        }}
                    />
                </Box>
            )}

            {/* Quick stats */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha(theme.palette.primary.main, 0.05) }}>
                        <Typography variant="h4" fontWeight={700} color="primary">
                            {agents.length}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Total Agents
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha(statusColors.executing, 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: statusColors.executing }}>
                            {activeAgents}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Active Now
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha(statusColors.success, 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: statusColors.success }}>
                            {Math.round(avgConfidence * 100)}%
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Avg Confidence
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha(theme.palette.info.main, 0.05) }}>
                        <Typography variant="h4" fontWeight={700} color="info.main">
                            {agents.reduce((sum, a) => sum + a.metrics.totalTasks, 0).toLocaleString()}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Total Tasks
                        </Typography>
                    </Box>
                </Grid>
            </Grid>

            {/* Agent Cards */}
            <Grid container spacing={2}>
                {agents.map((agent) => (
                    <Grid item xs={12} md={6} key={agent.id}>
                        <AgentCard
                            agent={agent}
                            expanded={expandedAgents.has(agent.id)}
                            onToggle={() => toggleExpanded(agent.id)}
                            onClick={onAgentClick ? () => onAgentClick(agent) : undefined}
                        />
                    </Grid>
                ))}
            </Grid>
        </Paper>
    );
}
