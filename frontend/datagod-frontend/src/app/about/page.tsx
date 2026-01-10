'use client';

import { Box, Typography, Paper, Grid, Container } from '@mui/material';
import { Storage, Speed, Security, Public } from '@mui/icons-material';

export default function AboutPage() {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper sx={{ p: { xs: 3, md: 5 } }}>
        <Typography variant="h3" component="h1" gutterBottom align="center">
          About DataGod
        </Typography>

        <Typography variant="h6" color="text.secondary" align="center" sx={{ mb: 4 }}>
          The most comprehensive public records database in the United States
        </Typography>

        <Typography variant="body1" paragraph sx={{ mb: 4 }}>
          DataGod is a cutting-edge platform designed to aggregate, organize, and provide
          seamless access to public records from jurisdictions across the United States.
          Our mission is to make public data truly accessible to everyone—researchers,
          journalists, legal professionals, real estate agents, and everyday citizens.
        </Typography>

        <Grid container spacing={4} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ textAlign: 'center', p: 2 }}>
              <Box sx={{
                width: 64,
                height: 64,
                borderRadius: '50%',
                backgroundColor: 'primary.light',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px'
              }}>
                <Storage sx={{ fontSize: 32, color: 'primary.main' }} />
              </Box>
              <Typography variant="h6" gutterBottom>Comprehensive Data</Typography>
              <Typography variant="body2" color="text.secondary">
                Access millions of public records from counties across the nation.
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ textAlign: 'center', p: 2 }}>
              <Box sx={{
                width: 64,
                height: 64,
                borderRadius: '50%',
                backgroundColor: 'success.light',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px'
              }}>
                <Speed sx={{ fontSize: 32, color: 'success.main' }} />
              </Box>
              <Typography variant="h6" gutterBottom>Lightning Fast</Typography>
              <Typography variant="body2" color="text.secondary">
                Advanced search algorithms deliver results in milliseconds.
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ textAlign: 'center', p: 2 }}>
              <Box sx={{
                width: 64,
                height: 64,
                borderRadius: '50%',
                backgroundColor: 'warning.light',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px'
              }}>
                <Security sx={{ fontSize: 32, color: 'warning.main' }} />
              </Box>
              <Typography variant="h6" gutterBottom>Secure & Reliable</Typography>
              <Typography variant="body2" color="text.secondary">
                Enterprise-grade security protects your data and queries.
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Box sx={{ textAlign: 'center', p: 2 }}>
              <Box sx={{
                width: 64,
                height: 64,
                borderRadius: '50%',
                backgroundColor: 'info.light',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px'
              }}>
                <Public sx={{ fontSize: 32, color: 'info.main' }} />
              </Box>
              <Typography variant="h6" gutterBottom>Nationwide Coverage</Typography>
              <Typography variant="body2" color="text.secondary">
                Growing coverage across all 50 states and territories.
              </Typography>
            </Box>
          </Grid>
        </Grid>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          Our Vision
        </Typography>
        <Typography variant="body1" paragraph>
          We believe that public records should be just that—public. Too often,
          accessing government data requires navigating complex bureaucracies,
          visiting physical offices, or paying exorbitant fees. DataGod changes
          that by providing a unified, user-friendly interface to search, filter,
          and export public records from anywhere.
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          What We Offer
        </Typography>
        <Typography variant="body1" component="div">
          <ul>
            <li><strong>Property Records:</strong> Deeds, mortgages, liens, and ownership history</li>
            <li><strong>Court Records:</strong> Civil cases, judgments, and legal filings</li>
            <li><strong>Business Records:</strong> Corporate filings, licenses, and registrations</li>
            <li><strong>Tax Records:</strong> Property assessments and tax payment history</li>
            <li><strong>And More:</strong> Our database is constantly expanding</li>
          </ul>
        </Typography>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          Contact Us
        </Typography>
        <Typography variant="body1" paragraph>
          Have questions or feedback? We&apos;d love to hear from you. Visit our{' '}
          <a href="/contact" style={{ color: '#2a96f2' }}>contact page</a> to get in touch.
        </Typography>
      </Paper>
    </Container>
  );
}
