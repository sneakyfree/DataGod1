"""
Harris County, Texas Sheriff Inmate Scraper

Harris County Sheriff's Office operates the Harris County Jail, the
third largest county jail system in the United States with an average
daily population of approximately 9,000 inmates.

Website: https://www.harriscountyso.org/
Inmate Search: https://www.harriscountyso.org/jail-info/inmate-search

The Harris County Sheriff provides:
- Inmate search by name, SPN, booking number
- Charges and bond information
- Court dates and case information
- Custody status
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


class HarrisCountySheriff(SheriffInmateBase):
    """
    Harris County, Texas Sheriff's Office inmate scraper.

    Uses the Harris County Jail inmate search system.
    """

    COUNTY_NAME = "Harris County"
    STATE = "TX"
    FIPS_CODE = "48201"
    BASE_URL = "https://www.harriscountyso.org/"
    INMATE_SEARCH_URL = "https://www.harriscountyso.org/jail-info/inmate-search"
    SYSTEM_NAME = "Harris County Sheriff Inmate Search"

    # API endpoints
    API_BASE = "https://www.harriscountyso.org/api/jail/"

    # Facilities
    FACILITIES = {
        "1200": "1200 Baker Street Jail",
        "701": "701 N. San Jacinto Jail",
        "1307": "1307 Baker Street Processing",
        "KEGANS": "Kegans State Jail",
        "FEDERAL": "Federal Detention",
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
            "limit": min(max_results, 100),
        }

        if first_name:
            params["firstName"] = first_name
        if date_of_birth:
            params["dob"] = date_of_birth.strftime("%m/%d/%Y")
        if include_released:
            params["status"] = "all"
        else:
            params["status"] = "current"

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"Harris County inmate search failed: {e}")
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

    async def search_by_spn(
        self,
        spn: str
    ) -> Optional[InmateRecord]:
        """Search for an inmate by SPN (System Person Number)."""
        search_url = f"{self.API_BASE}spn/{spn}"

        try:
            json_response = await self._fetch_json(search_url)
        except Exception as e:
            logger.error(f"Harris County SPN search failed: {e}")
            return None

        if not json_response:
            return None

        return self._parse_inmate_detail(json_response)

    async def get_inmate_detail(
        self,
        inmate_id: str
    ) -> Optional[InmateRecord]:
        """Get detailed information for a specific inmate."""
        detail_url = f"{self.API_BASE}inmate/{inmate_id}"

        try:
            json_response = await self._fetch_json(detail_url)
        except Exception as e:
            logger.error(f"Harris County inmate detail failed: {e}")
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
            logger.error(f"Harris County booking search failed: {e}")
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
            logger.error(f"Harris County jail roster failed: {e}")
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
        inmate_id = item.get("spn", item.get("inmateId", item.get("id", "")))
        if not inmate_id:
            return None

        # Parse basic charges
        charges = []
        for charge_data in item.get("charges", []):
            if isinstance(charge_data, str):
                charge_data = {"description": charge_data}
            charge = InmateCharge(
                charge_description=charge_data.get("description", charge_data.get("offense", "")),
                charge_code=charge_data.get("code"),
                charge_type=self._parse_charge_type(charge_data.get("level", charge_data.get("type", ""))),
                is_felony="FELONY" in str(charge_data.get("level", "")).upper(),
                is_violent=self._is_violent_charge(charge_data.get("description", "")),
            )
            charges.append(charge)

        # Parse bond
        bond_amount = self._parse_decimal(str(item.get("bondAmount", item.get("bond", ""))))
        bond_info = BondInformation(
            bond_amount=bond_amount,
            bond_type=self._parse_bond_type(item.get("bondType", "")),
        ) if bond_amount else None

        return InmateRecord(
            inmate_id=str(inmate_id),
            booking_number=item.get("bookingNumber", item.get("soNumber")),
            first_name=item.get("firstName", ""),
            middle_name=item.get("middleName"),
            last_name=item.get("lastName", ""),
            date_of_birth=self._parse_date(item.get("dob", item.get("dateOfBirth", ""))),
            age=self._parse_int(str(item.get("age", ""))),
            gender=item.get("sex", item.get("gender")),
            race=item.get("race"),
            status=self._parse_inmate_status(item.get("status", "IN_CUSTODY")),
            facility=self.FACILITIES.get(item.get("facility"), item.get("facility", item.get("location"))),
            housing_location=item.get("housing", item.get("pod")),
            booking_date=self._parse_datetime(item.get("bookingDate", item.get("arrestDate", ""))),
            charges=charges,
            bond_info=bond_info,
            total_bond_amount=bond_amount,
            mugshot_url=item.get("photoUrl", item.get("mugshot")),
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.INMATE_SEARCH_URL}?spn={inmate_id}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_inmate_detail(self, data: Dict[str, Any]) -> InmateRecord:
        """Parse detailed inmate data."""
        inmate_id = str(data.get("spn", data.get("inmateId", data.get("id", ""))))

        # Parse charges with full details - Texas uses specific offense codes
        charges = []
        for charge_data in data.get("charges", data.get("offenses", [])):
            if isinstance(charge_data, str):
                charge_data = {"description": charge_data}

            # Texas offense levels
            level = charge_data.get("level", charge_data.get("offenseLevel", ""))
            charge_type = ChargeType.FELONY if "FELONY" in str(level).upper() else ChargeType.MISDEMEANOR if "MISDEMEANOR" in str(level).upper() else ChargeType.UNKNOWN

            charge = InmateCharge(
                charge_description=charge_data.get("description", charge_data.get("offense", "")),
                charge_code=charge_data.get("code", charge_data.get("offenseCode")),
                charge_type=charge_type,
                severity=self._parse_texas_offense_level(level),
                statute=charge_data.get("statute", charge_data.get("offenseCode")),
                offense_date=self._parse_date(charge_data.get("offenseDate", "")),
                arrest_date=self._parse_date(charge_data.get("arrestDate", "")),
                court=charge_data.get("court", charge_data.get("courtNumber")),
                case_number=charge_data.get("caseNumber", charge_data.get("causeNumber")),
                disposition=charge_data.get("disposition"),
                sentence=charge_data.get("sentence"),
                counts=charge_data.get("counts", 1),
                is_felony=charge_type == ChargeType.FELONY,
                is_violent=self._is_violent_charge(charge_data.get("description", "")),
                raw_data=charge_data,
            )
            charges.append(charge)

        # Parse bond information - Texas bond system
        bond_data = data.get("bond", data.get("bondInfo", {}))
        if isinstance(bond_data, (int, float, str)):
            bond_data = {"amount": bond_data}

        bond_amount = self._parse_decimal(str(bond_data.get("amount", bond_data.get("totalBond", ""))))
        bond_info = BondInformation(
            bond_amount=bond_amount,
            bond_type=self._parse_bond_type(bond_data.get("type", "")),
            bond_status=bond_data.get("status"),
            bondsman_name=bond_data.get("bondsman"),
            bondsman_company=bond_data.get("bondsmanCompany", bond_data.get("company")),
            total_bond=bond_amount,
            raw_data=bond_data if isinstance(bond_data, dict) else {},
        ) if bond_amount or bond_data.get("type") else None

        # Parse holds - Texas commonly has ICE holds
        holds = data.get("holds", [])
        if isinstance(holds, str):
            holds = [holds] if holds else []

        detainers = data.get("detainers", [])
        if isinstance(detainers, str):
            detainers = [detainers] if detainers else []

        # Check for immigration hold
        status = self._parse_inmate_status(data.get("status", "IN_CUSTODY"))
        if any("ICE" in str(h).upper() or "IMMIGRATION" in str(h).upper() for h in holds + detainers):
            status = InmateStatus.IMMIGRATION_HOLD

        return InmateRecord(
            inmate_id=inmate_id,
            booking_number=data.get("bookingNumber", data.get("soNumber")),
            jacket_number=data.get("jacketNumber"),
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
            scars_marks_tattoos=data.get("marks", data.get("identifyingMarks")),
            status=status,
            facility=self.FACILITIES.get(data.get("facility"), data.get("facility", data.get("location"))),
            housing_location=data.get("housing", data.get("pod")),
            custody_level=data.get("classification", data.get("custodyLevel")),
            booking_date=self._parse_datetime(data.get("bookingDate", "")),
            arrest_date=self._parse_date(data.get("arrestDate", "")),
            scheduled_release=self._parse_date(data.get("projectedRelease", "")),
            actual_release=self._parse_datetime(data.get("releaseDate", "")),
            charges=charges,
            bond_info=bond_info,
            total_bond_amount=bond_amount,
            bond_eligible=data.get("bondEligible", bond_amount is not None and bond_amount > 0),
            mugshot_url=data.get("photoUrl", data.get("mugshot")),
            mugshot_date=self._parse_date(data.get("photoDate", "")),
            holds=holds,
            detainers=detainers,
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.INMATE_SEARCH_URL}?spn={inmate_id}",
            source_system=self.SYSTEM_NAME,
            last_updated=self._parse_datetime(data.get("lastUpdate", "")),
            raw_data=data,
        )

    def _parse_texas_offense_level(self, level_str: str) -> ChargeSeverity:
        """Parse Texas-specific offense levels."""
        if not level_str:
            return ChargeSeverity.UNKNOWN

        upper = str(level_str).upper()

        # Texas felony levels
        if "CAPITAL" in upper:
            return ChargeSeverity.CAPITAL
        elif "1ST" in upper or "FIRST" in upper:
            return ChargeSeverity.FELONY_1
        elif "2ND" in upper or "SECOND" in upper:
            return ChargeSeverity.FELONY_2
        elif "3RD" in upper or "THIRD" in upper:
            return ChargeSeverity.FELONY_3
        elif "STATE JAIL" in upper or "SJF" in upper:
            return ChargeSeverity.FELONY_4  # State jail felony
        elif "FELONY" in upper:
            return ChargeSeverity.FELONY_UNCLASSIFIED
        # Texas misdemeanor levels
        elif "CLASS A" in upper:
            return ChargeSeverity.MISDEMEANOR_A
        elif "CLASS B" in upper:
            return ChargeSeverity.MISDEMEANOR_B
        elif "CLASS C" in upper:
            return ChargeSeverity.MISDEMEANOR_C
        elif "MISDEMEANOR" in upper:
            return ChargeSeverity.MISDEMEANOR_UNCLASSIFIED

        return ChargeSeverity.UNKNOWN


# Convenience functions

def search_harris_county_inmates(
    last_name: str,
    first_name: Optional[str] = None,
    **kwargs
) -> InmateSearchResult:
    """Search Harris County Jail inmates by name."""
    sheriff = HarrisCountySheriff()

    async def _search():
        async with sheriff:
            return await sheriff.search_inmates(last_name, first_name, **kwargs)
    return asyncio.run(_search())


def get_harris_county_inmate(inmate_id: str) -> Optional[InmateRecord]:
    """Get Harris County inmate details by SPN or ID."""
    sheriff = HarrisCountySheriff()

    async def _get():
        async with sheriff:
            return await sheriff.get_inmate_detail(inmate_id)
    return asyncio.run(_get())
