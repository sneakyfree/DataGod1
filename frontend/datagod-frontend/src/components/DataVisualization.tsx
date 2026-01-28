'use client';

import { useState } from 'react';
import { Box, Typography, Paper, CircularProgress, Alert, ToggleButtonGroup, ToggleButton, Tabs, Tab } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { HeatMap } from './visualization/HeatMap';
import MapIcon from '@mui/icons-material/Map';
import BarChartIcon from '@mui/icons-material/BarChart';
import TimelineIcon from '@mui/icons-material/Timeline';
import PieChartIcon from '@mui/icons-material/PieChart';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
    </div>
  );
}

export const DataVisualization = () => {
  const [tabValue, setTabValue] = useState(0);

  // Fetch visualization data from API
  const {
    data: visualizationData,
    isLoading,
    error
  } = useQuery({
    queryKey: ['visualizationData'],
    queryFn: () => apiService.getDashboardStats().then(res => res.data),
    retry: 3,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        Failed to load visualization data: {(error as Error).message}
      </Alert>
    );
  }

  // Data with fallbacks
  const mockData = visualizationData || {
    recordsOverTime: [
      { name: 'Jan', records: 4000 },
      { name: 'Feb', records: 3000 },
      { name: 'Mar', records: 5000 },
      { name: 'Apr', records: 4500 },
      { name: 'May', records: 6000 },
      { name: 'Jun', records: 5500 },
    ],
    recordsByType: [
      { name: 'Property', value: 45 },
      { name: 'Tax', value: 30 },
      { name: 'Legal', value: 15 },
      { name: 'Business', value: 10 },
    ],
    dataSources: [
      { name: 'API', value: 60 },
      { name: 'Scraper', value: 30 },
      { name: 'Manual', value: 10 },
    ],
    jurisdictionCoverage: [
      { name: 'California', coverage: 78 },
      { name: 'Texas', coverage: 47 },
      { name: 'Florida', coverage: 48 },
      { name: 'New York', coverage: 45 },
      { name: 'Illinois', coverage: 39 },
    ]
  };

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#A4DE6C'];

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>
        Data Visualization Dashboard
      </Typography>

      <Paper sx={{ mb: 2 }}>
        <Tabs value={tabValue} onChange={handleTabChange} variant="fullWidth">
          <Tab icon={<MapIcon />} label="Coverage Map" />
          <Tab icon={<TimelineIcon />} label="Trends" />
          <Tab icon={<PieChartIcon />} label="Distribution" />
          <Tab icon={<BarChartIcon />} label="States" />
        </Tabs>
      </Paper>

      {/* Tab 0: Geographic HeatMap */}
      <TabPanel value={tabValue} index={0}>
        <HeatMap
          title="Jurisdiction Coverage by State"
          metric="coverage"
          height={500}
          showControls={true}
          showLegend={true}
          onStateClick={(stateCode, data) => {
            console.log('State clicked:', stateCode, data);
          }}
        />
      </TabPanel>

      {/* Tab 1: Time Series */}
      <TabPanel value={tabValue} index={1}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Records Collected Over Time
          </Typography>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={mockData.recordsOverTime}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="records"
                stroke="#8884d8"
                strokeWidth={2}
                activeDot={{ r: 8 }}
                name="Total Records"
              />
            </LineChart>
          </ResponsiveContainer>
        </Paper>
      </TabPanel>

      {/* Tab 2: Distribution (Pie Charts) */}
      <TabPanel value={tabValue} index={2}>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Paper sx={{ flex: 1, p: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Records by Type
            </Typography>
            <ResponsiveContainer width="100%" height={350}>
              <PieChart>
                <Pie
                  data={mockData.recordsByType}
                  cx="50%"
                  cy="50%"
                  labelLine={true}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                  nameKey="name"
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                >
                  {mockData.recordsByType.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Paper>

          <Paper sx={{ flex: 1, p: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Data Sources
            </Typography>
            <ResponsiveContainer width="100%" height={350}>
              <PieChart>
                <Pie
                  data={mockData.dataSources}
                  cx="50%"
                  cy="50%"
                  labelLine={true}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                  nameKey="name"
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                >
                  {mockData.dataSources.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Box>
      </TabPanel>

      {/* Tab 3: State Bar Chart */}
      <TabPanel value={tabValue} index={3}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Top States by Coverage
          </Typography>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={mockData.jurisdictionCoverage} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" domain={[0, 100]} />
              <YAxis dataKey="name" type="category" width={100} />
              <Tooltip />
              <Legend />
              <Bar dataKey="coverage" fill="#82ca9d" name="Coverage %" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Paper>
      </TabPanel>
    </Box>
  );
};
