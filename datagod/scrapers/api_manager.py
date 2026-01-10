"""
API Manager for DataGod
Coordinates multiple API integrations and manages credentials, usage, and costs
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional, Type
from pathlib import Path
from datetime import datetime, timedelta
from datagod.scrapers.base_api_integration import BaseAPIIntegration

# Lazy imports to avoid circular dependencies
FloridaPropertyAppraiserAPI = None
FloridaMiamiDadeAPI = None
FloridaBrowardAPI = None
CaliforniaSecretaryOfStateAPI = None
CaliforniaCorporateFilingsAPI = None
CaliforniaTrademarkAPI = None

def _load_api_classes():
    """Lazily load API classes to avoid import errors"""
    global FloridaPropertyAppraiserAPI, FloridaMiamiDadeAPI, FloridaBrowardAPI
    global CaliforniaSecretaryOfStateAPI, CaliforniaCorporateFilingsAPI, CaliforniaTrademarkAPI

    try:
        from datagod.scrapers.florida_api import (
            FloridaPropertyAppraiserAPI as FPA,
            FloridaMiamiDadeAPI as FMD,
            FloridaBrowardAPI as FB
        )
        FloridaPropertyAppraiserAPI = FPA
        FloridaMiamiDadeAPI = FMD
        FloridaBrowardAPI = FB
    except ImportError:
        pass

    try:
        from datagod.scrapers.california_api import (
            CaliforniaSecretaryOfStateAPI as CSOS,
            CaliforniaCorporateFilingsAPI as CCF,
            CaliforniaTrademarkAPI as CT
        )
        CaliforniaSecretaryOfStateAPI = CSOS
        CaliforniaCorporateFilingsAPI = CCF
        CaliforniaTrademarkAPI = CT
    except ImportError:
        pass

logger = logging.getLogger(__name__)

class APIManager:
    """
    Manages multiple API integrations for different jurisdictions
    Handles credentials, usage tracking, and cost management
    """

    # Registry will be populated on first use
    API_REGISTRY = {}

    @classmethod
    def _get_api_registry(cls):
        """Get or initialize the API registry"""
        if not cls.API_REGISTRY:
            _load_api_classes()
            cls.API_REGISTRY = {
                # Florida APIs
                'florida_property_appraiser': FloridaPropertyAppraiserAPI,
                'florida_miami_dade': FloridaMiamiDadeAPI,
                'florida_broward': FloridaBrowardAPI,
                # California APIs
                'california_sos': CaliforniaSecretaryOfStateAPI,
                'california_corporate': CaliforniaCorporateFilingsAPI,
                'california_trademark': CaliforniaTrademarkAPI,
            }
            # Filter out None values (APIs that failed to import)
            cls.API_REGISTRY = {k: v for k, v in cls.API_REGISTRY.items() if v is not None}
        return cls.API_REGISTRY

    def __init__(self, credentials_file: str = None):
        self.credentials_file = credentials_file or self._get_default_credentials_file()
        self.credentials = self._load_credentials()
        self.active_integrations: Dict[int, BaseAPIIntegration] = {}
        self.usage_stats = {
            'total_requests': 0,
            'total_cost': 0.0,
            'api_usage': {},
            'last_updated': datetime.now().isoformat()
        }

        logger.info(f"Initialized API Manager with {len(self._get_api_registry())} registered APIs")

    def _get_default_credentials_file(self) -> str:
        """Get default credentials file path"""
        config_dir = Path(__file__).parent.parent / "config"
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / "api_credentials.json")

    def _load_credentials(self) -> Dict[str, Any]:
        """Load API credentials from file"""
        if os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load credentials: {e}")
                return {}
        else:
            logger.warning(f"Credentials file not found: {self.credentials_file}")
            return {}

    def _save_credentials(self):
        """Save API credentials to file"""
        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(self.credentials, f, indent=2)
            logger.info("Credentials saved successfully")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def add_credentials(self, api_name: str, credentials: Dict[str, Any]):
        """
        Add or update API credentials

        Args:
            api_name: Name of the API (e.g., 'florida_property_appraiser')
            credentials: Dictionary containing API credentials
        """
        self.credentials[api_name] = {
            **credentials,
            'updated_at': datetime.now().isoformat()
        }
        self._save_credentials()
        logger.info(f"Credentials updated for {api_name}")

    def get_integration(self, jurisdiction_id: int, api_type: str,
                       jurisdiction_name: str = None) -> Optional[BaseAPIIntegration]:
        """
        Get or create an API integration for a jurisdiction

        Args:
            jurisdiction_id: Database ID of the jurisdiction
            api_type: Type of API to use (e.g., 'florida_property_appraiser')
            jurisdiction_name: Name of the jurisdiction for configuration

        Returns:
            API integration instance or None if not available
        """
        cache_key = f"{jurisdiction_id}_{api_type}"

        # Return cached integration if available
        if cache_key in self.active_integrations:
            integration = self.active_integrations[cache_key]
            if self._is_integration_valid(integration):
                return integration
            else:
                # Remove invalid integration
                del self.active_integrations[cache_key]

        # Create new integration
        integration = self._create_integration(jurisdiction_id, api_type, jurisdiction_name)
        if integration:
            self.active_integrations[cache_key] = integration

        return integration

    def _create_integration(self, jurisdiction_id: int, api_type: str,
                           jurisdiction_name: str = None) -> Optional[BaseAPIIntegration]:
        """Create a new API integration instance"""
        registry = self._get_api_registry()
        if api_type not in registry:
            logger.error(f"Unknown API type: {api_type}")
            return None

        credentials = self.credentials.get(api_type, {})
        if not credentials:
            logger.warning(f"No credentials found for {api_type}")
            return None

        # Build configuration
        config = {
            **credentials,
            'jurisdiction_name': jurisdiction_name or 'Unknown'
        }

        try:
            api_class = registry[api_type]
            integration = api_class(jurisdiction_id, config)

            # Test authentication
            if integration.authenticate():
                logger.info(f"Successfully created {api_type} integration for jurisdiction {jurisdiction_id}")
                return integration
            else:
                logger.error(f"Authentication failed for {api_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to create {api_type} integration: {e}")
            return None

    def _is_integration_valid(self, integration: BaseAPIIntegration) -> bool:
        """Check if an integration is still valid"""
        # Check if token is expired (if applicable)
        if hasattr(integration, 'token_expires_at') and integration.token_expires_at:
            return datetime.now() < integration.token_expires_at - timedelta(minutes=5)
        return True

    def search_across_apis(self, jurisdiction_id: int, query: Dict[str, Any],
                          api_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search across multiple APIs for a jurisdiction

        Args:
            jurisdiction_id: Jurisdiction to search in
            query: Search query parameters
            api_types: List of API types to search (None for all available)

        Returns:
            Combined search results from all APIs
        """
        results = []

        if api_types is None:
            # Auto-detect appropriate APIs based on jurisdiction
            api_types = self._get_available_apis_for_jurisdiction(jurisdiction_id)

        for api_type in api_types:
            try:
                integration = self.get_integration(jurisdiction_id, api_type)
                if integration:
                    api_results = integration.search_records(query)
                    results.extend(api_results)

                    # Track usage
                    self._track_api_usage(api_type, len(api_results))

            except Exception as e:
                logger.error(f"Search failed for {api_type}: {e}")
                continue

        logger.info(f"Combined search returned {len(results)} results from {len(api_types)} APIs")
        return results

    def _get_available_apis_for_jurisdiction(self, jurisdiction_id: int) -> List[str]:
        """Get list of available APIs for a jurisdiction"""
        # This would typically query the database to see which APIs are configured
        # For now, return a default set based on jurisdiction patterns

        # TODO: Implement database lookup
        # For now, return common APIs
        return ['florida_property_appraiser', 'california_sos']

    def get_api_metrics(self) -> Dict[str, Any]:
        """Get comprehensive API usage metrics"""
        metrics = {
            'overall': self.usage_stats.copy(),
            'integrations': {}
        }

        # Get metrics from each active integration
        for cache_key, integration in self.active_integrations.items():
            jurisdiction_id, api_type = cache_key.split('_', 1)
            metrics['integrations'][cache_key] = {
                'jurisdiction_id': int(jurisdiction_id),
                'api_type': api_type,
                **integration.get_metrics()
            }

        return metrics

    def _track_api_usage(self, api_type: str, result_count: int):
        """Track API usage for cost calculation"""
        if api_type not in self.usage_stats['api_usage']:
            self.usage_stats['api_usage'][api_type] = {
                'requests': 0,
                'results': 0,
                'cost': 0.0
            }

        self.usage_stats['api_usage'][api_type]['requests'] += 1
        self.usage_stats['api_usage'][api_type]['results'] += result_count

        # Calculate cost (simplified - would need real pricing)
        cost = self._calculate_api_cost(api_type, result_count)
        self.usage_stats['api_usage'][api_type]['cost'] += cost
        self.usage_stats['total_cost'] += cost
        self.usage_stats['total_requests'] += 1

    def _calculate_api_cost(self, api_type: str, result_count: int) -> float:
        """Calculate API usage cost (simplified pricing model)"""
        # Simplified cost model - would need real pricing from each API provider
        cost_per_request = {
            'florida_property_appraiser': 0.10,  # $0.10 per request
            'california_sos': 0.15,               # $0.15 per request
            'florida_miami_dade': 0.12,
            'florida_broward': 0.12,
            'california_corporate': 0.20,
            'california_trademark': 0.18
        }

        base_cost = cost_per_request.get(api_type, 0.10)

        # Add per-result cost for high-volume APIs
        if result_count > 10:
            base_cost += (result_count - 10) * 0.01

        return base_cost

    def get_cost_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate cost report for the specified period"""
        report = {
            'period_days': days,
            'total_cost': self.usage_stats['total_cost'],
            'total_requests': self.usage_stats['total_requests'],
            'cost_per_request': 0.0,
            'api_breakdown': {},
            'generated_at': datetime.now().isoformat()
        }

        if self.usage_stats['total_requests'] > 0:
            report['cost_per_request'] = self.usage_stats['total_cost'] / self.usage_stats['total_requests']

        # API-specific breakdown
        for api_type, usage in self.usage_stats['api_usage'].items():
            report['api_breakdown'][api_type] = {
                'requests': usage['requests'],
                'results': usage['results'],
                'cost': usage['cost'],
                'cost_per_request': usage['cost'] / usage['requests'] if usage['requests'] > 0 else 0,
                'results_per_request': usage['results'] / usage['requests'] if usage['requests'] > 0 else 0
            }

        return report

    def cleanup_expired_integrations(self):
        """Clean up expired or invalid integrations"""
        expired_keys = []

        for cache_key, integration in self.active_integrations.items():
            if not self._is_integration_valid(integration):
                expired_keys.append(cache_key)

        for key in expired_keys:
            del self.active_integrations[key]
            logger.info(f"Cleaned up expired integration: {key}")

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired integrations")

    def list_available_apis(self) -> List[str]:
        """List all available API types"""
        return list(self._get_api_registry().keys())

    def get_api_info(self, api_type: str) -> Dict[str, Any]:
        """Get information about a specific API"""
        registry = self._get_api_registry()
        if api_type not in registry:
            return {}

        api_class = registry[api_type]
        credentials = self.credentials.get(api_type, {})

        return {
            'api_type': api_type,
            'class_name': api_class.__name__ if api_class else 'Unknown',
            'has_credentials': bool(credentials),
            'last_updated': credentials.get('updated_at'),
            'module': api_class.__module__ if api_class else 'unknown'
        }

# Global API manager instance
api_manager = APIManager()

def get_api_manager() -> APIManager:
    """Get the global API manager instance"""
    return api_manager
