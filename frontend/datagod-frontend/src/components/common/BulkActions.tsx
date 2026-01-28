'use client';

import React, { useState } from 'react';
import {
    Box,
    Toolbar,
    Typography,
    Button,
    IconButton,
    Tooltip,
    Menu,
    MenuItem,
    Divider,
    Checkbox,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
    TextField,
    Chip,
    LinearProgress,
    Slide,
    alpha,
    useTheme,
} from '@mui/material';
import {
    Delete as DeleteIcon,
    Download as DownloadIcon,
    Label as LabelIcon,
    Archive as ArchiveIcon,
    UnarchiveOutlined as UnarchiveIcon,
    Share as ShareIcon,
    MoreVert as MoreIcon,
    Close as CloseIcon,
    CheckBox as CheckBoxIcon,
    IndeterminateCheckBox as IndeterminateCheckBoxIcon,
    Star as StarIcon,
    StarBorder as StarBorderIcon,
} from '@mui/icons-material';

// =============================================================================
// TYPES
// =============================================================================

export interface BulkActionItem {
    id: string | number;
    label?: string;
}

export interface BulkActionsProps<T extends BulkActionItem> {
    items: T[];
    selectedIds: Set<string | number>;
    onSelectAll: (selectAll: boolean) => void;
    onClearSelection: () => void;
    onDelete?: (ids: (string | number)[]) => Promise<void>;
    onExport?: (ids: (string | number)[], format: 'csv' | 'json' | 'pdf') => Promise<void>;
    onTag?: (ids: (string | number)[], tag: string) => Promise<void>;
    onArchive?: (ids: (string | number)[], archive: boolean) => Promise<void>;
    onFavorite?: (ids: (string | number)[], favorite: boolean) => Promise<void>;
    onShare?: (ids: (string | number)[]) => void;
    customActions?: {
        label: string;
        icon: React.ReactNode;
        onClick: (ids: (string | number)[]) => Promise<void>;
        color?: 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success';
    }[];
    disabled?: boolean;
}

// =============================================================================
// COMPONENT
// =============================================================================

export default function BulkActions<T extends BulkActionItem>({
    items,
    selectedIds,
    onSelectAll,
    onClearSelection,
    onDelete,
    onExport,
    onTag,
    onArchive,
    onFavorite,
    onShare,
    customActions = [],
    disabled = false,
}: BulkActionsProps<T>) {
    const theme = useTheme();
    const [loading, setLoading] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [tagDialogOpen, setTagDialogOpen] = useState(false);
    const [tagValue, setTagValue] = useState('');
    const [exportMenuAnchor, setExportMenuAnchor] = useState<null | HTMLElement>(null);
    const [moreMenuAnchor, setMoreMenuAnchor] = useState<null | HTMLElement>(null);

    const selectedCount = selectedIds.size;
    const totalCount = items.length;
    const allSelected = selectedCount === totalCount && totalCount > 0;
    const someSelected = selectedCount > 0 && selectedCount < totalCount;
    const isVisible = selectedCount > 0;

    // =============================================================================
    // HANDLERS
    // =============================================================================

    const handleSelectAllClick = () => {
        if (allSelected) {
            onSelectAll(false);
        } else {
            onSelectAll(true);
        }
    };

    const executeAction = async (action: () => Promise<void>) => {
        setLoading(true);
        try {
            await action();
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async () => {
        if (!onDelete) return;
        setDeleteDialogOpen(false);
        await executeAction(() => onDelete(Array.from(selectedIds)));
        onClearSelection();
    };

    const handleExport = async (format: 'csv' | 'json' | 'pdf') => {
        if (!onExport) return;
        setExportMenuAnchor(null);
        await executeAction(() => onExport(Array.from(selectedIds), format));
    };

    const handleTag = async () => {
        if (!onTag || !tagValue.trim()) return;
        setTagDialogOpen(false);
        await executeAction(() => onTag(Array.from(selectedIds), tagValue.trim()));
        setTagValue('');
    };

    const handleArchive = async (archive: boolean) => {
        if (!onArchive) return;
        setMoreMenuAnchor(null);
        await executeAction(() => onArchive(Array.from(selectedIds), archive));
        onClearSelection();
    };

    const handleFavorite = async (favorite: boolean) => {
        if (!onFavorite) return;
        await executeAction(() => onFavorite(Array.from(selectedIds), favorite));
    };

    const handleShare = () => {
        if (!onShare) return;
        onShare(Array.from(selectedIds));
    };

    // =============================================================================
    // RENDER
    // =============================================================================

    if (!isVisible) {
        return null;
    }

    return (
        <>
            <Slide direction="down" in={isVisible} mountOnEnter unmountOnExit>
                <Toolbar
                    sx={{
                        position: 'sticky',
                        top: 0,
                        zIndex: theme.zIndex.appBar + 1,
                        backgroundColor: alpha(theme.palette.primary.main, 0.1),
                        borderRadius: 1,
                        mb: 2,
                        px: 2,
                        minHeight: 56,
                        gap: 1,
                    }}
                >
                    {/* Selection checkbox */}
                    <Tooltip title={allSelected ? 'Deselect all' : 'Select all'}>
                        <Checkbox
                            checked={allSelected}
                            indeterminate={someSelected}
                            onChange={handleSelectAllClick}
                            disabled={disabled}
                            icon={<CheckBoxIcon />}
                            indeterminateIcon={<IndeterminateCheckBoxIcon />}
                        />
                    </Tooltip>

                    {/* Selection count */}
                    <Typography variant="subtitle1" fontWeight="medium" sx={{ minWidth: 100 }}>
                        {selectedCount} selected
                    </Typography>

                    <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />

                    {/* Action buttons */}
                    {onDelete && (
                        <Tooltip title="Delete selected">
                            <IconButton
                                color="error"
                                onClick={() => setDeleteDialogOpen(true)}
                                disabled={disabled || loading}
                            >
                                <DeleteIcon />
                            </IconButton>
                        </Tooltip>
                    )}

                    {onExport && (
                        <>
                            <Tooltip title="Export selected">
                                <IconButton
                                    onClick={(e) => setExportMenuAnchor(e.currentTarget)}
                                    disabled={disabled || loading}
                                >
                                    <DownloadIcon />
                                </IconButton>
                            </Tooltip>
                            <Menu
                                anchorEl={exportMenuAnchor}
                                open={Boolean(exportMenuAnchor)}
                                onClose={() => setExportMenuAnchor(null)}
                            >
                                <MenuItem onClick={() => handleExport('csv')}>Export as CSV</MenuItem>
                                <MenuItem onClick={() => handleExport('json')}>Export as JSON</MenuItem>
                                <MenuItem onClick={() => handleExport('pdf')}>Export as PDF</MenuItem>
                            </Menu>
                        </>
                    )}

                    {onTag && (
                        <Tooltip title="Add tag">
                            <IconButton
                                onClick={() => setTagDialogOpen(true)}
                                disabled={disabled || loading}
                            >
                                <LabelIcon />
                            </IconButton>
                        </Tooltip>
                    )}

                    {onFavorite && (
                        <Tooltip title="Toggle favorite">
                            <IconButton
                                onClick={() => handleFavorite(true)}
                                disabled={disabled || loading}
                            >
                                <StarBorderIcon />
                            </IconButton>
                        </Tooltip>
                    )}

                    {onShare && (
                        <Tooltip title="Share selected">
                            <IconButton onClick={handleShare} disabled={disabled || loading}>
                                <ShareIcon />
                            </IconButton>
                        </Tooltip>
                    )}

                    {/* Custom actions */}
                    {customActions.map((action, index) => (
                        <Tooltip key={index} title={action.label}>
                            <IconButton
                                color={action.color || 'default'}
                                onClick={() => executeAction(() => action.onClick(Array.from(selectedIds)))}
                                disabled={disabled || loading}
                            >
                                {action.icon}
                            </IconButton>
                        </Tooltip>
                    ))}

                    {/* More menu */}
                    {(onArchive) && (
                        <>
                            <Tooltip title="More actions">
                                <IconButton
                                    onClick={(e) => setMoreMenuAnchor(e.currentTarget)}
                                    disabled={disabled || loading}
                                >
                                    <MoreIcon />
                                </IconButton>
                            </Tooltip>
                            <Menu
                                anchorEl={moreMenuAnchor}
                                open={Boolean(moreMenuAnchor)}
                                onClose={() => setMoreMenuAnchor(null)}
                            >
                                <MenuItem onClick={() => handleArchive(true)}>
                                    <ArchiveIcon sx={{ mr: 1 }} /> Archive
                                </MenuItem>
                                <MenuItem onClick={() => handleArchive(false)}>
                                    <UnarchiveIcon sx={{ mr: 1 }} /> Unarchive
                                </MenuItem>
                            </Menu>
                        </>
                    )}

                    <Box sx={{ flexGrow: 1 }} />

                    {/* Clear selection button */}
                    <Tooltip title="Clear selection">
                        <IconButton onClick={onClearSelection} disabled={disabled}>
                            <CloseIcon />
                        </IconButton>
                    </Tooltip>

                    {/* Loading indicator */}
                    {loading && (
                        <LinearProgress
                            sx={{
                                position: 'absolute',
                                bottom: 0,
                                left: 0,
                                right: 0,
                                height: 2,
                            }}
                        />
                    )}
                </Toolbar>
            </Slide>

            {/* Delete Confirmation Dialog */}
            <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
                <DialogTitle>Confirm Delete</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Are you sure you want to delete {selectedCount} selected item{selectedCount !== 1 ? 's' : ''}?
                        This action cannot be undone.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
                    <Button onClick={handleDelete} color="error" variant="contained">
                        Delete
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Tag Dialog */}
            <Dialog open={tagDialogOpen} onClose={() => setTagDialogOpen(false)}>
                <DialogTitle>Add Tag</DialogTitle>
                <DialogContent>
                    <DialogContentText sx={{ mb: 2 }}>
                        Add a tag to {selectedCount} selected item{selectedCount !== 1 ? 's' : ''}.
                    </DialogContentText>
                    <TextField
                        autoFocus
                        label="Tag name"
                        fullWidth
                        value={tagValue}
                        onChange={(e) => setTagValue(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleTag()}
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setTagDialogOpen(false)}>Cancel</Button>
                    <Button onClick={handleTag} variant="contained" disabled={!tagValue.trim()}>
                        Add Tag
                    </Button>
                </DialogActions>
            </Dialog>
        </>
    );
}
