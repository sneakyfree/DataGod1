"""
Comprehensive tests for Court Records module.

Tests cover:
- Enums (CaseType, CaseStatus, PartyType)
- Data classes (CaseParty, CourtCase, CaseSearch, PartySearch)
- CourtRecordsScraper abstract class and utilities
- StateCourtScraper implementation
- Convenience functions
"""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from datagod.scrapers.categories.court_records import (
    CaseParty,
    CaseSearch,
    CaseStatus,
    CaseType,
    CourtCase,
    CourtRecordsScraper,
    PartySearch,
    PartyType,
    StateCourtScraper,
    search_court_records,
)


class TestCaseTypeEnum:
    """Tests for CaseType enumeration"""

    def test_all_case_types_exist(self):
        """Verify all expected case types are defined"""
        expected_types = [
            "CIVIL",
            "CRIMINAL",
            "FAMILY",
            "PROBATE",
            "BANKRUPTCY",
            "SMALL_CLAIMS",
            "TAX",
            "TRAFFIC",
            "JUVENILE",
            "APPELLATE",
            "UNKNOWN",
        ]
        for case_type in expected_types:
            assert hasattr(CaseType, case_type)

    def test_case_type_values(self):
        """Verify case type string values"""
        assert CaseType.CIVIL.value == "civil"
        assert CaseType.CRIMINAL.value == "criminal"
        assert CaseType.FAMILY.value == "family"
        assert CaseType.PROBATE.value == "probate"
        assert CaseType.BANKRUPTCY.value == "bankruptcy"

    def test_case_type_from_value(self):
        """Test creating CaseType from string value"""
        assert CaseType("civil") == CaseType.CIVIL
        assert CaseType("criminal") == CaseType.CRIMINAL


class TestCaseStatusEnum:
    """Tests for CaseStatus enumeration"""

    def test_all_case_statuses_exist(self):
        """Verify all expected case statuses are defined"""
        expected_statuses = [
            "OPEN",
            "CLOSED",
            "PENDING",
            "DISMISSED",
            "SETTLED",
            "APPEALED",
            "ON_HOLD",
            "UNKNOWN",
        ]
        for status in expected_statuses:
            assert hasattr(CaseStatus, status)

    def test_case_status_values(self):
        """Verify case status string values"""
        assert CaseStatus.OPEN.value == "open"
        assert CaseStatus.CLOSED.value == "closed"
        assert CaseStatus.PENDING.value == "pending"
        assert CaseStatus.DISMISSED.value == "dismissed"


class TestPartyTypeEnum:
    """Tests for PartyType enumeration"""

    def test_all_party_types_exist(self):
        """Verify all expected party types are defined"""
        expected_types = [
            "PLAINTIFF",
            "DEFENDANT",
            "PETITIONER",
            "RESPONDENT",
            "APPELLANT",
            "APPELLEE",
            "CREDITOR",
            "DEBTOR",
            "WITNESS",
            "ATTORNEY",
            "JUDGE",
            "OTHER",
        ]
        for party_type in expected_types:
            assert hasattr(PartyType, party_type)

    def test_party_type_values(self):
        """Verify party type string values"""
        assert PartyType.PLAINTIFF.value == "plaintiff"
        assert PartyType.DEFENDANT.value == "defendant"


class TestCaseParty:
    """Tests for CaseParty dataclass"""

    def test_create_basic_party(self):
        """Test creating a basic case party"""
        party = CaseParty(name="John Doe", party_type=PartyType.PLAINTIFF)
        assert party.name == "John Doe"
        assert party.party_type == PartyType.PLAINTIFF
        assert party.party_id is None
        assert party.address is None
        assert party.is_business is False

    def test_create_full_party(self):
        """Test creating a party with all fields"""
        party = CaseParty(
            name="ABC Corporation",
            party_type=PartyType.DEFENDANT,
            party_id="P123",
            address="123 Main St, City, ST 12345",
            attorney_name="Jane Smith",
            attorney_firm="Smith & Associates",
            is_business=True,
        )
        assert party.name == "ABC Corporation"
        assert party.party_id == "P123"
        assert party.is_business is True

    def test_party_to_dict(self):
        """Test converting party to dictionary"""
        party = CaseParty(
            name="John Doe", party_type=PartyType.PLAINTIFF, attorney_name="Jane Smith"
        )
        result = party.to_dict()
        assert result["name"] == "John Doe"
        assert result["party_type"] == "plaintiff"
        assert result["attorney_name"] == "Jane Smith"
        assert result["is_business"] is False


class TestCourtCase:
    """Tests for CourtCase dataclass"""

    def test_create_minimal_court_case(self):
        """Test creating a court case with minimal fields"""
        case = CourtCase(
            case_number="2024-CV-001234",
            case_type=CaseType.CIVIL,
            court_name="Superior Court",
        )
        assert case.case_number == "2024-CV-001234"
        assert case.case_type == CaseType.CIVIL
        assert case.court_name == "Superior Court"
        assert case.status == CaseStatus.UNKNOWN
        assert case.parties == []

    def test_create_full_court_case(self):
        """Test creating a court case with all fields"""
        parties = [
            CaseParty(name="John Doe", party_type=PartyType.PLAINTIFF),
            CaseParty(name="ABC Corp", party_type=PartyType.DEFENDANT),
        ]
        case = CourtCase(
            case_number="2024-CV-001234",
            case_type=CaseType.CIVIL,
            court_name="Superior Court",
            filing_date=date(2024, 1, 15),
            case_title="Doe v. ABC Corp",
            status=CaseStatus.OPEN,
            judge_name="Hon. Smith",
            parties=parties,
            jurisdiction="California",
            county="Los Angeles",
            state="CA",
            amount_claimed=100000.00,
        )
        assert case.filing_date == date(2024, 1, 15)
        assert case.amount_claimed == 100000.00
        assert len(case.parties) == 2

    def test_court_case_to_dict(self):
        """Test converting court case to dictionary"""
        case = CourtCase(
            case_number="2024-CV-001234",
            case_type=CaseType.CIVIL,
            court_name="Superior Court",
            filing_date=date(2024, 1, 15),
        )
        result = case.to_dict()
        assert result["case_number"] == "2024-CV-001234"
        assert result["case_type"] == "civil"
        assert result["filing_date"] == "2024-01-15"
        assert "fetched_at" in result

    def test_plaintiffs_property(self):
        """Test getting plaintiffs from parties"""
        parties = [
            CaseParty(name="John Doe", party_type=PartyType.PLAINTIFF),
            CaseParty(name="Jane Doe", party_type=PartyType.PETITIONER),
            CaseParty(name="ABC Corp", party_type=PartyType.DEFENDANT),
        ]
        case = CourtCase(
            case_number="2024-CV-001234",
            case_type=CaseType.CIVIL,
            court_name="Superior Court",
            parties=parties,
        )
        plaintiffs = case.plaintiffs
        assert len(plaintiffs) == 2
        assert plaintiffs[0].name == "John Doe"
        assert plaintiffs[1].name == "Jane Doe"

    def test_defendants_property(self):
        """Test getting defendants from parties"""
        parties = [
            CaseParty(name="John Doe", party_type=PartyType.PLAINTIFF),
            CaseParty(name="ABC Corp", party_type=PartyType.DEFENDANT),
            CaseParty(name="XYZ Inc", party_type=PartyType.RESPONDENT),
        ]
        case = CourtCase(
            case_number="2024-CV-001234",
            case_type=CaseType.CIVIL,
            court_name="Superior Court",
            parties=parties,
        )
        defendants = case.defendants
        assert len(defendants) == 2


class TestCaseSearch:
    """Tests for CaseSearch dataclass"""

    def test_create_empty_search(self):
        """Test creating search with no parameters"""
        search = CaseSearch()
        assert search.case_number is None
        assert search.party_name is None
        assert search.include_closed is True

    def test_create_full_search(self):
        """Test creating search with all parameters"""
        search = CaseSearch(
            case_number="2024-CV-001234",
            party_name="John Doe",
            case_type=CaseType.CIVIL,
            court_name="Superior Court",
            county="Los Angeles",
            state="CA",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31),
            status=CaseStatus.OPEN,
            include_closed=False,
        )
        assert search.case_number == "2024-CV-001234"
        assert search.include_closed is False


class TestPartySearch:
    """Tests for PartySearch dataclass"""

    def test_create_minimal_party_search(self):
        """Test creating party search with required fields only"""
        search = PartySearch(name="John Doe")
        assert search.name == "John Doe"
        assert search.party_type is None
        assert search.exact_match is False

    def test_create_full_party_search(self):
        """Test creating party search with all fields"""
        search = PartySearch(
            name="John Doe",
            party_type=PartyType.DEFENDANT,
            state="CA",
            county="Los Angeles",
            case_type=CaseType.CIVIL,
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31),
            exact_match=True,
        )
        assert search.exact_match is True
        assert search.party_type == PartyType.DEFENDANT


class TestCourtRecordsScraperUtils:
    """Tests for CourtRecordsScraper utility methods"""

    @pytest.fixture
    def scraper(self):
        """Create a StateCourtScraper for testing utility methods"""
        return StateCourtScraper("CA", config={"base_url": "https://example.com"})

    def test_classify_case_type_civil(self, scraper):
        """Test classifying civil cases"""
        assert scraper.classify_case_type("Civil Contract Dispute") == CaseType.CIVIL
        assert scraper.classify_case_type("Tort - Personal Injury") == CaseType.CIVIL
        assert scraper.classify_case_type("Breach of Contract") == CaseType.CIVIL

    def test_classify_case_type_criminal(self, scraper):
        """Test classifying criminal cases"""
        assert scraper.classify_case_type("Criminal Felony") == CaseType.CRIMINAL
        assert scraper.classify_case_type("Misdemeanor - Theft") == CaseType.CRIMINAL
        assert scraper.classify_case_type("DUI Offense") == CaseType.CRIMINAL

    def test_classify_case_type_family(self, scraper):
        """Test classifying family cases"""
        assert scraper.classify_case_type("Family Law - Divorce") == CaseType.FAMILY
        assert scraper.classify_case_type("Child Custody") == CaseType.FAMILY
        assert scraper.classify_case_type("Adoption Petition") == CaseType.FAMILY

    def test_classify_case_type_probate(self, scraper):
        """Test classifying probate cases"""
        assert scraper.classify_case_type("Probate - Estate") == CaseType.PROBATE
        assert scraper.classify_case_type("Trust Administration") == CaseType.PROBATE
        assert scraper.classify_case_type("Guardianship") == CaseType.PROBATE

    def test_classify_case_type_special(self, scraper):
        """Test classifying special case types"""
        assert scraper.classify_case_type("Bankruptcy Chapter 7") == CaseType.BANKRUPTCY
        assert scraper.classify_case_type("Small Claims") == CaseType.SMALL_CLAIMS
        assert scraper.classify_case_type("Tax Court") == CaseType.TAX
        assert scraper.classify_case_type("Traffic Violation") == CaseType.TRAFFIC
        assert scraper.classify_case_type("Juvenile Matter") == CaseType.JUVENILE
        assert scraper.classify_case_type("Appeal Filed") == CaseType.APPELLATE

    def test_classify_case_type_unknown(self, scraper):
        """Test classifying unknown case types"""
        assert scraper.classify_case_type("Random Text") == CaseType.UNKNOWN
        assert scraper.classify_case_type("") == CaseType.UNKNOWN

    def test_parse_case_status_open(self, scraper):
        """Test parsing open case statuses"""
        assert scraper.parse_case_status("Open") == CaseStatus.OPEN
        assert scraper.parse_case_status("Active") == CaseStatus.OPEN
        assert scraper.parse_case_status("PENDING TRIAL") == CaseStatus.OPEN

    def test_parse_case_status_closed(self, scraper):
        """Test parsing closed case statuses"""
        assert scraper.parse_case_status("Closed") == CaseStatus.CLOSED
        assert scraper.parse_case_status("Disposed") == CaseStatus.CLOSED
        assert scraper.parse_case_status("Final Judgment") == CaseStatus.CLOSED

    def test_parse_case_status_other(self, scraper):
        """Test parsing other case statuses"""
        assert scraper.parse_case_status("Pending Review") == CaseStatus.PENDING
        assert (
            scraper.parse_case_status("Dismissed with Prejudice")
            == CaseStatus.DISMISSED
        )
        assert scraper.parse_case_status("Settled out of court") == CaseStatus.SETTLED
        assert scraper.parse_case_status("On Appeal") == CaseStatus.APPEALED
        assert scraper.parse_case_status("On Hold") == CaseStatus.ON_HOLD

    def test_parse_case_status_unknown(self, scraper):
        """Test parsing unknown case statuses"""
        assert scraper.parse_case_status("Some Random Status") == CaseStatus.UNKNOWN

    def test_parse_party_type(self, scraper):
        """Test parsing party types"""
        assert scraper.parse_party_type("Plaintiff") == PartyType.PLAINTIFF
        assert scraper.parse_party_type("DEFENDANT") == PartyType.DEFENDANT
        assert scraper.parse_party_type("Petitioner") == PartyType.PETITIONER
        assert scraper.parse_party_type("respondent") == PartyType.RESPONDENT
        assert scraper.parse_party_type("Appellant") == PartyType.APPELLANT
        assert scraper.parse_party_type("Appellee") == PartyType.APPELLEE
        assert scraper.parse_party_type("Creditor") == PartyType.CREDITOR
        assert scraper.parse_party_type("Debtor") == PartyType.DEBTOR
        assert scraper.parse_party_type("Attorney") == PartyType.ATTORNEY
        # Note: "Counsel for Plaintiff" contains "plaintiff" which is checked before "counsel"
        assert scraper.parse_party_type("Counsel for Plaintiff") == PartyType.PLAINTIFF
        # Use pure "Counsel" to test attorney matching
        assert scraper.parse_party_type("Legal Counsel") == PartyType.ATTORNEY
        assert scraper.parse_party_type("Presiding Judge") == PartyType.JUDGE
        assert scraper.parse_party_type("Witness") == PartyType.WITNESS
        assert scraper.parse_party_type("Unknown Role") == PartyType.OTHER

    def test_normalize_case_number(self, scraper):
        """Test normalizing case numbers"""
        assert scraper.normalize_case_number("2024-cv-001234") == "2024-CV-001234"
        assert scraper.normalize_case_number("2024 - cv - 001234") == "2024-CV-001234"
        assert scraper.normalize_case_number("2024 / cv / 001234") == "2024/CV/001234"
        assert (
            scraper.normalize_case_number("  spaces  in  number  ")
            == "SPACES IN NUMBER"
        )

    def test_parse_amount_valid(self, scraper):
        """Test parsing valid amounts"""
        assert scraper.parse_amount("$1,234.56") == 1234.56
        assert scraper.parse_amount("$ 1,000,000") == 1000000.0
        assert scraper.parse_amount("500.00") == 500.0
        assert scraper.parse_amount("100") == 100.0

    def test_parse_amount_invalid(self, scraper):
        """Test parsing invalid amounts"""
        assert scraper.parse_amount("") is None
        assert scraper.parse_amount(None) is None
        assert scraper.parse_amount("not a number") is None

    def test_parse_date_valid(self, scraper):
        """Test parsing valid dates"""
        assert scraper.parse_date("2024-01-15") == date(2024, 1, 15)
        assert scraper.parse_date("01/15/2024") == date(2024, 1, 15)
        assert scraper.parse_date("01-15-2024") == date(2024, 1, 15)
        assert scraper.parse_date("20240115") == date(2024, 1, 15)
        assert scraper.parse_date("15-Jan-2024") == date(2024, 1, 15)
        assert scraper.parse_date("January 15, 2024") == date(2024, 1, 15)

    def test_parse_date_invalid(self, scraper):
        """Test parsing invalid dates"""
        assert scraper.parse_date("") is None
        assert scraper.parse_date(None) is None
        assert scraper.parse_date("not a date") is None

    def test_get_statistics(self, scraper):
        """Test getting scraper statistics"""
        stats = scraper.get_statistics()
        assert stats["jurisdiction"] == "CA"
        assert stats["scraper_class"] == "StateCourtScraper"


class TestStateCourtScraper:
    """Tests for StateCourtScraper implementation"""

    def test_initialization(self):
        """Test StateCourtScraper initialization"""
        config = {
            "base_url": "https://courts.ca.gov",
            "court_api": "https://api.courts.ca.gov",
        }
        scraper = StateCourtScraper("CA", config=config)
        assert scraper.state_code == "CA"
        assert scraper.base_url == "https://courts.ca.gov"
        assert scraper.court_api == "https://api.courts.ca.gov"

    def test_initialization_without_config(self):
        """Test StateCourtScraper initialization without config"""
        scraper = StateCourtScraper("TX")
        assert scraper.state_code == "TX"
        assert scraper.base_url == ""
        assert scraper.court_api == ""

    def test_initialization_lowercase_state(self):
        """Test that state code is uppercased"""
        scraper = StateCourtScraper("ca")
        assert scraper.state_code == "CA"

    def test_search_cases(self):
        """Test search_cases method returns empty list (placeholder)"""
        scraper = StateCourtScraper("CA")
        search = CaseSearch(party_name="John Doe")
        results = scraper.search_cases(search)
        assert results == []

    def test_search_by_party(self):
        """Test search_by_party method returns empty list (placeholder)"""
        scraper = StateCourtScraper("CA")
        search = PartySearch(name="John Doe")
        results = scraper.search_by_party(search)
        assert results == []

    def test_get_case_details(self):
        """Test get_case_details method returns None (placeholder)"""
        scraper = StateCourtScraper("CA")
        result = scraper.get_case_details("2024-CV-001234")
        assert result is None


class TestSearchCourtRecordsFunction:
    """Tests for search_court_records convenience function"""

    def test_basic_search(self):
        """Test basic court records search"""
        results = search_court_records("John Doe")
        assert isinstance(results, list)

    def test_search_with_filters(self):
        """Test court records search with filters"""
        results = search_court_records(
            party_name="John Doe",
            states=["CA", "TX"],
            case_types=[CaseType.CIVIL, CaseType.CRIMINAL],
            date_from=date(2024, 1, 1),
            date_to=date(2024, 12, 31),
        )
        assert isinstance(results, list)


class TestCourtRecordsImports:
    """Tests for module imports"""

    def test_all_exports_available(self):
        """Test that all expected exports are available"""
        from datagod.scrapers.categories.court_records import (
            CaseParty,
            CaseSearch,
            CaseStatus,
            CaseType,
            CourtCase,
            CourtRecordsScraper,
            PartySearch,
            PartyType,
            StateCourtScraper,
            search_court_records,
        )

        # All imports should succeed
        assert CaseType is not None
        assert CaseStatus is not None
        assert PartyType is not None
        assert CaseParty is not None
        assert CourtCase is not None


class TestCourtRecordsEdgeCases:
    """Edge case tests for court records module"""

    def test_empty_parties_list(self):
        """Test court case with empty parties"""
        case = CourtCase(
            case_number="2024-CV-001234",
            case_type=CaseType.CIVIL,
            court_name="Superior Court",
        )
        assert case.plaintiffs == []
        assert case.defendants == []

    def test_case_with_only_plaintiffs(self):
        """Test court case with only plaintiffs"""
        parties = [
            CaseParty(name="John Doe", party_type=PartyType.PLAINTIFF),
            CaseParty(name="Jane Doe", party_type=PartyType.PLAINTIFF),
        ]
        case = CourtCase(
            case_number="2024-CV-001234",
            case_type=CaseType.CIVIL,
            court_name="Superior Court",
            parties=parties,
        )
        assert len(case.plaintiffs) == 2
        assert len(case.defendants) == 0

    def test_party_with_special_characters(self):
        """Test party name with special characters"""
        party = CaseParty(
            name="O'Brien & Associates, LLC", party_type=PartyType.PLAINTIFF
        )
        assert party.name == "O'Brien & Associates, LLC"
        result = party.to_dict()
        assert result["name"] == "O'Brien & Associates, LLC"

    def test_court_case_null_dates(self):
        """Test court case to_dict with null dates"""
        case = CourtCase(
            case_number="2024-CV-001234",
            case_type=CaseType.CIVIL,
            court_name="Superior Court",
        )
        result = case.to_dict()
        assert result["filing_date"] is None
        assert result["disposition_date"] is None

    def test_case_type_priority(self):
        """Test that criminal takes precedence over civil in classification"""
        scraper = StateCourtScraper("CA")
        # Criminal keywords should be checked first
        result = scraper.classify_case_type("Criminal Felony Civil Case")
        assert result == CaseType.CRIMINAL
