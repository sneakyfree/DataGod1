'use client';

import React, { useState } from 'react';
import {
    Box,
    Paper,
    Typography,
    Grid,
    Chip,
    IconButton,
    Tooltip,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TablePagination,
    Avatar,
    Button,
    TextField,
    InputAdornment,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    useTheme,
    alpha,
    Collapse,
} from '@mui/material';
import {
    Refresh as RefreshIcon,
    Search as SearchIcon,
    Download as ExportIcon,
    FilterList as FilterIcon,
    ExpandMore as ExpandIcon,
    ExpandLess as CollapseIcon,
    Login as LoginIcon,
    Logout as LogoutIcon,
    Edit as EditIcon,
    Delete as DeleteIcon,
    Add as CreateIcon,
    Visibility as ViewIcon,
    Security as SecurityIcon,
    Settings as SettingsIcon,
    AdminPanelSettings as AdminIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';

// =============================================================================
// TYPES
// =============================================================================

export type AuditAction = 'login' | 'logout' | 'create' | 'read' | 'update' | 'delete' | 'export' | 'settings' | 'security';
export type AuditSeverity = 'info' | 'warning' | 'critical';

export interface AuditLogEntry {
    id: string;
    timestamp: string;
    userId: string;
    userEmail: string;
    userName: string;
    action: AuditAction;
    resource: string;
    resourceId?: string;
    details: Record<string, unknown>;
    ipAddress: string;
    userAgent: string;
    severity: AuditSeverity;
    success: boolean;
}

interface AuditLogViewerProps {
    onEntrySelect?: (entry: AuditLogEntry) => void;
}

// =============================================================================
// HELPERS
// =============================================================================

const actionConfig: Record<AuditAction, { color: string; label: string; icon: React.ReactNode }> = {
    login: { color: '#4caf50', label: 'Login', icon: <LoginIcon /> },
    logout: { color: '#9e9e9e', label: 'Logout', icon: <LogoutIcon /> },
    create: { color: '#2196f3', label: 'Create', icon: <CreateIcon /> },
    read: { color: '#00bcd4', label: 'View', icon: <ViewIcon /> },
    update: { color: '#ff9800', label: 'Update', icon: <EditIcon /> },
    delete: { color: '#f44336', label: 'Delete', icon: <DeleteIcon /> },
    export: { color: '#9c27b0', label: 'Export', icon: <ExportIcon /> },
    settings: { color: '#607d8b', label: 'Settings', icon: <SettingsIcon /> },
    security: { color: '#e91e63', label: 'Security', icon: <SecurityIcon /> },
};

const severityColors = {
    info: '#4caf50',
    warning: '#ff9800',
    critical: '#f44336',
};

// =============================================================================
// MOCK DATA
// =============================================================================

const mockAuditLogs: AuditLogEntry[] = [
    { id: '1', timestamp: new Date(Date.now() - 60000).toISOString(), userId: '1', userEmail: 'john.admin@company.com', userName: 'John Smith', action: 'login', resource: 'auth', severity: 'info', success: true, ipAddress: '192.168.1.100', userAgent: 'Chrome/120', details: { method: 'sso' } },
    { id: '2', timestamp: new Date(Date.now() - 300000).toISOString(), userId: '1', userEmail: 'john.admin@company.com', userName: 'John Smith', action: 'update', resource: 'user', resourceId: '5', severity: 'warning', success: true, ipAddress: '192.168.1.100', userAgent: 'Chrome/120', details: { changes: { role: 'analyst → manager' } } },
    { id: '3', timestamp: new Date(Date.now() - 600000).toISOString(), userId: '2', userEmail: 'sarah.manager@company.com', userName: 'Sarah Johnson', action: 'export', resource: 'records', severity: 'info', success: true, ipAddress: '192.168.1.101', userAgent: 'Firefox/121', details: { recordCount: 1500, format: 'csv' } },
    { id: '4', timestamp: new Date(Date.now() - 900000).toISOString(), userId: '3', userEmail: 'mike.analyst@company.com', userName: 'Mike Williams', action: 'read', resource: 'record', resourceId: '12345', severity: 'info', success: true, ipAddress: '192.168.1.102', userAgent: 'Chrome/120', details: {} },
    { id: '5', timestamp: new Date(Date.now() - 1200000).toISOString(), userId: '1', userEmail: 'john.admin@company.com', userName: 'John Smith', action: 'security', resource: 'mfa', severity: 'critical', success: true, ipAddress: '192.168.1.100', userAgent: 'Chrome/120', details: { operation: 'enabled' } },
    { id: '6', timestamp: new Date(Date.now() - 1800000).toISOString(), userId: '7', userEmail: 'chris.suspended@company.com', userName: 'Chris Wilson', action: 'login', resource: 'auth', severity: 'warning', success: false, ipAddress: '10.0.0.50', userAgent: 'Safari/17', details: { reason: 'account_suspended' } },
    { id: '7', timestamp: new Date(Date.now() - 3600000).toISOString(), userId: '2', userEmail: 'sarah.manager@company.com', userName: 'Sarah Johnson', action: 'create', resource: 'search', severity: 'info', success: true, ipAddress: '192.168.1.101', userAgent: 'Firefox/121', details: { query: 'Miami property records' } },
    { id: '8', timestamp: new Date(Date.now() - 7200000).toISOString(), userId: '1', userEmail: 'john.admin@company.com', userName: 'John Smith', action: 'delete', resource: 'user', resourceId: '8', severity: 'critical', success: true, ipAddress: '192.168.1.100', userAgent: 'Chrome/120', details: { deletedUser: 'temp.user@company.com' } },
];

// =============================================================================
// EXPANDED ROW COMPONENT
// =============================================================================

interface ExpandedRowProps {
    entry: AuditLogEntry;
}

function ExpandedRow({ entry }: ExpandedRowProps) {
    const theme = useTheme();

    return (
        <Box
            sx={{
                p: 2,
                backgroundColor: alpha(theme.palette.background.default, 0.5),
                borderTop: `1px solid ${theme.palette.divider}`,
            }}
        >
            <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>
                        Request Details
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        <Box>
                            <Typography variant="caption" color="text.secondary">IP Address</Typography>
                            <Typography variant="body2">{entry.ipAddress}</Typography>
                        </Box>
                        <Box>
                            <Typography variant="caption" color="text.secondary">User Agent</Typography>
                            <Typography variant="body2">{entry.userAgent}</Typography>
                        </Box>
                        {entry.resourceId && (
                            <Box>
                                <Typography variant="caption" color="text.secondary">Resource ID</Typography>
                                <Typography variant="body2"><code>{entry.resourceId}</code></Typography>
                            </Box>
                        )}
                    </Box>
                </Grid>
                <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>
                        Additional Details
                    </Typography>
                    <Box
                        component="pre"
                        sx={{
                            p: 1.5,
                            borderRadius: 1,
                            backgroundColor: theme.palette.mode === 'dark' ? alpha('#000', 0.3) : alpha('#000', 0.05),
                            fontSize: 12,
                            overflow: 'auto',
                            maxHeight: 120,
                        }}
                    >
                        {JSON.stringify(entry.details, null, 2)}
                    </Box>
                </Grid>
            </Grid>
        </Box>
    );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function AuditLogViewer({
    onEntrySelect,
}: AuditLogViewerProps) {
    const theme = useTheme();
    const [search, setSearch] = useState('');
    const [actionFilter, setActionFilter] = useState<string>('all');
    const [severityFilter, setSeverityFilter] = useState<string>('all');
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(10);
    const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

    // Fetch logs
    const { data: logs = mockAuditLogs, refetch, isLoading } = useQuery<AuditLogEntry[]>({
        queryKey: ['audit-logs'],
        queryFn: async () => {
            try {
                const response = await apiService.get('/audit/logs');
                return response.data;
            } catch {
                return mockAuditLogs;
            }
        },
    });

    // Filter logs
    const filteredLogs = logs.filter((log) => {
        if (actionFilter !== 'all' && log.action !== actionFilter) return false;
        if (severityFilter !== 'all' && log.severity !== severityFilter) return false;
        if (search) {
            const searchLower = search.toLowerCase();
            return (
                log.userEmail.toLowerCase().includes(searchLower) ||
                log.userName.toLowerCase().includes(searchLower) ||
                log.resource.toLowerCase().includes(searchLower)
            );
        }
        return true;
    });

    const toggleRow = (id: string) => {
        setExpandedRows((prev) => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    };

    // Stats
    const criticalCount = logs.filter((l) => l.severity === 'critical').length;
    const failedCount = logs.filter((l) => !l.success).length;

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
                        Audit Log
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Track all system activities and user actions
                    </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button variant="outlined" startIcon={<ExportIcon />}>
                        Export
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
                            {logs.length}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Total Events
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#4caf50', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#4caf50' }}>
                            {logs.filter((l) => l.action === 'login').length}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Logins (24h)
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#f44336', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#f44336' }}>
                            {criticalCount}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Critical
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#ff9800', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#ff9800' }}>
                            {failedCount}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Failed
                        </Typography>
                    </Box>
                </Grid>
            </Grid>

            {/* Filters */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                <TextField
                    size="small"
                    placeholder="Search logs..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    InputProps={{
                        startAdornment: (
                            <InputAdornment position="start">
                                <SearchIcon />
                            </InputAdornment>
                        ),
                    }}
                    sx={{ minWidth: 250 }}
                />
                <FormControl size="small" sx={{ minWidth: 120 }}>
                    <InputLabel>Action</InputLabel>
                    <Select value={actionFilter} label="Action" onChange={(e) => setActionFilter(e.target.value)}>
                        <MenuItem value="all">All Actions</MenuItem>
                        {Object.entries(actionConfig).map(([key, config]) => (
                            <MenuItem key={key} value={key}>{config.label}</MenuItem>
                        ))}
                    </Select>
                </FormControl>
                <FormControl size="small" sx={{ minWidth: 120 }}>
                    <InputLabel>Severity</InputLabel>
                    <Select value={severityFilter} label="Severity" onChange={(e) => setSeverityFilter(e.target.value)}>
                        <MenuItem value="all">All</MenuItem>
                        <MenuItem value="info">Info</MenuItem>
                        <MenuItem value="warning">Warning</MenuItem>
                        <MenuItem value="critical">Critical</MenuItem>
                    </Select>
                </FormControl>
            </Box>

            {/* Logs table */}
            <TableContainer>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell width={40}></TableCell>
                            <TableCell>Timestamp</TableCell>
                            <TableCell>User</TableCell>
                            <TableCell>Action</TableCell>
                            <TableCell>Resource</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Severity</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {filteredLogs.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((log) => {
                            const action = actionConfig[log.action];
                            const expanded = expandedRows.has(log.id);
                            return (
                                <React.Fragment key={log.id}>
                                    <TableRow hover sx={{ cursor: 'pointer' }} onClick={() => toggleRow(log.id)}>
                                        <TableCell>
                                            <IconButton size="small">
                                                {expanded ? <CollapseIcon /> : <ExpandIcon />}
                                            </IconButton>
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="body2">
                                                {new Date(log.timestamp).toLocaleString()}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                <Avatar sx={{ width: 28, height: 28, fontSize: 12 }}>
                                                    {log.userName.split(' ').map((n) => n[0]).join('')}
                                                </Avatar>
                                                <Box>
                                                    <Typography variant="body2" fontWeight={500}>
                                                        {log.userName}
                                                    </Typography>
                                                    <Typography variant="caption" color="text.secondary">
                                                        {log.userEmail}
                                                    </Typography>
                                                </Box>
                                            </Box>
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                size="small"
                                                icon={action.icon as React.ReactElement}
                                                label={action.label}
                                                sx={{ bgcolor: alpha(action.color, 0.1), color: action.color }}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="body2">{log.resource}</Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                size="small"
                                                label={log.success ? 'Success' : 'Failed'}
                                                color={log.success ? 'success' : 'error'}
                                                variant="outlined"
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                size="small"
                                                label={log.severity}
                                                sx={{
                                                    bgcolor: alpha(severityColors[log.severity], 0.1),
                                                    color: severityColors[log.severity],
                                                    textTransform: 'capitalize',
                                                }}
                                            />
                                        </TableCell>
                                    </TableRow>
                                    <TableRow>
                                        <TableCell colSpan={7} sx={{ p: 0, border: 0 }}>
                                            <Collapse in={expanded}>
                                                <ExpandedRow entry={log} />
                                            </Collapse>
                                        </TableCell>
                                    </TableRow>
                                </React.Fragment>
                            );
                        })}
                    </TableBody>
                </Table>
            </TableContainer>
            <TablePagination
                component="div"
                count={filteredLogs.length}
                page={page}
                onPageChange={(_, p) => setPage(p)}
                rowsPerPage={rowsPerPage}
                onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
            />
        </Paper>
    );
}
