'use client';

import { Box, Typography, Button, Paper } from '@mui/material';
import { SearchOff, Home, ArrowBack } from '@mui/icons-material';
import { useRouter } from 'next/navigation';

export default function NotFound() {
  const router = useRouter();

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
            backgroundColor: '#fff3e0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 24px',
          }}
        >
          <SearchOff sx={{ fontSize: 48, color: '#ff9800' }} />
        </Box>

        <Typography
          variant="h1"
          component="h1"
          sx={{
            fontSize: { xs: '4rem', sm: '6rem' },
            fontWeight: 'bold',
            color: 'primary.main',
            lineHeight: 1,
            mb: 1,
          }}
        >
          404
        </Typography>

        <Typography variant="h5" component="h2" gutterBottom>
          Page Not Found
        </Typography>

        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
          Please check the URL or navigate back to safety.
        </Typography>

        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<Home />}
            href="/"
          >
            Go Home
          </Button>
          <Button
            variant="outlined"
            color="primary"
            startIcon={<ArrowBack />}
            onClick={() => router.back()}
          >
            Go Back
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}
