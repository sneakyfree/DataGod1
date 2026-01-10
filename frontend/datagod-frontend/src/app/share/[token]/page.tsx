'use client';

import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Paper,
  Chip,
  Alert,
  CircularProgress,
  Divider,
  Card,
  CardContent,
  Link as MuiLink,
  Avatar,
  Stack
} from '@mui/material';
import ShareIcon from '@mui/icons-material/Share';
import PersonIcon from '@mui/icons-material/Person';
import BusinessIcon from '@mui/icons-material/Business';
import DescriptionIcon from '@mui/icons-material/Description';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import PlaceIcon from '@mui/icons-material/Place';
import InfoIcon from '@mui/icons-material/Info';
import { apiService } from '../../../services/api';

interface SharedRecord {
  id: number;
  external_id?: string;
  record_type: string;
  title: string;
  description?: string;
  filing_date?: string;
  effective_date?: string;
  jurisdiction_id?: number;
  jurisdiction_name?: string;
  data?: Record<string, any>;
  parties?: string[];
  amounts?: Record<string, any>;
  status?: string;
}

interface SharedEntity {
  id: number;
  name: string;
  entity_type: string;
  normalized_name?: string;
  aliases?: string[];
  identifiers?: Record<string, any>;
  metadata?: Record<string, any>;
  created_at?: string;
}

interface SharedItemData {
  share_type: 'record' | 'entity';
  shared_by: string;
  message?: string;
  shared_at: string;
  record?: SharedRecord;
  entity?: SharedEntity;
}

function formatDate(dateString?: string) {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
}

function formatDateTime(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function getRecordTypeColor(type: string): 'primary' | 'secondary' | 'success' | 'warning' | 'info' {
  const colorMap: Record<string, 'primary' | 'secondary' | 'success' | 'warning' | 'info'> = {
    'mortgage': 'primary',
    'deed': 'secondary',
    'lien': 'warning',
    'judgment': 'warning',
    'property': 'success',
    'business': 'info'
  };
  return colorMap[type.toLowerCase()] || 'primary';
}

function getEntityTypeIcon(type: string) {
  switch (type.toLowerCase()) {
    case 'person':
      return <PersonIcon />;
    case 'business':
    case 'company':
    case 'corporation':
      return <BusinessIcon />;
    default:
      return <PersonIcon />;
  }
}

function SharedRecordView({ record }: { record: SharedRecord }) {
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <Avatar sx={{ bgcolor: 'primary.main', width: 56, height: 56 }}>
          <DescriptionIcon />
        </Avatar>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 600 }}>
            {record.title}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mt: 0.5, flexWrap: 'wrap' }}>
            <Chip
              label={record.record_type}
              size="small"
              color={getRecordTypeColor(record.record_type)}
            />
            {record.status && (
              <Chip
                label={record.status}
                size="small"
                variant="outlined"
              />
            )}
          </Box>
        </Box>
      </Box>

      {record.description && (
        <Paper sx={{ p: 2, mb: 3, bgcolor: 'grey.50' }}>
          <Typography variant="body1">{record.description}</Typography>
        </Paper>
      )}

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2, mb: 3 }}>
        <Card variant="outlined">
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <CalendarTodayIcon fontSize="small" color="action" />
              <Typography variant="subtitle2" color="text.secondary">Filing Date</Typography>
            </Box>
            <Typography variant="body1" sx={{ fontWeight: 500 }}>
              {formatDate(record.filing_date)}
            </Typography>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <CalendarTodayIcon fontSize="small" color="action" />
              <Typography variant="subtitle2" color="text.secondary">Effective Date</Typography>
            </Box>
            <Typography variant="body1" sx={{ fontWeight: 500 }}>
              {formatDate(record.effective_date)}
            </Typography>
          </CardContent>
        </Card>

        {record.jurisdiction_name && (
          <Card variant="outlined">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <PlaceIcon fontSize="small" color="action" />
                <Typography variant="subtitle2" color="text.secondary">Jurisdiction</Typography>
              </Box>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                {record.jurisdiction_name}
              </Typography>
            </CardContent>
          </Card>
        )}

        {record.external_id && (
          <Card variant="outlined">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <InfoIcon fontSize="small" color="action" />
                <Typography variant="subtitle2" color="text.secondary">Record ID</Typography>
              </Box>
              <Typography variant="body1" sx={{ fontWeight: 500, fontFamily: 'monospace' }}>
                {record.external_id}
              </Typography>
            </CardContent>
          </Card>
        )}
      </Box>

      {record.parties && record.parties.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
            Parties Involved
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {record.parties.map((party, index) => (
              <Chip key={index} label={party} variant="outlined" />
            ))}
          </Box>
        </Box>
      )}

      {record.amounts && Object.keys(record.amounts).length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
            Financial Details
          </Typography>
          <Paper variant="outlined" sx={{ p: 2 }}>
            {Object.entries(record.amounts).map(([key, value]) => (
              <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
                <Typography color="text.secondary" sx={{ textTransform: 'capitalize' }}>
                  {key.replace(/_/g, ' ')}
                </Typography>
                <Typography sx={{ fontWeight: 500 }}>
                  {typeof value === 'number'
                    ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
                    : String(value)
                  }
                </Typography>
              </Box>
            ))}
          </Paper>
        </Box>
      )}

      {record.data && Object.keys(record.data).length > 0 && (
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
            Additional Details
          </Typography>
          <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.875rem' }}>
              {JSON.stringify(record.data, null, 2)}
            </pre>
          </Paper>
        </Box>
      )}
    </Box>
  );
}

function SharedEntityView({ entity }: { entity: SharedEntity }) {
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <Avatar sx={{ bgcolor: 'secondary.main', width: 56, height: 56 }}>
          {getEntityTypeIcon(entity.entity_type)}
        </Avatar>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 600 }}>
            {entity.name}
          </Typography>
          <Chip
            label={entity.entity_type}
            size="small"
            color="secondary"
            sx={{ mt: 0.5 }}
          />
        </Box>
      </Box>

      {entity.aliases && entity.aliases.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
            Also Known As
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {entity.aliases.map((alias, index) => (
              <Chip key={index} label={alias} variant="outlined" size="small" />
            ))}
          </Box>
        </Box>
      )}

      {entity.identifiers && Object.keys(entity.identifiers).length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
            Identifiers
          </Typography>
          <Paper variant="outlined" sx={{ p: 2 }}>
            {Object.entries(entity.identifiers).map(([key, value]) => (
              <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
                <Typography color="text.secondary" sx={{ textTransform: 'capitalize' }}>
                  {key.replace(/_/g, ' ')}
                </Typography>
                <Typography sx={{ fontWeight: 500, fontFamily: 'monospace' }}>
                  {String(value)}
                </Typography>
              </Box>
            ))}
          </Paper>
        </Box>
      )}

      {entity.metadata && Object.keys(entity.metadata).length > 0 && (
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
            Additional Information
          </Typography>
          <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.875rem' }}>
              {JSON.stringify(entity.metadata, null, 2)}
            </pre>
          </Paper>
        </Box>
      )}
    </Box>
  );
}

export default function PublicSharePage() {
  const params = useParams();
  const token = params?.token as string;

  const { data: sharedData, isLoading, error } = useQuery<SharedItemData>({
    queryKey: ['shared-item', token],
    queryFn: async () => {
      const response = await apiService.getSharedItem(token);
      return response.data;
    },
    enabled: !!token,
    retry: false
  });

  if (isLoading) {
    return (
      <Box sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'grey.100'
      }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    const errorMessage = (error as any)?.response?.data?.detail || 'This share link is invalid or has expired.';
    return (
      <Box sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'grey.100',
        p: 3
      }}>
        <Paper sx={{ p: 4, maxWidth: 500, textAlign: 'center' }}>
          <ShareIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            Share Link Unavailable
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 3 }}>
            {errorMessage}
          </Typography>
          <MuiLink href="/" underline="hover">
            Go to DataGod Home
          </MuiLink>
        </Paper>
      </Box>
    );
  }

  if (!sharedData) {
    return null;
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'grey.100', py: 4 }}>
      <Box sx={{ maxWidth: 900, mx: 'auto', px: 3 }}>
        {/* Header */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
            <ShareIcon color="primary" />
            <Box>
              <Typography variant="h6" component="h1">
                Shared {sharedData.share_type === 'record' ? 'Record' : 'Entity'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Shared by {sharedData.shared_by} on {formatDateTime(sharedData.shared_at)}
              </Typography>
            </Box>
          </Stack>

          {sharedData.message && (
            <Alert severity="info" icon={false} sx={{ mt: 2 }}>
              <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                &quot;{sharedData.message}&quot;
              </Typography>
            </Alert>
          )}
        </Paper>

        {/* Content */}
        <Paper sx={{ p: 3 }}>
          {sharedData.share_type === 'record' && sharedData.record ? (
            <SharedRecordView record={sharedData.record} />
          ) : sharedData.share_type === 'entity' && sharedData.entity ? (
            <SharedEntityView entity={sharedData.entity} />
          ) : (
            <Alert severity="warning">
              The shared content is no longer available.
            </Alert>
          )}
        </Paper>

        {/* Footer */}
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            This content was shared via DataGod
          </Typography>
          <MuiLink href="/" underline="hover" sx={{ fontSize: '0.875rem' }}>
            Learn more about DataGod
          </MuiLink>
        </Box>
      </Box>
    </Box>
  );
}
