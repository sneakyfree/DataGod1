'use client';

import { Box, Paper, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/api';

export const DashboardStats = () => {
  // Fetch real data from API
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: () => apiService.getDashboardStats().then(res => res.data),
    retry: 3,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fallback data while loading
  const defaultStats = {
    totalRecords: 0,
    jurisdictions: 0,
    dataSources: 0,
    activeScrapers: 0,
  };

  const currentStats = stats || defaultStats;

  const statsItems = [
    { label: 'Total Records', value: currentStats.totalRecords, color: 'primary' },
    { label: 'Jurisdictions', value: currentStats.jurisdictions, color: 'secondary' },
    { label: 'Data Sources', value: currentStats.dataSources, color: 'success' },
    { label: 'Active Scrapers', value: currentStats.activeScrapers, color: 'info' },
  ];

  return (
    <Box sx={{
      display: 'grid',
      gridTemplateColumns: {
        xs: 'repeat(2, 1fr)',  // 2 columns on mobile
        sm: 'repeat(2, 1fr)',   // 2 columns on small tablets
        md: 'repeat(4, 1fr)',   // 4 columns on tablets+
      },
      gap: { xs: 1, sm: 2 }
    }}>
      {statsItems.map((item, index) => (
        <Paper key={index} sx={{
          p: { xs: 1.5, sm: 2 },
          textAlign: 'center',
          backgroundColor: `${item.color}.light`,
          color: `${item.color}.contrastText`,
          minHeight: { xs: 80, sm: 100 },
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
        }}>
          <Typography
            variant="caption"
            sx={{
              fontSize: { xs: '0.65rem', sm: '0.75rem' },
              fontWeight: 500
            }}
          >
            {item.label}
          </Typography>
          <Typography
            variant="h4"
            sx={{
              fontSize: { xs: '1.5rem', sm: '2rem', md: '2.125rem' },
              fontWeight: 'bold'
            }}
          >
            {item.value.toLocaleString()}
          </Typography>
        </Paper>
      ))}
    </Box>
  );
};
