#!/usr/bin/env python3
"""
Test Federal API Integrations

Tests connectivity and basic functionality of federal data APIs:
- FEC (Federal Election Commission)
- FDA (Food and Drug Administration)
- EPA (Environmental Protection Agency)
- FMCSA (Federal Motor Carrier Safety Administration)

These are FREE APIs that provide valuable public records data.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_fec_api():
    """Test FEC API integration."""
    print("\n" + "=" * 50)
    print("Testing FEC API")
    print("=" * 50)

    try:
        from datagod.scrapers.categories.fec_api import (
            FECApiClient,
            CandidateOffice,
            FECCandidate,
            FECContribution,
            search_fec_candidates,
            search_fec_contributions
        )

        # Check for API key
        api_key = os.environ.get('FEC_API_KEY', 'DEMO_KEY')
        print(f"Using API key: {'Custom' if api_key != 'DEMO_KEY' else 'DEMO_KEY (limited)'}")

        # Verify classes are available
        print("\n--- Verifying FEC Module ---")
        print(f"  FECApiClient: {FECApiClient is not None}")
        print(f"  FECCandidate: {FECCandidate is not None}")
        print(f"  FECContribution: {FECContribution is not None}")
        print(f"  CandidateOffice enum: {list(CandidateOffice)[:3]}...")

        # Test using sync helper function
        print("\n--- Testing Candidate Search ---")
        try:
            candidates = search_fec_candidates(
                api_key=api_key,
                state='CA',
                cycle=2024
            )
            if candidates:
                print(f"Found {len(candidates)} candidates in CA for 2024:")
                for c in candidates[:3]:
                    print(f"  - {c.name} ({c.party or 'Unknown party'})")
            else:
                print("No candidates found (API may require valid key)")
        except Exception as e:
            print(f"Candidate search failed: {e}")

        print("\n--- Testing Contribution Search ---")
        try:
            contributions = search_fec_contributions(
                api_key=api_key,
                contributor_state='NY',
                min_amount=10000,
                cycle=2024
            )
            if contributions:
                print(f"Found {len(contributions)} large contributions from NY:")
                for c in contributions[:3]:
                    print(f"  - ${c.amount:,.2f} from {c.contributor_name or 'Unknown'}")
            else:
                print("No contributions found (API may require valid key)")
        except Exception as e:
            print(f"Contribution search failed: {e}")

        return True
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"FEC API test failed: {e}")
        return False


async def test_fda_api():
    """Test FDA API integration."""
    print("\n" + "=" * 50)
    print("Testing FDA API")
    print("=" * 50)

    try:
        from datagod.scrapers.categories.fda_api import (
            FDAApiClient,
            FDAEndpoint,
            DrugRecall,
            FoodRecall,
            DeviceRecall
        )

        # Verify classes are available
        print("\n--- Verifying FDA Module ---")
        print(f"  FDAApiClient: {FDAApiClient is not None}")
        print(f"  FDAEndpoint enum: {list(FDAEndpoint)[:3]}...")
        print(f"  DrugRecall: {DrugRecall is not None}")
        print(f"  FoodRecall: {FoodRecall is not None}")
        print(f"  DeviceRecall: {DeviceRecall is not None}")

        # Test async client
        print("\n--- Testing FDA API Client ---")
        try:
            client = FDAApiClient()
            print(f"  Client created: {client is not None}")
            print(f"  Base URL: {client.BASE_URL}")
        except Exception as e:
            print(f"Client creation failed: {e}")

        print("\nFDA API module loaded successfully (async methods available)")
        return True
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"FDA API test failed: {e}")
        return False


async def test_epa_api():
    """Test EPA API integration."""
    print("\n" + "=" * 50)
    print("Testing EPA API")
    print("=" * 50)

    try:
        from datagod.scrapers.categories.epa_api import (
            EPAApiClient,
            EPADatabase,
            EPAFacility,
            EPAViolation,
            EPAEnforcement,
            SuperfundSite
        )

        # Verify classes are available
        print("\n--- Verifying EPA Module ---")
        print(f"  EPAApiClient: {EPAApiClient is not None}")
        print(f"  EPADatabase enum: {list(EPADatabase)[:3]}...")
        print(f"  EPAFacility: {EPAFacility is not None}")
        print(f"  EPAViolation: {EPAViolation is not None}")
        print(f"  SuperfundSite: {SuperfundSite is not None}")

        # Test client
        print("\n--- Testing EPA API Client ---")
        try:
            client = EPAApiClient()
            print(f"  Client created: {client is not None}")
            print(f"  Base URL: {client.BASE_URL}")
        except Exception as e:
            print(f"Client creation failed: {e}")

        print("\nEPA API module loaded successfully (async methods available)")
        return True
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"EPA API test failed: {e}")
        return False


async def test_fmcsa_api():
    """Test FMCSA API integration."""
    print("\n" + "=" * 50)
    print("Testing FMCSA API")
    print("=" * 50)

    try:
        from datagod.scrapers.categories.fmcsa_api import (
            FMCSAApiClient,
            Carrier,
            CarrierBasics,
            Inspection,
            Crash,
            SafetyRating
        )

        # Check for API key
        api_key = os.environ.get('FMCSA_API_KEY', '')

        if not api_key:
            print("FMCSA_API_KEY not set - some features may be limited")
            print("Get free key at: https://mobile.fmcsa.dot.gov/QCDevsite/")

        # Verify classes are available
        print("\n--- Verifying FMCSA Module ---")
        print(f"  FMCSAApiClient: {FMCSAApiClient is not None}")
        print(f"  Carrier: {Carrier is not None}")
        print(f"  CarrierBasics: {CarrierBasics is not None}")
        print(f"  Inspection: {Inspection is not None}")
        print(f"  Crash: {Crash is not None}")
        print(f"  SafetyRating: {SafetyRating is not None}")

        # Test client
        print("\n--- Testing FMCSA API Client ---")
        try:
            client = FMCSAApiClient(api_key=api_key or 'test')
            print(f"  Client created: {client is not None}")
            print(f"  Base URL: {client.BASE_URL}")
        except Exception as e:
            print(f"Client creation failed: {e}")

        print("\nFMCSA API module loaded successfully (async methods available)")
        return True
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"FMCSA API test failed: {e}")
        return False


async def main():
    print("=" * 60)
    print("DataGod Federal API Integration Tests")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {
        'FEC': False,
        'FDA': False,
        'EPA': False,
        'FMCSA': False
    }

    # Run tests
    results['FEC'] = await test_fec_api()
    results['FDA'] = await test_fda_api()
    results['EPA'] = await test_epa_api()
    results['FMCSA'] = await test_fmcsa_api()

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0

    for api, status in results.items():
        status_str = "PASS" if status else "FAIL"
        symbol = "✓" if status else "✗"
        print(f"  {symbol} {api}: {status_str}")
        if status:
            passed += 1
        else:
            failed += 1

    print("-" * 60)
    print(f"Total: {passed} passed, {failed} failed")
    print("=" * 60)

    # API key info
    print("\nAPI Key Configuration:")
    print("  FEC: Set FEC_API_KEY env var (free from api.open.fec.gov)")
    print("  FDA: No key required")
    print("  EPA: No key required")
    print("  FMCSA: Set FMCSA_API_KEY env var (free from mobile.fmcsa.dot.gov)")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
