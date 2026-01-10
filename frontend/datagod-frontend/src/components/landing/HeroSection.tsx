'use client';

import { Box, Typography, Button, Container, Paper, TextField, InputAdornment } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export const HeroSection = () => {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = () => {
    if (searchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    } else {
      router.push('/search');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <Box
      sx={{
        background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
        minHeight: '80vh',
        display: 'flex',
        alignItems: 'center',
        position: 'relative',
        overflow: 'hidden',
        py: { xs: 6, md: 10 },
      }}
    >
      {/* Animated background elements */}
      <Box
        sx={{
          position: 'absolute',
          top: '10%',
          left: '5%',
          width: 300,
          height: 300,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(42,150,242,0.15) 0%, transparent 70%)',
          animation: 'pulse 4s ease-in-out infinite',
          '@keyframes pulse': {
            '0%, 100%': { transform: 'scale(1)', opacity: 0.5 },
            '50%': { transform: 'scale(1.1)', opacity: 0.8 },
          },
        }}
      />
      <Box
        sx={{
          position: 'absolute',
          bottom: '20%',
          right: '10%',
          width: 200,
          height: 200,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(238,111,167,0.15) 0%, transparent 70%)',
          animation: 'pulse 5s ease-in-out infinite',
        }}
      />

      <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 1 }}>
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          {/* Main headline */}
          <Typography
            variant="h1"
            sx={{
              fontSize: { xs: '2rem', sm: '2.5rem', md: '3.5rem', lg: '4rem' },
              fontWeight: 800,
              color: 'white',
              mb: 2,
              lineHeight: 1.2,
            }}
          >
            Pull anything about{' '}
            <Box
              component="span"
              sx={{
                background: 'linear-gradient(90deg, #2a96f2, #ee6fa7)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              anyone
            </Box>
            {' '}anywhere
          </Typography>

          {/* Subheadline */}
          <Typography
            variant="h5"
            sx={{
              fontSize: { xs: '1rem', sm: '1.25rem', md: '1.5rem' },
              color: 'rgba(255,255,255,0.8)',
              mb: 4,
              maxWidth: 700,
              mx: 'auto',
              fontWeight: 400,
            }}
          >
            Free access to millions of public records across all 50 states.
            Mortgages, property deeds, tax liens, court filings, and more.
          </Typography>

          {/* Search bar */}
          <Paper
            sx={{
              p: 0.5,
              display: 'flex',
              alignItems: 'center',
              maxWidth: 600,
              mx: 'auto',
              mb: 4,
              borderRadius: 3,
              boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
            }}
          >
            <TextField
              fullWidth
              placeholder="Search by name, address, or property..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              variant="standard"
              InputProps={{
                disableUnderline: true,
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon sx={{ color: 'text.secondary', ml: 1 }} />
                  </InputAdornment>
                ),
              }}
              sx={{
                '& input': {
                  py: 1.5,
                  px: 1,
                  fontSize: { xs: '0.9rem', sm: '1rem' },
                },
              }}
            />
            <Button
              variant="contained"
              size="large"
              onClick={handleSearch}
              endIcon={<ArrowForwardIcon />}
              sx={{
                px: { xs: 2, sm: 4 },
                py: 1.5,
                borderRadius: 2,
                fontWeight: 600,
                whiteSpace: 'nowrap',
              }}
            >
              Search Free
            </Button>
          </Paper>

          {/* CTA buttons */}
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Button
              variant="outlined"
              size="large"
              onClick={() => router.push('/register')}
              sx={{
                color: 'white',
                borderColor: 'rgba(255,255,255,0.5)',
                px: 4,
                '&:hover': {
                  borderColor: 'white',
                  backgroundColor: 'rgba(255,255,255,0.1)',
                },
              }}
            >
              Create Free Account
            </Button>
            <Button
              variant="text"
              size="large"
              onClick={() => router.push('/login')}
              sx={{
                color: 'rgba(255,255,255,0.8)',
                px: 3,
                '&:hover': {
                  color: 'white',
                  backgroundColor: 'rgba(255,255,255,0.1)',
                },
              }}
            >
              Sign In
            </Button>
          </Box>
        </Box>

        {/* Trust badges */}
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            gap: { xs: 2, sm: 4 },
            flexWrap: 'wrap',
            mt: 6,
          }}
        >
          {[
            { value: '50+', label: 'States Covered' },
            { value: '12M+', label: 'Records' },
            { value: '3,000+', label: 'Counties' },
            { value: '100%', label: 'Free to Search' },
          ].map((stat) => (
            <Box key={stat.label} sx={{ textAlign: 'center' }}>
              <Typography
                sx={{
                  fontSize: { xs: '1.5rem', sm: '2rem' },
                  fontWeight: 700,
                  color: 'white',
                }}
              >
                {stat.value}
              </Typography>
              <Typography
                sx={{
                  fontSize: { xs: '0.75rem', sm: '0.875rem' },
                  color: 'rgba(255,255,255,0.6)',
                  textTransform: 'uppercase',
                  letterSpacing: 1,
                }}
              >
                {stat.label}
              </Typography>
            </Box>
          ))}
        </Box>
      </Container>
    </Box>
  );
};
