'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControlLabel,
  Switch,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Box,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material';
import BookmarkAddIcon from '@mui/icons-material/BookmarkAdd';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../../services/api';

interface SearchParams {
  query?: string;
  filters?: {
    jurisdiction_ids?: number[];
    record_types?: string[];
    date_from?: string;
    date_to?: string;
    amount_min?: number;
    amount_max?: number;
  };
}

interface SaveSearchModalProps {
  open: boolean;
  onClose: () => void;
  searchParams: SearchParams;
  onSuccess?: () => void;
}

export const SaveSearchModal = ({
  open,
  onClose,
  searchParams,
  onSuccess,
}: SaveSearchModalProps) => {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [notifyOnNewResults, setNotifyOnNewResults] = useState(false);
  const [notificationFrequency, setNotificationFrequency] = useState('daily');
  const [error, setError] = useState<string | null>(null);

  const saveSearchMutation = useMutation({
    mutationFn: (data: {
      name: string;
      description?: string;
      search_params: SearchParams;
      notify_on_new_results: boolean;
      notification_frequency: string;
    }) => apiService.createSavedSearch(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['savedSearches'] });
      handleClose();
      onSuccess?.();
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to save search');
    },
  });

  const handleClose = () => {
    setName('');
    setDescription('');
    setNotifyOnNewResults(false);
    setNotificationFrequency('daily');
    setError(null);
    onClose();
  };

  const handleSave = () => {
    if (!name.trim()) {
      setError('Please enter a name for this search');
      return;
    }

    saveSearchMutation.mutate({
      name: name.trim(),
      description: description.trim() || undefined,
      search_params: searchParams,
      notify_on_new_results: notifyOnNewResults,
      notification_frequency: notificationFrequency,
    });
  };

  const getSearchSummary = () => {
    const parts: string[] = [];

    if (searchParams.query) {
      parts.push(`"${searchParams.query}"`);
    }

    if (searchParams.filters?.jurisdiction_ids?.length) {
      parts.push(`${searchParams.filters.jurisdiction_ids.length} jurisdiction(s)`);
    }

    if (searchParams.filters?.record_types?.length) {
      parts.push(searchParams.filters.record_types.join(', '));
    }

    if (searchParams.filters?.date_from || searchParams.filters?.date_to) {
      parts.push('date range');
    }

    if (searchParams.filters?.amount_min || searchParams.filters?.amount_max) {
      parts.push('amount range');
    }

    return parts.length > 0 ? parts.join(' + ') : 'All records';
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <BookmarkAddIcon color="primary" />
        Save This Search
      </DialogTitle>

      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Box sx={{ mb: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
            Search Criteria
          </Typography>
          <Typography variant="body2" fontWeight={500}>
            {getSearchSummary()}
          </Typography>
        </Box>

        <TextField
          autoFocus
          label="Search Name"
          fullWidth
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., My Property Search"
          sx={{ mb: 2 }}
          required
        />

        <TextField
          label="Description (optional)"
          fullWidth
          multiline
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Add notes about this search..."
          sx={{ mb: 3 }}
        />

        <Box sx={{ bgcolor: 'primary.50', p: 2, borderRadius: 1 }}>
          <FormControlLabel
            control={
              <Switch
                checked={notifyOnNewResults}
                onChange={(e) => setNotifyOnNewResults(e.target.checked)}
                color="primary"
              />
            }
            label={
              <Box>
                <Typography variant="body2" fontWeight={500}>
                  Notify me of new results
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Get email alerts when new matching records are added
                </Typography>
              </Box>
            }
            sx={{ alignItems: 'flex-start', m: 0 }}
          />

          {notifyOnNewResults && (
            <FormControl fullWidth sx={{ mt: 2 }} size="small">
              <InputLabel>Notification Frequency</InputLabel>
              <Select
                value={notificationFrequency}
                label="Notification Frequency"
                onChange={(e) => setNotificationFrequency(e.target.value)}
              >
                <MenuItem value="instant">Instant</MenuItem>
                <MenuItem value="daily">Daily Digest</MenuItem>
                <MenuItem value="weekly">Weekly Digest</MenuItem>
              </Select>
            </FormControl>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} disabled={saveSearchMutation.isPending}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={saveSearchMutation.isPending || !name.trim()}
          startIcon={saveSearchMutation.isPending ? <CircularProgress size={16} /> : <BookmarkAddIcon />}
        >
          {saveSearchMutation.isPending ? 'Saving...' : 'Save Search'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
