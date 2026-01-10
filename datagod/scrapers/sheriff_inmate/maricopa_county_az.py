"""
Maricopa County, Arizona Sheriff Inmate Scraper

Maricopa County Sheriff's Office operates one of the largest jail systems
in the Southwest with multiple facilities and an average daily population
of approximately 7,000 inmates.

Website: https://www.mcso.org/
Inmate Search: https://www.mcso.org/InmateData

The Maricopa County Sheriff provides:
- Inmate lookup by name and booking number
- Charges and bond information
- Court dates
- Mugshots
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


class MaricopaCountySheriff(SheriffInmateBase):
    """
    Maricopa County, Arizona Sheriff's Office inmate scraper.

    Uses the MCSO inmate data search system.
    """

    COUNTY_NAME = "Maricopa County"
    STATE = "AZ"
    FIPS_CODE = "04013"
    BASE_URL = "https://www.mcso.org/"
    INMATE_SEARCH_URL = "https://www.mcso.org/InmateData"
    SYSTEM_NAME = "Maricopa County Sheriff Inmate Search"

    # API endpoints
    API_BASE = "https://www.mcso.org/api/inmates/"

    # Facilities
    FACILITIES = {
        "4TH": "4th Avenue Jail",
        "TOWERS": "Towers Jail",
        "ESTRELLA": "Estrella Jail (Women's)",
        "LOWER": "Lower Buckeye Jail",
        "DURANGO": "Durango Jail",
        "INTAKE": "Intake, Transfer, and Release",
        "COURT": "Court Transport",
    }

    # Arizona offense classes
    AZ_FELONY_CLASSES = {
        "1": "Class 1 Felony",
        "2": "Class 2 Felony",
        "3": "Class 3 Felony",
        "4": "Class 4 Felony",
        "5": "Class 5 Felony",
        "6": "Class 6 Felony",
    }

    AZ_MISDEMEANOR_CLASSES = {
        "1": "Class 1 Misdemeanor",
        "2": "Class 2 Misdemeanor",
        "3": "Class 3 Misdemeanor",
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
            params["inCustody"] = "Y"

        try:
            json_response = await self._fetch_json(search_url, params=params)
        except Exception as e:
            logger.error(f"Maricopa County inmate search failed: {e}")
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
        detail_url = f"{self.API_BASE}{inmate_id}"

        try:
            json_response = await self._fetch_json(detail_url)
        except Exception as e:
            logger.error(f"Maricopa County inmate detail failed: {e}")
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
            logger.error(f"Maricopa County booking search failed: {e}")
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
            logger.error(f"Maricopa County jail roster failed: {e}")
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
                charge_type=self._parse_charge_type(charge_data.get("class", charge_data.get("type", ""))),
                is_felony="FELONY" in str(charge_data.get("class", "")).upper(),
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
            booking_number=item.get("bookingNumber"),
            first_name=item.get("firstName", ""),
            middle_name=item.get("middleName"),
            last_name=item.get("lastName", ""),
            date_of_birth=self._parse_date(item.get("dob", item.get("dateOfBirth", ""))),
            age=self._parse_int(str(item.get("age", ""))),
            gender=item.get("sex", item.get("gender")),
            race=item.get("race"),
            status=self._parse_inmate_status(item.get("custodyStatus", item.get("status", "IN_CUSTODY"))),
            facility=self.FACILITIES.get(item.get("facility"), item.get("facility", item.get("location"))),
            housing_location=item.get("housing", item.get("pod")),
            booking_date=self._parse_datetime(item.get("bookingDate", "")),
            charges=charges,
            bond_info=bond_info,
            total_bond_amount=bond_amount,
            mugshot_url=item.get("photoUrl", item.get("mugshot")),
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.INMATE_SEARCH_URL}/{inmate_id}",
            source_system=self.SYSTEM_NAME,
            raw_data=item,
        )

    def _parse_inmate_detail(self, data: Dict[str, Any]) -> InmateRecord:
        """Parse detailed inmate data."""
        inmate_id = str(data.get("inmateNumber", data.get("bookingNumber", data.get("id", ""))))

        # Parse charges with Arizona-specific offense classes
        charges = []
        for charge_data in data.get("charges", data.get("offenses", [])):
            if isinstance(charge_data, str):
                charge_data = {"description": charge_data}

            # Arizona offense class parsing
            offense_class = charge_data.get("class", charge_data.get("offenseClass", ""))
            charge_type, severity = self._parse_arizona_offense_class(offense_class)

            charge = InmateCharge(
                charge_description=charge_data.get("description", charge_data.get("offense", "")),
                charge_code=charge_data.get("code", charge_data.get("statute")),
                charge_type=charge_type,
                severity=severity,
                statute=charge_data.get("statute", charge_data.get("ars")),  # Arizona Revised Statutes
                offense_date=self._parse_date(charge_data.get("offenseDate", "")),
                arrest_date=self._parse_date(charge_data.get("arrestDate", "")),
                court=charge_data.get("court"),
                case_number=charge_data.get("caseNumber", charge_data.get("crNumber")),
                disposition=charge_data.get("disposition"),
                sentence=charge_data.get("sentence"),
                counts=charge_data.get("counts", 1),
                is_felony=charge_type == ChargeType.FELONY,
                is_violent=self._is_violent_charge(charge_data.get("description", "")),
                raw_data=charge_data,
            )
            charges.append(charge)

        # Parse bond information
        bond_data = data.get("bond", data.get("bondInfo", {}))
        if isinstance(bond_data, (int, float, str)):
            bond_data = {"amount": bond_data}

        bond_amount = self._parse_decimal(str(bond_data.get("amount", bond_data.get("totalBond", ""))))
        bond_info = BondInformation(
            bond_amount=bond_amount,
            bond_type=self._parse_bond_type(bond_data.get("type", "")),
            bond_status=bond_data.get("status"),
            bondsman_name=bond_data.get("bondsman"),
            bondsman_company=bond_data.get("company"),
            total_bond=bond_amount,
            raw_data=bond_data if isinstance(bond_data, dict) else {},
        ) if bond_amount or bond_data.get("type") else None

        # Parse visitation info - Maricopa uses video visitation
        visit_data = data.get("visitation", {})
        visitation = VisitationInfo(
            visitation_allowed=visit_data.get("allowed", True),
            visitation_days=visit_data.get("days", []),
            visitation_hours=visit_data.get("hours"),
            video_visitation=True,  # MCSO uses video visitation
            video_url=visit_data.get("videoUrl", "https://www.gettingout.com/"),
            restrictions=visit_data.get("restrictions"),
            raw_data=visit_data,
        ) if visit_data else None

        # Parse holds
        holds = data.get("holds", [])
        if isinstance(holds, str):
            holds = [holds] if holds else []

        detainers = data.get("detainers", [])
        if isinstance(detainers, str):
            detainers = [detainers] if detainers else []

        return InmateRecord(
            inmate_id=inmate_id,
            booking_number=data.get("bookingNumber"),
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
            status=self._parse_inmate_status(data.get("custodyStatus", data.get("status", "IN_CUSTODY"))),
            facility=self.FACILITIES.get(data.get("facility"), data.get("facility", data.get("location"))),
            housing_location=data.get("housing", data.get("pod")),
            custody_level=data.get("classification", data.get("custodyLevel")),
            booking_date=self._parse_datetime(data.get("bookingDate", "")),
            arrest_date=self._parse_date(data.get("arrestDate", "")),
            scheduled_release=self._parse_date(data.get("projectedRelease", data.get("scheduledRelease", ""))),
            actual_release=self._parse_datetime(data.get("releaseDate", "")),
            charges=charges,
            bond_info=bond_info,
            total_bond_amount=bond_amount,
            bond_eligible=data.get("bondEligible", bond_amount is not None and bond_amount > 0),
            visitation=visitation,
            mugshot_url=data.get("photoUrl", data.get("mugshot")),
            mugshot_date=self._parse_date(data.get("photoDate", "")),
            holds=holds,
            detainers=detainers,
            county=self.COUNTY_NAME,
            state=self.STATE,
            source_url=f"{self.INMATE_SEARCH_URL}/{inmate_id}",
            source_system=self.SYSTEM_NAME,
            last_updated=self._parse_datetime(data.get("lastUpdate", "")),
            raw_data=data,
        )

    def _parse_arizona_offense_class(self, class_str: str) -> tuple:
        """Parse Arizona-specific offense classes."""
        if not class_str:
            return ChargeType.UNKNOWN, ChargeSeverity.UNKNOWN

        upper = str(class_str).upper()

        # Arizona felony classes (1-6)
        if "FELONY" in upper or "F" in upper:
            charge_type = ChargeType.FELONY
            if "1" in upper or "ONE" in upper:
                severity = ChargeSeverity.FELONY_1
            elif "2" in upper or "TWO" in upper:
                severity = ChargeSeverity.FELONY_2
            elif "3" in upper or "THREE" in upper:
                severity = ChargeSeverity.FELONY_3
            elif "4" in upper or "FOUR" in upper:
                severity = ChargeSeverity.FELONY_4
            elif "5" in upper or "FIVE" in upper:
                severity = ChargeSeverity.FELONY_5
            elif "6" in upper or "SIX" in upper:
                # Class 6 felony is wobbler in AZ
                severity = ChargeSeverity.FELONY_UNCLASSIFIED
            else:
                severity = ChargeSeverity.FELONY_UNCLASSIFIED
            return charge_type, severity

        # Arizona misdemeanor classes (1-3)
        elif "MISDEMEANOR" in upper or "M" in upper:
            charge_type = ChargeType.MISDEMEANOR
            if "1" in upper:
                severity = ChargeSeverity.MISDEMEANOR_A
            elif "2" in upper:
                severity = ChargeSeverity.MISDEMEANOR_B
            elif "3" in upper:
                severity = ChargeSeverity.MISDEMEANOR_C
            else:
                severity = ChargeSeverity.MISDEMEANOR_UNCLASSIFIED
            return charge_type, severity

        # Petty offense
        elif "PETTY" in upper:
            return ChargeType.INFRACTION, ChargeSeverity.PETTY

        return ChargeType.UNKNOWN, ChargeSeverity.UNKNOWN


# Convenience functions

def search_maricopa_county_inmates(
    last_name: str,
    first_name: Optional[str] = None,
    **kwargs
) -> InmateSearchResult:
    """Search Maricopa County Jail inmates by name."""
    sheriff = MaricopaCountySheriff()

    async def _search():
        async with sheriff:
            return await sheriff.search_inmates(last_name, first_name, **kwargs)
    return asyncio.run(_search())


def get_maricopa_county_inmate(inmate_id: str) -> Optional[InmateRecord]:
    """Get Maricopa County inmate details by ID."""
    sheriff = MaricopaCountySheriff()

    async def _get():
        async with sheriff:
            return await sheriff.get_inmate_detail(inmate_id)
    return asyncio.run(_get())
