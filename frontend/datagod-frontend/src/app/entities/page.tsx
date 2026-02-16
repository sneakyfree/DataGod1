'use client';

import { useState, useMemo } from 'react';
import {
    Box,
    Typography,
    Container,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TablePagination,
    TextField,
    InputAdornment,
    Chip,
    CircularProgress,
    Alert,
    Button,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    IconButton,
    Tooltip,
} from '@mui/material';
import {
    Search,
    Person,
    Business,
    Home,
    AccountBalance,
    Category,
    Visibility,
    Hub,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';
import { ProtectedRoute } from '../../context/AuthContext';

const entityTypeConfig: Record<string, { color: 'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'default'; icon: React.ReactNode }> = {
    person: { color: 'primary', icon: <Person fontSize="small" /> },
    company: { color: 'success', icon: <Business fontSize="small" /> },
    property: { color: 'warning', icon: <Home fontSize="small" /> },
    government: { color: 'info', icon: <AccountBalance fontSize="small" /> },
    other: { color: 'default', icon: <Category fontSize="small" /> },
};

function EntitiesContent() {
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(25);
    const [searchTerm, setSearchTerm] = useState('');
    const [typeFilter, setTypeFilter] = useState<string>('');

    const { data, isLoading, error } = useQuery({
        queryKey: ['entities', page, rowsPerPage, searchTerm, typeFilter],
        queryFn: () =>
            apiService.get('/entities', {
                params: {
                    page: page + 1,
                    limit: rowsPerPage,
                    search: searchTerm || undefined,
                    entity_type: typeFilter || undefined,
                },
            }).then((res: any) => res.data),
        staleTime: 2 * 60 * 1000,
    });

    const entities = data?.entities || data || [];
    const totalEntities = data?.total || entities.length || 0;

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

    return (
        <Container maxWidth="xl" sx={{ py: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
                <Box>
                    <Typography variant="h4" component="h1" gutterBottom>
                        Entities
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                        Browse people, companies, properties, and government entities in the database
                    </Typography>
                </Box>
            </Box>

            {/* Search & Filters */}
            <Paper sx={{ p: 2, mb: 3 }}>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <form onSubmit={handleSearch} style={{ flexGrow: 1, minWidth: 300 }}>
                        <TextField
                            fullWidth
                            placeholder="Search entities by name..."
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
                    </form>
                    <FormControl sx={{ minWidth: 180 }}>
                        <InputLabel>Entity Type</InputLabel>
                        <Select
                            value={typeFilter}
                            onChange={(e) => { setTypeFilter(e.target.value); setPage(0); }}
                            label="Entity Type"
                        >
                            <MenuItem value="">All Types</MenuItem>
                            <MenuItem value="person">Person</MenuItem>
                            <MenuItem value="company">Company</MenuItem>
                            <MenuItem value="property">Property</MenuItem>
                            <MenuItem value="government">Government</MenuItem>
                            <MenuItem value="other">Other</MenuItem>
                        </Select>
                    </FormControl>
                </Box>
            </Paper>

            {/* Error State */}
            {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                    Failed to load entities. Please try again.
                </Alert>
            )}

            {/* Entities Table */}
            <Paper>
                <TableContainer>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Name</TableCell>
                                <TableCell>Type</TableCell>
                                <TableCell>External ID</TableCell>
                                <TableCell>Description</TableCell>
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
                            ) : entities.length > 0 ? (
                                entities.map((entity: any) => {
                                    const config = entityTypeConfig[entity.entity_type || entity.type || 'other'] || entityTypeConfig.other;
                                    return (
                                        <TableRow key={entity.id} hover>
                                            <TableCell>
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                    {config.icon}
                                                    <Box>
                                                        <Typography variant="body2" fontWeight={500}>
                                                            {entity.entity_name || entity.name || 'Unknown Entity'}
                                                        </Typography>
                                                        <Typography variant="caption" color="text.secondary">
                                                            ID: {entity.id}
                                                        </Typography>
                                                    </Box>
                                                </Box>
                                            </TableCell>
                                            <TableCell>
                                                <Chip
                                                    label={entity.entity_type || entity.type || 'Unknown'}
                                                    size="small"
                                                    color={config.color}
                                                    variant="outlined"
                                                />
                                            </TableCell>
                                            <TableCell>
                                                <Typography variant="body2" color="text.secondary">
                                                    {entity.entity_id || entity.external_id || '—'}
                                                </Typography>
                                            </TableCell>
                                            <TableCell>
                                                <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 300 }}>
                                                    {entity.description || '—'}
                                                </Typography>
                                            </TableCell>
                                            <TableCell align="right">
                                                <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                                                    <Tooltip title="View Details">
                                                        <IconButton size="small" color="primary" href={`/entity/${entity.id}`}>
                                                            <Visibility />
                                                        </IconButton>
                                                    </Tooltip>
                                                    <Tooltip title="View Network">
                                                        <IconButton size="small" color="secondary" href={`/network?entity=${entity.id}`}>
                                                            <Hub />
                                                        </IconButton>
                                                    </Tooltip>
                                                </Box>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                                        <Typography color="text.secondary">
                                            No entities found
                                        </Typography>
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>

                <TablePagination
                    component="div"
                    count={totalEntities}
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

export default function EntitiesPage() {
    return (
        <ProtectedRoute>
            <EntitiesContent />
        </ProtectedRoute>
    );
}
