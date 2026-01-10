'use client';

import { Box, Typography, Container, Grid, Paper, Button, Chip } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import HomeIcon from '@mui/icons-material/Home';
import BusinessIcon from '@mui/icons-material/Business';
import PersonIcon from '@mui/icons-material/Person';
import { useRouter } from 'next/navigation';

const sampleSearches = [
  {
    query: 'John Smith',
    location: 'Harris County, TX',
    resultCount: 847,
    icon: <PersonIcon />,
    type: 'Person',
    color: '#2a96f2',
  },
  {
    query: '123 Main Street',
    location: 'Miami-Dade, FL',
    resultCount: 23,
    icon: <HomeIcon />,
    type: 'Property',
    color: '#4caf50',
  },
  {
    query: 'Acme Holdings LLC',
    location: 'Los Angeles, CA',
    resultCount: 156,
    icon: <BusinessIcon />,
    type: 'Company',
    color: '#ee6fa7',
  },
];

const sampleResults = [
  {
    title: 'Mortgage Deed',
    parties: 'J**** S**** → Bank of ****',
    amount: '$***,***',
    date: 'Dec 2024',
    location: 'Harris County, TX',
    blurred: true,
  },
  {
    title: 'Property Transfer',
    parties: 'A**** LLC → J**** Corp',
    amount: '$*,***,***',
    date: 'Nov 2024',
    location: 'Miami-Dade, FL',
    blurred: true,
  },
  {
    title: 'Tax Lien Release',
    parties: 'State of TX vs S**** J****',
    amount: '$**,***',
    date: 'Oct 2024',
    location: 'Dallas County, TX',
    blurred: true,
  },
];

export const SampleSearch = () => {
  const router = useRouter();

  return (
    <Box sx={{ py: { xs: 8, md: 12 }, backgroundColor: 'grey.50' }}>
      <Container maxWidth="lg">
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          <Typography
            variant="h2"
            sx={{
              fontSize: { xs: '1.75rem', sm: '2rem', md: '2.5rem' },
              fontWeight: 700,
              mb: 2,
            }}
          >
            See What You Can Find
          </Typography>
          <Typography
            variant="body1"
            sx={{
              fontSize: { xs: '1rem', md: '1.125rem' },
              color: 'text.secondary',
              maxWidth: 600,
              mx: 'auto',
            }}
          >
            Try these sample searches or jump right in with your own query
          </Typography>
        </Box>

        {/* Sample Search Buttons */}
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap', mb: 6 }}>
          {sampleSearches.map((search) => (
            <Paper
              key={search.query}
              sx={{
                p: 2,
                cursor: 'pointer',
                transition: 'transform 0.2s, box-shadow 0.2s',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                },
              }}
              onClick={() => router.push(`/search?q=${encodeURIComponent(search.query)}`)}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    borderRadius: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: `${search.color}15`,
                    color: search.color,
                  }}
                >
                  {search.icon}
                </Box>
                <Box>
                  <Typography variant="subtitle2" fontWeight={600}>
                    &quot;{search.query}&quot;
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {search.location} • {search.resultCount.toLocaleString()} results
                  </Typography>
                </Box>
                <SearchIcon sx={{ color: 'text.secondary', ml: 1 }} />
              </Box>
            </Paper>
          ))}
        </Box>

        {/* Sample Results Preview */}
        <Paper sx={{ p: 4, maxWidth: 800, mx: 'auto' }}>
          <Typography variant="h6" sx={{ mb: 3 }}>
            Sample Results Preview
          </Typography>

          <Grid container spacing={2}>
            {sampleResults.map((result, index) => (
              <Grid item xs={12} key={index}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Box>
                      <Typography variant="subtitle1" fontWeight={600}>
                        {result.title}
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          color: 'text.secondary',
                          filter: result.blurred ? 'blur(3px)' : 'none',
                          userSelect: 'none',
                        }}
                      >
                        {result.parties}
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                      <Typography
                        variant="subtitle2"
                        sx={{
                          filter: result.blurred ? 'blur(3px)' : 'none',
                          userSelect: 'none',
                        }}
                      >
                        {result.amount}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {result.date}
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{ mt: 1 }}>
                    <Chip label={result.location} size="small" variant="outlined" />
                  </Box>

                  {/* Blur overlay */}
                  {result.blurred && (
                    <Box
                      sx={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        backgroundColor: 'rgba(255,255,255,0.5)',
                        backdropFilter: 'blur(2px)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Chip
                        label="Sign up to view full details"
                        color="primary"
                        onClick={() => router.push('/register')}
                        sx={{ cursor: 'pointer' }}
                      />
                    </Box>
                  )}
                </Paper>
              </Grid>
            ))}
          </Grid>

          <Box sx={{ textAlign: 'center', mt: 4 }}>
            <Button
              variant="contained"
              size="large"
              endIcon={<ArrowForwardIcon />}
              onClick={() => router.push('/register')}
              sx={{ px: 4 }}
            >
              Start Searching for Free
            </Button>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
};
