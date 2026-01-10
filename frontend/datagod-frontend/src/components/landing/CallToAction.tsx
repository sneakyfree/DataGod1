'use client';

import { Box, Typography, Container, Button, Grid } from '@mui/material';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { useRouter } from 'next/navigation';

export const CallToAction = () => {
  const router = useRouter();

  return (
    <Box
      sx={{
        py: { xs: 8, md: 12 },
        background: 'linear-gradient(135deg, #2a96f2 0%, #1976d2 100%)',
      }}
    >
      <Container maxWidth="md">
        <Box sx={{ textAlign: 'center' }}>
          <Typography
            variant="h2"
            sx={{
              fontSize: { xs: '1.75rem', sm: '2rem', md: '2.5rem' },
              fontWeight: 700,
              color: 'white',
              mb: 2,
            }}
          >
            Ready to Start Researching?
          </Typography>
          <Typography
            variant="body1"
            sx={{
              fontSize: { xs: '1rem', md: '1.25rem' },
              color: 'rgba(255,255,255,0.9)',
              mb: 4,
              maxWidth: 500,
              mx: 'auto',
            }}
          >
            Create your free account today. No credit card required.
            Start searching in seconds.
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              size="large"
              endIcon={<ArrowForwardIcon />}
              onClick={() => router.push('/register')}
              sx={{
                px: 4,
                py: 1.5,
                backgroundColor: 'white',
                color: 'primary.main',
                fontWeight: 600,
                '&:hover': {
                  backgroundColor: 'rgba(255,255,255,0.9)',
                },
              }}
            >
              Get Started Free
            </Button>
            <Button
              variant="outlined"
              size="large"
              onClick={() => router.push('/pricing')}
              sx={{
                px: 4,
                py: 1.5,
                color: 'white',
                borderColor: 'rgba(255,255,255,0.5)',
                '&:hover': {
                  borderColor: 'white',
                  backgroundColor: 'rgba(255,255,255,0.1)',
                },
              }}
            >
              View Pricing
            </Button>
          </Box>

          {/* Trust indicators */}
          <Box sx={{ mt: 6 }}>
            <Typography
              variant="body2"
              sx={{ color: 'rgba(255,255,255,0.7)', mb: 2 }}
            >
              Trusted by professionals nationwide
            </Typography>
            <Grid container spacing={4} justifyContent="center">
              {[
                'Real Estate Agents',
                'Private Investigators',
                'Mortgage Brokers',
                'Due Diligence Teams',
              ].map((profession) => (
                <Grid item key={profession}>
                  <Typography
                    variant="body2"
                    sx={{
                      color: 'rgba(255,255,255,0.9)',
                      fontWeight: 500,
                    }}
                  >
                    {profession}
                  </Typography>
                </Grid>
              ))}
            </Grid>
          </Box>
        </Box>
      </Container>
    </Box>
  );
};
