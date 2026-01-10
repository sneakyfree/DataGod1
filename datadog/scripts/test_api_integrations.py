#!/usr/bin/env python3
"""
Test API Integrations Script
Demonstrates and tests the API integration system
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datadog.scrapers.api_manager import get_api_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test API integrations"""
    api_manager = get_api_manager()

    print("="*70)
    print("DATAGOD API INTEGRATION SYSTEM TEST")
    print("="*70)

    # Test 1: List available APIs
    print("\n1. Available APIs:")
    available_apis = api_manager.list_available_apis()
    for api in available_apis:
        info = api_manager.get_api_info(api)
        has_creds = "✓" if info.get('has_credentials') else "✗"
        print(f"   {has_creds} {api} ({info.get('class_name', 'Unknown')})")

    # Test 2: Add sample credentials (mock)
    print("\n2. Adding sample credentials...")
    try:
        # Florida Property Appraiser
        api_manager.add_credentials('florida_property_appraiser', {
            'api_key': 'demo_florida_api_key_12345',
            'base_url': 'https://api-demo.floridapropertyappraiser.com',
            'requests_per_minute': 30,
            'requests_per_hour': 500
        })

        # California SOS
        api_manager.add_credentials('california_sos', {
            'api_key': 'demo_california_api_key_67890',
            'base_url': 'https://api-demo.sos.ca.gov',
            'requests_per_minute': 20,
            'requests_per_hour': 300
        })

        print("✓ Sample credentials added")

    except Exception as e:
        print(f"✗ Failed to add credentials: {e}")

    # Test 3: Test integration creation
    print("\n3. Testing integration creation...")
    test_jurisdictions = [
        (1, 'florida_property_appraiser', 'Miami-Dade County'),
        (2, 'california_sos', 'California Secretary of State')
    ]

    for jur_id, api_type, jur_name in test_jurisdictions:
        try:
            integration = api_manager.get_integration(jur_id, api_type, jur_name)
            if integration:
                print(f"✓ Created {api_type} integration for {jur_name}")
            else:
                print(f"✗ Failed to create {api_type} integration for {jur_name}")
        except Exception as e:
            print(f"✗ Error creating {api_type} for {jur_name}: {e}")

    # Test 4: Test search functionality (mock data)
    print("\n4. Testing search functionality...")
    test_queries = [
        {
            'jurisdiction_id': 1,
            'api_type': 'florida_property_appraiser',
            'query': {'address': '123 Main St', 'owner_name': 'John Smith'}
        },
        {
            'jurisdiction_id': 2,
            'api_type': 'california_sos',
            'query': {'business_name': 'ACME Corp', 'status': 'active'}
        }
    ]

    for test in test_queries:
        try:
            integration = api_manager.get_integration(
                test['jurisdiction_id'],
                test['api_type']
            )
            if integration:
                # Note: This will fail with real APIs since we're using demo credentials
                # In a real scenario, this would call integration.search_records(test['query'])
                print(f"✓ Integration ready for {test['api_type']} search")
                print(f"   Query: {test['query']}")
            else:
                print(f"✗ Integration not available for {test['api_type']}")
        except Exception as e:
            print(f"✗ Search test failed for {test['api_type']}: {e}")

    # Test 5: Cost tracking
    print("\n5. Testing cost tracking...")
    try:
        # Simulate some API usage
        api_manager._track_api_usage('florida_property_appraiser', 5)
        api_manager._track_api_usage('california_sos', 3)
        api_manager._track_api_usage('florida_property_appraiser', 8)

        cost_report = api_manager.get_cost_report(days=30)
        print("Cost Report (30 days):")
        print(f"   Total Cost: ${cost_report['total_cost']:.2f}")
        print(f"   Total Requests: {cost_report['total_requests']}")
        print(f"   Cost per Request: ${cost_report['cost_per_request']:.2f}")

        print("   API Breakdown:")
        for api, stats in cost_report['api_breakdown'].items():
            print(f"     {api}: {stats['requests']} req, ${stats['cost']:.2f}")

    except Exception as e:
        print(f"✗ Cost tracking test failed: {e}")

    # Test 6: Metrics
    print("\n6. API Metrics:")
    try:
        metrics = api_manager.get_api_metrics()
        print(f"   Overall Requests: {metrics['overall']['total_requests']}")
        print(f"   Overall Cost: ${metrics['overall']['total_cost']:.2f}")
        print(f"   Active Integrations: {len(metrics['integrations'])}")

    except Exception as e:
        print(f"✗ Metrics test failed: {e}")

    print("\n" + "="*70)
    print("API INTEGRATION SYSTEM TEST COMPLETE")
    print("="*70)

    print("\nNext Steps:")
    print("1. Obtain real API credentials from jurisdiction providers")
    print("2. Test with actual API endpoints")
    print("3. Implement error handling for production scenarios")
    print("4. Set up monitoring and alerting for API failures")
    print("5. Configure rate limiting based on actual API limits")

if __name__ == "__main__":
    main()
