#!/usr/bin/env python3
"""
Seed US Jurisdictions Data

This script populates the database with US county jurisdictions data.
Includes all 50 states and major counties with population data.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Top 100 US Counties by Population (2023 estimates)
US_COUNTIES = [
    # California
    {"name": "Los Angeles County", "state": "CA", "county": "Los Angeles", "population": 9829544, "api_available": True},
    {"name": "San Diego County", "state": "CA", "county": "San Diego", "population": 3286069, "api_available": True},
    {"name": "Orange County", "state": "CA", "county": "Orange", "population": 3167809, "api_available": True},
    {"name": "Riverside County", "state": "CA", "county": "Riverside", "population": 2450758, "api_available": False},
    {"name": "San Bernardino County", "state": "CA", "county": "San Bernardino", "population": 2171603, "api_available": False},
    {"name": "Santa Clara County", "state": "CA", "county": "Santa Clara", "population": 1936259, "api_available": True},
    {"name": "Alameda County", "state": "CA", "county": "Alameda", "population": 1671329, "api_available": True},
    {"name": "Sacramento County", "state": "CA", "county": "Sacramento", "population": 1552058, "api_available": True},
    {"name": "Contra Costa County", "state": "CA", "county": "Contra Costa", "population": 1153526, "api_available": False},
    {"name": "Fresno County", "state": "CA", "county": "Fresno", "population": 1008654, "api_available": False},

    # Texas
    {"name": "Harris County", "state": "TX", "county": "Harris", "population": 4731145, "api_available": True},
    {"name": "Dallas County", "state": "TX", "county": "Dallas", "population": 2613539, "api_available": True},
    {"name": "Tarrant County", "state": "TX", "county": "Tarrant", "population": 2110640, "api_available": True},
    {"name": "Bexar County", "state": "TX", "county": "Bexar", "population": 2009324, "api_available": True},
    {"name": "Travis County", "state": "TX", "county": "Travis", "population": 1290188, "api_available": True},
    {"name": "Collin County", "state": "TX", "county": "Collin", "population": 1064465, "api_available": False},
    {"name": "Hidalgo County", "state": "TX", "county": "Hidalgo", "population": 868707, "api_available": False},
    {"name": "El Paso County", "state": "TX", "county": "El Paso", "population": 865657, "api_available": False},
    {"name": "Denton County", "state": "TX", "county": "Denton", "population": 906422, "api_available": False},
    {"name": "Fort Bend County", "state": "TX", "county": "Fort Bend", "population": 811688, "api_available": False},

    # Florida
    {"name": "Miami-Dade County", "state": "FL", "county": "Miami-Dade", "population": 2716940, "api_available": True},
    {"name": "Broward County", "state": "FL", "county": "Broward", "population": 1944375, "api_available": True},
    {"name": "Palm Beach County", "state": "FL", "county": "Palm Beach", "population": 1492191, "api_available": True},
    {"name": "Hillsborough County", "state": "FL", "county": "Hillsborough", "population": 1459762, "api_available": True},
    {"name": "Orange County", "state": "FL", "county": "Orange", "population": 1393452, "api_available": True},
    {"name": "Pinellas County", "state": "FL", "county": "Pinellas", "population": 959107, "api_available": False},
    {"name": "Duval County", "state": "FL", "county": "Duval", "population": 995567, "api_available": True},
    {"name": "Lee County", "state": "FL", "county": "Lee", "population": 760822, "api_available": False},
    {"name": "Polk County", "state": "FL", "county": "Polk", "population": 725046, "api_available": False},
    {"name": "Brevard County", "state": "FL", "county": "Brevard", "population": 601942, "api_available": False},

    # New York
    {"name": "Kings County (Brooklyn)", "state": "NY", "county": "Kings", "population": 2590516, "api_available": True},
    {"name": "Queens County", "state": "NY", "county": "Queens", "population": 2278906, "api_available": True},
    {"name": "New York County (Manhattan)", "state": "NY", "county": "New York", "population": 1596273, "api_available": True},
    {"name": "Suffolk County", "state": "NY", "county": "Suffolk", "population": 1525920, "api_available": True},
    {"name": "Bronx County", "state": "NY", "county": "Bronx", "population": 1379946, "api_available": True},
    {"name": "Nassau County", "state": "NY", "county": "Nassau", "population": 1369514, "api_available": True},
    {"name": "Westchester County", "state": "NY", "county": "Westchester", "population": 1004457, "api_available": False},
    {"name": "Erie County", "state": "NY", "county": "Erie", "population": 954236, "api_available": False},
    {"name": "Richmond County (Staten Island)", "state": "NY", "county": "Richmond", "population": 495747, "api_available": True},

    # Illinois
    {"name": "Cook County", "state": "IL", "county": "Cook", "population": 5150233, "api_available": True},
    {"name": "DuPage County", "state": "IL", "county": "DuPage", "population": 932877, "api_available": False},
    {"name": "Lake County", "state": "IL", "county": "Lake", "population": 714342, "api_available": False},
    {"name": "Will County", "state": "IL", "county": "Will", "population": 696355, "api_available": False},
    {"name": "Kane County", "state": "IL", "county": "Kane", "population": 516522, "api_available": False},

    # Pennsylvania
    {"name": "Philadelphia County", "state": "PA", "county": "Philadelphia", "population": 1576251, "api_available": True},
    {"name": "Allegheny County", "state": "PA", "county": "Allegheny", "population": 1250578, "api_available": True},
    {"name": "Montgomery County", "state": "PA", "county": "Montgomery", "population": 856553, "api_available": False},
    {"name": "Bucks County", "state": "PA", "county": "Bucks", "population": 646538, "api_available": False},
    {"name": "Delaware County", "state": "PA", "county": "Delaware", "population": 576830, "api_available": False},

    # Arizona
    {"name": "Maricopa County", "state": "AZ", "county": "Maricopa", "population": 4485414, "api_available": True},
    {"name": "Pima County", "state": "AZ", "county": "Pima", "population": 1043433, "api_available": False},
    {"name": "Pinal County", "state": "AZ", "county": "Pinal", "population": 450610, "api_available": False},

    # Ohio
    {"name": "Cuyahoga County", "state": "OH", "county": "Cuyahoga", "population": 1264817, "api_available": True},
    {"name": "Franklin County", "state": "OH", "county": "Franklin", "population": 1316756, "api_available": True},
    {"name": "Hamilton County", "state": "OH", "county": "Hamilton", "population": 830639, "api_available": False},
    {"name": "Summit County", "state": "OH", "county": "Summit", "population": 540428, "api_available": False},
    {"name": "Montgomery County", "state": "OH", "county": "Montgomery", "population": 537309, "api_available": False},

    # Georgia
    {"name": "Fulton County", "state": "GA", "county": "Fulton", "population": 1066710, "api_available": True},
    {"name": "Gwinnett County", "state": "GA", "county": "Gwinnett", "population": 957062, "api_available": False},
    {"name": "Cobb County", "state": "GA", "county": "Cobb", "population": 766149, "api_available": False},
    {"name": "DeKalb County", "state": "GA", "county": "DeKalb", "population": 764382, "api_available": False},

    # Michigan
    {"name": "Wayne County", "state": "MI", "county": "Wayne", "population": 1793561, "api_available": True},
    {"name": "Oakland County", "state": "MI", "county": "Oakland", "population": 1274395, "api_available": False},
    {"name": "Macomb County", "state": "MI", "county": "Macomb", "population": 881217, "api_available": False},
    {"name": "Kent County", "state": "MI", "county": "Kent", "population": 657974, "api_available": False},

    # North Carolina
    {"name": "Mecklenburg County", "state": "NC", "county": "Mecklenburg", "population": 1115482, "api_available": True},
    {"name": "Wake County", "state": "NC", "county": "Wake", "population": 1129410, "api_available": True},
    {"name": "Guilford County", "state": "NC", "county": "Guilford", "population": 541299, "api_available": False},
    {"name": "Forsyth County", "state": "NC", "county": "Forsyth", "population": 382590, "api_available": False},

    # New Jersey
    {"name": "Bergen County", "state": "NJ", "county": "Bergen", "population": 955732, "api_available": False},
    {"name": "Middlesex County", "state": "NJ", "county": "Middlesex", "population": 863162, "api_available": False},
    {"name": "Essex County", "state": "NJ", "county": "Essex", "population": 863728, "api_available": False},
    {"name": "Hudson County", "state": "NJ", "county": "Hudson", "population": 724854, "api_available": False},

    # Virginia
    {"name": "Fairfax County", "state": "VA", "county": "Fairfax", "population": 1150309, "api_available": True},
    {"name": "Prince William County", "state": "VA", "county": "Prince William", "population": 482204, "api_available": False},
    {"name": "Virginia Beach City", "state": "VA", "county": "Virginia Beach", "population": 459470, "api_available": False},
    {"name": "Loudoun County", "state": "VA", "county": "Loudoun", "population": 420959, "api_available": False},

    # Washington
    {"name": "King County", "state": "WA", "county": "King", "population": 2269675, "api_available": True},
    {"name": "Pierce County", "state": "WA", "county": "Pierce", "population": 921130, "api_available": False},
    {"name": "Snohomish County", "state": "WA", "county": "Snohomish", "population": 822083, "api_available": False},

    # Massachusetts
    {"name": "Middlesex County", "state": "MA", "county": "Middlesex", "population": 1632002, "api_available": True},
    {"name": "Suffolk County", "state": "MA", "county": "Suffolk", "population": 797936, "api_available": True},
    {"name": "Worcester County", "state": "MA", "county": "Worcester", "population": 862111, "api_available": False},
    {"name": "Essex County", "state": "MA", "county": "Essex", "population": 809829, "api_available": False},

    # Maryland
    {"name": "Montgomery County", "state": "MD", "county": "Montgomery", "population": 1062061, "api_available": True},
    {"name": "Prince George's County", "state": "MD", "county": "Prince George's", "population": 967201, "api_available": False},
    {"name": "Baltimore County", "state": "MD", "county": "Baltimore", "population": 854535, "api_available": False},
    {"name": "Baltimore City", "state": "MD", "county": "Baltimore City", "population": 585708, "api_available": True},

    # Colorado
    {"name": "Denver County", "state": "CO", "county": "Denver", "population": 715522, "api_available": True},
    {"name": "El Paso County", "state": "CO", "county": "El Paso", "population": 730395, "api_available": False},
    {"name": "Arapahoe County", "state": "CO", "county": "Arapahoe", "population": 656590, "api_available": False},
    {"name": "Jefferson County", "state": "CO", "county": "Jefferson", "population": 582881, "api_available": False},
    {"name": "Adams County", "state": "CO", "county": "Adams", "population": 519572, "api_available": False},

    # Nevada
    {"name": "Clark County", "state": "NV", "county": "Clark", "population": 2265461, "api_available": True},
    {"name": "Washoe County", "state": "NV", "county": "Washoe", "population": 490486, "api_available": False},

    # Tennessee
    {"name": "Shelby County", "state": "TN", "county": "Shelby", "population": 929744, "api_available": True},
    {"name": "Davidson County", "state": "TN", "county": "Davidson", "population": 715884, "api_available": True},
    {"name": "Knox County", "state": "TN", "county": "Knox", "population": 478971, "api_available": False},

    # Missouri
    {"name": "St. Louis County", "state": "MO", "county": "St. Louis", "population": 1004125, "api_available": True},
    {"name": "Jackson County", "state": "MO", "county": "Jackson", "population": 717204, "api_available": False},
    {"name": "St. Louis City", "state": "MO", "county": "St. Louis City", "population": 301578, "api_available": True},

    # Indiana
    {"name": "Marion County", "state": "IN", "county": "Marion", "population": 977203, "api_available": True},
    {"name": "Lake County", "state": "IN", "county": "Lake", "population": 498700, "api_available": False},
    {"name": "Allen County", "state": "IN", "county": "Allen", "population": 385438, "api_available": False},

    # Wisconsin
    {"name": "Milwaukee County", "state": "WI", "county": "Milwaukee", "population": 939489, "api_available": True},
    {"name": "Dane County", "state": "WI", "county": "Dane", "population": 561504, "api_available": False},
    {"name": "Waukesha County", "state": "WI", "county": "Waukesha", "population": 406978, "api_available": False},

    # Minnesota
    {"name": "Hennepin County", "state": "MN", "county": "Hennepin", "population": 1281565, "api_available": True},
    {"name": "Ramsey County", "state": "MN", "county": "Ramsey", "population": 552352, "api_available": False},
    {"name": "Dakota County", "state": "MN", "county": "Dakota", "population": 439882, "api_available": False},

    # Oregon
    {"name": "Multnomah County", "state": "OR", "county": "Multnomah", "population": 815428, "api_available": True},
    {"name": "Washington County", "state": "OR", "county": "Washington", "population": 600372, "api_available": False},
    {"name": "Clackamas County", "state": "OR", "county": "Clackamas", "population": 421401, "api_available": False},

    # South Carolina
    {"name": "Greenville County", "state": "SC", "county": "Greenville", "population": 523542, "api_available": False},
    {"name": "Richland County", "state": "SC", "county": "Richland", "population": 415759, "api_available": False},
    {"name": "Charleston County", "state": "SC", "county": "Charleston", "population": 408235, "api_available": False},

    # Alabama
    {"name": "Jefferson County", "state": "AL", "county": "Jefferson", "population": 674721, "api_available": False},
    {"name": "Mobile County", "state": "AL", "county": "Mobile", "population": 414809, "api_available": False},

    # Louisiana
    {"name": "East Baton Rouge Parish", "state": "LA", "county": "East Baton Rouge", "population": 456781, "api_available": False},
    {"name": "Jefferson Parish", "state": "LA", "county": "Jefferson", "population": 440781, "api_available": False},
    {"name": "Orleans Parish", "state": "LA", "county": "Orleans", "population": 383997, "api_available": True},

    # Kentucky
    {"name": "Jefferson County", "state": "KY", "county": "Jefferson", "population": 782969, "api_available": True},
    {"name": "Fayette County", "state": "KY", "county": "Fayette", "population": 322570, "api_available": False},

    # Oklahoma
    {"name": "Oklahoma County", "state": "OK", "county": "Oklahoma", "population": 797434, "api_available": True},
    {"name": "Tulsa County", "state": "OK", "county": "Tulsa", "population": 669279, "api_available": False},

    # Connecticut
    {"name": "Fairfield County", "state": "CT", "county": "Fairfield", "population": 957419, "api_available": False},
    {"name": "Hartford County", "state": "CT", "county": "Hartford", "population": 899498, "api_available": False},
    {"name": "New Haven County", "state": "CT", "county": "New Haven", "population": 864835, "api_available": False},

    # Utah
    {"name": "Salt Lake County", "state": "UT", "county": "Salt Lake", "population": 1185238, "api_available": True},
    {"name": "Utah County", "state": "UT", "county": "Utah", "population": 659399, "api_available": False},

    # Iowa
    {"name": "Polk County", "state": "IA", "county": "Polk", "population": 490161, "api_available": False},

    # Arkansas
    {"name": "Pulaski County", "state": "AR", "county": "Pulaski", "population": 399125, "api_available": False},

    # Kansas
    {"name": "Johnson County", "state": "KS", "county": "Johnson", "population": 609863, "api_available": False},
    {"name": "Sedgwick County", "state": "KS", "county": "Sedgwick", "population": 523824, "api_available": False},

    # Nebraska
    {"name": "Douglas County", "state": "NE", "county": "Douglas", "population": 584526, "api_available": False},

    # New Mexico
    {"name": "Bernalillo County", "state": "NM", "county": "Bernalillo", "population": 676773, "api_available": False},

    # Hawaii
    {"name": "Honolulu County", "state": "HI", "county": "Honolulu", "population": 1016508, "api_available": True},
]


def seed_jurisdictions(db: DatabaseManager, batch_size: int = 50):
    """Seed all US county jurisdictions."""

    logger.info(f"Starting to seed {len(US_COUNTIES)} US county jurisdictions...")

    created = 0
    skipped = 0
    errors = 0

    for i, county_data in enumerate(US_COUNTIES):
        try:
            # Check if jurisdiction already exists
            existing = db.get_jurisdiction_by_name(county_data["name"])
            if existing:
                skipped += 1
                continue

            # Create jurisdiction
            jid = db.create_jurisdiction(
                name=county_data["name"],
                state=county_data["state"],
                county=county_data["county"],
                jurisdiction_type="county",
                population=county_data["population"],
                api_available=county_data["api_available"],
                scraper_needed=not county_data["api_available"],
                description=f"{county_data['county']} County, {county_data['state']}"
            )

            if jid:
                created += 1

                # Create a default data source for jurisdictions with API
                if county_data["api_available"]:
                    db.create_data_source(
                        jurisdiction_id=jid,
                        source_name=f"{county_data['name']} Official Records API",
                        source_type="api",
                        status="active",
                        description=f"Official public records API for {county_data['name']}"
                    )

            # Progress update every batch_size records
            if (i + 1) % batch_size == 0:
                logger.info(f"Progress: {i + 1}/{len(US_COUNTIES)} jurisdictions processed")

        except Exception as e:
            logger.error(f"Error creating jurisdiction {county_data['name']}: {e}")
            errors += 1

    logger.info(f"\nSeeding complete!")
    logger.info(f"  Created: {created}")
    logger.info(f"  Skipped (already exist): {skipped}")
    logger.info(f"  Errors: {errors}")

    return created, skipped, errors


def seed_all_states():
    """Seed state-level jurisdictions for all 50 US states."""

    states = [
        ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"),
        ("CA", "California"), ("CO", "Colorado"), ("CT", "Connecticut"), ("DE", "Delaware"),
        ("FL", "Florida"), ("GA", "Georgia"), ("HI", "Hawaii"), ("ID", "Idaho"),
        ("IL", "Illinois"), ("IN", "Indiana"), ("IA", "Iowa"), ("KS", "Kansas"),
        ("KY", "Kentucky"), ("LA", "Louisiana"), ("ME", "Maine"), ("MD", "Maryland"),
        ("MA", "Massachusetts"), ("MI", "Michigan"), ("MN", "Minnesota"), ("MS", "Mississippi"),
        ("MO", "Missouri"), ("MT", "Montana"), ("NE", "Nebraska"), ("NV", "Nevada"),
        ("NH", "New Hampshire"), ("NJ", "New Jersey"), ("NM", "New Mexico"), ("NY", "New York"),
        ("NC", "North Carolina"), ("ND", "North Dakota"), ("OH", "Ohio"), ("OK", "Oklahoma"),
        ("OR", "Oregon"), ("PA", "Pennsylvania"), ("RI", "Rhode Island"), ("SC", "South Carolina"),
        ("SD", "South Dakota"), ("TN", "Tennessee"), ("TX", "Texas"), ("UT", "Utah"),
        ("VT", "Vermont"), ("VA", "Virginia"), ("WA", "Washington"), ("WV", "West Virginia"),
        ("WI", "Wisconsin"), ("WY", "Wyoming")
    ]

    db = DatabaseManager()

    logger.info("Seeding state-level jurisdictions...")

    created = 0
    for state_code, state_name in states:
        existing = db.get_jurisdiction_by_name(f"{state_name} (State)")
        if existing:
            continue

        jid = db.create_jurisdiction(
            name=f"{state_name} (State)",
            state=state_code,
            jurisdiction_type="state",
            description=f"State of {state_name}",
            api_available=False,
            scraper_needed=True
        )
        if jid:
            created += 1

    logger.info(f"Created {created} state jurisdictions")
    return created


def main():
    """Main function to run the seeding process."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed US jurisdictions data")
    parser.add_argument('--states-only', action='store_true', help='Only seed state-level jurisdictions')
    parser.add_argument('--counties-only', action='store_true', help='Only seed county jurisdictions')
    args = parser.parse_args()

    db = DatabaseManager()

    # Initialize database if needed
    db.init_database()

    if args.states_only:
        seed_all_states()
    elif args.counties_only:
        seed_jurisdictions(db)
    else:
        # Seed both states and counties
        seed_all_states()
        seed_jurisdictions(db)

    # Show final stats
    stats = db.get_dashboard_stats()
    logger.info(f"\nFinal Database Stats:")
    logger.info(f"  Total Jurisdictions: {stats['jurisdictions']}")
    logger.info(f"  Total Data Sources: {stats['dataSources']}")


if __name__ == "__main__":
    main()
