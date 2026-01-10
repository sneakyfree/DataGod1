'use client';

import { useEffect } from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import { ErrorOutline, Refresh, Home } from '@mui/icons-material';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Application error:', error);
  }, [error]);

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: '#f5f5f5',
        p: 3,
      }}
    >
      <Paper
        sx={{
          p: 4,
          maxWidth: 500,
          width: '100%',
          textAlign: 'center',
          boxShadow: 3,
        }}
      >
        <Box
          sx={{
            width: 80,
            height: 80,
            borderRadius: '50%',
            backgroundColor: '#ffebee',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 24px',
          }}
        >
          <ErrorOutline sx={{ fontSize: 48, color: '#f44336' }} />
        </Box>

        <Typography variant="h4" component="h1" gutterBottom>
          Something went wrong
        </Typography>

        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          We apologize for the inconvenience. An unexpected error has occurred.
          Please try again or return to the home page.
        </Typography>

        {error.digest && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              display: 'block',
              mb: 3,
              fontFamily: 'monospace',
              backgroundColor: '#f5f5f5',
              p: 1,
              borderRadius: 1,
            }}
          >
            Error ID: {error.digest}
          </Typography>
        )}

        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<Refresh />}
            onClick={reset}
          >
            Try Again
          </Button>
          <Button
            variant="outlined"
            color="primary"
            startIcon={<Home />}
            href="/"
          >
            Go Home
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}
