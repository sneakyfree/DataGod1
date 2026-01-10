'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Database,
  Globe,
  RefreshCw,
  TrendingUp,
  XCircle,
} from 'lucide-react';

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
  if (percent >= 80) return 'bg-green-500';
  if (percent >= 60) return 'bg-green-400';
  if (percent >= 40) return 'bg-yellow-400';
  if (percent >= 20) return 'bg-orange-400';
  if (percent > 0) return 'bg-red-400';
  return 'bg-gray-200';
}

// Helper to get grade color
function getGradeColor(grade: string): string {
  switch (grade) {
    case 'A': return 'bg-green-500 text-white';
    case 'B': return 'bg-green-400 text-white';
    case 'C': return 'bg-yellow-400 text-black';
    case 'D': return 'bg-orange-400 text-white';
    case 'F': return 'bg-red-500 text-white';
    default: return 'bg-gray-400 text-white';
  }
}

// Overview Card Component
function OverviewCard({ data }: { data: CoverageData }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">States Covered</CardTitle>
          <Globe className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{data.states_covered}/{data.total_states}</div>
          <Progress value={(data.states_covered / data.total_states) * 100} className="mt-2" />
          <p className="text-xs text-muted-foreground mt-2">
            {data.coverage_percent.toFixed(1)}% coverage
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Records</CardTitle>
          <Database className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{data.total_records.toLocaleString()}</div>
          <p className="text-xs text-muted-foreground mt-2">
            Across all jurisdictions
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Jurisdictions</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{data.jurisdictions_tracked}</div>
          <p className="text-xs text-muted-foreground mt-2">
            Active data sources
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Coverage Rate</CardTitle>
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{data.coverage_percent.toFixed(1)}%</div>
          <Progress value={data.coverage_percent} className="mt-2" />
        </CardContent>
      </Card>
    </div>
  );
}

// Coverage Heatmap Component
function CoverageHeatmap({ heatmapData }: { heatmapData: Record<string, number> }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>State Coverage Heatmap</CardTitle>
        <CardDescription>Coverage percentage by state</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-8 gap-1">
          {US_STATES.map((state) => {
            const coverage = heatmapData[state] || 0;
            return (
              <div
                key={state}
                className={`${getCoverageColor(coverage)} p-2 rounded text-center text-xs font-medium`}
                title={`${state}: ${coverage.toFixed(1)}%`}
              >
                {state}
              </div>
            );
          })}
        </div>
        <div className="flex items-center justify-center mt-4 gap-2 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-gray-200 rounded"></div>
            <span>0%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-red-400 rounded"></div>
            <span>1-20%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-orange-400 rounded"></div>
            <span>20-40%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-yellow-400 rounded"></div>
            <span>40-60%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-green-400 rounded"></div>
            <span>60-80%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-green-500 rounded"></div>
            <span>80-100%</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Quality Summary Component
function QualitySummaryCard({ quality }: { quality: QualitySummary }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Data Quality</CardTitle>
        <CardDescription>Quality metrics across all datasets</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Average Score</span>
            <span className="text-2xl font-bold">{quality.avg_score.toFixed(1)}</span>
          </div>
          <Progress value={quality.avg_score} className="h-2" />

          <div className="space-y-2">
            <span className="text-sm font-medium">Grade Distribution</span>
            <div className="flex gap-2">
              {['A', 'B', 'C', 'D', 'F'].map((grade) => (
                <Badge key={grade} className={getGradeColor(grade)}>
                  {grade}: {quality.grade_distribution[grade] || 0}
                </Badge>
              ))}
            </div>
          </div>

          {quality.lowest_scoring.length > 0 && (
            <div className="space-y-2">
              <span className="text-sm font-medium text-red-500">Needs Attention</span>
              <div className="space-y-1">
                {quality.lowest_scoring.slice(0, 3).map((item, i) => (
                  <div key={i} className="flex justify-between text-sm">
                    <span>{item.dataset}</span>
                    <Badge variant="destructive">{item.score.toFixed(1)}</Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// Error Summary Component
function ErrorSummaryCard({ errors }: { errors: ErrorSummary }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Error Log</CardTitle>
        <CardDescription>Recent errors and issues</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-red-500">{errors.unresolved_count}</div>
              <div className="text-xs text-muted-foreground">Unresolved</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-500">{errors.resolved_count}</div>
              <div className="text-xs text-muted-foreground">Resolved</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{errors.total_errors}</div>
              <div className="text-xs text-muted-foreground">Total</div>
            </div>
          </div>

          {errors.unresolved_count > 0 && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Active Issues</AlertTitle>
              <AlertDescription>
                {errors.unresolved_count} unresolved errors require attention
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <span className="text-sm font-medium">Recent Errors</span>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {errors.recent_errors.slice(0, 5).map((error, i) => (
                <div key={i} className="p-2 border rounded text-sm">
                  <div className="flex justify-between">
                    <Badge variant="outline">{error.source}</Badge>
                    <span className="text-xs text-muted-foreground">
                      {new Date(error.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <div className="mt-1 text-muted-foreground truncate">{error.message}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Quota Summary Component
function QuotaSummaryCard({ quotas }: { quotas: QuotaSummary }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>API Quotas</CardTitle>
        <CardDescription>Usage across all APIs</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {quotas.critical_count > 0 && (
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertTitle>Critical</AlertTitle>
              <AlertDescription>
                {quotas.critical_count} API(s) at critical quota levels
              </AlertDescription>
            </Alert>
          )}

          {quotas.warning_count > 0 && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Warning</AlertTitle>
              <AlertDescription>
                {quotas.warning_count} API(s) approaching quota limits
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-3">
            {quotas.quotas.map((quota, i) => (
              <div key={i} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium">{quota.api_name}</span>
                  <span>
                    {quota.used.toLocaleString()} / {quota.limit.toLocaleString()}
                  </span>
                </div>
                <Progress
                  value={quota.usage_percent}
                  className={`h-2 ${
                    quota.is_critical ? 'bg-red-200' :
                    quota.is_warning ? 'bg-yellow-200' : ''
                  }`}
                />
              </div>
            ))}
          </div>
        </div>
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
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Data Quality Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor coverage, quality, and system health
          </p>
        </div>
        <div className="flex items-center gap-4">
          {lastUpdated && (
            <span className="text-sm text-muted-foreground">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={fetchDashboardData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      <OverviewCard data={data.overview} />

      <Tabs defaultValue="coverage" className="space-y-4">
        <TabsList>
          <TabsTrigger value="coverage">Coverage</TabsTrigger>
          <TabsTrigger value="quality">Quality</TabsTrigger>
          <TabsTrigger value="errors">Errors</TabsTrigger>
          <TabsTrigger value="quotas">API Quotas</TabsTrigger>
        </TabsList>

        <TabsContent value="coverage" className="space-y-4">
          <CoverageHeatmap heatmapData={data.coverage.heatmap_data} />
        </TabsContent>

        <TabsContent value="quality" className="space-y-4">
          <QualitySummaryCard quality={data.quality} />
        </TabsContent>

        <TabsContent value="errors" className="space-y-4">
          <ErrorSummaryCard errors={data.errors} />
        </TabsContent>

        <TabsContent value="quotas" className="space-y-4">
          <QuotaSummaryCard quotas={data.quotas} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default DataQualityDashboard;
