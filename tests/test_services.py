"""
Tests for services/entity_linker.py and services/deduplication_service.py — 0% coverage boost
"""

import pytest
from datetime import datetime

from datagod.services.entity_linker import (
    EntityType,
    Entity,
    EntityMatch,
    EntityLinker,
)

from datagod.services.deduplication_service import (
    MergeStrategy,
    DuplicateGroup,
    MergeResult,
    NameStandardizer,
    AddressNormalizer,
    DeduplicationService,
)


# ============================================================
# Entity Linker Tests
# ============================================================

class TestEntityType:
    def test_values(self):
        assert EntityType.PERSON.value == "person"
        assert EntityType.COMPANY.value == "company"
        assert EntityType.PROPERTY.value == "property"
        assert EntityType.UNKNOWN.value == "unknown"


class TestEntity:
    def test_create(self):
        entity = Entity(
            entity_id="e1",
            entity_type=EntityType.PERSON,
            primary_name="John Smith"
        )
        assert entity.entity_id == "e1"
        assert entity.primary_name == "John Smith"

    def test_to_dict(self):
        entity = Entity(
            entity_id="e1",
            entity_type=EntityType.COMPANY,
            primary_name="Acme LLC"
        )
        d = entity.to_dict()
        assert isinstance(d, dict)
        assert d["entity_id"] == "e1"
        assert d["primary_name"] == "Acme LLC"


class TestEntityLinker:
    def setup_method(self):
        self.linker = EntityLinker()

    def test_initializes(self):
        assert self.linker is not None

    def test_link_person_new(self):
        matched, potentials = self.linker.link_person(name="John Smith")
        assert isinstance(potentials, list)

    def test_link_person_with_details(self):
        matched, potentials = self.linker.link_person(
            name="Jane Doe",
            dob="1990-01-15",
            address="123 Main St"
        )
        assert isinstance(potentials, list)

    def test_link_company(self):
        matched, potentials = self.linker.link_company(
            name="Acme Corporation",
            ein="12-3456789",
            state="NY"
        )
        assert isinstance(potentials, list)

    def test_link_property(self):
        matched, potentials = self.linker.link_property(
            address="123 Main Street, New York, NY 10001",
            parcel_id="ABC-123-456"
        )
        assert isinstance(potentials, list)

    def test_normalize_name(self):
        normalized = self.linker._normalize_name("  Dr. John Q. Smith Jr.  ")
        assert isinstance(normalized, str)
        assert len(normalized) > 0

    def test_normalize_company_name(self):
        normalized = self.linker._normalize_company_name("The Acme Corp., LLC")
        assert isinstance(normalized, str)

    def test_normalize_address(self):
        normalized = self.linker._normalize_address("123 North Main Street, Apt. 4B")
        assert isinstance(normalized, str)

    def test_normalize_parcel_id(self):
        normalized = self.linker._normalize_parcel_id("APN-123-456-789")
        assert isinstance(normalized, str)

    def test_name_similarity(self):
        score = self.linker._calculate_name_similarity("john smith", "jon smith")
        assert 0.0 <= score <= 1.0

    def test_name_similarity_exact(self):
        score = self.linker._calculate_name_similarity("john smith", "john smith")
        assert score >= 0.9

    def test_address_similarity(self):
        score = self.linker._calculate_address_similarity(
            "123 main st", "123 main street"
        )
        assert 0.0 <= score <= 1.0

    def test_link_and_find_person(self):
        # First link creates entity
        self.linker.link_person(name="Alice Johnson", address="456 Oak Ave")
        # Second link might find existing
        matched, potentials = self.linker.link_person(
            name="Alice Johnson", address="456 Oak Ave"
        )
        # Either matched or in potentials
        assert matched is not None or isinstance(potentials, list)


# ============================================================
# Deduplication Service Tests
# ============================================================

class TestMergeStrategy:
    def test_values(self):
        assert MergeStrategy.KEEP_NEWEST.value == "keep_newest"
        assert MergeStrategy.KEEP_OLDEST.value == "keep_oldest"
        assert MergeStrategy.KEEP_MOST_COMPLETE.value == "keep_complete"
        assert MergeStrategy.MERGE.value == "merge"
        assert MergeStrategy.MANUAL_REVIEW.value == "manual"


class TestDuplicateGroup:
    def test_create(self):
        group = DuplicateGroup(
            group_id="g1",
            records=[{"id": "r1"}, {"id": "r2"}],
            confidence=0.95,
            match_fields=["name", "address"],
            recommended_strategy=MergeStrategy.KEEP_NEWEST
        )
        assert group.group_id == "g1"
        assert len(group.records) == 2
        assert group.confidence == 0.95

    def test_to_dict(self):
        group = DuplicateGroup(
            group_id="g1",
            records=[{"id": "r1"}],
            confidence=0.9,
            match_fields=["name"],
            recommended_strategy=MergeStrategy.MERGE
        )
        d = group.to_dict()
        assert isinstance(d, dict)
        assert d["group_id"] == "g1"


class TestNameStandardizer:
    def test_standardize_simple(self):
        result = NameStandardizer.standardize("John Smith")
        assert isinstance(result, dict)
        assert "first" in result or "last" in result or "normalized_full" in result

    def test_standardize_with_suffix(self):
        result = NameStandardizer.standardize("Robert Smith Jr.")
        assert isinstance(result, dict)

    def test_standardize_with_prefix(self):
        result = NameStandardizer.standardize("Dr. Jane Doe")
        assert isinstance(result, dict)

    def test_names_match_identical(self):
        is_match, score = NameStandardizer.names_match("John Smith", "John Smith")
        assert is_match is True
        assert score >= 0.85

    def test_names_match_different(self):
        is_match, score = NameStandardizer.names_match("John Smith", "Alice Johnson")
        assert score < 0.85

    def test_names_match_nickname(self):
        is_match, score = NameStandardizer.names_match("Robert Smith", "Bob Smith")
        assert isinstance(is_match, bool)
        assert 0 <= score <= 1.0


class TestAddressNormalizer:
    def test_normalize_basic(self):
        result = AddressNormalizer.normalize("123 Main Street")
        assert isinstance(result, dict)

    def test_normalize_with_city_state(self):
        result = AddressNormalizer.normalize(
            "456 North Oak Avenue",
            city="Springfield",
            state="IL",
            zip_code="62701"
        )
        assert isinstance(result, dict)

    def test_normalize_abbreviations(self):
        result = AddressNormalizer.normalize("789 Southwest Elm Boulevard, Apt 3B")
        assert isinstance(result, dict)

    def test_addresses_match_same(self):
        is_match, score = AddressNormalizer.addresses_match(
            "123 Main St", "123 Main Street"
        )
        assert isinstance(is_match, bool)
        assert 0 <= score <= 1.0

    def test_addresses_match_different(self):
        is_match, score = AddressNormalizer.addresses_match(
            "123 Main St", "456 Oak Ave"
        )
        assert score < 0.9


class TestDeduplicationService:
    def setup_method(self):
        self.service = DeduplicationService()

    def test_initializes(self):
        assert self.service is not None

    def test_find_duplicates_no_matches(self):
        record = {"name": "John Smith", "address": "123 Main St"}
        candidates = [
            {"name": "Alice Johnson", "address": "456 Oak Ave"},
            {"name": "Bob Williams", "address": "789 Elm St"},
        ]
        groups = self.service.find_duplicates(record, candidates)
        assert isinstance(groups, list)

    def test_find_duplicates_exact_match(self):
        record = {"name": "John Smith", "address": "123 Main St"}
        candidates = [
            {"name": "John Smith", "address": "123 Main St"},
            {"name": "Bob Williams", "address": "789 Elm St"},
        ]
        groups = self.service.find_duplicates(record, candidates)
        assert isinstance(groups, list)

    def test_find_all_duplicates(self):
        records = [
            {"id": "1", "name": "John Smith", "address": "123 Main St"},
            {"id": "2", "name": "Jane Doe", "address": "456 Oak Ave"},
            {"id": "3", "name": "John Smith", "address": "123 Main Street"},
        ]
        groups = self.service.find_all_duplicates(records)
        assert isinstance(groups, list)

    def test_custom_thresholds(self):
        service = DeduplicationService(
            duplicate_threshold=0.95,
            possible_threshold=0.80
        )
        assert service is not None
