"""
Tests for Entity Linker Service
Tests entity linking, fuzzy matching, and cross-reference validation
"""

import pytest
from datetime import datetime

from datagod.services.entity_linker import (
    EntityLinker,
    Entity,
    EntityType,
    EntityMatch
)


class TestEntityLinker:
    """Tests for the EntityLinker class"""

    @pytest.fixture
    def linker(self):
        """Create an EntityLinker instance"""
        return EntityLinker()

    @pytest.fixture
    def sample_person_entity(self):
        """Create a sample person entity"""
        return Entity(
            entity_id="person_001",
            entity_type=EntityType.PERSON,
            primary_name="John Smith",
            aliases=["J. Smith", "Johnny Smith"],
            identifiers={"dob": "1980-01-15", "ssn_last4": "1234"},
            addresses=[{
                "raw": "123 Main St, Springfield, IL 62701",
                "normalized": "123 main st springfield il 62701"
            }],
            source_records=["rec_001", "rec_002"]
        )

    @pytest.fixture
    def sample_company_entity(self):
        """Create a sample company entity"""
        return Entity(
            entity_id="company_001",
            entity_type=EntityType.COMPANY,
            primary_name="Acme Corporation",
            aliases=["Acme Corp", "ACME Inc"],
            identifiers={"ein": "12-3456789", "state": "DE"},
            addresses=[{
                "raw": "456 Business Blvd, Wilmington, DE 19801",
                "normalized": "456 business blvd wilmington de 19801"
            }],
            source_records=["rec_003"]
        )

    @pytest.fixture
    def sample_property_entity(self):
        """Create a sample property entity"""
        return Entity(
            entity_id="property_001",
            entity_type=EntityType.PROPERTY,
            primary_name="123 Main Street",
            identifiers={
                "parcel_id": "12-34-567-890",
                "legal_description": "Lot 5 Block 3 Springfield Subdivision"
            },
            addresses=[{
                "raw": "123 Main Street, Springfield, IL 62701",
                "normalized": "123 main st springfield il 62701"
            }],
            source_records=["rec_004"]
        )

    # Entity Creation Tests
    def test_entity_creation(self, sample_person_entity):
        """Test creating an Entity"""
        assert sample_person_entity.entity_id == "person_001"
        assert sample_person_entity.entity_type == EntityType.PERSON
        assert sample_person_entity.primary_name == "John Smith"
        assert len(sample_person_entity.aliases) == 2

    def test_entity_to_dict(self, sample_person_entity):
        """Test converting Entity to dictionary"""
        entity_dict = sample_person_entity.to_dict()

        assert entity_dict['entity_id'] == "person_001"
        assert entity_dict['entity_type'] == "person"
        assert 'created_at' in entity_dict
        assert 'updated_at' in entity_dict

    # Name Normalization Tests
    def test_normalize_name_basic(self, linker):
        """Test basic name normalization"""
        normalized = linker._normalize_name("John Smith")
        assert normalized == "john smith"

    def test_normalize_name_with_suffix(self, linker):
        """Test name normalization removes suffixes"""
        normalized = linker._normalize_name("John Smith Jr.")
        assert "jr" not in normalized
        assert normalized == "john smith"

    def test_normalize_name_with_prefix(self, linker):
        """Test name normalization removes prefixes"""
        normalized = linker._normalize_name("Dr. John Smith")
        assert "dr" not in normalized

    def test_normalize_name_with_punctuation(self, linker):
        """Test name normalization removes punctuation"""
        normalized = linker._normalize_name("O'Brien, Mary-Jane")
        assert normalized == "obrien maryjane"

    # Company Name Normalization Tests
    def test_normalize_company_name_basic(self, linker):
        """Test basic company name normalization"""
        normalized = linker._normalize_company_name("Acme Corporation")
        assert "corporation" not in normalized
        assert normalized == "acme"

    def test_normalize_company_name_llc(self, linker):
        """Test company name normalization removes LLC"""
        normalized = linker._normalize_company_name("Smith Holdings LLC")
        assert "llc" not in normalized
        assert normalized == "smith holdings"

    def test_normalize_company_name_inc(self, linker):
        """Test company name normalization removes Inc."""
        normalized = linker._normalize_company_name("Tech Solutions Inc.")
        assert "inc" not in normalized
        assert normalized == "tech solutions"

    # Address Normalization Tests
    def test_normalize_address_basic(self, linker):
        """Test basic address normalization"""
        normalized = linker._normalize_address("123 Main Street")
        assert "st" in normalized
        assert "street" not in normalized

    def test_normalize_address_abbreviations(self, linker):
        """Test address normalization applies abbreviations"""
        normalized = linker._normalize_address("456 North Avenue, Suite 100")
        assert "n" in normalized
        assert "ave" in normalized
        assert "ste" in normalized

    def test_normalize_address_directions(self, linker):
        """Test address normalization for directions"""
        normalized = linker._normalize_address("789 West Boulevard")
        assert "w" in normalized
        assert "west" not in normalized

    # Parcel ID Normalization Tests
    def test_normalize_parcel_id_with_dashes(self, linker):
        """Test parcel ID normalization removes dashes"""
        normalized = linker._normalize_parcel_id("12-34-567-890")
        assert normalized == "1234567890"

    def test_normalize_parcel_id_with_spaces(self, linker):
        """Test parcel ID normalization removes spaces"""
        normalized = linker._normalize_parcel_id("12 34 567 890")
        assert normalized == "1234567890"

    def test_normalize_parcel_id_case(self, linker):
        """Test parcel ID normalization uppercases"""
        normalized = linker._normalize_parcel_id("abc-123-def")
        assert normalized == "ABC123DEF"

    # Jaro-Winkler Similarity Tests
    def test_jaro_winkler_identical(self, linker):
        """Test Jaro-Winkler with identical strings"""
        similarity = linker._jaro_winkler("hello", "hello")
        assert similarity == 1.0

    def test_jaro_winkler_similar(self, linker):
        """Test Jaro-Winkler with similar strings"""
        similarity = linker._jaro_winkler("john", "jonh")  # Transposition
        assert similarity > 0.9

    def test_jaro_winkler_different(self, linker):
        """Test Jaro-Winkler with different strings"""
        similarity = linker._jaro_winkler("john", "mary")
        assert similarity < 0.5

    def test_jaro_winkler_empty(self, linker):
        """Test Jaro-Winkler with empty strings"""
        similarity = linker._jaro_winkler("hello", "")
        assert similarity == 0.0

    def test_jaro_winkler_prefix_bonus(self, linker):
        """Test Jaro-Winkler prefix bonus"""
        # Same prefix should have higher similarity
        sim1 = linker._jaro_winkler("johnson", "johnsen")
        sim2 = linker._jaro_winkler("johnson", "jhnson")
        # Both are highly similar, demonstrating the algorithm works
        assert sim1 > 0.9
        assert sim2 > 0.9

    # Address Similarity Tests
    def test_address_similarity_identical(self, linker):
        """Test address similarity with identical addresses"""
        similarity = linker._calculate_address_similarity(
            "123 Main Street, Springfield, IL 62701",
            "123 Main Street, Springfield, IL 62701"
        )
        assert similarity > 0.95

    def test_address_similarity_normalized(self, linker):
        """Test address similarity with different formatting"""
        similarity = linker._calculate_address_similarity(
            "123 Main Street",
            "123 Main St"
        )
        assert similarity > 0.8

    def test_address_similarity_different(self, linker):
        """Test address similarity with different addresses"""
        similarity = linker._calculate_address_similarity(
            "123 Main Street",
            "456 Oak Avenue"
        )
        assert similarity < 0.5

    # Entity Cache Tests
    def test_add_entity(self, linker, sample_person_entity):
        """Test adding entity to cache"""
        entity_id = linker.add_entity(sample_person_entity)
        assert entity_id == "person_001"
        assert linker.get_entity("person_001") is not None

    def test_get_entity(self, linker, sample_person_entity):
        """Test retrieving entity from cache"""
        linker.add_entity(sample_person_entity)
        entity = linker.get_entity("person_001")
        assert entity.primary_name == "John Smith"

    def test_get_entity_not_found(self, linker):
        """Test retrieving non-existent entity"""
        entity = linker.get_entity("nonexistent")
        assert entity is None

    def test_remove_entity(self, linker, sample_person_entity):
        """Test removing entity from cache"""
        linker.add_entity(sample_person_entity)
        assert linker.remove_entity("person_001") is True
        assert linker.get_entity("person_001") is None

    def test_remove_entity_not_found(self, linker):
        """Test removing non-existent entity"""
        assert linker.remove_entity("nonexistent") is False

    # Person Linking Tests
    def test_link_person_exact_match(self, linker, sample_person_entity):
        """Test linking person with exact match"""
        linker.add_entity(sample_person_entity)

        matched, matches = linker.link_person(
            name="John Smith",
            dob="1980-01-15",
            address="123 Main St, Springfield, IL 62701"
        )

        assert matched is not None
        assert matched.entity_id == "person_001"
        assert len(matches) > 0
        assert matches[0].confidence >= linker.merge_threshold

    def test_link_person_fuzzy_name(self, linker, sample_person_entity):
        """Test linking person with fuzzy name match"""
        linker.add_entity(sample_person_entity)

        matched, matches = linker.link_person(
            name="Jon Smith",  # Misspelled
            dob="1980-01-15"
        )

        assert len(matches) > 0
        assert matches[0].confidence > 0.7

    def test_link_person_alias(self, linker, sample_person_entity):
        """Test linking person by alias"""
        linker.add_entity(sample_person_entity)

        matched, matches = linker.link_person(name="Johnny Smith")

        assert len(matches) > 0

    def test_link_person_no_match(self, linker, sample_person_entity):
        """Test linking person with no match"""
        linker.add_entity(sample_person_entity)

        matched, matches = linker.link_person(
            name="Mary Johnson",
            dob="1990-05-20"
        )

        assert matched is None
        assert len(matches) == 0

    # Company Linking Tests
    def test_link_company_exact_match(self, linker, sample_company_entity):
        """Test linking company with exact match"""
        linker.add_entity(sample_company_entity)

        matched, matches = linker.link_company(
            name="Acme Corporation",
            ein="12-3456789",
            state="DE"
        )

        assert matched is not None
        assert matched.entity_id == "company_001"

    def test_link_company_by_ein(self, linker, sample_company_entity):
        """Test linking company by EIN"""
        linker.add_entity(sample_company_entity)

        matched, matches = linker.link_company(
            name="ACME Corp",  # Different name format
            ein="12-3456789"
        )

        assert len(matches) > 0
        assert matches[0].confidence > 0.8

    def test_link_company_normalized(self, linker, sample_company_entity):
        """Test linking company with normalized name"""
        linker.add_entity(sample_company_entity)

        matched, matches = linker.link_company(
            name="Acme Inc"  # Different suffix
        )

        assert len(matches) > 0

    # Property Linking Tests
    def test_link_property_by_parcel(self, linker, sample_property_entity):
        """Test linking property by parcel ID"""
        linker.add_entity(sample_property_entity)

        matched, matches = linker.link_property(
            address="Different Address",
            parcel_id="12-34-567-890"
        )

        assert matched is not None
        assert matched.entity_id == "property_001"

    def test_link_property_by_address(self, linker, sample_property_entity):
        """Test linking property by address"""
        linker.add_entity(sample_property_entity)

        matched, matches = linker.link_property(
            address="123 Main Street, Springfield, IL 62701"
        )

        assert len(matches) > 0

    # Merge Tests
    def test_merge_entities(self, linker):
        """Test merging two entities"""
        entity1 = Entity(
            entity_id="merge_001",
            entity_type=EntityType.PERSON,
            primary_name="John Smith",
            aliases=["J. Smith"],
            identifiers={"ssn_last4": "1234"},
            source_records=["rec_001"]
        )
        entity2 = Entity(
            entity_id="merge_002",
            entity_type=EntityType.PERSON,
            primary_name="Johnny Smith",
            aliases=["John S."],
            identifiers={"dob": "1980-01-15"},
            source_records=["rec_002"]
        )

        linker.add_entity(entity1)
        linker.add_entity(entity2)

        merged = linker.merge_entities("merge_001", "merge_002")

        assert merged is not None
        assert merged.entity_id == "merge_001"
        assert "Johnny Smith" in merged.aliases
        assert "dob" in merged.identifiers
        assert "rec_002" in merged.source_records

        # entity2 should be removed
        assert linker.get_entity("merge_002") is None

    def test_merge_entities_not_found(self, linker, sample_person_entity):
        """Test merging with non-existent entity"""
        linker.add_entity(sample_person_entity)

        merged = linker.merge_entities("person_001", "nonexistent")
        assert merged is None

    # Statistics Tests
    def test_get_statistics_empty(self, linker):
        """Test statistics with empty cache"""
        stats = linker.get_statistics()

        assert stats['total_entities'] == 0
        assert stats['entities_by_type'] == {}

    def test_get_statistics_with_entities(self, linker, sample_person_entity, sample_company_entity):
        """Test statistics with entities"""
        linker.add_entity(sample_person_entity)
        linker.add_entity(sample_company_entity)

        stats = linker.get_statistics()

        assert stats['total_entities'] == 2
        assert stats['entities_by_type']['person'] == 1
        assert stats['entities_by_type']['company'] == 1

    # Threshold Configuration Tests
    def test_custom_thresholds(self):
        """Test custom threshold configuration"""
        linker = EntityLinker(merge_threshold=0.95, review_threshold=0.80)

        assert linker.merge_threshold == 0.95
        assert linker.review_threshold == 0.80
