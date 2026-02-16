'use client';

import { useState } from 'react';
import {
    Box,
    Typography,
    Container,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    CircularProgress,
    Alert,
    Chip,
    IconButton,
    Tooltip,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
    Snackbar,
} from '@mui/material';
import {
    ContentCopy,
    Delete,
    Visibility,
    Link as LinkIcon,
    Share,
    Refresh,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../../services/api';
import { ProtectedRoute } from '../../context/AuthContext';

function SharesContent() {
    const [revokeTarget, setRevokeTarget] = useState<any>(null);
    const [copiedId, setCopiedId] = useState<number | null>(null);
    const queryClient = useQueryClient();

    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['user-shares'],
        queryFn: () => apiService.get('/shares').then((res: any) => res.data),
        staleTime: 30 * 1000,
    });

    const revokeMutation = useMutation({
        mutationFn: (shareId: number) => apiService.delete(`/shares/${shareId}`),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['user-shares'] });
            setRevokeTarget(null);
        },
    });

    const shares = data?.shares || data || [];

    const copyToClipboard = (link: string, id: number) => {
        navigator.clipboard.writeText(link);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
    };

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
                <Box>
                    <Typography variant="h4" component="h1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Share color="primary" /> Shared Links
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                        Manage your shared records and entity links
                    </Typography>
                </Box>
                <Tooltip title="Refresh">
                    <IconButton onClick={() => refetch()}>
                        <Refresh />
                    </IconButton>
                </Tooltip>
            </Box>

            {error && (
                <Alert severity="warning" sx={{ mb: 3 }}>
                    Sharing service may not be available. Showing cached data.
                </Alert>
            )}

            <Paper>
                <TableContainer>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Shared Item</TableCell>
                                <TableCell>Type</TableCell>
                                <TableCell>Link</TableCell>
                                <TableCell>Created</TableCell>
                                <TableCell>Views</TableCell>
                                <TableCell>Expires</TableCell>
                                <TableCell>Status</TableCell>
                                <TableCell>Actions</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {isLoading ? (
                                <TableRow>
                                    <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                                        <CircularProgress />
                                    </TableCell>
                                </TableRow>
                            ) : shares.length > 0 ? (
                                shares.map((share: any) => (
                                    <TableRow key={share.id} hover>
                                        <TableCell>
                                            <Typography variant="body2" fontWeight={500}>
                                                {share.item_name || share.title || `Item #${share.record_id || share.entity_id}`}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={share.item_type || 'record'}
                                                size="small"
                                                variant="outlined"
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                <LinkIcon fontSize="small" color="action" />
                                                <Typography variant="caption" noWrap sx={{ maxWidth: 200 }}>
                                                    {share.share_url || share.link || '—'}
                                                </Typography>
                                            </Box>
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="caption">
                                                {share.created_at ? new Date(share.created_at).toLocaleDateString() : '—'}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={share.view_count ?? 0}
                                                size="small"
                                                icon={<Visibility fontSize="small" />}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Typography variant="caption" color={share.expires_at ? 'text.primary' : 'text.disabled'}>
                                                {share.expires_at ? new Date(share.expires_at).toLocaleDateString() : 'Never'}
                                            </Typography>
                                        </TableCell>
                                        <TableCell>
                                            <Chip
                                                label={share.active !== false ? 'Active' : 'Revoked'}
                                                size="small"
                                                color={share.active !== false ? 'success' : 'default'}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Tooltip title="Copy link">
                                                <IconButton
                                                    size="small"
                                                    onClick={() => copyToClipboard(share.share_url || share.link || '', share.id)}
                                                >
                                                    <ContentCopy fontSize="small" />
                                                </IconButton>
                                            </Tooltip>
                                            <Tooltip title="Revoke">
                                                <IconButton
                                                    size="small"
                                                    color="error"
                                                    onClick={() => setRevokeTarget(share)}
                                                    disabled={share.active === false}
                                                >
                                                    <Delete fontSize="small" />
                                                </IconButton>
                                            </Tooltip>
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                                        <LinkIcon sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} />
                                        <Typography color="text.secondary">No shared links yet</Typography>
                                        <Typography variant="caption" color="text.disabled">
                                            Share records or entities from their detail pages
                                        </Typography>
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>
            </Paper>

            {/* Revoke Confirmation */}
            <Dialog open={!!revokeTarget} onClose={() => setRevokeTarget(null)}>
                <DialogTitle>Revoke Share Link?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        This will permanently disable the share link for &quot;{revokeTarget?.item_name || 'this item'}&quot;. Anyone with the link will no longer be able to access it.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setRevokeTarget(null)}>Cancel</Button>
                    <Button
                        color="error"
                        onClick={() => revokeTarget && revokeMutation.mutate(revokeTarget.id)}
                        disabled={revokeMutation.isPending}
                    >
                        Revoke
                    </Button>
                </DialogActions>
            </Dialog>

            <Snackbar
                open={copiedId !== null}
                autoHideDuration={2000}
                message="Link copied to clipboard"
                onClose={() => setCopiedId(null)}
            />
        </Container>
    );
}

export default function SharesPage() {
    return (
        <ProtectedRoute>
            <SharesContent />
        </ProtectedRoute>
    );
}
