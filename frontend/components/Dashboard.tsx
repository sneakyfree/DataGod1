import React from 'react';
import { Box, Typography, Grid, Card, CardContent, CardHeader, Divider, CircularProgress } from '@mui/material';
import { LineChart, BarChart, PieChart } from '@mui/x-charts';
import { useTheme } from '@mui/material/styles';

const Dashboard: React.FC = () => {
  const theme = useTheme();

  // Mock data for visualizations
  const recordsOverTime = [
    { month: 'Jan', count: 120 },
    { month: 'Feb', count: 150 },
    { month: 'Mar', count: 180 },
    { month: 'Apr', count: 220 },
    { month: 'May', count: 250 },
    { month: 'Jun', count: 280 },
    { month: 'Jul', count: 310 },
    { month: 'Aug', count: 340 },
    { month: 'Sep', count: 370 },
    { month: 'Oct', count: 400 },
    { month: 'Nov', count: 430 },
    { month: 'Dec', count: 460 },
  ];

  const jurisdictionCoverage = [
    { name: 'New York', value: 85 },
    { name: 'California', value: 92 },
    { name: 'Texas', value: 78 },
    { name: 'Illinois', value: 88 },
    { name: 'Arizona', value: 75 },
    { name: 'Florida', value: 80 },
    { name: 'Pennsylvania', value: 82 },
    { name: 'Ohio', value: 79 },
    { name: 'Georgia', value: 81 },
    { name: 'North Carolina', value: 77 },
  ];

  const recordsByType = [
    { name: 'Mortgage', value: 45 },
    { name: 'Deed', value: 30 },
    { name: 'Lien', value: 15 },
    { name: 'Foreclosure', value: 5 },
    { name: 'Tax Lien', value: 5 },
  ];

  const dataSourceStatus = [
    { name: 'Active', value: 85 },
    { name: 'Inactive', value: 10 },
    { name: 'Error', value: 5 },
  ];

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Records Over Time" />
            <CardContent>
              <LineChart
                width={500}
                height={300}
                series={[
                  {
                    data: recordsOverTime.map(item => ({ x: item.month, y: item.count })),
                    label: 'Records',
                  },
                ]}
                xAxis={[
                  {
                    scaleType: 'band',
                    data: recordsOverTime.map(item => item.month),
                  },
                ]}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Jurisdiction Coverage" />
            <CardContent>
              <PieChart
                width={500}
                height={300}
                series={[
                  {
                    data: jurisdictionCoverage,
                    label: 'Coverage',
                  },
                ]}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Records by Type" />
            <CardContent>
              <BarChart
                width={500}
                height={300}
                series={[
                  {
                    data: recordsByType.map(item => ({ x: item.name, y: item.value })),
                    label: 'Records',
                  },
                ]}
                xAxis={[
                  {
                    scaleType: 'band',
                    data: recordsByType.map(item => item.name),
                  },
                ]}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Data Source Status" />
            <CardContent>
              <PieChart
                width={500}
                height={300}
                series={[
                  {
                    data: dataSourceStatus,
                    label: 'Status',
                  },
                ]}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
