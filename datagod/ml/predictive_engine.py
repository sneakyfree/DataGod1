"""
DataGod Predictive Analytics Engine

Time series forecasting, pattern detection, and predictive modeling
for public records data trends.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ForecastMethod(str, Enum):
    """Available forecasting methods."""
    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    LINEAR_REGRESSION = "linear_regression"
    ARIMA = "arima"
    PROPHET = "prophet"
    AUTO = "auto"


class PatternType(str, Enum):
    """Types of patterns that can be detected."""
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    SEASONAL = "seasonal"
    CYCLICAL = "cyclical"
    SPIKE = "spike"
    DIP = "dip"
    PLATEAU = "plateau"
    ANOMALOUS = "anomalous"


class Confidence(str, Enum):
    """Confidence levels for predictions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Forecast:
    """Represents a forecast result."""
    start_date: datetime
    end_date: datetime
    horizon_days: int
    method: ForecastMethod
    predictions: List[Dict[str, Any]]
    confidence: Confidence
    metrics: Dict[str, float]
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "horizon_days": self.horizon_days,
            "method": self.method.value,
            "predictions": self.predictions,
            "confidence": self.confidence.value,
            "metrics": self.metrics,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class Pattern:
    """Represents a detected pattern."""
    pattern_type: PatternType
    description: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    significance: float  # 0-1
    data_points: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_type": self.pattern_type.value,
            "description": self.description,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "significance": self.significance,
            "data_points": self.data_points,
            "metadata": self.metadata,
        }


@dataclass
class GapPrediction:
    """Prediction of where data gaps will occur."""
    jurisdiction_id: Optional[int]
    jurisdiction_name: str
    state: str
    predicted_gap_date: datetime
    probability: float
    reason: str
    recommended_action: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "jurisdiction_id": self.jurisdiction_id,
            "jurisdiction_name": self.jurisdiction_name,
            "state": self.state,
            "predicted_gap_date": self.predicted_gap_date.isoformat(),
            "probability": self.probability,
            "reason": self.reason,
            "recommended_action": self.recommended_action,
        }


@dataclass
class PredictiveConfig:
    """Configuration for predictive analytics."""
    default_horizon_days: int = 30
    min_history_days: int = 14
    confidence_threshold: float = 0.8
    seasonality_period: int = 7  # Weekly
    trend_window: int = 14
    spike_threshold: float = 2.0  # Standard deviations


class PredictiveEngine:
    """
    Time series forecasting and pattern recognition engine.
    
    Provides forecasting, pattern detection, and gap prediction
    capabilities for public records data.
    """
    
    def __init__(self, config: Optional[PredictiveConfig] = None):
        """Initialize the predictive engine."""
        self.config = config or PredictiveConfig()
        self._forecast_cache: Dict[str, Forecast] = {}
        logger.info("PredictiveEngine initialized")
    
    def forecast_volume(
        self,
        data: pd.DataFrame,
        date_column: str = "date",
        value_column: str = "count",
        horizon_days: int = None,
        method: ForecastMethod = ForecastMethod.AUTO
    ) -> Forecast:
        """
        Predict record volume trends.
        
        Args:
            data: DataFrame with time series data
            date_column: Name of the date column
            value_column: Name of the value column to forecast
            horizon_days: Days to forecast ahead
            method: Forecasting method to use
            
        Returns:
            Forecast object with predictions
        """
        horizon = horizon_days or self.config.default_horizon_days
        
        if len(data) < self.config.min_history_days:
            logger.warning("Insufficient data for forecasting: %d days", len(data))
            return self._empty_forecast(horizon, method)
        
        try:
            # Prepare data
            df = data.copy()
            df[date_column] = pd.to_datetime(df[date_column])
            df = df.sort_values(date_column)
            
            # Select forecasting method
            if method == ForecastMethod.AUTO:
                method = self._select_best_method(df, value_column)
            
            # Run forecast
            if method == ForecastMethod.MOVING_AVERAGE:
                predictions, metrics = self._forecast_moving_average(df, date_column, value_column, horizon)
            elif method == ForecastMethod.EXPONENTIAL_SMOOTHING:
                predictions, metrics = self._forecast_exponential_smoothing(df, date_column, value_column, horizon)
            elif method == ForecastMethod.LINEAR_REGRESSION:
                predictions, metrics = self._forecast_linear_regression(df, date_column, value_column, horizon)
            elif method == ForecastMethod.ARIMA:
                predictions, metrics = self._forecast_arima(df, date_column, value_column, horizon)
            else:
                predictions, metrics = self._forecast_moving_average(df, date_column, value_column, horizon)
            
            # Calculate confidence
            confidence = self._calculate_confidence(metrics)
            
            forecast = Forecast(
                start_date=df[date_column].max(),
                end_date=df[date_column].max() + timedelta(days=horizon),
                horizon_days=horizon,
                method=method,
                predictions=predictions,
                confidence=confidence,
                metrics=metrics,
            )
            
            # Cache the forecast
            cache_key = self._generate_cache_key(data, method, horizon)
            self._forecast_cache[cache_key] = forecast
            
            return forecast
            
        except Exception as e:
            logger.error("Forecasting failed: %s", e)
            return self._empty_forecast(horizon, method)
    
    def detect_patterns(self, data: pd.DataFrame, date_column: str = "date", value_column: str = "count") -> List[Pattern]:
        """
        Identify recurring patterns in the data.
        
        Args:
            data: DataFrame with time series data
            date_column: Name of the date column
            value_column: Name of the value column
            
        Returns:
            List of detected patterns
        """
        patterns: List[Pattern] = []
        
        if len(data) < self.config.min_history_days:
            return patterns
        
        try:
            df = data.copy()
            df[date_column] = pd.to_datetime(df[date_column])
            df = df.sort_values(date_column)
            values = df[value_column].values
            
            # Detect trend
            trend_pattern = self._detect_trend(df, date_column, value_column)
            if trend_pattern:
                patterns.append(trend_pattern)
            
            # Detect seasonality
            seasonal_pattern = self._detect_seasonality(df, date_column, value_column)
            if seasonal_pattern:
                patterns.append(seasonal_pattern)
            
            # Detect spikes
            spike_patterns = self._detect_spikes(df, date_column, value_column)
            patterns.extend(spike_patterns)
            
            # Detect plateaus
            plateau_pattern = self._detect_plateau(df, date_column, value_column)
            if plateau_pattern:
                patterns.append(plateau_pattern)
            
            return patterns
            
        except Exception as e:
            logger.error("Pattern detection failed: %s", e)
            return patterns
    
    def predict_data_gaps(
        self,
        jurisdictions: List[Dict[str, Any]],
        historical_gaps: Optional[pd.DataFrame] = None
    ) -> List[GapPrediction]:
        """
        Predict where data gaps will occur.
        
        Args:
            jurisdictions: List of jurisdiction data
            historical_gaps: Optional historical gap data
            
        Returns:
            List of gap predictions
        """
        predictions: List[GapPrediction] = []
        
        for j in jurisdictions:
            # Calculate gap probability based on factors
            last_updated = j.get('last_updated')
            update_frequency = j.get('update_frequency_days', 7)
            reliability_score = j.get('reliability_score', 0.8)
            
            if last_updated:
                if isinstance(last_updated, str):
                    last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                
                days_since_update = (datetime.utcnow() - last_updated).days
                
                # Higher probability if overdue
                if days_since_update > update_frequency * 1.5:
                    probability = min(0.5 + (days_since_update - update_frequency) * 0.05, 0.95)
                    
                    prediction = GapPrediction(
                        jurisdiction_id=j.get('id'),
                        jurisdiction_name=j.get('name', 'Unknown'),
                        state=j.get('state', 'Unknown'),
                        predicted_gap_date=datetime.utcnow() + timedelta(days=7),
                        probability=probability,
                        reason=f"Last update was {days_since_update} days ago (expected every {update_frequency} days)",
                        recommended_action="Schedule immediate data refresh"
                    )
                    predictions.append(prediction)
            
            # Check reliability
            if reliability_score < 0.6:
                prediction = GapPrediction(
                    jurisdiction_id=j.get('id'),
                    jurisdiction_name=j.get('name', 'Unknown'),
                    state=j.get('state', 'Unknown'),
                    predicted_gap_date=datetime.utcnow() + timedelta(days=14),
                    probability=1 - reliability_score,
                    reason=f"Low reliability score: {reliability_score:.2f}",
                    recommended_action="Review data source and consider alternatives"
                )
                predictions.append(prediction)
        
        # Sort by probability
        predictions.sort(key=lambda x: -x.probability)
        
        return predictions
    
    def get_insights(self, data: pd.DataFrame, date_column: str = "date", value_column: str = "count") -> List[str]:
        """
        Generate natural language insights from the data.
        
        Args:
            data: DataFrame with time series data
            
        Returns:
            List of insight strings
        """
        insights: List[str] = []
        
        if len(data) < 7:
            return ["Insufficient data for analysis"]
        
        try:
            df = data.copy()
            df[date_column] = pd.to_datetime(df[date_column])
            df = df.sort_values(date_column)
            values = df[value_column].values
            
            # Total and average
            total = values.sum()
            avg = values.mean()
            insights.append(f"Total volume: {total:,.0f} records with a daily average of {avg:,.1f}")
            
            # Trend analysis
            if len(values) >= 14:
                first_half = values[:len(values)//2].mean()
                second_half = values[len(values)//2:].mean()
                change_pct = ((second_half - first_half) / first_half) * 100 if first_half > 0 else 0
                
                if abs(change_pct) > 10:
                    direction = "increased" if change_pct > 0 else "decreased"
                    insights.append(f"Volume has {direction} by {abs(change_pct):.1f}% over the analysis period")
            
            # Peak detection
            max_val = values.max()
            max_idx = values.argmax()
            max_date = df[date_column].iloc[max_idx]
            insights.append(f"Highest single-day volume of {max_val:,.0f} records occurred on {max_date.strftime('%B %d, %Y')}")
            
            # Variability
            std = values.std()
            cv = (std / avg) * 100 if avg > 0 else 0
            if cv > 50:
                insights.append(f"High variability detected (CV: {cv:.1f}%) - data collection may be inconsistent")
            elif cv < 20:
                insights.append(f"Volume is stable with low variability (CV: {cv:.1f}%)")
            
            # Recent trend
            if len(values) >= 7:
                recent_avg = values[-7:].mean()
                overall_avg = values.mean()
                recent_change = ((recent_avg - overall_avg) / overall_avg) * 100 if overall_avg > 0 else 0
                
                if abs(recent_change) > 15:
                    direction = "above" if recent_change > 0 else "below"
                    insights.append(f"Recent 7-day average is {abs(recent_change):.1f}% {direction} the overall average")
            
        except Exception as e:
            logger.error("Insight generation failed: %s", e)
            insights.append("Unable to generate insights from the provided data")
        
        return insights
    
    # Private methods
    
    def _forecast_moving_average(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        horizon: int
    ) -> Tuple[List[Dict], Dict[str, float]]:
        """Simple moving average forecast."""
        values = df[value_col].values
        window = min(7, len(values) // 2)
        
        # Calculate moving average
        ma = pd.Series(values).rolling(window=window).mean().iloc[-1]
        
        predictions = []
        last_date = df[date_col].max()
        
        for i in range(1, horizon + 1):
            pred_date = last_date + timedelta(days=i)
            # Add slight noise for realism
            noise = np.random.normal(0, ma * 0.05)
            predictions.append({
                "date": pred_date.isoformat(),
                "predicted_value": max(0, ma + noise),
                "lower_bound": max(0, ma * 0.85),
                "upper_bound": ma * 1.15,
            })
        
        # Calculate metrics
        metrics = {
            "mae": float(np.abs(values - ma).mean()),
            "mape": float(np.abs((values - ma) / values).mean() * 100) if values.mean() > 0 else 0,
            "window_size": window,
        }
        
        return predictions, metrics
    
    def _forecast_exponential_smoothing(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        horizon: int
    ) -> Tuple[List[Dict], Dict[str, float]]:
        """Exponential smoothing forecast."""
        values = df[value_col].values
        alpha = 0.3  # Smoothing factor
        
        # Calculate exponential weighted average
        smoothed = pd.Series(values).ewm(alpha=alpha, adjust=False).mean().iloc[-1]
        
        predictions = []
        last_date = df[date_col].max()
        
        for i in range(1, horizon + 1):
            pred_date = last_date + timedelta(days=i)
            predictions.append({
                "date": pred_date.isoformat(),
                "predicted_value": float(smoothed),
                "lower_bound": float(smoothed * 0.8),
                "upper_bound": float(smoothed * 1.2),
            })
        
        metrics = {
            "alpha": alpha,
            "mae": float(np.abs(values - smoothed).mean()),
        }
        
        return predictions, metrics
    
    def _forecast_linear_regression(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        horizon: int
    ) -> Tuple[List[Dict], Dict[str, float]]:
        """Linear regression forecast."""
        values = df[value_col].values
        x = np.arange(len(values))
        
        # Fit linear regression
        coeffs = np.polyfit(x, values, 1)
        slope, intercept = coeffs
        
        predictions = []
        last_date = df[date_col].max()
        
        for i in range(1, horizon + 1):
            pred_date = last_date + timedelta(days=i)
            pred_x = len(values) + i - 1
            pred_value = slope * pred_x + intercept
            std = values.std()
            
            predictions.append({
                "date": pred_date.isoformat(),
                "predicted_value": max(0, float(pred_value)),
                "lower_bound": max(0, float(pred_value - 1.96 * std)),
                "upper_bound": float(pred_value + 1.96 * std),
            })
        
        # Calculate R-squared
        y_pred = slope * x + intercept
        ss_res = np.sum((values - y_pred) ** 2)
        ss_tot = np.sum((values - values.mean()) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        metrics = {
            "slope": float(slope),
            "intercept": float(intercept),
            "r_squared": float(r_squared),
            "mae": float(np.abs(values - y_pred).mean()),
        }
        
        return predictions, metrics
    
    def _forecast_arima(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        horizon: int
    ) -> Tuple[List[Dict], Dict[str, float]]:
        """ARIMA forecast (simplified implementation)."""
        try:
            from statsmodels.tsa.arima.model import ARIMA as StatsARIMA
            
            values = df[value_col].values
            
            # Fit ARIMA(1,1,1)
            model = StatsARIMA(values, order=(1, 1, 1))
            fitted = model.fit()
            
            # Forecast
            forecast = fitted.forecast(steps=horizon)
            conf_int = fitted.get_forecast(steps=horizon).conf_int()
            
            predictions = []
            last_date = df[date_col].max()
            
            for i in range(horizon):
                pred_date = last_date + timedelta(days=i + 1)
                predictions.append({
                    "date": pred_date.isoformat(),
                    "predicted_value": max(0, float(forecast[i])),
                    "lower_bound": max(0, float(conf_int[i, 0])),
                    "upper_bound": float(conf_int[i, 1]),
                })
            
            metrics = {
                "aic": float(fitted.aic),
                "bic": float(fitted.bic),
            }
            
            return predictions, metrics
            
        except Exception as e:
            logger.warning("ARIMA failed, falling back to linear regression: %s", e)
            return self._forecast_linear_regression(df, date_col, value_col, horizon)
    
    def _detect_trend(self, df: pd.DataFrame, date_col: str, value_col: str) -> Optional[Pattern]:
        """Detect overall trend in the data."""
        values = df[value_col].values
        x = np.arange(len(values))
        
        coeffs = np.polyfit(x, values, 1)
        slope = coeffs[0]
        
        # Calculate trend strength
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((values - y_pred) ** 2)
        ss_tot = np.sum((values - values.mean()) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        if r_squared > 0.3:  # Significant trend
            if slope > 0:
                pattern_type = PatternType.TREND_UP
                description = f"Upward trend detected with {slope:.1f} increase per period"
            else:
                pattern_type = PatternType.TREND_DOWN
                description = f"Downward trend detected with {abs(slope):.1f} decrease per period"
            
            return Pattern(
                pattern_type=pattern_type,
                description=description,
                start_date=df[date_col].min(),
                end_date=df[date_col].max(),
                significance=r_squared,
                data_points=len(values),
                metadata={"slope": float(slope), "r_squared": float(r_squared)}
            )
        
        return None
    
    def _detect_seasonality(self, df: pd.DataFrame, date_col: str, value_col: str) -> Optional[Pattern]:
        """Detect seasonal patterns."""
        values = df[value_col].values
        
        if len(values) < 14:  # Need at least 2 weeks
            return None
        
        try:
            # Check for weekly seasonality using autocorrelation
            from scipy import stats as scipy_stats
            
            if len(values) >= 14:
                # Lag 7 correlation for weekly pattern
                lag7_corr = np.corrcoef(values[:-7], values[7:])[0, 1]
                
                if abs(lag7_corr) > 0.5:
                    return Pattern(
                        pattern_type=PatternType.SEASONAL,
                        description=f"Weekly seasonality detected (correlation: {lag7_corr:.2f})",
                        start_date=df[date_col].min(),
                        end_date=df[date_col].max(),
                        significance=abs(lag7_corr),
                        data_points=len(values),
                        metadata={"period": 7, "autocorrelation": float(lag7_corr)}
                    )
        except Exception:
            pass
        
        return None
    
    def _detect_spikes(self, df: pd.DataFrame, date_col: str, value_col: str) -> List[Pattern]:
        """Detect spikes and dips in the data."""
        patterns = []
        values = df[value_col].values
        mean = values.mean()
        std = values.std()
        
        if std == 0:
            return patterns
        
        z_scores = (values - mean) / std
        
        for i, z in enumerate(z_scores):
            if abs(z) > self.config.spike_threshold:
                date = df[date_col].iloc[i]
                pattern_type = PatternType.SPIKE if z > 0 else PatternType.DIP
                description = f"{'Spike' if z > 0 else 'Dip'} detected on {date.strftime('%Y-%m-%d')}"
                
                patterns.append(Pattern(
                    pattern_type=pattern_type,
                    description=description,
                    start_date=date,
                    end_date=date,
                    significance=min(abs(z) / 5, 1.0),
                    data_points=1,
                    metadata={"z_score": float(z), "value": float(values[i]), "mean": float(mean)}
                ))
        
        return patterns[:10]  # Limit to top 10
    
    def _detect_plateau(self, df: pd.DataFrame, date_col: str, value_col: str) -> Optional[Pattern]:
        """Detect plateau periods."""
        values = df[value_col].values
        
        if len(values) < 7:
            return None
        
        # Check if recent values are flat
        recent = values[-7:]
        cv = recent.std() / recent.mean() if recent.mean() > 0 else 0
        
        if cv < 0.1:  # Very stable
            return Pattern(
                pattern_type=PatternType.PLATEAU,
                description=f"Stable plateau detected in recent data (CV: {cv:.2f})",
                start_date=df[date_col].iloc[-7],
                end_date=df[date_col].iloc[-1],
                significance=1 - cv,
                data_points=7,
                metadata={"cv": float(cv), "mean": float(recent.mean())}
            )
        
        return None
    
    def _select_best_method(self, df: pd.DataFrame, value_col: str) -> ForecastMethod:
        """Select the best forecasting method based on data characteristics."""
        values = df[value_col].values
        
        # Check for trend
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((values - y_pred) ** 2)
        ss_tot = np.sum((values - values.mean()) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        if r_squared > 0.5:
            return ForecastMethod.LINEAR_REGRESSION
        
        # Check data length for ARIMA
        if len(values) >= 30:
            try:
                from statsmodels.tsa.arima.model import ARIMA
                return ForecastMethod.ARIMA
            except ImportError:
                pass
        
        # Default to exponential smoothing
        return ForecastMethod.EXPONENTIAL_SMOOTHING
    
    def _calculate_confidence(self, metrics: Dict[str, float]) -> Confidence:
        """Calculate confidence level from metrics."""
        r_squared = metrics.get('r_squared', 0)
        mape = metrics.get('mape', 100)
        
        if r_squared > 0.7 or mape < 10:
            return Confidence.HIGH
        elif r_squared > 0.4 or mape < 25:
            return Confidence.MEDIUM
        return Confidence.LOW
    
    def _empty_forecast(self, horizon: int, method: ForecastMethod) -> Forecast:
        """Return an empty forecast for insufficient data."""
        return Forecast(
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=horizon),
            horizon_days=horizon,
            method=method,
            predictions=[],
            confidence=Confidence.LOW,
            metrics={"error": "Insufficient data"}
        )
    
    def _generate_cache_key(self, data: pd.DataFrame, method: ForecastMethod, horizon: int) -> str:
        """Generate a cache key for the forecast."""
        data_hash = hashlib.md5(str(data.values.tobytes()).encode()).hexdigest()[:8]
        return f"{data_hash}_{method.value}_{horizon}"


# Create default engine instance
_default_engine: Optional[PredictiveEngine] = None


def get_predictive_engine() -> PredictiveEngine:
    """Get or create the default predictive engine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = PredictiveEngine()
    return _default_engine
