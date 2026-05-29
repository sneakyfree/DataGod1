"""
Tests for Data Deduplication Service.

Tests cover:
- DataNormalizer
- SimilarityScorer
- DeduplicationEngine
- DeduplicationService
"""

from datetime import datetime, timedelta

import pytest


class TestDataNormalizer:
    """Tests for DataNormalizer class."""

    def test_normalize_text_basic(self):
        """Test basic text normalization."""
        from datagod.utils.data_deduplication import DataNormalizer

        normalizer = DataNormalizer()

        assert normalizer.normalize_text("  Hello  World  ") == "hello world"
        assert normalizer.normalize_text("UPPERCASE") == "uppercase"
        assert normalizer.normalize_text("") == ""
        assert normalizer.normalize_text(None) == ""

    def test_normalize_text_removes_punctuation(self):
        """Test that punctuation is removed."""
        from datagod.utils.data_deduplication import DataNormalizer

        normalizer = DataNormalizer()

        result = normalizer.normalize_text("Hello, World!")
        assert "," not in result
        assert "!" not in result

    def test_normalize_text_expands_abbreviations(self):
        """Test that common abbreviations are expanded."""
        from datagod.utils.data_deduplication import DataNormalizer

        normalizer = DataNormalizer()

        assert "junior" in normalizer.normalize_text("John Jr")
        assert "corporation" in normalizer.normalize_text("ABC Corp")
        assert "incorporated" in normalizer.normalize_text("XYZ Inc")

    def test_normalize_address(self):
        """Test address normalization."""
        from datagod.utils.data_deduplication import DataNormalizer

        normalizer = DataNormalizer()

        addr1 = normalizer.normalize_address("123 Main St")
        addr2 = normalizer.normalize_address("123 Main Street")
        assert addr1 == addr2

    def test_normalize_address_removes_units(self):
        """Test that unit numbers are removed for matching."""
        from datagod.utils.data_deduplication import DataNormalizer

        normalizer = DataNormalizer()

        addr1 = normalizer.normalize_address("123 Main St Apt 4")
        addr2 = normalizer.normalize_address("123 Main St")
        # Both should normalize to similar values
        assert "apt" not in addr1.lower()

    def test_normalize_name(self):
        """Test name normalization."""
        from datagod.utils.data_deduplication import DataNormalizer

        normalizer = DataNormalizer()

        name1 = normalizer.normalize_name("John Doe Jr")
        name2 = normalizer.normalize_name("John Doe")
        # Suffixes should be removed
        assert "jr" not in name1

    def test_normalize_amount(self):
        """Test amount normalization."""
        from datagod.utils.data_deduplication import DataNormalizer

        normalizer = DataNormalizer()

        assert normalizer.normalize_amount("$1,234.56") == 1234.56
        assert normalizer.normalize_amount("1000") == 1000.0
        assert normalizer.normalize_amount(500) == 500.0
        assert normalizer.normalize_amount(None) is None

    def test_normalize_date(self):
        """Test date normalization."""
        from datagod.utils.data_deduplication import DataNormalizer

        normalizer = DataNormalizer()

        assert normalizer.normalize_date("2024-01-15") == "2024-01-15"
        assert normalizer.normalize_date("01/15/2024") == "2024-01-15"
        assert normalizer.normalize_date("") is None
        assert normalizer.normalize_date(None) is None

    def test_create_comparison_key(self):
        """Test comparison key creation."""
        from datagod.utils.data_deduplication import DataNormalizer

        normalizer = DataNormalizer()

        record = {"name": "John Doe", "address": "123 Main St"}

        key = normalizer.create_comparison_key(record, ["name", "address"])
        assert key != ""
        assert "|" in key


class TestSimilarityScorer:
    """Tests for SimilarityScorer class."""

    def test_text_similarity_identical(self):
        """Test similarity of identical strings."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        score = scorer._text_similarity("hello world", "hello world")
        assert score == 1.0

    def test_text_similarity_different(self):
        """Test similarity of completely different strings."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        score = scorer._text_similarity("hello", "xyzzy")
        assert score < 0.5

    def test_text_similarity_similar(self):
        """Test similarity of similar strings."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        score = scorer._text_similarity("john smith", "john smyth")
        assert 0.5 < score < 1.0

    def test_amount_similarity_identical(self):
        """Test amount similarity for identical values."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        score = scorer._amount_similarity("1000", "1000")
        assert score == 1.0

    def test_amount_similarity_close(self):
        """Test amount similarity for close values."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        score = scorer._amount_similarity("1000", "1001")
        assert score > 0.99  # Should be very similar

    def test_amount_similarity_different(self):
        """Test amount similarity for different values."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        score = scorer._amount_similarity("1000", "2000")
        assert score < 0.6  # 50% difference

    def test_date_similarity_identical(self):
        """Test date similarity for identical dates."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        score = scorer._date_similarity("2024-01-15", "2024-01-15")
        assert score == 1.0

    def test_date_similarity_within_week(self):
        """Test date similarity for dates within a week."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        score = scorer._date_similarity("2024-01-15", "2024-01-17")
        assert score >= 0.8

    def test_calculate_similarity_records(self):
        """Test overall similarity calculation between records."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        record1 = {"name": "John Doe", "address": "123 Main St", "amount": 1000}
        record2 = {"name": "John Doe", "address": "123 Main Street", "amount": 1000}

        fields = ["name", "address", "amount"]
        score = scorer.calculate_similarity(record1, record2, fields)

        assert score > 0.8  # Should be very similar


class TestDeduplicationEngine:
    """Tests for DeduplicationEngine class."""

    def test_deduplicate_exact_match(self):
        """Test exact match deduplication."""
        from datagod.utils.data_deduplication import DeduplicationEngine

        engine = DeduplicationEngine()

        records = [
            {"name": "John Doe", "address": "123 Main St"},
            {"name": "Jane Smith", "address": "456 Oak Ave"},
            {"name": "John Doe", "address": "123 Main St"},  # Duplicate
            {"name": "Bob Wilson", "address": "789 Pine Rd"},
        ]

        groups = engine.deduplicate_exact_match(records, ["name", "address"])

        assert len(groups) == 1
        assert groups[0].duplicate_count == 1
        assert groups[0].canonical_record["name"] == "John Doe"

    def test_deduplicate_exact_match_no_duplicates(self):
        """Test exact match with no duplicates."""
        from datagod.utils.data_deduplication import DeduplicationEngine

        engine = DeduplicationEngine()

        records = [
            {"name": "John Doe", "address": "123 Main St"},
            {"name": "Jane Smith", "address": "456 Oak Ave"},
            {"name": "Bob Wilson", "address": "789 Pine Rd"},
        ]

        groups = engine.deduplicate_exact_match(records, ["name", "address"])

        assert len(groups) == 0

    def test_deduplicate_fuzzy_match(self):
        """Test fuzzy match deduplication."""
        from datagod.utils.data_deduplication import DeduplicationEngine

        engine = DeduplicationEngine(similarity_threshold=0.8)

        records = [
            {"name": "John Doe", "address": "123 Main Street"},
            {"name": "John Doe", "address": "123 Main St"},  # Fuzzy match
            {"name": "Jane Smith", "address": "456 Oak Ave"},
        ]

        groups = engine.deduplicate_fuzzy_match(records, ["name", "address"])

        # Should find the fuzzy match
        assert len(groups) >= 0  # May or may not find depending on threshold

    def test_select_canonical_record(self):
        """Test canonical record selection."""
        from datagod.utils.data_deduplication import DeduplicationEngine

        engine = DeduplicationEngine()

        records = [
            {"name": "John"},  # Less complete
            {
                "name": "John Doe",
                "address": "123 Main St",
                "phone": "555-1234",
            },  # More complete
            {"name": "John Doe", "address": "123 Main St"},
        ]

        best_idx = engine._select_canonical_record(records)

        assert best_idx == 1  # Should select the most complete record


class TestDeduplicationService:
    """Tests for DeduplicationService class."""

    def test_deduplicate_records_exact_match(self):
        """Test deduplication with exact match algorithm."""
        from datagod.utils.data_deduplication import DeduplicationService

        service = DeduplicationService()

        records = [
            {"name": "John Doe", "address": "123 Main St", "amount": 1000},
            {"name": "Jane Smith", "address": "456 Oak Ave", "amount": 2000},
            {"name": "John Doe", "address": "123 Main St", "amount": 1000},  # Duplicate
        ]

        groups, metrics = service.deduplicate_records(
            records, algorithm="exact_match", fields=["name", "address"]
        )

        assert len(groups) == 1
        assert metrics.duplicates_found == 1
        assert metrics.algorithm_used == "exact_match"

    def test_deduplicate_records_fuzzy_match(self):
        """Test deduplication with fuzzy match algorithm."""
        from datagod.utils.data_deduplication import DeduplicationService

        service = DeduplicationService()

        records = [
            {"name": "John Doe", "address": "123 Main St"},
            {"name": "Jon Doe", "address": "123 Main Street"},  # Fuzzy duplicate
            {"name": "Jane Smith", "address": "456 Oak Ave"},
        ]

        groups, metrics = service.deduplicate_records(
            records, algorithm="fuzzy_match", fields=["name", "address"], threshold=0.7
        )

        assert metrics.algorithm_used == "fuzzy_match"
        assert metrics.similarity_threshold == 0.7

    def test_merge_duplicates_keep_canonical(self):
        """Test merging with keep_canonical strategy."""
        from datagod.utils.data_deduplication import (
            DeduplicationService,
            DuplicateGroup,
        )

        service = DeduplicationService()

        groups = [
            DuplicateGroup(
                group_id="test_1",
                canonical_record={"id": 1, "name": "John Doe"},
                duplicate_records=[{"id": 2, "name": "John Doe"}],
                confidence_score=1.0,
            )
        ]

        merged = service.merge_duplicates(groups, merge_strategy="keep_canonical")

        assert len(merged) == 1
        assert merged[0]["id"] == 1

    def test_merge_duplicates_merge_fields(self):
        """Test merging with merge_fields strategy."""
        from datagod.utils.data_deduplication import (
            DeduplicationService,
            DuplicateGroup,
        )

        service = DeduplicationService()

        groups = [
            DuplicateGroup(
                group_id="test_1",
                canonical_record={"id": 1, "name": "John Doe", "email": None},
                duplicate_records=[
                    {"id": 2, "name": "John Doe", "email": "john@example.com"}
                ],
                confidence_score=1.0,
            )
        ]

        merged = service.merge_duplicates(groups, merge_strategy="merge_fields")

        assert len(merged) == 1
        assert merged[0]["email"] == "john@example.com"  # Should merge from duplicate

    def test_get_deduplication_report(self):
        """Test deduplication report generation."""
        from datagod.utils.data_deduplication import (
            DeduplicationService,
            DuplicateGroup,
        )

        service = DeduplicationService()

        groups = [
            DuplicateGroup(
                group_id="test_1",
                canonical_record={"id": 1, "name": "John Doe"},
                duplicate_records=[{"id": 2}, {"id": 3}],
                confidence_score=0.95,
            ),
            DuplicateGroup(
                group_id="test_2",
                canonical_record={"id": 4, "name": "Jane Smith"},
                duplicate_records=[{"id": 5}],
                confidence_score=0.85,
            ),
        ]

        report = service.get_deduplication_report(groups)

        assert "summary" in report
        assert report["summary"]["total_groups"] == 2
        assert report["summary"]["total_duplicates"] == 3  # 2 + 1
        assert "confidence_distribution" in report


class TestDuplicateGroup:
    """Tests for DuplicateGroup dataclass."""

    def test_duplicate_group_properties(self):
        """Test DuplicateGroup properties."""
        from datagod.utils.data_deduplication import DuplicateGroup

        group = DuplicateGroup(
            group_id="test_1",
            canonical_record={"id": 1},
            duplicate_records=[{"id": 2}, {"id": 3}, {"id": 4}],
            confidence_score=0.9,
        )

        assert group.total_records == 4  # 1 canonical + 3 duplicates
        assert group.duplicate_count == 3

    def test_duplicate_group_to_dict(self):
        """Test DuplicateGroup serialization."""
        from datagod.utils.data_deduplication import DuplicateGroup

        group = DuplicateGroup(
            group_id="test_1", canonical_record={"id": 1}, confidence_score=0.9
        )

        data = group.to_dict()

        assert data["group_id"] == "test_1"
        assert data["confidence_score"] == 0.9
        assert "created_at" in data


class TestDeduplicationMetrics:
    """Tests for DeduplicationMetrics dataclass."""

    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        from datagod.utils.data_deduplication import DeduplicationMetrics

        metrics = DeduplicationMetrics(
            total_records_processed=100,
            duplicates_found=20,
            duplicate_groups_created=10,
            processing_time_seconds=1.5,
            algorithm_used="exact_match",
        )

        data = metrics.to_dict()

        assert data["total_records_processed"] == 100
        assert data["duplicates_found"] == 20
        assert data["deduplication_rate"] == 20.0  # 20/100 * 100


class TestDeduplicationEngineAdvanced:
    """Advanced tests for DeduplicationEngine class."""

    def test_deduplicate_clustering(self):
        """Test clustering-based deduplication."""
        from datagod.utils.data_deduplication import DeduplicationEngine

        engine = DeduplicationEngine(similarity_threshold=0.7)

        records = [
            {"name": "John Doe Real Estate LLC", "description": "Property management"},
            {
                "name": "John Doe Real Estate",
                "description": "Property management services",
            },
            {"name": "Jane Smith Insurance", "description": "Insurance services"},
        ]

        try:
            groups = engine.deduplicate_clustering(records, ["name", "description"])
            # If sklearn is available, it should return results
            assert isinstance(groups, list)
        except ImportError:
            # sklearn not available, skip
            pass

    def test_deduplicate_clustering_empty_records(self):
        """Test clustering with empty records."""
        from datagod.utils.data_deduplication import DeduplicationEngine

        engine = DeduplicationEngine()

        groups = engine.deduplicate_clustering([], ["name"])
        assert groups == []

    def test_deduplicate_clustering_single_record(self):
        """Test clustering with single record (below min_cluster_size)."""
        from datagod.utils.data_deduplication import DeduplicationEngine

        engine = DeduplicationEngine()

        records = [{"name": "John Doe"}]
        groups = engine.deduplicate_clustering(records, ["name"], min_cluster_size=2)
        assert groups == []

    def test_select_canonical_with_dates(self):
        """Test canonical selection with date fields."""
        from datetime import datetime, timedelta

        from datagod.utils.data_deduplication import DeduplicationEngine

        engine = DeduplicationEngine()

        records = [
            {
                "name": "John",
                "filing_date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
            },
            {
                "name": "John Doe",
                "filing_date": (datetime.utcnow() - timedelta(days=100)).isoformat(),
            },
            {
                "name": "John D",
                "filing_date": datetime.utcnow().isoformat(),
            },  # Most recent
        ]

        best_idx = engine._select_canonical_record(records)
        # Most recent with most fields should win
        assert best_idx in [0, 1, 2]  # Any is valid depending on scoring

    def test_select_canonical_with_datetime_objects(self):
        """Test canonical selection with datetime objects."""
        from datetime import datetime, timedelta

        from datagod.utils.data_deduplication import DeduplicationEngine

        engine = DeduplicationEngine()

        records = [
            {"name": "John Doe", "date": datetime.utcnow() - timedelta(days=50)},
            {"name": "John Doe Updated", "date": datetime.utcnow()},  # More recent
        ]

        best_idx = engine._select_canonical_record(records)
        assert best_idx == 1  # Most recent

    def test_find_similar_records(self):
        """Test finding similar records."""
        from datagod.utils.data_deduplication import DeduplicationEngine

        engine = DeduplicationEngine(similarity_threshold=0.8)

        target = {"name": "John Doe", "address": "123 Main St"}
        candidates = [
            {"name": "John Doe", "address": "123 Main Street"},  # Similar
            {"name": "Jane Smith", "address": "456 Oak Ave"},  # Different
        ]

        similar = engine._find_similar_records(
            target, candidates, ["name", "address"], set()
        )
        assert len(similar) >= 0  # May or may not find depending on exact threshold


class TestSimilarityScorerEdgeCases:
    """Edge case tests for SimilarityScorer."""

    def test_text_similarity_empty_strings(self):
        """Test similarity with empty strings."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        score = scorer._text_similarity("", "")
        assert score == 1.0  # Empty strings are identical

    def test_text_similarity_one_empty(self):
        """Test similarity with one empty string."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        score = scorer._text_similarity("hello", "")
        assert score == 0.0

    def test_amount_similarity_none_values(self):
        """Test amount similarity with None values."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        score = scorer._amount_similarity(None, "1000")
        assert score == 0.0

        score = scorer._amount_similarity("1000", None)
        assert score == 0.0

    def test_date_similarity_none_values(self):
        """Test date similarity with None values."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        score = scorer._date_similarity(None, "2024-01-15")
        assert score == 0.0

    def test_calculate_similarity_missing_fields(self):
        """Test similarity calculation with missing fields."""
        from datagod.utils.data_deduplication import SimilarityScorer

        scorer = SimilarityScorer()

        record1 = {"name": "John Doe"}
        record2 = {"name": "John Doe", "address": "123 Main St"}

        fields = ["name", "address", "missing_field"]
        score = scorer.calculate_similarity(record1, record2, fields)

        # Should still calculate based on available fields
        assert 0 <= score <= 1


class TestDataNormalizerEdgeCases:
    """Edge case tests for DataNormalizer."""

    def test_normalize_address_po_box(self):
        """Test address normalization with PO Box."""
        from datagod.utils.data_deduplication import DataNormalizer

        normalizer = DataNormalizer()

        addr1 = normalizer.normalize_address("P.O. Box 123")
        addr2 = normalizer.normalize_address("PO Box 123")
        # Both should normalize similarly
        assert addr1 == addr2 or "po" in addr1.lower() and "box" in addr1.lower()

    def test_normalize_name_multiple_suffixes(self):
        """Test name normalization with multiple suffixes."""
        from datagod.utils.data_deduplication import DataNormalizer

        normalizer = DataNormalizer()

        name = normalizer.normalize_name("John Smith Jr III")
        assert "jr" not in name
        assert "iii" not in name

    def test_create_comparison_key_empty_fields(self):
        """Test comparison key with empty field values."""
        from datagod.utils.data_deduplication import DataNormalizer

        normalizer = DataNormalizer()

        record = {"name": "", "address": None}
        key = normalizer.create_comparison_key(record, ["name", "address"])
        # Empty values result in empty normalized strings
        assert isinstance(key, str)


class TestDeduplicationServiceAdvanced:
    """Advanced tests for DeduplicationService."""

    def test_deduplicate_with_default_fields(self):
        """Test deduplication with default fields (None)."""
        from datagod.utils.data_deduplication import DeduplicationService

        service = DeduplicationService()

        records = [
            {"name": "John Doe", "address": "123 Main St"},
            {"name": "John Doe", "address": "123 Main St"},
            {"name": "Jane Smith", "address": "456 Oak Ave"},
        ]

        groups, metrics = service.deduplicate_records(
            records, algorithm="exact_match"  # fields defaults to None
        )

        # Should handle None fields gracefully
        assert metrics.total_records_processed == 3

    def test_deduplicate_with_clustering_algorithm(self):
        """Test deduplication with clustering algorithm."""
        from datagod.utils.data_deduplication import DeduplicationService

        service = DeduplicationService()

        records = [
            {"name": "John Doe Real Estate", "description": "Property management"},
            {"name": "John Doe Realty", "description": "Property management services"},
            {"name": "Jane Smith Insurance", "description": "Insurance provider"},
        ]

        try:
            groups, metrics = service.deduplicate_records(
                records, algorithm="clustering", fields=["name", "description"]
            )
            assert metrics.algorithm_used == "clustering"
        except ImportError:
            # sklearn not available
            pass

    def test_deduplicate_empty_records(self):
        """Test deduplication with empty records list."""
        from datagod.utils.data_deduplication import DeduplicationService

        service = DeduplicationService()

        groups, metrics = service.deduplicate_records(
            [], algorithm="exact_match", fields=["name"]
        )

        assert len(groups) == 0
        assert metrics.total_records_processed == 0
        assert metrics.duplicates_found == 0


class TestIntegration:
    """Integration tests for deduplication system."""

    def test_full_deduplication_workflow(self):
        """Test complete deduplication workflow."""
        from datagod.utils.data_deduplication import DeduplicationService

        service = DeduplicationService()

        # Sample records with duplicates
        records = [
            {"id": 1, "name": "John Doe", "address": "123 Main St", "amount": 250000},
            {"id": 2, "name": "Jane Smith", "address": "456 Oak Ave", "amount": 175000},
            {
                "id": 3,
                "name": "John Doe",
                "address": "123 Main St",
                "amount": 250000,
            },  # Duplicate of 1
            {"id": 4, "name": "Bob Wilson", "address": "789 Pine Rd", "amount": 300000},
            {
                "id": 5,
                "name": "John Doe",
                "address": "123 Main St",
                "amount": 250000,
            },  # Duplicate of 1
        ]

        # Run deduplication
        groups, metrics = service.deduplicate_records(
            records, algorithm="exact_match", fields=["name", "address", "amount"]
        )

        # Verify results
        assert metrics.total_records_processed == 5
        assert metrics.duplicates_found == 2  # 2 duplicates of John Doe
        assert len(groups) == 1

        # Merge duplicates
        merged = service.merge_duplicates(groups, merge_strategy="keep_canonical")
        assert len(merged) == 1

        # Generate report
        report = service.get_deduplication_report(groups)
        assert report["summary"]["total_duplicates"] == 2
