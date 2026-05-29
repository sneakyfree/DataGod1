'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Box,
  Container,
  Typography,
  Paper,
  Chip,
  Button,
  Grid,
  Divider,
  Skeleton,
  Alert,
  Breadcrumbs,
  Link as MuiLink,
  IconButton,
  Tooltip,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ShareIcon from '@mui/icons-material/Share';
import FavoriteIcon from '@mui/icons-material/Favorite';
import FavoriteBorderIcon from '@mui/icons-material/FavoriteBorder';
import DownloadIcon from '@mui/icons-material/Download';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import DescriptionIcon from '@mui/icons-material/Description';
import LinkIcon from '@mui/icons-material/Link';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { apiService } from '../../../services/api';
import { ProtectedRoute } from '../../../context/AuthContext';
import { RecordDetailView } from '../../../components/records/RecordDetailView';
import { RelatedEntities } from '../../../components/records/RelatedEntities';
import { RelatedRecords } from '../../../components/records/RelatedRecords';
import { ShareModal } from '../../../components/data-sharing/ShareModal';
import { FavoriteButton } from '../../../components/favorites/FavoriteButton';
import CommentsPanel from '../../../components/data-sharing/CommentsPanel';
import LivePresence from '../../../components/common/LivePresence';

const recordTypeColors: Record<string, 'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'error'> = {
  mortgage: 'primary',
  deed: 'secondary',
  lien: 'warning',
  tax: 'info',
  court: 'default' as any,
  business: 'success',
  property: 'error',
};

function RecordDetailContent() {
  const params = useParams();
  const router = useRouter();
  const recordId = params.id as string;
  const [shareModalOpen, setShareModalOpen] = useState(false);

  const { data: record, isLoading, error } = useQuery({
    queryKey: ['record', recordId],
    queryFn: async () => {
      const response = await apiService.getRecord(recordId);
      return response.data;
    },
    enabled: !!recordId,
    retry: false,
  });

  const handleShare = () => {
    setShareModalOpen(true);
  };

  const handleExport = () => {
    // Export single record
    console.log('Exporting record:', recordId);
  };

  const handleViewNetwork = () => {
    // Navigate to network view centered on entities from this record
    router.push(`/network?recordId=${recordId}`);
  };

  if (isLoading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Skeleton variant="text" width={200} height={40} />
        <Skeleton variant="rectangular" height={300} sx={{ mt: 2, borderRadius: 2 }} />
        <Grid container spacing={3} sx={{ mt: 2 }}>
          <Grid item xs={12} md={8}>
            <Skeleton variant="rectangular" height={400} sx={{ borderRadius: 2 }} />
          </Grid>
          <Grid item xs={12} md={4}>
            <Skeleton variant="rectangular" height={300} sx={{ borderRadius: 2 }} />
          </Grid>
        </Grid>
      </Container>
    );
  }

  if (error || !record) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error ? 'Failed to load record. Please try again.' : 'Record not found.'}
        </Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => router.back()}>
          Go Back
        </Button>
      </Container>
    );
  }

  const recordType = record.record_type || record.type || 'document';
  const formattedDate = record.date
    ? new Date(record.date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
    : 'Unknown';
  const formattedAmount = record.amount
    ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(record.amount)
    : null;

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <MuiLink component={Link} href="/dashboard" color="inherit" underline="hover">
          Dashboard
        </MuiLink>
        <MuiLink component={Link} href="/records" color="inherit" underline="hover">
          Records
        </MuiLink>
        <Typography color="text.primary">
          {record.title?.substring(0, 30) || `Record #${recordId}`}
          {record.title?.length > 30 ? '...' : ''}
        </Typography>
      </Breadcrumbs>

      {/* Header */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 2 }}>
          <Box sx={{ flex: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              <Chip
                label={recordType.charAt(0).toUpperCase() + recordType.slice(1)}
                color={recordTypeColors[recordType.toLowerCase()] || 'default'}
                size="small"
              />
              {record.status && record.status !== 'active' && (
                <Chip label={record.status} variant="outlined" size="small" />
              )}
            </Box>
            <Typography variant="h4" component="h1" gutterBottom>
              {record.title || `Record #${recordId}`}
            </Typography>
            {record.description && (
              <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                {record.description}
              </Typography>
            )}

            {/* Quick Info */}
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mt: 2 }}>
              {record.jurisdiction && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <LocationOnIcon fontSize="small" color="action" />
                  <Typography variant="body2" color="text.secondary">
                    {typeof record.jurisdiction === 'object'
                      ? `${record.jurisdiction.name || ''}, ${record.jurisdiction.state || ''}`
                      : record.jurisdiction}
                  </Typography>
                </Box>
              )}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <CalendarTodayIcon fontSize="small" color="action" />
                <Typography variant="body2" color="text.secondary">
                  {formattedDate}
                </Typography>
              </Box>
              {formattedAmount && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <AttachMoneyIcon fontSize="small" color="action" />
                  <Typography variant="body2" color="text.secondary">
                    {formattedAmount}
                  </Typography>
                </Box>
              )}
            </Box>
          </Box>

          {/* Actions */}
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <LivePresence roomId={`record:${recordId}`} />
            <FavoriteButton type="record" itemId={parseInt(recordId)} />
            <Tooltip title="Share record">
              <IconButton onClick={handleShare}>
                <ShareIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Export record">
              <IconButton onClick={handleExport}>
                <DownloadIcon />
              </IconButton>
            </Tooltip>
            <Button
              variant="outlined"
              startIcon={<AccountTreeIcon />}
              onClick={handleViewNetwork}
              size="small"
            >
              View Network
            </Button>
          </Box>
        </Box>
      </Paper>

      {/* Main Content */}
      <Grid container spacing={3}>
        {/* Record Details */}
        <Grid item xs={12} md={8}>
          <RecordDetailView record={record} />
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          {/* Related Entities */}
          <RelatedEntities recordId={recordId} record={record} />

          {/* Related Records */}
          <Box sx={{ mt: 3 }}>
            <RelatedRecords recordId={recordId} record={record} />
          </Box>
        </Grid>
      </Grid>

      {/* Comments Section */}
      <Box sx={{ mt: 3 }}>
        <CommentsPanel recordId={parseInt(recordId)} />
      </Box>

      {/* Share Modal */}
      <ShareModal
        open={shareModalOpen}
        onClose={() => setShareModalOpen(false)}
        recordId={parseInt(recordId)}
        itemTitle={record.title}
        itemType="record"
      />
    </Container>
  );
}

export default function RecordDetailPage() {
  return (
    <ProtectedRoute>
      <RecordDetailContent />
    </ProtectedRoute>
  );
}
