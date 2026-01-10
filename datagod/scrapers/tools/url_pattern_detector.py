"""
URL Pattern Detector for Data Sources

Analyzes existing working data sources to detect URL patterns
that can be applied to other jurisdictions.
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class URLPattern:
    """A detected URL pattern."""
    pattern: str
    category: str
    placeholders: List[str]
    example_urls: List[str]
    confidence: float  # 0.0 to 1.0
    state_codes: Set[str]
    match_count: int


class URLPatternDetector:
    """
    Detects URL patterns from existing data sources.

    Analyzes working URLs to identify patterns that can
    be applied to generate URLs for new jurisdictions.
    """

    # Common URL components to look for
    JURISDICTION_INDICATORS = [
        r'county',
        r'parish',
        r'borough',
        r'municipality',
        r'city',
        r'district',
    ]

    # Data category keywords
    CATEGORY_KEYWORDS = {
        'property': ['assessor', 'property', 'parcel', 'land', 'real-estate', 'realestate', 'tax'],
        'court': ['court', 'judicial', 'case', 'docket', 'filing', 'clerk'],
        'business': ['sos', 'secretary', 'corporation', 'llc', 'business', 'entity', 'ucc'],
        'recorder': ['recorder', 'deed', 'document', 'vital', 'marriage', 'birth', 'death'],
        'sheriff': ['sheriff', 'police', 'jail', 'inmate', 'arrest', 'warrant'],
        'permits': ['permit', 'building', 'zoning', 'planning', 'code', 'inspection'],
        'license': ['license', 'professional', 'certification', 'board'],
        'voter': ['voter', 'election', 'ballot', 'campaign', 'registration'],
    }

    def __init__(self, configs_dir: Optional[str] = None):
        """
        Initialize the pattern detector.

        Args:
            configs_dir: Path to scraper configs directory
        """
        if configs_dir is None:
            configs_dir = Path(__file__).parent.parent / "configs"
        self.configs_dir = Path(configs_dir)
        self.patterns: Dict[str, List[URLPattern]] = defaultdict(list)

    def _extract_placeholders(self, url: str, county_name: str, state_code: str) -> Tuple[str, List[str]]:
        """
        Extract placeholders from a URL.

        Args:
            url: The URL to analyze
            county_name: Known county name
            state_code: Known state code

        Returns:
            Tuple of (pattern_string, list_of_placeholders)
        """
        placeholders = []
        pattern = url

        # Create variations of county name
        county_variations = [
            county_name.lower(),
            county_name.lower().replace(' ', ''),
            county_name.lower().replace(' ', '-'),
            county_name.lower().replace(' ', '_'),
            re.sub(r'\s+county$', '', county_name.lower(), flags=re.IGNORECASE),
            re.sub(r'\s+county$', '', county_name.lower(), flags=re.IGNORECASE).replace(' ', '-'),
        ]

        # Replace county name variations
        for variation in county_variations:
            if variation and variation in pattern.lower():
                pattern = re.sub(re.escape(variation), '{county}', pattern, flags=re.IGNORECASE)
                if '{county}' not in placeholders:
                    placeholders.append('{county}')
                break

        # Replace state code
        state_lower = state_code.lower()
        if state_lower in pattern.lower():
            pattern = re.sub(rf'\b{state_lower}\b', '{state}', pattern, flags=re.IGNORECASE)
            if '{state}' not in placeholders:
                placeholders.append('{state}')

        return pattern, placeholders

    def _detect_category(self, url: str) -> str:
        """
        Detect the data category from a URL.

        Args:
            url: URL to analyze

        Returns:
            Category name or 'unknown'
        """
        url_lower = url.lower()

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in url_lower:
                    return category

        return 'unknown'

    def analyze_config(self, config_path: Path) -> List[URLPattern]:
        """
        Analyze a single config file for patterns.

        Args:
            config_path: Path to config JSON file

        Returns:
            List of detected patterns
        """
        patterns = []

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error reading config {config_path}: {e}")
            return patterns

        state_code = config.get('state_code', config_path.stem.upper())
        counties = config.get('counties', [])

        for county in counties:
            county_name = county.get('name', '')
            base_urls = county.get('base_urls', {})

            for category, url in base_urls.items():
                if not url:
                    continue

                # Extract pattern
                pattern_str, placeholders = self._extract_placeholders(
                    url, county_name, state_code
                )

                # Only keep patterns with placeholders
                if not placeholders:
                    continue

                # Detect category if not provided
                detected_category = self._detect_category(url)
                if detected_category != 'unknown':
                    category = detected_category

                # Check if pattern already exists
                existing = None
                for p in patterns:
                    if p.pattern == pattern_str and p.category == category:
                        existing = p
                        break

                if existing:
                    existing.example_urls.append(url)
                    existing.state_codes.add(state_code)
                    existing.match_count += 1
                else:
                    patterns.append(URLPattern(
                        pattern=pattern_str,
                        category=category,
                        placeholders=placeholders,
                        example_urls=[url],
                        confidence=0.0,
                        state_codes={state_code},
                        match_count=1,
                    ))

        return patterns

    def analyze_all_configs(self) -> Dict[str, List[URLPattern]]:
        """
        Analyze all config files for patterns.

        Returns:
            Dictionary mapping categories to patterns
        """
        all_patterns: Dict[str, List[URLPattern]] = defaultdict(list)

        config_files = list(self.configs_dir.glob("*.json"))
        logger.info(f"Analyzing {len(config_files)} config files...")

        for config_path in config_files:
            patterns = self.analyze_config(config_path)

            for pattern in patterns:
                # Merge with existing patterns
                existing = None
                for p in all_patterns[pattern.category]:
                    if p.pattern == pattern.pattern:
                        existing = p
                        break

                if existing:
                    existing.example_urls.extend(pattern.example_urls)
                    existing.state_codes.update(pattern.state_codes)
                    existing.match_count += pattern.match_count
                else:
                    all_patterns[pattern.category].append(pattern)

        # Calculate confidence scores
        for category, patterns in all_patterns.items():
            total_matches = sum(p.match_count for p in patterns)
            for pattern in patterns:
                pattern.confidence = pattern.match_count / total_matches if total_matches > 0 else 0

        self.patterns = all_patterns
        return all_patterns

    def get_best_patterns(self, category: str, limit: int = 5) -> List[URLPattern]:
        """
        Get the best patterns for a category.

        Args:
            category: Data category
            limit: Maximum patterns to return

        Returns:
            List of patterns sorted by confidence
        """
        patterns = self.patterns.get(category, [])
        sorted_patterns = sorted(patterns, key=lambda p: p.confidence, reverse=True)
        return sorted_patterns[:limit]

    def generate_urls(
        self,
        category: str,
        county_name: str,
        state_code: str,
        limit: int = 3
    ) -> List[str]:
        """
        Generate possible URLs for a new jurisdiction.

        Args:
            category: Data category
            county_name: County name
            state_code: Two-letter state code
            limit: Maximum URLs to generate

        Returns:
            List of possible URLs
        """
        patterns = self.get_best_patterns(category, limit=limit)
        urls = []

        # Create county slug
        county_slug = re.sub(r'\s+county$', '', county_name, flags=re.IGNORECASE)
        county_slug = re.sub(r'[^a-z0-9]+', '-', county_slug.lower()).strip('-')

        for pattern in patterns:
            url = pattern.pattern
            url = url.replace('{county}', county_slug)
            url = url.replace('{state}', state_code.lower())
            urls.append(url)

        return urls

    def get_pattern_summary(self) -> Dict[str, Any]:
        """
        Get summary of detected patterns.

        Returns:
            Summary dictionary
        """
        summary = {
            "total_patterns": 0,
            "categories": {},
        }

        for category, patterns in self.patterns.items():
            summary["total_patterns"] += len(patterns)
            summary["categories"][category] = {
                "pattern_count": len(patterns),
                "total_examples": sum(len(p.example_urls) for p in patterns),
                "states_covered": len(set().union(*(p.state_codes for p in patterns))),
                "top_patterns": [
                    {
                        "pattern": p.pattern,
                        "confidence": round(p.confidence, 2),
                        "match_count": p.match_count,
                    }
                    for p in sorted(patterns, key=lambda x: x.confidence, reverse=True)[:3]
                ],
            }

        return summary

    def save_patterns(self, output_path: Optional[str] = None) -> str:
        """
        Save detected patterns to JSON file.

        Args:
            output_path: Optional output path

        Returns:
            Path to saved file
        """
        if output_path is None:
            output_path = self.configs_dir.parent / "detected_patterns.json"

        output = {}
        for category, patterns in self.patterns.items():
            output[category] = [
                {
                    "pattern": p.pattern,
                    "placeholders": p.placeholders,
                    "confidence": round(p.confidence, 3),
                    "match_count": p.match_count,
                    "states": list(p.state_codes),
                    "example_urls": p.example_urls[:5],  # Limit examples
                }
                for p in sorted(patterns, key=lambda x: x.confidence, reverse=True)
            ]

        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        logger.info(f"Saved patterns to: {output_path}")
        return str(output_path)


def main():
    """CLI entry point for pattern detector."""
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Detect URL patterns from configs")
    parser.add_argument("--analyze", action="store_true", help="Analyze all configs")
    parser.add_argument("--category", type=str, help="Show patterns for category")
    parser.add_argument("--generate", type=str, help="Generate URLs for county (format: COUNTY,STATE)")
    parser.add_argument("--save", action="store_true", help="Save patterns to file")

    args = parser.parse_args()

    detector = URLPatternDetector()

    if args.analyze or args.save or args.category or args.generate:
        patterns = detector.analyze_all_configs()
        summary = detector.get_pattern_summary()

        print("\n=== URL Pattern Detection Summary ===")
        print(f"Total patterns detected: {summary['total_patterns']}")

        for category, info in summary['categories'].items():
            print(f"\n{category}:")
            print(f"  Patterns: {info['pattern_count']}")
            print(f"  Examples: {info['total_examples']}")
            print(f"  States: {info['states_covered']}")

        if args.category:
            print(f"\n=== Patterns for {args.category} ===")
            patterns = detector.get_best_patterns(args.category)
            for p in patterns:
                print(f"\n  Pattern: {p.pattern}")
                print(f"  Confidence: {p.confidence:.1%}")
                print(f"  Matches: {p.match_count}")

        if args.generate:
            parts = args.generate.split(',')
            if len(parts) == 2:
                county, state = parts
                for category in ['property', 'court', 'business', 'recorder']:
                    urls = detector.generate_urls(category, county.strip(), state.strip())
                    print(f"\n{category}: {urls}")

        if args.save:
            path = detector.save_patterns()
            print(f"\nPatterns saved to: {path}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
