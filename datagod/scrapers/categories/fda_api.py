"""
FDA (Food and Drug Administration) API Integration

Free public API providing access to:
- Drug adverse events (FAERS)
- Drug product labels
- Drug recalls and enforcement
- Medical device recalls
- Food recalls and enforcement
- Inspection and compliance data

API Documentation: https://open.fda.gov/apis/
Rate Limit: 240 requests/minute without API key, 120,000/day with free key
"""

import asyncio
import aiohttp
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FDAEndpoint(Enum):
    """FDA API endpoints"""
    # Drug endpoints
    DRUG_EVENT = "drug/event"
    DRUG_LABEL = "drug/label"
    DRUG_NDC = "drug/ndc"
    DRUG_ENFORCEMENT = "drug/enforcement"

    # Device endpoints
    DEVICE_EVENT = "device/event"
    DEVICE_RECALL = "device/recall"
    DEVICE_CLASSIFICATION = "device/classification"
    DEVICE_510K = "device/510k"
    DEVICE_PMA = "device/pma"
    DEVICE_ENFORCEMENT = "device/enforcement"

    # Food endpoints
    FOOD_EVENT = "food/event"
    FOOD_ENFORCEMENT = "food/enforcement"
    FOOD_RECALL = "food/recall"


class RecallClassification(Enum):
    """FDA recall classification levels"""
    CLASS_I = "Class I"      # Serious health hazard
    CLASS_II = "Class II"    # Temporary/reversible health effects
    CLASS_III = "Class III"  # Unlikely to cause adverse health


class RecallStatus(Enum):
    """FDA recall status"""
    ONGOING = "Ongoing"
    COMPLETED = "Completed"
    TERMINATED = "Terminated"
    PENDING = "Pending"


@dataclass
class DrugAdverseEvent:
    """Drug adverse event report from FAERS"""
    report_id: str
    receive_date: Optional[date] = None
    receipt_date: Optional[date] = None
    serious: bool = False
    serious_death: bool = False
    serious_hospitalization: bool = False
    serious_disability: bool = False
    patient_age: Optional[float] = None
    patient_sex: Optional[str] = None
    patient_weight: Optional[float] = None
    drugs: List[Dict[str, Any]] = field(default_factory=list)
    reactions: List[str] = field(default_factory=list)
    outcomes: List[str] = field(default_factory=list)
    reporter_qualification: Optional[str] = None
    sender_organization: Optional[str] = None


@dataclass
class DrugRecall:
    """Drug recall/enforcement record"""
    recall_number: str
    product_description: str
    reason_for_recall: str
    classification: Optional[RecallClassification] = None
    status: Optional[RecallStatus] = None
    recalling_firm: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    voluntary_mandated: Optional[str] = None
    initial_firm_notification: Optional[str] = None
    distribution_pattern: Optional[str] = None
    recall_initiation_date: Optional[date] = None
    center_classification_date: Optional[date] = None
    report_date: Optional[date] = None
    product_quantity: Optional[str] = None
    code_info: Optional[str] = None


@dataclass
class DeviceRecall:
    """Medical device recall record"""
    recall_number: str
    product_description: str
    reason_for_recall: str
    product_code: Optional[str] = None
    k_number: Optional[str] = None  # 510(k) clearance number
    pma_number: Optional[str] = None  # PMA approval number
    classification: Optional[RecallClassification] = None
    recalling_firm: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    event_date: Optional[date] = None
    root_cause_description: Optional[str] = None


@dataclass
class FoodRecall:
    """Food recall/enforcement record"""
    recall_number: str
    product_description: str
    reason_for_recall: str
    classification: Optional[RecallClassification] = None
    status: Optional[RecallStatus] = None
    recalling_firm: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    distribution_pattern: Optional[str] = None
    recall_initiation_date: Optional[date] = None
    report_date: Optional[date] = None
    product_quantity: Optional[str] = None
    code_info: Optional[str] = None


@dataclass
class DrugLabel:
    """Drug product label information"""
    set_id: str
    spl_id: str
    effective_time: Optional[date] = None
    brand_name: Optional[str] = None
    generic_name: Optional[str] = None
    manufacturer_name: Optional[str] = None
    product_ndc: List[str] = field(default_factory=list)
    product_type: Optional[str] = None
    route: List[str] = field(default_factory=list)
    substance_name: List[str] = field(default_factory=list)
    pharm_class: List[str] = field(default_factory=list)
    dosage_form: Optional[str] = None
    indications_and_usage: Optional[str] = None
    warnings: Optional[str] = None
    adverse_reactions: Optional[str] = None
    boxed_warning: Optional[str] = None


class FDAApiClient:
    """
    FDA openFDA API client

    Provides access to FDA public data including:
    - Drug adverse event reports (FAERS)
    - Drug labels and NDC directory
    - Drug recalls and enforcement actions
    - Medical device events and recalls
    - Food recalls and enforcement

    Free API with generous rate limits (240/min without key, 120K/day with key)
    """

    BASE_URL = "https://api.fda.gov"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FDA API client

        Args:
            api_key: Optional API key for higher rate limits (free from openFDA)
        """
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _make_request(
        self,
        endpoint: FDAEndpoint,
        search: Optional[str] = None,
        count: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        Make request to FDA API

        Args:
            endpoint: FDA API endpoint
            search: Search query in openFDA query syntax
            count: Field to count/aggregate
            limit: Number of results (max 1000)
            skip: Number of results to skip

        Returns:
            API response as dictionary
        """
        session = await self._get_session()

        url = f"{self.BASE_URL}/{endpoint.value}.json"

        params = {
            "limit": min(limit, 1000)
        }

        if skip > 0:
            params["skip"] = skip

        if search:
            params["search"] = search

        if count:
            params["count"] = count

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return {"results": [], "meta": {"results": {"total": 0}}}
                else:
                    error_text = await response.text()
                    logger.error(f"FDA API error {response.status}: {error_text}")
                    return {"error": error_text, "status": response.status}

        except asyncio.TimeoutError:
            logger.error("FDA API request timed out")
            return {"error": "Request timed out", "status": 408}
        except Exception as e:
            logger.error(f"FDA API request failed: {e}")
            return {"error": str(e), "status": 500}

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse FDA date format (YYYYMMDD)"""
        if not date_str:
            return None
        try:
            if len(date_str) == 8:
                return datetime.strptime(date_str, "%Y%m%d").date()
            elif len(date_str) == 10:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            return None
        except ValueError:
            return None

    # Drug Adverse Events (FAERS)

    async def search_drug_adverse_events(
        self,
        drug_name: Optional[str] = None,
        reaction: Optional[str] = None,
        serious: Optional[bool] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[DrugAdverseEvent]:
        """
        Search drug adverse event reports

        Args:
            drug_name: Drug brand or generic name
            reaction: Adverse reaction term
            serious: Filter for serious events only
            date_from: Start date for reports
            date_to: End date for reports
            limit: Number of results
            skip: Skip results for pagination

        Returns:
            List of adverse event records
        """
        search_parts = []

        if drug_name:
            search_parts.append(f'patient.drug.medicinalproduct:"{drug_name}"')

        if reaction:
            search_parts.append(f'patient.reaction.reactionmeddrapt:"{reaction}"')

        if serious is True:
            search_parts.append("serious:1")
        elif serious is False:
            search_parts.append("serious:2")

        if date_from or date_to:
            date_range = f"[{date_from.strftime('%Y%m%d') if date_from else '*'} TO {date_to.strftime('%Y%m%d') if date_to else '*'}]"
            search_parts.append(f"receivedate:{date_range}")

        search = "+AND+".join(search_parts) if search_parts else None

        response = await self._make_request(
            FDAEndpoint.DRUG_EVENT,
            search=search,
            limit=limit,
            skip=skip
        )

        events = []
        for result in response.get("results", []):
            patient = result.get("patient", {})

            drugs = []
            for drug in patient.get("drug", []):
                drugs.append({
                    "name": drug.get("medicinalproduct"),
                    "generic_name": drug.get("openfda", {}).get("generic_name", [None])[0],
                    "brand_name": drug.get("openfda", {}).get("brand_name", [None])[0],
                    "manufacturer": drug.get("openfda", {}).get("manufacturer_name", [None])[0],
                    "characterization": drug.get("drugcharacterization"),
                    "indication": drug.get("drugindication"),
                    "route": drug.get("drugadministrationroute"),
                    "dose": drug.get("drugdosagetext")
                })

            reactions = [r.get("reactionmeddrapt") for r in patient.get("reaction", [])]

            events.append(DrugAdverseEvent(
                report_id=result.get("safetyreportid", ""),
                receive_date=self._parse_date(result.get("receivedate")),
                receipt_date=self._parse_date(result.get("receiptdate")),
                serious=result.get("serious") == "1",
                serious_death=result.get("seriousnessdeath") == "1",
                serious_hospitalization=result.get("seriousnesshospitalization") == "1",
                serious_disability=result.get("seriousnessdisabling") == "1",
                patient_age=patient.get("patientonsetage"),
                patient_sex=patient.get("patientsex"),
                patient_weight=patient.get("patientweight"),
                drugs=drugs,
                reactions=[r for r in reactions if r],
                outcomes=[o.get("patientoutcome") for o in patient.get("patientoutcome", [])],
                reporter_qualification=result.get("primarysource", {}).get("qualification"),
                sender_organization=result.get("sender", {}).get("senderorganization")
            ))

        return events

    # Drug Recalls/Enforcement

    async def search_drug_recalls(
        self,
        firm_name: Optional[str] = None,
        product: Optional[str] = None,
        classification: Optional[RecallClassification] = None,
        state: Optional[str] = None,
        status: Optional[RecallStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[DrugRecall]:
        """
        Search drug recall/enforcement records

        Args:
            firm_name: Name of recalling firm
            product: Product description search
            classification: Recall class (I, II, III)
            state: State code
            status: Recall status
            date_from: Start date
            date_to: End date
            limit: Number of results
            skip: Skip for pagination

        Returns:
            List of drug recall records
        """
        search_parts = []

        if firm_name:
            search_parts.append(f'recalling_firm:"{firm_name}"')

        if product:
            search_parts.append(f'product_description:"{product}"')

        if classification:
            search_parts.append(f'classification:"{classification.value}"')

        if state:
            search_parts.append(f'state:"{state}"')

        if status:
            search_parts.append(f'status:"{status.value}"')

        if date_from or date_to:
            date_range = f"[{date_from.strftime('%Y%m%d') if date_from else '*'} TO {date_to.strftime('%Y%m%d') if date_to else '*'}]"
            search_parts.append(f"report_date:{date_range}")

        search = "+AND+".join(search_parts) if search_parts else None

        response = await self._make_request(
            FDAEndpoint.DRUG_ENFORCEMENT,
            search=search,
            limit=limit,
            skip=skip
        )

        recalls = []
        for result in response.get("results", []):
            classification_str = result.get("classification", "")
            recall_classification = None
            for rc in RecallClassification:
                if rc.value in classification_str:
                    recall_classification = rc
                    break

            status_str = result.get("status", "")
            recall_status = None
            for rs in RecallStatus:
                if rs.value.lower() in status_str.lower():
                    recall_status = rs
                    break

            recalls.append(DrugRecall(
                recall_number=result.get("recall_number", ""),
                product_description=result.get("product_description", ""),
                reason_for_recall=result.get("reason_for_recall", ""),
                classification=recall_classification,
                status=recall_status,
                recalling_firm=result.get("recalling_firm"),
                city=result.get("city"),
                state=result.get("state"),
                country=result.get("country"),
                voluntary_mandated=result.get("voluntary_mandated"),
                initial_firm_notification=result.get("initial_firm_notification"),
                distribution_pattern=result.get("distribution_pattern"),
                recall_initiation_date=self._parse_date(result.get("recall_initiation_date")),
                center_classification_date=self._parse_date(result.get("center_classification_date")),
                report_date=self._parse_date(result.get("report_date")),
                product_quantity=result.get("product_quantity"),
                code_info=result.get("code_info")
            ))

        return recalls

    # Device Recalls

    async def search_device_recalls(
        self,
        firm_name: Optional[str] = None,
        product: Optional[str] = None,
        product_code: Optional[str] = None,
        classification: Optional[RecallClassification] = None,
        state: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[DeviceRecall]:
        """
        Search medical device recall records

        Args:
            firm_name: Name of recalling firm
            product: Product description search
            product_code: FDA product code
            classification: Recall class
            state: State code
            limit: Number of results
            skip: Skip for pagination

        Returns:
            List of device recall records
        """
        search_parts = []

        if firm_name:
            search_parts.append(f'recalling_firm:"{firm_name}"')

        if product:
            search_parts.append(f'product_description:"{product}"')

        if product_code:
            search_parts.append(f'product_code:"{product_code}"')

        if classification:
            search_parts.append(f'res_event_number:"{classification.value}"')

        if state:
            search_parts.append(f'state:"{state}"')

        search = "+AND+".join(search_parts) if search_parts else None

        response = await self._make_request(
            FDAEndpoint.DEVICE_RECALL,
            search=search,
            limit=limit,
            skip=skip
        )

        recalls = []
        for result in response.get("results", []):
            recalls.append(DeviceRecall(
                recall_number=result.get("res_event_number", ""),
                product_description=result.get("product_description", ""),
                reason_for_recall=result.get("reason_for_recall", ""),
                product_code=result.get("product_code"),
                k_number=result.get("k_numbers", [None])[0] if result.get("k_numbers") else None,
                pma_number=result.get("pma_numbers", [None])[0] if result.get("pma_numbers") else None,
                recalling_firm=result.get("recalling_firm"),
                city=result.get("city"),
                state=result.get("state"),
                event_date=self._parse_date(result.get("event_date_initiated")),
                root_cause_description=result.get("root_cause_description")
            ))

        return recalls

    # Food Recalls

    async def search_food_recalls(
        self,
        firm_name: Optional[str] = None,
        product: Optional[str] = None,
        classification: Optional[RecallClassification] = None,
        state: Optional[str] = None,
        status: Optional[RecallStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[FoodRecall]:
        """
        Search food recall/enforcement records

        Args:
            firm_name: Name of recalling firm
            product: Product description search
            classification: Recall class
            state: State code
            status: Recall status
            date_from: Start date
            date_to: End date
            limit: Number of results
            skip: Skip for pagination

        Returns:
            List of food recall records
        """
        search_parts = []

        if firm_name:
            search_parts.append(f'recalling_firm:"{firm_name}"')

        if product:
            search_parts.append(f'product_description:"{product}"')

        if classification:
            search_parts.append(f'classification:"{classification.value}"')

        if state:
            search_parts.append(f'state:"{state}"')

        if status:
            search_parts.append(f'status:"{status.value}"')

        if date_from or date_to:
            date_range = f"[{date_from.strftime('%Y%m%d') if date_from else '*'} TO {date_to.strftime('%Y%m%d') if date_to else '*'}]"
            search_parts.append(f"report_date:{date_range}")

        search = "+AND+".join(search_parts) if search_parts else None

        response = await self._make_request(
            FDAEndpoint.FOOD_ENFORCEMENT,
            search=search,
            limit=limit,
            skip=skip
        )

        recalls = []
        for result in response.get("results", []):
            classification_str = result.get("classification", "")
            recall_classification = None
            for rc in RecallClassification:
                if rc.value in classification_str:
                    recall_classification = rc
                    break

            status_str = result.get("status", "")
            recall_status = None
            for rs in RecallStatus:
                if rs.value.lower() in status_str.lower():
                    recall_status = rs
                    break

            recalls.append(FoodRecall(
                recall_number=result.get("recall_number", ""),
                product_description=result.get("product_description", ""),
                reason_for_recall=result.get("reason_for_recall", ""),
                classification=recall_classification,
                status=recall_status,
                recalling_firm=result.get("recalling_firm"),
                city=result.get("city"),
                state=result.get("state"),
                distribution_pattern=result.get("distribution_pattern"),
                recall_initiation_date=self._parse_date(result.get("recall_initiation_date")),
                report_date=self._parse_date(result.get("report_date")),
                product_quantity=result.get("product_quantity"),
                code_info=result.get("code_info")
            ))

        return recalls

    # Drug Labels

    async def search_drug_labels(
        self,
        drug_name: Optional[str] = None,
        manufacturer: Optional[str] = None,
        ndc: Optional[str] = None,
        pharm_class: Optional[str] = None,
        route: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[DrugLabel]:
        """
        Search drug product labels (SPL)

        Args:
            drug_name: Brand or generic name
            manufacturer: Manufacturer name
            ndc: National Drug Code
            pharm_class: Pharmacologic class
            route: Administration route
            limit: Number of results
            skip: Skip for pagination

        Returns:
            List of drug label records
        """
        search_parts = []

        if drug_name:
            search_parts.append(f'(openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}")')

        if manufacturer:
            search_parts.append(f'openfda.manufacturer_name:"{manufacturer}"')

        if ndc:
            search_parts.append(f'openfda.product_ndc:"{ndc}"')

        if pharm_class:
            search_parts.append(f'openfda.pharm_class_epc:"{pharm_class}"')

        if route:
            search_parts.append(f'openfda.route:"{route}"')

        search = "+AND+".join(search_parts) if search_parts else None

        response = await self._make_request(
            FDAEndpoint.DRUG_LABEL,
            search=search,
            limit=limit,
            skip=skip
        )

        labels = []
        for result in response.get("results", []):
            openfda = result.get("openfda", {})

            labels.append(DrugLabel(
                set_id=result.get("set_id", ""),
                spl_id=result.get("id", ""),
                effective_time=self._parse_date(result.get("effective_time")),
                brand_name=openfda.get("brand_name", [None])[0] if openfda.get("brand_name") else None,
                generic_name=openfda.get("generic_name", [None])[0] if openfda.get("generic_name") else None,
                manufacturer_name=openfda.get("manufacturer_name", [None])[0] if openfda.get("manufacturer_name") else None,
                product_ndc=openfda.get("product_ndc", []),
                product_type=openfda.get("product_type", [None])[0] if openfda.get("product_type") else None,
                route=openfda.get("route", []),
                substance_name=openfda.get("substance_name", []),
                pharm_class=openfda.get("pharm_class_epc", []),
                dosage_form=result.get("dosage_and_administration", [None])[0] if result.get("dosage_and_administration") else None,
                indications_and_usage=result.get("indications_and_usage", [None])[0] if result.get("indications_and_usage") else None,
                warnings=result.get("warnings", [None])[0] if result.get("warnings") else None,
                adverse_reactions=result.get("adverse_reactions", [None])[0] if result.get("adverse_reactions") else None,
                boxed_warning=result.get("boxed_warning", [None])[0] if result.get("boxed_warning") else None
            ))

        return labels

    # Aggregate/Count Methods

    async def get_adverse_event_counts_by_reaction(
        self,
        drug_name: str,
        limit: int = 10
    ) -> Dict[str, int]:
        """Get top adverse reactions for a drug"""
        search = f'patient.drug.medicinalproduct:"{drug_name}"'

        response = await self._make_request(
            FDAEndpoint.DRUG_EVENT,
            search=search,
            count="patient.reaction.reactionmeddrapt.exact",
            limit=limit
        )

        return {
            item["term"]: item["count"]
            for item in response.get("results", [])
        }

    async def get_recall_counts_by_state(
        self,
        endpoint: FDAEndpoint = FDAEndpoint.DRUG_ENFORCEMENT,
        limit: int = 56  # All states + territories
    ) -> Dict[str, int]:
        """Get recall counts by state"""
        response = await self._make_request(
            endpoint,
            count="state",
            limit=limit
        )

        return {
            item["term"]: item["count"]
            for item in response.get("results", [])
        }


# Convenience functions for synchronous usage

def search_drug_adverse_events_sync(
    drug_name: Optional[str] = None,
    reaction: Optional[str] = None,
    serious: Optional[bool] = None,
    limit: int = 100,
    api_key: Optional[str] = None
) -> List[DrugAdverseEvent]:
    """Synchronous wrapper for drug adverse event search"""
    async def _search():
        client = FDAApiClient(api_key=api_key)
        try:
            return await client.search_drug_adverse_events(
                drug_name=drug_name,
                reaction=reaction,
                serious=serious,
                limit=limit
            )
        finally:
            await client.close()

    return asyncio.run(_search())


def search_drug_recalls_sync(
    firm_name: Optional[str] = None,
    product: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 100,
    api_key: Optional[str] = None
) -> List[DrugRecall]:
    """Synchronous wrapper for drug recall search"""
    async def _search():
        client = FDAApiClient(api_key=api_key)
        try:
            return await client.search_drug_recalls(
                firm_name=firm_name,
                product=product,
                state=state,
                limit=limit
            )
        finally:
            await client.close()

    return asyncio.run(_search())


def search_food_recalls_sync(
    firm_name: Optional[str] = None,
    product: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 100,
    api_key: Optional[str] = None
) -> List[FoodRecall]:
    """Synchronous wrapper for food recall search"""
    async def _search():
        client = FDAApiClient(api_key=api_key)
        try:
            return await client.search_food_recalls(
                firm_name=firm_name,
                product=product,
                state=state,
                limit=limit
            )
        finally:
            await client.close()

    return asyncio.run(_search())


if __name__ == "__main__":
    # Example usage
    async def main():
        client = FDAApiClient()

        try:
            # Search for drug adverse events
            print("Searching drug adverse events for 'aspirin'...")
            events = await client.search_drug_adverse_events(
                drug_name="aspirin",
                serious=True,
                limit=5
            )
            for event in events:
                print(f"  Report {event.report_id}: {len(event.reactions)} reactions")

            # Search drug recalls
            print("\nSearching recent drug recalls...")
            recalls = await client.search_drug_recalls(limit=5)
            for recall in recalls:
                print(f"  {recall.recall_number}: {recall.recalling_firm} - {recall.classification}")

            # Get top adverse reactions for a drug
            print("\nTop adverse reactions for 'ibuprofen'...")
            counts = await client.get_adverse_event_counts_by_reaction("ibuprofen", limit=5)
            for reaction, count in counts.items():
                print(f"  {reaction}: {count}")

        finally:
            await client.close()

    asyncio.run(main())
