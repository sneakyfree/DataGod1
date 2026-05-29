"""
DataGod Data Analytics Engine

Statistical analysis, aggregations, and automated insights generation
for public records data.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

logger = logging.getLogger(__name__)


class InsightType(str, Enum):
    """Types of auto-generated insights."""

    TREND = "trend"
    COMPARISON = "comparison"
    ANOMALY = "anomaly"
    SUMMARY = "summary"
    RECOMMENDATION = "recommendation"
    CORRELATION = "correlation"


class InsightPriority(str, Enum):
    """Priority levels for insights."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Insight:
    """Auto-generated insight."""

    id: str
    insight_type: InsightType
    priority: InsightPriority
    title: str
    description: str
    value: Optional[float] = None
    comparison_value: Optional[float] = None
    change_pct: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "insight_type": self.insight_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "value": self.value,
            "comparison_value": self.comparison_value,
            "change_pct": self.change_pct,
            "metadata": self.metadata,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class TimeSeriesReport:
    """Time series analysis report."""

    trend: str  # 'increasing', 'decreasing', 'stable'
    trend_strength: float  # 0-1
    seasonality: Optional[str]  # 'daily', 'weekly', 'monthly', None
    seasonality_strength: float
    decomposition: Dict[str, List[float]]
    summary_stats: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trend": self.trend,
            "trend_strength": self.trend_strength,
            "seasonality": self.seasonality,
            "seasonality_strength": self.seasonality_strength,
            "decomposition": self.decomposition,
            "summary_stats": self.summary_stats,
        }


@dataclass
class DistributionReport:
    """Distribution analysis report."""

    column: str
    count: int
    mean: float
    median: float
    std: float
    min: float
    max: float
    percentiles: Dict[str, float]
    skewness: float
    kurtosis: float
    distribution_type: str  # 'normal', 'skewed', 'bimodal', 'uniform'
    histogram: Dict[str, List[float]]
    outlier_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "column": self.column,
            "count": self.count,
            "mean": self.mean,
            "median": self.median,
            "std": self.std,
            "min": self.min,
            "max": self.max,
            "percentiles": self.percentiles,
            "skewness": self.skewness,
            "kurtosis": self.kurtosis,
            "distribution_type": self.distribution_type,
            "histogram": self.histogram,
            "outlier_count": self.outlier_count,
        }


@dataclass
class CorrelationMatrix:
    """Correlation analysis result."""

    columns: List[str]
    matrix: List[List[float]]
    significant_pairs: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "columns": self.columns,
            "matrix": self.matrix,
            "significant_pairs": self.significant_pairs,
        }


@dataclass
class AggregationReport:
    """Group-wise aggregation report."""

    group_by: List[str]
    metrics: List[str]
    results: List[Dict[str, Any]]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_by": self.group_by,
            "metrics": self.metrics,
            "results": self.results,
            "summary": self.summary,
        }


class AnalyticsEngine:
    """
    Statistical analysis and insights generation engine.

    Provides comprehensive analytical capabilities:
    - Time series analysis (trend, seasonality, decomposition)
    - Distribution analysis (histograms, percentiles, outliers)
    - Correlation analysis (pairwise with significance)
    - Aggregation analysis (group-wise statistics)
    - Auto-generated insights with NLG
    """

    def __init__(self):
        """Initialize the analytics engine."""
        self._insight_cache: Dict[str, List[Insight]] = {}
        logger.info("AnalyticsEngine initialized")

    def time_series_analysis(
        self, data: pd.DataFrame, date_column: str = "date", value_column: str = "value"
    ) -> TimeSeriesReport:
        """
        Perform time series analysis.

        Args:
            data: DataFrame with time series data
            date_column: Name of date column
            value_column: Name of value column

        Returns:
            TimeSeriesReport with trend and seasonality analysis
        """
        df = data.copy()
        df[date_column] = pd.to_datetime(df[date_column])
        df = df.sort_values(date_column)
        values = df[value_column].values

        # Calculate basic stats
        summary_stats = {
            "count": len(values),
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
        }

        # Trend analysis
        x = np.arange(len(values))
        if len(values) >= 3:
            slope, intercept, r_value, _, _ = scipy_stats.linregress(x, values)
            trend_strength = abs(r_value)

            if slope > 0.01 * np.mean(values):
                trend = "increasing"
            elif slope < -0.01 * np.mean(values):
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
            trend_strength = 0.0

        # Seasonality detection
        seasonality = None
        seasonality_strength = 0.0

        if len(values) >= 14:
            # Check for weekly pattern (lag-7 autocorrelation)
            try:
                lag7_corr = np.corrcoef(values[:-7], values[7:])[0, 1]
                if not np.isnan(lag7_corr) and abs(lag7_corr) > 0.3:
                    seasonality = "weekly"
                    seasonality_strength = abs(lag7_corr)
            except Exception:
                pass

        if len(values) >= 60 and seasonality is None:
            # Check for monthly pattern
            try:
                lag30_corr = np.corrcoef(values[:-30], values[30:])[0, 1]
                if not np.isnan(lag30_corr) and abs(lag30_corr) > 0.3:
                    seasonality = "monthly"
                    seasonality_strength = abs(lag30_corr)
            except Exception:
                pass

        # Simple decomposition
        decomposition = {
            "original": values.tolist(),
            "trend": self._moving_average(values, min(7, len(values) // 2)).tolist(),
        }

        return TimeSeriesReport(
            trend=trend,
            trend_strength=round(trend_strength, 4),
            seasonality=seasonality,
            seasonality_strength=round(seasonality_strength, 4),
            decomposition=decomposition,
            summary_stats=summary_stats,
        )

    def distribution_analysis(
        self, data: pd.DataFrame, column: str
    ) -> DistributionReport:
        """
        Analyze the distribution of a column.

        Args:
            data: DataFrame to analyze
            column: Column name to analyze

        Returns:
            DistributionReport with distribution statistics
        """
        values = pd.to_numeric(data[column], errors="coerce").dropna()

        if len(values) == 0:
            return DistributionReport(
                column=column,
                count=0,
                mean=0.0,
                median=0.0,
                std=0.0,
                min=0.0,
                max=0.0,
                percentiles={},
                skewness=0.0,
                kurtosis=0.0,
                distribution_type="no_data",
                histogram={"bins": [], "counts": []},
                outlier_count=0,
            )

        # Basic statistics
        count = len(values)
        mean = float(values.mean())
        median = float(values.median())
        std = float(values.std())
        min_val = float(values.min())
        max_val = float(values.max())

        # Percentiles
        percentiles = {
            "p5": float(np.percentile(values, 5)),
            "p25": float(np.percentile(values, 25)),
            "p50": float(np.percentile(values, 50)),
            "p75": float(np.percentile(values, 75)),
            "p95": float(np.percentile(values, 95)),
            "p99": float(np.percentile(values, 99)),
        }

        # Skewness and kurtosis
        skewness = float(scipy_stats.skew(values))
        kurtosis = float(scipy_stats.kurtosis(values))

        # Determine distribution type
        if abs(skewness) < 0.5 and abs(kurtosis) < 1:
            distribution_type = "normal"
        elif abs(skewness) > 1:
            distribution_type = "skewed"
        elif kurtosis > 2:
            distribution_type = "heavy_tailed"
        else:
            distribution_type = "mixed"

        # Histogram
        hist_counts, hist_bins = np.histogram(values, bins=20)
        histogram = {
            "bins": hist_bins.tolist(),
            "counts": hist_counts.tolist(),
        }

        # Outlier detection (IQR method)
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outlier_count = int(((values < lower_bound) | (values > upper_bound)).sum())

        return DistributionReport(
            column=column,
            count=count,
            mean=mean,
            median=median,
            std=std,
            min=min_val,
            max=max_val,
            percentiles=percentiles,
            skewness=round(skewness, 4),
            kurtosis=round(kurtosis, 4),
            distribution_type=distribution_type,
            histogram=histogram,
            outlier_count=outlier_count,
        )

    def correlation_analysis(
        self,
        data: pd.DataFrame,
        columns: Optional[List[str]] = None,
        method: str = "pearson",
    ) -> CorrelationMatrix:
        """
        Calculate pairwise correlations with significance testing.

        Args:
            data: DataFrame to analyze
            columns: Columns to include (None for all numeric)
            method: Correlation method ('pearson', 'spearman', 'kendall')

        Returns:
            CorrelationMatrix with correlation values and significant pairs
        """
        numeric_data = data.select_dtypes(include=[np.number])

        if columns:
            columns = [c for c in columns if c in numeric_data.columns]
            numeric_data = numeric_data[columns]

        if numeric_data.empty or len(numeric_data.columns) < 2:
            return CorrelationMatrix(
                columns=[],
                matrix=[],
                significant_pairs=[],
            )

        # Calculate correlation matrix
        corr_matrix = numeric_data.corr(method=method)

        # Find significant pairs
        significant_pairs = []
        columns_list = corr_matrix.columns.tolist()

        for i in range(len(columns_list)):
            for j in range(i + 1, len(columns_list)):
                col1, col2 = columns_list[i], columns_list[j]
                corr = corr_matrix.loc[col1, col2]

                if not np.isnan(corr) and abs(corr) > 0.3:  # Significant threshold
                    # Calculate p-value
                    valid_data = numeric_data[[col1, col2]].dropna()
                    if len(valid_data) >= 3:
                        if method == "pearson":
                            _, p_value = scipy_stats.pearsonr(
                                valid_data[col1], valid_data[col2]
                            )
                        elif method == "spearman":
                            _, p_value = scipy_stats.spearmanr(
                                valid_data[col1], valid_data[col2]
                            )
                        else:
                            _, p_value = scipy_stats.kendalltau(
                                valid_data[col1], valid_data[col2]
                            )

                        if p_value < 0.05:  # Statistically significant
                            relationship = "positive" if corr > 0 else "negative"
                            strength = "strong" if abs(corr) > 0.7 else "moderate"

                            significant_pairs.append(
                                {
                                    "column1": col1,
                                    "column2": col2,
                                    "correlation": round(float(corr), 4),
                                    "p_value": round(float(p_value), 6),
                                    "relationship": relationship,
                                    "strength": strength,
                                }
                            )

        # Sort by absolute correlation
        significant_pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)

        return CorrelationMatrix(
            columns=columns_list,
            matrix=corr_matrix.values.tolist(),
            significant_pairs=significant_pairs[:20],  # Top 20
        )

    def aggregation_analysis(
        self,
        data: pd.DataFrame,
        group_by: List[str],
        metrics: Optional[List[str]] = None,
        agg_functions: Optional[List[str]] = None,
    ) -> AggregationReport:
        """
        Perform group-wise aggregation analysis.

        Args:
            data: DataFrame to analyze
            group_by: Columns to group by
            metrics: Columns to aggregate (None for all numeric)
            agg_functions: Aggregation functions ('sum', 'mean', 'count', 'min', 'max')

        Returns:
            AggregationReport with group-wise statistics
        """
        # Validate group_by columns
        group_by = [c for c in group_by if c in data.columns]
        if not group_by:
            return AggregationReport(group_by=[], metrics=[], results=[], summary={})

        # Get numeric columns for metrics
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
        if metrics:
            metrics = [m for m in metrics if m in numeric_cols]
        else:
            metrics = numeric_cols

        if not metrics:
            return AggregationReport(
                group_by=group_by, metrics=[], results=[], summary={}
            )

        # Default aggregation functions
        if not agg_functions:
            agg_functions = ["count", "mean", "sum"]

        # Perform aggregation
        agg_dict = {m: agg_functions for m in metrics}
        grouped = data.groupby(group_by, as_index=False).agg(agg_dict)

        # Flatten column names
        grouped.columns = [f"{c[0]}_{c[1]}" if c[1] else c[0] for c in grouped.columns]

        # Convert to results list
        results = grouped.head(100).to_dict("records")  # Limit to 100 groups

        # Summary statistics
        summary = {
            "total_groups": len(grouped),
            "rows_per_group_avg": len(data) / len(grouped) if len(grouped) > 0 else 0,
        }

        # Add metric summaries
        for metric in metrics:
            col_name = f"{metric}_sum"
            if col_name in grouped.columns:
                summary[f"{metric}_total"] = float(grouped[col_name].sum())

        return AggregationReport(
            group_by=group_by,
            metrics=metrics,
            results=results,
            summary=summary,
        )

    def generate_insights(
        self,
        data: pd.DataFrame,
        date_column: Optional[str] = None,
        compare_period: bool = True,
    ) -> List[Insight]:
        """
        Auto-generate insights from the data.

        Args:
            data: DataFrame to analyze
            date_column: Optional date column for time-based insights
            compare_period: Compare with previous period

        Returns:
            List of auto-generated insights
        """
        insights: List[Insight] = []

        if len(data) == 0:
            return insights

        # Summary insights
        insights.append(
            Insight(
                id=self._generate_id("summary_total"),
                insight_type=InsightType.SUMMARY,
                priority=InsightPriority.MEDIUM,
                title="Total Records",
                description=f"Dataset contains {len(data):,} records",
                value=float(len(data)),
            )
        )

        # Numeric column insights
        numeric_cols = data.select_dtypes(include=[np.number]).columns

        for col in numeric_cols[:5]:  # Top 5 numeric columns
            values = data[col].dropna()
            if len(values) == 0:
                continue

            total = values.sum()
            mean = values.mean()

            insights.append(
                Insight(
                    id=self._generate_id(f"summary_{col}"),
                    insight_type=InsightType.SUMMARY,
                    priority=InsightPriority.LOW,
                    title=f"{col.replace('_', ' ').title()} Summary",
                    description=f"Total: {total:,.2f}, Average: {mean:,.2f}",
                    value=float(total),
                    metadata={"column": col, "mean": float(mean), "count": len(values)},
                )
            )

        # Time-based insights
        if date_column and date_column in data.columns:
            df = data.copy()
            df[date_column] = pd.to_datetime(df[date_column], errors="coerce")
            df = df.dropna(subset=[date_column])

            if len(df) > 0:
                # Latest data
                latest = df[date_column].max()
                earliest = df[date_column].min()

                insights.append(
                    Insight(
                        id=self._generate_id("timespan"),
                        insight_type=InsightType.SUMMARY,
                        priority=InsightPriority.MEDIUM,
                        title="Data Timespan",
                        description=f"Data spans from {earliest.strftime('%b %d, %Y')} to {latest.strftime('%b %d, %Y')}",
                        metadata={
                            "earliest": earliest.isoformat(),
                            "latest": latest.isoformat(),
                        },
                    )
                )

                # Period comparison
                if compare_period and len(df) >= 14:
                    midpoint = earliest + (latest - earliest) / 2
                    first_half = df[df[date_column] < midpoint]
                    second_half = df[df[date_column] >= midpoint]

                    first_count = len(first_half)
                    second_count = len(second_half)

                    if first_count > 0:
                        change_pct = ((second_count - first_count) / first_count) * 100

                        if abs(change_pct) > 10:
                            direction = "increased" if change_pct > 0 else "decreased"
                            insights.append(
                                Insight(
                                    id=self._generate_id("period_comparison"),
                                    insight_type=InsightType.COMPARISON,
                                    priority=InsightPriority.HIGH,
                                    title="Period Comparison",
                                    description=f"Record volume {direction} by {abs(change_pct):.1f}% in the second half of the period",
                                    value=float(second_count),
                                    comparison_value=float(first_count),
                                    change_pct=round(change_pct, 2),
                                )
                            )

        # Distribution insights
        for col in numeric_cols[:3]:
            dist = self.distribution_analysis(data, col)

            if dist.outlier_count > 0 and dist.count > 0:
                outlier_pct = (dist.outlier_count / dist.count) * 100

                if outlier_pct > 5:
                    insights.append(
                        Insight(
                            id=self._generate_id(f"outliers_{col}"),
                            insight_type=InsightType.ANOMALY,
                            priority=InsightPriority.HIGH,
                            title=f"Outliers in {col.replace('_', ' ').title()}",
                            description=f"{dist.outlier_count:,} outliers detected ({outlier_pct:.1f}% of records)",
                            value=float(dist.outlier_count),
                            metadata={"column": col, "percentage": outlier_pct},
                        )
                    )

        # Correlation insights
        if len(numeric_cols) >= 2:
            corr = self.correlation_analysis(data, list(numeric_cols))

            for pair in corr.significant_pairs[:3]:
                if abs(pair["correlation"]) > 0.5:
                    insights.append(
                        Insight(
                            id=self._generate_id(
                                f"corr_{pair['column1']}_{pair['column2']}"
                            ),
                            insight_type=InsightType.CORRELATION,
                            priority=InsightPriority.MEDIUM,
                            title=f"{pair['strength'].title()} {pair['relationship']} correlation found",
                            description=f"{pair['column1']} and {pair['column2']} show {pair['relationship']} correlation (r={pair['correlation']:.2f})",
                            value=pair["correlation"],
                            metadata=pair,
                        )
                    )

        # Sort by priority
        priority_order = {
            InsightPriority.HIGH: 0,
            InsightPriority.MEDIUM: 1,
            InsightPriority.LOW: 2,
        }
        insights.sort(key=lambda x: priority_order.get(x.priority, 2))

        return insights[:15]  # Top 15 insights

    def get_quick_stats(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get quick summary statistics.

        Args:
            data: DataFrame to summarize

        Returns:
            Dictionary with quick stats
        """
        numeric_cols = data.select_dtypes(include=[np.number])

        stats = {
            "total_records": len(data),
            "total_columns": len(data.columns),
            "numeric_columns": len(numeric_cols.columns),
            "categorical_columns": len(
                data.select_dtypes(include=["object", "category"]).columns
            ),
            "null_values": int(data.isnull().sum().sum()),
            "null_percentage": (
                round((data.isnull().sum().sum() / data.size) * 100, 2)
                if data.size > 0
                else 0
            ),
        }

        # Add numeric column stats
        if not numeric_cols.empty:
            stats["numeric_summary"] = {}
            for col in numeric_cols.columns[:5]:
                stats["numeric_summary"][col] = {
                    "mean": float(numeric_cols[col].mean()),
                    "std": float(numeric_cols[col].std()),
                    "min": float(numeric_cols[col].min()),
                    "max": float(numeric_cols[col].max()),
                }

        return stats

    def _moving_average(self, values: np.ndarray, window: int) -> np.ndarray:
        """Calculate moving average with edge handling."""
        result = np.full(len(values), np.nan)

        for i in range(len(values)):
            start = max(0, i - window // 2)
            end = min(len(values), i + window // 2 + 1)
            result[i] = np.mean(values[start:end])

        return result

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID."""
        timestamp = datetime.utcnow().isoformat()
        hash_input = f"{prefix}_{timestamp}"
        return hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()[:12]


# Create default engine instance
_default_engine: Optional[AnalyticsEngine] = None


def get_analytics_engine() -> AnalyticsEngine:
    """Get or create the default analytics engine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = AnalyticsEngine()
    return _default_engine
