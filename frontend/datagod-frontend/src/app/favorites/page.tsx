'use client';

import { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Tabs,
  Tab,
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
  Skeleton,
  Card,
  CardContent,
  Grid,
} from '@mui/material';
import FavoriteIcon from '@mui/icons-material/Favorite';
import DeleteIcon from '@mui/icons-material/Delete';
import DescriptionIcon from '@mui/icons-material/Description';
import PersonIcon from '@mui/icons-material/Person';
import BusinessIcon from '@mui/icons-material/Business';
import HomeIcon from '@mui/icons-material/Home';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import SearchIcon from '@mui/icons-material/Search';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { apiService } from '../../services/api';
import { ProtectedRoute } from '../../context/AuthContext';

interface Favorite {
  id: number;
  record_id?: number;
  entity_id?: number;
  favorite_type: 'record' | 'entity';
  notes?: string;
  tags?: string[];
  created_at: string;
  record?: {
    id: number;
    title: string;
    record_type?: string;
    date?: string;
  };
  entity?: {
    id: number;
    entity_name: string;
    entity_type: string;
  };
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ py: 2 }}>{children}</Box>}
    </div>
  );
}

function FavoritesContent() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [favoriteToDelete, setFavoriteToDelete] = useState<Favorite | null>(null);

  // Fetch all favorites
  const { data: allFavorites, isLoading, error } = useQuery({
    queryKey: ['favorites'],
    queryFn: () => apiService.getFavorites().then(res => res.data),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiService.removeFavorite(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['favorites'] });
      setDeleteDialogOpen(false);
      setFavoriteToDelete(null);
    },
  });

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleDeleteClick = (favorite: Favorite) => {
    setFavoriteToDelete(favorite);
    setDeleteDialogOpen(true);
  };

  const handleNavigate = (favorite: Favorite) => {
    if (favorite.favorite_type === 'record' && favorite.record_id) {
      router.push(`/records/${favorite.record_id}`);
    } else if (favorite.favorite_type === 'entity' && favorite.entity_id) {
      router.push(`/network?entityId=${favorite.entity_id}`);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getEntityIcon = (type?: string) => {
    switch (type?.toLowerCase()) {
      case 'person':
        return <PersonIcon />;
      case 'company':
        return <BusinessIcon />;
      case 'property':
        return <HomeIcon />;
      default:
        return <PersonIcon />;
    }
  };

  const favorites = allFavorites || [];
  const recordFavorites = favorites.filter((f: Favorite) => f.favorite_type === 'record');
  const entityFavorites = favorites.filter((f: Favorite) => f.favorite_type === 'entity');

  if (isLoading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Favorites
        </Typography>
        <Paper sx={{ p: 0 }}>
          {[1, 2, 3].map((i) => (
            <Box key={i} sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
              <Skeleton variant="text" width="40%" height={28} />
              <Skeleton variant="text" width="60%" height={20} />
            </Box>
          ))}
        </Paper>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">Failed to load favorites. Please try again.</Alert>
      </Container>
    );
  }

  const renderFavoritesList = (items: Favorite[], type: 'record' | 'entity') => {
    if (items.length === 0) {
      return (
        <Paper sx={{ p: 6, textAlign: 'center' }}>
          <FavoriteIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No {type === 'record' ? 'records' : 'entities'} favorited yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {type === 'record'
              ? 'Browse records and click the heart icon to add them here'
              : 'Explore the entity network and favorite people, companies, or properties'}
          </Typography>
          <Button
            variant="contained"
            startIcon={<SearchIcon />}
            onClick={() => router.push(type === 'record' ? '/search' : '/network')}
          >
            {type === 'record' ? 'Search Records' : 'Explore Network'}
          </Button>
        </Paper>
      );
    }

    return (
      <Paper sx={{ overflow: 'hidden' }}>
        <List disablePadding>
          {items.map((favorite, index) => (
            <ListItem
              key={favorite.id}
              sx={{
                py: 2,
                px: 3,
                borderBottom: index < items.length - 1 ? '1px solid' : 'none',
                borderColor: 'divider',
                cursor: 'pointer',
                '&:hover': { bgcolor: 'action.hover' },
              }}
              onClick={() => handleNavigate(favorite)}
            >
              <ListItemIcon sx={{ minWidth: 48 }}>
                {type === 'record' ? (
                  <DescriptionIcon color="primary" />
                ) : (
                  getEntityIcon(favorite.entity?.entity_type)
                )}
              </ListItemIcon>
              <ListItemText
                primary={
                  <Typography variant="subtitle1" fontWeight={500}>
                    {type === 'record'
                      ? favorite.record?.title || `Record #${favorite.record_id}`
                      : favorite.entity?.entity_name || `Entity #${favorite.entity_id}`}
                  </Typography>
                }
                secondary={
                  <Box sx={{ mt: 0.5 }}>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                      {type === 'record' && favorite.record?.record_type && (
                        <Chip
                          size="small"
                          label={favorite.record.record_type}
                          variant="outlined"
                          sx={{ height: 22, fontSize: '0.7rem', textTransform: 'capitalize' }}
                        />
                      )}
                      {type === 'entity' && favorite.entity?.entity_type && (
                        <Chip
                          size="small"
                          label={favorite.entity.entity_type}
                          variant="outlined"
                          sx={{ height: 22, fontSize: '0.7rem', textTransform: 'capitalize' }}
                        />
                      )}
                      {favorite.tags?.map((tag) => (
                        <Chip
                          key={tag}
                          size="small"
                          label={tag}
                          color="primary"
                          variant="outlined"
                          sx={{ height: 22, fontSize: '0.7rem' }}
                        />
                      ))}
                      <Typography variant="caption" color="text.secondary">
                        Added {formatDate(favorite.created_at)}
                      </Typography>
                    </Box>
                    {favorite.notes && (
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                        {favorite.notes}
                      </Typography>
                    )}
                  </Box>
                }
              />
              <ListItemSecondaryAction sx={{ display: 'flex', gap: 1 }}>
                <Tooltip title="Open">
                  <IconButton edge="end" onClick={() => handleNavigate(favorite)}>
                    <OpenInNewIcon />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Remove from favorites">
                  <IconButton
                    edge="end"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteClick(favorite);
                    }}
                    sx={{ color: 'error.main' }}
                  >
                    <DeleteIcon />
                  </IconButton>
                </Tooltip>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      </Paper>
    );
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Favorites
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Quick access to your saved records and entities
          </Typography>
        </Box>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6}>
          <Card variant="outlined">
            <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <DescriptionIcon sx={{ fontSize: 40, color: 'primary.main' }} />
              <Box>
                <Typography variant="h4" fontWeight={600}>
                  {recordFavorites.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Saved Records
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6}>
          <Card variant="outlined">
            <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <PersonIcon sx={{ fontSize: 40, color: 'secondary.main' }} />
              <Box>
                <Typography variant="h4" fontWeight={600}>
                  {entityFavorites.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Saved Entities
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ mb: 2 }}>
        <Tabs value={tabValue} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tab label={`Records (${recordFavorites.length})`} />
          <Tab label={`Entities (${entityFavorites.length})`} />
        </Tabs>
      </Paper>

      {/* Tab Panels */}
      <TabPanel value={tabValue} index={0}>
        {renderFavoritesList(recordFavorites, 'record')}
      </TabPanel>
      <TabPanel value={tabValue} index={1}>
        {renderFavoritesList(entityFavorites, 'entity')}
      </TabPanel>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Remove from Favorites?</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to remove this item from your favorites?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={() => favoriteToDelete && deleteMutation.mutate(favoriteToDelete.id)}
            color="error"
            variant="contained"
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? 'Removing...' : 'Remove'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default function FavoritesPage() {
  return (
    <ProtectedRoute>
      <FavoritesContent />
    </ProtectedRoute>
  );
}
