"""
Scraper Generator System
Generates state-specific scrapers from templates and configuration files
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ScraperGeneratorError(Exception):
    """Raised when scraper generation fails"""

    pass


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""

    pass


class ScraperGenerator:
    """
    Generates state-specific API scrapers from templates and configuration.

    This enables rapid development of new state scrapers by:
    1. Loading a base template
    2. Applying state-specific configuration
    3. Generating validated Python code
    """

    # Required fields in state configuration
    REQUIRED_CONFIG_FIELDS = ["state_code", "state_name", "counties"]

    # Optional configuration fields with defaults
    DEFAULT_CONFIG = {
        "requests_per_minute": 60,
        "requests_per_hour": 1000,
        "timeout": 30,
        "retry_attempts": 3,
        "retry_backoff": 1.0,
        "auth_type": "api_key",  # api_key, oauth2, hmac, none
        "data_sources": {},
    }

    def __init__(
        self, templates_dir: str = None, configs_dir: str = None, output_dir: str = None
    ):
        """
        Initialize the ScraperGenerator.

        Args:
            templates_dir: Directory containing scraper templates
            configs_dir: Directory containing state configuration files
            output_dir: Directory for generated scrapers
        """
        base_dir = Path(__file__).parent

        self.templates_dir = (
            Path(templates_dir) if templates_dir else base_dir / "templates"
        )
        self.configs_dir = Path(configs_dir) if configs_dir else base_dir / "configs"
        self.output_dir = Path(output_dir) if output_dir else base_dir

        # Ensure directories exist
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.configs_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"ScraperGenerator initialized: templates={self.templates_dir}, configs={self.configs_dir}"
        )

    def load_config(self, state_code: str) -> Dict[str, Any]:
        """
        Load configuration for a state.

        Args:
            state_code: Two-letter state code (e.g., 'CA', 'TX')

        Returns:
            State configuration dictionary

        Raises:
            ConfigValidationError: If config file doesn't exist or is invalid
        """
        config_file = self.configs_dir / f"{state_code.lower()}.json"

        if not config_file.exists():
            raise ConfigValidationError(f"Configuration file not found: {config_file}")

        try:
            with open(config_file, "r") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Invalid JSON in config file: {e}")

        # Apply defaults
        for key, default_value in self.DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = default_value

        # Validate required fields
        self._validate_config(config)

        return config

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate a state configuration.

        Args:
            config: Configuration dictionary to validate

        Raises:
            ConfigValidationError: If validation fails
        """
        errors = []

        # Check required fields
        for field in self.REQUIRED_CONFIG_FIELDS:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # Validate state code format
        if "state_code" in config:
            state_code = config["state_code"]
            if not isinstance(state_code, str) or len(state_code) != 2:
                errors.append("state_code must be a 2-letter string")

        # Validate counties
        if "counties" in config:
            counties = config["counties"]
            if not isinstance(counties, list):
                errors.append("counties must be a list")
            elif len(counties) == 0:
                errors.append("counties list cannot be empty")
            else:
                for i, county in enumerate(counties):
                    if not isinstance(county, dict):
                        errors.append(f"County {i} must be a dictionary")
                    elif "name" not in county:
                        errors.append(f"County {i} missing 'name' field")

        # Validate auth_type
        valid_auth_types = ["api_key", "oauth2", "hmac", "none"]
        if config.get("auth_type") not in valid_auth_types:
            errors.append(f"auth_type must be one of: {valid_auth_types}")

        if errors:
            raise ConfigValidationError(
                f"Configuration validation failed: {'; '.join(errors)}"
            )

    def load_template(self, template_name: str = "state_api_template") -> str:
        """
        Load a scraper template.

        Args:
            template_name: Name of the template file (without .py extension)

        Returns:
            Template content as string

        Raises:
            ScraperGeneratorError: If template doesn't exist
        """
        template_file = self.templates_dir / f"{template_name}.py"

        if not template_file.exists():
            raise ScraperGeneratorError(f"Template file not found: {template_file}")

        with open(template_file, "r") as f:
            return f.read()

    def generate_scraper(self, config: Dict[str, Any], template: str = None) -> str:
        """
        Generate a scraper from configuration.

        Args:
            config: State configuration dictionary
            template: Optional custom template string

        Returns:
            Generated Python code as string
        """
        if template is None:
            template = self.load_template()

        # Prepare template variables
        state_code = config["state_code"]
        state_name = config["state_name"]
        class_name = f"{state_name.replace(' ', '')}API"

        # Generate county APIs dictionary
        county_apis = self._generate_county_apis(config["counties"])

        # Generate data source handlers
        data_source_methods = self._generate_data_source_methods(
            config.get("data_sources", {})
        )

        # Determine auth mixin
        auth_mixin = self._get_auth_mixin(config.get("auth_type", "api_key"))

        # Build the generated code
        generated_code = self._apply_template(
            template=template,
            state_code=state_code,
            state_name=state_name,
            class_name=class_name,
            county_apis=county_apis,
            data_source_methods=data_source_methods,
            auth_mixin=auth_mixin,
            config=config,
        )

        return generated_code

    def _generate_county_apis(self, counties: List[Dict[str, Any]]) -> str:
        """Generate the COUNTY_APIS dictionary code."""
        lines = ["COUNTY_APIS = {"]

        for county in counties:
            name = county["name"]
            county_key = name.lower().replace(" ", "_").replace("'", "")

            county_config = {
                "name": name,
                "base_url": county.get("base_url", ""),
                "property_endpoint": county.get(
                    "property_endpoint", "/property/search"
                ),
                "deed_endpoint": county.get("deed_endpoint", "/deed/search"),
                "lien_endpoint": county.get("lien_endpoint", "/lien/search"),
                "requires_auth": county.get("requires_auth", True),
                "rate_limit": county.get("rate_limit", 60),
            }

            lines.append(f"    '{county_key}': {{")
            for key, value in county_config.items():
                if isinstance(value, str):
                    lines.append(f"        '{key}': '{value}',")
                else:
                    lines.append(f"        '{key}': {value},")
            lines.append("    },")

        lines.append("}")
        return "\n".join(lines)

    def _generate_data_source_methods(self, data_sources: Dict[str, Any]) -> str:
        """Generate methods for handling different data sources."""
        methods = []

        for source_type, source_config in data_sources.items():
            method_name = f"search_{source_type}"
            source_url = source_config.get("url", "")

            method_code = f'''
    def {method_name}(self, query: Dict[str, Any], county: str = None) -> List[Dict[str, Any]]:
        """Search {source_type} records."""
        endpoint = "{source_url}"
        if county:
            county_config = self.COUNTY_APIS.get(county.lower().replace(' ', '_'))
            if county_config:
                endpoint = county_config.get('{source_type}_endpoint', endpoint)

        response = self.make_request('GET', endpoint, params=query)
        data = self.validate_response(response)

        results = []
        for record in data.get('results', []):
            mapped = self.map_api_data_to_standard_format(record)
            mapped['record_type'] = '{source_type}'
            results.append(mapped)

        return results
'''
            methods.append(method_code)

        return "\n".join(methods)

    def _get_auth_mixin(self, auth_type: str) -> str:
        """Get the appropriate authentication mixin class."""
        mixins = {
            "api_key": "APIKeyAuthentication",
            "oauth2": "OAuth2Authentication",
            "hmac": "HMACAuthentication",
            "none": "",
        }
        return mixins.get(auth_type, "APIKeyAuthentication")

    def _apply_template(
        self,
        template: str,
        state_code: str,
        state_name: str,
        class_name: str,
        county_apis: str,
        data_source_methods: str,
        auth_mixin: str,
        config: Dict[str, Any],
    ) -> str:
        """Apply configuration values to template."""

        # Create inheritance string
        if auth_mixin:
            inheritance = f"{auth_mixin}, BaseAPIIntegration"
        else:
            inheritance = "BaseAPIIntegration"

        # Perform substitutions
        substitutions = {
            "STATE_CODE": state_code,
            "STATE_CODE_LOWER": state_code.lower(),
            "STATE_NAME": state_name,
            "CLASS_NAME": class_name,
            "COUNTY_APIS": county_apis,
            "INHERITANCE": inheritance,
            "AUTH_MIXIN": auth_mixin,
            "DATA_SOURCE_METHODS": data_source_methods,
            "REQUESTS_PER_MINUTE": str(config.get("requests_per_minute", 60)),
            "REQUESTS_PER_HOUR": str(config.get("requests_per_hour", 1000)),
            "TIMEOUT": str(config.get("timeout", 30)),
            "GENERATED_DATE": datetime.now().isoformat(),
        }

        result = template
        for key, value in substitutions.items():
            result = result.replace(f"${{{key}}}", value)
            result = result.replace(f"${key}", value)

        return result

    def validate_generated_code(self, code: str) -> bool:
        """
        Validate that generated code is syntactically correct.

        Args:
            code: Generated Python code

        Returns:
            True if code is valid

        Raises:
            ScraperGeneratorError: If code has syntax errors
        """
        try:
            compile(code, "<generated>", "exec")
            return True
        except SyntaxError as e:
            raise ScraperGeneratorError(f"Generated code has syntax errors: {e}")

    def save_scraper(self, code: str, state_code: str) -> Path:
        """
        Save generated scraper to file.

        Args:
            code: Generated Python code
            state_code: Two-letter state code

        Returns:
            Path to saved file
        """
        filename = f"{state_code.lower()}_api.py"
        output_path = self.output_dir / filename

        with open(output_path, "w") as f:
            f.write(code)

        logger.info(f"Saved generated scraper to {output_path}")
        return output_path

    def generate_and_save(self, state_code: str) -> Path:
        """
        Generate and save a scraper for a state.

        This is the main entry point for generating scrapers.

        Args:
            state_code: Two-letter state code

        Returns:
            Path to saved scraper file
        """
        logger.info(f"Generating scraper for state: {state_code}")

        # Load configuration
        config = self.load_config(state_code)

        # Load template
        template = self.load_template()

        # Generate code
        code = self.generate_scraper(config, template)

        # Validate
        self.validate_generated_code(code)

        # Save
        output_path = self.save_scraper(code, state_code)

        logger.info(f"Successfully generated scraper for {state_code}")
        return output_path

    def list_available_configs(self) -> List[str]:
        """List all available state configurations."""
        configs = []
        for f in self.configs_dir.glob("*.json"):
            configs.append(f.stem.upper())
        return sorted(configs)

    def list_generated_scrapers(self) -> List[str]:
        """List all generated state scrapers."""
        scrapers = []
        for f in self.output_dir.glob("*_api.py"):
            # Extract state code from filename
            state_code = f.stem.replace("_api", "").upper()
            scrapers.append(state_code)
        return sorted(scrapers)

    def get_coverage_report(self) -> Dict[str, Any]:
        """
        Get a coverage report showing which states have scrapers.

        Returns:
            Dictionary with coverage statistics
        """
        # All US states + DC
        all_states = [
            "AL",
            "AK",
            "AZ",
            "AR",
            "CA",
            "CO",
            "CT",
            "DE",
            "DC",
            "FL",
            "GA",
            "HI",
            "ID",
            "IL",
            "IN",
            "IA",
            "KS",
            "KY",
            "LA",
            "ME",
            "MD",
            "MA",
            "MI",
            "MN",
            "MS",
            "MO",
            "MT",
            "NE",
            "NV",
            "NH",
            "NJ",
            "NM",
            "NY",
            "NC",
            "ND",
            "OH",
            "OK",
            "OR",
            "PA",
            "RI",
            "SC",
            "SD",
            "TN",
            "TX",
            "UT",
            "VT",
            "VA",
            "WA",
            "WV",
            "WI",
            "WY",
        ]

        # Territories
        territories = ["PR", "GU", "VI", "AS", "MP"]

        generated = set(self.list_generated_scrapers())
        configs = set(self.list_available_configs())

        covered_states = generated.intersection(set(all_states))
        covered_territories = generated.intersection(set(territories))

        return {
            "total_states": len(all_states),
            "total_territories": len(territories),
            "covered_states": len(covered_states),
            "covered_territories": len(covered_territories),
            "coverage_percentage": (len(covered_states) / len(all_states)) * 100,
            "states_with_scrapers": sorted(covered_states),
            "states_missing": sorted(set(all_states) - generated),
            "territories_with_scrapers": sorted(covered_territories),
            "territories_missing": sorted(set(territories) - generated),
            "configs_available": sorted(configs),
            "configs_without_scrapers": sorted(configs - generated),
        }


# Factory function for CLI usage
def create_generator() -> ScraperGenerator:
    """Create a ScraperGenerator with default paths."""
    return ScraperGenerator()


if __name__ == "__main__":
    # Example usage
    import sys

    generator = create_generator()

    if len(sys.argv) > 1:
        state_code = sys.argv[1].upper()
        try:
            output_path = generator.generate_and_save(state_code)
            print(f"Generated scraper: {output_path}")
        except (ConfigValidationError, ScraperGeneratorError) as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        # Show coverage report
        report = generator.get_coverage_report()
        print(f"\nState Coverage Report")
        print(f"=====================")
        print(
            f"States with scrapers: {report['covered_states']}/{report['total_states']} ({report['coverage_percentage']:.1f}%)"
        )
        print(
            f"Territories with scrapers: {report['covered_territories']}/{report['total_territories']}"
        )
        print(
            f"\nMissing states: {', '.join(report['states_missing'][:10])}{'...' if len(report['states_missing']) > 10 else ''}"
        )
