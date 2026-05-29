"""
Entity Linking Service
Links and correlates entities across different data sources

This service provides:
- Fuzzy name matching using Levenshtein and Jaro-Winkler algorithms
- Address normalization and matching
- Cross-reference validation between data sources
- Confidence scoring for entity matches
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Types of entities that can be linked"""

    PERSON = "person"
    COMPANY = "company"
    PROPERTY = "property"
    UNKNOWN = "unknown"


@dataclass
class Entity:
    """Represents an entity that can be linked across data sources"""

    entity_id: str
    entity_type: EntityType
    primary_name: str
    aliases: List[str] = field(default_factory=list)
    identifiers: Dict[str, str] = field(default_factory=dict)
    addresses: List[Dict[str, Any]] = field(default_factory=list)
    source_records: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary"""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "primary_name": self.primary_name,
            "aliases": self.aliases,
            "identifiers": self.identifiers,
            "addresses": self.addresses,
            "source_records": self.source_records,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class EntityMatch:
    """Represents a potential match between entities"""

    entity1_id: str
    entity2_id: str
    confidence: float
    match_factors: Dict[str, float]
    recommended_action: str  # 'merge', 'review', 'no_match'


class EntityLinker:
    """
    Links entities across different data sources using fuzzy matching.

    Features:
    - Name matching with multiple algorithms
    - Address normalization and comparison
    - Identifier-based matching (SSN, EIN, parcel ID)
    - Configurable confidence thresholds
    """

    # Default thresholds
    DEFAULT_MERGE_THRESHOLD = 0.90
    DEFAULT_REVIEW_THRESHOLD = 0.75
    DEFAULT_NO_MATCH_THRESHOLD = 0.50

    # Address abbreviation mappings for normalization
    ADDRESS_ABBREVIATIONS = {
        "street": "st",
        "st.": "st",
        "avenue": "ave",
        "ave.": "ave",
        "boulevard": "blvd",
        "blvd.": "blvd",
        "drive": "dr",
        "dr.": "dr",
        "road": "rd",
        "rd.": "rd",
        "lane": "ln",
        "ln.": "ln",
        "court": "ct",
        "ct.": "ct",
        "circle": "cir",
        "cir.": "cir",
        "place": "pl",
        "pl.": "pl",
        "north": "n",
        "n.": "n",
        "south": "s",
        "s.": "s",
        "east": "e",
        "e.": "e",
        "west": "w",
        "w.": "w",
        "apartment": "apt",
        "apt.": "apt",
        "suite": "ste",
        "ste.": "ste",
        "unit": "unit",
    }

    def __init__(self, merge_threshold: float = None, review_threshold: float = None):
        """
        Initialize the EntityLinker.

        Args:
            merge_threshold: Confidence threshold for automatic merge (default 0.90)
            review_threshold: Confidence threshold for manual review (default 0.75)
        """
        self.merge_threshold = merge_threshold or self.DEFAULT_MERGE_THRESHOLD
        self.review_threshold = review_threshold or self.DEFAULT_REVIEW_THRESHOLD

        # Cache for entity lookups
        self.entity_cache: Dict[str, Entity] = {}

        logger.info(
            f"EntityLinker initialized with thresholds: merge={self.merge_threshold}, review={self.review_threshold}"
        )

    def link_person(
        self,
        name: str,
        dob: str = None,
        address: str = None,
        identifiers: Dict[str, str] = None,
    ) -> Tuple[Optional[Entity], List[EntityMatch]]:
        """
        Link a person entity to existing entities.

        Args:
            name: Person's name
            dob: Date of birth (optional)
            address: Address (optional)
            identifiers: Other identifiers like SSN (optional)

        Returns:
            Tuple of (matched entity if found, list of potential matches)
        """
        entity_type = EntityType.PERSON
        normalized_name = self._normalize_name(name)

        # Search existing entities
        matches = []
        for entity_id, entity in self.entity_cache.items():
            if entity.entity_type != EntityType.PERSON:
                continue

            confidence, factors = self._calculate_person_match(
                normalized_name, dob, address, identifiers, entity
            )

            if confidence >= self.review_threshold:
                action = "merge" if confidence >= self.merge_threshold else "review"
                matches.append(
                    EntityMatch(
                        entity1_id="new",
                        entity2_id=entity_id,
                        confidence=confidence,
                        match_factors=factors,
                        recommended_action=action,
                    )
                )

        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)

        # If high confidence match, return existing entity
        if matches and matches[0].confidence >= self.merge_threshold:
            return self.entity_cache[matches[0].entity2_id], matches

        return None, matches

    def link_company(
        self, name: str, ein: str = None, state: str = None, address: str = None
    ) -> Tuple[Optional[Entity], List[EntityMatch]]:
        """
        Link a company entity to existing entities.

        Args:
            name: Company name
            ein: Employer Identification Number (optional)
            state: State of incorporation (optional)
            address: Business address (optional)

        Returns:
            Tuple of (matched entity if found, list of potential matches)
        """
        normalized_name = self._normalize_company_name(name)

        matches = []
        for entity_id, entity in self.entity_cache.items():
            if entity.entity_type != EntityType.COMPANY:
                continue

            confidence, factors = self._calculate_company_match(
                normalized_name, ein, state, address, entity
            )

            if confidence >= self.review_threshold:
                action = "merge" if confidence >= self.merge_threshold else "review"
                matches.append(
                    EntityMatch(
                        entity1_id="new",
                        entity2_id=entity_id,
                        confidence=confidence,
                        match_factors=factors,
                        recommended_action=action,
                    )
                )

        matches.sort(key=lambda m: m.confidence, reverse=True)

        if matches and matches[0].confidence >= self.merge_threshold:
            return self.entity_cache[matches[0].entity2_id], matches

        return None, matches

    def link_property(
        self, address: str, parcel_id: str = None, legal_description: str = None
    ) -> Tuple[Optional[Entity], List[EntityMatch]]:
        """
        Link a property entity to existing entities.

        Args:
            address: Property address
            parcel_id: Parcel/APN number (optional)
            legal_description: Legal description (optional)

        Returns:
            Tuple of (matched entity if found, list of potential matches)
        """
        normalized_address = self._normalize_address(address)

        matches = []
        for entity_id, entity in self.entity_cache.items():
            if entity.entity_type != EntityType.PROPERTY:
                continue

            confidence, factors = self._calculate_property_match(
                normalized_address, parcel_id, legal_description, entity
            )

            if confidence >= self.review_threshold:
                action = "merge" if confidence >= self.merge_threshold else "review"
                matches.append(
                    EntityMatch(
                        entity1_id="new",
                        entity2_id=entity_id,
                        confidence=confidence,
                        match_factors=factors,
                        recommended_action=action,
                    )
                )

        matches.sort(key=lambda m: m.confidence, reverse=True)

        if matches and matches[0].confidence >= self.merge_threshold:
            return self.entity_cache[matches[0].entity2_id], matches

        return None, matches

    def _calculate_person_match(
        self,
        name: str,
        dob: str,
        address: str,
        identifiers: Dict[str, str],
        entity: Entity,
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate match confidence for a person."""
        factors = {}

        # Name matching (weight: 0.4)
        name_score = self._calculate_name_similarity(name, entity.primary_name)
        for alias in entity.aliases:
            alias_score = self._calculate_name_similarity(name, alias)
            name_score = max(name_score, alias_score)
        factors["name"] = name_score

        # DOB matching (weight: 0.25)
        dob_score = 0.0
        if dob and "dob" in entity.identifiers:
            dob_score = 1.0 if dob == entity.identifiers["dob"] else 0.0
        factors["dob"] = dob_score

        # Address matching (weight: 0.2)
        address_score = 0.0
        if address and entity.addresses:
            normalized_address = self._normalize_address(address)
            for ent_address in entity.addresses:
                addr_str = ent_address.get("normalized", "")
                score = self._calculate_address_similarity(normalized_address, addr_str)
                address_score = max(address_score, score)
        factors["address"] = address_score

        # Identifier matching (weight: 0.15)
        id_score = 0.0
        if identifiers:
            for key, value in identifiers.items():
                if key in entity.identifiers and entity.identifiers[key] == value:
                    id_score = 1.0
                    break
        factors["identifiers"] = id_score

        # Calculate weighted score
        weights = {"name": 0.4, "dob": 0.25, "address": 0.2, "identifiers": 0.15}
        total_weight = sum(weights[k] for k in factors if factors[k] > 0 or k == "name")

        confidence = sum(factors[k] * weights[k] for k in factors) / total_weight

        return confidence, factors

    def _calculate_company_match(
        self, name: str, ein: str, state: str, address: str, entity: Entity
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate match confidence for a company."""
        factors = {}

        # Name matching (weight: 0.35) - use company name normalization
        normalized_input = self._normalize_company_name(name)
        normalized_entity = self._normalize_company_name(entity.primary_name)
        name_score = self._jaro_winkler(normalized_input, normalized_entity)
        for alias in entity.aliases:
            normalized_alias = self._normalize_company_name(alias)
            alias_score = self._jaro_winkler(normalized_input, normalized_alias)
            name_score = max(name_score, alias_score)
        factors["name"] = name_score

        # EIN matching (weight: 0.35)
        ein_score = 0.0
        if ein and "ein" in entity.identifiers:
            ein_score = 1.0 if ein == entity.identifiers["ein"] else 0.0
        factors["ein"] = ein_score

        # State matching (weight: 0.1)
        state_score = 0.0
        if state and "state" in entity.identifiers:
            state_score = (
                1.0 if state.upper() == entity.identifiers["state"].upper() else 0.0
            )
        factors["state"] = state_score

        # Address matching (weight: 0.2)
        address_score = 0.0
        if address and entity.addresses:
            normalized_address = self._normalize_address(address)
            for ent_address in entity.addresses:
                addr_str = ent_address.get("normalized", "")
                score = self._calculate_address_similarity(normalized_address, addr_str)
                address_score = max(address_score, score)
        factors["address"] = address_score

        # Calculate weighted score - only count weights for provided data
        weights = {"name": 0.35, "ein": 0.35, "state": 0.1, "address": 0.2}

        # Determine which factors were actually provided (not just empty/missing)
        provided_factors = ["name"]  # Name is always provided
        if ein:
            provided_factors.append("ein")
        if state:
            provided_factors.append("state")
        if address:
            provided_factors.append("address")

        total_weight = sum(weights[k] for k in provided_factors)
        if total_weight == 0:
            total_weight = weights["name"]

        confidence = (
            sum(factors[k] * weights[k] for k in provided_factors) / total_weight
        )

        return confidence, factors

    def _calculate_property_match(
        self, address: str, parcel_id: str, legal_description: str, entity: Entity
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate match confidence for a property."""
        factors = {}

        # Parcel ID matching - unique identifier, if it matches exactly, very high confidence
        parcel_score = 0.0
        parcel_exact_match = False
        if parcel_id and "parcel_id" in entity.identifiers:
            normalized_parcel = self._normalize_parcel_id(parcel_id)
            entity_parcel = self._normalize_parcel_id(entity.identifiers["parcel_id"])
            if normalized_parcel == entity_parcel:
                parcel_score = 1.0
                parcel_exact_match = True
        factors["parcel_id"] = parcel_score

        # Address matching
        address_score = 0.0
        if address and entity.addresses:
            for ent_address in entity.addresses:
                addr_str = ent_address.get("normalized", "")
                score = self._calculate_address_similarity(address, addr_str)
                address_score = max(address_score, score)
        factors["address"] = address_score

        # Legal description matching
        legal_score = 0.0
        if legal_description and "legal_description" in entity.identifiers:
            legal_score = self._calculate_legal_description_similarity(
                legal_description, entity.identifiers["legal_description"]
            )
        factors["legal_description"] = legal_score

        # Parcel ID is a unique identifier - if it matches exactly, confidence is very high
        # regardless of other factors
        if parcel_exact_match:
            return 0.95, factors

        # Calculate weighted score - only count weights for provided data
        weights = {"parcel_id": 0.5, "address": 0.35, "legal_description": 0.15}

        # Determine which factors were actually provided
        provided_factors = []
        if parcel_id:
            provided_factors.append("parcel_id")
        if address:
            provided_factors.append("address")
        if legal_description:
            provided_factors.append("legal_description")

        # At least one factor must be provided
        if not provided_factors:
            return 0.0, factors

        total_weight = sum(weights[k] for k in provided_factors)
        confidence = (
            sum(factors[k] * weights[k] for k in provided_factors) / total_weight
        )

        return confidence, factors

    def _normalize_name(self, name: str) -> str:
        """Normalize a person's name for matching."""
        if not name:
            return ""

        # Convert to lowercase
        name = name.lower().strip()

        # Remove common suffixes and prefixes
        name = re.sub(r"\b(jr|sr|ii|iii|iv|mr|mrs|ms|dr|phd|md|esq)\.?\b", "", name)

        # Remove punctuation
        name = re.sub(r"[^\w\s]", "", name)

        # Collapse whitespace
        name = " ".join(name.split())

        return name

    def _normalize_company_name(self, name: str) -> str:
        """Normalize a company name for matching."""
        if not name:
            return ""

        # Convert to lowercase
        name = name.lower().strip()

        # Remove common business suffixes
        suffixes = [
            "llc",
            "l.l.c.",
            "inc",
            "inc.",
            "incorporated",
            "corp",
            "corp.",
            "corporation",
            "co",
            "co.",
            "company",
            "ltd",
            "ltd.",
            "limited",
            "lp",
            "l.p.",
            "llp",
            "l.l.p.",
            "pllc",
            "p.l.l.c.",
            "pc",
            "p.c.",
        ]
        for suffix in suffixes:
            name = re.sub(rf"\b{re.escape(suffix)}\b", "", name)

        # Remove punctuation
        name = re.sub(r"[^\w\s]", "", name)

        # Collapse whitespace
        name = " ".join(name.split())

        return name

    def _normalize_address(self, address: str) -> str:
        """Normalize an address for matching."""
        if not address:
            return ""

        # Convert to lowercase
        address = address.lower().strip()

        # Apply abbreviations
        for full, abbrev in self.ADDRESS_ABBREVIATIONS.items():
            address = re.sub(rf"\b{re.escape(full)}\b", abbrev, address)

        # Remove punctuation except hyphen
        address = re.sub(r"[^\w\s-]", "", address)

        # Collapse whitespace
        address = " ".join(address.split())

        return address

    def _normalize_parcel_id(self, parcel_id: str) -> str:
        """Normalize a parcel ID for matching."""
        if not parcel_id:
            return ""

        # Remove all non-alphanumeric characters
        return re.sub(r"[^a-zA-Z0-9]", "", parcel_id.upper())

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names using Jaro-Winkler."""
        if not name1 or not name2:
            return 0.0

        name1 = self._normalize_name(name1)
        name2 = self._normalize_name(name2)

        # Use Jaro-Winkler similarity
        return self._jaro_winkler(name1, name2)

    def _calculate_address_similarity(self, addr1: str, addr2: str) -> float:
        """Calculate similarity between two addresses."""
        if not addr1 or not addr2:
            return 0.0

        # Normalize both addresses
        addr1 = self._normalize_address(addr1)
        addr2 = self._normalize_address(addr2)

        # Calculate token-based similarity
        tokens1 = set(addr1.split())
        tokens2 = set(addr2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)

        jaccard = len(intersection) / len(union)

        # Also consider Jaro-Winkler for overall similarity
        jaro = self._jaro_winkler(addr1, addr2)

        # Combine both metrics
        return 0.6 * jaccard + 0.4 * jaro

    def _calculate_legal_description_similarity(
        self, legal1: str, legal2: str
    ) -> float:
        """Calculate similarity between legal descriptions."""
        if not legal1 or not legal2:
            return 0.0

        # Normalize
        legal1 = legal1.lower().strip()
        legal2 = legal2.lower().strip()

        # Extract key elements (lot, block, section, etc.)
        pattern = r"(lot|block|section|township|range|subdivision)\s*[\d\w]+"

        elements1 = set(re.findall(pattern, legal1))
        elements2 = set(re.findall(pattern, legal2))

        if not elements1 and not elements2:
            return self._jaro_winkler(legal1, legal2)

        intersection = elements1.intersection(elements2)
        union = elements1.union(elements2)

        return len(intersection) / len(union) if union else 0.0

    def _jaro_winkler(
        self, s1: str, s2: str, winkler_prefix_weight: float = 0.1
    ) -> float:
        """Calculate Jaro-Winkler similarity between two strings."""
        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)

        if len1 == 0 or len2 == 0:
            return 0.0

        # Calculate match window
        match_distance = max(len1, len2) // 2 - 1
        match_distance = max(0, match_distance)

        s1_matches = [False] * len1
        s2_matches = [False] * len2

        matches = 0
        transpositions = 0

        # Find matches
        for i in range(len1):
            start = max(0, i - match_distance)
            end = min(i + match_distance + 1, len2)

            for j in range(start, end):
                if s2_matches[j] or s1[i] != s2[j]:
                    continue
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

        if matches == 0:
            return 0.0

        # Count transpositions
        k = 0
        for i in range(len1):
            if not s1_matches[i]:
                continue
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1

        transpositions //= 2

        # Calculate Jaro similarity
        jaro = (
            matches / len1 + matches / len2 + (matches - transpositions) / matches
        ) / 3

        # Apply Winkler prefix bonus
        prefix = 0
        for i in range(min(4, len1, len2)):
            if s1[i] == s2[i]:
                prefix += 1
            else:
                break

        return jaro + prefix * winkler_prefix_weight * (1 - jaro)

    def add_entity(self, entity: Entity) -> str:
        """Add an entity to the cache."""
        self.entity_cache[entity.entity_id] = entity
        logger.debug(f"Added entity {entity.entity_id} to cache")
        return entity.entity_id

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity from the cache."""
        return self.entity_cache.get(entity_id)

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity from the cache."""
        if entity_id in self.entity_cache:
            del self.entity_cache[entity_id]
            return True
        return False

    def merge_entities(self, entity1_id: str, entity2_id: str) -> Optional[Entity]:
        """
        Merge two entities into one.

        Args:
            entity1_id: Primary entity ID (will be kept)
            entity2_id: Secondary entity ID (will be merged and removed)

        Returns:
            Merged entity or None if merge fails
        """
        entity1 = self.entity_cache.get(entity1_id)
        entity2 = self.entity_cache.get(entity2_id)

        if not entity1 or not entity2:
            return None

        # Merge aliases
        entity1.aliases.extend(entity2.aliases)
        if entity2.primary_name not in entity1.aliases:
            entity1.aliases.append(entity2.primary_name)

        # Merge identifiers
        entity1.identifiers.update(entity2.identifiers)

        # Merge addresses
        entity1.addresses.extend(entity2.addresses)

        # Merge source records
        entity1.source_records.extend(entity2.source_records)

        # Update timestamp
        entity1.updated_at = datetime.now()

        # Remove entity2
        self.remove_entity(entity2_id)

        logger.info(f"Merged entity {entity2_id} into {entity1_id}")
        return entity1

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the entity cache."""
        type_counts = {}
        for entity in self.entity_cache.values():
            entity_type = entity.entity_type.value
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

        return {
            "total_entities": len(self.entity_cache),
            "entities_by_type": type_counts,
            "merge_threshold": self.merge_threshold,
            "review_threshold": self.review_threshold,
        }
