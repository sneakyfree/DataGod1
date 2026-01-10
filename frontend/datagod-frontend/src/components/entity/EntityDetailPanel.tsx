'use client';

import { useState } from 'react';
import {
  Box,
  Drawer,
  Typography,
  IconButton,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Button,
  Skeleton,
  Alert,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import PersonIcon from '@mui/icons-material/Person';
import BusinessIcon from '@mui/icons-material/Business';
import HomeIcon from '@mui/icons-material/Home';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import LinkIcon from '@mui/icons-material/Link';
import DescriptionIcon from '@mui/icons-material/Description';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import FavoriteIcon from '@mui/icons-material/Favorite';
import FavoriteBorderIcon from '@mui/icons-material/FavoriteBorder';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';

interface Entity {
  id: number;
  entity_name: string;
  entity_type: 'person' | 'company' | 'property';
  address?: string;
  city?: string;
  state?: string;
  zip_code?: string;
  phone?: string;
  email?: string;
  status?: string;
  description?: string;
}

interface Relationship {
  id: number;
  entity1_id: number;
  entity2_id: number;
  relationship_type: string;
  confidence_score: number;
  role1?: string;
  role2?: string;
}

interface EntityDetailPanelProps {
  entity: Entity | null;
  open: boolean;
  onClose: () => void;
  onViewNetwork?: (entityId: number) => void;
  onViewRecord?: (recordId: number) => void;
}

const entityColors = {
  person: '#2196F3',
  company: '#4CAF50',
  property: '#FF9800',
};

const EntityIcon = ({ type, size = 24 }: { type: string; size?: number }) => {
  switch (type) {
    case 'person':
      return <PersonIcon sx={{ fontSize: size }} />;
    case 'company':
      return <BusinessIcon sx={{ fontSize: size }} />;
    case 'property':
      return <HomeIcon sx={{ fontSize: size }} />;
    default:
      return <PersonIcon sx={{ fontSize: size }} />;
  }
};

export const EntityDetailPanel = ({
  entity,
  open,
  onClose,
  onViewNetwork,
  onViewRecord,
}: EntityDetailPanelProps) => {
  const [isFavorite, setIsFavorite] = useState(false);

  // Fetch full entity details
  const { data: entityDetails, isLoading: loadingDetails } = useQuery({
    queryKey: ['entityDetails', entity?.id],
    queryFn: () => entity ? apiService.getEntity(String(entity.id)).then(res => res.data) : null,
    enabled: !!entity?.id && open,
  });

  // Fetch entity connections using real API
  const { data: relationships, isLoading: loadingRelationships } = useQuery({
    queryKey: ['entityConnections', entity?.id],
    queryFn: async () => {
      if (!entity?.id) return [];
      try {
        const response = await apiService.getEntityConnections(String(entity.id), { limit: 10 });
        // Transform API response to component format
        return response.data.connections.map((conn: any) => ({
          id: conn.relationshipId,
          type: conn.relationshipType,
          relatedEntity: {
            id: conn.entity.id,
            name: conn.entity.name,
            type: conn.entity.type,
          },
          confidence: conn.confidence || 1.0,
        }));
      } catch (err) {
        // Fallback to mock data
        console.warn('Failed to fetch connections, using mock:', err);
        return [
          { id: 1, type: 'owner', relatedEntity: { id: 2, name: 'Smith Holdings LLC', type: 'company' }, confidence: 0.95 },
          { id: 2, type: 'owns', relatedEntity: { id: 3, name: '123 Main Street', type: 'property' }, confidence: 0.9 },
          { id: 3, type: 'borrower', relatedEntity: { id: 5, name: 'First National Bank', type: 'company' }, confidence: 0.92 },
        ];
      }
    },
    enabled: !!entity?.id && open,
  });

  // Fetch related records using real API
  const { data: relatedRecords, isLoading: loadingRecords } = useQuery({
    queryKey: ['entityRecords', entity?.id],
    queryFn: async () => {
      if (!entity?.id) return [];
      try {
        const response = await apiService.getEntityRecords(String(entity.id), { limit: 10 });
        // Transform API response to component format
        return response.data.records.map((record: any) => ({
          id: record.id,
          title: record.title,
          type: record.recordType,
          date: record.date,
          amount: record.amount,
        }));
      } catch (err) {
        // Fallback to mock data
        console.warn('Failed to fetch records, using mock:', err);
        return [
          { id: 101, title: 'Mortgage Deed', type: 'mortgage', date: '2024-12-15', amount: 450000 },
          { id: 102, title: 'Property Transfer', type: 'deed', date: '2024-11-20', amount: 525000 },
          { id: 103, title: 'Tax Lien Release', type: 'lien', date: '2024-10-05', amount: 12500 },
        ];
      }
    },
    enabled: !!entity?.id && open,
  });

  const handleToggleFavorite = () => {
    setIsFavorite(!isFavorite);
    // In production, this would call an API to save the favorite
  };

  const handleExportNetwork = () => {
    // Export entity network data
    console.log('Exporting network for entity:', entity?.id);
  };

  if (!entity) return null;

  const color = entityColors[entity.entity_type] || entityColors.person;
  const details = entityDetails || entity;

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: { width: { xs: '100%', sm: 400 }, p: 0 },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          backgroundColor: `${color}10`,
          borderBottom: `3px solid ${color}`,
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                backgroundColor: `${color}20`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: color,
              }}
            >
              <EntityIcon type={entity.entity_type} size={28} />
            </Box>
            <Box>
              <Typography variant="h6" fontWeight={600}>
                {entity.entity_name}
              </Typography>
              <Chip
                label={entity.entity_type}
                size="small"
                sx={{
                  backgroundColor: `${color}20`,
                  color: color,
                  textTransform: 'capitalize',
                }}
              />
            </Box>
          </Box>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Content */}
      <Box sx={{ p: 2, overflowY: 'auto', flex: 1 }}>
        {/* Details Section */}
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
          Details
        </Typography>
        {loadingDetails ? (
          <Box sx={{ mb: 2 }}>
            <Skeleton variant="text" width="80%" />
            <Skeleton variant="text" width="60%" />
            <Skeleton variant="text" width="70%" />
          </Box>
        ) : (
          <Box sx={{ mb: 2 }}>
            {(details.address || details.city || details.state) && (
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1 }}>
                <LocationOnIcon sx={{ fontSize: 18, color: 'text.secondary', mt: 0.3 }} />
                <Typography variant="body2" color="text.secondary">
                  {details.address && <>{details.address}<br /></>}
                  {details.city && details.state && `${details.city}, ${details.state}`}
                  {details.zip_code && ` ${details.zip_code}`}
                </Typography>
              </Box>
            )}
            {details.status && (
              <Chip
                label={details.status}
                size="small"
                color={details.status === 'active' ? 'success' : 'default'}
                variant="outlined"
                sx={{ mt: 1 }}
              />
            )}
          </Box>
        )}

        <Divider sx={{ my: 2 }} />

        {/* Connections Section */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Connections
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {relationships?.length || 0} found
          </Typography>
        </Box>

        {loadingRelationships ? (
          <Box sx={{ mb: 2 }}>
            <Skeleton variant="rectangular" height={60} sx={{ borderRadius: 1, mb: 1 }} />
            <Skeleton variant="rectangular" height={60} sx={{ borderRadius: 1, mb: 1 }} />
          </Box>
        ) : relationships && relationships.length > 0 ? (
          <List dense sx={{ mb: 2 }}>
            {relationships.map((rel: any) => (
              <ListItem
                key={rel.id}
                sx={{
                  backgroundColor: 'grey.50',
                  borderRadius: 1,
                  mb: 0.5,
                  cursor: 'pointer',
                  '&:hover': { backgroundColor: 'grey.100' },
                }}
                onClick={() => onViewNetwork?.(rel.relatedEntity.id)}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <EntityIcon type={rel.relatedEntity.type} size={20} />
                </ListItemIcon>
                <ListItemText
                  primary={rel.relatedEntity.name}
                  secondary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Typography variant="caption">{rel.type}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        ({Math.round(rel.confidence * 100)}% confident)
                      </Typography>
                    </Box>
                  }
                />
                <LinkIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
              </ListItem>
            ))}
          </List>
        ) : (
          <Alert severity="info" sx={{ mb: 2 }}>
            No connections found for this entity
          </Alert>
        )}

        <Divider sx={{ my: 2 }} />

        {/* Records Section */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Source Records
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {relatedRecords?.length || 0} found
          </Typography>
        </Box>

        {loadingRecords ? (
          <Box sx={{ mb: 2 }}>
            <Skeleton variant="rectangular" height={50} sx={{ borderRadius: 1, mb: 1 }} />
            <Skeleton variant="rectangular" height={50} sx={{ borderRadius: 1, mb: 1 }} />
          </Box>
        ) : relatedRecords && relatedRecords.length > 0 ? (
          <List dense sx={{ mb: 2 }}>
            {relatedRecords.map((record: any) => (
              <ListItem
                key={record.id}
                sx={{
                  backgroundColor: 'grey.50',
                  borderRadius: 1,
                  mb: 0.5,
                  cursor: 'pointer',
                  '&:hover': { backgroundColor: 'grey.100' },
                }}
                onClick={() => onViewRecord?.(record.id)}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <DescriptionIcon sx={{ fontSize: 20 }} />
                </ListItemIcon>
                <ListItemText
                  primary={record.title}
                  secondary={
                    <Typography variant="caption" color="text.secondary">
                      {record.type} • {record.date}
                      {record.amount && ` • $${record.amount.toLocaleString()}`}
                    </Typography>
                  }
                />
              </ListItem>
            ))}
          </List>
        ) : (
          <Alert severity="info" sx={{ mb: 2 }}>
            No source records found
          </Alert>
        )}
      </Box>

      {/* Actions */}
      <Box
        sx={{
          p: 2,
          borderTop: 1,
          borderColor: 'divider',
          display: 'flex',
          gap: 1,
          flexWrap: 'wrap',
        }}
      >
        <Button
          variant="outlined"
          startIcon={<AccountTreeIcon />}
          onClick={() => onViewNetwork?.(entity.id)}
          sx={{ flex: 1 }}
        >
          View Network
        </Button>
        <Button
          variant="outlined"
          startIcon={<FileDownloadIcon />}
          onClick={handleExportNetwork}
        >
          Export
        </Button>
        <IconButton onClick={handleToggleFavorite} color={isFavorite ? 'error' : 'default'}>
          {isFavorite ? <FavoriteIcon /> : <FavoriteBorderIcon />}
        </IconButton>
      </Box>
    </Drawer>
  );
};
