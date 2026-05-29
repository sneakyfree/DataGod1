"""
Tests for datagod/models/data_categories.py

Comprehensive tests for all data category models:
- TimestampMixin
- CourtCaseRecord
- BusinessEntityRecord
- UCCFilingRecord
- ProfessionalLicenseRecord
- TrademarkRecord
- PatentRecord
- SECFilingRecord
- BankRecord
- NewsArticleRecord
- PressReleaseRecord
"""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

# These tests are model structure tests that don't require actual database operations
# For database operations, we use mocks


class TestTimestampMixin:
    """Tests for TimestampMixin class"""

    def test_mixin_has_created_at(self):
        """Test that mixin defines created_at column"""
        from datagod.models.data_categories import TimestampMixin

        assert hasattr(TimestampMixin, "created_at")

    def test_mixin_has_updated_at(self):
        """Test that mixin defines updated_at column"""
        from datagod.models.data_categories import TimestampMixin

        assert hasattr(TimestampMixin, "updated_at")


class TestCourtCaseRecord:
    """Tests for CourtCaseRecord model structure"""

    def test_tablename(self):
        """Test table name is correct"""
        from datagod.models.data_categories import CourtCaseRecord

        assert CourtCaseRecord.__tablename__ == "court_cases"

    def test_has_required_columns(self):
        """Test that required columns exist"""
        from datagod.models.data_categories import CourtCaseRecord

        columns = {c.name for c in CourtCaseRecord.__table__.columns}
        required = {"id", "jurisdiction_id", "case_number", "case_type", "status"}
        assert required.issubset(columns)

    def test_has_optional_columns(self):
        """Test that optional columns exist"""
        from datagod.models.data_categories import CourtCaseRecord

        columns = {c.name for c in CourtCaseRecord.__table__.columns}
        optional = {
            "court_name",
            "case_title",
            "filing_date",
            "disposition_date",
            "judge_name",
            "county",
            "state",
            "amount_claimed",
            "amount_awarded",
            "parties",
            "url",
            "document_url",
            "raw_data",
        }
        assert optional.issubset(columns)

    def test_repr(self):
        """Test __repr__ method"""
        from datagod.models.data_categories import CourtCaseRecord

        case = CourtCaseRecord(case_number="2023-CV-12345", case_type="civil")
        repr_str = repr(case)
        assert "CourtCase" in repr_str
        assert "2023-CV-12345" in repr_str
        assert "civil" in repr_str

    def test_indexes_exist(self):
        """Test that indexes are defined"""
        from datagod.models.data_categories import CourtCaseRecord

        indexes = {idx.name for idx in CourtCaseRecord.__table__.indexes}
        assert "idx_court_case_number" in indexes
        assert "idx_court_case_type" in indexes


class TestBusinessEntityRecord:
    """Tests for BusinessEntityRecord model structure"""

    def test_tablename(self):
        """Test table name is correct"""
        from datagod.models.data_categories import BusinessEntityRecord

        assert BusinessEntityRecord.__tablename__ == "business_entities"

    def test_has_required_columns(self):
        """Test that required columns exist"""
        from datagod.models.data_categories import BusinessEntityRecord

        columns = {c.name for c in BusinessEntityRecord.__table__.columns}
        required = {
            "id",
            "jurisdiction_id",
            "entity_id",
            "entity_name",
            "entity_type",
            "state",
        }
        assert required.issubset(columns)

    def test_has_optional_columns(self):
        """Test that optional columns exist"""
        from datagod.models.data_categories import BusinessEntityRecord

        columns = {c.name for c in BusinessEntityRecord.__table__.columns}
        optional = {
            "status",
            "formation_date",
            "dissolution_date",
            "registered_agent_name",
            "registered_agent_address",
            "principal_address",
            "officers",
            "previous_names",
            "ein",
            "raw_data",
        }
        assert optional.issubset(columns)

    def test_repr(self):
        """Test __repr__ method"""
        from datagod.models.data_categories import BusinessEntityRecord

        entity = BusinessEntityRecord(
            entity_name="Acme Corp", entity_type="corporation"
        )
        repr_str = repr(entity)
        assert "BusinessEntity" in repr_str
        assert "Acme Corp" in repr_str
        assert "corporation" in repr_str

    def test_indexes_exist(self):
        """Test that indexes are defined"""
        from datagod.models.data_categories import BusinessEntityRecord

        indexes = {idx.name for idx in BusinessEntityRecord.__table__.indexes}
        assert "idx_business_entity_id" in indexes
        assert "idx_business_entity_name" in indexes


class TestUCCFilingRecord:
    """Tests for UCCFilingRecord model structure"""

    def test_tablename(self):
        """Test table name is correct"""
        from datagod.models.data_categories import UCCFilingRecord

        assert UCCFilingRecord.__tablename__ == "ucc_filings"

    def test_has_required_columns(self):
        """Test that required columns exist"""
        from datagod.models.data_categories import UCCFilingRecord

        columns = {c.name for c in UCCFilingRecord.__table__.columns}
        required = {
            "id",
            "jurisdiction_id",
            "filing_number",
            "filing_type",
            "filing_date",
        }
        assert required.issubset(columns)

    def test_has_optional_columns(self):
        """Test that optional columns exist"""
        from datagod.models.data_categories import UCCFilingRecord

        columns = {c.name for c in UCCFilingRecord.__table__.columns}
        optional = {
            "lapse_date",
            "secured_party",
            "secured_party_address",
            "debtor_name",
            "debtor_address",
            "collateral_description",
            "state",
            "amendments",
            "raw_data",
        }
        assert optional.issubset(columns)

    def test_repr(self):
        """Test __repr__ method"""
        from datagod.models.data_categories import UCCFilingRecord

        filing = UCCFilingRecord(filing_number="UCC-2023-12345", debtor_name="John Doe")
        repr_str = repr(filing)
        assert "UCCFiling" in repr_str
        assert "UCC-2023-12345" in repr_str

    def test_indexes_exist(self):
        """Test that indexes are defined"""
        from datagod.models.data_categories import UCCFilingRecord

        indexes = {idx.name for idx in UCCFilingRecord.__table__.indexes}
        assert "idx_ucc_filing_number" in indexes
        assert "idx_ucc_debtor" in indexes


class TestProfessionalLicenseRecord:
    """Tests for ProfessionalLicenseRecord model structure"""

    def test_tablename(self):
        """Test table name is correct"""
        from datagod.models.data_categories import ProfessionalLicenseRecord

        assert ProfessionalLicenseRecord.__tablename__ == "professional_licenses"

    def test_has_required_columns(self):
        """Test that required columns exist"""
        from datagod.models.data_categories import ProfessionalLicenseRecord

        columns = {c.name for c in ProfessionalLicenseRecord.__table__.columns}
        required = {
            "id",
            "jurisdiction_id",
            "license_number",
            "license_type",
            "licensee_name",
            "state",
        }
        assert required.issubset(columns)

    def test_has_optional_columns(self):
        """Test that optional columns exist"""
        from datagod.models.data_categories import ProfessionalLicenseRecord

        columns = {c.name for c in ProfessionalLicenseRecord.__table__.columns}
        optional = {
            "licensee_type",
            "first_name",
            "last_name",
            "status",
            "issue_date",
            "expiration_date",
            "city",
            "address",
            "employer_name",
            "specializations",
            "disciplinary_actions",
            "nmls_id",
            "raw_data",
        }
        assert optional.issubset(columns)

    def test_repr(self):
        """Test __repr__ method"""
        from datagod.models.data_categories import ProfessionalLicenseRecord

        license = ProfessionalLicenseRecord(
            license_number="RE-12345", licensee_name="John Agent"
        )
        repr_str = repr(license)
        assert "ProfessionalLicense" in repr_str
        assert "RE-12345" in repr_str

    def test_indexes_exist(self):
        """Test that indexes are defined"""
        from datagod.models.data_categories import ProfessionalLicenseRecord

        indexes = {idx.name for idx in ProfessionalLicenseRecord.__table__.indexes}
        assert "idx_license_number" in indexes
        assert "idx_license_nmls" in indexes


class TestTrademarkRecord:
    """Tests for TrademarkRecord model structure"""

    def test_tablename(self):
        """Test table name is correct"""
        from datagod.models.data_categories import TrademarkRecord

        assert TrademarkRecord.__tablename__ == "trademarks"

    def test_has_required_columns(self):
        """Test that required columns exist"""
        from datagod.models.data_categories import TrademarkRecord

        columns = {c.name for c in TrademarkRecord.__table__.columns}
        required = {"id", "serial_number"}
        assert required.issubset(columns)

    def test_has_optional_columns(self):
        """Test that optional columns exist"""
        from datagod.models.data_categories import TrademarkRecord

        columns = {c.name for c in TrademarkRecord.__table__.columns}
        optional = {
            "registration_number",
            "mark_text",
            "mark_description",
            "status",
            "filing_date",
            "registration_date",
            "owner_name",
            "owner_address",
            "owner_type",
            "attorney_name",
            "goods_services",
            "international_classes",
            "design_search_codes",
            "raw_data",
        }
        assert optional.issubset(columns)

    def test_repr(self):
        """Test __repr__ method"""
        from datagod.models.data_categories import TrademarkRecord

        tm = TrademarkRecord(serial_number="88123456", mark_text="ACME")
        repr_str = repr(tm)
        assert "Trademark" in repr_str
        assert "88123456" in repr_str
        assert "ACME" in repr_str

    def test_indexes_exist(self):
        """Test that indexes are defined"""
        from datagod.models.data_categories import TrademarkRecord

        indexes = {idx.name for idx in TrademarkRecord.__table__.indexes}
        assert "idx_trademark_serial" in indexes
        assert "idx_trademark_owner" in indexes


class TestPatentRecord:
    """Tests for PatentRecord model structure"""

    def test_tablename(self):
        """Test table name is correct"""
        from datagod.models.data_categories import PatentRecord

        assert PatentRecord.__tablename__ == "patents"

    def test_has_required_columns(self):
        """Test that required columns exist"""
        from datagod.models.data_categories import PatentRecord

        columns = {c.name for c in PatentRecord.__table__.columns}
        required = {"id", "patent_number"}
        assert required.issubset(columns)

    def test_has_optional_columns(self):
        """Test that optional columns exist"""
        from datagod.models.data_categories import PatentRecord

        columns = {c.name for c in PatentRecord.__table__.columns}
        optional = {
            "application_number",
            "title",
            "abstract",
            "patent_type",
            "status",
            "filing_date",
            "issue_date",
            "expiration_date",
            "inventors",
            "assignee_name",
            "assignee_address",
            "claims_count",
            "classification_codes",
            "citations",
            "raw_data",
        }
        assert optional.issubset(columns)

    def test_repr(self):
        """Test __repr__ method"""
        from datagod.models.data_categories import PatentRecord

        patent = PatentRecord(patent_number="US10123456", title="Widget Invention")
        repr_str = repr(patent)
        assert "Patent" in repr_str
        assert "US10123456" in repr_str

    def test_indexes_exist(self):
        """Test that indexes are defined"""
        from datagod.models.data_categories import PatentRecord

        indexes = {idx.name for idx in PatentRecord.__table__.indexes}
        assert "idx_patent_number" in indexes
        assert "idx_patent_assignee" in indexes


class TestSECFilingRecord:
    """Tests for SECFilingRecord model structure"""

    def test_tablename(self):
        """Test table name is correct"""
        from datagod.models.data_categories import SECFilingRecord

        assert SECFilingRecord.__tablename__ == "sec_filings"

    def test_has_required_columns(self):
        """Test that required columns exist"""
        from datagod.models.data_categories import SECFilingRecord

        columns = {c.name for c in SECFilingRecord.__table__.columns}
        required = {"id", "accession_number", "form_type", "cik", "filing_date"}
        assert required.issubset(columns)

    def test_has_optional_columns(self):
        """Test that optional columns exist"""
        from datagod.models.data_categories import SECFilingRecord

        columns = {c.name for c in SECFilingRecord.__table__.columns}
        optional = {
            "company_name",
            "ticker",
            "accepted_datetime",
            "period_of_report",
            "document_url",
            "description",
            "file_size",
            "sic_code",
            "sic_description",
            "state",
            "raw_data",
        }
        assert optional.issubset(columns)

    def test_repr(self):
        """Test __repr__ method"""
        from datagod.models.data_categories import SECFilingRecord

        filing = SECFilingRecord(
            accession_number="0001234567-23-012345", form_type="10-K"
        )
        repr_str = repr(filing)
        assert "SECFiling" in repr_str
        assert "10-K" in repr_str

    def test_indexes_exist(self):
        """Test that indexes are defined"""
        from datagod.models.data_categories import SECFilingRecord

        indexes = {idx.name for idx in SECFilingRecord.__table__.indexes}
        assert "idx_sec_accession" in indexes
        assert "idx_sec_ticker" in indexes


class TestBankRecord:
    """Tests for BankRecord model structure"""

    def test_tablename(self):
        """Test table name is correct"""
        from datagod.models.data_categories import BankRecord

        assert BankRecord.__tablename__ == "banks"

    def test_has_required_columns(self):
        """Test that required columns exist"""
        from datagod.models.data_categories import BankRecord

        columns = {c.name for c in BankRecord.__table__.columns}
        required = {"id", "fdic_cert", "bank_name"}
        assert required.issubset(columns)

    def test_has_optional_columns(self):
        """Test that optional columns exist"""
        from datagod.models.data_categories import BankRecord

        columns = {c.name for c in BankRecord.__table__.columns}
        optional = {
            "status",
            "charter_type",
            "headquarters_city",
            "headquarters_state",
            "headquarters_address",
            "established_date",
            "insured_date",
            "total_assets",
            "total_deposits",
            "branches_count",
            "holding_company",
            "primary_regulator",
            "raw_data",
        }
        assert optional.issubset(columns)

    def test_repr(self):
        """Test __repr__ method"""
        from datagod.models.data_categories import BankRecord

        bank = BankRecord(fdic_cert="12345", bank_name="First National Bank")
        repr_str = repr(bank)
        assert "Bank" in repr_str
        assert "12345" in repr_str
        assert "First National Bank" in repr_str

    def test_indexes_exist(self):
        """Test that indexes are defined"""
        from datagod.models.data_categories import BankRecord

        indexes = {idx.name for idx in BankRecord.__table__.indexes}
        assert "idx_bank_fdic_cert" in indexes
        assert "idx_bank_name" in indexes


class TestNewsArticleRecord:
    """Tests for NewsArticleRecord model structure"""

    def test_tablename(self):
        """Test table name is correct"""
        from datagod.models.data_categories import NewsArticleRecord

        assert NewsArticleRecord.__tablename__ == "news_articles"

    def test_has_required_columns(self):
        """Test that required columns exist"""
        from datagod.models.data_categories import NewsArticleRecord

        columns = {c.name for c in NewsArticleRecord.__table__.columns}
        required = {"id", "article_id", "title", "published_at"}
        assert required.issubset(columns)

    def test_has_optional_columns(self):
        """Test that optional columns exist"""
        from datagod.models.data_categories import NewsArticleRecord

        columns = {c.name for c in NewsArticleRecord.__table__.columns}
        optional = {
            "url",
            "author",
            "description",
            "content",
            "source_name",
            "source_type",
            "state",
            "city",
            "category",
            "sentiment",
            "keywords",
            "entities_mentioned",
            "locations_mentioned",
            "image_url",
            "raw_data",
        }
        assert optional.issubset(columns)

    def test_repr(self):
        """Test __repr__ method"""
        from datagod.models.data_categories import NewsArticleRecord

        article = NewsArticleRecord(
            title="A very long article title that should be truncated",
            source_name="Daily News",
        )
        repr_str = repr(article)
        assert "NewsArticle" in repr_str
        assert "Daily News" in repr_str

    def test_indexes_exist(self):
        """Test that indexes are defined"""
        from datagod.models.data_categories import NewsArticleRecord

        indexes = {idx.name for idx in NewsArticleRecord.__table__.indexes}
        assert "idx_news_article_id" in indexes
        assert "idx_news_source" in indexes


class TestPressReleaseRecord:
    """Tests for PressReleaseRecord model structure"""

    def test_tablename(self):
        """Test table name is correct"""
        from datagod.models.data_categories import PressReleaseRecord

        assert PressReleaseRecord.__tablename__ == "press_releases"

    def test_has_required_columns(self):
        """Test that required columns exist"""
        from datagod.models.data_categories import PressReleaseRecord

        columns = {c.name for c in PressReleaseRecord.__table__.columns}
        required = {"id", "release_id", "headline", "source_company", "published_at"}
        assert required.issubset(columns)

    def test_has_optional_columns(self):
        """Test that optional columns exist"""
        from datagod.models.data_categories import PressReleaseRecord

        columns = {c.name for c in PressReleaseRecord.__table__.columns}
        optional = {
            "url",
            "summary",
            "full_text",
            "contact_name",
            "contact_email",
            "contact_phone",
            "ticker_symbols",
            "topics",
            "wire_service",
            "raw_data",
        }
        assert optional.issubset(columns)

    def test_repr(self):
        """Test __repr__ method"""
        from datagod.models.data_categories import PressReleaseRecord

        release = PressReleaseRecord(
            headline="A very long headline that should be truncated in the repr",
            source_company="Test Company",
        )
        repr_str = repr(release)
        assert "PressRelease" in repr_str
        assert "Test Company" in repr_str

    def test_indexes_exist(self):
        """Test that indexes are defined"""
        from datagod.models.data_categories import PressReleaseRecord

        indexes = {idx.name for idx in PressReleaseRecord.__table__.indexes}
        assert "idx_press_release_id" in indexes
        assert "idx_press_company" in indexes


class TestModelImports:
    """Tests for model import functionality"""

    def test_all_models_importable(self):
        """Test that all models can be imported"""
        from datagod.models.data_categories import (
            BankRecord,
            BusinessEntityRecord,
            CourtCaseRecord,
            NewsArticleRecord,
            PatentRecord,
            PressReleaseRecord,
            ProfessionalLicenseRecord,
            SECFilingRecord,
            TimestampMixin,
            TrademarkRecord,
            UCCFilingRecord,
        )

        assert TimestampMixin is not None
        assert CourtCaseRecord is not None
        assert BusinessEntityRecord is not None
        assert UCCFilingRecord is not None
        assert ProfessionalLicenseRecord is not None
        assert TrademarkRecord is not None
        assert PatentRecord is not None
        assert SECFilingRecord is not None
        assert BankRecord is not None
        assert NewsArticleRecord is not None
        assert PressReleaseRecord is not None

    def test_models_inherit_from_base(self):
        """Test that all models inherit from Base"""
        from datagod.models.base import Base
        from datagod.models.data_categories import (
            BankRecord,
            BusinessEntityRecord,
            CourtCaseRecord,
            NewsArticleRecord,
            PatentRecord,
            PressReleaseRecord,
            ProfessionalLicenseRecord,
            SECFilingRecord,
            TrademarkRecord,
            UCCFilingRecord,
        )

        models = [
            CourtCaseRecord,
            BusinessEntityRecord,
            UCCFilingRecord,
            ProfessionalLicenseRecord,
            TrademarkRecord,
            PatentRecord,
            SECFilingRecord,
            BankRecord,
            NewsArticleRecord,
            PressReleaseRecord,
        ]
        for model in models:
            assert issubclass(model, Base)


class TestColumnDefaults:
    """Tests for column default values"""

    def test_court_case_default_status(self):
        """Test CourtCaseRecord default status"""
        from datagod.models.data_categories import CourtCaseRecord

        column = CourtCaseRecord.__table__.c.status
        assert column.default.arg == "open"

    def test_business_entity_default_status(self):
        """Test BusinessEntityRecord default status"""
        from datagod.models.data_categories import BusinessEntityRecord

        column = BusinessEntityRecord.__table__.c.status
        assert column.default.arg == "active"

    def test_professional_license_default_status(self):
        """Test ProfessionalLicenseRecord default status"""
        from datagod.models.data_categories import ProfessionalLicenseRecord

        column = ProfessionalLicenseRecord.__table__.c.status
        assert column.default.arg == "active"

    def test_bank_default_status(self):
        """Test BankRecord default status"""
        from datagod.models.data_categories import BankRecord

        column = BankRecord.__table__.c.status
        assert column.default.arg == "active"

    def test_bank_default_branches_count(self):
        """Test BankRecord default branches_count"""
        from datagod.models.data_categories import BankRecord

        column = BankRecord.__table__.c.branches_count
        assert column.default.arg == 0


class TestColumnTypes:
    """Tests for column type definitions"""

    def test_court_case_json_columns(self):
        """Test CourtCaseRecord JSON columns"""
        from sqlalchemy import JSON

        from datagod.models.data_categories import CourtCaseRecord

        parties_col = CourtCaseRecord.__table__.c.parties
        raw_data_col = CourtCaseRecord.__table__.c.raw_data
        assert isinstance(parties_col.type, JSON)
        assert isinstance(raw_data_col.type, JSON)

    def test_business_entity_json_columns(self):
        """Test BusinessEntityRecord JSON columns"""
        from sqlalchemy import JSON

        from datagod.models.data_categories import BusinessEntityRecord

        officers_col = BusinessEntityRecord.__table__.c.officers
        prev_names_col = BusinessEntityRecord.__table__.c.previous_names
        assert isinstance(officers_col.type, JSON)
        assert isinstance(prev_names_col.type, JSON)

    def test_trademark_json_columns(self):
        """Test TrademarkRecord JSON columns"""
        from sqlalchemy import JSON

        from datagod.models.data_categories import TrademarkRecord

        classes_col = TrademarkRecord.__table__.c.international_classes
        assert isinstance(classes_col.type, JSON)

    def test_patent_json_columns(self):
        """Test PatentRecord JSON columns"""
        from sqlalchemy import JSON

        from datagod.models.data_categories import PatentRecord

        inventors_col = PatentRecord.__table__.c.inventors
        citations_col = PatentRecord.__table__.c.citations
        assert isinstance(inventors_col.type, JSON)
        assert isinstance(citations_col.type, JSON)

    def test_news_article_json_columns(self):
        """Test NewsArticleRecord JSON columns"""
        from sqlalchemy import JSON

        from datagod.models.data_categories import NewsArticleRecord

        keywords_col = NewsArticleRecord.__table__.c.keywords
        entities_col = NewsArticleRecord.__table__.c.entities_mentioned
        locations_col = NewsArticleRecord.__table__.c.locations_mentioned
        assert isinstance(keywords_col.type, JSON)
        assert isinstance(entities_col.type, JSON)
        assert isinstance(locations_col.type, JSON)


class TestForeignKeys:
    """Tests for foreign key definitions"""

    def test_court_case_foreign_keys(self):
        """Test CourtCaseRecord foreign keys"""
        from datagod.models.data_categories import CourtCaseRecord

        fks = {fk.target_fullname for fk in CourtCaseRecord.__table__.foreign_keys}
        assert "jurisdictions.id" in fks
        assert "data_sources.id" in fks

    def test_business_entity_foreign_keys(self):
        """Test BusinessEntityRecord foreign keys"""
        from datagod.models.data_categories import BusinessEntityRecord

        fks = {fk.target_fullname for fk in BusinessEntityRecord.__table__.foreign_keys}
        assert "jurisdictions.id" in fks
        assert "data_sources.id" in fks

    def test_professional_license_foreign_keys(self):
        """Test ProfessionalLicenseRecord foreign keys"""
        from datagod.models.data_categories import ProfessionalLicenseRecord

        fks = {
            fk.target_fullname
            for fk in ProfessionalLicenseRecord.__table__.foreign_keys
        }
        assert "jurisdictions.id" in fks
        assert "data_sources.id" in fks
