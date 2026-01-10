"""
Tests for Data Quality Dashboard

Comprehensive tests for coverage tracking, quality scoring,
error logging, and quota management.
"""

import pytest
from datetime import datetime, timedelta
from datagod.monitoring.data_quality_dashboard import (
    DataQualityDashboard,
    CoverageMetrics,
    QualityScore,
    QualityGrade,
    FreshnessStatus,
    ErrorLogEntry,
    QuotaStatus,
    get_dashboard,
    update_coverage,
    log_data_error,
    get_dashboard_summary,
)


class TestFreshnessStatusEnum:
    """Tests for FreshnessStatus enum"""

    def test_all_statuses_exist(self):
        """Test all freshness statuses exist"""
        assert FreshnessStatus.FRESH
        assert FreshnessStatus.RECENT
        assert FreshnessStatus.STALE
        assert FreshnessStatus.OUTDATED
        assert FreshnessStatus.UNKNOWN

    def test_status_values(self):
        """Test status values are correct"""
        assert FreshnessStatus.FRESH.value == "fresh"
        assert FreshnessStatus.RECENT.value == "recent"
        assert FreshnessStatus.STALE.value == "stale"
        assert FreshnessStatus.OUTDATED.value == "outdated"
        assert FreshnessStatus.UNKNOWN.value == "unknown"


class TestQualityGradeEnum:
    """Tests for QualityGrade enum"""

    def test_all_grades_exist(self):
        """Test all quality grades exist"""
        assert QualityGrade.A
        assert QualityGrade.B
        assert QualityGrade.C
        assert QualityGrade.D
        assert QualityGrade.F

    def test_grade_values(self):
        """Test grade values are correct"""
        assert QualityGrade.A.value == "A"
        assert QualityGrade.B.value == "B"
        assert QualityGrade.C.value == "C"
        assert QualityGrade.D.value == "D"
        assert QualityGrade.F.value == "F"


class TestCoverageMetrics:
    """Tests for CoverageMetrics dataclass"""

    def test_create_metrics(self):
        """Test creating coverage metrics"""
        metrics = CoverageMetrics(
            jurisdiction_id="CA",
            jurisdiction_name="California",
            total_records=1000,
            property_records=500,
            deed_records=300,
        )
        assert metrics.jurisdiction_id == "CA"
        assert metrics.jurisdiction_name == "California"
        assert metrics.total_records == 1000
        assert metrics.property_records == 500
        assert metrics.deed_records == 300

    def test_freshness_fresh(self):
        """Test fresh status (updated recently)"""
        metrics = CoverageMetrics(
            jurisdiction_id="CA",
            jurisdiction_name="California",
            last_updated=datetime.now() - timedelta(hours=1),
        )
        assert metrics.freshness_status == FreshnessStatus.FRESH

    def test_freshness_recent(self):
        """Test recent status (updated within 7 days)"""
        metrics = CoverageMetrics(
            jurisdiction_id="CA",
            jurisdiction_name="California",
            last_updated=datetime.now() - timedelta(days=3),
        )
        assert metrics.freshness_status == FreshnessStatus.RECENT

    def test_freshness_stale(self):
        """Test stale status (updated within 30 days)"""
        metrics = CoverageMetrics(
            jurisdiction_id="CA",
            jurisdiction_name="California",
            last_updated=datetime.now() - timedelta(days=15),
        )
        assert metrics.freshness_status == FreshnessStatus.STALE

    def test_freshness_outdated(self):
        """Test outdated status (not updated in 30+ days)"""
        metrics = CoverageMetrics(
            jurisdiction_id="CA",
            jurisdiction_name="California",
            last_updated=datetime.now() - timedelta(days=45),
        )
        assert metrics.freshness_status == FreshnessStatus.OUTDATED

    def test_freshness_unknown(self):
        """Test unknown status (no update timestamp)"""
        metrics = CoverageMetrics(
            jurisdiction_id="CA",
            jurisdiction_name="California",
        )
        assert metrics.freshness_status == FreshnessStatus.UNKNOWN

    def test_to_dict(self):
        """Test conversion to dictionary"""
        metrics = CoverageMetrics(
            jurisdiction_id="CA",
            jurisdiction_name="California",
            total_records=1000,
            property_records=500,
            coverage_percent=60.0,
            last_updated=datetime.now(),
        )
        result = metrics.to_dict()
        assert result['jurisdiction_id'] == "CA"
        assert result['jurisdiction_name'] == "California"
        assert result['total_records'] == 1000
        assert result['coverage_percent'] == 60.0
        assert 'freshness_status' in result


class TestQualityScore:
    """Tests for QualityScore dataclass"""

    def test_create_score(self):
        """Test creating quality score"""
        score = QualityScore(
            completeness=90.0,
            accuracy=85.0,
            consistency=80.0,
            timeliness=75.0,
            uniqueness=95.0,
        )
        assert score.completeness == 90.0
        assert score.accuracy == 85.0
        assert score.consistency == 80.0
        assert score.timeliness == 75.0
        assert score.uniqueness == 95.0

    def test_overall_score_calculation(self):
        """Test overall score calculation with weights"""
        score = QualityScore(
            completeness=100.0,  # 25% weight
            accuracy=100.0,     # 30% weight
            consistency=100.0,  # 20% weight
            timeliness=100.0,   # 15% weight
            uniqueness=100.0,   # 10% weight
        )
        assert score.overall_score == 100.0

    def test_overall_score_partial(self):
        """Test overall score with partial values"""
        score = QualityScore(
            completeness=80.0,
            accuracy=80.0,
            consistency=80.0,
            timeliness=80.0,
            uniqueness=80.0,
        )
        assert score.overall_score == 80.0

    def test_grade_a(self):
        """Test grade A (90-100)"""
        score = QualityScore(
            completeness=95.0,
            accuracy=95.0,
            consistency=95.0,
            timeliness=95.0,
            uniqueness=95.0,
        )
        assert score.grade == QualityGrade.A

    def test_grade_b(self):
        """Test grade B (80-89)"""
        score = QualityScore(
            completeness=85.0,
            accuracy=85.0,
            consistency=85.0,
            timeliness=85.0,
            uniqueness=85.0,
        )
        assert score.grade == QualityGrade.B

    def test_grade_c(self):
        """Test grade C (70-79)"""
        score = QualityScore(
            completeness=75.0,
            accuracy=75.0,
            consistency=75.0,
            timeliness=75.0,
            uniqueness=75.0,
        )
        assert score.grade == QualityGrade.C

    def test_grade_d(self):
        """Test grade D (60-69)"""
        score = QualityScore(
            completeness=65.0,
            accuracy=65.0,
            consistency=65.0,
            timeliness=65.0,
            uniqueness=65.0,
        )
        assert score.grade == QualityGrade.D

    def test_grade_f(self):
        """Test grade F (below 60)"""
        score = QualityScore(
            completeness=50.0,
            accuracy=50.0,
            consistency=50.0,
            timeliness=50.0,
            uniqueness=50.0,
        )
        assert score.grade == QualityGrade.F

    def test_to_dict(self):
        """Test conversion to dictionary"""
        score = QualityScore(
            completeness=90.0,
            accuracy=85.0,
            consistency=80.0,
            timeliness=75.0,
            uniqueness=95.0,
        )
        result = score.to_dict()
        assert result['completeness'] == 90.0
        assert result['accuracy'] == 85.0
        assert 'overall_score' in result
        assert 'grade' in result


class TestErrorLogEntry:
    """Tests for ErrorLogEntry dataclass"""

    def test_create_entry(self):
        """Test creating error log entry"""
        entry = ErrorLogEntry(
            timestamp=datetime.now(),
            source="california_api",
            error_type="connection",
            message="Connection refused",
        )
        assert entry.source == "california_api"
        assert entry.error_type == "connection"
        assert entry.message == "Connection refused"
        assert entry.resolved is False

    def test_with_optional_fields(self):
        """Test entry with optional fields"""
        entry = ErrorLogEntry(
            timestamp=datetime.now(),
            source="texas_api",
            error_type="parse",
            message="Invalid JSON",
            jurisdiction="TX",
            record_id="TX-001",
            stack_trace="Traceback...",
        )
        assert entry.jurisdiction == "TX"
        assert entry.record_id == "TX-001"
        assert entry.stack_trace == "Traceback..."

    def test_to_dict(self):
        """Test conversion to dictionary"""
        entry = ErrorLogEntry(
            timestamp=datetime.now(),
            source="api",
            error_type="timeout",
            message="Request timed out",
        )
        result = entry.to_dict()
        assert result['source'] == "api"
        assert result['error_type'] == "timeout"
        assert result['resolved'] is False


class TestQuotaStatus:
    """Tests for QuotaStatus dataclass"""

    def test_create_status(self):
        """Test creating quota status"""
        status = QuotaStatus(
            api_name="CoreLogic",
            used=500,
            limit=1000,
        )
        assert status.api_name == "CoreLogic"
        assert status.used == 500
        assert status.limit == 1000

    def test_usage_percent(self):
        """Test usage percentage calculation"""
        status = QuotaStatus(api_name="API", used=750, limit=1000)
        assert status.usage_percent == 75.0

    def test_usage_percent_zero_limit(self):
        """Test usage percentage with zero limit"""
        status = QuotaStatus(api_name="API", used=100, limit=0)
        assert status.usage_percent == 0.0

    def test_remaining(self):
        """Test remaining quota calculation"""
        status = QuotaStatus(api_name="API", used=300, limit=1000)
        assert status.remaining == 700

    def test_remaining_exceeded(self):
        """Test remaining when exceeded"""
        status = QuotaStatus(api_name="API", used=1200, limit=1000)
        assert status.remaining == 0

    def test_is_critical(self):
        """Test critical threshold (>90%)"""
        status = QuotaStatus(api_name="API", used=950, limit=1000)
        assert status.is_critical is True

        status2 = QuotaStatus(api_name="API", used=850, limit=1000)
        assert status2.is_critical is False

    def test_is_warning(self):
        """Test warning threshold (>75%)"""
        status = QuotaStatus(api_name="API", used=800, limit=1000)
        assert status.is_warning is True

        status2 = QuotaStatus(api_name="API", used=700, limit=1000)
        assert status2.is_warning is False

    def test_to_dict(self):
        """Test conversion to dictionary"""
        status = QuotaStatus(
            api_name="API",
            used=500,
            limit=1000,
            reset_at=datetime.now() + timedelta(hours=1),
        )
        result = status.to_dict()
        assert result['api_name'] == "API"
        assert result['used'] == 500
        assert result['remaining'] == 500
        assert result['usage_percent'] == 50.0


class TestDataQualityDashboard:
    """Tests for DataQualityDashboard class"""

    @pytest.fixture
    def dashboard(self):
        return DataQualityDashboard()

    # ===== Coverage Tests =====

    def test_dashboard_initialization(self, dashboard):
        """Test dashboard initialization"""
        assert dashboard._coverage == {}
        assert dashboard._quality_scores == {}
        assert dashboard._error_logs == []
        assert dashboard._quota_status == {}

    def test_all_states_list(self, dashboard):
        """Test all states list includes all US states and territories"""
        assert len(dashboard.ALL_STATES) == 56  # 50 states + DC + 5 territories
        assert 'CA' in dashboard.ALL_STATES
        assert 'TX' in dashboard.ALL_STATES
        assert 'DC' in dashboard.ALL_STATES
        assert 'PR' in dashboard.ALL_STATES

    def test_update_coverage(self, dashboard):
        """Test updating coverage metrics"""
        dashboard.update_coverage(
            jurisdiction_id="CA",
            jurisdiction_name="California",
            record_counts={
                'property': 1000,
                'deed': 500,
                'court': 300,
            },
        )

        metrics = dashboard.get_coverage("CA")
        assert metrics is not None
        assert metrics.jurisdiction_id == "CA"
        assert metrics.property_records == 1000
        assert metrics.deed_records == 500
        assert metrics.court_records == 300
        assert metrics.total_records == 1800

    def test_update_coverage_with_sources(self, dashboard):
        """Test updating coverage with data sources"""
        dashboard.update_coverage(
            jurisdiction_id="TX",
            jurisdiction_name="Texas",
            record_counts={'property': 500},
            data_sources=['county_api', 'state_portal'],
        )

        metrics = dashboard.get_coverage("TX")
        assert 'county_api' in metrics.data_sources
        assert 'state_portal' in metrics.data_sources

    def test_update_coverage_explicit_percent(self, dashboard):
        """Test coverage with explicit percentage"""
        dashboard.update_coverage(
            jurisdiction_id="FL",
            jurisdiction_name="Florida",
            record_counts={'property': 1000},
            coverage_percent=85.5,
        )

        metrics = dashboard.get_coverage("FL")
        assert metrics.coverage_percent == 85.5

    def test_coverage_auto_calculate(self, dashboard):
        """Test coverage auto-calculation"""
        dashboard.update_coverage(
            jurisdiction_id="NY",
            jurisdiction_name="New York",
            record_counts={
                'property': 100,
                'deed': 100,
                'court': 0,
                'business': 100,
                'license': 0,
            },
        )

        metrics = dashboard.get_coverage("NY")
        # 3 out of 5 categories have data = 60%
        assert metrics.coverage_percent == 60.0

    def test_get_all_coverage(self, dashboard):
        """Test getting all coverage metrics"""
        dashboard.update_coverage("CA", "California", {'property': 100})
        dashboard.update_coverage("TX", "Texas", {'property': 200})

        all_coverage = dashboard.get_all_coverage()
        assert len(all_coverage) == 2
        assert "CA" in all_coverage
        assert "TX" in all_coverage

    def test_get_state_coverage_summary(self, dashboard):
        """Test getting state coverage summary"""
        dashboard.update_coverage("CA", "California", {'property': 1000})
        dashboard.update_coverage("CA-LOS_ANGELES", "Los Angeles County",
                                 {'property': 500, 'deed': 200})

        summary = dashboard.get_state_coverage_summary()

        assert "CA" in summary
        assert summary["CA"]['has_coverage'] is True
        assert summary["CA"]['county_count'] == 2
        assert summary["CA"]['total_records'] == 1700

        # States without coverage
        assert summary["MT"]['has_coverage'] is False
        assert summary["MT"]['county_count'] == 0

    def test_get_coverage_heatmap_data(self, dashboard):
        """Test getting heatmap data"""
        dashboard.update_coverage("CA", "California",
                                 {'property': 100}, coverage_percent=80.0)
        dashboard.update_coverage("TX", "Texas",
                                 {'property': 100}, coverage_percent=60.0)

        heatmap = dashboard.get_coverage_heatmap_data()

        assert heatmap["CA"] == 80.0
        assert heatmap["TX"] == 60.0
        assert heatmap["WY"] == 0.0  # No coverage

    # ===== Quality Score Tests =====

    def test_update_quality_score(self, dashboard):
        """Test updating quality score"""
        dashboard.update_quality_score(
            dataset_id="property_data",
            completeness=90.0,
            accuracy=85.0,
        )

        score = dashboard.get_quality_score("property_data")
        assert score is not None
        assert score.completeness == 90.0
        assert score.accuracy == 85.0

    def test_update_quality_score_partial(self, dashboard):
        """Test partial quality score update"""
        dashboard.update_quality_score("data1", completeness=80.0)
        dashboard.update_quality_score("data1", accuracy=75.0)

        score = dashboard.get_quality_score("data1")
        assert score.completeness == 80.0
        assert score.accuracy == 75.0

    def test_get_all_quality_scores(self, dashboard):
        """Test getting all quality scores"""
        dashboard.update_quality_score("data1", completeness=90.0)
        dashboard.update_quality_score("data2", completeness=80.0)

        scores = dashboard.get_all_quality_scores()
        assert len(scores) == 2

    def test_get_quality_summary(self, dashboard):
        """Test getting quality summary"""
        dashboard.update_quality_score("data1", completeness=95.0, accuracy=95.0,
                                       consistency=95.0, timeliness=95.0, uniqueness=95.0)
        dashboard.update_quality_score("data2", completeness=50.0, accuracy=50.0,
                                       consistency=50.0, timeliness=50.0, uniqueness=50.0)

        summary = dashboard.get_quality_summary()

        assert summary['dataset_count'] == 2
        assert len(summary['lowest_scoring']) > 0
        assert len(summary['highest_scoring']) > 0
        assert 'grade_distribution' in summary

    def test_get_quality_summary_empty(self, dashboard):
        """Test quality summary with no data"""
        summary = dashboard.get_quality_summary()
        assert summary['dataset_count'] == 0
        assert summary['avg_score'] == 0.0

    # ===== Error Logging Tests =====

    def test_log_error(self, dashboard):
        """Test logging an error"""
        dashboard.log_error(
            source="california_api",
            error_type="connection",
            message="Connection refused",
        )

        errors = dashboard.get_errors()
        assert len(errors) == 1
        assert errors[0].source == "california_api"

    def test_log_error_with_details(self, dashboard):
        """Test logging error with details"""
        dashboard.log_error(
            source="api",
            error_type="parse",
            message="Invalid JSON",
            jurisdiction="TX",
            record_id="TX-001",
            stack_trace="Traceback...",
        )

        errors = dashboard.get_errors()
        assert errors[0].jurisdiction == "TX"
        assert errors[0].record_id == "TX-001"
        assert errors[0].stack_trace == "Traceback..."

    def test_get_errors_filter_by_source(self, dashboard):
        """Test filtering errors by source"""
        dashboard.log_error("api1", "error", "msg1")
        dashboard.log_error("api2", "error", "msg2")
        dashboard.log_error("api1", "error", "msg3")

        errors = dashboard.get_errors(source="api1")
        assert len(errors) == 2

    def test_get_errors_filter_by_type(self, dashboard):
        """Test filtering errors by type"""
        dashboard.log_error("api", "timeout", "timed out")
        dashboard.log_error("api", "connection", "refused")

        errors = dashboard.get_errors(error_type="timeout")
        assert len(errors) == 1
        assert errors[0].error_type == "timeout"

    def test_get_errors_filter_by_jurisdiction(self, dashboard):
        """Test filtering errors by jurisdiction"""
        dashboard.log_error("api", "error", "msg", jurisdiction="CA")
        dashboard.log_error("api", "error", "msg", jurisdiction="TX")

        errors = dashboard.get_errors(jurisdiction="CA")
        assert len(errors) == 1
        assert errors[0].jurisdiction == "CA"

    def test_get_errors_filter_by_time(self, dashboard):
        """Test filtering errors by time"""
        dashboard.log_error("api", "error", "old")
        # Simulate old error by modifying timestamp
        dashboard._error_logs[0].timestamp = datetime.now() - timedelta(days=2)

        dashboard.log_error("api", "error", "new")

        since = datetime.now() - timedelta(days=1)
        errors = dashboard.get_errors(since=since)
        assert len(errors) == 1
        assert errors[0].message == "new"

    def test_get_errors_include_resolved(self, dashboard):
        """Test including resolved errors"""
        dashboard.log_error("api", "error", "msg1")
        dashboard.log_error("api", "error", "msg2")
        dashboard._error_logs[0].resolved = True

        unresolved = dashboard.get_errors(include_resolved=False)
        assert len(unresolved) == 1

        all_errors = dashboard.get_errors(include_resolved=True)
        assert len(all_errors) == 2

    def test_get_errors_limit(self, dashboard):
        """Test error limit"""
        for i in range(20):
            dashboard.log_error("api", "error", f"msg{i}")

        errors = dashboard.get_errors(limit=5)
        assert len(errors) == 5

    def test_resolve_error(self, dashboard):
        """Test resolving an error"""
        dashboard.log_error("api", "error", "msg")
        assert dashboard._error_logs[0].resolved is False

        dashboard.resolve_error(0)
        assert dashboard._error_logs[0].resolved is True

    def test_get_error_summary(self, dashboard):
        """Test getting error summary"""
        dashboard.log_error("api1", "timeout", "msg1", jurisdiction="CA")
        dashboard.log_error("api1", "connection", "msg2", jurisdiction="TX")
        dashboard.log_error("api2", "timeout", "msg3", jurisdiction="CA")

        summary = dashboard.get_error_summary()

        assert summary['total_errors'] == 3
        assert summary['unresolved_count'] == 3
        assert summary['by_source']['api1'] == 2
        assert summary['by_type']['timeout'] == 2
        assert summary['by_jurisdiction']['CA'] == 2

    def test_cleanup_old_errors(self, dashboard):
        """Test cleaning up old errors"""
        dashboard.log_error("api", "error", "old")
        dashboard._error_logs[0].timestamp = datetime.now() - timedelta(hours=200)

        dashboard.log_error("api", "error", "new")

        dashboard.cleanup_old_errors()
        assert len(dashboard._error_logs) == 1
        assert dashboard._error_logs[0].message == "new"

    # ===== Quota Tests =====

    def test_update_quota(self, dashboard):
        """Test updating quota"""
        dashboard.update_quota("CoreLogic", used=500, limit=1000)

        quota = dashboard.get_quota("CoreLogic")
        assert quota is not None
        assert quota.used == 500
        assert quota.limit == 1000

    def test_update_quota_with_reset(self, dashboard):
        """Test quota with reset time"""
        reset = datetime.now() + timedelta(hours=1)
        dashboard.update_quota("API", used=100, limit=1000, reset_at=reset)

        quota = dashboard.get_quota("API")
        assert quota.reset_at == reset

    def test_get_all_quotas(self, dashboard):
        """Test getting all quotas"""
        dashboard.update_quota("API1", used=100, limit=1000)
        dashboard.update_quota("API2", used=200, limit=500)

        quotas = dashboard.get_all_quotas()
        assert len(quotas) == 2

    def test_get_quota_summary(self, dashboard):
        """Test getting quota summary"""
        dashboard.update_quota("Critical", used=950, limit=1000)  # Critical
        dashboard.update_quota("Warning", used=800, limit=1000)   # Warning
        dashboard.update_quota("Normal", used=500, limit=1000)    # Normal

        summary = dashboard.get_quota_summary()

        assert summary['api_count'] == 3
        assert summary['critical_count'] == 1
        assert summary['warning_count'] == 1
        assert "Critical" in summary['critical_apis']
        assert "Warning" in summary['warning_apis']

    def test_get_quota_summary_empty(self, dashboard):
        """Test quota summary with no data"""
        summary = dashboard.get_quota_summary()
        assert summary['api_count'] == 0

    # ===== Dashboard Export Tests =====

    def test_get_dashboard_data(self, dashboard):
        """Test getting complete dashboard data"""
        dashboard.update_coverage("CA", "California", {'property': 1000})
        dashboard.update_quality_score("data1", completeness=90.0)
        dashboard.log_error("api", "error", "msg")
        dashboard.update_quota("API", used=500, limit=1000)

        data = dashboard.get_dashboard_data()

        assert 'timestamp' in data
        assert 'overview' in data
        assert 'coverage' in data
        assert 'quality' in data
        assert 'errors' in data
        assert 'quotas' in data

    def test_dashboard_overview(self, dashboard):
        """Test dashboard overview"""
        dashboard.update_coverage("CA", "California", {'property': 1000})
        dashboard.update_coverage("TX", "Texas", {'property': 500})

        data = dashboard.get_dashboard_data()
        overview = data['overview']

        assert overview['states_covered'] == 2
        assert overview['total_states'] == 56
        assert overview['total_records'] == 1500
        assert overview['jurisdictions_tracked'] == 2

    def test_export_to_json(self, dashboard, tmp_path):
        """Test exporting to JSON"""
        dashboard.update_coverage("CA", "California", {'property': 1000})

        json_str = dashboard.export_to_json()
        assert '"CA"' in json_str
        assert '"has_coverage": true' in json_str
        assert '"total_records": 1000' in json_str

    def test_export_to_json_file(self, dashboard, tmp_path):
        """Test exporting to JSON file"""
        dashboard.update_coverage("CA", "California", {'property': 1000})

        filepath = tmp_path / "dashboard.json"
        dashboard.export_to_json(str(filepath))

        assert filepath.exists()
        content = filepath.read_text()
        assert '"CA"' in content

    def test_reset(self, dashboard):
        """Test resetting dashboard"""
        dashboard.update_coverage("CA", "California", {'property': 1000})
        dashboard.update_quality_score("data1", completeness=90.0)
        dashboard.log_error("api", "error", "msg")
        dashboard.update_quota("API", used=500, limit=1000)

        dashboard.reset()

        assert dashboard._coverage == {}
        assert dashboard._quality_scores == {}
        assert dashboard._error_logs == []
        assert dashboard._quota_status == {}


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_get_dashboard(self):
        """Test getting singleton dashboard"""
        dashboard1 = get_dashboard()
        dashboard2 = get_dashboard()
        assert dashboard1 is dashboard2

    def test_update_coverage_func(self):
        """Test update_coverage convenience function"""
        dashboard = get_dashboard()
        dashboard.reset()

        update_coverage("CA", "California", {'property': 100})

        metrics = dashboard.get_coverage("CA")
        assert metrics is not None
        assert metrics.property_records == 100

    def test_log_data_error_func(self):
        """Test log_data_error convenience function"""
        dashboard = get_dashboard()
        dashboard.reset()

        log_data_error("api", "timeout", "timed out")

        errors = dashboard.get_errors()
        assert len(errors) == 1
        assert errors[0].error_type == "timeout"

    def test_get_dashboard_summary_func(self):
        """Test get_dashboard_summary convenience function"""
        dashboard = get_dashboard()
        dashboard.reset()
        dashboard.update_coverage("CA", "California", {'property': 100})

        summary = get_dashboard_summary()

        assert 'overview' in summary
        assert summary['overview']['jurisdictions_tracked'] == 1


class TestHistoricalTracking:
    """Tests for historical data tracking"""

    @pytest.fixture
    def dashboard(self):
        return DataQualityDashboard()

    def test_coverage_history_recorded(self, dashboard):
        """Test that coverage history is recorded"""
        dashboard.update_coverage("CA", "California",
                                 {'property': 100}, coverage_percent=50.0)
        dashboard.update_coverage("CA", "California",
                                 {'property': 200}, coverage_percent=60.0)

        history = dashboard._historical_coverage["CA"]
        assert len(history) == 2
        assert history[0][1] == 50.0
        assert history[1][1] == 60.0

    def test_coverage_history_timestamps(self, dashboard):
        """Test coverage history has timestamps"""
        dashboard.update_coverage("TX", "Texas", {'property': 100})

        history = dashboard._historical_coverage["TX"]
        assert len(history) == 1
        timestamp, coverage = history[0]
        assert isinstance(timestamp, datetime)
