"""
Miami-Dade County, Florida Corrections Inmate Scraper

Miami-Dade Corrections and Rehabilitation Department operates multiple
detention facilities with an average daily population of approximately
4,500 inmates.

Website: https://www.miamidade.gov/global/publicsafety/corrections.page
Inmate Search: https://www3.mdcr.miamidade.gov/inmatesearch/

The Miami-Dade Corrections provides:
- Inmate search by name, booking number
- Charges and bond information
- Court dates
- Facility location
- Release information
"""

import asyncio
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aiohttp

from .base import (
    ArrestRecord,
    BondInformation,
    BondType,
    BookingRecord,
    ChargeSeverity,
    ChargeType,
    InmateCharge,
    InmateRecord,
    InmateSearchCriteria,
    InmateSearchResult,
    InmateStatus,
    ReleaseType,
    SheriffInmateBase,
    VisitationInfo,
    WarrantRecord,
)

logger = logging.getLogger(__name__)


class MiamiDadeCorrections(SheriffInmateBase):
    """
    Miami-Dade County, Florida Corrections inmate scraper.

    Uses the Miami-Dade Corrections inmate search system.
    """

    COUNTY_NAME = "Miami-Dade County"
    STATE = "FL"
    FIPS_CODE = "12086"
    BASE_URL = "https://www.miamidade.gov/global/publicsafety/corrections.page"
    INMATE_SEARCH_URL = "https://www3.mdcr.miamidade.gov/inmatesearch/"
    SYSTEM_NAME = "Miami-Dade Corrections Inmate Search"

    # API endpoints
    API_BASE = "https://www3.mdcr.miamidade.gov/api/inmates/"

    # Facilities
    FACILITIES = {
        "TGK": "Turner Guilford Knight Correctional Center",
        "PTDC": "Pre-Trial Detention Center",
        "MWDC": "Metro West Detention Center",
        "WDC": "Women's Detention Center",
        "BOOT": "Boot Camp",
        "WORK": "Work Release",
    }

    # Florida statute sections for common offenses
    FL_STATUTES = {
        "316": "Motor Vehicle",
        "784": "Assault/Battery",
        "790": "Weapons/Firearms",
        "806": "Arson",
        "810": "Burglary/Trespass",
        "812": "Theft/Robbery",
        "817": "Fraud",
        "827": "Child Abuse",
        "843": "Obstruction",
        "856": "Loitering/Prowling",
        "893": "Drug Offenses",
    }

    async def search_inmates(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        include_released: bool = False,
        max_results: int = 100,
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
        if not include_released:
            params["status"] = "incarcerated"

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"Miami-Dade inmate search failed: {e}")
            return InmateSearchResult(
                inmates=[],
                total_count=0,
                page_number=1,
                page_size=max_results,
                has_more=False,
                search_criteria=InmateSearchCriteria(
                    last_name=last_name,
                    first_name=first_name,
                    date_of_birth=date_of_birth,
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
                include_released=include_released,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def get_inmate_detail(self, inmate_id: str) -> Optional[InmateRecord]:
        """Get detailed information for a specific inmate."""
        detail_url = f"{self.API_BASE}{inmate_id}"

        try:
            json_response = await self._fetch_json(detail_url)
        except Exception as e:
            logger.error(f"Miami-Dade inmate detail failed: {e}")
            return None

        if not json_response:
            return None

        return self._parse_inmate_detail(json_response)

    async def search_by_booking_number(
        self, booking_number: str
    ) -> Optional[InmateRecord]:
        """Search for an inmate by booking number."""
        search_url = f"{self.API_BASE}booking/{booking_number}"

        try:
            json_response = await self._fetch_json(search_url)
        except Exception as e:
            logger.error(f"Miami-Dade booking search failed: {e}")
            return None

        if not json_response:
            return None

        return self._parse_inmate_detail(json_response)

    async def get_current_inmates(
        self, facility: Optional[str] = None, max_results: int = 500
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
            logger.error(f"Miami-Dade jail roster failed: {e}")
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
        inmate_id = item.get(
            "inmateNumber", item.get("bookingNumber", item.get("id", ""))
        )
        if not inmate_id:
            return None

        # Parse basic charges
        charges = []
        for charge_data in item.get("charges", []):
            if isinstance(charge_data, str):
                charge_data = {"description": charge_data}
            charge = InmateCharge(
                charge_description=charge_data.get(
                    "description", charge_data.get("charge", "")
                ),
                charge_code=charge_data.get("code", charge_data.get("statute")),
                charge_type=self._parse_florida_charge_type(
                    charge_data.get("degree", charge_data.get("type", ""))
                ),
                is_felony="FELONY" in str(charge_data.get("degree", "")).upper()
                or "F" == str(charge_data.get("degree", "")).upper(),
                is_violent=self._is_violent_charge(charge_data.get("description", "")),
            )
            charges.append(charge)

        # Parse bond
        bond_amount = self._parse_decimal(
            str(item.get("bondAmount", item.get("bond", "")))
        )
        bond_info = (
            BondInformation(
                bond_amount=bond_amount,
                bond_type=self._parse_bond_type(item.get("bondType", "")),
            )
            if bond_amount
            else None
        )

        return InmateRecord(
            inmate_id=str(inmate_id),
            booking_number=item.get("bookingNumber"),
            first_name=item.get("firstName", ""),
            middle_name=item.get("middleName"),
            last_name=item.get("lastName", ""),
            date_of_birth=self._parse_date(
                item.get("dob", item.get("dateOfBirth", ""))
            ),
            age=self._parse_int(str(item.get("age", ""))),
            gender=item.get("sex", item.get("gender")),
            race=item.get("race"),
            status=self._parse_inmate_status(item.get("status", "IN_CUSTODY")),
            facility=self.FACILITIES.get(
                item.get("facility"), item.get("facility", item.get("location"))
            ),
            housing_location=item.get("housing", item.get("cell")),
            booking_date=self._parse_datetime(
                item.get("bookingDate", item.get("arrestDate", ""))
            ),
            charges=charges,
            bond_info=bond_info,
            total_bond_amount=bond_amount,
            mugshot_url=item.get("photoUrl", item.get("mugshot")),
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.INMATE_SEARCH_URL}?id={inmate_id}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_inmate_detail(self, data: Dict[str, Any]) -> InmateRecord:
        """Parse detailed inmate data."""
        inmate_id = str(
            data.get("inmateNumber", data.get("bookingNumber", data.get("id", "")))
        )

        # Parse charges with Florida-specific degree parsing
        charges = []
        for charge_data in data.get("charges", data.get("offenses", [])):
            if isinstance(charge_data, str):
                charge_data = {"description": charge_data}

            # Florida uses degree system (F1, F2, F3, M1, M2)
            degree = charge_data.get("degree", charge_data.get("offenseDegree", ""))
            charge_type = self._parse_florida_charge_type(degree)
            severity = self._parse_florida_degree(degree)

            charge = InmateCharge(
                charge_description=charge_data.get(
                    "description", charge_data.get("offense", "")
                ),
                charge_code=charge_data.get("code", charge_data.get("statute")),
                charge_type=charge_type,
                severity=severity,
                statute=charge_data.get("statute", charge_data.get("flStatute")),
                offense_date=self._parse_date(charge_data.get("offenseDate", "")),
                arrest_date=self._parse_date(charge_data.get("arrestDate", "")),
                court=charge_data.get("court", charge_data.get("division")),
                case_number=charge_data.get("caseNumber"),
                disposition=charge_data.get("disposition"),
                sentence=charge_data.get("sentence"),
                counts=charge_data.get("counts", 1),
                is_felony=charge_type == ChargeType.FELONY,
                is_violent=self._is_violent_charge(charge_data.get("description", "")),
                raw_data=charge_data,
            )
            charges.append(charge)

        # Parse bond information - Florida bond system
        bond_data = data.get("bond", data.get("bondInfo", {}))
        if isinstance(bond_data, (int, float, str)):
            bond_data = {"amount": bond_data}

        bond_amount = self._parse_decimal(
            str(bond_data.get("amount", bond_data.get("totalBond", "")))
        )
        bond_info = (
            BondInformation(
                bond_amount=bond_amount,
                bond_type=self._parse_bond_type(bond_data.get("type", "")),
                bond_status=bond_data.get("status"),
                bondsman_name=bond_data.get("bondsman"),
                bondsman_company=bond_data.get("company"),
                total_bond=bond_amount,
                raw_data=bond_data if isinstance(bond_data, dict) else {},
            )
            if bond_amount or bond_data.get("type")
            else None
        )

        # Parse visitation info
        visit_data = data.get("visitation", {})
        visitation = (
            VisitationInfo(
                visitation_allowed=visit_data.get("allowed", True),
                visitation_days=visit_data.get("days", []),
                visitation_hours=visit_data.get("hours"),
                video_visitation=visit_data.get("videoAvailable", True),
                video_url=visit_data.get("videoUrl"),
                restrictions=visit_data.get("restrictions"),
                raw_data=visit_data,
            )
            if visit_data
            else None
        )

        # Parse holds
        holds = data.get("holds", [])
        if isinstance(holds, str):
            holds = [holds] if holds else []

        detainers = data.get("detainers", [])
        if isinstance(detainers, str):
            detainers = [detainers] if detainers else []

        # Check for immigration hold
        status = self._parse_inmate_status(data.get("status", "IN_CUSTODY"))
        if any(
            "ICE" in str(h).upper() or "IMMIGRATION" in str(h).upper()
            for h in holds + detainers
        ):
            status = InmateStatus.IMMIGRATION_HOLD

        return InmateRecord(
            inmate_id=inmate_id,
            booking_number=data.get("bookingNumber"),
            jacket_number=data.get("jacketNumber"),
            first_name=data.get("firstName", ""),
            middle_name=data.get("middleName"),
            last_name=data.get("lastName", ""),
            suffix=data.get("suffix"),
            aliases=data.get("aliases", data.get("aka", [])),
            date_of_birth=self._parse_date(
                data.get("dob", data.get("dateOfBirth", ""))
            ),
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
            facility=self.FACILITIES.get(
                data.get("facility"), data.get("facility", data.get("location"))
            ),
            housing_location=data.get("housing", data.get("cell")),
            custody_level=data.get("classification", data.get("custodyLevel")),
            booking_date=self._parse_datetime(data.get("bookingDate", "")),
            arrest_date=self._parse_date(data.get("arrestDate", "")),
            scheduled_release=self._parse_date(
                data.get("projectedRelease", data.get("releaseDate", ""))
            ),
            actual_release=self._parse_datetime(data.get("actualRelease", "")),
            charges=charges,
            bond_info=bond_info,
            total_bond_amount=bond_amount,
            bond_eligible=data.get(
                "bondEligible", bond_amount is not None and bond_amount > 0
            ),
            visitation=visitation,
            mugshot_url=data.get("photoUrl", data.get("mugshot")),
            mugshot_date=self._parse_date(data.get("photoDate", "")),
            holds=holds,
            detainers=detainers,
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.INMATE_SEARCH_URL}?id={inmate_id}",
            source_system=self.SYSTEM_NAME,
            last_updated=self._parse_datetime(data.get("lastUpdate", "")),
            raw_data=data,
        )

    def _parse_florida_charge_type(self, degree_str: str) -> ChargeType:
        """Parse Florida charge type from degree."""
        if not degree_str:
            return ChargeType.UNKNOWN

        upper = str(degree_str).upper()

        if (
            upper.startswith("F")
            or "FELONY" in upper
            or "CAP" in upper
            or "LIFE" in upper
            or "PBL" in upper
        ):
            return ChargeType.FELONY
        elif upper.startswith("M") or "MISDEMEANOR" in upper:
            return ChargeType.MISDEMEANOR
        elif "ORD" in upper or "ORDINANCE" in upper:
            return ChargeType.ORDINANCE
        elif "INFRACTION" in upper:
            return ChargeType.INFRACTION

        return ChargeType.UNKNOWN

    def _parse_florida_degree(self, degree_str: str) -> ChargeSeverity:
        """Parse Florida-specific offense degrees."""
        if not degree_str:
            return ChargeSeverity.UNKNOWN

        upper = str(degree_str).upper()

        # Florida felony degrees
        if "CAPITAL" in upper or "CAP" in upper:
            return ChargeSeverity.CAPITAL
        elif "LIFE" in upper or "PBL" in upper:  # Punishable by life
            return ChargeSeverity.FELONY_1
        elif "F1" in upper or "1F" in upper or "FIRST" in upper:
            return ChargeSeverity.FELONY_1
        elif "F2" in upper or "2F" in upper or "SECOND" in upper:
            return ChargeSeverity.FELONY_2
        elif "F3" in upper or "3F" in upper or "THIRD" in upper:
            return ChargeSeverity.FELONY_3
        elif "FELONY" in upper or upper.startswith("F"):
            return ChargeSeverity.FELONY_UNCLASSIFIED

        # Florida misdemeanor degrees
        elif "M1" in upper or "1M" in upper or "FIRST" in upper:
            return ChargeSeverity.MISDEMEANOR_A
        elif "M2" in upper or "2M" in upper or "SECOND" in upper:
            return ChargeSeverity.MISDEMEANOR_B
        elif "MISDEMEANOR" in upper or upper.startswith("M"):
            return ChargeSeverity.MISDEMEANOR_UNCLASSIFIED

        return ChargeSeverity.UNKNOWN


# Convenience functions


def search_miami_dade_inmates(
    last_name: str, first_name: Optional[str] = None, **kwargs
) -> InmateSearchResult:
    """Search Miami-Dade Corrections inmates by name."""
    corrections = MiamiDadeCorrections()

    async def _search():
        async with corrections:
            return await corrections.search_inmates(last_name, first_name, **kwargs)

    return asyncio.run(_search())


def get_miami_dade_inmate(inmate_id: str) -> Optional[InmateRecord]:
    """Get Miami-Dade inmate details by ID."""
    corrections = MiamiDadeCorrections()

    async def _get():
        async with corrections:
            return await corrections.get_inmate_detail(inmate_id)

    return asyncio.run(_get())
