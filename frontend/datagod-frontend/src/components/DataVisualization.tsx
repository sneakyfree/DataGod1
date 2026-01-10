import { Box, Typography, Paper, CircularProgress, Alert } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';

export const DataVisualization = () => {
  // Fetch visualization data from API
  const {
    data: visualizationData,
    isLoading,
    error
  } = useQuery({
    queryKey: ['visualizationData'],
    queryFn: () => apiService.getDashboardStats().then(res => res.data),
    retry: 3,
    staleTime: 5 * 60 * 1000, // 5 minutes
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
        Failed to load visualization data: {error.message}
      </Alert>
    );
  }

  // Mock data for visualization (will be replaced with real API data)
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

  // Color palette for charts
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#A4DE6C'];

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>
        Data Visualization Dashboard
      </Typography>

      {/* Records Over Time - Line Chart */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Records Collected Over Time
        </Typography>
        <ResponsiveContainer width="100%" height={300}>
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
              activeDot={{ r: 8 }}
              name="Total Records"
            />
          </LineChart>
        </ResponsiveContainer>
      </Paper>

      {/* Records by Type - Pie Chart */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <Paper sx={{ flex: 1, p: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Records by Type
          </Typography>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={mockData.recordsByType}
                cx="50%"
                cy="50%"
                labelLine={false}
                outerRadius={80}
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
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={mockData.dataSources}
                cx="50%"
                cy="50%"
                labelLine={false}
                outerRadius={80}
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

      {/* Jurisdiction Coverage - Bar Chart */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          Top 5 States by Coverage
        </Typography>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={mockData.jurisdictionCoverage}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="coverage" fill="#82ca9d" name="Coverage %" />
          </BarChart>
        </ResponsiveContainer>
      </Paper>
    </Box>
  );
};
