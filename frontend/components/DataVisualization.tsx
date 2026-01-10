import React, { useState } from 'react';
import {
  Box, Paper, Typography, Grid, Card, CardContent,
  FormControl, InputLabel, Select, MenuItem, Chip,
  LinearProgress, Alert, Button, ButtonGroup,
  TextField, Divider
} from '@mui/material';

// Mock data for demonstration
const generateTimeSeriesData = () => {
  const data = [];
  const now = new Date();
  for (let i = 30; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    data.push({
      date: date.toLocaleDateString(),
      records: Math.floor(Math.random() * 1000) + 200,
      duplicates: Math.floor(Math.random() * 200) + 50,
      jurisdictions: Math.floor(Math.random() * 20) + 10,
      api_calls: Math.floor(Math.random() * 5000) + 1000
    });
  }
  return data;
};

const generateJurisdictionData = () => [
  { name: 'Florida', records: 15420, color: '#0088FE' },
  { name: 'California', records: 12890, color: '#00C49F' },
  { name: 'Texas', records: 9870, color: '#FFBB28' },
  { name: 'New York', records: 7650, color: '#FF8042' },
  { name: 'Illinois', records: 5430, color: '#8884D8' }
];

const generateRecordTypeData = () => [
  { name: 'Property Deeds', value: 45, color: '#0088FE' },
  { name: 'Mortgage Filings', value: 30, color: '#00C49F' },
  { name: 'UCC Liens', value: 15, color: '#FFBB28' },
  { name: 'Business Filings', value: 10, color: '#FF8042' }
];

interface DataVisualizationProps {
  data?: any;
}

const DataVisualization: React.FC<DataVisualizationProps> = ({ data }) => {
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');
  const [chartType, setChartType] = useState<'records' | 'duplicates' | 'jurisdictions' | 'api'>('records');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const timeSeriesData = generateTimeSeriesData();
  const jurisdictionData = generateJurisdictionData();
  const recordTypeData = generateRecordTypeData();

  // Calculate summary statistics
  const totalRecords = timeSeriesData.reduce((sum, d) => sum + d.records, 0);
  const avgRecordsPerDay = Math.round(totalRecords / timeSeriesData.length);
  const totalDuplicates = timeSeriesData.reduce((sum, d) => sum + d.duplicates, 0);
  const deduplicationRate = ((totalRecords - totalDuplicates) / totalRecords * 100).toFixed(1);

  const handleTimeRangeChange = (newRange: '7d' | '30d' | '90d') => {
    setTimeRange(newRange);
    // Simple date calculation for demo
    const now = new Date();
    const days = newRange === '7d' ? 7 : newRange === '30d' ? 30 : 90;
    const start = new Date(now);
    start.setDate(start.getDate() - days);
    setStartDate(start.toISOString().split('T')[0]);
    setEndDate(now.toISOString().split('T')[0]);
  };

  const handleChartTypeChange = (newChartType: 'records' | 'duplicates' | 'jurisdictions' | 'api') => {
    setChartType(newChartType);
  };

  // Simple chart visualization using divs (since recharts isn't available)
  const renderSimpleChart = (data: any[], dataKey: string, title: string) => {
    const maxValue = Math.max(...data.map(d => d[dataKey] || 0));

    return (
      <Box sx={{ mt: 2 }}>
        <Typography variant="subtitle2" gutterBottom>{title}</Typography>
        <Box sx={{ display: 'flex', height: 200, alignItems: 'end', gap: 1 }}>
          {data.slice(-10).map((item, index) => {
            const value = item[dataKey] || 0;
            const height = (value / maxValue) * 180;
            return (
              <Box key={index} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
                <Box
                  sx={{
                    width: '100%',
                    maxWidth: 30,
                    height: height,
                    backgroundColor: '#8884d8',
                    borderRadius: '4px 4px 0 0',
                    display: 'flex',
                    alignItems: 'end',
                    justifyContent: 'center',
                    color: 'white',
                    fontSize: '10px',
                    fontWeight: 'bold',
                    p: 0.5
                  }}
                >
                  {value > 1000 ? `${(value/1000).toFixed(1)}k` : value}
                </Box>
                <Typography variant="caption" sx={{ mt: 0.5, fontSize: '8px', textAlign: 'center' }}>
                  {item.date?.split('/')[0] || index}
                </Typography>
              </Box>
            );
          })}
        </Box>
      </Box>
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Data Analytics Dashboard
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Records
              </Typography>
              <Typography variant="h4">
                {totalRecords.toLocaleString()}
              </Typography>
              <Typography variant="body2" color="success.main">
                +12.5% from last period
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Avg Daily Records
              </Typography>
              <Typography variant="h4">
                {avgRecordsPerDay.toLocaleString()}
              </Typography>
              <Typography variant="body2" color="success.main">
                +8.2% from last period
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Deduplication Rate
              </Typography>
              <Typography variant="h4">
                {deduplicationRate}%
              </Typography>
              <Typography variant="body2" color="success.main">
                +2.1% from last period
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Jurisdictions
              </Typography>
              <Typography variant="h4">
                {jurisdictionData.length}
              </Typography>
              <Typography variant="body2" color="info.main">
                +1 new jurisdiction
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Controls */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={3} alignItems="center">
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>Time Range</InputLabel>
              <Select
                value={timeRange}
                label="Time Range"
                onChange={(e) => handleTimeRangeChange(e.target.value as '7d' | '30d' | '90d')}
              >
                <MenuItem value="7d">Last 7 Days</MenuItem>
                <MenuItem value="30d">Last 30 Days</MenuItem>
                <MenuItem value="90d">Last 90 Days</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              label="Start Date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              label="End Date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
        </Grid>
      </Paper>

      {/* Main Charts */}
      <Grid container spacing={3}>
        {/* Time Series Chart */}
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Data Trends Over Time
              </Typography>
              <ButtonGroup size="small">
                <Button
                  variant={chartType === 'records' ? 'contained' : 'outlined'}
                  onClick={() => handleChartTypeChange('records')}
                >
                  Records
                </Button>
                <Button
                  variant={chartType === 'duplicates' ? 'contained' : 'outlined'}
                  onClick={() => handleChartTypeChange('duplicates')}
                >
                  Duplicates
                </Button>
                <Button
                  variant={chartType === 'jurisdictions' ? 'contained' : 'outlined'}
                  onClick={() => handleChartTypeChange('jurisdictions')}
                >
                  Jurisdictions
                </Button>
                <Button
                  variant={chartType === 'api' ? 'contained' : 'outlined'}
                  onClick={() => handleChartTypeChange('api')}
                >
                  API Calls
                </Button>
              </ButtonGroup>
            </Box>
            {loading ? (
              <LinearProgress />
            ) : (
              renderSimpleChart(timeSeriesData, chartType, `${chartType.charAt(0).toUpperCase() + chartType.slice(1)} Over Time`)
            )}
          </Paper>
        </Grid>

        {/* Record Types Distribution */}
        <Grid item xs={12} lg={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Records by Type
            </Typography>
            <Box sx={{ mt: 2 }}>
              {recordTypeData.map((item, index) => (
                <Box key={index} sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2">{item.name}</Typography>
                    <Typography variant="body2" color="textSecondary">
                      {item.value}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={item.value}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      backgroundColor: '#e0e0e0',
                      '& .MuiLinearProgress-bar': {
                        backgroundColor: item.color,
                        borderRadius: 4
                      }
                    }}
                  />
                </Box>
              ))}
            </Box>
          </Paper>
        </Grid>

        {/* Jurisdiction Rankings */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Records by Jurisdiction
            </Typography>
            <Box sx={{ mt: 2 }}>
              {jurisdictionData.map((item, index) => (
                <Box key={index} sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2">{item.name}</Typography>
                    <Typography variant="body2" color="textSecondary">
                      {item.records.toLocaleString()}
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(item.records / jurisdictionData[0].records) * 100}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      backgroundColor: '#e0e0e0',
                      '& .MuiLinearProgress-bar': {
                        backgroundColor: item.color,
                        borderRadius: 4
                      }
                    }}
                  />
                </Box>
              ))}
            </Box>
          </Paper>
        </Grid>

        {/* Performance Metrics */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              System Performance
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="textSecondary">
                API Response Time
              </Typography>
              <Typography variant="h6" color="success.main">
                245ms avg
              </Typography>
              <LinearProgress variant="determinate" value={75} sx={{ mt: 1 }} />
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="textSecondary">
                Scraper Success Rate
              </Typography>
              <Typography variant="h6" color="success.main">
                94.2%
              </Typography>
              <LinearProgress variant="determinate" value={94} sx={{ mt: 1 }} />
            </Box>
            <Box>
              <Typography variant="body2" color="textSecondary">
                Data Quality Score
              </Typography>
              <Typography variant="h6" color="success.main">
                87.5%
              </Typography>
              <LinearProgress variant="determinate" value={88} sx={{ mt: 1 }} />
            </Box>
          </Paper>
        </Grid>

        {/* Recent Activity */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Recent Activity
            </Typography>
            <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
              {[
                { time: '2 minutes ago', action: 'New records processed from Florida API', type: 'success' },
                { time: '15 minutes ago', action: 'Deduplication completed for Texas data', type: 'info' },
                { time: '1 hour ago', action: 'California scraper completed 1,247 records', type: 'success' },
                { time: '2 hours ago', action: 'Scheduled task executed for New York', type: 'info' },
                { time: '3 hours ago', action: 'API rate limit warning for Florida Property Appraiser', type: 'warning' },
                { time: '4 hours ago', action: 'Database backup completed successfully', type: 'success' }
              ].map((activity, index) => (
                <Box key={index} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Chip
                    size="small"
                    label={activity.type}
                    color={activity.type === 'success' ? 'success' :
                           activity.type === 'warning' ? 'warning' : 'info'}
                    sx={{ mr: 1, minWidth: 60 }}
                  />
                  <Box>
                    <Typography variant="body2">
                      {activity.action}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {activity.time}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DataVisualization;
