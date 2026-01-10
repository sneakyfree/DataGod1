"""
Comprehensive tests for ATTOM API module.

Tests cover:
- Enums (RiskLevel, SchoolType)
- Data classes (ATTOMProperty, SalesComparable, NeighborhoodData,
               SchoolInfo, HazardRisk, MarketTrend, ATTOMSearch)
- ATTOMAPI abstract class
- ATTOMAPIClient implementation
"""

import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from datagod.scrapers.paid.attom_api import (
    RiskLevel,
    SchoolType,
    ATTOMProperty,
    SalesComparable,
    NeighborhoodData,
    SchoolInfo,
    HazardRisk,
    MarketTrend,
    ATTOMSearch,
    ATTOMAPI,
    ATTOMAPIClient,
    create_attom_client,
)


class TestRiskLevelEnum:
    """Tests for RiskLevel enumeration"""

    def test_all_risk_levels_exist(self):
        """Verify all expected risk levels are defined"""
        expected_levels = ['VERY_LOW', 'LOW', 'MODERATE', 'HIGH', 'VERY_HIGH', 'UNKNOWN']
        for level in expected_levels:
            assert hasattr(RiskLevel, level)

    def test_risk_level_values(self):
        """Verify risk level string values"""
        assert RiskLevel.VERY_LOW.value == "very_low"
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MODERATE.value == "moderate"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.VERY_HIGH.value == "very_high"


class TestSchoolTypeEnum:
    """Tests for SchoolType enumeration"""

    def test_all_school_types_exist(self):
        """Verify all expected school types are defined"""
        expected_types = ['ELEMENTARY', 'MIDDLE', 'HIGH', 'COMBINED', 'PRIVATE', 'CHARTER', 'UNKNOWN']
        for school_type in expected_types:
            assert hasattr(SchoolType, school_type)

    def test_school_type_values(self):
        """Verify school type string values"""
        assert SchoolType.ELEMENTARY.value == "elementary"
        assert SchoolType.MIDDLE.value == "middle"
        assert SchoolType.HIGH.value == "high"


class TestATTOMProperty:
    """Tests for ATTOMProperty dataclass"""

    def test_create_minimal_property(self):
        """Test creating property with required fields"""
        prop = ATTOMProperty(
            attom_id="A123456",
            address="123 Main St",
            city="Houston",
            state="TX",
            zip_code="77001",
            county="Harris",
            fips="48201",
            property_type="SFR"
        )
        assert prop.attom_id == "A123456"
        assert prop.address == "123 Main St"
        assert prop.bedrooms is None
        assert prop.pool is False

    def test_create_full_property(self):
        """Test creating property with all fields"""
        prop = ATTOMProperty(
            attom_id="A123456",
            address="123 Main St",
            city="Houston",
            state="TX",
            zip_code="77001",
            county="Harris",
            fips="48201",
            apn="1234567890",
            property_type="SFR",
            lot_size_sqft=8500.0,
            building_sqft=2500.0,
            bedrooms=4,
            bathrooms=2.5,
            year_built=2010,
            stories=2,
            pool=True,
            assessed_value=350000.0,
            market_value=400000.0,
            last_sale_date=date(2020, 6, 15),
            last_sale_price=380000.0,
            latitude=29.7604,
            longitude=-95.3698
        )
        assert prop.bedrooms == 4
        assert prop.pool is True
        assert prop.last_sale_price == 380000.0

    def test_property_to_dict(self):
        """Test converting property to dictionary"""
        prop = ATTOMProperty(
            attom_id="A123456",
            address="123 Main St",
            city="Houston",
            state="TX",
            zip_code="77001",
            county="Harris",
            fips="48201",
            property_type="SFR",
            last_sale_date=date(2020, 6, 15)
        )
        result = prop.to_dict()
        assert result['attom_id'] == "A123456"
        assert result['last_sale_date'] == "2020-06-15"
        assert 'fetched_at' in result


class TestSalesComparable:
    """Tests for SalesComparable dataclass"""

    def test_create_minimal_comparable(self):
        """Test creating sales comparable with required fields"""
        comp = SalesComparable(
            attom_id="A789012",
            address="456 Oak St",
            city="Houston",
            state="TX",
            zip_code="77002",
            property_type="SFR"
        )
        assert comp.attom_id == "A789012"
        assert comp.sale_price is None

    def test_create_full_comparable(self):
        """Test creating sales comparable with all fields"""
        comp = SalesComparable(
            attom_id="A789012",
            address="456 Oak St",
            city="Houston",
            state="TX",
            zip_code="77002",
            property_type="SFR",
            sale_date=date(2024, 3, 15),
            sale_price=425000.0,
            distance_miles=0.5,
            bedrooms=4,
            bathrooms=2.5,
            building_sqft=2300.0,
            year_built=2012,
            price_per_sqft=184.78,
            adjusted_price=430000.0
        )
        assert comp.distance_miles == 0.5
        assert comp.sale_price == 425000.0

    def test_comparable_to_dict(self):
        """Test converting sales comparable to dictionary"""
        comp = SalesComparable(
            attom_id="A789012",
            address="456 Oak St",
            city="Houston",
            state="TX",
            zip_code="77002",
            property_type="SFR",
            sale_date=date(2024, 3, 15),
            sale_price=425000.0
        )
        result = comp.to_dict()
        assert result['sale_date'] == "2024-03-15"
        assert result['sale_price'] == 425000.0


class TestNeighborhoodData:
    """Tests for NeighborhoodData dataclass"""

    def test_create_minimal_neighborhood(self):
        """Test creating neighborhood data with required fields"""
        neighborhood = NeighborhoodData(
            fips="48201",
            name="Downtown",
            city="Houston",
            state="TX"
        )
        assert neighborhood.fips == "48201"
        assert neighborhood.name == "Downtown"

    def test_create_full_neighborhood(self):
        """Test creating neighborhood data with all fields"""
        neighborhood = NeighborhoodData(
            fips="48201",
            name="Downtown",
            city="Houston",
            state="TX",
            median_home_value=450000.0,
            median_rent=2100.0,
            median_household_income=75000.0,
            population=15000,
            population_density=5000.0,
            median_age=35.5,
            owner_occupied_rate=0.45,
            crime_index=85
        )
        assert neighborhood.median_home_value == 450000.0
        assert neighborhood.crime_index == 85

    def test_neighborhood_to_dict(self):
        """Test converting neighborhood data to dictionary"""
        neighborhood = NeighborhoodData(
            fips="48201",
            name="Downtown",
            city="Houston",
            state="TX",
            median_home_value=450000.0
        )
        result = neighborhood.to_dict()
        assert result['name'] == "Downtown"
        assert result['median_home_value'] == 450000.0


class TestSchoolInfo:
    """Tests for SchoolInfo dataclass"""

    def test_create_minimal_school(self):
        """Test creating school info with required fields"""
        school = SchoolInfo(
            school_id="S123",
            name="Lincoln Elementary",
            school_type=SchoolType.ELEMENTARY
        )
        assert school.school_id == "S123"
        assert school.school_type == SchoolType.ELEMENTARY

    def test_create_full_school(self):
        """Test creating school info with all fields"""
        school = SchoolInfo(
            school_id="S123",
            name="Lincoln Elementary",
            school_type=SchoolType.ELEMENTARY,
            address="789 School St",
            city="Houston",
            state="TX",
            zip_code="77001",
            district_name="Houston ISD",
            grade_low="K",
            grade_high="5",
            enrollment=450,
            student_teacher_ratio=18.5,
            great_schools_rating=8,
            distance_miles=0.3
        )
        assert school.district_name == "Houston ISD"
        assert school.great_schools_rating == 8

    def test_school_to_dict(self):
        """Test converting school info to dictionary"""
        school = SchoolInfo(
            school_id="S123",
            name="Lincoln Elementary",
            school_type=SchoolType.ELEMENTARY,
            great_schools_rating=8
        )
        result = school.to_dict()
        assert result['name'] == "Lincoln Elementary"
        assert result['school_type'] == "elementary"
        assert result['great_schools_rating'] == 8


class TestHazardRisk:
    """Tests for HazardRisk dataclass"""

    def test_create_minimal_hazard(self):
        """Test creating hazard risk with required fields"""
        hazard = HazardRisk(
            property_id="A123456"
        )
        assert hazard.property_id == "A123456"
        assert hazard.flood_risk == RiskLevel.UNKNOWN

    def test_create_full_hazard(self):
        """Test creating hazard risk with all fields"""
        hazard = HazardRisk(
            property_id="A123456",
            flood_risk=RiskLevel.MODERATE,
            flood_zone="AE",
            flood_factor=5,
            earthquake_risk=RiskLevel.LOW,
            fire_risk=RiskLevel.VERY_LOW,
            wind_risk=RiskLevel.HIGH,
            tornado_risk=RiskLevel.MODERATE,
            superfund_site_nearby=False,
            composite_risk_score=65
        )
        assert hazard.flood_risk == RiskLevel.MODERATE
        assert hazard.composite_risk_score == 65

    def test_hazard_to_dict(self):
        """Test converting hazard risk to dictionary"""
        hazard = HazardRisk(
            property_id="A123456",
            flood_risk=RiskLevel.HIGH,
            flood_zone="VE"
        )
        result = hazard.to_dict()
        assert result['flood_risk'] == "high"
        assert result['flood_zone'] == "VE"


class TestMarketTrend:
    """Tests for MarketTrend dataclass"""

    def test_create_minimal_trend(self):
        """Test creating market trend with required fields"""
        trend = MarketTrend(
            area_name="77001",
            area_type="zip",
            period="2024-01"
        )
        assert trend.area_name == "77001"
        assert trend.area_type == "zip"
        assert trend.period == "2024-01"

    def test_create_full_trend(self):
        """Test creating market trend with all fields"""
        trend = MarketTrend(
            area_name="77001",
            area_type="zip",
            period="2024-01",
            median_sale_price=425000.0,
            median_price_per_sqft=185.0,
            median_price_change_yoy=5.2,
            sales_count=125,
            active_listings=85,
            median_dom=22,
            months_of_supply=2.1,
            foreclosure_rate=0.5
        )
        assert trend.median_sale_price == 425000.0
        assert trend.median_price_change_yoy == 5.2

    def test_trend_to_dict(self):
        """Test converting market trend to dictionary"""
        trend = MarketTrend(
            area_name="77001",
            area_type="zip",
            period="2024-01",
            median_sale_price=425000.0
        )
        result = trend.to_dict()
        assert result['area_name'] == "77001"
        assert result['period'] == "2024-01"
        assert result['median_sale_price'] == 425000.0


class TestATTOMSearch:
    """Tests for ATTOMSearch dataclass"""

    def test_create_empty_search(self):
        """Test creating search with default values"""
        search = ATTOMSearch()
        assert search.address is None
        assert search.radius_miles is None
        assert search.page_size == 50

    def test_create_address_search(self):
        """Test creating search by address"""
        search = ATTOMSearch(
            address="123 Main St",
            city="Houston",
            state="TX",
            zip_code="77001"
        )
        assert search.address == "123 Main St"

    def test_create_filtered_search(self):
        """Test creating search with filters"""
        search = ATTOMSearch(
            state="TX",
            property_type="SFR",
            min_beds=3,
            max_value=500000.0,
            radius_miles=2.0,
            page_size=100
        )
        assert search.min_beds == 3
        assert search.radius_miles == 2.0


class TestATTOMAPIClient:
    """Tests for ATTOMAPIClient implementation"""

    def test_initialization(self):
        """Test ATTOMAPIClient initialization"""
        client = ATTOMAPIClient(api_key="test_key")
        assert client.api_key == "test_key"

    def test_initialization_with_config(self):
        """Test ATTOMAPIClient initialization with config"""
        config = {'timeout': 60}
        client = ATTOMAPIClient(api_key="test_key", config=config)
        assert client.config['timeout'] == 60

    def test_get_headers(self):
        """Test authenticated headers generation"""
        client = ATTOMAPIClient(api_key="test_key")
        headers = client._get_headers()
        assert headers['apikey'] == "test_key"
        assert headers['Accept'] == 'application/json'

    def test_search_properties_returns_list(self):
        """Test search_properties method returns list"""
        client = ATTOMAPIClient(api_key="test_key")
        search = ATTOMSearch(address="123 Main St")
        results = client.search_properties(search)
        assert isinstance(results, list)

    def test_get_property_returns_none(self):
        """Test get_property method returns None (placeholder)"""
        client = ATTOMAPIClient(api_key="test_key")
        result = client.get_property("A123456")
        assert result is None

    def test_get_sales_comparables_returns_list(self):
        """Test get_sales_comparables method returns list"""
        client = ATTOMAPIClient(api_key="test_key")
        results = client.get_sales_comparables("A123456", radius_miles=1.0)
        assert isinstance(results, list)

    def test_get_neighborhood_data_returns_none(self):
        """Test get_neighborhood_data method returns None (placeholder)"""
        client = ATTOMAPIClient(api_key="test_key")
        result = client.get_neighborhood_data("A123456")
        assert result is None

    def test_get_nearby_schools_returns_list(self):
        """Test get_nearby_schools method returns list"""
        client = ATTOMAPIClient(api_key="test_key")
        results = client.get_nearby_schools(29.7604, -95.3698, radius_miles=2.0)
        assert isinstance(results, list)

    def test_get_hazard_risk_returns_none(self):
        """Test get_hazard_risk method returns None (placeholder)"""
        client = ATTOMAPIClient(api_key="test_key")
        result = client.get_hazard_risk("A123456")
        assert result is None

    def test_get_market_trends_returns_list(self):
        """Test get_market_trends method returns list"""
        client = ATTOMAPIClient(api_key="test_key")
        results = client.get_market_trends("zip", "77001", months_back=12)
        assert isinstance(results, list)


class TestCreateAttomClientFunction:
    """Tests for create_attom_client factory function"""

    def test_create_client(self):
        """Test creating ATTOM client via factory function"""
        client = create_attom_client(api_key="test_key")
        assert isinstance(client, ATTOMAPIClient)
        assert client.api_key == "test_key"

    def test_create_client_with_config(self):
        """Test creating ATTOM client with config"""
        config = {'timeout': 60}
        client = create_attom_client(api_key="test_key", config=config)
        assert client.config['timeout'] == 60


class TestATTOMImports:
    """Tests for module imports"""

    def test_all_exports_available(self):
        """Test that all expected exports are available"""
        from datagod.scrapers.paid.attom_api import (
            RiskLevel,
            SchoolType,
            ATTOMProperty,
            SalesComparable,
            NeighborhoodData,
            SchoolInfo,
            HazardRisk,
            MarketTrend,
            ATTOMSearch,
            ATTOMAPI,
            ATTOMAPIClient,
            create_attom_client
        )
        assert all([
            RiskLevel, SchoolType, ATTOMProperty, SalesComparable,
            NeighborhoodData, SchoolInfo, HazardRisk, MarketTrend,
            ATTOMSearch, ATTOMAPI, ATTOMAPIClient, create_attom_client
        ])


class TestATTOMEdgeCases:
    """Edge case tests for ATTOM API module"""

    def test_property_with_null_dates(self):
        """Test property to_dict with null dates"""
        prop = ATTOMProperty(
            attom_id="A123456",
            address="123 Main St",
            city="Houston",
            state="TX",
            zip_code="77001",
            county="Harris",
            fips="48201",
            property_type="SFR"
        )
        result = prop.to_dict()
        assert result['last_sale_date'] is None

    def test_hazard_all_unknown_risks(self):
        """Test hazard with all unknown risk levels"""
        hazard = HazardRisk(property_id="A123456")
        result = hazard.to_dict()
        assert result['flood_risk'] == "unknown"
        assert result['earthquake_risk'] == "unknown"

    def test_school_without_rating(self):
        """Test school info without rating"""
        school = SchoolInfo(
            school_id="S123",
            name="New School"
        )
        result = school.to_dict()
        assert result['great_schools_rating'] is None

    def test_trend_null_statistics(self):
        """Test market trend with null statistics"""
        trend = MarketTrend(
            area_name="77001",
            area_type="zip",
            period="2024-01"
        )
        result = trend.to_dict()
        assert result['median_sale_price'] is None
        assert result['sales_count'] is None
