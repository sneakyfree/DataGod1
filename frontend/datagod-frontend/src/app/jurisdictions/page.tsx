'use client';

import { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Container,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  LinearProgress,
} from '@mui/material';
import { Search, LocationOn } from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';
import { ProtectedRoute } from '../../context/AuthContext';

const US_STATES = [
  'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut',
  'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
  'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan',
  'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire',
  'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio',
  'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
  'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia',
  'Wisconsin', 'Wyoming',
];

function JurisdictionsContent() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedState, setSelectedState] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['jurisdictions', selectedState],
    queryFn: () => apiService.getJurisdictions({
      state: selectedState || undefined,
      limit: 200,
    }).then(res => res.data),
    staleTime: 5 * 60 * 1000,
  });

  const jurisdictions = data?.jurisdictions || [];

  // Filter by search term
  const filteredJurisdictions = jurisdictions.filter((j: any) =>
    j.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    j.state?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Group by state
  const groupedByState = filteredJurisdictions.reduce((acc: Record<string, any[]>, j: any) => {
    const state = j.state || 'Unknown';
    if (!acc[state]) acc[state] = [];
    acc[state].push(j);
    return acc;
  }, {});

  const getCoverageColor = (coverage: number) => {
    if (coverage >= 80) return 'success';
    if (coverage >= 50) return 'warning';
    return 'error';
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Jurisdictions
      </Typography>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Explore our coverage across counties and jurisdictions nationwide
      </Typography>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              placeholder="Search jurisdictions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>State</InputLabel>
              <Select
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
                label="State"
              >
                <MenuItem value="">All States</MenuItem>
                {US_STATES.map((state) => (
                  <MenuItem key={state} value={state}>
                    {state}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {/* Stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" color="primary">
              {data?.total || 0}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Total Jurisdictions
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" color="success.main">
              {Object.keys(groupedByState).length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              States Covered
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" color="info.main">
              {filteredJurisdictions.length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Showing
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Error State */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load jurisdictions. Please try again.
        </Alert>
      )}

      {/* Loading State */}
      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Jurisdictions Grid */}
      {!isLoading && filteredJurisdictions.length > 0 && (
        <Box>
          {(Object.entries(groupedByState) as [string, any[]][])
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([state, stateJurisdictions]) => (
            <Box key={state} sx={{ mb: 4 }}>
              <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <LocationOn color="primary" />
                {state}
                <Chip label={stateJurisdictions.length} size="small" color="primary" variant="outlined" />
              </Typography>

              <Grid container spacing={2}>
                {stateJurisdictions.map((jurisdiction: any) => (
                  <Grid item xs={12} sm={6} md={4} lg={3} key={jurisdiction.id}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>
                          {jurisdiction.name}
                        </Typography>

                        <Box sx={{ mb: 2 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">
                              Coverage
                            </Typography>
                            <Typography variant="caption" fontWeight={600}>
                              {jurisdiction.coverage || 0}%
                            </Typography>
                          </Box>
                          <LinearProgress
                            variant="determinate"
                            value={jurisdiction.coverage || 0}
                            color={getCoverageColor(jurisdiction.coverage || 0) as any}
                            sx={{ height: 6, borderRadius: 3 }}
                          />
                        </Box>

                        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                          {jurisdiction.record_count && (
                            <Chip
                              label={`${jurisdiction.record_count.toLocaleString()} records`}
                              size="small"
                              variant="outlined"
                            />
                          )}
                          {jurisdiction.data_sources && (
                            <Chip
                              label={`${jurisdiction.data_sources} sources`}
                              size="small"
                              variant="outlined"
                            />
                          )}
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Box>
          ))}
        </Box>
      )}

      {/* No Results */}
      {!isLoading && filteredJurisdictions.length === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No jurisdictions found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Try adjusting your search or filter
          </Typography>
        </Paper>
      )}
    </Container>
  );
}

export default function JurisdictionsPage() {
  return (
    <ProtectedRoute>
      <JurisdictionsContent />
    </ProtectedRoute>
  );
}
