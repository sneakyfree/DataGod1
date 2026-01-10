'use client';

import { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Grid,
  Container,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Pagination,
} from '@mui/material';
import { Search as SearchIcon, FilterList, Clear } from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';
import { ProtectedRoute } from '../../context/AuthContext';

interface SearchFilters {
  query: string;
  jurisdiction_ids: number[];
  record_types: string[];
  date_from: string;
  date_to: string;
  page: number;
  page_size: number;
}

const recordTypes = [
  'Deed',
  'Mortgage',
  'Lien',
  'Tax Record',
  'Court Filing',
  'Business Filing',
  'Property Assessment',
  'Other',
];

function SearchContent() {
  const [filters, setFilters] = useState<SearchFilters>({
    query: '',
    jurisdiction_ids: [],
    record_types: [],
    date_from: '',
    date_to: '',
    page: 1,
    page_size: 20,
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [hasSearched, setHasSearched] = useState(false);

  // Fetch jurisdictions for filter dropdown
  const { data: jurisdictions } = useQuery({
    queryKey: ['jurisdictions'],
    queryFn: () => apiService.getJurisdictions({ limit: 100 }).then(res => res.data.jurisdictions || []),
    staleTime: 10 * 60 * 1000,
  });

  // Search query
  const { data: searchResults, isLoading, error, refetch } = useQuery({
    queryKey: ['search', filters],
    queryFn: () => apiService.search(filters.query, {
      jurisdiction_ids: filters.jurisdiction_ids.length > 0 ? filters.jurisdiction_ids : undefined,
      record_types: filters.record_types.length > 0 ? filters.record_types : undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
      page: filters.page,
      page_size: filters.page_size,
    }).then(res => res.data),
    enabled: hasSearched && filters.query.length > 0,
    staleTime: 2 * 60 * 1000,
  });

  const handleSearch = () => {
    if (searchQuery.trim()) {
      setFilters(prev => ({ ...prev, query: searchQuery.trim(), page: 1 }));
      setHasSearched(true);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleClearFilters = () => {
    setFilters({
      query: '',
      jurisdiction_ids: [],
      record_types: [],
      date_from: '',
      date_to: '',
      page: 1,
      page_size: 20,
    });
    setSearchQuery('');
    setHasSearched(false);
  };

  const handlePageChange = (_: React.ChangeEvent<unknown>, page: number) => {
    setFilters(prev => ({ ...prev, page }));
  };

  const records = searchResults?.records || [];
  const totalPages = Math.ceil((searchResults?.total || 0) / filters.page_size);

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Search Records
      </Typography>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Search across millions of public records from jurisdictions nationwide.
      </Typography>

      {/* Search Bar */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <TextField
            fullWidth
            label="Search records"
            placeholder="Enter names, addresses, document numbers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
            sx={{ flexGrow: 1, minWidth: 300 }}
          />
          <Button
            variant="contained"
            color="primary"
            onClick={handleSearch}
            disabled={!searchQuery.trim() || isLoading}
            startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
            sx={{ px: 4 }}
          >
            Search
          </Button>
        </Box>

        {/* Filters */}
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle2" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <FilterList fontSize="small" /> Filters
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Record Type</InputLabel>
                <Select
                  multiple
                  value={filters.record_types}
                  onChange={(e) => setFilters(prev => ({ ...prev, record_types: e.target.value as string[] }))}
                  label="Record Type"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {recordTypes.map((type) => (
                    <MenuItem key={type} value={type}>
                      {type}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                size="small"
                label="Date From"
                type="date"
                value={filters.date_from}
                onChange={(e) => setFilters(prev => ({ ...prev, date_from: e.target.value }))}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                size="small"
                label="Date To"
                type="date"
                value={filters.date_to}
                onChange={(e) => setFilters(prev => ({ ...prev, date_to: e.target.value }))}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Button
                variant="outlined"
                color="secondary"
                onClick={handleClearFilters}
                startIcon={<Clear />}
                fullWidth
              >
                Clear Filters
              </Button>
            </Grid>
          </Grid>
        </Box>
      </Paper>

      {/* Error State */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          An error occurred while searching. Please try again.
        </Alert>
      )}

      {/* Results */}
      {hasSearched && (
        <Box>
          {isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : records.length > 0 ? (
            <>
              <Typography variant="subtitle1" sx={{ mb: 2 }}>
                Found {searchResults?.total || 0} results for &quot;{filters.query}&quot;
              </Typography>

              <Grid container spacing={2}>
                {records.map((record: any) => (
                  <Grid item xs={12} key={record.id}>
                    <Card variant="outlined">
                      <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 1 }}>
                          <Box>
                            <Typography variant="h6" sx={{ mb: 1 }}>
                              {record.title || record.name || 'Untitled Record'}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                              {record.description || 'No description available'}
                            </Typography>
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                              {record.type && <Chip label={record.type} size="small" variant="outlined" />}
                              {record.jurisdiction && <Chip label={record.jurisdiction} size="small" color="primary" variant="outlined" />}
                              {record.date && <Chip label={record.date} size="small" variant="outlined" />}
                            </Box>
                          </Box>
                          <Button variant="outlined" size="small" href={`/records/${record.id}`}>
                            View Details
                          </Button>
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>

              {/* Pagination */}
              {totalPages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                  <Pagination
                    count={totalPages}
                    page={filters.page}
                    onChange={handlePageChange}
                    color="primary"
                  />
                </Box>
              )}
            </>
          ) : (
            <Paper sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="h6" color="text.secondary">
                No results found
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Try adjusting your search terms or filters
              </Typography>
            </Paper>
          )}
        </Box>
      )}

      {/* Initial State */}
      {!hasSearched && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <SearchIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            Enter a search term to get started
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Search for names, addresses, document numbers, or any relevant keywords
          </Typography>
        </Paper>
      )}
    </Container>
  );
}

export default function SearchPage() {
  return (
    <ProtectedRoute>
      <SearchContent />
    </ProtectedRoute>
  );
}
