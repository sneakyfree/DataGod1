'use client';

import { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Container,
  TextField,
  InputAdornment,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Search,
  Visibility,
  Download,
  FilterList,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';
import { ProtectedRoute } from '../../context/AuthContext';

function RecordsContent() {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [searchTerm, setSearchTerm] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['records', page, rowsPerPage, searchTerm],
    queryFn: () => apiService.getRecords({
      page: page + 1,
      limit: rowsPerPage,
      search: searchTerm || undefined,
    }).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const records = data?.records || [];
  const totalRecords = data?.total || 0;

  const handleChangePage = (_: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, 'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'info'> = {
      'Deed': 'primary',
      'Mortgage': 'secondary',
      'Lien': 'warning',
      'Tax Record': 'info',
      'Court Filing': 'default',
    };
    return colors[type] || 'default';
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Records
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Browse and search through all available public records
          </Typography>
        </Box>

        <Button
          variant="outlined"
          startIcon={<Download />}
          disabled
        >
          Export
        </Button>
      </Box>

      {/* Search */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <form onSubmit={handleSearch}>
          <TextField
            fullWidth
            placeholder="Search records..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
              endAdornment: (
                <InputAdornment position="end">
                  <Tooltip title="Advanced Filters">
                    <IconButton size="small">
                      <FilterList />
                    </IconButton>
                  </Tooltip>
                </InputAdornment>
              ),
            }}
          />
        </form>
      </Paper>

      {/* Error State */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load records. Please try again.
        </Alert>
      )}

      {/* Records Table */}
      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Title</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Jurisdiction</TableCell>
                <TableCell>Date</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : records.length > 0 ? (
                records.map((record: any) => (
                  <TableRow key={record.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>
                        {record.title || record.name || 'Untitled Record'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        ID: {record.id}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={record.type || record.category || 'Unknown'}
                        size="small"
                        color={getTypeColor(record.type || record.category)}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      {record.jurisdiction || record.location || 'Unknown'}
                    </TableCell>
                    <TableCell>
                      {record.date || record.created_at || 'Unknown'}
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="View Details">
                        <IconButton
                          size="small"
                          color="primary"
                          href={`/records/${record.id}`}
                        >
                          <Visibility />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">
                      No records found
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          component="div"
          count={totalRecords}
          page={page}
          onPageChange={handleChangePage}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          rowsPerPageOptions={[10, 25, 50, 100]}
        />
      </Paper>
    </Container>
  );
}

export default function RecordsPage() {
  return (
    <ProtectedRoute>
      <RecordsContent />
    </ProtectedRoute>
  );
}
