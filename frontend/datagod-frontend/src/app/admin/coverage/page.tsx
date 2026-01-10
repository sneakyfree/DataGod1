'use client';

import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  MenuItem,
  Button,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import MapIcon from '@mui/icons-material/Map';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import { MainLayout } from '../../../components/layout/MainLayout';
import { apiService } from '../../../services/api';

interface CoverageSummary {
  total_jurisdictions: number;
  jurisdictions_with_fips: number;
  jurisdictions_with_coverage: number;
  jurisdictions_complete: number;
  coverage_percentage: number;
  complete_percentage: number;
  by_state: Record<string, number>;
}

interface CoverageGap {
  id: number;
  name: string;
  state: string;
  fips_code: string;
  population: number;
  missing_categories: string[];
  current_coverage: Record<string, any>;
}

const STATE_NAMES: Record<string, string> = {
  AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California',
  CO: 'Colorado', CT: 'Connecticut', DE: 'Delaware', DC: 'District of Columbia',
  FL: 'Florida', GA: 'Georgia', HI: 'Hawaii', ID: 'Idaho', IL: 'Illinois',
  IN: 'Indiana', IA: 'Iowa', KS: 'Kansas', KY: 'Kentucky', LA: 'Louisiana',
  ME: 'Maine', MD: 'Maryland', MA: 'Massachusetts', MI: 'Michigan', MN: 'Minnesota',
  MS: 'Mississippi', MO: 'Missouri', MT: 'Montana', NE: 'Nebraska', NV: 'Nevada',
  NH: 'New Hampshire', NJ: 'New Jersey', NM: 'New Mexico', NY: 'New York',
  NC: 'North Carolina', ND: 'North Dakota', OH: 'Ohio', OK: 'Oklahoma', OR: 'Oregon',
  PA: 'Pennsylvania', RI: 'Rhode Island', SC: 'South Carolina', SD: 'South Dakota',
  TN: 'Tennessee', TX: 'Texas', UT: 'Utah', VT: 'Vermont', VA: 'Virginia',
  WA: 'Washington', WV: 'West Virginia', WI: 'Wisconsin', WY: 'Wyoming',
  PR: 'Puerto Rico', GU: 'Guam', VI: 'Virgin Islands', AS: 'American Samoa',
  MP: 'Northern Mariana Islands'
};

const DATA_CATEGORIES = [
  'court_records',
  'business_filings',
  'property_records',
  'professional_licenses',
  'vital_records',
  'criminal_records',
  'voter_records',
];

export default function CoveragePage() {
  const [summary, setSummary] = useState<CoverageSummary | null>(null);
  const [gaps, setGaps] = useState<CoverageGap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedState, setSelectedState] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    loadCoverageData();
  }, []);

  const loadCoverageData = async () => {
    setLoading(true);
    setError(null);

    // Mock data for fallback
    const mockSummary: CoverageSummary = {
      total_jurisdictions: 3240,
      jurisdictions_with_fips: 3235,
      jurisdictions_with_coverage: 4,
      jurisdictions_complete: 4,
      coverage_percentage: 0.12,
      complete_percentage: 0.12,
      by_state: {
        TX: 255, GA: 159, VA: 133, KY: 120, MO: 115, IL: 103, NC: 100,
        IA: 99, TN: 95, IN: 92, KS: 105, OH: 88, MN: 87, MI: 83,
        MS: 82, PR: 78, OK: 77, AR: 75, WI: 72, FL: 68, AL: 67,
        PA: 67, SD: 66, CO: 64, LA: 64, NY: 62, CA: 59, MT: 56,
        WV: 55, ND: 53, SC: 46, ID: 44, OR: 36, WA: 39, NM: 33,
        AK: 31, UT: 29, NE: 93, NV: 17, ME: 16, AZ: 16, VT: 14,
        MA: 14, NH: 10, CT: 8, HI: 5, AS: 5, RI: 5, MP: 4, DE: 3,
        VI: 3, GU: 1, DC: 1, WY: 23, NJ: 21, MD: 24
      }
    };

    const mockGaps: CoverageGap[] = [
      { id: 1, name: 'Los Angeles County, CA', state: 'CA', fips_code: '06037', population: 9829544, missing_categories: ['vital_records'], current_coverage: { court_records: 'complete' } },
      { id: 2, name: 'Cook County, IL', state: 'IL', fips_code: '17031', population: 5173146, missing_categories: ['vital_records', 'voter_records'], current_coverage: {} },
      { id: 3, name: 'Harris County, TX', state: 'TX', fips_code: '48201', population: 4731145, missing_categories: [], current_coverage: { court_records: 'complete' } },
      { id: 4, name: 'Maricopa County, AZ', state: 'AZ', fips_code: '04013', population: 4485414, missing_categories: ['criminal_records'], current_coverage: {} },
    ];

    try {
      // Try to fetch from API
      const summaryResponse = await apiService.getCoverageSummary();
      if (summaryResponse.data) {
        setSummary(summaryResponse.data);
      } else {
        setSummary(mockSummary);
      }

      const gapsResponse = await apiService.getCoverageGaps({
        state: selectedState || undefined,
      });
      if (gapsResponse.data) {
        setGaps(gapsResponse.data);
      } else {
        setGaps(mockGaps);
      }
    } catch (err: any) {
      // Fall back to mock data on error
      console.warn('API unavailable, using mock data:', err.message);
      setSummary(mockSummary);
      setGaps(mockGaps);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    loadCoverageData();
  };

  const getStatusColor = (percentage: number): 'success' | 'warning' | 'error' => {
    if (percentage >= 80) return 'success';
    if (percentage >= 40) return 'warning';
    return 'error';
  };

  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  if (loading) {
    return (
      <MainLayout>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
          <CircularProgress />
        </Box>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box>
            <Typography variant="h4" component="h1" gutterBottom>
              Coverage Dashboard
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Monitor and manage public records coverage across all US jurisdictions
            </Typography>
          </Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
          >
            Refresh
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Summary Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <MapIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="subtitle2" color="text.secondary">
                    Total Jurisdictions
                  </Typography>
                </Box>
                <Typography variant="h4">
                  {formatNumber(summary?.total_jurisdictions || 0)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Counties, parishes & boroughs
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                  <Typography variant="subtitle2" color="text.secondary">
                    With Coverage
                  </Typography>
                </Box>
                <Typography variant="h4">
                  {formatNumber(summary?.jurisdictions_with_coverage || 0)}
                </Typography>
                <Box sx={{ mt: 1 }}>
                  <LinearProgress
                    variant="determinate"
                    value={summary?.coverage_percentage || 0}
                    color={getStatusColor(summary?.coverage_percentage || 0)}
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {(summary?.coverage_percentage || 0).toFixed(1)}% coverage
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <TrendingUpIcon color="info" sx={{ mr: 1 }} />
                  <Typography variant="subtitle2" color="text.secondary">
                    Complete Coverage
                  </Typography>
                </Box>
                <Typography variant="h4">
                  {formatNumber(summary?.jurisdictions_complete || 0)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  All data categories available
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <WarningIcon color="warning" sx={{ mr: 1 }} />
                  <Typography variant="subtitle2" color="text.secondary">
                    Coverage Gaps
                  </Typography>
                </Box>
                <Typography variant="h4">
                  {formatNumber((summary?.total_jurisdictions || 0) - (summary?.jurisdictions_with_coverage || 0))}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Jurisdictions needing data
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Tabs */}
        <Paper sx={{ mb: 3 }}>
          <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}>
            <Tab label="State Overview" />
            <Tab label="Coverage Gaps" />
            <Tab label="Data Categories" />
          </Tabs>
        </Paper>

        {/* State Overview Tab */}
        {activeTab === 0 && (
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Jurisdictions by State
            </Typography>
            <Grid container spacing={2}>
              {summary?.by_state && Object.entries(summary.by_state)
                .sort((a, b) => b[1] - a[1])
                .map(([state, count]) => (
                  <Grid item xs={6} sm={4} md={3} lg={2} key={state}>
                    <Card variant="outlined" sx={{ textAlign: 'center', p: 1 }}>
                      <Typography variant="h6" color="primary">
                        {state}
                      </Typography>
                      <Typography variant="body2">
                        {count} counties
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {STATE_NAMES[state] || state}
                      </Typography>
                    </Card>
                  </Grid>
                ))}
            </Grid>
          </Paper>
        )}

        {/* Coverage Gaps Tab */}
        {activeTab === 1 && (
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                select
                label="Filter by State"
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
                size="small"
                sx={{ minWidth: 150 }}
              >
                <MenuItem value="">All States</MenuItem>
                {Object.keys(STATE_NAMES).sort().map((state) => (
                  <MenuItem key={state} value={state}>
                    {state} - {STATE_NAMES[state]}
                  </MenuItem>
                ))}
              </TextField>

              <TextField
                select
                label="Filter by Category"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                size="small"
                sx={{ minWidth: 180 }}
              >
                <MenuItem value="">All Categories</MenuItem>
                {DATA_CATEGORIES.map((cat) => (
                  <MenuItem key={cat} value={cat}>
                    {cat.replace(/_/g, ' ')}
                  </MenuItem>
                ))}
              </TextField>
            </Box>

            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Jurisdiction</TableCell>
                    <TableCell>State</TableCell>
                    <TableCell>FIPS</TableCell>
                    <TableCell align="right">Population</TableCell>
                    <TableCell>Missing Categories</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {gaps
                    .filter((gap) => !selectedState || gap.state === selectedState)
                    .map((gap) => (
                      <TableRow key={gap.id}>
                        <TableCell>{gap.name}</TableCell>
                        <TableCell>
                          <Chip label={gap.state} size="small" />
                        </TableCell>
                        <TableCell>{gap.fips_code}</TableCell>
                        <TableCell align="right">{formatNumber(gap.population)}</TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                            {gap.missing_categories.length > 0 ? (
                              gap.missing_categories.map((cat) => (
                                <Chip
                                  key={cat}
                                  label={cat.replace(/_/g, ' ')}
                                  size="small"
                                  color="warning"
                                  variant="outlined"
                                />
                              ))
                            ) : (
                              <Chip label="Complete" size="small" color="success" />
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Tooltip title="Refresh Coverage">
                            <IconButton size="small">
                              <RefreshIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        )}

        {/* Data Categories Tab */}
        {activeTab === 2 && (
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Coverage by Data Category
            </Typography>
            <Grid container spacing={2}>
              {DATA_CATEGORIES.map((category) => (
                <Grid item xs={12} sm={6} md={4} key={category}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle1" sx={{ textTransform: 'capitalize' }}>
                        {category.replace(/_/g, ' ')}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={Math.random() * 30} // Mock data
                          sx={{ flexGrow: 1, mr: 2, height: 8, borderRadius: 4 }}
                          color="primary"
                        />
                        <Typography variant="body2" color="text.secondary">
                          {Math.floor(Math.random() * 1000)} / 3240
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>
        )}

        {/* Quick Stats Footer */}
        <Paper sx={{ p: 2, mt: 3, bgcolor: 'grey.50' }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Quick Stats
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={6} md={3}>
              <Typography variant="body2">
                <strong>States Covered:</strong> 56 (50 + DC + territories)
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="body2">
                <strong>Data Categories:</strong> {DATA_CATEGORIES.length}
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="body2">
                <strong>Largest State:</strong> TX (254 counties)
              </Typography>
            </Grid>
            <Grid item xs={6} md={3}>
              <Typography variant="body2">
                <strong>Target:</strong> 100% coverage
              </Typography>
            </Grid>
          </Grid>
        </Paper>
      </Box>
    </MainLayout>
  );
}
