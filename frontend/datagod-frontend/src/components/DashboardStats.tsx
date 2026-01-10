'use client';

import { Box, Paper, Typography, Tooltip } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/api';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

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

  // User-friendly labels with tooltips for clarity
  const statsItems = [
    {
      label: 'Total Records',
      value: currentStats.totalRecords,
      color: 'primary',
      tooltip: 'Public records available for search'
    },
    {
      label: 'Coverage Areas',
      value: currentStats.jurisdictions,
      color: 'secondary',
      tooltip: 'Counties and states with available records'
    },
    {
      label: 'Record Sources',
      value: currentStats.dataSources,
      color: 'success',
      tooltip: 'Different types of public record sources'
    },
    {
      label: 'Live Data Feeds',
      value: currentStats.activeScrapers,
      color: 'info',
      tooltip: 'Active connections bringing in fresh data'
    },
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
        <Tooltip key={index} title={item.tooltip} arrow placement="top">
          <Paper sx={{
            p: { xs: 1.5, sm: 2 },
            textAlign: 'center',
            backgroundColor: `${item.color}.light`,
            color: `${item.color}.contrastText`,
            minHeight: { xs: 80, sm: 100 },
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            cursor: 'help',
            transition: 'transform 0.2s, box-shadow 0.2s',
            '&:hover': {
              transform: 'translateY(-2px)',
              boxShadow: 2,
            },
          }}>
            <Typography
              variant="caption"
              sx={{
                fontSize: { xs: '0.65rem', sm: '0.75rem' },
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 0.5,
              }}
            >
              {item.label}
              <InfoOutlinedIcon sx={{ fontSize: 12, opacity: 0.7 }} />
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
        </Tooltip>
      ))}
    </Box>
  );
};
