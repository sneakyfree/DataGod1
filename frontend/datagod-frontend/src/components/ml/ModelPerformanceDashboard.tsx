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
    Tab,
    Tabs,
    Avatar,
} from '@mui/material';
import {
    TrendingUp as AccuracyIcon,
    Speed as SpeedIcon,
    Memory as MemoryIcon,
    Refresh as RefreshIcon,
    Timeline as TimelineIcon,
    Assessment as AssessmentIcon,
    CheckCircle as SuccessIcon,
    Warning as WarningIcon,
    Error as ErrorIcon,
    Psychology as ModelIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';
import ConfidenceScore from '../agent/ConfidenceScore';

// =============================================================================
// TYPES
// =============================================================================

export type ModelStatus = 'active' | 'training' | 'deprecated' | 'failed';

export interface ModelMetrics {
    accuracy: number;
    precision: number;
    recall: number;
    f1Score: number;
    auc: number;
    latencyMs: number;
    memoryMb: number;
    lastTrainedAt: string;
    trainingSamples: number;
    validationSamples: number;
}

export interface ConfusionMatrixData {
    truePositive: number;
    trueNegative: number;
    falsePositive: number;
    falseNegative: number;
}

export interface ModelInfo {
    id: string;
    name: string;
    version: string;
    type: 'classification' | 'regression' | 'clustering' | 'nlp';
    status: ModelStatus;
    description: string;
    metrics: ModelMetrics;
    confusionMatrix?: ConfusionMatrixData;
    features: string[];
    deployedAt?: string;
}

interface ModelPerformanceDashboardProps {
    onModelSelect?: (model: ModelInfo) => void;
}

// =============================================================================
// HELPERS
// =============================================================================

const statusConfig: Record<ModelStatus, { color: string; label: string; icon: React.ReactNode }> = {
    active: { color: '#4caf50', label: 'Active', icon: <SuccessIcon /> },
    training: { color: '#2196f3', label: 'Training', icon: <SpeedIcon /> },
    deprecated: { color: '#ff9800', label: 'Deprecated', icon: <WarningIcon /> },
    failed: { color: '#f44336', label: 'Failed', icon: <ErrorIcon /> },
};

const typeColors: Record<string, string> = {
    classification: '#9c27b0',
    regression: '#2196f3',
    clustering: '#ff9800',
    nlp: '#4caf50',
};

// =============================================================================
// MOCK DATA
// =============================================================================

const mockModels: ModelInfo[] = [
    {
        id: 'model-1',
        name: 'Entity Linker',
        version: '2.4.1',
        type: 'classification',
        status: 'active',
        description: 'Links related entities across public records using name matching and address similarity',
        metrics: {
            accuracy: 0.94,
            precision: 0.92,
            recall: 0.89,
            f1Score: 0.905,
            auc: 0.96,
            latencyMs: 45,
            memoryMb: 512,
            lastTrainedAt: new Date(Date.now() - 86400000 * 3).toISOString(),
            trainingSamples: 125000,
            validationSamples: 25000,
        },
        confusionMatrix: {
            truePositive: 8900,
            trueNegative: 14500,
            falsePositive: 750,
            falseNegative: 850,
        },
        features: ['name_similarity', 'address_match', 'tax_id_match', 'date_proximity', 'role_match'],
    },
    {
        id: 'model-2',
        name: 'Property Valuation',
        version: '1.8.3',
        type: 'regression',
        status: 'active',
        description: 'Predicts property values based on comparable sales and market conditions',
        metrics: {
            accuracy: 0.87,
            precision: 0.85,
            recall: 0.91,
            f1Score: 0.879,
            auc: 0.92,
            latencyMs: 120,
            memoryMb: 1024,
            lastTrainedAt: new Date(Date.now() - 86400000 * 7).toISOString(),
            trainingSamples: 250000,
            validationSamples: 50000,
        },
        features: ['sqft', 'bedrooms', 'bathrooms', 'lot_size', 'year_built', 'location_score', 'recent_sales'],
    },
    {
        id: 'model-3',
        name: 'Document Classifier',
        version: '3.1.0',
        type: 'nlp',
        status: 'training',
        description: 'Classifies legal documents into categories (deed, mortgage, lien, judgment)',
        metrics: {
            accuracy: 0.91,
            precision: 0.88,
            recall: 0.93,
            f1Score: 0.904,
            auc: 0.95,
            latencyMs: 85,
            memoryMb: 768,
            lastTrainedAt: new Date(Date.now() - 86400000).toISOString(),
            trainingSamples: 75000,
            validationSamples: 15000,
        },
        features: ['document_text', 'title_keywords', 'party_names', 'document_type_hints'],
    },
    {
        id: 'model-4',
        name: 'Fraud Detector',
        version: '1.2.0',
        type: 'classification',
        status: 'active',
        description: 'Detects potentially fraudulent ownership transfers and suspicious patterns',
        metrics: {
            accuracy: 0.96,
            precision: 0.94,
            recall: 0.85,
            f1Score: 0.893,
            auc: 0.98,
            latencyMs: 35,
            memoryMb: 256,
            lastTrainedAt: new Date(Date.now() - 86400000 * 14).toISOString(),
            trainingSamples: 50000,
            validationSamples: 10000,
        },
        confusionMatrix: {
            truePositive: 850,
            trueNegative: 8800,
            falsePositive: 55,
            falseNegative: 145,
        },
        features: ['transfer_frequency', 'price_deviation', 'party_history', 'timing_pattern', 'geographic_anomaly'],
    },
];

// =============================================================================
// MODEL CARD COMPONENT
// =============================================================================

interface ModelCardProps {
    model: ModelInfo;
    selected: boolean;
    onClick: () => void;
}

function ModelCard({ model, selected, onClick }: ModelCardProps) {
    const theme = useTheme();
    const status = statusConfig[model.status];

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
                {/* Header */}
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 2 }}>
                    <Avatar
                        sx={{
                            bgcolor: alpha(typeColors[model.type], 0.1),
                            color: typeColors[model.type],
                        }}
                    >
                        <ModelIcon />
                    </Avatar>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="subtitle1" fontWeight={600} noWrap>
                            {model.name}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                            <Chip
                                size="small"
                                label={`v${model.version}`}
                                variant="outlined"
                            />
                            <Chip
                                size="small"
                                label={model.type}
                                sx={{
                                    backgroundColor: alpha(typeColors[model.type], 0.1),
                                    color: typeColors[model.type],
                                }}
                            />
                        </Box>
                    </Box>
                    <Chip
                        size="small"
                        icon={status.icon as React.ReactElement}
                        label={status.label}
                        sx={{
                            backgroundColor: alpha(status.color, 0.1),
                            color: status.color,
                            '& .MuiChip-icon': { color: status.color },
                        }}
                    />
                </Box>

                {/* Metrics preview */}
                <Grid container spacing={1}>
                    <Grid item xs={4}>
                        <Box sx={{ textAlign: 'center' }}>
                            <Typography variant="h6" fontWeight={700} color="primary">
                                {Math.round(model.metrics.accuracy * 100)}%
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Accuracy
                            </Typography>
                        </Box>
                    </Grid>
                    <Grid item xs={4}>
                        <Box sx={{ textAlign: 'center' }}>
                            <Typography variant="h6" fontWeight={700} color="success.main">
                                {model.metrics.f1Score.toFixed(2)}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                F1 Score
                            </Typography>
                        </Box>
                    </Grid>
                    <Grid item xs={4}>
                        <Box sx={{ textAlign: 'center' }}>
                            <Typography variant="h6" fontWeight={700} color="info.main">
                                {model.metrics.latencyMs}ms
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Latency
                            </Typography>
                        </Box>
                    </Grid>
                </Grid>
            </CardContent>
        </Card>
    );
}

// =============================================================================
// METRICS DETAIL COMPONENT
// =============================================================================

interface MetricsDetailProps {
    model: ModelInfo;
}

function MetricsDetail({ model }: MetricsDetailProps) {
    const theme = useTheme();

    const metrics = [
        { label: 'Accuracy', value: model.metrics.accuracy, format: 'percent' },
        { label: 'Precision', value: model.metrics.precision, format: 'percent' },
        { label: 'Recall', value: model.metrics.recall, format: 'percent' },
        { label: 'F1 Score', value: model.metrics.f1Score, format: 'decimal' },
        { label: 'AUC-ROC', value: model.metrics.auc, format: 'decimal' },
    ];

    return (
        <Paper sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight={600} gutterBottom>
                {model.name} - Detailed Metrics
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                {model.description}
            </Typography>

            {/* Performance metrics */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
                {metrics.map((metric) => (
                    <Grid item xs={6} sm={4} md={2.4} key={metric.label}>
                        <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha(theme.palette.primary.main, 0.05) }}>
                            <Typography variant="h5" fontWeight={700} color="primary">
                                {metric.format === 'percent'
                                    ? `${Math.round(metric.value * 100)}%`
                                    : metric.value.toFixed(3)}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                {metric.label}
                            </Typography>
                        </Box>
                    </Grid>
                ))}
            </Grid>

            {/* System metrics */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <SpeedIcon color="action" />
                        <Box>
                            <Typography variant="body2" fontWeight={600}>
                                {model.metrics.latencyMs}ms
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Avg Latency
                            </Typography>
                        </Box>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <MemoryIcon color="action" />
                        <Box>
                            <Typography variant="body2" fontWeight={600}>
                                {model.metrics.memoryMb} MB
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Memory Usage
                            </Typography>
                        </Box>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <AssessmentIcon color="action" />
                        <Box>
                            <Typography variant="body2" fontWeight={600}>
                                {model.metrics.trainingSamples.toLocaleString()}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Training Samples
                            </Typography>
                        </Box>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <TimelineIcon color="action" />
                        <Box>
                            <Typography variant="body2" fontWeight={600}>
                                {new Date(model.metrics.lastTrainedAt).toLocaleDateString()}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Last Trained
                            </Typography>
                        </Box>
                    </Box>
                </Grid>
            </Grid>

            {/* Confusion Matrix */}
            {model.confusionMatrix && (
                <Box sx={{ mb: 4 }}>
                    <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                        Confusion Matrix
                    </Typography>
                    <Grid container spacing={1} sx={{ maxWidth: 300 }}>
                        <Grid item xs={6}>
                            <Box sx={{ p: 2, textAlign: 'center', backgroundColor: alpha('#4caf50', 0.1), borderRadius: 1 }}>
                                <Typography variant="h6" fontWeight={700} color="success.main">
                                    {model.confusionMatrix.truePositive.toLocaleString()}
                                </Typography>
                                <Typography variant="caption">True Positive</Typography>
                            </Box>
                        </Grid>
                        <Grid item xs={6}>
                            <Box sx={{ p: 2, textAlign: 'center', backgroundColor: alpha('#f44336', 0.1), borderRadius: 1 }}>
                                <Typography variant="h6" fontWeight={700} color="error.main">
                                    {model.confusionMatrix.falsePositive.toLocaleString()}
                                </Typography>
                                <Typography variant="caption">False Positive</Typography>
                            </Box>
                        </Grid>
                        <Grid item xs={6}>
                            <Box sx={{ p: 2, textAlign: 'center', backgroundColor: alpha('#f44336', 0.1), borderRadius: 1 }}>
                                <Typography variant="h6" fontWeight={700} color="error.main">
                                    {model.confusionMatrix.falseNegative.toLocaleString()}
                                </Typography>
                                <Typography variant="caption">False Negative</Typography>
                            </Box>
                        </Grid>
                        <Grid item xs={6}>
                            <Box sx={{ p: 2, textAlign: 'center', backgroundColor: alpha('#4caf50', 0.1), borderRadius: 1 }}>
                                <Typography variant="h6" fontWeight={700} color="success.main">
                                    {model.confusionMatrix.trueNegative.toLocaleString()}
                                </Typography>
                                <Typography variant="caption">True Negative</Typography>
                            </Box>
                        </Grid>
                    </Grid>
                </Box>
            )}

            {/* Features */}
            <Box>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Input Features
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {model.features.map((feature) => (
                        <Chip key={feature} label={feature} size="small" variant="outlined" />
                    ))}
                </Box>
            </Box>
        </Paper>
    );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function ModelPerformanceDashboard({
    onModelSelect,
}: ModelPerformanceDashboardProps) {
    const theme = useTheme();
    const [selectedModel, setSelectedModel] = useState<ModelInfo | null>(mockModels[0]);
    const [filterType, setFilterType] = useState<string>('all');
    const [filterStatus, setFilterStatus] = useState<string>('all');

    // Fetch models
    const { data: models = mockModels, isLoading, refetch } = useQuery<ModelInfo[]>({
        queryKey: ['ml-models'],
        queryFn: async () => {
            try {
                const response = await apiService.get('/ml/models');
                return response.data;
            } catch {
                return mockModels;
            }
        },
    });

    // Filter models
    const filteredModels = models.filter((m) => {
        if (filterType !== 'all' && m.type !== filterType) return false;
        if (filterStatus !== 'all' && m.status !== filterStatus) return false;
        return true;
    });

    const handleModelClick = (model: ModelInfo) => {
        setSelectedModel(model);
        onModelSelect?.(model);
    };

    // Calculate aggregate stats
    const activeModels = models.filter((m) => m.status === 'active').length;
    const avgAccuracy = models.reduce((sum, m) => sum + m.metrics.accuracy, 0) / models.length;
    const avgLatency = models.reduce((sum, m) => sum + m.metrics.latencyMs, 0) / models.length;

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
                        Model Performance Dashboard
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Monitor and analyze ML model performance metrics
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
                            {models.length}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Total Models
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#4caf50', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#4caf50' }}>
                            {activeModels}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Active Models
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#2196f3', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#2196f3' }}>
                            {Math.round(avgAccuracy * 100)}%
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Avg Accuracy
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#ff9800', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#ff9800' }}>
                            {Math.round(avgLatency)}ms
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Avg Latency
                        </Typography>
                    </Box>
                </Grid>
            </Grid>

            {/* Filters */}
            <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                <FormControl size="small" sx={{ minWidth: 120 }}>
                    <InputLabel>Type</InputLabel>
                    <Select
                        value={filterType}
                        label="Type"
                        onChange={(e) => setFilterType(e.target.value)}
                    >
                        <MenuItem value="all">All Types</MenuItem>
                        <MenuItem value="classification">Classification</MenuItem>
                        <MenuItem value="regression">Regression</MenuItem>
                        <MenuItem value="clustering">Clustering</MenuItem>
                        <MenuItem value="nlp">NLP</MenuItem>
                    </Select>
                </FormControl>
                <FormControl size="small" sx={{ minWidth: 120 }}>
                    <InputLabel>Status</InputLabel>
                    <Select
                        value={filterStatus}
                        label="Status"
                        onChange={(e) => setFilterStatus(e.target.value)}
                    >
                        <MenuItem value="all">All Status</MenuItem>
                        <MenuItem value="active">Active</MenuItem>
                        <MenuItem value="training">Training</MenuItem>
                        <MenuItem value="deprecated">Deprecated</MenuItem>
                        <MenuItem value="failed">Failed</MenuItem>
                    </Select>
                </FormControl>
            </Box>

            {/* Model grid + detail */}
            <Grid container spacing={3}>
                <Grid item xs={12} md={5}>
                    <Grid container spacing={2}>
                        {filteredModels.map((model) => (
                            <Grid item xs={12} key={model.id}>
                                <ModelCard
                                    model={model}
                                    selected={selectedModel?.id === model.id}
                                    onClick={() => handleModelClick(model)}
                                />
                            </Grid>
                        ))}
                    </Grid>
                </Grid>
                <Grid item xs={12} md={7}>
                    {selectedModel && <MetricsDetail model={selectedModel} />}
                </Grid>
            </Grid>
        </Paper>
    );
}
