'use client';

import { useState } from 'react';
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
} from '@mui/material';
import { ContentCopy, Share, Close, Check } from '@mui/icons-material';
import { useMutation } from '@tanstack/react-query';
import { apiService } from '../../services/api';

interface ShareModalProps {
  open: boolean;
  onClose: () => void;
  recordId: string;
  recordTitle: string;
}

export const ShareModal = ({ open, onClose, recordId, recordTitle }: ShareModalProps) => {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [shareLink, setShareLink] = useState('');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Generate share link
  const generateShareLink = () => {
    const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
    const shareUrl = `${baseUrl}/share/${recordId}`;
    setShareLink(shareUrl);
    return shareUrl;
  };

  // Copy to clipboard
  const copyToClipboard = () => {
    const link = shareLink || generateShareLink();

    navigator.clipboard.writeText(link)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => {
        setError('Failed to copy link to clipboard');
      });
  };

  // Share via email mutation
  const shareMutation = useMutation({
    mutationFn: (data: { recordId: string; email: string; message: string }) =>
      apiService.shareRecord(data),
    onSuccess: () => {
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        handleClose();
      }, 2000);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to share record. Please try again.');
    }
  });

  const handleShare = () => {
    if (!email) {
      setError('Please enter an email address');
      return;
    }

    shareMutation.mutate({
      recordId,
      email,
      message: message || `I thought you might be interested in this record: ${recordTitle}`,
    });
  };

  const handleClose = () => {
    setEmail('');
    setMessage('');
    setError(null);
    setSuccess(false);
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
          width: { xs: '90%', sm: 450 },
          maxHeight: '90vh',
          overflow: 'auto',
          p: 3,
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography id="share-modal-title" variant="h6">
            Share Record
          </Typography>
          <IconButton onClick={handleClose} size="small">
            <Close />
          </IconButton>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Share &quot;{recordTitle}&quot; with others
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Record shared successfully!
          </Alert>
        )}

        {/* Share Link Section */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Share Link
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              fullWidth
              size="small"
              value={shareLink || generateShareLink()}
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
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Share via Email Section */}
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Share via Email
          </Typography>

          <TextField
            fullWidth
            size="small"
            label="Email address"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            sx={{ mb: 2 }}
            disabled={shareMutation.isPending}
          />

          <TextField
            fullWidth
            size="small"
            label="Message (optional)"
            multiline
            rows={3}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            sx={{ mb: 2 }}
            disabled={shareMutation.isPending}
          />

          <Button
            variant="contained"
            color="primary"
            onClick={handleShare}
            disabled={shareMutation.isPending}
            startIcon={shareMutation.isPending ? <CircularProgress size={20} /> : <Share />}
            fullWidth
          >
            {shareMutation.isPending ? 'Sharing...' : 'Share via Email'}
          </Button>
        </Box>
      </Paper>
    </Modal>
  );
};
