'use client';

import React, { useState, useCallback } from 'react';
import {
    Box,
    Card,
    CardContent,
    Typography,
    ToggleButtonGroup,
    ToggleButton,
    Button,
    Divider,
    Paper,
    Chip,
    Alert,
    CircularProgress,
    Menu,
    MenuItem,
    ListItemIcon,
    ListItemText,
} from '@mui/material';
import {
    Person as ConsumerIcon,
    Engineering as OperatorIcon,
    Analytics as AnalystIcon,
    Gavel as AuditIcon,
    Download as DownloadIcon,
    PictureAsPdf as PdfIcon,
    Code as JsonIcon,
    Description as MarkdownIcon,
    Html as HtmlIcon,
} from '@mui/icons-material';

type ReportView = 'consumer' | 'operator' | 'analyst' | 'audit';
type ExportFormat = 'json' | 'html' | 'markdown' | 'pdf';

interface ReportSection {
    id: string;
    title: string;
    content: Record<string, any>;
    description?: string;
    order: number;
}

interface ReportData {
    report_id: string;
    title: string;
    view: string;
    generated_at: string;
    sections: ReportSection[];
    disclaimer: string;
    footer: Record<string, any>;
}

interface ReportViewerProps {
    data: Record<string, any>;
    title?: string;
    initialView?: ReportView;
}

const viewConfig = {
    consumer: { label: 'Consumer', icon: ConsumerIcon, color: '#4caf50' },
    operator: { label: 'Operator', icon: OperatorIcon, color: '#2196f3' },
    analyst: { label: 'Analyst', icon: AnalystIcon, color: '#9c27b0' },
    audit: { label: 'Audit', icon: AuditIcon, color: '#ff9800' },
};

export function ReportViewer({ data, title, initialView = 'consumer' }: ReportViewerProps) {
    const [view, setView] = useState<ReportView>(initialView);
    const [report, setReport] = useState<ReportData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [exportAnchor, setExportAnchor] = useState<null | HTMLElement>(null);

    // Generate report
    const generateReport = useCallback(async (selectedView: ReportView) => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch('/api/v2/reports/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    data,
                    view: selectedView,
                    title: title || 'Research Report',
                }),
            });
            if (!response.ok) throw new Error('Failed to generate report');
            const reportData = await response.json();
            setReport(reportData);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to generate report');
        } finally {
            setLoading(false);
        }
    }, [data, title]);

    // Handle view change
    const handleViewChange = (_: React.MouseEvent<HTMLElement>, newView: ReportView | null) => {
        if (newView) {
            setView(newView);
            generateReport(newView);
        }
    };

    // Export report
    const handleExport = async (format: ExportFormat) => {
        if (!report) return;
        setExportAnchor(null);

        try {
            const response = await fetch(`/api/v2/reports/${report.report_id}/export?format=${format}`);
            if (!response.ok) throw new Error('Failed to export report');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `report_${report.report_id}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to export report');
        }
    };

    // Render section based on view
    const renderSection = (section: ReportSection) => {
        const ViewIcon = viewConfig[view].icon;

        return (
            <Paper key={section.id} sx={{ p: 3, mb: 2 }} elevation={1}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6" sx={{ flexGrow: 1 }}>{section.title}</Typography>
                    <Chip
                        label={view}
                        size="small"
                        sx={{ bgcolor: viewConfig[view].color, color: 'white' }}
                    />
                </Box>

                {section.description && (
                    <Typography color="text.secondary" sx={{ mb: 2 }}>
                        {section.description}
                    </Typography>
                )}

                <Divider sx={{ my: 2 }} />

                {/* Render content based on view type */}
                {view === 'consumer' ? (
                    <Box>
                        {Object.entries(section.content).map(([key, value]) => {
                            if (typeof value === 'object') return null;
                            return (
                                <Typography key={key} sx={{ mb: 1 }}>
                                    <strong>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong>{' '}
                                    {String(value)}
                                </Typography>
                            );
                        })}
                    </Box>
                ) : view === 'operator' ? (
                    <Box>
                        {Object.entries(section.content).map(([key, value]) => (
                            <Box key={key} sx={{ mb: 1 }}>
                                <Typography variant="subtitle2" color="primary">
                                    {key.replace(/_/g, ' ')}
                                </Typography>
                                <Typography variant="body2">
                                    {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                                </Typography>
                            </Box>
                        ))}
                    </Box>
                ) : (
                    <Box
                        component="pre"
                        sx={{
                            bgcolor: 'grey.100',
                            p: 2,
                            borderRadius: 1,
                            overflow: 'auto',
                            fontSize: '0.875rem',
                        }}
                    >
                        {JSON.stringify(section.content, null, 2)}
                    </Box>
                )}
            </Paper>
        );
    };

    // Initial load
    React.useEffect(() => {
        if (data && Object.keys(data).length > 0) {
            generateReport(view);
        }
    }, []);

    return (
        <Card sx={{ maxWidth: 900, mx: 'auto', mt: 4 }}>
            <CardContent>
                {/* Header */}
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
                    <Typography variant="h5" sx={{ flexGrow: 1 }}>
                        {report?.title || title || 'Report'}
                    </Typography>

                    <Button
                        variant="outlined"
                        startIcon={<DownloadIcon />}
                        onClick={(e) => setExportAnchor(e.currentTarget)}
                        disabled={!report}
                    >
                        Export
                    </Button>

                    <Menu
                        anchorEl={exportAnchor}
                        open={Boolean(exportAnchor)}
                        onClose={() => setExportAnchor(null)}
                    >
                        <MenuItem onClick={() => handleExport('json')}>
                            <ListItemIcon><JsonIcon /></ListItemIcon>
                            <ListItemText>JSON</ListItemText>
                        </MenuItem>
                        <MenuItem onClick={() => handleExport('html')}>
                            <ListItemIcon><HtmlIcon /></ListItemIcon>
                            <ListItemText>HTML</ListItemText>
                        </MenuItem>
                        <MenuItem onClick={() => handleExport('markdown')}>
                            <ListItemIcon><MarkdownIcon /></ListItemIcon>
                            <ListItemText>Markdown</ListItemText>
                        </MenuItem>
                        <MenuItem onClick={() => handleExport('pdf')}>
                            <ListItemIcon><PdfIcon /></ListItemIcon>
                            <ListItemText>PDF</ListItemText>
                        </MenuItem>
                    </Menu>
                </Box>

                {/* View Toggle */}
                <ToggleButtonGroup
                    value={view}
                    exclusive
                    onChange={handleViewChange}
                    sx={{ mb: 3, display: 'flex', flexWrap: 'wrap' }}
                >
                    {(Object.keys(viewConfig) as ReportView[]).map((v) => {
                        const config = viewConfig[v];
                        const Icon = config.icon;
                        return (
                            <ToggleButton key={v} value={v} sx={{ px: 3 }}>
                                <Icon sx={{ mr: 1, color: view === v ? config.color : 'inherit' }} />
                                {config.label}
                            </ToggleButton>
                        );
                    })}
                </ToggleButtonGroup>

                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

                {loading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                        <CircularProgress />
                    </Box>
                ) : report ? (
                    <>
                        {/* Disclaimer */}
                        {report.disclaimer && (
                            <Alert severity="info" sx={{ mb: 3 }}>
                                {report.disclaimer}
                            </Alert>
                        )}

                        {/* Sections */}
                        {report.sections.map(renderSection)}

                        {/* Footer */}
                        <Box sx={{ mt: 3, pt: 2, borderTop: 1, borderColor: 'divider' }}>
                            <Typography variant="caption" color="text.secondary">
                                Generated: {new Date(report.generated_at).toLocaleString()}
                            </Typography>
                            {report.footer?.verify_note && (
                                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                                    {report.footer.verify_note}
                                </Typography>
                            )}
                        </Box>
                    </>
                ) : (
                    <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                        No report data available
                    </Typography>
                )}
            </CardContent>
        </Card>
    );
}

export default ReportViewer;
