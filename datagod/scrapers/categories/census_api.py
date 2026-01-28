"""
Census Bureau API Integration

Collects US Census Bureau public data including:
- Decennial Census data
- American Community Survey (ACS)
- Population estimates
- Economic indicators
- Housing data
- Geographic data (TIGER)
- Business patterns

API Documentation: https://www.census.gov/data/developers/guidance.html
"""

import logging
import asyncio
import aiohttp
import os
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class CensusDataset(Enum):
    """Available Census datasets."""
    DECENNIAL_2020 = "dec/pl"  # 2020 Decennial Census
    DECENNIAL_2010 = "dec/sf1"  # 2010 Decennial Census
    ACS_5YEAR = "acs/acs5"  # American Community Survey 5-year
    ACS_1YEAR = "acs/acs1"  # American Community Survey 1-year
    ACS_5YEAR_PROFILE = "acs/acs5/profile"  # ACS Data Profiles
    ACS_5YEAR_SUBJECT = "acs/acs5/subject"  # ACS Subject Tables
    PEP = "pep/population"  # Population Estimates Program
    PEP_CHARAGEGROUPS = "pep/charagegroups"  # PEP by age groups
    CBP = "cbp"  # County Business Patterns
    ZBP = "zbp"  # ZIP Code Business Patterns
    ABS = "abscs"  # Annual Business Survey
    SAHIE = "timeseries/healthins/sahie"  # Health Insurance
    SAIPE = "timeseries/poverty/saipe"  # Poverty Estimates


class GeographyLevel(Enum):
    """Geographic hierarchy levels."""
    US = "us"
    REGION = "region"
    DIVISION = "division"
    STATE = "state"
    COUNTY = "county"
    TRACT = "tract"
    BLOCK_GROUP = "block group"
    BLOCK = "block"
    PLACE = "place"
    MSA = "metropolitan statistical area/micropolitan statistical area"
    CONGRESSIONAL_DISTRICT = "congressional district"
    ZCTA = "zip code tabulation area"
    SCHOOL_DISTRICT = "school district (unified)"


@dataclass
class CensusRecord:
    """Census data record structure."""
    geography_id: str
    geography_name: str
    geography_level: GeographyLevel
    state_fips: Optional[str] = None
    county_fips: Optional[str] = None
    tract_fips: Optional[str] = None
    dataset: CensusDataset = CensusDataset.ACS_5YEAR
    year: int = 2023
    variables: Dict[str, Any] = field(default_factory=dict)
    population: Optional[int] = None
    households: Optional[int] = None
    median_income: Optional[float] = None
    median_age: Optional[float] = None
    housing_units: Optional[int] = None
    source_url: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'geography_id': self.geography_id,
            'geography_name': self.geography_name,
            'geography_level': self.geography_level.value,
            'state_fips': self.state_fips,
            'county_fips': self.county_fips,
            'tract_fips': self.tract_fips,
            'dataset': self.dataset.value,
            'year': self.year,
            'variables': self.variables,
            'population': self.population,
            'households': self.households,
            'median_income': self.median_income,
            'median_age': self.median_age,
            'housing_units': self.housing_units,
            'source_url': self.source_url,
        }


@dataclass
class BusinessPatternRecord:
    """County/ZIP Business Patterns record."""
    geography_id: str
    geography_name: str
    state_fips: Optional[str] = None
    county_fips: Optional[str] = None
    zip_code: Optional[str] = None
    year: int = 2022
    naics_code: Optional[str] = None
    naics_description: Optional[str] = None
    establishments: Optional[int] = None
    employees: Optional[int] = None
    annual_payroll: Optional[float] = None
    first_quarter_payroll: Optional[float] = None
    source_url: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'geography_id': self.geography_id,
            'geography_name': self.geography_name,
            'state_fips': self.state_fips,
            'county_fips': self.county_fips,
            'zip_code': self.zip_code,
            'year': self.year,
            'naics_code': self.naics_code,
            'naics_description': self.naics_description,
            'establishments': self.establishments,
            'employees': self.employees,
            'annual_payroll': self.annual_payroll,
            'first_quarter_payroll': self.first_quarter_payroll,
            'source_url': self.source_url,
        }


@dataclass
class PopulationEstimate:
    """Population estimate record."""
    geography_id: str
    geography_name: str
    state_fips: Optional[str] = None
    county_fips: Optional[str] = None
    year: int = 2023
    population: Optional[int] = None
    population_change: Optional[int] = None
    births: Optional[int] = None
    deaths: Optional[int] = None
    net_migration: Optional[int] = None
    source_url: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'geography_id': self.geography_id,
            'geography_name': self.geography_name,
            'state_fips': self.state_fips,
            'county_fips': self.county_fips,
            'year': self.year,
            'population': self.population,
            'population_change': self.population_change,
            'births': self.births,
            'deaths': self.deaths,
            'net_migration': self.net_migration,
            'source_url': self.source_url,
        }


# Census API configuration
CENSUS_API_CONFIG = {
    'base_url': 'https://api.census.gov/data/',
    'key_required': False,  # Optional but increases rate limit
    'key_env_var': 'CENSUS_API_KEY',
    'rate_limit_no_key': 500,  # per day without key
    'rate_limit_with_key': 'unlimited',
    'documentation': 'https://www.census.gov/data/developers/guidance.html',
}

# Common Census variables for ACS
COMMON_VARIABLES = {
    'population': {
        'B01003_001E': 'Total Population',
        'B01001_001E': 'Total Population (Sex by Age)',
        'B01002_001E': 'Median Age',
    },
    'households': {
        'B11001_001E': 'Total Households',
        'B11016_001E': 'Household Type by Household Size',
        'B25010_001E': 'Average Household Size',
    },
    'income': {
        'B19013_001E': 'Median Household Income',
        'B19301_001E': 'Per Capita Income',
        'B19001_001E': 'Household Income Distribution',
    },
    'housing': {
        'B25001_001E': 'Total Housing Units',
        'B25002_001E': 'Occupancy Status',
        'B25003_001E': 'Tenure (Owner/Renter)',
        'B25077_001E': 'Median Home Value',
        'B25064_001E': 'Median Gross Rent',
    },
    'education': {
        'B15003_001E': 'Educational Attainment',
        'B14001_001E': 'School Enrollment',
    },
    'employment': {
        'B23025_001E': 'Employment Status',
        'B24011_001E': 'Occupation by Sex',
    },
    'poverty': {
        'B17001_001E': 'Poverty Status',
        'B17010_001E': 'Poverty Status of Families',
    },
    'race_ethnicity': {
        'B02001_001E': 'Race',
        'B03003_001E': 'Hispanic or Latino Origin',
    },
}

# ACS Profile variables (DP prefix)
ACS_PROFILE_VARIABLES = {
    'DP02_0001E': 'Total Households',
    'DP02_0059PE': 'Percent with Bachelor\'s Degree or Higher',
    'DP03_0004PE': 'Employment Rate',
    'DP03_0062E': 'Median Household Income',
    'DP04_0001E': 'Total Housing Units',
    'DP04_0089E': 'Median Home Value',
    'DP05_0001E': 'Total Population',
}

# State FIPS codes
STATE_FIPS = {
    'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06',
    'CO': '08', 'CT': '09', 'DE': '10', 'DC': '11', 'FL': '12',
    'GA': '13', 'HI': '15', 'ID': '16', 'IL': '17', 'IN': '18',
    'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22', 'ME': '23',
    'MD': '24', 'MA': '25', 'MI': '26', 'MN': '27', 'MS': '28',
    'MO': '29', 'MT': '30', 'NE': '31', 'NV': '32', 'NH': '33',
    'NJ': '34', 'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38',
    'OH': '39', 'OK': '40', 'OR': '41', 'PA': '42', 'RI': '44',
    'SC': '45', 'SD': '46', 'TN': '47', 'TX': '48', 'UT': '49',
    'VT': '50', 'VA': '51', 'WA': '53', 'WV': '54', 'WI': '55',
    'WY': '56', 'PR': '72', 'GU': '66', 'VI': '78', 'AS': '60', 'MP': '69',
}


class CensusApiScraper:
    """
    Census Bureau API integration.

    Features:
    - Decennial Census data
    - American Community Survey (ACS) 1-year and 5-year
    - Population estimates (PEP)
    - County/ZIP Business Patterns
    - Small Area Income and Poverty Estimates (SAIPE)
    - Small Area Health Insurance Estimates (SAHIE)
    - Geographic data
    - FREE API with optional key for higher rate limits

    Rate Limits:
    - Without API key: 500 requests/day
    - With API key: Essentially unlimited

    API Key: Get free at https://api.census.gov/data/key_signup.html
    """

    CATEGORY = "census_data"
    DISPLAY_NAME = "US Census Bureau Data"
    BASE_URL = "https://api.census.gov/data"

    def __init__(self, api_key: str = None):
        """
        Initialize the Census API scraper.

        Args:
            api_key: Census API key (optional, increases rate limit)
        """
        self.api_key = api_key or os.environ.get('CENSUS_API_KEY')
        self.config = CENSUS_API_CONFIG
        self.variables = COMMON_VARIABLES
        self._last_request_time = 0
        # Rate limit: be nice to Census servers
        # With key: ~10 req/sec, without: ~0.5 req/sec
        self._min_request_interval = 0.1 if self.api_key else 2.0
        logger.info(f"CensusApiScraper initialized (API key: {'present' if self.api_key else 'not set'})")

    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    async def _make_request(
        self,
        url: str,
        session: aiohttp.ClientSession = None
    ) -> List[List[Any]]:
        """
        Make an async HTTP request to Census API.

        Args:
            url: Full URL to request
            session: Optional aiohttp session to reuse

        Returns:
            List of rows (Census API returns JSON array of arrays)
        """
        await self._rate_limit()

        headers = {
            'Accept': 'application/json',
        }

        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                elif response.status == 204:
                    logger.warning(f"No data found for request: {url}")
                    return []
                elif response.status == 400:
                    error_text = await response.text()
                    logger.error(f"Census API bad request: {error_text}")
                    return []
                elif response.status == 404:
                    logger.warning(f"Census API endpoint not found: {url}")
                    return []
                elif response.status == 429:
                    logger.warning("Census API rate limit hit, waiting...")
                    await asyncio.sleep(60)
                    return await self._make_request(url, session if not close_session else None)
                else:
                    logger.error(f"Census API error {response.status}: {await response.text()}")
                    return []
        except asyncio.TimeoutError:
            logger.error(f"Timeout requesting: {url}")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error: {e}")
            return []
        finally:
            if close_session:
                await session.close()

    def _build_url(
        self,
        year: int,
        dataset: Union[CensusDataset, str],
        variables: List[str],
        geography: str,
        key: bool = True
    ) -> str:
        """
        Build Census API URL.

        Args:
            year: Data year
            dataset: Census dataset
            variables: List of variable codes
            geography: Geography specification (e.g., "state:06" or "county:*&in=state:06")
            key: Whether to include API key

        Returns:
            Full API URL
        """
        dataset_path = dataset.value if isinstance(dataset, CensusDataset) else dataset

        # Handle timeseries datasets differently
        if 'timeseries' in dataset_path:
            base = f"{self.BASE_URL}/{dataset_path}"
        else:
            base = f"{self.BASE_URL}/{year}/{dataset_path}"

        # Build URL manually to handle the special "&in=" syntax properly
        # Census API expects: for=county:*&in=state:17 (not URL-encoded &in=)
        url = f"{base}?get={','.join(variables)}"

        # Handle geography - split on "&in=" to separate for and in parameters
        if "&in=" in geography:
            for_part, in_part = geography.split("&in=", 1)
            url += f"&for={for_part}&in={in_part}"
        else:
            url += f"&for={geography}"

        if key and self.api_key:
            url += f"&key={self.api_key}"

        return url

    def _parse_response(
        self,
        data: List[List[Any]],
        variable_names: Dict[str, str] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse Census API response into dictionaries.

        Args:
            data: Raw response (list of lists, first row is headers)
            variable_names: Optional mapping of variable codes to friendly names

        Returns:
            List of dictionaries with parsed data
        """
        if not data or len(data) < 2:
            return []

        headers = data[0]
        results = []

        for row in data[1:]:
            record = {}
            for i, header in enumerate(headers):
                value = row[i] if i < len(row) else None

                # Convert numeric values
                if value is not None and value != '':
                    try:
                        # Check if it's a negative value indicator (Census uses negative for suppressed)
                        if isinstance(value, str) and value.startswith('-'):
                            value = int(value) if '.' not in value else float(value)
                        elif isinstance(value, str) and value.replace('.', '').isdigit():
                            value = int(value) if '.' not in value else float(value)
                    except (ValueError, TypeError):
                        logger.debug(f"Failed to convert value '{value}' in column {i}")


                # Use friendly name if available
                if variable_names and header in variable_names:
                    record[variable_names[header]] = value
                else:
                    record[header] = value

            results.append(record)

        return results

    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int."""
        if value is None or value == '' or value == 'null':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or value == '' or value == 'null':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def get_population(
        self,
        state_fips: str,
        county_fips: str = "*",
        year: int = 2022,
        dataset: CensusDataset = CensusDataset.ACS_5YEAR
    ) -> List[CensusRecord]:
        """
        Get population data.

        Args:
            state_fips: State FIPS code (2 digits)
            county_fips: County FIPS code (3 digits, * for all)
            year: Data year
            dataset: Census dataset to use

        Returns:
            List of census records with population data
        """
        logger.info(f"Getting population for state {state_fips}, county {county_fips}")

        variables = ['NAME', 'B01003_001E', 'B01002_001E']

        if county_fips == "*":
            geography = f"county:*&in=state:{state_fips}"
        else:
            geography = f"county:{county_fips}&in=state:{state_fips}"

        url = self._build_url(year, dataset, variables, geography)
        data = await self._make_request(url)

        records = []
        parsed = self._parse_response(data)

        for row in parsed:
            state = row.get('state', state_fips)
            county = row.get('county', '')

            record = CensusRecord(
                geography_id=f"{state}{county}",
                geography_name=row.get('NAME', ''),
                geography_level=GeographyLevel.COUNTY,
                state_fips=state,
                county_fips=county,
                dataset=dataset,
                year=year,
                population=self._safe_int(row.get('B01003_001E')),
                median_age=self._safe_float(row.get('B01002_001E')),
                variables={
                    'total_population': self._safe_int(row.get('B01003_001E')),
                    'median_age': self._safe_float(row.get('B01002_001E')),
                },
                source_url=url,
                raw_data=row,
            )
            records.append(record)

        logger.info(f"Retrieved {len(records)} population records")
        return records

    async def get_demographics(
        self,
        state_fips: str,
        county_fips: str = "*",
        year: int = 2022,
        variables: List[str] = None
    ) -> List[CensusRecord]:
        """
        Get demographic data.

        Args:
            state_fips: State FIPS code
            county_fips: County FIPS code
            year: Data year
            variables: Specific variable codes to retrieve

        Returns:
            List of census records with demographic data
        """
        logger.info(f"Getting demographics for state {state_fips}")

        # Default demographic variables
        if variables is None:
            variables = [
                'NAME',
                'B01003_001E',  # Total population
                'B01002_001E',  # Median age
                'B11001_001E',  # Total households
                'B19013_001E',  # Median household income
                'B25001_001E',  # Total housing units
                'B25077_001E',  # Median home value
            ]
        elif 'NAME' not in variables:
            variables = ['NAME'] + variables

        if county_fips == "*":
            geography = f"county:*&in=state:{state_fips}"
        else:
            geography = f"county:{county_fips}&in=state:{state_fips}"

        url = self._build_url(year, CensusDataset.ACS_5YEAR, variables, geography)
        data = await self._make_request(url)

        records = []
        parsed = self._parse_response(data)

        for row in parsed:
            state = row.get('state', state_fips)
            county = row.get('county', '')

            record = CensusRecord(
                geography_id=f"{state}{county}",
                geography_name=row.get('NAME', ''),
                geography_level=GeographyLevel.COUNTY,
                state_fips=state,
                county_fips=county,
                dataset=CensusDataset.ACS_5YEAR,
                year=year,
                population=self._safe_int(row.get('B01003_001E')),
                median_age=self._safe_float(row.get('B01002_001E')),
                households=self._safe_int(row.get('B11001_001E')),
                median_income=self._safe_float(row.get('B19013_001E')),
                housing_units=self._safe_int(row.get('B25001_001E')),
                variables={k: v for k, v in row.items() if k not in ['NAME', 'state', 'county']},
                source_url=url,
                raw_data=row,
            )
            records.append(record)

        logger.info(f"Retrieved {len(records)} demographic records")
        return records

    async def get_income_data(
        self,
        state_fips: str,
        county_fips: str = "*",
        year: int = 2022
    ) -> List[CensusRecord]:
        """
        Get income and poverty data.

        Args:
            state_fips: State FIPS code
            county_fips: County FIPS code
            year: Data year

        Returns:
            List of census records with income data
        """
        logger.info(f"Getting income data for state {state_fips}")

        variables = [
            'NAME',
            'B19013_001E',  # Median household income
            'B19301_001E',  # Per capita income
            'B17001_001E',  # Poverty status total
            'B17001_002E',  # Income below poverty level
            'B19001_001E',  # Household income total
        ]

        if county_fips == "*":
            geography = f"county:*&in=state:{state_fips}"
        else:
            geography = f"county:{county_fips}&in=state:{state_fips}"

        url = self._build_url(year, CensusDataset.ACS_5YEAR, variables, geography)
        data = await self._make_request(url)

        records = []
        parsed = self._parse_response(data)

        for row in parsed:
            state = row.get('state', state_fips)
            county = row.get('county', '')

            record = CensusRecord(
                geography_id=f"{state}{county}",
                geography_name=row.get('NAME', ''),
                geography_level=GeographyLevel.COUNTY,
                state_fips=state,
                county_fips=county,
                dataset=CensusDataset.ACS_5YEAR,
                year=year,
                median_income=self._safe_float(row.get('B19013_001E')),
                variables={
                    'median_household_income': self._safe_float(row.get('B19013_001E')),
                    'per_capita_income': self._safe_float(row.get('B19301_001E')),
                    'poverty_status_total': self._safe_int(row.get('B17001_001E')),
                    'below_poverty_level': self._safe_int(row.get('B17001_002E')),
                },
                source_url=url,
                raw_data=row,
            )
            records.append(record)

        logger.info(f"Retrieved {len(records)} income records")
        return records

    async def get_housing_data(
        self,
        state_fips: str,
        county_fips: str = "*",
        year: int = 2022
    ) -> List[CensusRecord]:
        """
        Get housing data.

        Args:
            state_fips: State FIPS code
            county_fips: County FIPS code
            year: Data year

        Returns:
            List of census records with housing data
        """
        logger.info(f"Getting housing data for state {state_fips}")

        variables = [
            'NAME',
            'B25001_001E',  # Total housing units
            'B25002_002E',  # Occupied units
            'B25002_003E',  # Vacant units
            'B25003_002E',  # Owner occupied
            'B25003_003E',  # Renter occupied
            'B25077_001E',  # Median home value
            'B25064_001E',  # Median gross rent
            'B25010_001E',  # Average household size
        ]

        if county_fips == "*":
            geography = f"county:*&in=state:{state_fips}"
        else:
            geography = f"county:{county_fips}&in=state:{state_fips}"

        url = self._build_url(year, CensusDataset.ACS_5YEAR, variables, geography)
        data = await self._make_request(url)

        records = []
        parsed = self._parse_response(data)

        for row in parsed:
            state = row.get('state', state_fips)
            county = row.get('county', '')

            record = CensusRecord(
                geography_id=f"{state}{county}",
                geography_name=row.get('NAME', ''),
                geography_level=GeographyLevel.COUNTY,
                state_fips=state,
                county_fips=county,
                dataset=CensusDataset.ACS_5YEAR,
                year=year,
                housing_units=self._safe_int(row.get('B25001_001E')),
                variables={
                    'total_housing_units': self._safe_int(row.get('B25001_001E')),
                    'occupied_units': self._safe_int(row.get('B25002_002E')),
                    'vacant_units': self._safe_int(row.get('B25002_003E')),
                    'owner_occupied': self._safe_int(row.get('B25003_002E')),
                    'renter_occupied': self._safe_int(row.get('B25003_003E')),
                    'median_home_value': self._safe_float(row.get('B25077_001E')),
                    'median_gross_rent': self._safe_float(row.get('B25064_001E')),
                    'avg_household_size': self._safe_float(row.get('B25010_001E')),
                },
                source_url=url,
                raw_data=row,
            )
            records.append(record)

        logger.info(f"Retrieved {len(records)} housing records")
        return records

    async def get_business_patterns(
        self,
        state_fips: str,
        county_fips: str = "*",
        naics_code: str = "",
        year: int = 2021
    ) -> List[BusinessPatternRecord]:
        """
        Get County Business Patterns data.

        Args:
            state_fips: State FIPS code
            county_fips: County FIPS code
            naics_code: NAICS industry code filter (2-6 digits)
            year: Data year (CBP typically available through 2021)

        Returns:
            List of business pattern records
        """
        logger.info(f"Getting business patterns for state {state_fips}")

        variables = [
            'NAME',
            'NAICS2017',
            'NAICS2017_LABEL',
            'ESTAB',  # Number of establishments
            'EMP',    # Number of employees
            'PAYANN', # Annual payroll ($1000)
            'PAYQTR1', # First quarter payroll ($1000)
        ]

        if county_fips == "*":
            geography = f"county:*&in=state:{state_fips}"
        else:
            geography = f"county:{county_fips}&in=state:{state_fips}"

        # Add NAICS filter if specified
        if naics_code:
            # For CBP, we need to add NAICS as a variable filter
            base_url = f"{self.BASE_URL}/{year}/cbp"
            params = {
                'get': ','.join(variables),
                'for': geography,
                'NAICS2017': naics_code,
            }
            if self.api_key:
                params['key'] = self.api_key
            url = f"{base_url}?{urlencode(params)}"
        else:
            url = self._build_url(year, 'cbp', variables, geography)

        data = await self._make_request(url)

        records = []
        parsed = self._parse_response(data)

        for row in parsed:
            state = row.get('state', state_fips)
            county = row.get('county', '')

            record = BusinessPatternRecord(
                geography_id=f"{state}{county}",
                geography_name=row.get('NAME', ''),
                state_fips=state,
                county_fips=county,
                year=year,
                naics_code=row.get('NAICS2017'),
                naics_description=row.get('NAICS2017_LABEL'),
                establishments=self._safe_int(row.get('ESTAB')),
                employees=self._safe_int(row.get('EMP')),
                annual_payroll=self._safe_float(row.get('PAYANN')),
                first_quarter_payroll=self._safe_float(row.get('PAYQTR1')),
                source_url=url,
                raw_data=row,
            )
            records.append(record)

        logger.info(f"Retrieved {len(records)} business pattern records")
        return records

    async def get_zip_business_patterns(
        self,
        zip_code: str = "*",
        state_fips: str = "",
        naics_code: str = "",
        year: int = 2021
    ) -> List[BusinessPatternRecord]:
        """
        Get ZIP Code Business Patterns data.

        Args:
            zip_code: ZIP code (5 digits, or * for all in state)
            state_fips: State FIPS code (required if zip_code is *)
            naics_code: NAICS industry code filter
            year: Data year

        Returns:
            List of business pattern records
        """
        logger.info(f"Getting ZIP business patterns for {zip_code}")

        variables = [
            'NAME',
            'ZIPCODE',
            'NAICS2017',
            'NAICS2017_LABEL',
            'ESTAB',
            'EMP',
            'PAYANN',
        ]

        # ZBP geography is different
        if zip_code == "*" and state_fips:
            geography = f"zipcode:*&in=state:{state_fips}"
        else:
            geography = f"zipcode:{zip_code}"

        url = self._build_url(year, 'zbp', variables, geography)
        data = await self._make_request(url)

        records = []
        parsed = self._parse_response(data)

        for row in parsed:
            record = BusinessPatternRecord(
                geography_id=row.get('ZIPCODE', zip_code),
                geography_name=row.get('NAME', ''),
                zip_code=row.get('ZIPCODE', zip_code),
                year=year,
                naics_code=row.get('NAICS2017'),
                naics_description=row.get('NAICS2017_LABEL'),
                establishments=self._safe_int(row.get('ESTAB')),
                employees=self._safe_int(row.get('EMP')),
                annual_payroll=self._safe_float(row.get('PAYANN')),
                source_url=url,
                raw_data=row,
            )
            records.append(record)

        logger.info(f"Retrieved {len(records)} ZIP business pattern records")
        return records

    async def get_tract_data(
        self,
        state_fips: str,
        county_fips: str,
        tract: str = "*",
        variables: List[str] = None,
        year: int = 2022
    ) -> List[CensusRecord]:
        """
        Get census tract level data.

        Args:
            state_fips: State FIPS code
            county_fips: County FIPS code
            tract: Census tract code (* for all in county)
            variables: Variable codes to retrieve
            year: Data year

        Returns:
            List of census records at tract level
        """
        logger.info(f"Getting tract data for {state_fips}/{county_fips}")

        if variables is None:
            variables = [
                'NAME',
                'B01003_001E',  # Population
                'B19013_001E',  # Median income
                'B25077_001E',  # Median home value
            ]
        elif 'NAME' not in variables:
            variables = ['NAME'] + variables

        if tract == "*":
            geography = f"tract:*&in=state:{state_fips}&in=county:{county_fips}"
        else:
            geography = f"tract:{tract}&in=state:{state_fips}&in=county:{county_fips}"

        url = self._build_url(year, CensusDataset.ACS_5YEAR, variables, geography)
        data = await self._make_request(url)

        records = []
        parsed = self._parse_response(data)

        for row in parsed:
            state = row.get('state', state_fips)
            county = row.get('county', county_fips)
            tract_code = row.get('tract', '')

            record = CensusRecord(
                geography_id=f"{state}{county}{tract_code}",
                geography_name=row.get('NAME', ''),
                geography_level=GeographyLevel.TRACT,
                state_fips=state,
                county_fips=county,
                tract_fips=tract_code,
                dataset=CensusDataset.ACS_5YEAR,
                year=year,
                population=self._safe_int(row.get('B01003_001E')),
                median_income=self._safe_float(row.get('B19013_001E')),
                variables={k: v for k, v in row.items() if k not in ['NAME', 'state', 'county', 'tract']},
                source_url=url,
                raw_data=row,
            )
            records.append(record)

        logger.info(f"Retrieved {len(records)} tract records")
        return records

    async def get_poverty_estimates(
        self,
        state_fips: str,
        county_fips: str = "*",
        year: int = 2022
    ) -> List[Dict[str, Any]]:
        """
        Get Small Area Income and Poverty Estimates (SAIPE).

        Args:
            state_fips: State FIPS code
            county_fips: County FIPS code
            year: Data year

        Returns:
            List of poverty estimate records
        """
        logger.info(f"Getting SAIPE data for state {state_fips}")

        variables = [
            'NAME',
            'SAEPOVALL_PT',   # All ages in poverty estimate
            'SAEPOVALL_MOE',  # Margin of error
            'SAEPOV0_17_PT',  # Ages 0-17 in poverty
            'SAEPOV5_17R_PT', # Ages 5-17 related in poverty
            'SAEMHI_PT',      # Median household income estimate
            'YEAR',
        ]

        if county_fips == "*":
            geography = f"county:*&in=state:{state_fips}"
        else:
            geography = f"county:{county_fips}&in=state:{state_fips}"

        # SAIPE is a timeseries dataset
        base_url = f"{self.BASE_URL}/timeseries/poverty/saipe"
        params = {
            'get': ','.join(variables),
            'for': geography,
            'time': year,
        }
        if self.api_key:
            params['key'] = self.api_key

        url = f"{base_url}?{urlencode(params)}"
        data = await self._make_request(url)

        records = []
        parsed = self._parse_response(data)

        for row in parsed:
            records.append({
                'geography_id': f"{row.get('state', state_fips)}{row.get('county', '')}",
                'geography_name': row.get('NAME', ''),
                'state_fips': row.get('state'),
                'county_fips': row.get('county'),
                'year': year,
                'all_ages_poverty': self._safe_int(row.get('SAEPOVALL_PT')),
                'all_ages_poverty_moe': self._safe_int(row.get('SAEPOVALL_MOE')),
                'children_0_17_poverty': self._safe_int(row.get('SAEPOV0_17_PT')),
                'children_5_17_poverty': self._safe_int(row.get('SAEPOV5_17R_PT')),
                'median_household_income': self._safe_float(row.get('SAEMHI_PT')),
                'source_url': url,
            })

        logger.info(f"Retrieved {len(records)} SAIPE records")
        return records

    async def get_health_insurance(
        self,
        state_fips: str,
        county_fips: str = "*",
        year: int = 2022
    ) -> List[Dict[str, Any]]:
        """
        Get Small Area Health Insurance Estimates (SAHIE).

        Args:
            state_fips: State FIPS code
            county_fips: County FIPS code
            year: Data year

        Returns:
            List of health insurance estimate records
        """
        logger.info(f"Getting SAHIE data for state {state_fips}")

        variables = [
            'NAME',
            'NIC_PT',    # Number insured estimate
            'NUI_PT',    # Number uninsured estimate
            'PCTUI_PT',  # Percent uninsured
            'YEAR',
        ]

        if county_fips == "*":
            geography = f"county:*&in=state:{state_fips}"
        else:
            geography = f"county:{county_fips}&in=state:{state_fips}"

        # SAHIE is a timeseries dataset
        base_url = f"{self.BASE_URL}/timeseries/healthins/sahie"
        params = {
            'get': ','.join(variables),
            'for': geography,
            'time': year,
        }
        if self.api_key:
            params['key'] = self.api_key

        url = f"{base_url}?{urlencode(params)}"
        data = await self._make_request(url)

        records = []
        parsed = self._parse_response(data)

        for row in parsed:
            records.append({
                'geography_id': f"{row.get('state', state_fips)}{row.get('county', '')}",
                'geography_name': row.get('NAME', ''),
                'state_fips': row.get('state'),
                'county_fips': row.get('county'),
                'year': year,
                'number_insured': self._safe_int(row.get('NIC_PT')),
                'number_uninsured': self._safe_int(row.get('NUI_PT')),
                'percent_uninsured': self._safe_float(row.get('PCTUI_PT')),
                'source_url': url,
            })

        logger.info(f"Retrieved {len(records)} SAHIE records")
        return records

    async def get_population_estimates(
        self,
        state_fips: str,
        county_fips: str = "*",
        vintage: int = 2023
    ) -> List[PopulationEstimate]:
        """
        Get Population Estimates Program (PEP) data.

        Args:
            state_fips: State FIPS code
            county_fips: County FIPS code
            vintage: Estimates vintage year

        Returns:
            List of population estimate records
        """
        logger.info(f"Getting PEP data for state {state_fips}")

        # PEP dataset path varies by vintage
        if vintage >= 2020:
            dataset = f"pep/charagegroups"
        else:
            dataset = f"pep/population"

        variables = [
            'NAME',
            'POP',       # Population
        ]

        if county_fips == "*":
            geography = f"county:*&in=state:{state_fips}"
        else:
            geography = f"county:{county_fips}&in=state:{state_fips}"

        url = self._build_url(vintage, dataset, variables, geography)
        data = await self._make_request(url)

        records = []
        parsed = self._parse_response(data)

        for row in parsed:
            state = row.get('state', state_fips)
            county = row.get('county', '')

            record = PopulationEstimate(
                geography_id=f"{state}{county}",
                geography_name=row.get('NAME', ''),
                state_fips=state,
                county_fips=county,
                year=vintage,
                population=self._safe_int(row.get('POP')),
                source_url=url,
                raw_data=row,
            )
            records.append(record)

        logger.info(f"Retrieved {len(records)} PEP records")
        return records

    async def get_state_data(
        self,
        state_fips: str = "*",
        variables: List[str] = None,
        year: int = 2022,
        dataset: CensusDataset = CensusDataset.ACS_5YEAR
    ) -> List[CensusRecord]:
        """
        Get state-level data.

        Args:
            state_fips: State FIPS code (* for all states)
            variables: Variable codes to retrieve
            year: Data year
            dataset: Census dataset to use

        Returns:
            List of census records at state level
        """
        logger.info(f"Getting state data for {state_fips}")

        if variables is None:
            variables = [
                'NAME',
                'B01003_001E',  # Population
                'B19013_001E',  # Median income
                'B25077_001E',  # Median home value
            ]
        elif 'NAME' not in variables:
            variables = ['NAME'] + variables

        geography = f"state:{state_fips}"
        url = self._build_url(year, dataset, variables, geography)
        data = await self._make_request(url)

        records = []
        parsed = self._parse_response(data)

        for row in parsed:
            state = row.get('state', state_fips)

            record = CensusRecord(
                geography_id=state,
                geography_name=row.get('NAME', ''),
                geography_level=GeographyLevel.STATE,
                state_fips=state,
                dataset=dataset,
                year=year,
                population=self._safe_int(row.get('B01003_001E')),
                median_income=self._safe_float(row.get('B19013_001E')),
                variables={k: v for k, v in row.items() if k not in ['NAME', 'state']},
                source_url=url,
                raw_data=row,
            )
            records.append(record)

        logger.info(f"Retrieved {len(records)} state records")
        return records

    async def search_variables(
        self,
        keyword: str,
        dataset: CensusDataset = CensusDataset.ACS_5YEAR,
        year: int = 2022
    ) -> List[Dict[str, str]]:
        """
        Search for Census variable codes by keyword.

        Args:
            keyword: Search keyword
            dataset: Dataset to search
            year: Data year

        Returns:
            List of matching variables with codes and descriptions
        """
        logger.info(f"Searching Census variables: {keyword}")

        # Fetch the variables JSON for the dataset
        dataset_path = dataset.value if isinstance(dataset, CensusDataset) else dataset
        url = f"{self.BASE_URL}/{year}/{dataset_path}/variables.json"

        await self._rate_limit()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        logger.warning(f"Could not fetch variables list: {response.status}")
                        return []

                    data = await response.json()
                    variables_dict = data.get('variables', {})

                    results = []
                    keyword_lower = keyword.lower()

                    for var_code, var_info in variables_dict.items():
                        label = var_info.get('label', '')
                        concept = var_info.get('concept', '')

                        if keyword_lower in label.lower() or keyword_lower in concept.lower():
                            results.append({
                                'code': var_code,
                                'label': label,
                                'concept': concept,
                                'predicate_type': var_info.get('predicateType', ''),
                            })

                    logger.info(f"Found {len(results)} matching variables")
                    return results[:100]  # Limit results

            except Exception as e:
                logger.error(f"Error searching variables: {e}")
                return []

    async def get_geography_codes(
        self,
        geography_level: GeographyLevel,
        state_fips: str = "*"
    ) -> List[Dict[str, str]]:
        """
        Get geography codes for a level.

        Args:
            geography_level: Geographic level
            state_fips: State filter

        Returns:
            List of geography codes and names
        """
        logger.info(f"Getting geography codes for {geography_level.value}")

        # Use NAME variable to get geography names
        variables = ['NAME']

        if geography_level == GeographyLevel.STATE:
            geography = f"state:{state_fips}"
        elif geography_level == GeographyLevel.COUNTY:
            if state_fips == "*":
                geography = "county:*"
            else:
                geography = f"county:*&in=state:{state_fips}"
        elif geography_level == GeographyLevel.PLACE:
            if state_fips == "*":
                return []  # Too many places without state filter
            geography = f"place:*&in=state:{state_fips}"
        else:
            logger.warning(f"Geography level {geography_level} not supported for code lookup")
            return []

        url = self._build_url(2022, CensusDataset.ACS_5YEAR, variables, geography)
        data = await self._make_request(url)

        codes = []
        parsed = self._parse_response(data)

        for row in parsed:
            code_dict = {'name': row.get('NAME', '')}

            if 'state' in row:
                code_dict['state_fips'] = row['state']
            if 'county' in row:
                code_dict['county_fips'] = row['county']
            if 'place' in row:
                code_dict['place_fips'] = row['place']

            codes.append(code_dict)

        logger.info(f"Retrieved {len(codes)} geography codes")
        return codes

    async def get_decennial_population(
        self,
        state_fips: str,
        county_fips: str = "*",
        census_year: int = 2020
    ) -> List[CensusRecord]:
        """
        Get Decennial Census population data.

        Args:
            state_fips: State FIPS code
            county_fips: County FIPS code
            census_year: Census year (2010 or 2020)

        Returns:
            List of census records with decennial data
        """
        logger.info(f"Getting {census_year} decennial census for state {state_fips}")

        if census_year == 2020:
            dataset = CensusDataset.DECENNIAL_2020
            # 2020 PL data variables
            variables = ['NAME', 'P1_001N']  # Total population
        else:
            dataset = CensusDataset.DECENNIAL_2010
            variables = ['NAME', 'P001001']  # Total population

        if county_fips == "*":
            geography = f"county:*&in=state:{state_fips}"
        else:
            geography = f"county:{county_fips}&in=state:{state_fips}"

        url = self._build_url(census_year, dataset, variables, geography)
        data = await self._make_request(url)

        records = []
        parsed = self._parse_response(data)

        pop_var = 'P1_001N' if census_year == 2020 else 'P001001'

        for row in parsed:
            state = row.get('state', state_fips)
            county = row.get('county', '')

            record = CensusRecord(
                geography_id=f"{state}{county}",
                geography_name=row.get('NAME', ''),
                geography_level=GeographyLevel.COUNTY,
                state_fips=state,
                county_fips=county,
                dataset=dataset,
                year=census_year,
                population=self._safe_int(row.get(pop_var)),
                variables={'total_population': self._safe_int(row.get(pop_var))},
                source_url=url,
                raw_data=row,
            )
            records.append(record)

        logger.info(f"Retrieved {len(records)} decennial census records")
        return records

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get coverage statistics."""
        return {
            'category': self.CATEGORY,
            'display_name': self.DISPLAY_NAME,
            'datasets': [d.value for d in CensusDataset],
            'geography_levels': [g.value for g in GeographyLevel],
            'variable_categories': list(self.variables.keys()),
            'auth_required': 'Optional (increases rate limit)',
            'rate_limit': self.config['rate_limit_no_key'] if not self.api_key else 'unlimited',
            'api_key_present': bool(self.api_key),
            'state_fips_codes': len(STATE_FIPS),
        }


# Synchronous wrappers for backward compatibility
def get_census_scraper(api_key: str = None) -> CensusApiScraper:
    """Get Census API scraper instance."""
    return CensusApiScraper(api_key=api_key)


def get_county_demographics(
    state_fips: str,
    county_fips: str = "*",
    year: int = 2022
) -> List[Dict[str, Any]]:
    """Get demographics for a county (synchronous wrapper)."""
    scraper = get_census_scraper()
    loop = asyncio.get_event_loop()
    records = loop.run_until_complete(scraper.get_demographics(state_fips, county_fips, year))
    return [r.to_dict() for r in records]


def get_county_population(
    state_fips: str,
    county_fips: str = "*",
    year: int = 2022
) -> List[Dict[str, Any]]:
    """Get population for a county (synchronous wrapper)."""
    scraper = get_census_scraper()
    loop = asyncio.get_event_loop()
    records = loop.run_until_complete(scraper.get_population(state_fips, county_fips, year))
    return [r.to_dict() for r in records]


def get_available_datasets() -> Dict[str, str]:
    """Get all available Census datasets."""
    return {d.name: d.value for d in CensusDataset}


def get_common_variables() -> Dict[str, Dict[str, str]]:
    """Get commonly used Census variable codes."""
    return COMMON_VARIABLES


def get_state_fips(state_abbr: str) -> Optional[str]:
    """Get FIPS code for state abbreviation."""
    return STATE_FIPS.get(state_abbr.upper())


def get_all_state_fips() -> Dict[str, str]:
    """Get all state FIPS codes."""
    return STATE_FIPS.copy()
