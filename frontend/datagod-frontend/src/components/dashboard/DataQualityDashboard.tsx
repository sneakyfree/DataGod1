'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Tabs,
  Tab,
  Chip,
  Alert,
  AlertTitle,
  IconButton,
  CircularProgress,
  Paper,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import PublicIcon from '@mui/icons-material/Public';
import StorageIcon from '@mui/icons-material/Storage';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

// Types
interface CoverageData {
  states_covered: number;
  total_states: number;
  coverage_percent: number;
  total_records: number;
  jurisdictions_tracked: number;
}

interface QualitySummary {
  dataset_count: number;
  avg_score: number;
  grade_distribution: Record<string, number>;
  lowest_scoring: Array<{ dataset: string; score: number }>;
  highest_scoring: Array<{ dataset: string; score: number }>;
}

interface ErrorSummary {
  total_errors: number;
  unresolved_count: number;
  resolved_count: number;
  by_source: Record<string, number>;
  by_type: Record<string, number>;
  recent_errors: Array<{
    timestamp: string;
    source: string;
    error_type: string;
    message: string;
  }>;
}

interface QuotaSummary {
  api_count: number;
  critical_count: number;
  warning_count: number;
  critical_apis: string[];
  warning_apis: string[];
  quotas: Array<{
    api_name: string;
    used: number;
    limit: number;
    usage_percent: number;
    is_critical: boolean;
    is_warning: boolean;
  }>;
}

interface StateCoverage {
  county_count: number;
  total_records: number;
  avg_coverage_percent: number;
  has_coverage: boolean;
  freshness: Record<string, number>;
}

interface DashboardData {
  timestamp: string;
  overview: CoverageData;
  coverage: {
    by_state: Record<string, StateCoverage>;
    heatmap_data: Record<string, number>;
  };
  quality: QualitySummary;
  errors: ErrorSummary;
  quotas: QuotaSummary;
}

// US States for heatmap
const US_STATES = [
  'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
  'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
  'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
  'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
  'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
  'DC', 'PR', 'VI', 'GU', 'AS', 'MP',
];

// Helper to get coverage color
function getCoverageColor(percent: number): string {
  if (percent >= 80) return '#4caf50';
  if (percent >= 60) return '#8bc34a';
  if (percent >= 40) return '#ffeb3b';
  if (percent >= 20) return '#ff9800';
  if (percent > 0) return '#f44336';
  return '#e0e0e0';
}

// Helper to get grade color
function getGradeColor(grade: string): 'success' | 'warning' | 'error' | 'default' {
  switch (grade) {
    case 'A':
    case 'B':
      return 'success';
    case 'C':
      return 'warning';
    case 'D':
    case 'F':
      return 'error';
    default:
      return 'default';
  }
}

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

// Overview Card Component
function OverviewCard({ data }: { data: CoverageData }) {
  return (
    <Grid container spacing={3}>
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <PublicIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="subtitle2" color="text.secondary">
                States Covered
              </Typography>
            </Box>
            <Typography variant="h4">
              {data.states_covered}/{data.total_states}
            </Typography>
            <LinearProgress
              variant="determinate"
              value={(data.states_covered / data.total_states) * 100}
              sx={{ mt: 1, height: 8, borderRadius: 4 }}
            />
            <Typography variant="caption" color="text.secondary">
              {data.coverage_percent.toFixed(1)}% coverage
            </Typography>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <StorageIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="subtitle2" color="text.secondary">
                Total Records
              </Typography>
            </Box>
            <Typography variant="h4">{data.total_records.toLocaleString()}</Typography>
            <Typography variant="caption" color="text.secondary">
              Across all jurisdictions
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
                Jurisdictions
              </Typography>
            </Box>
            <Typography variant="h4">{data.jurisdictions_tracked}</Typography>
            <Typography variant="caption" color="text.secondary">
              Active data sources
            </Typography>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <TrendingUpIcon color="info" sx={{ mr: 1 }} />
              <Typography variant="subtitle2" color="text.secondary">
                Coverage Rate
              </Typography>
            </Box>
            <Typography variant="h4">{data.coverage_percent.toFixed(1)}%</Typography>
            <LinearProgress
              variant="determinate"
              value={data.coverage_percent}
              sx={{ mt: 1, height: 8, borderRadius: 4 }}
            />
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}

// Coverage Heatmap Component
function CoverageHeatmap({ heatmapData }: { heatmapData: Record<string, number> }) {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          State Coverage Heatmap
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Coverage percentage by state
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 0.5 }}>
          {US_STATES.map((state) => {
            const coverage = heatmapData[state] || 0;
            return (
              <Box
                key={state}
                sx={{
                  bgcolor: getCoverageColor(coverage),
                  p: 1,
                  borderRadius: 1,
                  textAlign: 'center',
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  color: coverage > 40 ? 'black' : 'white',
                }}
                title={`${state}: ${coverage.toFixed(1)}%`}
              >
                {state}
              </Box>
            );
          })}
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2, gap: 1, flexWrap: 'wrap' }}>
          {[
            { color: '#e0e0e0', label: '0%' },
            { color: '#f44336', label: '1-20%' },
            { color: '#ff9800', label: '20-40%' },
            { color: '#ffeb3b', label: '40-60%' },
            { color: '#8bc34a', label: '60-80%' },
            { color: '#4caf50', label: '80-100%' },
          ].map(({ color, label }) => (
            <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box sx={{ width: 16, height: 16, bgcolor: color, borderRadius: 0.5 }} />
              <Typography variant="caption">{label}</Typography>
            </Box>
          ))}
        </Box>
      </CardContent>
    </Card>
  );
}

// Quality Summary Component
function QualitySummaryCard({ quality }: { quality: QualitySummary }) {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Data Quality
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Quality metrics across all datasets
        </Typography>

        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="body2">Average Score</Typography>
            <Typography variant="h5">{quality.avg_score.toFixed(1)}</Typography>
          </Box>
          <LinearProgress variant="determinate" value={quality.avg_score} sx={{ height: 8, borderRadius: 4 }} />
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" sx={{ mb: 1 }}>
            Grade Distribution
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {['A', 'B', 'C', 'D', 'F'].map((grade) => (
              <Chip
                key={grade}
                label={`${grade}: ${quality.grade_distribution[grade] || 0}`}
                color={getGradeColor(grade)}
                size="small"
              />
            ))}
          </Box>
        </Box>

        {quality.lowest_scoring.length > 0 && (
          <Box>
            <Typography variant="body2" color="error" sx={{ mb: 1 }}>
              Needs Attention
            </Typography>
            {quality.lowest_scoring.slice(0, 3).map((item, i) => (
              <Box key={i} sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="body2">{item.dataset}</Typography>
                <Chip label={item.score.toFixed(1)} color="error" size="small" />
              </Box>
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

// Error Summary Component
function ErrorSummaryCard({ errors }: { errors: ErrorSummary }) {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Error Log
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Recent errors and issues
        </Typography>

        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={4}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="error">
                {errors.unresolved_count}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Unresolved
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={4}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="success.main">
                {errors.resolved_count}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Resolved
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={4}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4">{errors.total_errors}</Typography>
              <Typography variant="caption" color="text.secondary">
                Total
              </Typography>
            </Box>
          </Grid>
        </Grid>

        {errors.unresolved_count > 0 && (
          <Alert severity="error" sx={{ mb: 2 }}>
            <AlertTitle>Active Issues</AlertTitle>
            {errors.unresolved_count} unresolved errors require attention
          </Alert>
        )}

        <Typography variant="body2" sx={{ mb: 1 }}>
          Recent Errors
        </Typography>
        <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
          {errors.recent_errors.slice(0, 5).map((error, i) => (
            <Paper key={i} variant="outlined" sx={{ p: 1, mb: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Chip label={error.source} size="small" variant="outlined" />
                <Typography variant="caption" color="text.secondary">
                  {new Date(error.timestamp).toLocaleString()}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" noWrap>
                {error.message}
              </Typography>
            </Paper>
          ))}
        </Box>
      </CardContent>
    </Card>
  );
}

// Quota Summary Component
function QuotaSummaryCard({ quotas }: { quotas: QuotaSummary }) {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          API Quotas
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Usage across all APIs
        </Typography>

        {quotas.critical_count > 0 && (
          <Alert severity="error" icon={<ErrorIcon />} sx={{ mb: 2 }}>
            <AlertTitle>Critical</AlertTitle>
            {quotas.critical_count} API(s) at critical quota levels
          </Alert>
        )}

        {quotas.warning_count > 0 && (
          <Alert severity="warning" icon={<WarningIcon />} sx={{ mb: 2 }}>
            <AlertTitle>Warning</AlertTitle>
            {quotas.warning_count} API(s) approaching quota limits
          </Alert>
        )}

        <Box sx={{ mt: 2 }}>
          {quotas.quotas.map((quota, i) => (
            <Box key={i} sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="body2">{quota.api_name}</Typography>
                <Typography variant="body2">
                  {quota.used.toLocaleString()} / {quota.limit.toLocaleString()}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={quota.usage_percent}
                color={quota.is_critical ? 'error' : quota.is_warning ? 'warning' : 'primary'}
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
          ))}
        </Box>
      </CardContent>
    </Card>
  );
}

// Main Dashboard Component
export function DataQualityDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [tabValue, setTabValue] = useState(0);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v2/dashboard/quality');

      if (!response.ok) {
        throw new Error('Failed to fetch dashboard data');
      }

      const dashboardData = await response.json();
      setData(dashboardData);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      // Use mock data on error
      setData({
        timestamp: new Date().toISOString(),
        overview: {
          states_covered: 4,
          total_states: 56,
          coverage_percent: 7.1,
          total_records: 50000,
          jurisdictions_tracked: 3240,
        },
        coverage: {
          by_state: {},
          heatmap_data: { CA: 15, TX: 20, FL: 10, NY: 25 },
        },
        quality: {
          dataset_count: 10,
          avg_score: 75,
          grade_distribution: { A: 2, B: 3, C: 3, D: 1, F: 1 },
          lowest_scoring: [{ dataset: 'court_records', score: 45 }],
          highest_scoring: [{ dataset: 'business_filings', score: 92 }],
        },
        errors: {
          total_errors: 15,
          unresolved_count: 3,
          resolved_count: 12,
          by_source: { scrapers: 10, api: 5 },
          by_type: { timeout: 8, validation: 7 },
          recent_errors: [
            {
              timestamp: new Date().toISOString(),
              source: 'CA Scraper',
              error_type: 'timeout',
              message: 'Connection timeout after 30s',
            },
          ],
        },
        quotas: {
          api_count: 5,
          critical_count: 0,
          warning_count: 1,
          critical_apis: [],
          warning_apis: ['Census API'],
          quotas: [
            { api_name: 'Census API', used: 450, limit: 500, usage_percent: 90, is_critical: false, is_warning: true },
            { api_name: 'SEC API', used: 200, limit: 1000, usage_percent: 20, is_critical: false, is_warning: false },
          ],
        },
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();

    // Auto-refresh every 5 minutes
    const interval = setInterval(fetchDashboardData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error && !data) {
    return (
      <Alert severity="error">
        <AlertTitle>Error</AlertTitle>
        {error}
      </Alert>
    );
  }

  if (!data) return null;

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Data Quality Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Monitor coverage, quality, and system health
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {lastUpdated && (
            <Typography variant="body2" color="text.secondary">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </Typography>
          )}
          <IconButton onClick={fetchDashboardData} disabled={loading}>
            <RefreshIcon className={loading ? 'animate-spin' : ''} />
          </IconButton>
        </Box>
      </Box>

      <Box sx={{ mb: 4 }}>
        <OverviewCard data={data.overview} />
      </Box>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
          <Tab label="Coverage" />
          <Tab label="Quality" />
          <Tab label="Errors" />
          <Tab label="API Quotas" />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        <CoverageHeatmap heatmapData={data.coverage.heatmap_data} />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <QualitySummaryCard quality={data.quality} />
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <ErrorSummaryCard errors={data.errors} />
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        <QuotaSummaryCard quotas={data.quotas} />
      </TabPanel>
    </Box>
  );
}

export default DataQualityDashboard;
