import { Typography, Box, Grid, Paper } from '@mui/material';
import { DashboardStats } from '../components/DashboardStats';
import { RecentRecords } from '../components/RecentRecords';
import { JurisdictionCoverage } from '../components/JurisdictionCoverage';

export default function HomePage() {
  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        DataGod Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Stats Cards */}
        <Grid item xs={12} md={12}>
          <DashboardStats />
        </Grid>

        {/* Main Content */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Recent Records
            </Typography>
            <RecentRecords limit={10} />
          </Paper>
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Jurisdiction Coverage
            </Typography>
            <JurisdictionCoverage />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
