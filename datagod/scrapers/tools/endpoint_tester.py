"""
Endpoint Tester for Data Sources

Tests availability and responsiveness of data source endpoints
across all configured jurisdictions.
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EndpointStatus(Enum):
    """Status of an endpoint test."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    AUTH_REQUIRED = "auth_required"
    RATE_LIMITED = "rate_limited"
    REDIRECT = "redirect"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class EndpointTestResult:
    """Result of testing a single endpoint."""
    url: str
    status: EndpointStatus
    http_status: Optional[int]
    response_time_ms: Optional[float]
    redirect_url: Optional[str]
    content_type: Optional[str]
    error_message: Optional[str]
    tested_at: str


@dataclass
class JurisdictionTestResult:
    """Results of testing all endpoints for a jurisdiction."""
    fips_code: str
    name: str
    state_code: str
    endpoints: Dict[str, EndpointTestResult]
    availability_score: float  # 0.0 to 1.0
    tested_at: str


class EndpointTester:
    """
    Tests endpoint availability for data sources.

    Performs async HTTP HEAD/GET requests to verify that
    configured data source URLs are accessible.
    """

    # Timeout for individual requests (seconds)
    REQUEST_TIMEOUT = 10

    # Concurrent request limit
    CONCURRENT_LIMIT = 10

    # User agent for requests
    USER_AGENT = "DataGod Endpoint Tester/1.0 (Availability Check)"

    # Federal API endpoints to test
    FEDERAL_ENDPOINTS = {
        'fec': {
            'name': 'FEC Campaign Finance',
            'url': 'https://api.open.fec.gov/v1/candidates/?api_key=DEMO_KEY&per_page=1',
            'category': 'voter_records',
        },
        'fda_drugs': {
            'name': 'FDA Drug Events',
            'url': 'https://api.fda.gov/drug/event.json?limit=1',
            'category': 'regulatory_records',
        },
        'fda_recalls': {
            'name': 'FDA Drug Recalls',
            'url': 'https://api.fda.gov/drug/enforcement.json?limit=1',
            'category': 'regulatory_records',
        },
        'epa_tri': {
            'name': 'EPA TRI Facilities',
            'url': 'https://enviro.epa.gov/enviro/efservice/tri_facility/rows/1:1/json',
            'category': 'regulatory_records',
        },
        'nhtsa_recalls': {
            'name': 'NHTSA Vehicle Recalls',
            'url': 'https://api.nhtsa.gov/recalls/recallsByVehicle?make=ford&model=f-150&modelYear=2020',
            'category': 'transportation',
        },
        'nhtsa_vin': {
            'name': 'NHTSA VIN Decoder',
            'url': 'https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/1HGBH41JXMN109186?format=json',
            'category': 'transportation',
        },
        'census': {
            'name': 'Census ACS Data',
            'url': 'https://api.census.gov/data/2020/acs/acs5?get=NAME&for=state:*',
            'category': 'federal_sources',
        },
        'nppes': {
            'name': 'NPPES NPI Registry',
            'url': 'https://npiregistry.cms.hhs.gov/api/?version=2.1&limit=1',
            'category': 'health_safety',
        },
        'faa_registry': {
            'name': 'FAA Aircraft Registry',
            'url': 'https://registry.faa.gov/aircraftinquiry/',
            'category': 'asset_records',
        },
        'sec_edgar': {
            'name': 'SEC EDGAR',
            'url': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&output=atom',
            'category': 'financial_records',
        },
        'usaspending': {
            'name': 'USAspending Awards',
            'url': 'https://api.usaspending.gov/api/v2/references/agency/',
            'category': 'employment_records',
        },
        'osha': {
            'name': 'OSHA Enforcement Data',
            'url': 'https://enforcedata.dol.gov/views/data_summary.php',
            'category': 'regulatory_records',
        },
        'college_scorecard': {
            'name': 'College Scorecard',
            'url': 'https://api.data.gov/ed/collegescorecard/v1/schools?api_key=DEMO_KEY&per_page=1',
            'category': 'education_records',
        },
        'propublica_nonprofits': {
            'name': 'ProPublica Nonprofits',
            'url': 'https://projects.propublica.org/nonprofits/api/v2/search.json?q=red+cross',
            'category': 'financial_records',
        },
        'nsopw': {
            'name': 'National Sex Offender Registry',
            'url': 'https://www.nsopw.gov/',
            'category': 'criminal_records',
        },
    }

    def __init__(self, configs_dir: Optional[str] = None):
        """
        Initialize the endpoint tester.

        Args:
            configs_dir: Path to scraper configs directory
        """
        if configs_dir is None:
            configs_dir = Path(__file__).parent.parent / "configs"
        self.configs_dir = Path(configs_dir)
        self.results_dir = Path(__file__).parent.parent / "test_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def test_endpoint(
        self,
        session: aiohttp.ClientSession,
        url: str,
        method: str = "HEAD"
    ) -> EndpointTestResult:
        """
        Test a single endpoint.

        Args:
            session: aiohttp client session
            url: URL to test
            method: HTTP method (HEAD or GET)

        Returns:
            EndpointTestResult
        """
        start_time = datetime.utcnow()

        try:
            timeout = aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)

            if method == "HEAD":
                async with session.head(url, timeout=timeout, allow_redirects=False) as response:
                    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                    # Determine status
                    if response.status == 200:
                        status = EndpointStatus.AVAILABLE
                    elif response.status == 301 or response.status == 302:
                        status = EndpointStatus.REDIRECT
                    elif response.status == 401 or response.status == 403:
                        status = EndpointStatus.AUTH_REQUIRED
                    elif response.status == 429:
                        status = EndpointStatus.RATE_LIMITED
                    elif response.status >= 500:
                        status = EndpointStatus.ERROR
                    elif response.status == 404:
                        status = EndpointStatus.UNAVAILABLE
                    else:
                        status = EndpointStatus.UNKNOWN

                    return EndpointTestResult(
                        url=url,
                        status=status,
                        http_status=response.status,
                        response_time_ms=round(response_time, 2),
                        redirect_url=str(response.headers.get('Location', '')),
                        content_type=response.headers.get('Content-Type', ''),
                        error_message=None,
                        tested_at=start_time.isoformat(),
                    )
            else:
                # GET request
                async with session.get(url, timeout=timeout, allow_redirects=False) as response:
                    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                    if response.status == 200:
                        status = EndpointStatus.AVAILABLE
                    elif response.status == 301 or response.status == 302:
                        status = EndpointStatus.REDIRECT
                    elif response.status == 401 or response.status == 403:
                        status = EndpointStatus.AUTH_REQUIRED
                    elif response.status == 429:
                        status = EndpointStatus.RATE_LIMITED
                    elif response.status >= 500:
                        status = EndpointStatus.ERROR
                    elif response.status == 404:
                        status = EndpointStatus.UNAVAILABLE
                    else:
                        status = EndpointStatus.UNKNOWN

                    return EndpointTestResult(
                        url=url,
                        status=status,
                        http_status=response.status,
                        response_time_ms=round(response_time, 2),
                        redirect_url=str(response.headers.get('Location', '')),
                        content_type=response.headers.get('Content-Type', ''),
                        error_message=None,
                        tested_at=start_time.isoformat(),
                    )

        except asyncio.TimeoutError:
            return EndpointTestResult(
                url=url,
                status=EndpointStatus.TIMEOUT,
                http_status=None,
                response_time_ms=self.REQUEST_TIMEOUT * 1000,
                redirect_url=None,
                content_type=None,
                error_message="Request timed out",
                tested_at=start_time.isoformat(),
            )
        except aiohttp.ClientError as e:
            return EndpointTestResult(
                url=url,
                status=EndpointStatus.ERROR,
                http_status=None,
                response_time_ms=None,
                redirect_url=None,
                content_type=None,
                error_message=str(e),
                tested_at=start_time.isoformat(),
            )
        except Exception as e:
            return EndpointTestResult(
                url=url,
                status=EndpointStatus.ERROR,
                http_status=None,
                response_time_ms=None,
                redirect_url=None,
                content_type=None,
                error_message=f"Unexpected error: {str(e)}",
                tested_at=start_time.isoformat(),
            )

    async def test_state_config(
        self,
        state_code: str,
        limit_counties: Optional[int] = None
    ) -> List[JurisdictionTestResult]:
        """
        Test all endpoints in a state's configuration.

        Args:
            state_code: Two-letter state code
            limit_counties: Optional limit on counties to test

        Returns:
            List of JurisdictionTestResult
        """
        config_path = self.configs_dir / f"{state_code.lower()}.json"

        if not config_path.exists():
            logger.warning(f"No config found for state: {state_code}")
            return []

        with open(config_path, 'r') as f:
            config = json.load(f)

        counties = config.get('counties', [])
        if limit_counties:
            counties = counties[:limit_counties]

        results = []
        connector = aiohttp.TCPConnector(limit=self.CONCURRENT_LIMIT)

        async with aiohttp.ClientSession(
            connector=connector,
            headers={"User-Agent": self.USER_AGENT}
        ) as session:

            for county in counties:
                endpoints_results = {}
                base_urls = county.get('base_urls', {})

                # Test each category's base URL
                for category, url in base_urls.items():
                    result = await self.test_endpoint(session, url)
                    endpoints_results[category] = result

                # Calculate availability score
                available_count = sum(
                    1 for r in endpoints_results.values()
                    if r.status == EndpointStatus.AVAILABLE
                )
                total_count = len(endpoints_results)
                availability_score = available_count / total_count if total_count > 0 else 0

                jurisdiction_result = JurisdictionTestResult(
                    fips_code=county.get('fips_code', ''),
                    name=county.get('name', ''),
                    state_code=state_code,
                    endpoints=endpoints_results,
                    availability_score=round(availability_score, 2),
                    tested_at=datetime.utcnow().isoformat(),
                )
                results.append(jurisdiction_result)

        return results

    async def test_all_states(
        self,
        tier: Optional[int] = None,
        limit_counties_per_state: int = 5
    ) -> Dict[str, List[JurisdictionTestResult]]:
        """
        Test endpoints for all configured states.

        Args:
            tier: Optional tier to limit testing
            limit_counties_per_state: Max counties to test per state

        Returns:
            Dictionary mapping state codes to results
        """
        results = {}
        config_files = list(self.configs_dir.glob("*.json"))

        for config_path in config_files:
            state_code = config_path.stem.upper()

            try:
                state_results = await self.test_state_config(
                    state_code,
                    limit_counties=limit_counties_per_state
                )
                results[state_code] = state_results
                logger.info(f"Tested {len(state_results)} counties in {state_code}")
            except Exception as e:
                logger.error(f"Error testing {state_code}: {e}")
                results[state_code] = []

        return results

    def save_results(
        self,
        results: Dict[str, List[JurisdictionTestResult]],
        filename: Optional[str] = None
    ) -> str:
        """
        Save test results to JSON file.

        Args:
            results: Test results dictionary
            filename: Optional filename

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"endpoint_test_{timestamp}.json"

        output_path = self.results_dir / filename

        # Convert to JSON-serializable format
        output = {}
        for state_code, state_results in results.items():
            output[state_code] = []
            for jr in state_results:
                jr_dict = {
                    "fips_code": jr.fips_code,
                    "name": jr.name,
                    "state_code": jr.state_code,
                    "availability_score": jr.availability_score,
                    "tested_at": jr.tested_at,
                    "endpoints": {},
                }
                for category, er in jr.endpoints.items():
                    jr_dict["endpoints"][category] = {
                        "url": er.url,
                        "status": er.status.value,
                        "http_status": er.http_status,
                        "response_time_ms": er.response_time_ms,
                        "error_message": er.error_message,
                    }
                output[state_code].append(jr_dict)

        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        logger.info(f"Saved results to: {output_path}")
        return str(output_path)

    def get_availability_summary(
        self,
        results: Dict[str, List[JurisdictionTestResult]]
    ) -> Dict[str, Any]:
        """
        Generate summary statistics from test results.

        Args:
            results: Test results dictionary

        Returns:
            Summary statistics
        """
        total_jurisdictions = 0
        total_endpoints = 0
        available_endpoints = 0
        unavailable_endpoints = 0
        auth_required_endpoints = 0
        timeout_endpoints = 0

        state_summaries = {}

        for state_code, state_results in results.items():
            state_total = 0
            state_available = 0

            for jr in state_results:
                total_jurisdictions += 1

                for category, er in jr.endpoints.items():
                    total_endpoints += 1
                    state_total += 1

                    if er.status == EndpointStatus.AVAILABLE:
                        available_endpoints += 1
                        state_available += 1
                    elif er.status == EndpointStatus.UNAVAILABLE:
                        unavailable_endpoints += 1
                    elif er.status == EndpointStatus.AUTH_REQUIRED:
                        auth_required_endpoints += 1
                    elif er.status == EndpointStatus.TIMEOUT:
                        timeout_endpoints += 1

            state_summaries[state_code] = {
                "jurisdictions_tested": len(state_results),
                "endpoints_tested": state_total,
                "endpoints_available": state_available,
                "availability_pct": round(state_available / state_total * 100, 1) if state_total > 0 else 0,
            }

        return {
            "total_jurisdictions": total_jurisdictions,
            "total_endpoints": total_endpoints,
            "available_endpoints": available_endpoints,
            "unavailable_endpoints": unavailable_endpoints,
            "auth_required_endpoints": auth_required_endpoints,
            "timeout_endpoints": timeout_endpoints,
            "overall_availability_pct": round(available_endpoints / total_endpoints * 100, 1) if total_endpoints > 0 else 0,
            "state_summaries": state_summaries,
        }


    async def test_federal_endpoints(self) -> Dict[str, EndpointTestResult]:
        """
        Test all federal API endpoints.

        Returns:
            Dictionary mapping endpoint ID to test result
        """
        results = {}
        connector = aiohttp.TCPConnector(limit=self.CONCURRENT_LIMIT)

        async with aiohttp.ClientSession(
            connector=connector,
            headers={"User-Agent": self.USER_AGENT}
        ) as session:

            for endpoint_id, config in self.FEDERAL_ENDPOINTS.items():
                try:
                    result = await self.test_endpoint(session, config['url'], method="GET")
                    results[endpoint_id] = result
                    logger.info(f"Tested {config['name']}: {result.status.value}")
                except Exception as e:
                    logger.error(f"Error testing {endpoint_id}: {e}")
                    results[endpoint_id] = EndpointTestResult(
                        url=config['url'],
                        status=EndpointStatus.ERROR,
                        http_status=None,
                        response_time_ms=None,
                        redirect_url=None,
                        content_type=None,
                        error_message=str(e),
                        tested_at=datetime.utcnow().isoformat(),
                    )

        return results

    def get_federal_summary(self, results: Dict[str, EndpointTestResult]) -> Dict[str, Any]:
        """
        Generate summary of federal endpoint tests.

        Args:
            results: Federal endpoint test results

        Returns:
            Summary statistics
        """
        total = len(results)
        available = sum(1 for r in results.values() if r.status == EndpointStatus.AVAILABLE)
        auth_required = sum(1 for r in results.values() if r.status == EndpointStatus.AUTH_REQUIRED)
        timeout = sum(1 for r in results.values() if r.status == EndpointStatus.TIMEOUT)
        errors = sum(1 for r in results.values() if r.status == EndpointStatus.ERROR)

        # Group by category
        by_category: Dict[str, Dict[str, int]] = {}
        for endpoint_id, result in results.items():
            category = self.FEDERAL_ENDPOINTS[endpoint_id]['category']
            if category not in by_category:
                by_category[category] = {'total': 0, 'available': 0}
            by_category[category]['total'] += 1
            if result.status == EndpointStatus.AVAILABLE:
                by_category[category]['available'] += 1

        # Calculate average response time
        response_times = [r.response_time_ms for r in results.values() if r.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        return {
            'total_endpoints': total,
            'available': available,
            'auth_required': auth_required,
            'timeout': timeout,
            'errors': errors,
            'availability_pct': round(available / total * 100, 1) if total > 0 else 0,
            'avg_response_time_ms': round(avg_response_time, 2),
            'by_category': by_category,
            'endpoints': {
                endpoint_id: {
                    'name': self.FEDERAL_ENDPOINTS[endpoint_id]['name'],
                    'category': self.FEDERAL_ENDPOINTS[endpoint_id]['category'],
                    'status': results[endpoint_id].status.value,
                    'http_status': results[endpoint_id].http_status,
                    'response_time_ms': results[endpoint_id].response_time_ms,
                }
                for endpoint_id in results
            }
        }


async def main():
    """CLI entry point for endpoint tester."""
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Test data source endpoints")
    parser.add_argument("--state", type=str, help="Test specific state")
    parser.add_argument("--all", action="store_true", help="Test all configured states")
    parser.add_argument("--federal", action="store_true", help="Test federal API endpoints")
    parser.add_argument("--limit", type=int, default=5, help="Limit counties per state")
    parser.add_argument("--save", action="store_true", help="Save results to file")

    args = parser.parse_args()

    tester = EndpointTester()

    if args.federal:
        print("\n=== Testing Federal API Endpoints ===\n")
        results = await tester.test_federal_endpoints()
        summary = tester.get_federal_summary(results)

        print(f"Total endpoints: {summary['total_endpoints']}")
        print(f"Available: {summary['available']}")
        print(f"Auth required: {summary['auth_required']}")
        print(f"Timeouts: {summary['timeout']}")
        print(f"Errors: {summary['errors']}")
        print(f"Availability: {summary['availability_pct']}%")
        print(f"Avg response time: {summary['avg_response_time_ms']}ms")
        print("\n--- Endpoint Details ---")
        for endpoint_id, details in summary['endpoints'].items():
            status_icon = "✓" if details['status'] == 'available' else "✗"
            print(f"  {status_icon} {details['name']}: {details['status']} ({details['response_time_ms']}ms)")

    elif args.state:
        results = await tester.test_state_config(args.state.upper(), limit_counties=args.limit)
        print(f"\nTested {len(results)} jurisdictions in {args.state.upper()}")

        for jr in results:
            print(f"  {jr.name}: {jr.availability_score * 100:.0f}% available")

    elif args.all:
        results = await tester.test_all_states(limit_counties_per_state=args.limit)
        summary = tester.get_availability_summary(results)

        print("\n=== Endpoint Test Summary ===")
        print(f"Total jurisdictions tested: {summary['total_jurisdictions']}")
        print(f"Total endpoints tested: {summary['total_endpoints']}")
        print(f"Overall availability: {summary['overall_availability_pct']}%")

        if args.save:
            path = tester.save_results(results)
            print(f"\nResults saved to: {path}")

    else:
        parser.print_help()


# Convenience function for sync usage
def test_federal_apis_sync() -> Dict[str, Any]:
    """Test federal APIs synchronously and return summary."""
    tester = EndpointTester()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(tester.test_federal_endpoints())
        return tester.get_federal_summary(results)
    finally:
        loop.close()


if __name__ == "__main__":
    asyncio.run(main())
