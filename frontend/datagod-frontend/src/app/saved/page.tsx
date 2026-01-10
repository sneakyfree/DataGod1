'use client';

import { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Button,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  Menu,
  MenuItem,
  Divider,
  Skeleton,
} from '@mui/material';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import NotificationsIcon from '@mui/icons-material/Notifications';
import NotificationsOffIcon from '@mui/icons-material/NotificationsOff';
import SearchIcon from '@mui/icons-material/Search';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { apiService } from '../../services/api';
import { ProtectedRoute } from '../../context/AuthContext';

interface SavedSearch {
  id: number;
  name: string;
  description?: string;
  search_params: {
    query?: string;
    filters?: Record<string, any>;
  };
  last_run?: string;
  run_count: number;
  notify_on_new_results: boolean;
  notification_frequency?: string;
  last_result_count: number;
  created_at: string;
  updated_at: string;
}

function SavedSearchesContent() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [searchToDelete, setSearchToDelete] = useState<SavedSearch | null>(null);
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [activeSearch, setActiveSearch] = useState<SavedSearch | null>(null);

  const { data: savedSearches, isLoading, error } = useQuery({
    queryKey: ['savedSearches'],
    queryFn: () => apiService.getSavedSearches().then(res => res.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiService.deleteSavedSearch(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['savedSearches'] });
      setDeleteDialogOpen(false);
      setSearchToDelete(null);
    },
  });

  const runSearchMutation = useMutation({
    mutationFn: (id: number) => apiService.runSavedSearch(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['savedSearches'] });
      // Navigate to search page with the saved search parameters
      const search = savedSearches?.find((s: SavedSearch) => s.id === id);
      if (search?.search_params?.query) {
        router.push(`/search?q=${encodeURIComponent(search.search_params.query)}`);
      }
    },
  });

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, search: SavedSearch) => {
    setMenuAnchorEl(event.currentTarget);
    setActiveSearch(search);
  };

  const handleMenuClose = () => {
    setMenuAnchorEl(null);
    setActiveSearch(null);
  };

  const handleDeleteClick = (search: SavedSearch) => {
    setSearchToDelete(search);
    setDeleteDialogOpen(true);
    handleMenuClose();
  };

  const handleRunSearch = (search: SavedSearch) => {
    runSearchMutation.mutate(search.id);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getSearchSummary = (params: SavedSearch['search_params']) => {
    const parts: string[] = [];
    if (params.query) parts.push(`"${params.query}"`);
    if (params.filters?.record_types?.length) {
      parts.push(`${params.filters.record_types.length} type(s)`);
    }
    if (params.filters?.jurisdiction_ids?.length) {
      parts.push(`${params.filters.jurisdiction_ids.length} jurisdiction(s)`);
    }
    return parts.length > 0 ? parts.join(' + ') : 'All records';
  };

  if (isLoading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Saved Searches
        </Typography>
        <Paper sx={{ p: 0 }}>
          {[1, 2, 3].map((i) => (
            <Box key={i} sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
              <Skeleton variant="text" width="40%" height={28} />
              <Skeleton variant="text" width="60%" height={20} />
              <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                <Skeleton variant="rectangular" width={80} height={24} sx={{ borderRadius: 1 }} />
                <Skeleton variant="rectangular" width={100} height={24} sx={{ borderRadius: 1 }} />
              </Box>
            </Box>
          ))}
        </Paper>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">Failed to load saved searches. Please try again.</Alert>
      </Container>
    );
  }

  const searches = savedSearches || [];

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Saved Searches
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Quick access to your frequently used search queries
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<SearchIcon />}
          onClick={() => router.push('/search')}
        >
          New Search
        </Button>
      </Box>

      {searches.length === 0 ? (
        <Paper sx={{ p: 6, textAlign: 'center' }}>
          <BookmarkIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No saved searches yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Save your search queries for quick access and optional email notifications
          </Typography>
          <Button variant="contained" startIcon={<SearchIcon />} onClick={() => router.push('/search')}>
            Start Searching
          </Button>
        </Paper>
      ) : (
        <Paper sx={{ overflow: 'hidden' }}>
          <List disablePadding>
            {searches.map((search: SavedSearch, index: number) => (
              <ListItem
                key={search.id}
                sx={{
                  py: 2,
                  px: 3,
                  borderBottom: index < searches.length - 1 ? '1px solid' : 'none',
                  borderColor: 'divider',
                  '&:hover': { bgcolor: 'action.hover' },
                }}
              >
                <ListItemIcon sx={{ minWidth: 48 }}>
                  <BookmarkIcon color="primary" />
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        {search.name}
                      </Typography>
                      {search.notify_on_new_results && (
                        <Tooltip title={`Notifications: ${search.notification_frequency}`}>
                          <NotificationsIcon fontSize="small" color="primary" />
                        </Tooltip>
                      )}
                    </Box>
                  }
                  secondary={
                    <Box sx={{ mt: 0.5 }}>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        {getSearchSummary(search.search_params)}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                        <Chip
                          size="small"
                          label={`${search.run_count} runs`}
                          variant="outlined"
                          sx={{ height: 22, fontSize: '0.7rem' }}
                        />
                        {search.last_run && (
                          <Chip
                            size="small"
                            label={`Last run: ${formatDate(search.last_run)}`}
                            variant="outlined"
                            sx={{ height: 22, fontSize: '0.7rem' }}
                          />
                        )}
                        {search.last_result_count > 0 && (
                          <Chip
                            size="small"
                            label={`${search.last_result_count} results`}
                            color="primary"
                            variant="outlined"
                            sx={{ height: 22, fontSize: '0.7rem' }}
                          />
                        )}
                        <Typography variant="caption" color="text.secondary">
                          Created {formatDate(search.created_at)}
                        </Typography>
                      </Box>
                    </Box>
                  }
                />
                <ListItemSecondaryAction sx={{ display: 'flex', gap: 1 }}>
                  <Tooltip title="Run search">
                    <IconButton
                      edge="end"
                      onClick={() => handleRunSearch(search)}
                      disabled={runSearchMutation.isPending}
                      color="primary"
                    >
                      {runSearchMutation.isPending ? (
                        <CircularProgress size={20} />
                      ) : (
                        <PlayArrowIcon />
                      )}
                    </IconButton>
                  </Tooltip>
                  <IconButton edge="end" onClick={(e) => handleMenuOpen(e, search)}>
                    <MoreVertIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Paper>
      )}

      {/* Actions Menu */}
      <Menu
        anchorEl={menuAnchorEl}
        open={Boolean(menuAnchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleMenuClose}>
          <ListItemIcon>
            <EditIcon fontSize="small" />
          </ListItemIcon>
          Edit
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <ListItemIcon>
            {activeSearch?.notify_on_new_results ? (
              <NotificationsOffIcon fontSize="small" />
            ) : (
              <NotificationsIcon fontSize="small" />
            )}
          </ListItemIcon>
          {activeSearch?.notify_on_new_results ? 'Disable Notifications' : 'Enable Notifications'}
        </MenuItem>
        <Divider />
        <MenuItem onClick={() => activeSearch && handleDeleteClick(activeSearch)} sx={{ color: 'error.main' }}>
          <ListItemIcon>
            <DeleteIcon fontSize="small" color="error" />
          </ListItemIcon>
          Delete
        </MenuItem>
      </Menu>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Saved Search?</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete &quot;{searchToDelete?.name}&quot;? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={() => searchToDelete && deleteMutation.mutate(searchToDelete.id)}
            color="error"
            variant="contained"
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default function SavedSearchesPage() {
  return (
    <ProtectedRoute>
      <SavedSearchesContent />
    </ProtectedRoute>
  );
}
