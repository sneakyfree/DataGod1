"""
Tests for datagod/scrapers/categories/federal_sources.py

Comprehensive tests for the federal data sources module including
USPTO, SEC EDGAR, FDIC, Census, FHFA, and BLS data structures.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, date


class TestTrademarkStatusEnum:
    """Tests for TrademarkStatus enum"""

    def test_trademark_status_exists(self):
        """Test that TrademarkStatus enum exists"""
        from datagod.scrapers.categories.federal_sources import TrademarkStatus
        assert TrademarkStatus is not None

    def test_all_statuses_defined(self):
        """Test all expected trademark statuses are defined"""
        from datagod.scrapers.categories.federal_sources import TrademarkStatus
        expected = ['REGISTERED', 'PENDING', 'ABANDONED', 'CANCELLED',
                   'EXPIRED', 'OPPOSED', 'UNKNOWN']
        for status in expected:
            assert hasattr(TrademarkStatus, status)

    def test_registered_value(self):
        """Test REGISTERED status value"""
        from datagod.scrapers.categories.federal_sources import TrademarkStatus
        assert TrademarkStatus.REGISTERED.value == "registered"


class TestPatentTypeEnum:
    """Tests for PatentType enum"""

    def test_patent_type_exists(self):
        """Test that PatentType enum exists"""
        from datagod.scrapers.categories.federal_sources import PatentType
        assert PatentType is not None

    def test_all_types_defined(self):
        """Test all expected patent types are defined"""
        from datagod.scrapers.categories.federal_sources import PatentType
        expected = ['UTILITY', 'DESIGN', 'PLANT', 'REISSUE', 'PROVISIONAL', 'UNKNOWN']
        for pt in expected:
            assert hasattr(PatentType, pt)


class TestPatentStatusEnum:
    """Tests for PatentStatus enum"""

    def test_patent_status_exists(self):
        """Test that PatentStatus enum exists"""
        from datagod.scrapers.categories.federal_sources import PatentStatus
        assert PatentStatus is not None

    def test_all_statuses_defined(self):
        """Test all expected patent statuses are defined"""
        from datagod.scrapers.categories.federal_sources import PatentStatus
        expected = ['ACTIVE', 'EXPIRED', 'PENDING', 'ABANDONED', 'UNKNOWN']
        for status in expected:
            assert hasattr(PatentStatus, status)


class TestTrademark:
    """Tests for Trademark dataclass"""

    def test_trademark_exists(self):
        """Test that Trademark dataclass exists"""
        from datagod.scrapers.categories.federal_sources import Trademark
        assert Trademark is not None

    def test_create_trademark(self):
        """Test creating a Trademark"""
        from datagod.scrapers.categories.federal_sources import Trademark
        tm = Trademark(serial_number='12345678')
        assert tm.serial_number == '12345678'

    def test_trademark_to_dict(self):
        """Test Trademark to_dict method"""
        from datagod.scrapers.categories.federal_sources import Trademark, TrademarkStatus
        tm = Trademark(
            serial_number='12345678',
            registration_number='9876543',
            mark_text='TEST MARK',
            status=TrademarkStatus.REGISTERED
        )
        result = tm.to_dict()
        assert result['serial_number'] == '12345678'
        assert result['registration_number'] == '9876543'
        assert result['mark_text'] == 'TEST MARK'
        assert result['status'] == 'registered'


class TestPatent:
    """Tests for Patent dataclass"""

    def test_patent_exists(self):
        """Test that Patent dataclass exists"""
        from datagod.scrapers.categories.federal_sources import Patent
        assert Patent is not None

    def test_create_patent(self):
        """Test creating a Patent"""
        from datagod.scrapers.categories.federal_sources import Patent
        patent = Patent(patent_number='US10000000')
        assert patent.patent_number == 'US10000000'

    def test_patent_to_dict(self):
        """Test Patent to_dict method"""
        from datagod.scrapers.categories.federal_sources import Patent, PatentType, PatentStatus
        patent = Patent(
            patent_number='US10000000',
            title='Test Patent',
            patent_type=PatentType.UTILITY,
            status=PatentStatus.ACTIVE
        )
        result = patent.to_dict()
        assert result['patent_number'] == 'US10000000'
        assert result['title'] == 'Test Patent'
        assert result['patent_type'] == 'utility'
        assert result['status'] == 'active'


class TestTrademarkSearch:
    """Tests for TrademarkSearch dataclass"""

    def test_trademark_search_exists(self):
        """Test that TrademarkSearch dataclass exists"""
        from datagod.scrapers.categories.federal_sources import TrademarkSearch
        assert TrademarkSearch is not None

    def test_create_trademark_search(self):
        """Test creating a TrademarkSearch"""
        from datagod.scrapers.categories.federal_sources import TrademarkSearch
        search = TrademarkSearch(mark_text='TEST')
        assert search.mark_text == 'TEST'


class TestPatentSearch:
    """Tests for PatentSearch dataclass"""

    def test_patent_search_exists(self):
        """Test that PatentSearch dataclass exists"""
        from datagod.scrapers.categories.federal_sources import PatentSearch
        assert PatentSearch is not None

    def test_create_patent_search(self):
        """Test creating a PatentSearch"""
        from datagod.scrapers.categories.federal_sources import PatentSearch
        search = PatentSearch(inventor_name='John Doe')
        assert search.inventor_name == 'John Doe'


class TestUSPTOScraper:
    """Tests for USPTOScraper abstract class"""

    def test_uspto_scraper_exists(self):
        """Test that USPTOScraper class exists"""
        from datagod.scrapers.categories.federal_sources import USPTOScraper
        assert USPTOScraper is not None

    def test_uspto_scraper_is_abstract(self):
        """Test that USPTOScraper is abstract"""
        from datagod.scrapers.categories.federal_sources import USPTOScraper
        from abc import ABC
        assert issubclass(USPTOScraper, ABC)

    def test_uspto_scraper_base_url(self):
        """Test USPTOScraper BASE_URL"""
        from datagod.scrapers.categories.federal_sources import USPTOScraper
        assert USPTOScraper.BASE_URL == "https://developer.uspto.gov/ibd-api/v1"

    def test_parse_trademark_status(self):
        """Test parse_trademark_status method"""
        from datagod.scrapers.categories.federal_sources import USPTOScraper, TrademarkStatus

        class ConcreteScraper(USPTOScraper):
            def search_trademarks(self, search):
                return []
            def get_trademark_details(self, serial_number):
                return None
            def search_patents(self, search):
                return []
            def get_patent_details(self, patent_number):
                return None

        scraper = ConcreteScraper()

        assert scraper.parse_trademark_status('Registered') == TrademarkStatus.REGISTERED
        assert scraper.parse_trademark_status('PENDING') == TrademarkStatus.PENDING
        assert scraper.parse_trademark_status('abandoned') == TrademarkStatus.ABANDONED
        assert scraper.parse_trademark_status('unknown status') == TrademarkStatus.UNKNOWN


class TestSECFilingTypeEnum:
    """Tests for SECFilingType enum"""

    def test_sec_filing_type_exists(self):
        """Test that SECFilingType enum exists"""
        from datagod.scrapers.categories.federal_sources import SECFilingType
        assert SECFilingType is not None

    def test_all_filing_types_defined(self):
        """Test all expected filing types are defined"""
        from datagod.scrapers.categories.federal_sources import SECFilingType
        expected = ['FORM_10K', 'FORM_10Q', 'FORM_8K', 'FORM_4', 'FORM_S1',
                   'FORM_DEF14A', 'FORM_13F', 'FORM_13D', 'FORM_13G',
                   'FORM_144', 'OTHER']
        for ft in expected:
            assert hasattr(SECFilingType, ft)


class TestSECFiling:
    """Tests for SECFiling dataclass"""

    def test_sec_filing_exists(self):
        """Test that SECFiling dataclass exists"""
        from datagod.scrapers.categories.federal_sources import SECFiling
        assert SECFiling is not None

    def test_create_sec_filing(self):
        """Test creating an SECFiling"""
        from datagod.scrapers.categories.federal_sources import SECFiling, SECFilingType
        filing = SECFiling(
            accession_number='0000000000-00-000001',
            form_type=SECFilingType.FORM_10K,
            filing_date=date.today()
        )
        assert filing.accession_number == '0000000000-00-000001'
        assert filing.form_type == SECFilingType.FORM_10K

    def test_sec_filing_to_dict(self):
        """Test SECFiling to_dict method"""
        from datagod.scrapers.categories.federal_sources import SECFiling, SECFilingType
        filing = SECFiling(
            accession_number='0000000000-00-000001',
            form_type=SECFilingType.FORM_10K,
            filing_date=date.today(),
            company_name='Test Corp'
        )
        result = filing.to_dict()
        assert result['accession_number'] == '0000000000-00-000001'
        assert result['form_type'] == '10-K'
        assert result['company_name'] == 'Test Corp'


class TestSECCompany:
    """Tests for SECCompany dataclass"""

    def test_sec_company_exists(self):
        """Test that SECCompany dataclass exists"""
        from datagod.scrapers.categories.federal_sources import SECCompany
        assert SECCompany is not None

    def test_create_sec_company(self):
        """Test creating an SECCompany"""
        from datagod.scrapers.categories.federal_sources import SECCompany
        company = SECCompany(cik='0000000001', company_name='Test Corp')
        assert company.cik == '0000000001'
        assert company.company_name == 'Test Corp'

    def test_sec_company_to_dict(self):
        """Test SECCompany to_dict method"""
        from datagod.scrapers.categories.federal_sources import SECCompany
        company = SECCompany(
            cik='0000000001',
            company_name='Test Corp',
            ticker='TEST'
        )
        result = company.to_dict()
        assert result['cik'] == '0000000001'
        assert result['company_name'] == 'Test Corp'
        assert result['ticker'] == 'TEST'


class TestSECEdgarScraper:
    """Tests for SECEdgarScraper abstract class"""

    def test_sec_edgar_scraper_exists(self):
        """Test that SECEdgarScraper class exists"""
        from datagod.scrapers.categories.federal_sources import SECEdgarScraper
        assert SECEdgarScraper is not None

    def test_sec_edgar_scraper_base_url(self):
        """Test SECEdgarScraper BASE_URL"""
        from datagod.scrapers.categories.federal_sources import SECEdgarScraper
        assert SECEdgarScraper.BASE_URL == "https://data.sec.gov"

    def test_normalize_cik(self):
        """Test normalize_cik method"""
        from datagod.scrapers.categories.federal_sources import SECEdgarScraper

        class ConcreteScraper(SECEdgarScraper):
            def search_filings(self, search):
                return []
            def get_company_filings(self, cik, form_types=None):
                return []
            def get_company_info(self, cik):
                return None
            def search_companies(self, name):
                return []

        scraper = ConcreteScraper()
        assert scraper.normalize_cik('123') == '0000000123'
        assert scraper.normalize_cik('CIK-456') == '0000000456'

    def test_parse_form_type(self):
        """Test parse_form_type method"""
        from datagod.scrapers.categories.federal_sources import SECEdgarScraper, SECFilingType

        class ConcreteScraper(SECEdgarScraper):
            def search_filings(self, search):
                return []
            def get_company_filings(self, cik, form_types=None):
                return []
            def get_company_info(self, cik):
                return None
            def search_companies(self, name):
                return []

        scraper = ConcreteScraper()
        assert scraper.parse_form_type('10-K') == SECFilingType.FORM_10K
        assert scraper.parse_form_type('10Q') == SECFilingType.FORM_10Q
        assert scraper.parse_form_type('8-K') == SECFilingType.FORM_8K
        assert scraper.parse_form_type('UNKNOWN') == SECFilingType.OTHER


class TestBankStatusEnum:
    """Tests for BankStatus enum"""

    def test_bank_status_exists(self):
        """Test that BankStatus enum exists"""
        from datagod.scrapers.categories.federal_sources import BankStatus
        assert BankStatus is not None

    def test_all_statuses_defined(self):
        """Test all expected bank statuses are defined"""
        from datagod.scrapers.categories.federal_sources import BankStatus
        expected = ['ACTIVE', 'INACTIVE', 'FAILED', 'MERGED', 'UNKNOWN']
        for status in expected:
            assert hasattr(BankStatus, status)


class TestBank:
    """Tests for Bank dataclass"""

    def test_bank_exists(self):
        """Test that Bank dataclass exists"""
        from datagod.scrapers.categories.federal_sources import Bank
        assert Bank is not None

    def test_create_bank(self):
        """Test creating a Bank"""
        from datagod.scrapers.categories.federal_sources import Bank
        bank = Bank(fdic_cert='12345', bank_name='Test Bank')
        assert bank.fdic_cert == '12345'
        assert bank.bank_name == 'Test Bank'

    def test_bank_to_dict(self):
        """Test Bank to_dict method"""
        from datagod.scrapers.categories.federal_sources import Bank, BankStatus
        bank = Bank(
            fdic_cert='12345',
            bank_name='Test Bank',
            status=BankStatus.ACTIVE,
            headquarters_state='NY'
        )
        result = bank.to_dict()
        assert result['fdic_cert'] == '12345'
        assert result['bank_name'] == 'Test Bank'
        assert result['status'] == 'active'


class TestBankBranch:
    """Tests for BankBranch dataclass"""

    def test_bank_branch_exists(self):
        """Test that BankBranch dataclass exists"""
        from datagod.scrapers.categories.federal_sources import BankBranch
        assert BankBranch is not None

    def test_create_bank_branch(self):
        """Test creating a BankBranch"""
        from datagod.scrapers.categories.federal_sources import BankBranch
        branch = BankBranch(
            branch_number='001',
            branch_name='Main Branch',
            bank_fdic_cert='12345'
        )
        assert branch.branch_number == '001'
        assert branch.branch_name == 'Main Branch'

    def test_bank_branch_to_dict(self):
        """Test BankBranch to_dict method"""
        from datagod.scrapers.categories.federal_sources import BankBranch
        branch = BankBranch(
            branch_number='001',
            branch_name='Main Branch',
            bank_fdic_cert='12345',
            city='New York',
            state='NY'
        )
        result = branch.to_dict()
        assert result['branch_number'] == '001'
        assert result['city'] == 'New York'


class TestFDICScraper:
    """Tests for FDICScraper abstract class"""

    def test_fdic_scraper_exists(self):
        """Test that FDICScraper class exists"""
        from datagod.scrapers.categories.federal_sources import FDICScraper
        assert FDICScraper is not None

    def test_fdic_scraper_is_abstract(self):
        """Test that FDICScraper is abstract"""
        from datagod.scrapers.categories.federal_sources import FDICScraper
        from abc import ABC
        assert issubclass(FDICScraper, ABC)

    def test_fdic_scraper_base_url(self):
        """Test FDICScraper BASE_URL"""
        from datagod.scrapers.categories.federal_sources import FDICScraper
        assert FDICScraper.BASE_URL == "https://banks.data.fdic.gov/api"


class TestCensusData:
    """Tests for CensusData dataclass"""

    def test_census_data_exists(self):
        """Test that CensusData dataclass exists"""
        from datagod.scrapers.categories.federal_sources import CensusData
        assert CensusData is not None

    def test_create_census_data(self):
        """Test creating a CensusData"""
        from datagod.scrapers.categories.federal_sources import CensusData
        data = CensusData(
            geo_id='01',
            geo_name='Alabama',
            geo_type='state'
        )
        assert data.geo_id == '01'
        assert data.geo_name == 'Alabama'

    def test_census_data_to_dict(self):
        """Test CensusData to_dict method"""
        from datagod.scrapers.categories.federal_sources import CensusData
        data = CensusData(
            geo_id='01',
            geo_name='Alabama',
            geo_type='state',
            total_population=5000000
        )
        result = data.to_dict()
        assert result['geo_id'] == '01'
        assert result['total_population'] == 5000000


class TestCensusScraper:
    """Tests for CensusScraper abstract class"""

    def test_census_scraper_exists(self):
        """Test that CensusScraper class exists"""
        from datagod.scrapers.categories.federal_sources import CensusScraper
        assert CensusScraper is not None

    def test_census_scraper_base_url(self):
        """Test CensusScraper BASE_URL"""
        from datagod.scrapers.categories.federal_sources import CensusScraper
        assert CensusScraper.BASE_URL == "https://api.census.gov/data"

    def test_variable_mapping_defined(self):
        """Test VARIABLE_MAPPING is defined"""
        from datagod.scrapers.categories.federal_sources import CensusScraper
        assert hasattr(CensusScraper, 'VARIABLE_MAPPING')
        assert 'total_population' in CensusScraper.VARIABLE_MAPPING


class TestHousePriceIndex:
    """Tests for HousePriceIndex dataclass"""

    def test_house_price_index_exists(self):
        """Test that HousePriceIndex dataclass exists"""
        from datagod.scrapers.categories.federal_sources import HousePriceIndex
        assert HousePriceIndex is not None

    def test_create_house_price_index(self):
        """Test creating a HousePriceIndex"""
        from datagod.scrapers.categories.federal_sources import HousePriceIndex
        hpi = HousePriceIndex(
            geo_name='California',
            geo_type='state',
            period='2023-Q4',
            index_value=450.5
        )
        assert hpi.geo_name == 'California'
        assert hpi.index_value == 450.5

    def test_house_price_index_to_dict(self):
        """Test HousePriceIndex to_dict method"""
        from datagod.scrapers.categories.federal_sources import HousePriceIndex
        hpi = HousePriceIndex(
            geo_name='California',
            geo_type='state',
            period='2023-Q4',
            index_value=450.5,
            year_over_year_change=5.2
        )
        result = hpi.to_dict()
        assert result['geo_name'] == 'California'
        assert result['index_value'] == 450.5


class TestFHFAScraper:
    """Tests for FHFAScraper abstract class"""

    def test_fhfa_scraper_exists(self):
        """Test that FHFAScraper class exists"""
        from datagod.scrapers.categories.federal_sources import FHFAScraper
        assert FHFAScraper is not None

    def test_fhfa_scraper_is_abstract(self):
        """Test that FHFAScraper is abstract"""
        from datagod.scrapers.categories.federal_sources import FHFAScraper
        from abc import ABC
        assert issubclass(FHFAScraper, ABC)


class TestLaborStatistic:
    """Tests for LaborStatistic dataclass"""

    def test_labor_statistic_exists(self):
        """Test that LaborStatistic dataclass exists"""
        from datagod.scrapers.categories.federal_sources import LaborStatistic
        assert LaborStatistic is not None

    def test_create_labor_statistic(self):
        """Test creating a LaborStatistic"""
        from datagod.scrapers.categories.federal_sources import LaborStatistic
        stat = LaborStatistic(
            series_id='LNS14000000',
            series_title='Unemployment Rate',
            period='2023-12',
            value=3.7
        )
        assert stat.series_id == 'LNS14000000'
        assert stat.value == 3.7

    def test_labor_statistic_to_dict(self):
        """Test LaborStatistic to_dict method"""
        from datagod.scrapers.categories.federal_sources import LaborStatistic
        stat = LaborStatistic(
            series_id='LNS14000000',
            series_title='Unemployment Rate',
            period='2023-12',
            value=3.7
        )
        result = stat.to_dict()
        assert result['series_id'] == 'LNS14000000'
        assert result['value'] == 3.7


class TestUnemploymentData:
    """Tests for UnemploymentData dataclass"""

    def test_unemployment_data_exists(self):
        """Test that UnemploymentData dataclass exists"""
        from datagod.scrapers.categories.federal_sources import UnemploymentData
        assert UnemploymentData is not None

    def test_create_unemployment_data(self):
        """Test creating an UnemploymentData"""
        from datagod.scrapers.categories.federal_sources import UnemploymentData
        data = UnemploymentData(
            geo_name='California',
            geo_type='state',
            period='2023-12',
            unemployment_rate=4.5
        )
        assert data.geo_name == 'California'
        assert data.unemployment_rate == 4.5

    def test_unemployment_data_to_dict(self):
        """Test UnemploymentData to_dict method"""
        from datagod.scrapers.categories.federal_sources import UnemploymentData
        data = UnemploymentData(
            geo_name='California',
            geo_type='state',
            period='2023-12',
            unemployment_rate=4.5,
            labor_force=20000000
        )
        result = data.to_dict()
        assert result['geo_name'] == 'California'
        assert result['unemployment_rate'] == 4.5


class TestBLSScraper:
    """Tests for BLSScraper abstract class"""

    def test_bls_scraper_exists(self):
        """Test that BLSScraper class exists"""
        from datagod.scrapers.categories.federal_sources import BLSScraper
        assert BLSScraper is not None

    def test_bls_scraper_is_abstract(self):
        """Test that BLSScraper is abstract"""
        from datagod.scrapers.categories.federal_sources import BLSScraper
        from abc import ABC
        assert issubclass(BLSScraper, ABC)

    def test_bls_scraper_base_url(self):
        """Test BLSScraper BASE_URL"""
        from datagod.scrapers.categories.federal_sources import BLSScraper
        assert BLSScraper.BASE_URL == "https://api.bls.gov/publicAPI/v2"


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_search_trademarks_exists(self):
        """Test that search_trademarks function exists"""
        from datagod.scrapers.categories.federal_sources import search_trademarks
        assert callable(search_trademarks)

    def test_search_trademarks_returns_list(self):
        """Test search_trademarks returns a list"""
        from datagod.scrapers.categories.federal_sources import search_trademarks
        result = search_trademarks(mark_text='TEST')
        assert isinstance(result, list)

    def test_search_sec_filings_exists(self):
        """Test that search_sec_filings function exists"""
        from datagod.scrapers.categories.federal_sources import search_sec_filings
        assert callable(search_sec_filings)

    def test_search_sec_filings_returns_list(self):
        """Test search_sec_filings returns a list"""
        from datagod.scrapers.categories.federal_sources import search_sec_filings
        result = search_sec_filings(company_name='Test Corp')
        assert isinstance(result, list)

    def test_search_banks_exists(self):
        """Test that search_banks function exists"""
        from datagod.scrapers.categories.federal_sources import search_banks
        assert callable(search_banks)

    def test_search_banks_returns_list(self):
        """Test search_banks returns a list"""
        from datagod.scrapers.categories.federal_sources import search_banks
        result = search_banks(bank_name='Test Bank')
        assert isinstance(result, list)
