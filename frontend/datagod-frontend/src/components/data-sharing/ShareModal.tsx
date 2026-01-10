'use client';

import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Modal,
  Button,
  TextField,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  Paper,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { ContentCopy, Share, Close, Check, Link as LinkIcon } from '@mui/icons-material';
import { useMutation } from '@tanstack/react-query';
import { apiService } from '../../services/api';

interface ShareModalProps {
  open: boolean;
  onClose: () => void;
  recordId?: number;
  entityId?: number;
  itemTitle: string;
  itemType?: 'record' | 'entity';
}

interface ShareLinkResponse {
  id: number;
  token: string;
  share_url: string;
  share_type: string;
  expires_at: string | null;
  view_count: number;
  created_at: string;
}

export const ShareModal = ({
  open,
  onClose,
  recordId,
  entityId,
  itemTitle,
  itemType = 'record'
}: ShareModalProps) => {
  const [message, setMessage] = useState('');
  const [expiresInDays, setExpiresInDays] = useState<number | ''>('');
  const [shareLink, setShareLink] = useState('');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (open) {
      setShareLink('');
      setMessage('');
      setExpiresInDays('');
      setError(null);
      setCopied(false);
    }
  }, [open]);

  // Create share link mutation
  const createShareMutation = useMutation({
    mutationFn: async () => {
      const data: {
        record_id?: number;
        entity_id?: number;
        message?: string;
        expires_in_days?: number;
      } = {};

      if (recordId) data.record_id = recordId;
      if (entityId) data.entity_id = entityId;
      if (message) data.message = message;
      if (expiresInDays) data.expires_in_days = expiresInDays;

      return apiService.createShareLink(data);
    },
    onSuccess: (response) => {
      const shareData = response.data as ShareLinkResponse;
      setShareLink(shareData.share_url);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to create share link. Please try again.');
    }
  });

  // Copy to clipboard
  const copyToClipboard = () => {
    if (!shareLink) return;

    navigator.clipboard.writeText(shareLink)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => {
        setError('Failed to copy link to clipboard');
      });
  };

  const handleGenerateLink = () => {
    setError(null);
    createShareMutation.mutate();
  };

  const handleClose = () => {
    setMessage('');
    setExpiresInDays('');
    setShareLink('');
    setError(null);
    setCopied(false);
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={handleClose}
      aria-labelledby="share-modal-title"
      aria-describedby="share-modal-description"
    >
      <Paper
        sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: { xs: '90%', sm: 480 },
          maxHeight: '90vh',
          overflow: 'auto',
          p: 3,
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography id="share-modal-title" variant="h6">
            Share {itemType === 'entity' ? 'Entity' : 'Record'}
          </Typography>
          <IconButton onClick={handleClose} size="small">
            <Close />
          </IconButton>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Create a shareable link for &quot;{itemTitle}&quot;
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Share Link Generated */}
        {shareLink ? (
          <Box>
            <Alert severity="success" sx={{ mb: 2 }}>
              Share link created successfully!
            </Alert>

            <Typography variant="subtitle2" gutterBottom>
              Share Link
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <TextField
                fullWidth
                size="small"
                value={shareLink}
                InputProps={{
                  readOnly: true,
                }}
              />
              <Tooltip title={copied ? 'Copied!' : 'Copy link'}>
                <IconButton onClick={copyToClipboard} color={copied ? 'success' : 'default'}>
                  {copied ? <Check /> : <ContentCopy />}
                </IconButton>
              </Tooltip>
            </Box>

            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Anyone with this link can view this {itemType}.
              {expiresInDays && ` Link expires in ${expiresInDays} day${expiresInDays > 1 ? 's' : ''}.`}
            </Typography>

            <Divider sx={{ my: 2 }} />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="outlined"
                onClick={() => setShareLink('')}
                fullWidth
              >
                Create Another Link
              </Button>
              <Button
                variant="contained"
                onClick={handleClose}
                fullWidth
              >
                Done
              </Button>
            </Box>
          </Box>
        ) : (
          /* Create Share Link Form */
          <Box>
            <TextField
              fullWidth
              size="small"
              label="Optional message"
              placeholder="Add a note for the recipient..."
              multiline
              rows={2}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              sx={{ mb: 2 }}
              disabled={createShareMutation.isPending}
            />

            <FormControl fullWidth size="small" sx={{ mb: 3 }}>
              <InputLabel>Link Expiration</InputLabel>
              <Select
                value={expiresInDays}
                label="Link Expiration"
                onChange={(e) => setExpiresInDays(e.target.value as number | '')}
                disabled={createShareMutation.isPending}
              >
                <MenuItem value="">Never expires</MenuItem>
                <MenuItem value={1}>1 day</MenuItem>
                <MenuItem value={7}>7 days</MenuItem>
                <MenuItem value={30}>30 days</MenuItem>
                <MenuItem value={90}>90 days</MenuItem>
                <MenuItem value={365}>1 year</MenuItem>
              </Select>
            </FormControl>

            <Button
              variant="contained"
              color="primary"
              onClick={handleGenerateLink}
              disabled={createShareMutation.isPending}
              startIcon={createShareMutation.isPending ? <CircularProgress size={20} /> : <LinkIcon />}
              fullWidth
            >
              {createShareMutation.isPending ? 'Creating Link...' : 'Create Share Link'}
            </Button>

            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2, textAlign: 'center' }}>
              The link will allow anyone to view this {itemType} without logging in.
            </Typography>
          </Box>
        )}
      </Paper>
    </Modal>
  );
};
