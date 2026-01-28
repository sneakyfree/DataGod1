'use client';

import React, { useState } from 'react';
import {
    Box,
    Paper,
    Typography,
    Card,
    CardContent,
    CardActions,
    Button,
    Chip,
    IconButton,
    Tooltip,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    List,
    ListItem,
    ListItemText,
    Divider,
    Avatar,
    Badge,
    Grid,
    useTheme,
    alpha,
    Collapse,
    LinearProgress,
    Tab,
    Tabs,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
} from '@mui/material';
import {
    CheckCircle as ApproveIcon,
    Cancel as RejectIcon,
    Edit as EditIcon,
    Visibility as ViewIcon,
    Warning as WarningIcon,
    Error as ErrorIcon,
    Info as InfoIcon,
    HourglassEmpty as PendingIcon,
    ThumbUp as ThumbUpIcon,
    ThumbDown as ThumbDownIcon,
    History as HistoryIcon,
    FilterList as FilterIcon,
    ExpandMore as ExpandIcon,
    ExpandLess as CollapseIcon,
    SmartToy as AgentIcon,
    Person as PersonIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../../services/api';

// =============================================================================
// TYPES
// =============================================================================

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'modified';
export type ApprovalPriority = 'low' | 'medium' | 'high' | 'critical';
export type ApprovalCategory = 'data' | 'entity' | 'relationship' | 'classification' | 'merge';

export interface ApprovalChange {
    field: string;
    oldValue: string | number | null;
    newValue: string | number | null;
    confidence: number;
    reasoning?: string;
}

export interface ApprovalItem {
    id: string;
    category: ApprovalCategory;
    priority: ApprovalPriority;
    status: ApprovalStatus;
    title: string;
    description: string;
    agentId: string;
    agentName: string;
    confidence: number;
    changes: ApprovalChange[];
    reasoning: string;
    impact: string;
    createdAt: string;
    reviewedBy?: string;
    reviewedAt?: string;
    reviewNotes?: string;
    relatedRecordId?: number;
    relatedEntityId?: number;
}

interface HITLApprovalQueueProps {
    onApprove?: (item: ApprovalItem, notes?: string) => void;
    onReject?: (item: ApprovalItem, reason: string) => void;
    onModify?: (item: ApprovalItem, modifications: Partial<ApprovalItem>) => void;
}

// =============================================================================
// HELPERS
// =============================================================================

const priorityColors: Record<ApprovalPriority, string> = {
    low: '#9e9e9e',
    medium: '#2196f3',
    high: '#ff9800',
    critical: '#f44336',
};

const categoryIcons: Record<ApprovalCategory, React.ReactNode> = {
    data: <InfoIcon />,
    entity: <PersonIcon />,
    relationship: <HistoryIcon />,
    classification: <FilterIcon />,
    merge: <EditIcon />,
};

const statusStyles: Record<ApprovalStatus, { color: string; label: string }> = {
    pending: { color: '#ff9800', label: 'Pending Review' },
    approved: { color: '#4caf50', label: 'Approved' },
    rejected: { color: '#f44336', label: 'Rejected' },
    modified: { color: '#2196f3', label: 'Modified' },
};

// =============================================================================
// MOCK DATA
// =============================================================================

const mockApprovalItems: ApprovalItem[] = [
    {
        id: 'approval-1',
        category: 'entity',
        priority: 'high',
        status: 'pending',
        title: 'Merge Duplicate Entities',
        description: 'Agent detected potential duplicate entities that should be merged',
        agentId: 'agent-3',
        agentName: 'Entity Linker',
        confidence: 0.87,
        changes: [
            { field: 'entity_name', oldValue: 'ACME Corp', newValue: 'ACME Corporation', confidence: 0.92, reasoning: 'Name standardization' },
            { field: 'address', oldValue: '123 Main St', newValue: '123 Main Street, Suite 100', confidence: 0.85, reasoning: 'Address normalization' },
        ],
        reasoning: 'Multiple records found with slight name variations but matching tax ID and address patterns. Confidence based on 5 matching attributes.',
        impact: 'Will merge 3 records into 1 master entity. 12 relationships will be updated.',
        createdAt: new Date(Date.now() - 300000).toISOString(),
        relatedEntityId: 1247,
    },
    {
        id: 'approval-2',
        category: 'classification',
        priority: 'critical',
        status: 'pending',
        title: 'Reclassify Entity Type',
        description: 'Agent suggests changing entity type from "person" to "company"',
        agentId: 'agent-4',
        agentName: 'Quality Validator',
        confidence: 0.94,
        changes: [
            { field: 'entity_type', oldValue: 'person', newValue: 'company', confidence: 0.94, reasoning: 'Corporate registration found' },
        ],
        reasoning: 'Found corporate registration documents indicating this is actually a registered LLC, not an individual.',
        impact: 'Entity will be reclassified. May affect 8 related ownership records.',
        createdAt: new Date(Date.now() - 600000).toISOString(),
        relatedEntityId: 892,
    },
    {
        id: 'approval-3',
        category: 'data',
        priority: 'medium',
        status: 'pending',
        title: 'Update Property Value',
        description: 'New assessment data available for property record',
        agentId: 'agent-2',
        agentName: 'Data Collector',
        confidence: 0.99,
        changes: [
            { field: 'assessed_value', oldValue: 450000, newValue: 525000, confidence: 0.99, reasoning: 'Official assessment record' },
            { field: 'last_assessment_date', oldValue: '2023-01-15', newValue: '2024-01-10', confidence: 0.99, reasoning: 'New assessment date' },
        ],
        reasoning: 'Official county assessment records updated for tax year 2024.',
        impact: 'Property value will be updated. No relationship changes.',
        createdAt: new Date(Date.now() - 900000).toISOString(),
        relatedRecordId: 4521,
    },
];

// =============================================================================
// APPROVAL CARD COMPONENT
// =============================================================================

interface ApprovalCardProps {
    item: ApprovalItem;
    onApprove: () => void;
    onReject: () => void;
    onView: () => void;
}

function ApprovalCard({ item, onApprove, onReject, onView }: ApprovalCardProps) {
    const theme = useTheme();
    const [expanded, setExpanded] = useState(false);
    const priorityColor = priorityColors[item.priority];

    return (
        <Card
            sx={{
                position: 'relative',
                overflow: 'visible',
                border: `1px solid ${alpha(priorityColor, 0.3)}`,
                transition: 'all 0.2s ease',
                '&:hover': {
                    boxShadow: theme.shadows[4],
                    borderColor: priorityColor,
                },
            }}
        >
            {/* Priority indicator */}
            <Box
                sx={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: 4,
                    height: '100%',
                    backgroundColor: priorityColor,
                    borderRadius: '4px 0 0 4px',
                }}
            />

            <CardContent sx={{ pl: 3 }}>
                {/* Header */}
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 2 }}>
                    <Avatar
                        sx={{
                            bgcolor: alpha(priorityColor, 0.1),
                            color: priorityColor,
                            width: 40,
                            height: 40,
                        }}
                    >
                        {categoryIcons[item.category]}
                    </Avatar>

                    <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="subtitle1" fontWeight={600}>
                            {item.title}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 0.5 }}>
                            <Chip
                                size="small"
                                label={item.priority.toUpperCase()}
                                sx={{
                                    backgroundColor: alpha(priorityColor, 0.1),
                                    color: priorityColor,
                                    fontWeight: 600,
                                    fontSize: '0.7rem',
                                }}
                            />
                            <Chip
                                size="small"
                                icon={<AgentIcon sx={{ fontSize: '0.875rem !important' }} />}
                                label={item.agentName}
                                variant="outlined"
                            />
                        </Box>
                    </Box>

                    {/* Confidence badge */}
                    <Tooltip title="Agent confidence score">
                        <Box
                            sx={{
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                p: 1,
                                borderRadius: 1,
                                backgroundColor: alpha(
                                    item.confidence >= 0.9 ? '#4caf50' : item.confidence >= 0.7 ? '#ff9800' : '#f44336',
                                    0.1
                                ),
                            }}
                        >
                            <Typography variant="h6" fontWeight={700} sx={{
                                color: item.confidence >= 0.9 ? '#4caf50' : item.confidence >= 0.7 ? '#ff9800' : '#f44336',
                            }}>
                                {Math.round(item.confidence * 100)}%
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                Confidence
                            </Typography>
                        </Box>
                    </Tooltip>
                </Box>

                {/* Description */}
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {item.description}
                </Typography>

                {/* Changes preview */}
                <Box sx={{ mb: 2, p: 1.5, borderRadius: 1, backgroundColor: alpha(theme.palette.background.default, 0.5) }}>
                    <Typography variant="caption" color="text.secondary" gutterBottom>
                        Proposed Changes ({item.changes.length})
                    </Typography>
                    {item.changes.slice(0, 2).map((change, idx) => (
                        <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                            <Typography variant="body2" fontWeight={500} sx={{ minWidth: 100 }}>
                                {change.field}:
                            </Typography>
                            <Typography
                                variant="body2"
                                sx={{ textDecoration: 'line-through', color: 'text.secondary' }}
                            >
                                {String(change.oldValue || 'null')}
                            </Typography>
                            <Typography variant="body2">→</Typography>
                            <Typography variant="body2" color="primary" fontWeight={500}>
                                {String(change.newValue || 'null')}
                            </Typography>
                        </Box>
                    ))}
                    {item.changes.length > 2 && (
                        <Typography variant="caption" color="primary">
                            +{item.changes.length - 2} more changes
                        </Typography>
                    )}
                </Box>

                {/* Expand/Collapse */}
                <Button
                    size="small"
                    onClick={() => setExpanded(!expanded)}
                    endIcon={expanded ? <CollapseIcon /> : <ExpandIcon />}
                    sx={{ mb: 1 }}
                >
                    {expanded ? 'Less Details' : 'More Details'}
                </Button>

                <Collapse in={expanded}>
                    <Divider sx={{ my: 1 }} />

                    <Typography variant="subtitle2" gutterBottom>
                        Reasoning
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {item.reasoning}
                    </Typography>

                    <Typography variant="subtitle2" gutterBottom>
                        Impact Analysis
                    </Typography>
                    <Box
                        sx={{
                            p: 1.5,
                            borderRadius: 1,
                            backgroundColor: alpha(theme.palette.warning.main, 0.1),
                            border: `1px solid ${alpha(theme.palette.warning.main, 0.3)}`,
                        }}
                    >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <WarningIcon fontSize="small" color="warning" />
                            <Typography variant="body2">
                                {item.impact}
                            </Typography>
                        </Box>
                    </Box>
                </Collapse>
            </CardContent>

            <Divider />

            <CardActions sx={{ justifyContent: 'space-between', px: 2, py: 1.5 }}>
                <Typography variant="caption" color="text.secondary">
                    {new Date(item.createdAt).toLocaleString()}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                    <Tooltip title="View Details">
                        <IconButton size="small" onClick={onView}>
                            <ViewIcon />
                        </IconButton>
                    </Tooltip>
                    <Button
                        size="small"
                        variant="outlined"
                        color="error"
                        startIcon={<RejectIcon />}
                        onClick={onReject}
                    >
                        Reject
                    </Button>
                    <Button
                        size="small"
                        variant="contained"
                        color="success"
                        startIcon={<ApproveIcon />}
                        onClick={onApprove}
                    >
                        Approve
                    </Button>
                </Box>
            </CardActions>
        </Card>
    );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function HITLApprovalQueue({
    onApprove,
    onReject,
    onModify,
}: HITLApprovalQueueProps) {
    const theme = useTheme();
    const queryClient = useQueryClient();

    const [currentTab, setCurrentTab] = useState(0);
    const [selectedItem, setSelectedItem] = useState<ApprovalItem | null>(null);
    const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
    const [rejectReason, setRejectReason] = useState('');
    const [filterPriority, setFilterPriority] = useState<ApprovalPriority | 'all'>('all');

    // Fetch approval items
    const { data: approvalItems = mockApprovalItems, isLoading } = useQuery<ApprovalItem[]>({
        queryKey: ['hitl-approvals'],
        queryFn: async () => {
            try {
                const response = await apiService.get('/agents/approvals/pending');
                return response.data;
            } catch {
                return mockApprovalItems;
            }
        },
        refetchInterval: 10000,
    });

    // Filter items
    const pendingItems = approvalItems.filter((i) => i.status === 'pending');
    const reviewedItems = approvalItems.filter((i) => i.status !== 'pending');

    const filteredPending = filterPriority === 'all'
        ? pendingItems
        : pendingItems.filter((i) => i.priority === filterPriority);

    const handleApprove = (item: ApprovalItem) => {
        onApprove?.(item);
        // TODO: API call to approve
    };

    const handleReject = (item: ApprovalItem) => {
        setSelectedItem(item);
        setRejectDialogOpen(true);
    };

    const confirmReject = () => {
        if (selectedItem) {
            onReject?.(selectedItem, rejectReason);
            // TODO: API call to reject
        }
        setRejectDialogOpen(false);
        setRejectReason('');
        setSelectedItem(null);
    };

    const handleView = (item: ApprovalItem) => {
        setSelectedItem(item);
        // TODO: Open detail view
    };

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
                        Human-in-the-Loop Approval Queue
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Review and approve agent-proposed changes
                    </Typography>
                </Box>
                <Badge badgeContent={pendingItems.length} color="warning">
                    <Chip
                        icon={<PendingIcon />}
                        label="Pending Reviews"
                        variant="outlined"
                    />
                </Badge>
            </Box>

            {/* Tabs */}
            <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                <Tabs value={currentTab} onChange={(_, v) => setCurrentTab(v)}>
                    <Tab
                        label={
                            <Badge badgeContent={pendingItems.length} color="warning" sx={{ pr: 2 }}>
                                Pending
                            </Badge>
                        }
                    />
                    <Tab label="History" />
                </Tabs>
            </Box>

            {/* Filters */}
            {currentTab === 0 && (
                <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                    <FormControl size="small" sx={{ minWidth: 150 }}>
                        <InputLabel>Priority</InputLabel>
                        <Select
                            value={filterPriority}
                            label="Priority"
                            onChange={(e) => setFilterPriority(e.target.value as ApprovalPriority | 'all')}
                        >
                            <MenuItem value="all">All Priorities</MenuItem>
                            <MenuItem value="critical">Critical</MenuItem>
                            <MenuItem value="high">High</MenuItem>
                            <MenuItem value="medium">Medium</MenuItem>
                            <MenuItem value="low">Low</MenuItem>
                        </Select>
                    </FormControl>
                </Box>
            )}

            {/* Content */}
            {currentTab === 0 && (
                <Grid container spacing={2}>
                    {filteredPending.map((item) => (
                        <Grid item xs={12} key={item.id}>
                            <ApprovalCard
                                item={item}
                                onApprove={() => handleApprove(item)}
                                onReject={() => handleReject(item)}
                                onView={() => handleView(item)}
                            />
                        </Grid>
                    ))}
                    {filteredPending.length === 0 && (
                        <Grid item xs={12}>
                            <Box sx={{ textAlign: 'center', py: 8 }}>
                                <ApproveIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
                                <Typography variant="h6" color="text.secondary">
                                    No pending approvals
                                </Typography>
                                <Typography variant="body2" color="text.disabled">
                                    All agent proposals have been reviewed
                                </Typography>
                            </Box>
                        </Grid>
                    )}
                </Grid>
            )}

            {currentTab === 1 && (
                <List>
                    {reviewedItems.map((item) => (
                        <React.Fragment key={item.id}>
                            <ListItem
                                secondaryAction={
                                    <Chip
                                        size="small"
                                        label={statusStyles[item.status].label}
                                        sx={{
                                            backgroundColor: alpha(statusStyles[item.status].color, 0.1),
                                            color: statusStyles[item.status].color,
                                        }}
                                    />
                                }
                            >
                                <ListItemText
                                    primary={item.title}
                                    secondary={`${item.agentName} • ${new Date(item.createdAt).toLocaleString()}`}
                                />
                            </ListItem>
                            <Divider />
                        </React.Fragment>
                    ))}
                    {reviewedItems.length === 0 && (
                        <Box sx={{ textAlign: 'center', py: 8 }}>
                            <HistoryIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
                            <Typography variant="h6" color="text.secondary">
                                No review history
                            </Typography>
                        </Box>
                    )}
                </List>
            )}

            {/* Reject Dialog */}
            <Dialog open={rejectDialogOpen} onClose={() => setRejectDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Reject Proposal</DialogTitle>
                <DialogContent>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Please provide a reason for rejecting this proposal. This feedback helps improve agent accuracy.
                    </Typography>
                    <TextField
                        autoFocus
                        fullWidth
                        multiline
                        rows={3}
                        label="Rejection Reason"
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="Explain why this proposal should be rejected..."
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setRejectDialogOpen(false)}>Cancel</Button>
                    <Button
                        variant="contained"
                        color="error"
                        onClick={confirmReject}
                        disabled={!rejectReason.trim()}
                    >
                        Confirm Rejection
                    </Button>
                </DialogActions>
            </Dialog>
        </Paper>
    );
}
