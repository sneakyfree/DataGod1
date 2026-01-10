'use client';

import { useState, Suspense } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  TextField,
  InputAdornment,
  Grid,
  CircularProgress,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Alert,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import { useSearchParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { ProtectedRoute } from '../../context/AuthContext';
import { EntityNetworkGraph, EntityDetailPanel } from '../../components/entity';
import { apiService } from '../../services/api';

interface Entity {
  id: number;
  entity_name: string;
  entity_type: 'person' | 'company' | 'property';
  address?: string;
  city?: string;
  state?: string;
}

function NetworkContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const entityIdParam = searchParams.get('entity');

  const [searchQuery, setSearchQuery] = useState('');
  const [entityType, setEntityType] = useState<string>('all');
  const [selectedEntityId, setSelectedEntityId] = useState<number | null>(
    entityIdParam ? parseInt(entityIdParam) : null
  );
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [detailPanelOpen, setDetailPanelOpen] = useState(false);
  const [networkDepth, setNetworkDepth] = useState(2);

  // Search for entities
  const { data: searchResults, isLoading: searchLoading } = useQuery({
    queryKey: ['entitySearch', searchQuery, entityType],
    queryFn: () =>
      apiService.getEntities({
        name: searchQuery,
        entity_type: entityType !== 'all' ? entityType : undefined,
        limit: 20,
      }).then((res) => res.data),
    enabled: searchQuery.length >= 2,
  });

  const entities = searchResults?.entities || [];

  const handleEntitySelect = (entity: Entity) => {
    setSelectedEntityId(entity.id);
    setSelectedEntity(entity);
    router.push(`/network?entity=${entity.id}`, { scroll: false });
  };

  const handleNodeClick = (entity: Entity) => {
    setSelectedEntity(entity);
    setDetailPanelOpen(true);
  };

  const handleViewNetwork = (entityId: number) => {
    setSelectedEntityId(entityId);
    setDetailPanelOpen(false);
    router.push(`/network?entity=${entityId}`, { scroll: false });
  };

  const handleViewRecord = (recordId: number) => {
    router.push(`/records/${recordId}`);
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AccountTreeIcon color="primary" />
          Entity Network
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Explore connections between people, companies, and properties. Click on any node to view details.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Left sidebar - Search */}
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
              Find Entity
            </Typography>
            <TextField
              fullWidth
              placeholder="Search by name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
              sx={{ mb: 2 }}
            />
            <FormControl fullWidth size="small" sx={{ mb: 2 }}>
              <InputLabel>Entity Type</InputLabel>
              <Select
                value={entityType}
                onChange={(e) => setEntityType(e.target.value)}
                label="Entity Type"
              >
                <MenuItem value="all">All Types</MenuItem>
                <MenuItem value="person">Person</MenuItem>
                <MenuItem value="company">Company</MenuItem>
                <MenuItem value="property">Property</MenuItem>
              </Select>
            </FormControl>

            {/* Search Results */}
            {searchLoading && (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                <CircularProgress size={24} />
              </Box>
            )}

            {entities.length > 0 && (
              <Box sx={{ maxHeight: 300, overflowY: 'auto' }}>
                {entities.map((entity: Entity) => (
                  <Box
                    key={entity.id}
                    sx={{
                      p: 1.5,
                      mb: 1,
                      borderRadius: 1,
                      backgroundColor: selectedEntityId === entity.id ? 'primary.light' : 'grey.50',
                      cursor: 'pointer',
                      '&:hover': {
                        backgroundColor: selectedEntityId === entity.id ? 'primary.light' : 'grey.100',
                      },
                    }}
                    onClick={() => handleEntitySelect(entity)}
                  >
                    <Typography variant="body2" fontWeight={500}>
                      {entity.entity_name}
                    </Typography>
                    <Chip
                      label={entity.entity_type}
                      size="small"
                      sx={{ mt: 0.5, textTransform: 'capitalize' }}
                    />
                  </Box>
                ))}
              </Box>
            )}

            {searchQuery.length >= 2 && !searchLoading && entities.length === 0 && (
              <Alert severity="info" sx={{ mt: 2 }}>
                No entities found matching "{searchQuery}"
              </Alert>
            )}
          </Paper>

          {/* Network Controls */}
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
              Network Settings
            </Typography>
            <FormControl fullWidth size="small" sx={{ mb: 2 }}>
              <InputLabel>Connection Depth</InputLabel>
              <Select
                value={networkDepth}
                onChange={(e) => setNetworkDepth(Number(e.target.value))}
                label="Connection Depth"
              >
                <MenuItem value={1}>1 hop</MenuItem>
                <MenuItem value={2}>2 hops (recommended)</MenuItem>
                <MenuItem value={3}>3 hops</MenuItem>
              </Select>
            </FormControl>
            <Typography variant="caption" color="text.secondary">
              Higher depth shows more connections but may be slower.
            </Typography>
          </Paper>
        </Grid>

        {/* Main content - Network Graph */}
        <Grid item xs={12} md={9}>
          <Paper sx={{ height: 'calc(100vh - 250px)', minHeight: 500 }}>
            <EntityNetworkGraph
              centerId={selectedEntityId || undefined}
              depth={networkDepth}
              width={900}
              height={600}
              onNodeClick={handleNodeClick}
            />
          </Paper>
        </Grid>
      </Grid>

      {/* Entity Detail Panel */}
      <EntityDetailPanel
        entity={selectedEntity}
        open={detailPanelOpen}
        onClose={() => setDetailPanelOpen(false)}
        onViewNetwork={handleViewNetwork}
        onViewRecord={handleViewRecord}
      />
    </Container>
  );
}

export default function NetworkPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={
        <Container maxWidth="xl" sx={{ py: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
            <CircularProgress />
          </Box>
        </Container>
      }>
        <NetworkContent />
      </Suspense>
    </ProtectedRoute>
  );
}
