"""
Config Generator for County Scrapers

Automatically generates scraper configuration files for all US counties
based on detected URL patterns and known data source templates.
"""

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CountyConfig:
    """Configuration for a single county's data sources."""

    fips_code: str
    name: str
    state_code: str
    county_seat: str
    population: int
    base_urls: Dict[str, str]
    endpoints: Dict[str, Dict[str, Any]]
    auth_type: str = "none"
    rate_limit: int = 100
    rate_limit_period: str = "minute"
    priority: int = 3
    notes: str = ""


@dataclass
class StateConfig:
    """Configuration for a state's scraper."""

    state_code: str
    state_name: str
    state_fips: str
    counties: List[CountyConfig]
    state_level_sources: Dict[str, Any]
    auth_config: Dict[str, Any]
    rate_limits: Dict[str, int]
    created_at: str
    updated_at: str


class ConfigGenerator:
    """
    Generates scraper configurations for US counties.

    Uses templates and URL pattern detection to create
    configuration files for data collection.
    """

    # Common URL patterns for county data sources
    URL_PATTERNS = {
        "property_assessor": [
            "https://{county_slug}.{state}.gov/assessor",
            "https://assessor.{county_slug}county.{state}.gov",
            "https://www.{county_slug}county.org/assessor",
            "https://{county_slug}county{state}.gov/property",
        ],
        "court_records": [
            "https://{state}courts.gov/{county_slug}",
            "https://www.courts.{state}.gov/county/{county_slug}",
            "https://{county_slug}.{state}courts.gov",
            "https://courtrecords.{county_slug}county.{state}.gov",
        ],
        "clerk_recorder": [
            "https://clerk.{county_slug}county.{state}.gov",
            "https://{county_slug}countyclerk.{state}.gov",
            "https://recorder.{county_slug}county.org",
        ],
        "sheriff": [
            "https://sheriff.{county_slug}county.{state}.gov",
            "https://{county_slug}sheriff.org",
        ],
        "building_permits": [
            "https://permits.{county_slug}county.{state}.gov",
            "https://building.{county_slug}county.org",
        ],
    }

    # State-level data source templates
    STATE_SOURCES = {
        "secretary_of_state": {
            "description": "Business filings, corporations, LLCs",
            "url_pattern": "https://sos.{state}.gov/business",
        },
        "professional_licensing": {
            "description": "Professional license verification",
            "url_pattern": "https://license.{state}.gov",
        },
        "ucc_filings": {
            "description": "UCC filings and searches",
            "url_pattern": "https://sos.{state}.gov/ucc",
        },
        "court_records": {
            "description": "Statewide court case search",
            "url_pattern": "https://courts.{state}.gov/search",
        },
    }

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the config generator.

        Args:
            data_dir: Path to the FIPS data directory
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data" / "fips"
        self.data_dir = Path(data_dir)
        self.configs_dir = Path(__file__).parent.parent / "configs"

        # Load FIPS data
        self.states = self._load_states()
        self.counties = self._load_counties()
        self.population_data = self._load_population_data()

    def _load_states(self) -> Dict[str, Any]:
        """Load state data from FIPS file."""
        states_file = self.data_dir / "us_states.json"
        if states_file.exists():
            with open(states_file, "r") as f:
                data = json.load(f)
                return {s["code"]: s for s in data.get("states", [])}
        return {}

    def _load_counties(self) -> Dict[str, List[Dict]]:
        """Load county data from FIPS file."""
        counties_file = self.data_dir / "us_counties_complete.json"
        if counties_file.exists():
            with open(counties_file, "r") as f:
                data = json.load(f)
                return data.get("counties", {})
        return {}

    def _load_population_data(self) -> Dict[str, Any]:
        """Load population and tier data."""
        pop_file = self.data_dir / "population_data.json"
        if pop_file.exists():
            with open(pop_file, "r") as f:
                return json.load(f)
        return {}

    def _slugify(self, name: str) -> str:
        """Convert county name to URL-safe slug."""
        # Remove "County" suffix
        name = re.sub(r"\s+County$", "", name, flags=re.IGNORECASE)
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
        # Remove leading/trailing hyphens
        return slug.strip("-")

    def _get_tier(self, state_code: str) -> int:
        """Get priority tier for a state."""
        tiers = self.population_data.get("tier_definitions", {})
        for tier_num, tier_data in [
            (1, tiers.get("tier_1", {})),
            (2, tiers.get("tier_2", {})),
            (3, tiers.get("tier_3", {})),
            (4, tiers.get("territories", {})),
        ]:
            if state_code in tier_data.get("states", []):
                return tier_num
        return 3

    def generate_county_config(
        self, state_code: str, county_data: Dict[str, Any]
    ) -> CountyConfig:
        """
        Generate configuration for a single county.

        Args:
            state_code: Two-letter state code
            county_data: County data from FIPS database

        Returns:
            CountyConfig object
        """
        county_slug = self._slugify(county_data["name"])
        state_lower = state_code.lower()

        # Generate base URLs for each data category
        base_urls = {}
        endpoints = {}

        for category, patterns in self.URL_PATTERNS.items():
            for pattern in patterns:
                url = pattern.format(county_slug=county_slug, state=state_lower)
                base_urls[category] = url
                endpoints[category] = {
                    "search": f"{url}/search",
                    "details": f"{url}/record/{{id}}",
                    "list": f"{url}/records",
                }
                break  # Use first pattern as default

        return CountyConfig(
            fips_code=county_data["fips"],
            name=county_data["name"],
            state_code=state_code,
            county_seat=county_data.get("seat", ""),
            population=county_data.get("population", 0),
            base_urls=base_urls,
            endpoints=endpoints,
            auth_type="none",
            rate_limit=100,
            rate_limit_period="minute",
            priority=self._get_tier(state_code),
        )

    def generate_state_config(self, state_code: str) -> StateConfig:
        """
        Generate complete configuration for a state.

        Args:
            state_code: Two-letter state code

        Returns:
            StateConfig object
        """
        state_info = self.states.get(state_code, {})
        counties_data = self.counties.get(state_code, [])
        state_lower = state_code.lower()

        # Generate county configs
        county_configs = []
        for county in counties_data:
            county_config = self.generate_county_config(state_code, county)
            county_configs.append(county_config)

        # Generate state-level sources
        state_sources = {}
        for source_name, source_template in self.STATE_SOURCES.items():
            state_sources[source_name] = {
                "description": source_template["description"],
                "url": source_template["url_pattern"].format(state=state_lower),
                "status": "unknown",
            }

        now = datetime.utcnow().isoformat()

        return StateConfig(
            state_code=state_code,
            state_name=state_info.get("name", state_code),
            state_fips=state_info.get("fips", ""),
            counties=county_configs,
            state_level_sources=state_sources,
            auth_config={
                "type": "none",
                "api_key": None,
                "oauth": None,
            },
            rate_limits={
                "requests_per_minute": 60,
                "requests_per_hour": 1000,
                "concurrent_requests": 5,
            },
            created_at=now,
            updated_at=now,
        )

    def save_state_config(self, state_code: str, overwrite: bool = False) -> str:
        """
        Generate and save configuration file for a state.

        Args:
            state_code: Two-letter state code
            overwrite: Whether to overwrite existing config

        Returns:
            Path to saved config file
        """
        config_path = self.configs_dir / f"{state_code.lower()}.json"

        if config_path.exists() and not overwrite:
            print(f"Config already exists: {config_path}")
            return str(config_path)

        # Generate config
        state_config = self.generate_state_config(state_code)

        # Convert to dict for JSON serialization
        config_dict = {
            "state_code": state_config.state_code,
            "state_name": state_config.state_name,
            "state_fips": state_config.state_fips,
            "auth_config": state_config.auth_config,
            "rate_limits": state_config.rate_limits,
            "state_level_sources": state_config.state_level_sources,
            "counties": [asdict(c) for c in state_config.counties],
            "created_at": state_config.created_at,
            "updated_at": state_config.updated_at,
        }

        # Ensure directory exists
        self.configs_dir.mkdir(parents=True, exist_ok=True)

        # Save config
        with open(config_path, "w") as f:
            json.dump(config_dict, f, indent=2)

        print(f"Saved config: {config_path}")
        return str(config_path)

    def generate_all_configs(
        self, tier: Optional[int] = None, overwrite: bool = False
    ) -> List[str]:
        """
        Generate configuration files for all states (or specific tier).

        Args:
            tier: Optional tier to limit generation (1, 2, 3, or 4)
            overwrite: Whether to overwrite existing configs

        Returns:
            List of paths to generated config files
        """
        tiers = self.population_data.get("tier_definitions", {})

        if tier == 1:
            states = tiers.get("tier_1", {}).get("states", [])
        elif tier == 2:
            states = tiers.get("tier_2", {}).get("states", [])
        elif tier == 3:
            states = tiers.get("tier_3", {}).get("states", [])
        elif tier == 4:
            states = tiers.get("territories", {}).get("states", [])
        else:
            # All states
            states = list(self.states.keys())

        generated = []
        for state_code in states:
            try:
                path = self.save_state_config(state_code, overwrite=overwrite)
                generated.append(path)
            except Exception as e:
                print(f"Error generating config for {state_code}: {e}")

        return generated

    def get_coverage_summary(self) -> Dict[str, Any]:
        """
        Get summary of current configuration coverage.

        Returns:
            Dictionary with coverage statistics
        """
        existing_configs = list(self.configs_dir.glob("*.json"))
        configured_states = {p.stem.upper() for p in existing_configs}

        all_states = set(self.states.keys())
        missing_states = all_states - configured_states

        # Count counties
        total_counties = sum(len(c) for c in self.counties.values())
        configured_counties = 0

        for config_path in existing_configs:
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    configured_counties += len(config.get("counties", []))
            except Exception:
                pass

        return {
            "total_states": len(all_states),
            "configured_states": len(configured_states),
            "missing_states": list(missing_states),
            "state_coverage_pct": round(
                len(configured_states) / len(all_states) * 100, 1
            ),
            "total_counties": total_counties,
            "configured_counties": configured_counties,
            "county_coverage_pct": (
                round(configured_counties / total_counties * 100, 1)
                if total_counties > 0
                else 0
            ),
        }


def main():
    """CLI entry point for config generator."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate scraper configurations")
    parser.add_argument("--state", type=str, help="Generate config for specific state")
    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3, 4],
        help="Generate configs for specific tier",
    )
    parser.add_argument(
        "--all", action="store_true", help="Generate configs for all states"
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing configs"
    )
    parser.add_argument("--summary", action="store_true", help="Show coverage summary")

    args = parser.parse_args()

    generator = ConfigGenerator()

    if args.summary:
        summary = generator.get_coverage_summary()
        print("\n=== Configuration Coverage Summary ===")
        print(
            f"States: {summary['configured_states']}/{summary['total_states']} ({summary['state_coverage_pct']}%)"
        )
        print(
            f"Counties: {summary['configured_counties']}/{summary['total_counties']} ({summary['county_coverage_pct']}%)"
        )
        if summary["missing_states"]:
            print(f"Missing states: {', '.join(sorted(summary['missing_states']))}")
        return

    if args.state:
        generator.save_state_config(args.state.upper(), overwrite=args.overwrite)
    elif args.tier:
        generated = generator.generate_all_configs(
            tier=args.tier, overwrite=args.overwrite
        )
        print(f"\nGenerated {len(generated)} config files for Tier {args.tier}")
    elif args.all:
        generated = generator.generate_all_configs(overwrite=args.overwrite)
        print(f"\nGenerated {len(generated)} config files")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
