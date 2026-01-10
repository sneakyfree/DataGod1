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
import DescriptionIcon from '@mui/icons-material/Description';
import HomeIcon from '@mui/icons-material/Home';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import GavelIcon from '@mui/icons-material/Gavel';
import BusinessIcon from '@mui/icons-material/Business';
import ReceiptIcon from '@mui/icons-material/Receipt';
import SearchIcon from '@mui/icons-material/Search';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { apiService } from '../../services/api';

interface RelatedRecord {
  id: number;
  title: string;
  record_type: string;
  date?: string;
  amount?: number;
  similarity_reason?: string;
  similarity_score?: number;
}

interface RelatedRecordsProps {
  recordId: string;
  record?: any;
}

const recordTypeIcons: Record<string, React.ReactNode> = {
  mortgage: <AccountBalanceIcon />,
  deed: <HomeIcon />,
  lien: <GavelIcon />,
  business: <BusinessIcon />,
  tax: <ReceiptIcon />,
  default: <DescriptionIcon />,
};

const recordTypeColors: Record<string, string> = {
  mortgage: '#1976d2',
  deed: '#388e3c',
  lien: '#f57c00',
  business: '#7b1fa2',
  tax: '#0288d1',
  court: '#d32f2f',
  default: '#616161',
};

const getRecordIcon = (type: string) => {
  return recordTypeIcons[type.toLowerCase()] || recordTypeIcons.default;
};

const getRecordColor = (type: string) => {
  return recordTypeColors[type.toLowerCase()] || recordTypeColors.default;
};

export const RelatedRecords = ({ recordId, record }: RelatedRecordsProps) => {
  const router = useRouter();

  // Fetch related records
  const { data: relatedData, isLoading, error } = useQuery({
    queryKey: ['relatedRecords', recordId],
    queryFn: async () => {
      try {
        // Try to fetch related records from API
        // This would typically use an endpoint like /records/{id}/related
        // For now, we'll construct a search query based on record metadata

        if (record?.data?.property_address) {
          // Search for records with same property address
          const response = await apiService.searchRecords({
            query: record.data.property_address,
            limit: 5,
          });

          const relatedRecords = response.data.results || response.data || [];
          // Filter out the current record and add similarity reason
          return relatedRecords
            .filter((r: any) => String(r.id) !== recordId)
            .slice(0, 5)
            .map((r: any) => ({
              ...r,
              similarity_reason: 'Same property address',
              similarity_score: 0.9,
            }));
        }

        // If we have entities, search for records with same entities
        if (record?.data?.grantor || record?.data?.grantee) {
          const searchTerm = record.data.grantor || record.data.grantee;
          const response = await apiService.searchRecords({
            query: searchTerm,
            limit: 5,
          });

          const relatedRecords = response.data.results || response.data || [];
          return relatedRecords
            .filter((r: any) => String(r.id) !== recordId)
            .slice(0, 5)
            .map((r: any) => ({
              ...r,
              similarity_reason: 'Same party involved',
              similarity_score: 0.85,
            }));
        }

        // Search by jurisdiction if available
        if (record?.jurisdiction_id) {
          const response = await apiService.searchRecords({
            jurisdictionId: record.jurisdiction_id,
            recordType: record.record_type,
            limit: 5,
          });

          const relatedRecords = response.data.results || response.data || [];
          return relatedRecords
            .filter((r: any) => String(r.id) !== recordId)
            .slice(0, 5)
            .map((r: any) => ({
              ...r,
              similarity_reason: 'Same jurisdiction & type',
              similarity_score: 0.7,
            }));
        }

        // Return mock data for demonstration
        return [
          {
            id: 1001,
            title: 'Previous Mortgage Filing',
            record_type: 'mortgage',
            date: '2023-06-15',
            amount: 380000,
            similarity_reason: 'Same property',
            similarity_score: 0.95,
          },
          {
            id: 1002,
            title: 'Property Tax Assessment',
            record_type: 'tax',
            date: '2024-01-10',
            amount: 4500,
            similarity_reason: 'Same address',
            similarity_score: 0.9,
          },
          {
            id: 1003,
            title: 'Lien Release Document',
            record_type: 'lien',
            date: '2023-09-20',
            amount: 15000,
            similarity_reason: 'Same grantor',
            similarity_score: 0.85,
          },
        ];
      } catch (err) {
        console.warn('Failed to fetch related records:', err);
        return [];
      }
    },
    enabled: !!recordId,
  });

  const relatedRecords = relatedData || [];

  const handleRecordClick = (relatedRecordId: number) => {
    router.push(`/records/${relatedRecordId}`);
  };

  const handleSearchMore = () => {
    // Navigate to search with pre-filled query based on current record
    const searchQuery = record?.data?.property_address || record?.title || '';
    router.push(`/search?q=${encodeURIComponent(searchQuery)}`);
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Unknown date';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatAmount = (amount?: number) => {
    if (!amount) return null;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  if (isLoading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
          Related Records
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
          Related Records
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {relatedRecords.length} found
        </Typography>
      </Box>

      {error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Unable to load related records
        </Alert>
      )}

      {relatedRecords.length === 0 ? (
        <Alert severity="info">
          No related records found
        </Alert>
      ) : (
        <>
          <List dense sx={{ mx: -3, mb: 2 }}>
            {relatedRecords.map((relatedRecord: RelatedRecord, index: number) => {
              const color = getRecordColor(relatedRecord.record_type);
              return (
                <ListItem key={relatedRecord.id || index} disablePadding>
                  <ListItemButton
                    onClick={() => handleRecordClick(relatedRecord.id)}
                    sx={{
                      px: 3,
                      '&:hover': { backgroundColor: `${color}10` },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 40, color }}>
                      {getRecordIcon(relatedRecord.record_type)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2" fontWeight={500} noWrap sx={{ maxWidth: 180 }}>
                            {relatedRecord.title}
                          </Typography>
                        </Box>
                      }
                      secondary={
                        <Box sx={{ mt: 0.5 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                            <Chip
                              label={relatedRecord.record_type}
                              size="small"
                              sx={{
                                height: 18,
                                fontSize: '0.65rem',
                                textTransform: 'capitalize',
                                backgroundColor: `${color}15`,
                                color: color,
                              }}
                            />
                            <Typography variant="caption" color="text.secondary">
                              {formatDate(relatedRecord.date)}
                            </Typography>
                            {relatedRecord.amount && (
                              <Typography variant="caption" color="text.secondary">
                                • {formatAmount(relatedRecord.amount)}
                              </Typography>
                            )}
                          </Box>
                          {relatedRecord.similarity_reason && (
                            <Typography
                              variant="caption"
                              sx={{
                                color: 'primary.main',
                                display: 'block',
                                mt: 0.5,
                                fontStyle: 'italic',
                              }}
                            >
                              {relatedRecord.similarity_reason}
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
            startIcon={<SearchIcon />}
            onClick={handleSearchMore}
            size="small"
          >
            Search for More
          </Button>
        </>
      )}
    </Paper>
  );
};
