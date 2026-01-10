'use client';

import { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Chip,
  Skeleton,
  Button,
  Divider,
  Alert,
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import BusinessIcon from '@mui/icons-material/Business';
import HomeIcon from '@mui/icons-material/Home';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { apiService } from '../../services/api';

interface Entity {
  id: number;
  entity_name: string;
  entity_type: 'person' | 'company' | 'property';
  role?: string;
  confidence?: number;
  address?: string;
  city?: string;
  state?: string;
}

interface RelatedEntitiesProps {
  recordId: string;
  record?: any;
}

const entityColors = {
  person: '#2196F3',
  company: '#4CAF50',
  property: '#FF9800',
};

const EntityIcon = ({ type }: { type: string }) => {
  switch (type) {
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

export const RelatedEntities = ({ recordId, record }: RelatedEntitiesProps) => {
  const router = useRouter();

  // Fetch entities related to this record
  const { data: entitiesData, isLoading, error } = useQuery({
    queryKey: ['recordEntities', recordId],
    queryFn: async () => {
      try {
        // Try to fetch entities related to this record
        // This would typically be a dedicated endpoint like /records/{id}/entities
        // For now, we'll extract from record data or use mock data

        // Check if record has entity data embedded
        if (record?.data?.entities) {
          return record.data.entities;
        }

        // Extract from standard fields like grantor, grantee
        const extractedEntities: Entity[] = [];

        if (record?.data?.grantor) {
          extractedEntities.push({
            id: 0,
            entity_name: record.data.grantor,
            entity_type: 'person',
            role: 'Grantor',
            confidence: 0.9,
          });
        }

        if (record?.data?.grantee) {
          extractedEntities.push({
            id: 0,
            entity_name: record.data.grantee,
            entity_type: 'person',
            role: 'Grantee',
            confidence: 0.9,
          });
        }

        if (record?.data?.borrower) {
          extractedEntities.push({
            id: 0,
            entity_name: record.data.borrower,
            entity_type: 'person',
            role: 'Borrower',
            confidence: 0.9,
          });
        }

        if (record?.data?.lender) {
          extractedEntities.push({
            id: 0,
            entity_name: record.data.lender,
            entity_type: 'company',
            role: 'Lender',
            confidence: 0.95,
          });
        }

        if (record?.data?.property_address) {
          extractedEntities.push({
            id: 0,
            entity_name: record.data.property_address,
            entity_type: 'property',
            role: 'Subject Property',
            confidence: 1.0,
            address: record.data.property_address,
            city: record.data.city,
            state: record.data.state,
          });
        }

        if (extractedEntities.length > 0) {
          return extractedEntities;
        }

        // Return mock data for demonstration
        return [
          {
            id: 1,
            entity_name: 'John Smith',
            entity_type: 'person',
            role: 'Grantor',
            confidence: 0.95,
          },
          {
            id: 2,
            entity_name: 'ABC Lending Corp',
            entity_type: 'company',
            role: 'Lender',
            confidence: 0.98,
          },
          {
            id: 3,
            entity_name: '123 Main Street',
            entity_type: 'property',
            role: 'Subject Property',
            address: '123 Main St',
            city: 'Houston',
            state: 'TX',
            confidence: 1.0,
          },
        ];
      } catch (err) {
        console.warn('Failed to fetch related entities:', err);
        return [];
      }
    },
    enabled: !!recordId,
  });

  const entities = entitiesData || [];

  const handleEntityClick = (entity: Entity) => {
    if (entity.id > 0) {
      router.push(`/network?entityId=${entity.id}`);
    }
  };

  const handleViewNetwork = () => {
    router.push(`/network?recordId=${recordId}`);
  };

  if (isLoading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
          Related Entities
        </Typography>
        <Skeleton variant="rectangular" height={60} sx={{ borderRadius: 1, mb: 1 }} />
        <Skeleton variant="rectangular" height={60} sx={{ borderRadius: 1, mb: 1 }} />
        <Skeleton variant="rectangular" height={60} sx={{ borderRadius: 1 }} />
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Related Entities
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {entities.length} found
        </Typography>
      </Box>

      {error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Unable to load entity relationships
        </Alert>
      )}

      {entities.length === 0 ? (
        <Alert severity="info">
          No entities have been linked to this record yet
        </Alert>
      ) : (
        <>
          <List dense sx={{ mx: -3, mb: 2 }}>
            {entities.map((entity: Entity, index: number) => {
              const color = entityColors[entity.entity_type] || entityColors.person;
              return (
                <ListItem key={entity.id || index} disablePadding>
                  <ListItemButton
                    onClick={() => handleEntityClick(entity)}
                    disabled={entity.id === 0}
                    sx={{
                      px: 3,
                      '&:hover': { backgroundColor: `${color}10` },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 40, color }}>
                      <EntityIcon type={entity.entity_type} />
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2" fontWeight={500}>
                            {entity.entity_name}
                          </Typography>
                          {entity.role && (
                            <Chip
                              label={entity.role}
                              size="small"
                              sx={{
                                height: 20,
                                fontSize: '0.7rem',
                                backgroundColor: `${color}20`,
                                color: color,
                              }}
                            />
                          )}
                        </Box>
                      }
                      secondary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                          <Chip
                            label={entity.entity_type}
                            size="small"
                            variant="outlined"
                            sx={{ height: 18, fontSize: '0.65rem', textTransform: 'capitalize' }}
                          />
                          {entity.confidence && (
                            <Typography variant="caption" color="text.secondary">
                              {Math.round(entity.confidence * 100)}% match
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>

          <Divider sx={{ mx: -3, mb: 2 }} />

          <Button
            fullWidth
            variant="outlined"
            startIcon={<AccountTreeIcon />}
            onClick={handleViewNetwork}
            size="small"
          >
            View Full Network
          </Button>
        </>
      )}
    </Paper>
  );
};
