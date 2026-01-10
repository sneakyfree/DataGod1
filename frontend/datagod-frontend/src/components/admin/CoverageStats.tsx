'use client';

import { useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  CircularProgress,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import StorageIcon from '@mui/icons-material/Storage';
import PublicIcon from '@mui/icons-material/Public';
import CategoryIcon from '@mui/icons-material/Category';

interface CategoryStats {
  category: string;
  display_name: string;
  coverage_percentage: number;
  covered_count: number;
  total_count: number;
  record_count: number;
  freshness: string;
}

interface CoverageStatsProps {
  totalJurisdictions?: number;
  jurisdictionsWithCoverage?: number;
  jurisdictionsComplete?: number;
  coveragePercentage?: number;
  totalRecords?: number;
  statesWithCoverage?: number;
  totalStates?: number;
  categoryCoverage?: CategoryStats[];
  loading?: boolean;
}

export function CoverageStats({
  totalJurisdictions = 0,
  jurisdictionsWithCoverage = 0,
  jurisdictionsComplete = 0,
  coveragePercentage = 0,
  totalRecords = 0,
  statesWithCoverage = 0,
  totalStates = 56,
  categoryCoverage = [],
  loading = false,
}: CoverageStatsProps) {
  const coverageGaps = totalJurisdictions - jurisdictionsWithCoverage;
  const completePercentage = totalJurisdictions > 0
    ? (jurisdictionsComplete / totalJurisdictions) * 100
    : 0;

  const getStatusColor = (pct: number): 'success' | 'warning' | 'error' => {
    if (pct >= 80) return 'success';
    if (pct >= 40) return 'warning';
    return 'error';
  };

  const getStatusIcon = (pct: number) => {
    if (pct >= 80) return <CheckCircleIcon color="success" />;
    if (pct >= 40) return <WarningIcon color="warning" />;
    return <ErrorIcon color="error" />;
  };

  const getFreshnessColor = (freshness: string): string => {
    switch (freshness) {
      case 'realtime':
      case 'daily':
        return '#2e7d32';
      case 'weekly':
        return '#4caf50';
      case 'monthly':
        return '#ff9800';
      case 'stale':
      case 'never':
        return '#f44336';
      default:
        return '#9e9e9e';
    }
  };

  // Sort categories by coverage percentage
  const sortedCategories = useMemo(() => {
    return [...categoryCoverage].sort((a, b) => b.coverage_percentage - a.coverage_percentage);
  }, [categoryCoverage]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Overview Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <PublicIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="subtitle2" color="text.secondary">
                  Total Jurisdictions
                </Typography>
              </Box>
              <Typography variant="h4">{totalJurisdictions.toLocaleString()}</Typography>
              <Typography variant="caption" color="text.secondary">
                US counties, parishes & boroughs
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
              <Typography variant="h4">{jurisdictionsWithCoverage.toLocaleString()}</Typography>
              <Box sx={{ mt: 1 }}>
                <LinearProgress
                  variant="determinate"
                  value={coveragePercentage}
                  color={getStatusColor(coveragePercentage)}
                  sx={{ height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" color="text.secondary">
                  {coveragePercentage.toFixed(1)}% overall coverage
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
              <Typography variant="h4">{jurisdictionsComplete.toLocaleString()}</Typography>
              <Box sx={{ mt: 1 }}>
                <LinearProgress
                  variant="determinate"
                  value={completePercentage}
                  color="info"
                  sx={{ height: 8, borderRadius: 4 }}
                />
                <Typography variant="caption" color="text.secondary">
                  {completePercentage.toFixed(1)}% fully complete
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <StorageIcon color="secondary" sx={{ mr: 1 }} />
                <Typography variant="subtitle2" color="text.secondary">
                  Total Records
                </Typography>
              </Box>
              <Typography variant="h4">{totalRecords.toLocaleString()}</Typography>
              <Typography variant="caption" color="text.secondary">
                Across all categories
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Coverage by Category */}
      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <CategoryIcon sx={{ mr: 1 }} color="primary" />
          <Typography variant="h6">Coverage by Category</Typography>
        </Box>

        <List dense>
          {sortedCategories.map((cat, idx) => (
            <Box key={cat.category}>
              <ListItem>
                <ListItemIcon>
                  {getStatusIcon(cat.coverage_percentage)}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body1" sx={{ textTransform: 'capitalize' }}>
                        {cat.display_name}
                      </Typography>
                      <Chip
                        label={cat.freshness}
                        size="small"
                        sx={{
                          bgcolor: getFreshnessColor(cat.freshness),
                          color: '#fff',
                          fontSize: '0.65rem',
                          height: 20,
                        }}
                      />
                    </Box>
                  }
                  secondary={
                    <Box sx={{ mt: 0.5 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Box sx={{ flexGrow: 1 }}>
                          <LinearProgress
                            variant="determinate"
                            value={cat.coverage_percentage}
                            color={getStatusColor(cat.coverage_percentage)}
                            sx={{ height: 6, borderRadius: 3 }}
                          />
                        </Box>
                        <Typography variant="body2" sx={{ minWidth: 60, textAlign: 'right' }}>
                          {cat.coverage_percentage.toFixed(1)}%
                        </Typography>
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        {cat.covered_count.toLocaleString()} / {cat.total_count.toLocaleString()} jurisdictions
                        {cat.record_count > 0 && ` | ${cat.record_count.toLocaleString()} records`}
                      </Typography>
                    </Box>
                  }
                />
              </ListItem>
              {idx < sortedCategories.length - 1 && <Divider variant="inset" component="li" />}
            </Box>
          ))}
        </List>

        {sortedCategories.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 3 }}>
            No category data available
          </Typography>
        )}
      </Paper>

      {/* Quick Stats Summary */}
      <Paper sx={{ p: 2, mt: 2, bgcolor: 'grey.50' }}>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          Quick Stats
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={6} md={3}>
            <Typography variant="body2">
              <strong>States Covered:</strong> {statesWithCoverage} / {totalStates}
            </Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="body2">
              <strong>Coverage Gaps:</strong> {coverageGaps.toLocaleString()}
            </Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="body2">
              <strong>Categories:</strong> {categoryCoverage.length}
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
  );
}

export default CoverageStats;
