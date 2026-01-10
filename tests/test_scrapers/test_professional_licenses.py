"""
Tests for datagod/scrapers/categories/professional_licenses.py

Comprehensive tests for Professional Licenses Scraper Module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime


class TestLicenseTypeEnum:
    """Tests for LicenseType enum"""

    def test_license_type_exists(self):
        """Test that LicenseType enum exists"""
        from datagod.scrapers.categories.professional_licenses import LicenseType
        assert LicenseType is not None

    def test_real_estate_types(self):
        """Test real estate license types"""
        from datagod.scrapers.categories.professional_licenses import LicenseType
        assert hasattr(LicenseType, 'REAL_ESTATE_AGENT')
        assert hasattr(LicenseType, 'REAL_ESTATE_BROKER')
        assert hasattr(LicenseType, 'REAL_ESTATE_APPRAISER')

    def test_mortgage_types(self):
        """Test mortgage license types"""
        from datagod.scrapers.categories.professional_licenses import LicenseType
        assert hasattr(LicenseType, 'LOAN_OFFICER')
        assert hasattr(LicenseType, 'MORTGAGE_BROKER')
        assert hasattr(LicenseType, 'MORTGAGE_LENDER')

    def test_legal_types(self):
        """Test legal license types"""
        from datagod.scrapers.categories.professional_licenses import LicenseType
        assert hasattr(LicenseType, 'ATTORNEY')
        assert hasattr(LicenseType, 'NOTARY')

    def test_construction_types(self):
        """Test construction license types"""
        from datagod.scrapers.categories.professional_licenses import LicenseType
        assert hasattr(LicenseType, 'GENERAL_CONTRACTOR')
        assert hasattr(LicenseType, 'ELECTRICIAN')
        assert hasattr(LicenseType, 'PLUMBER')

    def test_healthcare_types(self):
        """Test healthcare license types"""
        from datagod.scrapers.categories.professional_licenses import LicenseType
        assert hasattr(LicenseType, 'PHYSICIAN')
        assert hasattr(LicenseType, 'NURSE')
        assert hasattr(LicenseType, 'DENTIST')

    def test_financial_types(self):
        """Test financial license types"""
        from datagod.scrapers.categories.professional_licenses import LicenseType
        assert hasattr(LicenseType, 'CPA')
        assert hasattr(LicenseType, 'INSURANCE_AGENT')


class TestLicenseStatusEnum:
    """Tests for LicenseStatus enum"""

    def test_license_status_exists(self):
        """Test that LicenseStatus enum exists"""
        from datagod.scrapers.categories.professional_licenses import LicenseStatus
        assert LicenseStatus is not None

    def test_all_statuses_defined(self):
        """Test all status values are defined"""
        from datagod.scrapers.categories.professional_licenses import LicenseStatus
        expected = ['ACTIVE', 'INACTIVE', 'EXPIRED', 'SUSPENDED', 'REVOKED',
                   'SURRENDERED', 'PENDING', 'PROBATION', 'DECEASED', 'UNKNOWN']
        for status in expected:
            assert hasattr(LicenseStatus, status), f"Missing status: {status}"


class TestDisciplinaryAction:
    """Tests for DisciplinaryAction dataclass"""

    def test_disciplinary_action_exists(self):
        """Test that DisciplinaryAction class exists"""
        from datagod.scrapers.categories.professional_licenses import DisciplinaryAction
        assert DisciplinaryAction is not None

    def test_create_disciplinary_action(self):
        """Test creating a DisciplinaryAction"""
        from datagod.scrapers.categories.professional_licenses import DisciplinaryAction

        action = DisciplinaryAction(
            action_date=date(2024, 1, 15),
            action_type='Warning',
            description='Minor violation',
            case_number='DA-2024-001'
        )

        assert action.action_date == date(2024, 1, 15)
        assert action.action_type == 'Warning'

    def test_to_dict(self):
        """Test DisciplinaryAction.to_dict()"""
        from datagod.scrapers.categories.professional_licenses import DisciplinaryAction

        action = DisciplinaryAction(
            action_date=date(2024, 1, 15),
            action_type='Suspension',
            fine_amount=500.0
        )

        result = action.to_dict()
        assert isinstance(result, dict)
        assert result['action_type'] == 'Suspension'
        assert result['fine_amount'] == 500.0


class TestEmployer:
    """Tests for Employer dataclass"""

    def test_employer_exists(self):
        """Test that Employer class exists"""
        from datagod.scrapers.categories.professional_licenses import Employer
        assert Employer is not None

    def test_create_employer(self):
        """Test creating an Employer"""
        from datagod.scrapers.categories.professional_licenses import Employer

        employer = Employer(
            name='ABC Realty',
            address='123 Main St',
            city='Houston',
            state='TX',
            zip_code='77001'
        )

        assert employer.name == 'ABC Realty'
        assert employer.state == 'TX'

    def test_employer_to_dict(self):
        """Test Employer.to_dict()"""
        from datagod.scrapers.categories.professional_licenses import Employer

        employer = Employer(
            name='XYZ Bank',
            city='Austin'
        )

        result = employer.to_dict()
        assert isinstance(result, dict)
        assert result['name'] == 'XYZ Bank'
        assert result['city'] == 'Austin'


class TestProfessionalLicense:
    """Tests for ProfessionalLicense dataclass"""

    def test_professional_license_exists(self):
        """Test that ProfessionalLicense class exists"""
        from datagod.scrapers.categories.professional_licenses import ProfessionalLicense
        assert ProfessionalLicense is not None

    def test_create_professional_license(self):
        """Test creating a ProfessionalLicense"""
        from datagod.scrapers.categories.professional_licenses import (
            ProfessionalLicense, LicenseType, LicenseStatus
        )

        license = ProfessionalLicense(
            license_number='RE12345',
            license_type=LicenseType.REAL_ESTATE_AGENT,
            licensee_name='John Doe',
            state='TX',
            status=LicenseStatus.ACTIVE
        )

        assert license.license_number == 'RE12345'
        assert license.license_type == LicenseType.REAL_ESTATE_AGENT
        assert license.licensee_name == 'John Doe'

    def test_to_dict(self):
        """Test ProfessionalLicense.to_dict()"""
        from datagod.scrapers.categories.professional_licenses import (
            ProfessionalLicense, LicenseType, LicenseStatus
        )

        license = ProfessionalLicense(
            license_number='ATT99999',
            license_type=LicenseType.ATTORNEY,
            licensee_name='Jane Smith',
            state='CA',
            status=LicenseStatus.ACTIVE,
            bar_number='123456'
        )

        result = license.to_dict()
        assert isinstance(result, dict)
        assert result['license_number'] == 'ATT99999'
        assert result['state'] == 'CA'
        assert result['bar_number'] == '123456'

    def test_is_active_property_true(self):
        """Test is_active property when license is active"""
        from datagod.scrapers.categories.professional_licenses import (
            ProfessionalLicense, LicenseType, LicenseStatus
        )
        from datetime import date, timedelta

        license = ProfessionalLicense(
            license_number='LO12345',
            license_type=LicenseType.LOAN_OFFICER,
            licensee_name='John Doe',
            state='FL',
            status=LicenseStatus.ACTIVE,
            expiration_date=date.today() + timedelta(days=365)
        )

        assert license.is_active is True

    def test_is_active_property_false_expired(self):
        """Test is_active property when license is expired"""
        from datagod.scrapers.categories.professional_licenses import (
            ProfessionalLicense, LicenseType, LicenseStatus
        )
        from datetime import date, timedelta

        license = ProfessionalLicense(
            license_number='LO12345',
            license_type=LicenseType.LOAN_OFFICER,
            licensee_name='John Doe',
            state='FL',
            status=LicenseStatus.ACTIVE,
            expiration_date=date.today() - timedelta(days=30)
        )

        assert license.is_active is False

    def test_is_active_property_false_status(self):
        """Test is_active property when status is not active"""
        from datagod.scrapers.categories.professional_licenses import (
            ProfessionalLicense, LicenseType, LicenseStatus
        )

        license = ProfessionalLicense(
            license_number='LO12345',
            license_type=LicenseType.LOAN_OFFICER,
            licensee_name='John Doe',
            state='FL',
            status=LicenseStatus.SUSPENDED
        )

        assert license.is_active is False

    def test_has_disciplinary_history_false(self):
        """Test has_disciplinary_history when no actions"""
        from datagod.scrapers.categories.professional_licenses import (
            ProfessionalLicense, LicenseType, LicenseStatus
        )

        license = ProfessionalLicense(
            license_number='LO12345',
            license_type=LicenseType.LOAN_OFFICER,
            licensee_name='John Doe',
            state='FL',
            status=LicenseStatus.ACTIVE
        )

        assert license.has_disciplinary_history is False

    def test_has_disciplinary_history_true(self):
        """Test has_disciplinary_history when actions exist"""
        from datagod.scrapers.categories.professional_licenses import (
            ProfessionalLicense, LicenseType, LicenseStatus, DisciplinaryAction
        )

        license = ProfessionalLicense(
            license_number='LO12345',
            license_type=LicenseType.LOAN_OFFICER,
            licensee_name='John Doe',
            state='FL',
            status=LicenseStatus.ACTIVE,
            disciplinary_actions=[
                DisciplinaryAction(action_date=date(2023, 1, 1), action_type='Warning')
            ]
        )

        assert license.has_disciplinary_history is True


class TestLicenseSearch:
    """Tests for LicenseSearch dataclass"""

    def test_license_search_exists(self):
        """Test that LicenseSearch class exists"""
        from datagod.scrapers.categories.professional_licenses import LicenseSearch
        assert LicenseSearch is not None

    def test_create_license_search(self):
        """Test creating a LicenseSearch"""
        from datagod.scrapers.categories.professional_licenses import LicenseSearch, LicenseType

        search = LicenseSearch(
            name='John Doe',
            license_type=LicenseType.REAL_ESTATE_AGENT,
            state='TX',
            include_inactive=False
        )

        assert search.name == 'John Doe'
        assert search.license_type == LicenseType.REAL_ESTATE_AGENT
        assert search.state == 'TX'


class TestProfessionalLicensesScraper:
    """Tests for ProfessionalLicensesScraper abstract base class"""

    def test_base_scraper_exists(self):
        """Test that ProfessionalLicensesScraper class exists"""
        from datagod.scrapers.categories.professional_licenses import ProfessionalLicensesScraper
        assert ProfessionalLicensesScraper is not None

    def test_base_scraper_is_abstract(self):
        """Test that ProfessionalLicensesScraper is abstract"""
        from abc import ABC
        from datagod.scrapers.categories.professional_licenses import ProfessionalLicensesScraper
        assert issubclass(ProfessionalLicensesScraper, ABC)

    def test_abstract_methods_defined(self):
        """Test that abstract methods are defined"""
        from datagod.scrapers.categories.professional_licenses import ProfessionalLicensesScraper
        assert hasattr(ProfessionalLicensesScraper, 'search_licenses')
        assert hasattr(ProfessionalLicensesScraper, 'get_license_details')
        assert hasattr(ProfessionalLicensesScraper, 'verify_license')


class TestStateLicenseBoardScraper:
    """Tests for StateLicenseBoardScraper class"""

    def test_state_license_board_scraper_exists(self):
        """Test that StateLicenseBoardScraper class exists"""
        from datagod.scrapers.categories.professional_licenses import StateLicenseBoardScraper
        assert StateLicenseBoardScraper is not None

    def test_state_license_board_scraper_inherits(self):
        """Test that StateLicenseBoardScraper inherits from base"""
        from datagod.scrapers.categories.professional_licenses import (
            StateLicenseBoardScraper, ProfessionalLicensesScraper
        )
        assert issubclass(StateLicenseBoardScraper, ProfessionalLicensesScraper)

    def test_create_state_license_board_scraper(self):
        """Test creating a StateLicenseBoardScraper"""
        from datagod.scrapers.categories.professional_licenses import (
            StateLicenseBoardScraper, LicenseType
        )

        scraper = StateLicenseBoardScraper(
            state_code='TX',
            license_type=LicenseType.REAL_ESTATE_AGENT,
            config={'base_url': 'https://example.com'}
        )

        assert scraper.state_code == 'TX'
        assert scraper.license_type == LicenseType.REAL_ESTATE_AGENT

    def test_search_licenses_returns_list(self):
        """Test that search_licenses returns a list"""
        from datagod.scrapers.categories.professional_licenses import (
            StateLicenseBoardScraper, LicenseType, LicenseSearch
        )

        scraper = StateLicenseBoardScraper(
            state_code='TX',
            license_type=LicenseType.REAL_ESTATE_AGENT
        )

        result = scraper.search_licenses(LicenseSearch(name='John'))
        assert isinstance(result, list)


class TestNMLSScraper:
    """Tests for NMLSScraper class"""

    def test_nmls_scraper_exists(self):
        """Test that NMLSScraper class exists"""
        from datagod.scrapers.categories.professional_licenses import NMLSScraper
        assert NMLSScraper is not None

    def test_nmls_scraper_inherits(self):
        """Test that NMLSScraper inherits from base"""
        from datagod.scrapers.categories.professional_licenses import (
            NMLSScraper, ProfessionalLicensesScraper
        )
        assert issubclass(NMLSScraper, ProfessionalLicensesScraper)

    def test_nmls_base_url(self):
        """Test that NMLS_BASE_URL is defined"""
        from datagod.scrapers.categories.professional_licenses import NMLSScraper
        assert hasattr(NMLSScraper, 'NMLS_BASE_URL')
        assert 'nmlsconsumeraccess' in NMLSScraper.NMLS_BASE_URL

    def test_create_nmls_scraper(self):
        """Test creating an NMLSScraper"""
        from datagod.scrapers.categories.professional_licenses import NMLSScraper

        scraper = NMLSScraper()
        assert scraper.state_code is None

    def test_search_by_nmls_id(self):
        """Test search_by_nmls_id method exists"""
        from datagod.scrapers.categories.professional_licenses import NMLSScraper
        assert hasattr(NMLSScraper, 'search_by_nmls_id')


class TestHelperMethods:
    """Tests for helper methods in ProfessionalLicensesScraper"""

    @pytest.fixture
    def scraper(self):
        """Create a concrete scraper for testing"""
        from datagod.scrapers.categories.professional_licenses import (
            StateLicenseBoardScraper, LicenseType
        )
        return StateLicenseBoardScraper(
            state_code='TX',
            license_type=LicenseType.REAL_ESTATE_AGENT
        )

    def test_parse_license_status_active(self, scraper):
        """Test parsing active status"""
        from datagod.scrapers.categories.professional_licenses import LicenseStatus

        result = scraper.parse_license_status('Active')
        assert result == LicenseStatus.ACTIVE

        result = scraper.parse_license_status('Good Standing')
        assert result == LicenseStatus.ACTIVE

    def test_parse_license_status_suspended(self, scraper):
        """Test parsing suspended status"""
        from datagod.scrapers.categories.professional_licenses import LicenseStatus

        result = scraper.parse_license_status('Suspended')
        assert result == LicenseStatus.SUSPENDED

    def test_parse_license_status_unknown(self, scraper):
        """Test parsing unknown status"""
        from datagod.scrapers.categories.professional_licenses import LicenseStatus

        result = scraper.parse_license_status('Some Random Status')
        assert result == LicenseStatus.UNKNOWN

    def test_classify_license_type_real_estate(self, scraper):
        """Test classifying real estate license types"""
        from datagod.scrapers.categories.professional_licenses import LicenseType

        result = scraper.classify_license_type('Real Estate Agent')
        assert result == LicenseType.REAL_ESTATE_AGENT

        result = scraper.classify_license_type('Real Estate Broker')
        assert result == LicenseType.REAL_ESTATE_BROKER

    def test_classify_license_type_mortgage(self, scraper):
        """Test classifying mortgage license types"""
        from datagod.scrapers.categories.professional_licenses import LicenseType

        result = scraper.classify_license_type('Loan Officer')
        assert result == LicenseType.LOAN_OFFICER

        result = scraper.classify_license_type('Mortgage Loan Originator')
        assert result == LicenseType.LOAN_OFFICER

    def test_classify_license_type_legal(self, scraper):
        """Test classifying legal license types"""
        from datagod.scrapers.categories.professional_licenses import LicenseType

        result = scraper.classify_license_type('Attorney')
        assert result == LicenseType.ATTORNEY

        result = scraper.classify_license_type('Notary Public')
        assert result == LicenseType.NOTARY

    def test_normalize_name(self, scraper):
        """Test name normalization"""
        result = scraper.normalize_name('John Smith Jr.')
        assert 'Jr' not in result

        result = scraper.normalize_name('Jane Doe  MD')
        assert result.strip() == 'Jane Doe'

    def test_parse_date_formats(self, scraper):
        """Test parsing various date formats"""
        result = scraper.parse_date('2024-01-15')
        assert result == date(2024, 1, 15)

        result = scraper.parse_date('01/15/2024')
        assert result == date(2024, 1, 15)

    def test_parse_date_invalid(self, scraper):
        """Test parsing invalid date"""
        result = scraper.parse_date('not a date')
        assert result is None

        result = scraper.parse_date('')
        assert result is None


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_verify_professional_license_exists(self):
        """Test that verify_professional_license function exists"""
        from datagod.scrapers.categories.professional_licenses import verify_professional_license
        assert callable(verify_professional_license)

    def test_verify_professional_license_returns_dict(self):
        """Test that verify_professional_license returns a dict"""
        from datagod.scrapers.categories.professional_licenses import (
            verify_professional_license, LicenseType
        )

        result = verify_professional_license(
            license_number='RE12345',
            license_type=LicenseType.REAL_ESTATE_AGENT,
            state='TX'
        )

        assert isinstance(result, dict)
        assert 'license_number' in result
        assert 'verified' in result

    def test_search_professional_licenses_exists(self):
        """Test that search_professional_licenses function exists"""
        from datagod.scrapers.categories.professional_licenses import search_professional_licenses
        assert callable(search_professional_licenses)

    def test_search_professional_licenses_returns_list(self):
        """Test that search_professional_licenses returns a list"""
        from datagod.scrapers.categories.professional_licenses import search_professional_licenses

        result = search_professional_licenses(
            name='John Doe',
            states=['TX', 'CA']
        )

        assert isinstance(result, list)
