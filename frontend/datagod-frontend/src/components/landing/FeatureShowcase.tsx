'use client';

import { Box, Typography, Container, Grid, Paper } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import MapIcon from '@mui/icons-material/Map';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import SpeedIcon from '@mui/icons-material/Speed';
import SecurityIcon from '@mui/icons-material/Security';

const features = [
  {
    icon: <SearchIcon sx={{ fontSize: 40 }} />,
    title: 'Search Across 50 States',
    description: 'Access public records from coast to coast. Mortgages, deeds, liens, court filings, and business records all in one place.',
    color: '#2a96f2',
  },
  {
    icon: <AccountTreeIcon sx={{ fontSize: 40 }} />,
    title: 'Trace Connections',
    description: 'Discover hidden relationships between people, properties, and companies. Our AI links entities across millions of records.',
    color: '#ee6fa7',
  },
  {
    icon: <MapIcon sx={{ fontSize: 40 }} />,
    title: 'County-Level Coverage',
    description: 'Drill down to specific counties. See coverage levels, record counts, and available document types for each jurisdiction.',
    color: '#4caf50',
  },
  {
    icon: <FileDownloadIcon sx={{ fontSize: 40 }} />,
    title: 'Export Your Research',
    description: 'Download your findings in CSV, Excel, or JSON format. Perfect for reports, analysis, or integration with your tools.',
    color: '#ff9800',
  },
  {
    icon: <SpeedIcon sx={{ fontSize: 40 }} />,
    title: 'Real-Time Updates',
    description: 'Our data feeds pull fresh records daily. Stay ahead with the latest filings, transfers, and court documents.',
    color: '#9c27b0',
  },
  {
    icon: <SecurityIcon sx={{ fontSize: 40 }} />,
    title: 'Verified Public Records',
    description: 'All data sourced directly from official government databases. No scraped or unverified information.',
    color: '#00bcd4',
  },
];

export const FeatureShowcase = () => {
  return (
    <Box sx={{ py: { xs: 8, md: 12 }, backgroundColor: '#f8f9fa' }}>
      <Container maxWidth="lg">
        <Box sx={{ textAlign: 'center', mb: 8 }}>
          <Typography
            variant="h2"
            sx={{
              fontSize: { xs: '1.75rem', sm: '2rem', md: '2.5rem' },
              fontWeight: 700,
              mb: 2,
            }}
          >
            Everything You Need for Research
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
            Whether you&apos;re a real estate professional, investigator, or curious citizen,
            DataGod gives you the tools to uncover the information you need.
          </Typography>
        </Box>

        <Grid container spacing={4}>
          {features.map((feature) => (
            <Grid item xs={12} sm={6} md={4} key={feature.title}>
              <Paper
                sx={{
                  p: 4,
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
                  },
                }}
              >
                <Box
                  sx={{
                    width: 64,
                    height: 64,
                    borderRadius: 2,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: `${feature.color}15`,
                    color: feature.color,
                    mb: 2,
                  }}
                >
                  {feature.icon}
                </Box>
                <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
                  {feature.title}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                  {feature.description}
                </Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
};
