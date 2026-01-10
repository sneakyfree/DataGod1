"""
DataGod Scrapers Package
Comprehensive public records data collection from multiple jurisdictions
"""

# Base classes
from datagod.scrapers.base_scraper import BaseScraper
from datagod.scrapers.base_api_integration import (
    BaseAPIIntegration,
    APIKeyAuthentication,
    OAuth2Authentication,
    HMACAuthentication,
    APIIntegrationMetrics,
    RateLimitExceeded,
    APIAuthenticationError,
    APIDataError
)

# State-specific APIs
from datagod.scrapers.florida_api import (
    FloridaPropertyAppraiserAPI,
    FloridaMiamiDadeAPI,
    FloridaBrowardAPI
)

from datagod.scrapers.texas_api import (
    TexasCountyAPI,
    HarrisCountyAPI,
    DallasCountyAPI,
    TravisCountyAPI
)

from datagod.scrapers.california_api import (
    CaliforniaCountyAPI,
    CaliforniaSecretaryOfStateAPI,
    LosAngelesCountyAPI,
    SanDiegoCountyAPI,
    SanFranciscoCountyAPI,
    SantaClaraCountyAPI
)

from datagod.scrapers.newyork_api import (
    NewYorkCountyAPI,
    NYCACRISApi,
    NassauCountyAPI,
    SuffolkCountyAPI
)

from datagod.scrapers.illinois_api import (
    IllinoisCountyAPI,
    CookCountyAPI,
    DuPageCountyAPI,
    LakeCountyILAPI,
    WillCountyAPI
)

from datagod.scrapers.pennsylvania_api import (
    PennsylvaniaCountyAPI,
    PhiladelphiaCountyAPI,
    AlleghenyCountyAPI,
    MontgomeryCountyPAAPI,
    BucksCountyAPI
)

from datagod.scrapers.arizona_api import (
    ArizonaCountyAPI,
    MaricopaCountyAPI,
    PimaCountyAPI
)

from datagod.scrapers.georgia_api import (
    GeorgiaCountyAPI,
    FultonCountyAPI,
    DeKalbCountyAPI,
    CobbCountyAPI,
    GwinnettCountyAPI
)

from datagod.scrapers.ohio_api import (
    OhioCountyAPI,
    CuyahogaCountyAPI,
    FranklinCountyAPI,
    HamiltonCountyAPI
)

from datagod.scrapers.washington_api import (
    WashingtonCountyAPI,
    KingCountyAPI,
    PierceCountyAPI,
    SnohomishCountyAPI
)

from datagod.scrapers.colorado_api import (
    ColoradoCountyAPI,
    DenverCountyAPI,
    ElPasoCountyAPI,
    ArapahoeCountyAPI,
    JeffersonCountyAPI
)

from datagod.scrapers.northcarolina_api import (
    NorthCarolinaCountyAPI,
    MecklenburgCountyAPI,
    WakeCountyAPI,
    GuilfordCountyAPI,
    DurhamCountyAPI
)

from datagod.scrapers.virginia_api import (
    VirginiaCountyAPI,
    FairfaxCountyAPI,
    VirginiaBeachCityAPI,
    PrinceWilliamCountyAPI,
    LoudounCountyAPI
)

from datagod.scrapers.newjersey_api import (
    NewJerseyCountyAPI,
    BergenCountyAPI,
    MiddlesexCountyAPI,
    EssexCountyAPI,
    HudsonCountyAPI,
    MonmouthCountyAPI
)

# Scraper registry - maps state codes to their API classes
SCRAPER_REGISTRY = {
    'FL': {
        'default': FloridaPropertyAppraiserAPI,
        'miami-dade': FloridaMiamiDadeAPI,
        'broward': FloridaBrowardAPI,
    },
    'TX': {
        'default': TexasCountyAPI,
        'harris': HarrisCountyAPI,
        'dallas': DallasCountyAPI,
        'travis': TravisCountyAPI,
    },
    'CA': {
        'default': CaliforniaCountyAPI,
        'los-angeles': LosAngelesCountyAPI,
        'san-diego': SanDiegoCountyAPI,
        'san-francisco': SanFranciscoCountyAPI,
        'santa-clara': SantaClaraCountyAPI,
        'sos': CaliforniaSecretaryOfStateAPI,
    },
    'NY': {
        'default': NewYorkCountyAPI,
        'new-york': NYCACRISApi,
        'kings': NYCACRISApi,
        'queens': NYCACRISApi,
        'bronx': NYCACRISApi,
        'richmond': NYCACRISApi,
        'nassau': NassauCountyAPI,
        'suffolk': SuffolkCountyAPI,
    },
    'IL': {
        'default': IllinoisCountyAPI,
        'cook': CookCountyAPI,
        'dupage': DuPageCountyAPI,
        'lake': LakeCountyILAPI,
        'will': WillCountyAPI,
    },
    'PA': {
        'default': PennsylvaniaCountyAPI,
        'philadelphia': PhiladelphiaCountyAPI,
        'allegheny': AlleghenyCountyAPI,
        'montgomery': MontgomeryCountyPAAPI,
        'bucks': BucksCountyAPI,
    },
    'AZ': {
        'default': ArizonaCountyAPI,
        'maricopa': MaricopaCountyAPI,
        'pima': PimaCountyAPI,
    },
    'GA': {
        'default': GeorgiaCountyAPI,
        'fulton': FultonCountyAPI,
        'dekalb': DeKalbCountyAPI,
        'cobb': CobbCountyAPI,
        'gwinnett': GwinnettCountyAPI,
    },
    'OH': {
        'default': OhioCountyAPI,
        'cuyahoga': CuyahogaCountyAPI,
        'franklin': FranklinCountyAPI,
        'hamilton': HamiltonCountyAPI,
    },
    'WA': {
        'default': WashingtonCountyAPI,
        'king': KingCountyAPI,
        'pierce': PierceCountyAPI,
        'snohomish': SnohomishCountyAPI,
    },
    'CO': {
        'default': ColoradoCountyAPI,
        'denver': DenverCountyAPI,
        'el-paso': ElPasoCountyAPI,
        'arapahoe': ArapahoeCountyAPI,
        'jefferson': JeffersonCountyAPI,
    },
    'NC': {
        'default': NorthCarolinaCountyAPI,
        'mecklenburg': MecklenburgCountyAPI,
        'wake': WakeCountyAPI,
        'guilford': GuilfordCountyAPI,
        'durham': DurhamCountyAPI,
    },
    'VA': {
        'default': VirginiaCountyAPI,
        'fairfax': FairfaxCountyAPI,
        'virginia-beach': VirginiaBeachCityAPI,
        'prince-william': PrinceWilliamCountyAPI,
        'loudoun': LoudounCountyAPI,
    },
    'NJ': {
        'default': NewJerseyCountyAPI,
        'bergen': BergenCountyAPI,
        'middlesex': MiddlesexCountyAPI,
        'essex': EssexCountyAPI,
        'hudson': HudsonCountyAPI,
        'monmouth': MonmouthCountyAPI,
    },
}

# Count of supported jurisdictions
SUPPORTED_COUNTIES = {
    'FL': 6,   # Miami-Dade, Broward, Palm Beach, Hillsborough, Orange, Duval
    'TX': 10,  # Harris, Dallas, Tarrant, Bexar, Travis, Collin, Denton, Fort-Bend, El-Paso, Hidalgo
    'CA': 15,  # Los Angeles, San Diego, Orange, Riverside, San Bernardino, Santa Clara, Alameda, Sacramento, etc.
    'NY': 12,  # NYC boroughs (5), Nassau, Suffolk, Westchester, Erie, Monroe, Albany, Onondaga
    'IL': 10,  # Cook, DuPage, Lake, Will, Kane, McHenry, Winnebago, Madison, St. Clair, Champaign
    'PA': 12,  # Philadelphia, Allegheny, Montgomery, Bucks, Delaware, Chester, Lancaster, York, Berks, Lehigh, etc.
    'AZ': 8,   # Maricopa, Pima, Pinal, Yavapai, Mohave, Yuma, Cochise, Coconino
    'GA': 10,  # Fulton, DeKalb, Cobb, Gwinnett, Chatham, Clayton, Cherokee, Forsyth, Henry, Hall
    'OH': 10,  # Cuyahoga, Franklin, Hamilton, Summit, Montgomery, Lucas, Butler, Stark, Lorain, Mahoning
    'WA': 8,   # King, Pierce, Snohomish, Clark, Spokane, Thurston, Kitsap, Whatcom
    'CO': 8,   # Denver, El Paso, Arapahoe, Jefferson, Adams, Douglas, Boulder, Larimer
    'NC': 10,  # Mecklenburg, Wake, Guilford, Forsyth, Durham, Cumberland, Buncombe, Union, Cabarrus, New Hanover
    'VA': 8,   # Fairfax, Virginia Beach, Prince William, Loudoun, Chesterfield, Henrico, Norfolk, Chesapeake
    'NJ': 10,  # Bergen, Middlesex, Essex, Hudson, Monmouth, Ocean, Union, Passaic, Camden, Morris
}

TOTAL_SUPPORTED_COUNTIES = sum(SUPPORTED_COUNTIES.values())  # 137 counties (14 states)


def get_scraper_for_jurisdiction(state: str, county: str = None) -> type:
    """
    Get the appropriate scraper class for a jurisdiction.

    Args:
        state: Two-letter state code (e.g., 'CA', 'TX')
        county: County name (optional, will use default if not provided)

    Returns:
        The appropriate scraper class
    """
    state = state.upper()

    if state not in SCRAPER_REGISTRY:
        raise ValueError(f"No scraper available for state: {state}")

    state_scrapers = SCRAPER_REGISTRY[state]

    if county:
        county_key = county.lower().replace(' ', '-')
        if county_key in state_scrapers:
            return state_scrapers[county_key]

    return state_scrapers['default']


def list_supported_states() -> list:
    """Get list of supported state codes."""
    return list(SCRAPER_REGISTRY.keys())


def list_supported_counties(state: str) -> list:
    """Get list of specialized county scrapers for a state."""
    state = state.upper()
    if state not in SCRAPER_REGISTRY:
        return []

    return [k for k in SCRAPER_REGISTRY[state].keys() if k != 'default']


__all__ = [
    # Base classes
    'BaseScraper',
    'BaseAPIIntegration',
    'APIKeyAuthentication',
    'OAuth2Authentication',
    'HMACAuthentication',
    'APIIntegrationMetrics',
    'RateLimitExceeded',
    'APIAuthenticationError',
    'APIDataError',

    # Florida
    'FloridaPropertyAppraiserAPI',
    'FloridaMiamiDadeAPI',
    'FloridaBrowardAPI',

    # Texas
    'TexasCountyAPI',
    'HarrisCountyAPI',
    'DallasCountyAPI',
    'TravisCountyAPI',

    # California
    'CaliforniaCountyAPI',
    'CaliforniaSecretaryOfStateAPI',
    'LosAngelesCountyAPI',
    'SanDiegoCountyAPI',
    'SanFranciscoCountyAPI',
    'SantaClaraCountyAPI',

    # New York
    'NewYorkCountyAPI',
    'NYCACRISApi',
    'NassauCountyAPI',
    'SuffolkCountyAPI',

    # Illinois
    'IllinoisCountyAPI',
    'CookCountyAPI',
    'DuPageCountyAPI',
    'LakeCountyILAPI',
    'WillCountyAPI',

    # Pennsylvania
    'PennsylvaniaCountyAPI',
    'PhiladelphiaCountyAPI',
    'AlleghenyCountyAPI',
    'MontgomeryCountyPAAPI',
    'BucksCountyAPI',

    # Arizona
    'ArizonaCountyAPI',
    'MaricopaCountyAPI',
    'PimaCountyAPI',

    # Georgia
    'GeorgiaCountyAPI',
    'FultonCountyAPI',
    'DeKalbCountyAPI',
    'CobbCountyAPI',
    'GwinnettCountyAPI',

    # Ohio
    'OhioCountyAPI',
    'CuyahogaCountyAPI',
    'FranklinCountyAPI',
    'HamiltonCountyAPI',

    # Washington
    'WashingtonCountyAPI',
    'KingCountyAPI',
    'PierceCountyAPI',
    'SnohomishCountyAPI',

    # Colorado
    'ColoradoCountyAPI',
    'DenverCountyAPI',
    'ElPasoCountyAPI',
    'ArapahoeCountyAPI',
    'JeffersonCountyAPI',

    # North Carolina
    'NorthCarolinaCountyAPI',
    'MecklenburgCountyAPI',
    'WakeCountyAPI',
    'GuilfordCountyAPI',
    'DurhamCountyAPI',

    # Virginia
    'VirginiaCountyAPI',
    'FairfaxCountyAPI',
    'VirginiaBeachCityAPI',
    'PrinceWilliamCountyAPI',
    'LoudounCountyAPI',

    # New Jersey
    'NewJerseyCountyAPI',
    'BergenCountyAPI',
    'MiddlesexCountyAPI',
    'EssexCountyAPI',
    'HudsonCountyAPI',
    'MonmouthCountyAPI',

    # Registry and utilities
    'SCRAPER_REGISTRY',
    'SUPPORTED_COUNTIES',
    'TOTAL_SUPPORTED_COUNTIES',
    'get_scraper_for_jurisdiction',
    'list_supported_states',
    'list_supported_counties',
]
