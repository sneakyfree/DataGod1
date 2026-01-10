'use client';

import { Box, Paper, Typography, List, ListItem, ListItemText, Divider, CircularProgress, Chip, useMediaQuery, useTheme } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/api';

export const RecentRecords = ({ limit = 5 }: { limit?: number }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  // Fetch real records from API
  const { data: records, isLoading, error } = useQuery({
    queryKey: ['recentRecords', limit],
    queryFn: () => apiService.getRecords({ limit, page: 1 }).then(res => res.data.records || []),
    retry: 3,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (error) {
    return (
      <Typography variant="body2" color="error" sx={{ p: 2 }}>
        Failed to load recent records
      </Typography>
    );
  }

  const displayRecords = (records || []).slice(0, limit);

  return (
    <List sx={{ p: { xs: 0, sm: 1 } }}>
      {displayRecords.map((record: any, index: number) => (
        <Box key={record.id}>
          <ListItem
            sx={{
              flexDirection: { xs: 'column', sm: 'row' },
              alignItems: { xs: 'flex-start', sm: 'center' },
              py: { xs: 1.5, sm: 1 },
              px: { xs: 1, sm: 2 },
            }}
          >
            <ListItemText
              primary={
                <Typography
                  variant="body1"
                  sx={{
                    fontSize: { xs: '0.875rem', sm: '1rem' },
                    fontWeight: 500,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    maxWidth: { xs: '100%', sm: '300px', md: '400px' }
                  }}
                >
                  {record.title || record.name || 'Untitled Record'}
                </Typography>
              }
              secondary={
                <Box sx={{
                  display: 'flex',
                  flexDirection: { xs: 'column', sm: 'row' },
                  gap: { xs: 0.5, sm: 1 },
                  mt: 0.5
                }}>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    <Chip
                      label={record.type || record.category || 'Unknown'}
                      size="small"
                      variant="outlined"
                      sx={{ fontSize: { xs: '0.65rem', sm: '0.75rem' }, height: { xs: 20, sm: 24 } }}
                    />
                    <Chip
                      label={record.jurisdiction || record.location || 'Unknown'}
                      size="small"
                      color="primary"
                      variant="outlined"
                      sx={{ fontSize: { xs: '0.65rem', sm: '0.75rem' }, height: { xs: 20, sm: 24 } }}
                    />
                  </Box>
                  <Typography
                    component="span"
                    variant="caption"
                    color="text.secondary"
                    sx={{ fontSize: { xs: '0.65rem', sm: '0.75rem' } }}
                  >
                    {record.date || record.created_at || 'Unknown date'}
                  </Typography>
                </Box>
              }
              sx={{ my: 0 }}
            />
          </ListItem>
          {limit > 1 && index < displayRecords.length - 1 && <Divider />}
        </Box>
      ))}
      {displayRecords.length === 0 && (
        <ListItem>
          <Typography variant="body2" color="text.secondary">
            No records found
          </Typography>
        </ListItem>
      )}
    </List>
  );
};
