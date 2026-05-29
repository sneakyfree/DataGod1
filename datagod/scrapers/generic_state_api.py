"""
Generic State API Integration
Configuration-driven API handler that can work with any state's public records

This class allows adding new states via JSON configuration files rather than
writing new Python code for each state.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from datagod.scrapers.base_api_integration import (
    APIAuthenticationError,
    APIDataError,
    APIKeyAuthentication,
    BaseAPIIntegration,
    HMACAuthentication,
    OAuth2Authentication,
    RateLimitExceeded,
)

logger = logging.getLogger(__name__)


class GenericStateAPIError(Exception):
    """Raised when GenericStateAPI encounters an error"""

    pass


class GenericStateAPI(BaseAPIIntegration):
    """
    Configuration-driven API integration for any state's public records.

    This class eliminates the need to write custom Python code for each state.
    Instead, state-specific behavior is defined in JSON configuration files.

    Usage:
        config = load_state_config('TN')
        api = GenericStateAPI(jurisdiction_id=1, config=config)
        results = api.search_records({'name': 'Smith'}, county='Davidson')
    """

    def __init__(self, jurisdiction_id: int, config: Dict[str, Any]):
        """
        Initialize a GenericStateAPI instance.

        Args:
            jurisdiction_id: Database ID for this jurisdiction
            config: State configuration dictionary (loaded from JSON)
        """
        # Validate config
        self._validate_config(config)

        # Extract key fields
        self.state_code = config["state_code"]
        self.state_name = config["state_name"]
        self.auth_type = config.get("auth_type", "none")
        self.counties = {
            c["name"].lower().replace(" ", "_").replace("'", ""): c
            for c in config.get("counties", [])
        }
        self.data_sources = config.get("data_sources", {})
        self.current_county = None

        # Build base config for parent class
        base_config = {
            "base_url": config.get("base_url", ""),
            "requests_per_minute": config.get("requests_per_minute", 60),
            "requests_per_hour": config.get("requests_per_hour", 1000),
            "timeout": config.get("timeout", 30),
            "retry_attempts": config.get("retry_attempts", 3),
            "retry_backoff": config.get("retry_backoff", 1.0),
            "api_key": config.get("api_key"),
            "api_secret": config.get("api_secret"),
        }

        # Add OAuth2 config if needed
        if self.auth_type == "oauth2":
            base_config.update(
                {
                    "token_url": config.get("token_url"),
                    "client_id": config.get("client_id"),
                    "client_secret": config.get("client_secret"),
                    "scope": config.get("scope", ""),
                }
            )

        super().__init__(jurisdiction_id, base_config)

        # Store full config for reference
        self.full_config = config

        logger.info(
            f"Initialized GenericStateAPI for {self.state_name} ({self.state_code})"
        )

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate the state configuration."""
        required = ["state_code", "state_name"]
        for field in required:
            if field not in config:
                raise GenericStateAPIError(f"Missing required config field: {field}")

    def authenticate(self) -> bool:
        """
        Authenticate based on the configured auth type.

        Returns:
            True if authentication successful or not required
        """
        if self.auth_type == "none":
            logger.info(f"{self.state_name} API does not require authentication")
            return True

        if self.auth_type == "api_key":
            if not self.api_key:
                logger.warning(f"API key not configured for {self.state_name}")
                return True  # Allow attempts without key
            logger.info(f"{self.state_name} API key authentication configured")
            return True

        if self.auth_type == "oauth2":
            return self._oauth2_authenticate()

        if self.auth_type == "hmac":
            if not self.api_key or not self.api_secret:
                logger.warning(f"HMAC credentials not configured for {self.state_name}")
                return True
            logger.info(f"{self.state_name} HMAC authentication configured")
            return True

        logger.warning(f"Unknown auth type: {self.auth_type}")
        return True

    def _oauth2_authenticate(self) -> bool:
        """Perform OAuth2 authentication."""
        from datetime import timedelta

        import requests

        token_url = self.config.get("token_url")
        client_id = self.config.get("client_id")
        client_secret = self.config.get("client_secret")

        if not all([token_url, client_id, client_secret]):
            logger.error("OAuth2 credentials incomplete")
            return False

        try:
            data = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": self.config.get("scope", ""),
            }

            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

            logger.info(f"{self.state_name} OAuth2 authentication successful")
            return True

        except Exception as e:
            logger.error(f"OAuth2 authentication failed: {e}")
            return False

    def set_county(self, county_name: str) -> bool:
        """
        Set the active county for queries.

        Args:
            county_name: Name of the county

        Returns:
            True if county is valid and configured
        """
        county_key = county_name.lower().replace(" ", "_").replace("'", "")

        if county_key not in self.counties:
            # Try to find by partial match
            for key in self.counties:
                if county_key in key or key in county_key:
                    county_key = key
                    break
            else:
                logger.warning(f"County '{county_name}' not found in {self.state_name}")
                return False

        self.current_county = county_key
        county_config = self.counties[county_key]

        # Update base URL if county has specific URL
        if county_config.get("base_url"):
            self.base_url = county_config["base_url"]

        logger.info(f"Set active county to {county_config['name']}")
        return True

    def get_county_config(self, county_name: str = None) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific county."""
        if county_name:
            county_key = county_name.lower().replace(" ", "_").replace("'", "")
        else:
            county_key = self.current_county

        return self.counties.get(county_key)

    def list_counties(self) -> List[str]:
        """List all supported counties."""
        return [c["name"] for c in self.counties.values()]

    def search_records(self, query: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        """
        Search for records across all record types.

        Args:
            query: Search parameters
            **kwargs: Additional parameters including 'county'

        Returns:
            List of matching records
        """
        county = kwargs.get("county")
        if county:
            self.set_county(county)

        record_type = query.get("record_type", "all")

        results = []

        if record_type in ("all", "property"):
            results.extend(self._search_endpoint("property", query))

        if record_type in ("all", "deed"):
            results.extend(self._search_endpoint("deed", query))

        if record_type in ("all", "lien"):
            results.extend(self._search_endpoint("lien", query))

        logger.info(f"Search returned {len(results)} total records")
        return results

    def _search_endpoint(
        self, record_type: str, query: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Search a specific endpoint type.

        Args:
            record_type: Type of records to search (property, deed, lien)
            query: Search parameters

        Returns:
            List of matching records
        """
        county_config = self.get_county_config()
        if not county_config:
            logger.warning(f"No county configured for {record_type} search")
            return []

        # Get endpoint from county config or data sources config
        endpoint = county_config.get(f"{record_type}_endpoint")
        if not endpoint and record_type in self.data_sources:
            endpoint = self.data_sources[record_type].get("url")
        if not endpoint:
            endpoint = f"/{record_type}/search"

        # Build request parameters based on record type
        params = self._build_search_params(record_type, query)

        try:
            response = self.make_request("GET", endpoint, params=params)
            data = self.validate_response(response)

            # Handle various response formats
            records = data.get(
                "results", data.get(f"{record_type}s", data.get("data", []))
            )
            if isinstance(records, dict):
                records = [records]

            results = []
            for record in records:
                mapped = self.map_api_data_to_standard_format(record)
                mapped["record_type"] = record_type
                mapped["source_county"] = county_config["name"]
                results.append(mapped)

            logger.info(f"{record_type.title()} search returned {len(results)} records")
            return results

        except (APIDataError, RateLimitExceeded) as e:
            logger.error(f"{record_type.title()} search failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in {record_type} search: {e}")
            return []

    def _build_search_params(
        self, record_type: str, query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build API-specific search parameters from generic query."""
        params = {}

        # Common field mappings
        if record_type == "property":
            if query.get("name"):
                params["owner_name"] = query["name"]
            if query.get("address"):
                params["property_address"] = query["address"]
            if query.get("parcel_id"):
                params["parcel_number"] = query["parcel_id"]

        elif record_type == "deed":
            if query.get("name"):
                params["party_name"] = query["name"]
            if query.get("date_from"):
                params["start_date"] = query["date_from"]
            if query.get("date_to"):
                params["end_date"] = query["date_to"]
            if query.get("document_number"):
                params["doc_number"] = query["document_number"]

        elif record_type == "lien":
            if query.get("name"):
                params["debtor_name"] = query["name"]
            if query.get("date_from"):
                params["filed_from"] = query["date_from"]
            if query.get("date_to"):
                params["filed_to"] = query["date_to"]

        # Add any additional query params
        for key, value in query.items():
            if (
                key
                not in [
                    "name",
                    "address",
                    "parcel_id",
                    "date_from",
                    "date_to",
                    "document_number",
                    "record_type",
                ]
                and value
            ):
                params[key] = value

        return params

    def get_record_details(self, record_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific record.

        Args:
            record_id: Unique record identifier

        Returns:
            Detailed record information
        """
        county_config = self.get_county_config()
        if not county_config:
            logger.warning("No county configured for record details")
            return {}

        endpoint = f"/record/{record_id}"

        try:
            response = self.make_request("GET", endpoint)
            data = self.validate_response(response)
            return self.map_api_data_to_standard_format(data)

        except Exception as e:
            logger.error(f"Get record details failed: {e}")
            return {}

    def map_api_data_to_standard_format(
        self, api_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map state-specific API data to standard DataGod format.

        Args:
            api_data: Raw API response data

        Returns:
            Standardized record dictionary
        """
        standard = {
            "source_state": self.state_code,
            "source_api": f"GenericStateAPI:{self.state_code}",
            "raw_data": api_data,
            "fetched_at": datetime.now().isoformat(),
        }

        # Field mappings - try multiple possible field names
        field_mappings = {
            "record_id": [
                "id",
                "record_id",
                "document_id",
                "doc_id",
                "reference_number",
            ],
            "document_number": [
                "document_number",
                "doc_number",
                "instrument_number",
                "book_page",
            ],
            "record_date": [
                "record_date",
                "recorded_date",
                "filing_date",
                "date",
                "date_recorded",
            ],
            "document_type": ["document_type", "doc_type", "type", "instrument_type"],
            "grantor": ["grantor", "seller", "from_party", "party1"],
            "grantee": ["grantee", "buyer", "to_party", "party2"],
            "property_address": [
                "property_address",
                "address",
                "situs_address",
                "location",
            ],
            "parcel_id": ["parcel_id", "apn", "parcel_number", "tax_id", "pin"],
            "amount": ["amount", "consideration", "value", "sale_price", "loan_amount"],
            "legal_description": ["legal_description", "legal_desc", "legal"],
            "owner_name": ["owner_name", "owner", "property_owner"],
            "debtor": ["debtor", "debtor_name"],
            "creditor": ["creditor", "creditor_name", "lienholder"],
        }

        for standard_field, possible_names in field_mappings.items():
            for name in possible_names:
                if name in api_data and api_data[name]:
                    standard[standard_field] = api_data[name]
                    break

        # Parse amount to float if present
        if "amount" in standard:
            try:
                amount_str = str(standard["amount"]).replace("$", "").replace(",", "")
                standard["amount"] = float(amount_str)
            except (ValueError, TypeError):
                pass

        # Parse date if present
        if "record_date" in standard:
            try:
                if isinstance(standard["record_date"], str):
                    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%d-%m-%Y"]:
                        try:
                            dt = datetime.strptime(standard["record_date"], fmt)
                            standard["record_date"] = dt.date().isoformat()
                            break
                        except ValueError:
                            continue
            except Exception:
                pass

        return standard

    def get_supported_record_types(self) -> List[str]:
        """Get list of supported record types."""
        return ["property", "deed", "lien", "mortgage", "tax"]

    def get_state_info(self) -> Dict[str, Any]:
        """Get information about this state integration."""
        return {
            "state_code": self.state_code,
            "state_name": self.state_name,
            "counties_supported": len(self.counties),
            "counties": self.list_counties(),
            "record_types": self.get_supported_record_types(),
            "auth_type": self.auth_type,
            "api_class": "GenericStateAPI",
            "metrics": self.get_metrics(),
        }


def load_state_config(state_code: str, configs_dir: str = None) -> Dict[str, Any]:
    """
    Load configuration for a state from JSON file.

    Args:
        state_code: Two-letter state code
        configs_dir: Optional path to configs directory

    Returns:
        State configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    if configs_dir:
        config_path = Path(configs_dir) / f"{state_code.lower()}.json"
    else:
        config_path = Path(__file__).parent / "configs" / f"{state_code.lower()}.json"

    if not config_path.exists():
        raise FileNotFoundError(f"No configuration found for state: {state_code}")

    with open(config_path, "r") as f:
        return json.load(f)


def get_state_api(
    state_code: str, jurisdiction_id: int = 1, config: Dict[str, Any] = None
) -> GenericStateAPI:
    """
    Get a GenericStateAPI instance for a state.

    Args:
        state_code: Two-letter state code
        jurisdiction_id: Database jurisdiction ID
        config: Optional configuration override

    Returns:
        Configured GenericStateAPI instance
    """
    if config is None:
        config = load_state_config(state_code)

    return GenericStateAPI(jurisdiction_id, config)


def list_configured_states(configs_dir: str = None) -> List[str]:
    """
    List all states with configuration files.

    Args:
        configs_dir: Optional path to configs directory

    Returns:
        List of state codes with configurations
    """
    if configs_dir:
        config_path = Path(configs_dir)
    else:
        config_path = Path(__file__).parent / "configs"

    states = []
    for f in config_path.glob("*.json"):
        states.append(f.stem.upper())

    return sorted(states)
