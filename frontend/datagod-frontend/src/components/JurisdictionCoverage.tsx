'use client';

import { Box, Paper, Typography, LinearProgress, List, ListItem, ListItemText, CircularProgress } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/api';

export const JurisdictionCoverage = () => {
  // Fetch real jurisdiction data from API
  const { data: jurisdictions, isLoading, error } = useQuery({
    queryKey: ['jurisdictions'],
    queryFn: () => apiService.getJurisdictions().then(res => res.data),
    retry: 3,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  // Process jurisdiction data to get coverage statistics
  const coverageData = jurisdictions ? processJurisdictionData(jurisdictions) : [];

  function processJurisdictionData(jurisdictions: any[]) {
    // Group by state and calculate coverage
    const stateStats: Record<string, { total: number; covered: number }> = {};

    jurisdictions.forEach((jurisdiction: any) => {
      const state = jurisdiction.state || jurisdiction.name?.split(',')[1]?.trim() || 'Unknown';
      if (!stateStats[state]) {
        stateStats[state] = { total: 0, covered: 0 };
      }
      stateStats[state].total++;
      if (jurisdiction.status === 'active' || jurisdiction.is_active) {
        stateStats[state].covered++;
      }
    });

    // Convert to array and calculate percentages
    return Object.entries(stateStats)
      .map(([state, stats]) => ({
        state,
        counties: stats.total,
        covered: stats.covered,
        percentage: Math.round((stats.covered / stats.total) * 100),
      }))
      .sort((a, b) => b.percentage - a.percentage)
      .slice(0, 5); // Top 5 states
  }

  const totalJurisdictions = coverageData.reduce((sum, state) => sum + state.counties, 0);
  const totalStates = coverageData.length;

  return (
    <Box>
      <Typography variant="subtitle2" gutterBottom>
        Top 5 States by Coverage
      </Typography>
      <List dense>
        {coverageData.map((state, index) => (
          <ListItem key={index} sx={{ py: 0.5 }}>
            <ListItemText
              primary={
                <Typography variant="body2">
                  {state.state} ({state.percentage}%)
                </Typography>
              }
              secondary={
                <LinearProgress
                  variant="determinate"
                  value={state.percentage}
                  sx={{ height: 6, borderRadius: 3, my: 0.5 }}
                />
              }
            />
          </ListItem>
        ))}
      </List>

      <Box sx={{ mt: 2, p: 1, backgroundColor: 'background.paper' }}>
        <Typography variant="caption" display="block" gutterBottom>
          Total Coverage
        </Typography>
        <Typography variant="h6" align="center">
          {totalJurisdictions.toLocaleString()} Jurisdictions
        </Typography>
        <Typography variant="body2" align="center" color="text.secondary">
          Across {totalStates} States
        </Typography>
      </Box>
    </Box>
  );
};
