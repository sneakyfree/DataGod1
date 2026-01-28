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
    ListItemText,
    ListItemIcon,
    Divider,
    Button,
    useTheme,
    alpha,
    Avatar,
    Badge,
    Collapse,
} from '@mui/material';
import {
    PlayArrow as PlayIcon,
    Pause as PauseIcon,
    Stop as StopIcon,
    Refresh as RefreshIcon,
    CheckCircle as CompleteIcon,
    Error as ErrorIcon,
    HourglassEmpty as QueuedIcon,
    Speed as RunningIcon,
    Timeline as EpochIcon,
    Memory as MemoryIcon,
    Storage as DataIcon,
    Schedule as TimeIcon,
    ExpandMore as ExpandIcon,
    ExpandLess as CollapseIcon,
    TrendingDown as LossIcon,
    TrendingUp as AccuracyIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';

// =============================================================================
// TYPES
// =============================================================================

export type TrainingStatus = 'queued' | 'running' | 'completed' | 'failed' | 'paused' | 'cancelled';

export interface EpochMetrics {
    epoch: number;
    trainLoss: number;
    valLoss: number;
    trainAccuracy: number;
    valAccuracy: number;
    duration: number;
}

export interface TrainingJob {
    id: string;
    modelName: string;
    modelVersion: string;
    status: TrainingStatus;
    startedAt?: string;
    completedAt?: string;
    currentEpoch: number;
    totalEpochs: number;
    progress: number;
    trainingSamples: number;
    validationSamples: number;
    batchSize: number;
    learningRate: number;
    gpuUsage: number;
    memoryUsage: number;
    eta?: string;
    epochHistory: EpochMetrics[];
    errorMessage?: string;
}

interface TrainingStatusMonitorProps {
    onJobSelect?: (job: TrainingJob) => void;
}

// =============================================================================
// HELPERS
// =============================================================================

const statusConfig: Record<TrainingStatus, { color: string; label: string; icon: React.ReactNode }> = {
    queued: { color: '#9e9e9e', label: 'Queued', icon: <QueuedIcon /> },
    running: { color: '#2196f3', label: 'Running', icon: <RunningIcon /> },
    completed: { color: '#4caf50', label: 'Completed', icon: <CompleteIcon /> },
    failed: { color: '#f44336', label: 'Failed', icon: <ErrorIcon /> },
    paused: { color: '#ff9800', label: 'Paused', icon: <PauseIcon /> },
    cancelled: { color: '#9e9e9e', label: 'Cancelled', icon: <StopIcon /> },
};

// =============================================================================
// MOCK DATA
// =============================================================================

const mockTrainingJobs: TrainingJob[] = [
    {
        id: 'job-1',
        modelName: 'Entity Linker',
        modelVersion: '2.5.0',
        status: 'running',
        startedAt: new Date(Date.now() - 3600000).toISOString(),
        currentEpoch: 45,
        totalEpochs: 100,
        progress: 45,
        trainingSamples: 150000,
        validationSamples: 30000,
        batchSize: 256,
        learningRate: 0.001,
        gpuUsage: 87,
        memoryUsage: 12800,
        eta: '1h 15m',
        epochHistory: [
            { epoch: 43, trainLoss: 0.142, valLoss: 0.158, trainAccuracy: 0.932, valAccuracy: 0.918, duration: 42 },
            { epoch: 44, trainLoss: 0.138, valLoss: 0.154, trainAccuracy: 0.935, valAccuracy: 0.921, duration: 41 },
            { epoch: 45, trainLoss: 0.135, valLoss: 0.151, trainAccuracy: 0.938, valAccuracy: 0.924, duration: 43 },
        ],
    },
    {
        id: 'job-2',
        modelName: 'Document Classifier',
        modelVersion: '3.2.0',
        status: 'running',
        startedAt: new Date(Date.now() - 7200000).toISOString(),
        currentEpoch: 78,
        totalEpochs: 80,
        progress: 97.5,
        trainingSamples: 80000,
        validationSamples: 16000,
        batchSize: 128,
        learningRate: 0.0005,
        gpuUsage: 92,
        memoryUsage: 15400,
        eta: '5m',
        epochHistory: [
            { epoch: 76, trainLoss: 0.089, valLoss: 0.112, trainAccuracy: 0.961, valAccuracy: 0.948, duration: 65 },
            { epoch: 77, trainLoss: 0.087, valLoss: 0.110, trainAccuracy: 0.963, valAccuracy: 0.950, duration: 64 },
            { epoch: 78, trainLoss: 0.085, valLoss: 0.108, trainAccuracy: 0.965, valAccuracy: 0.952, duration: 66 },
        ],
    },
    {
        id: 'job-3',
        modelName: 'Fraud Detector',
        modelVersion: '1.3.0',
        status: 'queued',
        totalEpochs: 50,
        currentEpoch: 0,
        progress: 0,
        trainingSamples: 60000,
        validationSamples: 12000,
        batchSize: 64,
        learningRate: 0.0001,
        gpuUsage: 0,
        memoryUsage: 0,
        epochHistory: [],
    },
    {
        id: 'job-4',
        modelName: 'Property Valuation',
        modelVersion: '1.9.0',
        status: 'completed',
        startedAt: new Date(Date.now() - 86400000).toISOString(),
        completedAt: new Date(Date.now() - 82800000).toISOString(),
        currentEpoch: 75,
        totalEpochs: 75,
        progress: 100,
        trainingSamples: 280000,
        validationSamples: 56000,
        batchSize: 512,
        learningRate: 0.002,
        gpuUsage: 0,
        memoryUsage: 0,
        epochHistory: [
            { epoch: 73, trainLoss: 0.052, valLoss: 0.068, trainAccuracy: 0.978, valAccuracy: 0.965, duration: 120 },
            { epoch: 74, trainLoss: 0.051, valLoss: 0.067, trainAccuracy: 0.979, valAccuracy: 0.966, duration: 118 },
            { epoch: 75, trainLoss: 0.050, valLoss: 0.066, trainAccuracy: 0.980, valAccuracy: 0.967, duration: 121 },
        ],
    },
];

// =============================================================================
// JOB CARD COMPONENT
// =============================================================================

interface JobCardProps {
    job: TrainingJob;
    expanded: boolean;
    onToggle: () => void;
    onClick?: () => void;
}

function JobCard({ job, expanded, onToggle, onClick }: JobCardProps) {
    const theme = useTheme();
    const status = statusConfig[job.status];

    return (
        <Card
            sx={{
                border: `1px solid ${alpha(status.color, 0.3)}`,
                transition: 'all 0.2s ease',
                '&:hover': {
                    boxShadow: theme.shadows[4],
                    borderColor: status.color,
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
                            job.status === 'running' ? (
                                <Box
                                    sx={{
                                        width: 12,
                                        height: 12,
                                        borderRadius: '50%',
                                        backgroundColor: status.color,
                                        border: `2px solid ${theme.palette.background.paper}`,
                                        animation: 'pulse 1.5s infinite',
                                        '@keyframes pulse': {
                                            '0%': { opacity: 1 },
                                            '50%': { opacity: 0.5 },
                                            '100%': { opacity: 1 },
                                        },
                                    }}
                                />
                            ) : null
                        }
                    >
                        <Avatar
                            sx={{
                                bgcolor: alpha(status.color, 0.1),
                                color: status.color,
                            }}
                        >
                            {status.icon}
                        </Avatar>
                    </Badge>

                    <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="subtitle1" fontWeight={600}>
                            {job.modelName} v{job.modelVersion}
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

                    <Box sx={{ textAlign: 'right' }}>
                        {job.status === 'running' && job.eta && (
                            <Typography variant="caption" color="text.secondary">
                                ETA: {job.eta}
                            </Typography>
                        )}
                        <IconButton size="small" onClick={onToggle}>
                            {expanded ? <CollapseIcon /> : <ExpandIcon />}
                        </IconButton>
                    </Box>
                </Box>

                {/* Progress */}
                <Box sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="body2" color="text.secondary">
                            Epoch {job.currentEpoch} / {job.totalEpochs}
                        </Typography>
                        <Typography variant="body2" fontWeight={600}>
                            {job.progress.toFixed(1)}%
                        </Typography>
                    </Box>
                    <LinearProgress
                        variant="determinate"
                        value={job.progress}
                        sx={{
                            height: 8,
                            borderRadius: 4,
                            backgroundColor: alpha(status.color, 0.1),
                            '& .MuiLinearProgress-bar': {
                                backgroundColor: status.color,
                                borderRadius: 4,
                            },
                        }}
                    />
                </Box>

                {/* Quick stats */}
                {job.status === 'running' && (
                    <Grid container spacing={1}>
                        <Grid item xs={4}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <MemoryIcon fontSize="small" color="action" />
                                <Typography variant="caption">GPU: {job.gpuUsage}%</Typography>
                            </Box>
                        </Grid>
                        <Grid item xs={4}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <DataIcon fontSize="small" color="action" />
                                <Typography variant="caption">{(job.memoryUsage / 1024).toFixed(1)} GB</Typography>
                            </Box>
                        </Grid>
                        <Grid item xs={4}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <TimeIcon fontSize="small" color="action" />
                                <Typography variant="caption">
                                    {job.startedAt && new Date(job.startedAt).toLocaleTimeString()}
                                </Typography>
                            </Box>
                        </Grid>
                    </Grid>
                )}

                {/* Expanded content */}
                <Collapse in={expanded}>
                    <Divider sx={{ my: 2 }} />

                    {/* Training config */}
                    <Typography variant="subtitle2" gutterBottom>
                        Training Configuration
                    </Typography>
                    <Grid container spacing={1} sx={{ mb: 2 }}>
                        <Grid item xs={6}>
                            <Typography variant="caption" color="text.secondary">
                                Training Samples: {job.trainingSamples.toLocaleString()}
                            </Typography>
                        </Grid>
                        <Grid item xs={6}>
                            <Typography variant="caption" color="text.secondary">
                                Validation Samples: {job.validationSamples.toLocaleString()}
                            </Typography>
                        </Grid>
                        <Grid item xs={6}>
                            <Typography variant="caption" color="text.secondary">
                                Batch Size: {job.batchSize}
                            </Typography>
                        </Grid>
                        <Grid item xs={6}>
                            <Typography variant="caption" color="text.secondary">
                                Learning Rate: {job.learningRate}
                            </Typography>
                        </Grid>
                    </Grid>

                    {/* Epoch history */}
                    {job.epochHistory.length > 0 && (
                        <>
                            <Typography variant="subtitle2" gutterBottom>
                                Recent Epochs
                            </Typography>
                            <List dense disablePadding>
                                {job.epochHistory.slice(-3).map((epoch) => (
                                    <ListItem key={epoch.epoch} disableGutters>
                                        <ListItemIcon sx={{ minWidth: 32 }}>
                                            <Chip size="small" label={epoch.epoch} variant="outlined" />
                                        </ListItemIcon>
                                        <ListItemText
                                            primary={
                                                <Box sx={{ display: 'flex', gap: 2 }}>
                                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                        <LossIcon fontSize="small" color="error" />
                                                        <Typography variant="caption">
                                                            Loss: {epoch.trainLoss.toFixed(4)} / {epoch.valLoss.toFixed(4)}
                                                        </Typography>
                                                    </Box>
                                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                        <AccuracyIcon fontSize="small" color="success" />
                                                        <Typography variant="caption">
                                                            Acc: {(epoch.trainAccuracy * 100).toFixed(1)}% / {(epoch.valAccuracy * 100).toFixed(1)}%
                                                        </Typography>
                                                    </Box>
                                                </Box>
                                            }
                                            secondary={`${epoch.duration}s`}
                                        />
                                    </ListItem>
                                ))}
                            </List>
                        </>
                    )}

                    {/* Error message */}
                    {job.status === 'failed' && job.errorMessage && (
                        <Box
                            sx={{
                                p: 1.5,
                                borderRadius: 1,
                                backgroundColor: alpha(theme.palette.error.main, 0.1),
                                border: `1px solid ${alpha(theme.palette.error.main, 0.3)}`,
                            }}
                        >
                            <Typography variant="caption" color="error">
                                {job.errorMessage}
                            </Typography>
                        </Box>
                    )}

                    {/* Actions */}
                    {(job.status === 'running' || job.status === 'queued') && (
                        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                            {job.status === 'running' && (
                                <>
                                    <Button size="small" variant="outlined" startIcon={<PauseIcon />}>
                                        Pause
                                    </Button>
                                    <Button size="small" variant="outlined" color="error" startIcon={<StopIcon />}>
                                        Cancel
                                    </Button>
                                </>
                            )}
                            {job.status === 'queued' && (
                                <Button size="small" variant="outlined" color="error" startIcon={<StopIcon />}>
                                    Cancel
                                </Button>
                            )}
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

export default function TrainingStatusMonitor({
    onJobSelect,
}: TrainingStatusMonitorProps) {
    const theme = useTheme();
    const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set());

    // Fetch training jobs
    const { data: jobs = mockTrainingJobs, isLoading, refetch } = useQuery<TrainingJob[]>({
        queryKey: ['training-jobs'],
        queryFn: async () => {
            try {
                const response = await apiService.get('/ml/training/jobs');
                return response.data;
            } catch {
                return mockTrainingJobs;
            }
        },
        refetchInterval: 5000, // Auto-refresh every 5 seconds for running jobs
    });

    const toggleExpanded = (jobId: string) => {
        setExpandedJobs((prev) => {
            const next = new Set(prev);
            if (next.has(jobId)) {
                next.delete(jobId);
            } else {
                next.add(jobId);
            }
            return next;
        });
    };

    // Calculate stats
    const runningJobs = jobs.filter((j) => j.status === 'running').length;
    const queuedJobs = jobs.filter((j) => j.status === 'queued').length;
    const completedToday = jobs.filter(
        (j) => j.status === 'completed' && j.completedAt &&
            new Date(j.completedAt).toDateString() === new Date().toDateString()
    ).length;
    const totalGpuUsage = jobs.filter((j) => j.status === 'running')
        .reduce((sum, j) => sum + j.gpuUsage, 0);

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
                        Training Status Monitor
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Monitor active training jobs and resource usage
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
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#2196f3', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#2196f3' }}>
                            {runningJobs}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Running
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#9e9e9e', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} color="text.secondary">
                            {queuedJobs}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Queued
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#4caf50', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#4caf50' }}>
                            {completedToday}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Completed Today
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#ff9800', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#ff9800' }}>
                            {runningJobs > 0 ? Math.round(totalGpuUsage / runningJobs) : 0}%
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Avg GPU Usage
                        </Typography>
                    </Box>
                </Grid>
            </Grid>

            {/* Job list */}
            <Grid container spacing={2}>
                {jobs.map((job) => (
                    <Grid item xs={12} md={6} key={job.id}>
                        <JobCard
                            job={job}
                            expanded={expandedJobs.has(job.id)}
                            onToggle={() => toggleExpanded(job.id)}
                            onClick={onJobSelect ? () => onJobSelect(job) : undefined}
                        />
                    </Grid>
                ))}
                {jobs.length === 0 && (
                    <Grid item xs={12}>
                        <Box sx={{ textAlign: 'center', py: 8 }}>
                            <EpochIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
                            <Typography variant="h6" color="text.secondary">
                                No training jobs
                            </Typography>
                            <Typography variant="body2" color="text.disabled">
                                Start a new training job to see it here
                            </Typography>
                        </Box>
                    </Grid>
                )}
            </Grid>
        </Paper>
    );
}
