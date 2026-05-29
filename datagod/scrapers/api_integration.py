#!/usr/bin/env python3
"""
API Integration System
Build 20+ API integrations for public records data collection
"""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("api_integration.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@dataclass
class APIIntegrationConfig:
    """Configuration for an API integration"""

    name: str
    base_url: str
    api_key: Optional[str] = None
    rate_limit: int = 10
    rate_limit_period: int = 60
    timeout: int = 30
    retry_count: int = 3
    retry_delay: int = 5


class BaseAPIIntegration(ABC):
    """Base class for all API integrations"""

    def __init__(self, config: APIIntegrationConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "DataGod API Integration System",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        if config.api_key:
            self.session.headers["Authorization"] = f"Bearer {config.api_key}"

        self.last_request_time = 0
        self.request_count = 0

    def _check_rate_limit(self):
        """Check and enforce rate limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request > self.config.rate_limit_period:
            self.request_count = 0

        if self.request_count >= self.config.rate_limit:
            sleep_time = self.config.rate_limit_period - time_since_last_request
            if sleep_time > 0:
                logger.info(
                    f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds..."
                )
                time.sleep(sleep_time)
            self.request_count = 0

        self.request_count += 1
        self.last_request_time = time.time()

    def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Make an API request with retry logic"""
        url = f"{self.config.base_url}{endpoint}"
        self._check_rate_limit()

        for attempt in range(self.config.retry_count):
            try:
                response = self.session.request(
                    method, url, timeout=self.config.timeout, **kwargs
                )

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 429:
                    retry_after = int(
                        response.headers.get("Retry-After", self.config.retry_delay)
                    )
                    logger.warning(
                        f"Rate limited. Retrying after {retry_after} seconds..."
                    )
                    time.sleep(retry_after)
                    continue

                logger.error(
                    f"API request failed: {response.status_code} - {response.text}"
                )
                return None

            except requests.exceptions.RequestException as e:
                logger.error(f"Request attempt {attempt + 1} failed: {e}")
                if attempt < self.config.retry_count - 1:
                    time.sleep(self.config.retry_delay)

        return None

    @abstractmethod
    def get_records(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get records from the API"""
        pass

    @abstractmethod
    def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a record to DataGod format"""
        pass

    def close(self):
        """Close the session"""
        self.session.close()


class APIIntegrationManager:
    """Manage multiple API integrations"""

    def __init__(self):
        self.integrations: Dict[str, BaseAPIIntegration] = {}
        self.base_dir = "datagod/scrapers/data"
        os.makedirs(self.base_dir, exist_ok=True)

    def add_integration(self, name: str, integration: BaseAPIIntegration):
        """Add an API integration"""
        self.integrations[name] = integration
        logger.info(f"Added API integration: {name}")

    def get_integration(self, name: str) -> Optional[BaseAPIIntegration]:
        """Get an API integration by name"""
        return self.integrations.get(name)

    def collect_data(
        self, integration_name: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Collect data from a specific integration"""
        integration = self.get_integration(integration_name)
        if not integration:
            logger.error(f"Integration {integration_name} not found")
            return []

        try:
            records = integration.get_records(params)
            normalized_records = [
                integration.normalize_record(record) for record in records
            ]
            return normalized_records
        except Exception as e:
            logger.error(f"Error collecting data from {integration_name}: {e}")
            return []

    def save_integration_data(self, integration_name: str, data: List[Dict[str, Any]]):
        """Save collected data to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{integration_name}_data_{timestamp}.json"
        filepath = os.path.join(self.base_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(data)} records from {integration_name} to {filepath}")
        return filepath


# Example API Integrations


class MockAPIIntegration(BaseAPIIntegration):
    """Mock API integration for testing"""

    def get_records(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get mock records"""
        # Simulate API response
        mock_records = [
            {
                "id": f"mock_{i}",
                "title": f"Mock Record {i}",
                "description": f"This is a mock record {i}",
                "amount": 1000.0 + i * 100,
                "date": "2023-01-01",
                "url": f"https://example.com/record/{i}",
            }
            for i in range(1, 11)
        ]
        return mock_records

    def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize mock record"""
        return {
            "source": "mock_api",
            "source_id": record["id"],
            "title": record["title"],
            "description": record["description"],
            "amount": record["amount"],
            "date": record["date"],
            "url": record["url"],
            "jurisdiction": "Mock County, XX",
            "data_type": "property",
            "raw_data": record,
            "collected_at": datetime.now().isoformat(),
        }


class CaliforniaPropertyAPI(BaseAPIIntegration):
    """California Property Records API Integration"""

    def get_records(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get property records from California API"""
        # This would be the actual API call
        # For now, return mock data
        mock_records = [
            {
                "id": f"ca_property_{i}",
                "county": "Los Angeles",
                "address": f"123 Main St, Los Angeles, CA {90001 + i}",
                "owner": f"John Doe {i}",
                "assessed_value": 500000 + i * 10000,
                "last_sale_date": "2022-06-15",
                "last_sale_amount": 600000 + i * 12000,
                "property_type": "Single Family Residence",
                "bedrooms": 3,
                "bathrooms": 2,
                "square_feet": 1800 + i * 50,
                "year_built": 1990 + i,
            }
            for i in range(1, 6)
        ]
        return mock_records

    def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize California property record"""
        return {
            "source": "california_property_api",
            "source_id": record["id"],
            "title": f"Property at {record['address']}",
            "description": f"Property owned by {record['owner']} in {record['county']} County",
            "amount": record["assessed_value"],
            "date": record["last_sale_date"],
            "url": f"https://california.propertyapi.gov/records/{record['id']}",
            "jurisdiction": f"{record['county']} County, CA",
            "data_type": "property",
            "raw_data": record,
            "collected_at": datetime.now().isoformat(),
            "additional_data": {
                "owner": record["owner"],
                "property_type": record["property_type"],
                "bedrooms": record["bedrooms"],
                "bathrooms": record["bathrooms"],
                "square_feet": record["square_feet"],
                "year_built": record["year_built"],
            },
        }


class TexasPropertyAPI(BaseAPIIntegration):
    """Texas Property Records API Integration"""

    def get_records(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get property records from Texas API"""
        # Mock data for now
        mock_records = [
            {
                "id": f"tx_property_{i}",
                "county": "Harris",
                "address": f"456 Oak Ave, Houston, TX {77001 + i}",
                "owner": f"Jane Smith {i}",
                "appraised_value": 350000 + i * 8000,
                "last_sale_date": "2021-03-10",
                "last_sale_amount": 400000 + i * 10000,
                "property_type": "Single Family Residence",
                "bedrooms": 4,
                "bathrooms": 3,
                "square_feet": 2200 + i * 75,
                "year_built": 2005 + i,
            }
            for i in range(1, 6)
        ]
        return mock_records

    def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Texas property record"""
        return {
            "source": "texas_property_api",
            "source_id": record["id"],
            "title": f"Property at {record['address']}",
            "description": f"Property owned by {record['owner']} in {record['county']} County",
            "amount": record["appraised_value"],
            "date": record["last_sale_date"],
            "url": f"https://texas.propertyapi.gov/records/{record['id']}",
            "jurisdiction": f"{record['county']} County, TX",
            "data_type": "property",
            "raw_data": record,
            "collected_at": datetime.now().isoformat(),
            "additional_data": {
                "owner": record["owner"],
                "property_type": record["property_type"],
                "bedrooms": record["bedrooms"],
                "bathrooms": record["bathrooms"],
                "square_feet": record["square_feet"],
                "year_built": record["year_built"],
            },
        }


class FloridaPropertyAPI(BaseAPIIntegration):
    """Florida Property Records API Integration"""

    def get_records(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get property records from Florida API"""
        # Mock data
        mock_records = [
            {
                "id": f"fl_property_{i}",
                "county": "Miami-Dade",
                "address": f"789 Palm St, Miami, FL {33101 + i}",
                "owner": f"Robert Johnson {i}",
                "assessed_value": 450000 + i * 9000,
                "last_sale_date": "2020-11-05",
                "last_sale_amount": 500000 + i * 11000,
                "property_type": "Condominium",
                "bedrooms": 2,
                "bathrooms": 2,
                "square_feet": 1500 + i * 40,
                "year_built": 2010 + i,
            }
            for i in range(1, 6)
        ]
        return mock_records

    def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Florida property record"""
        return {
            "source": "florida_property_api",
            "source_id": record["id"],
            "title": f"Property at {record['address']}",
            "description": f"Property owned by {record['owner']} in {record['county']} County",
            "amount": record["assessed_value"],
            "date": record["last_sale_date"],
            "url": f"https://florida.propertyapi.gov/records/{record['id']}",
            "jurisdiction": f"{record['county']} County, FL",
            "data_type": "property",
            "raw_data": record,
            "collected_at": datetime.now().isoformat(),
            "additional_data": {
                "owner": record["owner"],
                "property_type": record["property_type"],
                "bedrooms": record["bedrooms"],
                "bathrooms": record["bathrooms"],
                "square_feet": record["square_feet"],
                "year_built": record["year_built"],
            },
        }


def main():
    """Main execution function"""
    print("🚀 DataGod API Integration System")
    print("=" * 50)

    # Initialize API integration manager
    manager = APIIntegrationManager()

    # Add mock integration for testing
    mock_config = APIIntegrationConfig(
        name="mock_api",
        base_url="https://api.mockapi.example.com/v1",
        rate_limit=10,
        rate_limit_period=60,
    )
    mock_api = MockAPIIntegration(mock_config)
    manager.add_integration("mock_api", mock_api)

    # Add California API
    ca_config = APIIntegrationConfig(
        name="california_property_api",
        base_url="https://api.california.gov/property/v1",
        rate_limit=20,
        rate_limit_period=60,
    )
    ca_api = CaliforniaPropertyAPI(ca_config)
    manager.add_integration("california_property_api", ca_api)

    # Add Texas API
    tx_config = APIIntegrationConfig(
        name="texas_property_api",
        base_url="https://api.texas.gov/property/v1",
        rate_limit=15,
        rate_limit_period=60,
    )
    tx_api = TexasPropertyAPI(tx_config)
    manager.add_integration("texas_property_api", tx_api)

    # Add Florida API
    fl_config = APIIntegrationConfig(
        name="florida_property_api",
        base_url="https://api.florida.gov/property/v1",
        rate_limit=18,
        rate_limit_period=60,
    )
    fl_api = FloridaPropertyAPI(fl_config)
    manager.add_integration("florida_property_api", fl_api)

    print("Available API Integrations:")
    for i, name in enumerate(manager.integrations.keys(), 1):
        print(f"{i}. {name}")

    # Test each integration
    print("\n" + "=" * 50)
    print("Testing API Integrations...")

    for integration_name in manager.integrations.keys():
        print(f"\nTesting {integration_name}...")
        try:
            # Collect data
            data = manager.collect_data(integration_name, {})

            if data:
                # Save data
                filepath = manager.save_integration_data(integration_name, data)
                print(
                    f"✅ Success! Collected {len(data)} records from {integration_name}"
                )
                print(f"   Data saved to: {filepath}")
            else:
                print(f"❌ No data collected from {integration_name}")

        except Exception as e:
            print(f"❌ Error testing {integration_name}: {e}")

    print("\n" + "=" * 50)
    print("API Integration Testing Complete!")


if __name__ == "__main__":
    main()
