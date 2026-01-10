"""
Los Angeles County, California Sheriff Inmate Scraper

Los Angeles County Sheriff's Department operates the largest jail system
in the United States with an average daily population of approximately
15,000 inmates across multiple facilities.

Website: https://lasd.org/
Inmate Search: https://app5.lasd.org/iic/

The LA County Sheriff provides:
- Inmate locator search
- Inmate custody status
- Bail/bond information
- Visitation scheduling
- Facility information
"""

import asyncio
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import aiohttp

from .base import (
    SheriffInmateBase,
    InmateStatus,
    ChargeType,
    ChargeSeverity,
    BondType,
    ReleaseType,
    InmateRecord,
    BookingRecord,
    InmateCharge,
    BondInformation,
    VisitationInfo,
    ArrestRecord,
    WarrantRecord,
    InmateSearchCriteria,
    InmateSearchResult,
)

logger = logging.getLogger(__name__)


class LosAngelesCountySheriff(SheriffInmateBase):
    """
    Los Angeles County Sheriff's Department inmate scraper.

    Uses the Inmate Information Center (IIC) portal.
    """

    COUNTY_NAME = "Los Angeles County"
    STATE = "CA"
    FIPS_CODE = "06037"
    BASE_URL = "https://lasd.org/"
    INMATE_SEARCH_URL = "https://app5.lasd.org/iic/"
    SYSTEM_NAME = "LA County Sheriff Inmate Information Center"

    # API endpoints
    API_BASE = "https://app5.lasd.org/iic/api/"

    # Facilities
    FACILITIES = {
        "MCJ": "Men's Central Jail",
        "TTCF": "Twin Towers Correctional Facility",
        "IRC": "Inmate Reception Center",
        "NCCF": "North County Correctional Facility",
        "PDC": "Pitchess Detention Center",
        "CRDF": "Century Regional Detention Facility (Women's)",
        "LAC+USC": "LAC+USC Medical Center Jail Ward",
        "LCMC": "LA County Medical Center",
    }

    # Booking prefixes by facility
    BOOKING_PREFIXES = {
        "M": "Men's Central Jail",
        "T": "Twin Towers",
        "N": "North County",
        "P": "Pitchess",
        "C": "Century (Women's)",
    }

    async def search_inmates(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        include_released: bool = False,
        max_results: int = 100
    ) -> InmateSearchResult:
        """Search for inmates by name and other criteria."""
        import time
        start_time = time.time()

        search_url = f"{self.API_BASE}search"

        params = {
            "lastName": last_name,
            "maxResults": min(max_results, 100),
        }

        if first_name:
            params["firstName"] = first_name
        if date_of_birth:
            params["dob"] = date_of_birth.strftime("%m/%d/%Y")
        if not include_released:
            params["inCustody"] = "true"

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"LA County inmate search failed: {e}")
            return InmateSearchResult(
                inmates=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=InmateSearchCriteria(
                    last_name=last_name,
                    first_name=first_name,
                    date_of_birth=date_of_birth
                ),
                warnings=[str(e)],
            )

        # Parse results
        inmates = []
        results = json_response.get("inmates", json_response.get("results", []))

        for item in results[:max_results]:
            inmate = self._parse_search_result(item)
            if inmate:
                inmates.append(inmate)

        search_time = int((time.time() - start_time) * 1000)

        return InmateSearchResult(
            inmates=inmates,
            total_count=json_response.get("totalCount", len(inmates)),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
            search_criteria=InmateSearchCriteria(
                last_name=last_name,
                first_name=first_name,
                date_of_birth=date_of_birth,
                include_released=include_released
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def get_inmate_detail(
        self,
        inmate_id: str
    ) -> Optional[InmateRecord]:
        """Get detailed information for a specific inmate."""
        detail_url = f"{self.API_BASE}inmate/{inmate_id}"

        try:
            json_response = await self._fetch_json(detail_url)
        except Exception as e:
            logger.error(f"LA County inmate detail failed: {e}")
            return None

        if not json_response:
            return None

        return self._parse_inmate_detail(json_response)

    async def search_by_booking_number(
        self,
        booking_number: str
    ) -> Optional[InmateRecord]:
        """Search for an inmate by booking number."""
        search_url = f"{self.API_BASE}booking/{booking_number}"

        try:
            json_response = await self._fetch_json(search_url)
        except Exception as e:
            logger.error(f"LA County booking search failed: {e}")
            return None

        if not json_response:
            return None

        return self._parse_inmate_detail(json_response)

    async def get_current_inmates(
        self,
        facility: Optional[str] = None,
        max_results: int = 500
    ) -> InmateSearchResult:
        """Get list of current inmates."""
        import time
        start_time = time.time()

        roster_url = f"{self.API_BASE}roster"

        params = {"limit": min(max_results, 500)}
        if facility:
            params["facility"] = facility

        try:
            json_response = await self._fetch_json(roster_url, params=params)
        except Exception as e:
            logger.error(f"LA County jail roster failed: {e}")
            return InmateSearchResult(
                inmates=[],
                total_count=0,
                warnings=[str(e)],
            )

        inmates = []
        results = json_response.get("inmates", json_response.get("results", []))

        for item in results[:max_results]:
            inmate = self._parse_search_result(item)
            if inmate:
                inmates.append(inmate)

        search_time = int((time.time() - start_time) * 1000)

        return InmateSearchResult(
            inmates=inmates,
            total_count=json_response.get("totalCount", len(inmates)),
            page_number=1,
            page_size=max_results,
            has_more=json_response.get("hasMore", False),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    def _parse_search_result(self, item: Dict[str, Any]) -> Optional[InmateRecord]:
        """Parse a search result item into InmateRecord."""
        inmate_id = item.get("inmateNumber", item.get("bookingNumber", item.get("id", "")))
        if not inmate_id:
            return None

        # Parse basic charges
        charges = []
        for charge_data in item.get("charges", []):
            if isinstance(charge_data, str):
                charge_data = {"description": charge_data}
            charge = InmateCharge(
                charge_description=charge_data.get("description", charge_data.get("charge", "")),
                charge_code=charge_data.get("code"),
                charge_type=self._parse_charge_type(charge_data.get("type", charge_data.get("description", ""))),
                is_felony="FELONY" in str(charge_data.get("type", charge_data.get("description", ""))).upper(),
                is_violent=self._is_violent_charge(charge_data.get("description", "")),
            )
            charges.append(charge)

        # Parse bail
        bail_amount = self._parse_decimal(str(item.get("bail", item.get("bondAmount", ""))))
        bond_info = BondInformation(
            bond_amount=bail_amount,
            bond_type=BondType.BAIL_BOND if bail_amount else None,
        ) if bail_amount else None

        # Determine facility from booking prefix
        booking = str(item.get("bookingNumber", ""))
        facility = item.get("facility", item.get("location"))
        if not facility and booking:
            prefix = booking[0].upper() if booking else ""
            facility = self.BOOKING_PREFIXES.get(prefix, facility)

        return InmateRecord(
            inmate_id=str(inmate_id),
            booking_number=item.get("bookingNumber"),
            first_name=item.get("firstName", ""),
            middle_name=item.get("middleName"),
            last_name=item.get("lastName", ""),
            date_of_birth=self._parse_date(item.get("dob", item.get("dateOfBirth", ""))),
            age=self._parse_int(str(item.get("age", ""))),
            gender=item.get("sex", item.get("gender")),
            race=item.get("race"),
            status=self._parse_inmate_status(item.get("custodyStatus", item.get("status", "IN_CUSTODY"))),
            facility=self.FACILITIES.get(facility, facility),
            housing_location=item.get("housing", item.get("location")),
            booking_date=self._parse_datetime(item.get("bookingDate", "")),
            charges=charges,
            bond_info=bond_info,
            total_bond_amount=bail_amount,
            mugshot_url=item.get("photoUrl", item.get("mugshot")),
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.INMATE_SEARCH_URL}?booking={inmate_id}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_inmate_detail(self, data: Dict[str, Any]) -> InmateRecord:
        """Parse detailed inmate data."""
        inmate_id = str(data.get("inmateNumber", data.get("bookingNumber", data.get("id", ""))))

        # Parse charges with full details
        charges = []
        for charge_data in data.get("charges", data.get("chargeList", [])):
            if isinstance(charge_data, str):
                charge_data = {"description": charge_data}
            charge = InmateCharge(
                charge_description=charge_data.get("description", charge_data.get("charge", "")),
                charge_code=charge_data.get("code", charge_data.get("section")),
                charge_type=self._parse_charge_type(charge_data.get("type", "")),
                severity=self._parse_charge_severity(charge_data.get("class", charge_data.get("level", ""))),
                statute=charge_data.get("statute", charge_data.get("section")),
                offense_date=self._parse_date(charge_data.get("offenseDate", "")),
                arrest_date=self._parse_date(charge_data.get("arrestDate", "")),
                court=charge_data.get("court"),
                case_number=charge_data.get("caseNumber"),
                disposition=charge_data.get("disposition"),
                counts=charge_data.get("counts", 1),
                is_felony="FELONY" in str(charge_data.get("type", charge_data.get("level", ""))).upper() or charge_data.get("felony", False),
                is_violent=self._is_violent_charge(charge_data.get("description", "")),
                raw_data=charge_data,
            )
            charges.append(charge)

        # Parse bail/bond information
        bail_data = data.get("bail", data.get("bond", {}))
        if isinstance(bail_data, (int, float, str)):
            bail_data = {"amount": bail_data}

        bail_amount = self._parse_decimal(str(bail_data.get("amount", bail_data.get("total", ""))))
        bond_info = BondInformation(
            bond_amount=bail_amount,
            bond_type=self._parse_bond_type(bail_data.get("type", "bail")),
            bond_status=bail_data.get("status"),
            total_bond=bail_amount,
            raw_data=bail_data if isinstance(bail_data, dict) else {},
        ) if bail_amount or bail_data.get("status") else None

        # Parse visitation info
        visit_data = data.get("visitation", data.get("visiting", {}))
        visitation = VisitationInfo(
            visitation_allowed=visit_data.get("allowed", True),
            visitation_days=visit_data.get("days", []),
            visitation_hours=visit_data.get("hours"),
            video_visitation=visit_data.get("videoAvailable", True),  # LA County has video visits
            video_url=visit_data.get("videoUrl", "https://web.gettingout.com/"),
            restrictions=visit_data.get("restrictions"),
            raw_data=visit_data,
        ) if visit_data else None

        # Determine facility
        facility_code = data.get("facility", data.get("location", ""))
        facility = self.FACILITIES.get(facility_code, facility_code)

        return InmateRecord(
            inmate_id=inmate_id,
            booking_number=data.get("bookingNumber"),
            first_name=data.get("firstName", ""),
            middle_name=data.get("middleName"),
            last_name=data.get("lastName", ""),
            suffix=data.get("suffix"),
            aliases=data.get("aliases", data.get("aka", [])),
            date_of_birth=self._parse_date(data.get("dob", data.get("dateOfBirth", ""))),
            age=self._parse_int(str(data.get("age", ""))),
            gender=data.get("sex", data.get("gender")),
            race=data.get("race"),
            ethnicity=data.get("ethnicity"),
            height=data.get("height"),
            weight=data.get("weight"),
            eye_color=data.get("eyes", data.get("eyeColor")),
            hair_color=data.get("hair", data.get("hairColor")),
            scars_marks_tattoos=data.get("marks", data.get("scarsMarksTattoos")),
            status=self._parse_inmate_status(data.get("custodyStatus", data.get("status", "IN_CUSTODY"))),
            facility=facility,
            housing_location=data.get("housing", data.get("location")),
            custody_level=data.get("classification", data.get("custodyLevel")),
            booking_date=self._parse_datetime(data.get("bookingDate", "")),
            arrest_date=self._parse_date(data.get("arrestDate", "")),
            scheduled_release=self._parse_date(data.get("scheduledRelease", data.get("projectedRelease", ""))),
            actual_release=self._parse_datetime(data.get("releaseDate", "")),
            charges=charges,
            bond_info=bond_info,
            total_bond_amount=bail_amount,
            bond_eligible=data.get("bailEligible", bail_amount is not None),
            visitation=visitation,
            mugshot_url=data.get("photoUrl", data.get("mugshot")),
            mugshot_date=self._parse_date(data.get("photoDate", "")),
            holds=data.get("holds", []),
            detainers=data.get("detainers", []),
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.INMATE_SEARCH_URL}?booking={inmate_id}",
            source_system=self.SYSTEM_NAME,
            last_updated=self._parse_datetime(data.get("lastUpdate", "")),
            raw_data=data,
        )


# Convenience functions

def search_la_county_inmates(
    last_name: str,
    first_name: Optional[str] = None,
    **kwargs
) -> InmateSearchResult:
    """Search LA County Jail inmates by name."""
    sheriff = LosAngelesCountySheriff()

    async def _search():
        async with sheriff:
            return await sheriff.search_inmates(last_name, first_name, **kwargs)
    return asyncio.run(_search())


def get_la_county_inmate(inmate_id: str) -> Optional[InmateRecord]:
    """Get LA County inmate details by ID."""
    sheriff = LosAngelesCountySheriff()

    async def _get():
        async with sheriff:
            return await sheriff.get_inmate_detail(inmate_id)
    return asyncio.run(_get())
