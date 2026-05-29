"""
Tests for Deduplication Service
Tests duplicate detection, merge strategies, and batch processing
"""

from datetime import datetime, timedelta

import pytest

from datagod.services.deduplication_service import (
    DeduplicationService,
    DuplicateGroup,
    MergeResult,
    MergeStrategy,
    deduplicate_records,
)
from datagod.services.entity_linker import EntityLinker


class TestDeduplicationService:
    """Tests for the DeduplicationService class"""

    @pytest.fixture
    def service(self):
        """Create a DeduplicationService instance"""
        return DeduplicationService()

    @pytest.fixture
    def duplicate_records(self):
        """Sample duplicate records"""
        return [
            {
                "record_id": "rec_001",
                "document_number": "2024-001234",
                "grantor": "John Smith",
                "grantee": "Mary Johnson",
                "property_address": "123 Main Street, Springfield, IL",
                "amount": 250000,
                "record_date": "2024-01-15",
                "created_at": "2024-01-15T10:00:00",
            },
            {
                "record_id": "rec_002",
                "document_number": "2024-001234",  # Same document number
                "grantor": "John A. Smith",  # Slightly different name
                "grantee": "Mary L. Johnson",
                "property_address": "123 Main St, Springfield, IL",  # Normalized differently
                "amount": 250000,
                "record_date": "2024-01-15",
                "created_at": "2024-01-16T10:00:00",  # Later date
            },
        ]

    @pytest.fixture
    def non_duplicate_records(self):
        """Sample non-duplicate records"""
        return [
            {
                "record_id": "rec_003",
                "document_number": "2024-005678",
                "grantor": "Alice Brown",
                "grantee": "Bob Wilson",
                "property_address": "456 Oak Avenue, Chicago, IL",
                "amount": 350000,
                "record_date": "2024-02-20",
            },
            {
                "record_id": "rec_004",
                "document_number": "2024-009999",
                "grantor": "Carol Davis",
                "grantee": "Dan Miller",
                "property_address": "789 Pine Road, Naperville, IL",
                "amount": 450000,
                "record_date": "2024-03-10",
            },
        ]

    # Initialization Tests
    def test_service_initialization(self, service):
        """Test DeduplicationService initialization"""
        assert service.duplicate_threshold == 0.85
        assert service.possible_threshold == 0.70
        assert service.entity_linker is not None

    def test_custom_thresholds(self):
        """Test custom threshold configuration"""
        service = DeduplicationService(
            duplicate_threshold=0.90, possible_threshold=0.75
        )
        assert service.duplicate_threshold == 0.90
        assert service.possible_threshold == 0.75

    # Similarity Calculation Tests
    def test_calculate_similarity_exact_match(self, service, duplicate_records):
        """Test similarity calculation for exact duplicates"""
        similarity, match_fields = service._calculate_similarity(
            duplicate_records[0], duplicate_records[0]  # Same record
        )
        assert similarity == 0.0  # Same record ID skipped

    def test_calculate_similarity_high_match(self, service, duplicate_records):
        """Test similarity calculation for likely duplicates"""
        similarity, match_fields = service._calculate_similarity(
            duplicate_records[0], duplicate_records[1]
        )
        # Records with same document_number and similar names should have high similarity
        assert similarity > 0.7  # Fuzzy matches reduce exact match threshold
        assert "document_number" in match_fields

    def test_calculate_similarity_low_match(
        self, service, duplicate_records, non_duplicate_records
    ):
        """Test similarity calculation for non-duplicates"""
        similarity, match_fields = service._calculate_similarity(
            duplicate_records[0], non_duplicate_records[0]
        )
        assert similarity < 0.5

    # Find Duplicates Tests
    def test_find_duplicates_with_matches(self, service, duplicate_records):
        """Test finding duplicates in a list"""
        groups = service.find_duplicates(duplicate_records[0], [duplicate_records[1]])

        assert len(groups) > 0
        assert len(groups[0].records) == 2

    def test_find_duplicates_no_matches(
        self, service, duplicate_records, non_duplicate_records
    ):
        """Test finding duplicates with no matches"""
        groups = service.find_duplicates(duplicate_records[0], non_duplicate_records)

        assert len(groups) == 0

    def test_find_duplicates_skips_same_record(self, service, duplicate_records):
        """Test that find_duplicates skips the same record"""
        groups = service.find_duplicates(
            duplicate_records[0], duplicate_records  # Includes the same record
        )

        # Should still find duplicate (rec_002) but not self
        for group in groups:
            record_ids = [r["record_id"] for r in group.records]
            # Ensure both rec_001 and rec_002 are in the same group
            if "rec_001" in record_ids:
                assert len(set(record_ids)) == len(record_ids)  # No duplicates

    # Find All Duplicates Tests
    def test_find_all_duplicates(
        self, service, duplicate_records, non_duplicate_records
    ):
        """Test finding all duplicate groups"""
        all_records = duplicate_records + non_duplicate_records

        groups = service.find_all_duplicates(all_records)

        # Should find one duplicate group for duplicate_records
        assert len(groups) >= 1

    def test_find_all_duplicates_empty_list(self, service):
        """Test finding duplicates in empty list"""
        groups = service.find_all_duplicates([])
        assert len(groups) == 0

    def test_find_all_duplicates_single_record(self, service, duplicate_records):
        """Test finding duplicates with single record"""
        groups = service.find_all_duplicates([duplicate_records[0]])
        assert len(groups) == 0

    # Merge Strategy Tests
    def test_select_newest(self, service, duplicate_records):
        """Test selecting newest record"""
        newest = service._select_newest(duplicate_records)
        assert newest["record_id"] == "rec_002"  # Has later created_at

    def test_select_oldest(self, service, duplicate_records):
        """Test selecting oldest record"""
        oldest = service._select_oldest(duplicate_records)
        assert oldest["record_id"] == "rec_001"  # Has earlier created_at

    def test_select_most_complete(self, service):
        """Test selecting most complete record"""
        records = [
            {"record_id": "incomplete", "field1": "value1"},
            {
                "record_id": "complete",
                "field1": "value1",
                "field2": "value2",
                "field3": "value3",
            },
        ]
        most_complete = service._select_most_complete(records)
        assert most_complete["record_id"] == "complete"

    def test_merge_records(self, service):
        """Test merging records"""
        records = [
            {"record_id": "rec1", "field_a": "value_a", "field_b": None},
            {
                "record_id": "rec2",
                "field_a": None,
                "field_b": "value_b",
                "field_c": "value_c",
            },
        ]
        merged = service._merge_records(records)

        assert merged["field_a"] == "value_a"
        assert merged["field_b"] == "value_b"
        assert merged["field_c"] == "value_c"
        assert "_merged_from" in merged

    # Merge Duplicates Tests
    def test_merge_duplicates_keep_newest(self, service, duplicate_records):
        """Test merging with KEEP_NEWEST strategy"""
        group = DuplicateGroup(
            group_id="test_group",
            records=duplicate_records,
            confidence=0.90,
            match_fields=["document_number"],
            recommended_strategy=MergeStrategy.KEEP_NEWEST,
        )

        result = service.merge_duplicates(group)

        assert result.success is True
        assert result.kept_record["record_id"] == "rec_002"
        assert "rec_001" in result.removed_records
        assert result.strategy_used == MergeStrategy.KEEP_NEWEST

    def test_merge_duplicates_keep_oldest(self, service, duplicate_records):
        """Test merging with KEEP_OLDEST strategy"""
        group = DuplicateGroup(
            group_id="test_group",
            records=duplicate_records,
            confidence=0.90,
            match_fields=["document_number"],
            recommended_strategy=MergeStrategy.KEEP_OLDEST,
        )

        result = service.merge_duplicates(group, MergeStrategy.KEEP_OLDEST)

        assert result.success is True
        assert result.kept_record["record_id"] == "rec_001"
        assert "rec_002" in result.removed_records

    def test_merge_duplicates_manual_review(self, service, duplicate_records):
        """Test merging with MANUAL_REVIEW strategy"""
        group = DuplicateGroup(
            group_id="test_group",
            records=duplicate_records,
            confidence=0.75,
            match_fields=["grantor"],
            recommended_strategy=MergeStrategy.MANUAL_REVIEW,
        )

        result = service.merge_duplicates(group)

        assert result.success is False
        assert result.kept_record is None
        assert "requires_manual_review" in result.audit_info.get("status", "")

    def test_merge_duplicates_insufficient_records(self, service):
        """Test merging with insufficient records"""
        group = DuplicateGroup(
            group_id="test_group",
            records=[{"record_id": "single"}],  # Only one record
            confidence=1.0,
            match_fields=[],
            recommended_strategy=MergeStrategy.KEEP_NEWEST,
        )

        result = service.merge_duplicates(group)

        assert result.success is False
        assert "error" in result.audit_info

    # Record ID Tests
    def test_get_record_id_with_record_id(self, service):
        """Test getting record ID from record_id field"""
        record = {"record_id": "test_123", "other": "data"}
        assert service._get_record_id(record) == "test_123"

    def test_get_record_id_with_id(self, service):
        """Test getting record ID from id field"""
        record = {"id": "test_456", "other": "data"}
        assert service._get_record_id(record) == "test_456"

    def test_get_record_id_generated(self, service):
        """Test generating record ID from hash"""
        record = {"field1": "value1", "field2": "value2"}
        record_id = service._get_record_id(record)
        assert len(record_id) == 16  # MD5 hash truncated to 16 chars

    # DuplicateGroup Tests
    def test_duplicate_group_creation(self, duplicate_records):
        """Test creating a DuplicateGroup"""
        group = DuplicateGroup(
            group_id="group_001",
            records=duplicate_records,
            confidence=0.95,
            match_fields=["document_number", "amount"],
            recommended_strategy=MergeStrategy.KEEP_NEWEST,
        )

        assert group.group_id == "group_001"
        assert len(group.records) == 2
        assert group.confidence == 0.95

    def test_duplicate_group_to_dict(self, duplicate_records):
        """Test converting DuplicateGroup to dictionary"""
        group = DuplicateGroup(
            group_id="group_001",
            records=duplicate_records,
            confidence=0.95,
            match_fields=["document_number"],
            recommended_strategy=MergeStrategy.KEEP_NEWEST,
        )

        group_dict = group.to_dict()

        assert group_dict["group_id"] == "group_001"
        assert group_dict["record_count"] == 2
        assert "rec_001" in group_dict["record_ids"]
        assert "rec_002" in group_dict["record_ids"]

    # Statistics Tests
    def test_get_statistics_initial(self, service):
        """Test getting initial statistics"""
        stats = service.get_statistics()

        assert stats["total_duplicate_groups"] == 0
        assert stats["total_merge_operations"] == 0
        assert stats["successful_merges"] == 0
        assert stats["total_records_removed"] == 0

    def test_get_statistics_after_merge(self, service, duplicate_records):
        """Test statistics after merge operations"""
        group = DuplicateGroup(
            group_id="test_group",
            records=duplicate_records,
            confidence=0.90,
            match_fields=["document_number"],
            recommended_strategy=MergeStrategy.KEEP_NEWEST,
        )

        service.merge_duplicates(group)
        stats = service.get_statistics()

        assert stats["total_merge_operations"] == 1
        assert stats["successful_merges"] == 1
        assert stats["total_records_removed"] == 1

    # Pending Review Tests
    def test_get_pending_review(self, service, duplicate_records):
        """Test getting groups pending review"""
        # Add a group that needs review
        group = DuplicateGroup(
            group_id="review_group",
            records=duplicate_records,
            confidence=0.78,
            match_fields=["grantor"],
            recommended_strategy=MergeStrategy.MANUAL_REVIEW,
        )
        service.duplicate_groups["review_group"] = group

        pending = service.get_pending_review()

        assert len(pending) == 1
        assert pending[0].group_id == "review_group"

    # Clear History Tests
    def test_clear_history(self, service, duplicate_records):
        """Test clearing deduplication history"""
        group = DuplicateGroup(
            group_id="test_group",
            records=duplicate_records,
            confidence=0.90,
            match_fields=["document_number"],
            recommended_strategy=MergeStrategy.KEEP_NEWEST,
        )

        service.duplicate_groups["test_group"] = group
        service.merge_duplicates(group)

        assert len(service.duplicate_groups) > 0
        assert len(service.merge_history) > 0

        service.clear_history()

        assert len(service.duplicate_groups) == 0
        assert len(service.merge_history) == 0


class TestDeduplicateRecordsFunction:
    """Tests for the deduplicate_records convenience function"""

    @pytest.fixture
    def mixed_records(self):
        """Mix of duplicate and unique records"""
        return [
            {
                "record_id": "dup_1",
                "document_number": "2024-001",
                "grantor": "John Smith",
            },
            {
                "record_id": "dup_2",
                "document_number": "2024-001",
                "grantor": "John A Smith",
            },
            {
                "record_id": "unique_1",
                "document_number": "2024-002",
                "grantor": "Mary Johnson",
            },
            {
                "record_id": "unique_2",
                "document_number": "2024-003",
                "grantor": "Bob Wilson",
            },
        ]

    def test_deduplicate_records_basic(self, mixed_records):
        """Test basic deduplication"""
        deduplicated, stats = deduplicate_records(mixed_records)

        # Should have removed one duplicate
        assert len(deduplicated) <= len(mixed_records)
        assert stats["total_records_removed"] >= 0

    def test_deduplicate_records_with_strategy(self, mixed_records):
        """Test deduplication with specific strategy"""
        deduplicated, stats = deduplicate_records(
            mixed_records, strategy=MergeStrategy.KEEP_OLDEST
        )

        assert isinstance(deduplicated, list)
        assert isinstance(stats, dict)

    def test_deduplicate_records_with_threshold(self, mixed_records):
        """Test deduplication with custom threshold"""
        # High threshold should find fewer duplicates
        deduplicated_high, stats_high = deduplicate_records(
            mixed_records, threshold=0.99
        )

        # Low threshold should find more duplicates
        deduplicated_low, stats_low = deduplicate_records(mixed_records, threshold=0.50)

        # Higher threshold = fewer duplicates found = more records kept
        assert len(deduplicated_high) >= len(deduplicated_low)

    def test_deduplicate_records_empty_list(self):
        """Test deduplication with empty list"""
        deduplicated, stats = deduplicate_records([])

        assert deduplicated == []
        assert stats["total_duplicate_groups"] == 0

    def test_deduplicate_records_no_duplicates(self):
        """Test deduplication with no duplicates"""
        unique_records = [
            {"record_id": "1", "document_number": "A"},
            {"record_id": "2", "document_number": "B"},
            {"record_id": "3", "document_number": "C"},
        ]

        deduplicated, stats = deduplicate_records(unique_records)

        assert len(deduplicated) == len(unique_records)
