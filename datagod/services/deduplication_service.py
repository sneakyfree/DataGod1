"""
Deduplication Service
Identifies and handles duplicate records across data sources

This service provides:
- Duplicate detection using fuzzy matching
- Multiple merge strategies (keep newest, keep most complete, manual)
- Batch deduplication for large datasets
- Audit trail for merged records
- Name standardization (first/middle/last parsing, suffix handling)
- Address normalization (USPS standards)
- Multi-pass matching (exact ID, normalized name, fuzzy)
"""

import logging
import re
from typing import Dict, List, Any, Optional, Callable, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json

from datagod.services.entity_linker import EntityLinker

logger = logging.getLogger(__name__)


class MergeStrategy(Enum):
    """Strategies for merging duplicate records"""
    KEEP_NEWEST = "keep_newest"          # Keep the most recently updated record
    KEEP_OLDEST = "keep_oldest"          # Keep the original record
    KEEP_MOST_COMPLETE = "keep_complete" # Keep the record with most fields filled
    MERGE = "merge"                       # Combine non-conflicting fields
    MANUAL_REVIEW = "manual"             # Flag for manual review


@dataclass
class DuplicateGroup:
    """Represents a group of duplicate records"""
    group_id: str
    records: List[Dict[str, Any]]
    confidence: float
    match_fields: List[str]
    recommended_strategy: MergeStrategy
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'group_id': self.group_id,
            'record_count': len(self.records),
            'record_ids': [r.get('record_id', r.get('id')) for r in self.records],
            'confidence': self.confidence,
            'match_fields': self.match_fields,
            'recommended_strategy': self.recommended_strategy.value,
            'created_at': self.created_at.isoformat(),
        }


@dataclass
class MergeResult:
    """Result of a merge operation"""
    success: bool
    kept_record: Optional[Dict[str, Any]]
    removed_records: List[str]
    strategy_used: MergeStrategy
    audit_info: Dict[str, Any]


class NameStandardizer:
    """
    Standardize names for deduplication matching.

    Handles:
    - First/middle/last name parsing
    - Suffix extraction (Jr., Sr., III, etc.)
    - Prefix removal (Mr., Mrs., Dr., etc.)
    - Case normalization
    - Common nickname expansion
    """

    # Common name suffixes
    SUFFIXES = {
        'jr', 'jr.', 'junior',
        'sr', 'sr.', 'senior',
        'i', 'ii', 'iii', 'iv', 'v',
        '1st', '2nd', '3rd', '4th', '5th',
        'esq', 'esq.', 'esquire',
        'phd', 'ph.d.', 'ph.d',
        'md', 'm.d.', 'm.d',
        'dds', 'd.d.s.',
        'jd', 'j.d.',
    }

    # Name prefixes to remove
    PREFIXES = {
        'mr', 'mr.', 'mister',
        'mrs', 'mrs.', 'missus',
        'ms', 'ms.', 'miss',
        'dr', 'dr.', 'doctor',
        'prof', 'prof.', 'professor',
        'rev', 'rev.', 'reverend',
        'hon', 'hon.', 'honorable',
        'sir', 'dame', 'lord', 'lady',
    }

    # Common nickname mappings
    NICKNAMES = {
        'william': ['bill', 'will', 'billy', 'willy', 'liam'],
        'robert': ['bob', 'rob', 'bobby', 'robby', 'bert'],
        'richard': ['rick', 'dick', 'rich', 'richie', 'ricky'],
        'james': ['jim', 'jimmy', 'jamie', 'jas'],
        'john': ['jack', 'johnny', 'jon'],
        'michael': ['mike', 'mikey', 'mick'],
        'thomas': ['tom', 'tommy', 'thom'],
        'charles': ['charlie', 'chuck', 'chas'],
        'joseph': ['joe', 'joey', 'jo'],
        'david': ['dave', 'davey', 'davie'],
        'edward': ['ed', 'eddie', 'ted', 'teddy', 'ned'],
        'christopher': ['chris', 'topher', 'kit'],
        'daniel': ['dan', 'danny'],
        'matthew': ['matt', 'matty'],
        'anthony': ['tony', 'ant'],
        'steven': ['steve', 'stevie'],
        'stephen': ['steve', 'stevie'],
        'andrew': ['andy', 'drew'],
        'joshua': ['josh'],
        'kenneth': ['ken', 'kenny'],
        'kevin': ['kev'],
        'brian': ['bri'],
        'timothy': ['tim', 'timmy'],
        'ronald': ['ron', 'ronny', 'ronnie'],
        'jason': ['jay', 'jase'],
        'jeffrey': ['jeff', 'geoff'],
        'benjamin': ['ben', 'benji', 'benny'],
        'nicholas': ['nick', 'nicky', 'nico'],
        'samuel': ['sam', 'sammy'],
        'patrick': ['pat', 'patty', 'paddy'],
        'alexander': ['alex', 'xander', 'sandy'],
        'jonathan': ['jon', 'jonny', 'nathan'],
        'elizabeth': ['liz', 'lizzy', 'beth', 'betty', 'eliza', 'lisa', 'libby'],
        'margaret': ['maggie', 'meg', 'peggy', 'marge', 'margie', 'greta'],
        'jennifer': ['jen', 'jenny', 'jenn'],
        'patricia': ['pat', 'patty', 'trish', 'tricia'],
        'barbara': ['barb', 'barbie', 'babs'],
        'susan': ['sue', 'suzy', 'susie'],
        'jessica': ['jess', 'jessie'],
        'catherine': ['cathy', 'kate', 'katie', 'cat'],
        'katherine': ['kathy', 'kate', 'katie', 'kat', 'kitty'],
        'rebecca': ['becky', 'becca', 'reba'],
        'deborah': ['deb', 'debbie', 'debby'],
        'stephanie': ['steph', 'stephie'],
        'christine': ['chris', 'chrissie', 'tina'],
        'christina': ['chris', 'chrissie', 'tina'],
        'victoria': ['vicky', 'vicki', 'tori'],
        'amanda': ['mandy', 'mandi'],
        'melissa': ['mel', 'missy', 'lisa'],
        'dorothy': ['dot', 'dotty', 'dottie'],
        'theodore': ['ted', 'teddy', 'theo'],
        'lawrence': ['larry', 'laurie'],
        'gerald': ['jerry', 'gerry'],
        'harold': ['harry', 'hal'],
        'walter': ['walt', 'wally'],
        'raymond': ['ray'],
        'gregory': ['greg', 'gregg'],
        'frederick': ['fred', 'freddy', 'rick'],
        'albert': ['al', 'bert', 'bertie'],
        'arthur': ['art', 'artie'],
        'eugene': ['gene'],
        'phillip': ['phil'],
        'philip': ['phil'],
        'leonard': ['leo', 'len', 'lenny'],
        'henry': ['hank', 'harry', 'hal'],
        'francis': ['frank', 'fran', 'frankie'],
        'frances': ['fran', 'frankie', 'fanny'],
    }

    # Build reverse nickname map
    _nickname_to_canonical = {}
    for canonical, nicks in NICKNAMES.items():
        _nickname_to_canonical[canonical] = canonical
        for nick in nicks:
            _nickname_to_canonical[nick] = canonical

    @classmethod
    def standardize(cls, name: str) -> Dict[str, str]:
        """
        Standardize a full name into components.

        Returns dict with: first, middle, last, suffix, normalized_full
        """
        if not name:
            return {'first': '', 'middle': '', 'last': '', 'suffix': '', 'normalized_full': ''}

        # Clean and normalize
        name = name.strip().lower()
        name = re.sub(r'[^\w\s\'-]', ' ', name)  # Keep letters, spaces, hyphens, apostrophes
        name = re.sub(r'\s+', ' ', name)  # Normalize whitespace

        parts = name.split()

        # Remove prefixes
        while parts and parts[0] in cls.PREFIXES:
            parts.pop(0)

        # Extract suffix
        suffix = ''
        if parts and parts[-1] in cls.SUFFIXES:
            suffix = parts.pop()

        # Also check for comma-separated suffix (e.g., "Smith, Jr.")
        if parts and ',' in parts[-1]:
            last_part = parts[-1].replace(',', '')
            if last_part in cls.SUFFIXES:
                suffix = last_part
                parts.pop()

        # Parse remaining parts
        first = ''
        middle = ''
        last = ''

        if len(parts) == 1:
            last = parts[0]
        elif len(parts) == 2:
            first = parts[0]
            last = parts[1]
        elif len(parts) >= 3:
            first = parts[0]
            last = parts[-1]
            middle = ' '.join(parts[1:-1])

        # Get canonical first name (for nickname matching)
        canonical_first = cls._nickname_to_canonical.get(first, first)

        # Build normalized full name
        normalized_parts = [canonical_first]
        if middle:
            normalized_parts.append(middle)
        normalized_parts.append(last)
        normalized_full = ' '.join(normalized_parts)

        return {
            'first': first,
            'middle': middle,
            'last': last,
            'suffix': suffix,
            'canonical_first': canonical_first,
            'normalized_full': normalized_full,
        }

    @classmethod
    def names_match(cls, name1: str, name2: str, threshold: float = 0.85) -> Tuple[bool, float]:
        """
        Check if two names match, accounting for nicknames.

        Returns (is_match, confidence_score)
        """
        std1 = cls.standardize(name1)
        std2 = cls.standardize(name2)

        # Exact match on normalized
        if std1['normalized_full'] == std2['normalized_full']:
            return True, 1.0

        # Check last name match
        if std1['last'] != std2['last']:
            # Allow for hyphenated names
            if not (std1['last'] in std2['last'] or std2['last'] in std1['last']):
                return False, 0.0

        # Check first name (with nickname expansion)
        first_match = (
            std1['canonical_first'] == std2['canonical_first'] or
            std1['first'] == std2['first']
        )

        if first_match:
            # First and last match
            score = 0.95 if std1['middle'] == std2['middle'] else 0.90
            return True, score

        # Partial first name match (initials)
        if std1['first'] and std2['first']:
            if std1['first'][0] == std2['first'][0]:
                # Same initial, might be abbreviation
                return True, 0.75

        return False, 0.0


class AddressNormalizer:
    """
    Normalize addresses according to USPS standards.

    Handles:
    - Street type abbreviations (Street -> ST, Avenue -> AVE)
    - Directional abbreviations (North -> N, Southwest -> SW)
    - Unit/apartment standardization
    - State abbreviations
    - ZIP code formatting
    """

    # USPS street type abbreviations
    STREET_TYPES = {
        'alley': 'ALY', 'allee': 'ALY', 'ally': 'ALY', 'aly': 'ALY',
        'avenue': 'AVE', 'av': 'AVE', 'aven': 'AVE', 'avenu': 'AVE', 'avn': 'AVE', 'avnue': 'AVE', 'ave': 'AVE',
        'boulevard': 'BLVD', 'boul': 'BLVD', 'boulv': 'BLVD', 'blvd': 'BLVD',
        'circle': 'CIR', 'circ': 'CIR', 'circl': 'CIR', 'crcl': 'CIR', 'crcle': 'CIR', 'cir': 'CIR',
        'court': 'CT', 'crt': 'CT', 'ct': 'CT',
        'drive': 'DR', 'driv': 'DR', 'drv': 'DR', 'dr': 'DR',
        'expressway': 'EXPY', 'exp': 'EXPY', 'expr': 'EXPY', 'express': 'EXPY', 'expw': 'EXPY', 'expy': 'EXPY',
        'freeway': 'FWY', 'freewy': 'FWY', 'frway': 'FWY', 'frwy': 'FWY', 'fwy': 'FWY',
        'highway': 'HWY', 'highwy': 'HWY', 'hiway': 'HWY', 'hiwy': 'HWY', 'hway': 'HWY', 'hwy': 'HWY',
        'lane': 'LN', 'ln': 'LN',
        'parkway': 'PKWY', 'parkwy': 'PKWY', 'pkway': 'PKWY', 'pkwy': 'PKWY', 'pky': 'PKWY',
        'place': 'PL', 'pl': 'PL',
        'plaza': 'PLZ', 'plza': 'PLZ', 'plz': 'PLZ',
        'road': 'RD', 'rd': 'RD',
        'route': 'RTE', 'rte': 'RTE', 'rt': 'RTE',
        'square': 'SQ', 'sqr': 'SQ', 'sqre': 'SQ', 'squ': 'SQ', 'sq': 'SQ',
        'street': 'ST', 'strt': 'ST', 'str': 'ST', 'st': 'ST',
        'terrace': 'TER', 'terr': 'TER', 'ter': 'TER',
        'trail': 'TRL', 'trails': 'TRL', 'trl': 'TRL',
        'turnpike': 'TPKE', 'trnpk': 'TPKE', 'turnpk': 'TPKE', 'tpke': 'TPKE',
        'way': 'WAY', 'wy': 'WAY',
        # Additional common types
        'crossing': 'XING', 'xing': 'XING',
        'path': 'PATH',
        'walk': 'WALK',
        'loop': 'LOOP',
        'run': 'RUN',
        'point': 'PT', 'pt': 'PT',
        'ridge': 'RDG', 'rdg': 'RDG',
        'view': 'VW', 'vw': 'VW',
        'cove': 'CV', 'cv': 'CV',
        'bend': 'BND', 'bnd': 'BND',
    }

    # Directional abbreviations
    DIRECTIONS = {
        'north': 'N', 'n': 'N', 'no': 'N',
        'south': 'S', 's': 'S', 'so': 'S',
        'east': 'E', 'e': 'E',
        'west': 'W', 'w': 'W',
        'northeast': 'NE', 'ne': 'NE',
        'northwest': 'NW', 'nw': 'NW',
        'southeast': 'SE', 'se': 'SE',
        'southwest': 'SW', 'sw': 'SW',
    }

    # Unit type abbreviations
    UNIT_TYPES = {
        'apartment': 'APT', 'apt': 'APT', 'ap': 'APT',
        'suite': 'STE', 'ste': 'STE', 'suit': 'STE',
        'unit': 'UNIT', 'un': 'UNIT',
        'building': 'BLDG', 'bldg': 'BLDG', 'bld': 'BLDG',
        'floor': 'FL', 'fl': 'FL', 'flr': 'FL',
        'room': 'RM', 'rm': 'RM',
        'department': 'DEPT', 'dept': 'DEPT',
        'office': 'OFC', 'ofc': 'OFC',
        'lot': 'LOT',
        'space': 'SPC', 'spc': 'SPC',
        'pier': 'PIER',
        'slip': 'SLIP',
        'trailer': 'TRLR', 'trlr': 'TRLR',
        'penthouse': 'PH', 'ph': 'PH',
        'basement': 'BSMT', 'bsmt': 'BSMT',
        'lower': 'LOWR', 'lowr': 'LOWR',
        'upper': 'UPPR', 'uppr': 'UPPR',
        'rear': 'REAR',
        'front': 'FRNT', 'frnt': 'FRNT',
        'side': 'SIDE',
        'stop': 'STOP',
    }

    # State abbreviations
    STATES = {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
        'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
        'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
        'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
        'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
        'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
        'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
        'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
        'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
        'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
        'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC',
        'puerto rico': 'PR', 'guam': 'GU', 'virgin islands': 'VI',
        'american samoa': 'AS', 'northern mariana islands': 'MP',
    }

    @classmethod
    def normalize(cls, address: str, city: str = '', state: str = '', zip_code: str = '') -> Dict[str, str]:
        """
        Normalize an address to USPS standards.

        Returns dict with normalized components.
        """
        if not address:
            return {
                'street': '',
                'city': '',
                'state': '',
                'zip': '',
                'normalized_full': '',
            }

        # Combine parts if provided separately
        full_addr = address.strip().upper()

        # Clean and normalize
        full_addr = re.sub(r'[^\w\s#\-/]', ' ', full_addr)
        full_addr = re.sub(r'\s+', ' ', full_addr)

        parts = full_addr.split()
        normalized_parts = []

        i = 0
        while i < len(parts):
            part = parts[i].lower()

            # Check for directions
            if part in cls.DIRECTIONS:
                normalized_parts.append(cls.DIRECTIONS[part])
            # Check for street types
            elif part in cls.STREET_TYPES:
                normalized_parts.append(cls.STREET_TYPES[part])
            # Check for unit types
            elif part in cls.UNIT_TYPES:
                normalized_parts.append(cls.UNIT_TYPES[part])
            # Check for ordinal numbers (1st, 2nd, etc.)
            elif re.match(r'^\d+(st|nd|rd|th)$', part):
                normalized_parts.append(part.upper())
            # Keep numbers and regular words
            else:
                normalized_parts.append(parts[i].upper())

            i += 1

        normalized_street = ' '.join(normalized_parts)

        # Normalize city
        normalized_city = city.strip().upper() if city else ''

        # Normalize state
        normalized_state = state.strip().upper() if state else ''
        if normalized_state.lower() in cls.STATES:
            normalized_state = cls.STATES[normalized_state.lower()]

        # Normalize ZIP code (keep first 5 digits)
        normalized_zip = re.sub(r'[^\d]', '', zip_code)[:5] if zip_code else ''

        # Build full normalized address
        full_parts = [normalized_street]
        if normalized_city:
            full_parts.append(normalized_city)
        if normalized_state:
            full_parts.append(normalized_state)
        if normalized_zip:
            full_parts.append(normalized_zip)

        return {
            'street': normalized_street,
            'city': normalized_city,
            'state': normalized_state,
            'zip': normalized_zip,
            'normalized_full': ', '.join(full_parts) if len(full_parts) > 1 else normalized_street,
        }

    @classmethod
    def addresses_match(cls, addr1: str, addr2: str,
                       city1: str = '', city2: str = '',
                       state1: str = '', state2: str = '',
                       zip1: str = '', zip2: str = '') -> Tuple[bool, float]:
        """
        Check if two addresses match.

        Returns (is_match, confidence_score)
        """
        norm1 = cls.normalize(addr1, city1, state1, zip1)
        norm2 = cls.normalize(addr2, city2, state2, zip2)

        # Exact match
        if norm1['normalized_full'] == norm2['normalized_full']:
            return True, 1.0

        # Street match with ZIP
        if norm1['street'] == norm2['street'] and norm1['zip'] == norm2['zip']:
            return True, 0.95

        # Street match with city/state
        if norm1['street'] == norm2['street']:
            if norm1['city'] == norm2['city'] and norm1['state'] == norm2['state']:
                return True, 0.90
            elif norm1['state'] == norm2['state']:
                return True, 0.80

        # Partial street match (handle unit differences)
        street1_parts = set(norm1['street'].split())
        street2_parts = set(norm2['street'].split())

        common = street1_parts & street2_parts
        total = street1_parts | street2_parts

        if len(common) > 0 and len(total) > 0:
            similarity = len(common) / len(total)
            if similarity >= 0.8:
                return True, similarity * 0.9

        return False, 0.0


class DeduplicationService:
    """
    Service for detecting and handling duplicate records.

    Features:
    - Configurable duplicate detection thresholds
    - Multiple merge strategies
    - Batch processing for large datasets
    - Full audit trail
    - Multi-pass matching (exact ID, normalized name, address, fuzzy)
    - Name standardization with nickname support
    - Address normalization (USPS standards)
    """

    # Default thresholds
    DEFAULT_DUPLICATE_THRESHOLD = 0.85
    DEFAULT_POSSIBLE_THRESHOLD = 0.70

    # Fields that indicate a likely duplicate if they match
    HIGH_WEIGHT_FIELDS = ['parcel_id', 'document_number', 'record_id', 'ssn', 'ein', 'license_number', 'case_number']
    MEDIUM_WEIGHT_FIELDS = ['property_address', 'grantor', 'grantee', 'owner_name', 'full_name', 'name', 'address']
    LOW_WEIGHT_FIELDS = ['record_date', 'amount', 'document_type', 'city', 'state', 'zip_code']

    # Name fields for standardized matching
    NAME_FIELDS = ['full_name', 'name', 'owner_name', 'grantor', 'grantee', 'defendant', 'plaintiff',
                   'first_name', 'last_name', 'business_name', 'entity_name']

    # Address fields for normalized matching
    ADDRESS_FIELDS = ['address', 'property_address', 'street_address', 'mailing_address',
                      'residence_address', 'business_address']

    def __init__(self,
                 entity_linker: EntityLinker = None,
                 duplicate_threshold: float = None,
                 possible_threshold: float = None,
                 use_name_standardization: bool = True,
                 use_address_normalization: bool = True):
        """
        Initialize the DeduplicationService.

        Args:
            entity_linker: EntityLinker instance for fuzzy matching
            duplicate_threshold: Threshold for definite duplicates (default 0.85)
            possible_threshold: Threshold for possible duplicates (default 0.70)
            use_name_standardization: Enable name standardization with nicknames
            use_address_normalization: Enable USPS address normalization
        """
        self.entity_linker = entity_linker or EntityLinker()
        self.duplicate_threshold = duplicate_threshold or self.DEFAULT_DUPLICATE_THRESHOLD
        self.possible_threshold = possible_threshold or self.DEFAULT_POSSIBLE_THRESHOLD
        self.use_name_standardization = use_name_standardization
        self.use_address_normalization = use_address_normalization

        # Track processed groups
        self.duplicate_groups: Dict[str, DuplicateGroup] = {}
        self.merge_history: List[MergeResult] = []

        logger.info(f"DeduplicationService initialized with thresholds: "
                   f"duplicate={self.duplicate_threshold}, possible={self.possible_threshold}, "
                   f"name_std={use_name_standardization}, addr_norm={use_address_normalization}")

    def find_duplicates(self, record: Dict[str, Any],
                       candidates: List[Dict[str, Any]]) -> List[DuplicateGroup]:
        """
        Find potential duplicates of a record in a list of candidates.

        Args:
            record: Record to check for duplicates
            candidates: List of records to compare against

        Returns:
            List of DuplicateGroups containing potential duplicates
        """
        matches = []

        for candidate in candidates:
            # Skip if same record
            if self._get_record_id(record) == self._get_record_id(candidate):
                continue

            similarity, match_fields = self._calculate_similarity(record, candidate)

            if similarity >= self.possible_threshold:
                matches.append({
                    'record': candidate,
                    'similarity': similarity,
                    'match_fields': match_fields
                })

        if not matches:
            return []

        # Group by similarity
        definite_matches = [m for m in matches if m['similarity'] >= self.duplicate_threshold]
        possible_matches = [m for m in matches if self.possible_threshold <= m['similarity'] < self.duplicate_threshold]

        groups = []

        if definite_matches:
            all_records = [record] + [m['record'] for m in definite_matches]
            avg_similarity = sum(m['similarity'] for m in definite_matches) / len(definite_matches)
            all_match_fields = set()
            for m in definite_matches:
                all_match_fields.update(m['match_fields'])

            group = DuplicateGroup(
                group_id=self._generate_group_id(all_records),
                records=all_records,
                confidence=avg_similarity,
                match_fields=list(all_match_fields),
                recommended_strategy=MergeStrategy.KEEP_NEWEST
            )
            groups.append(group)

        if possible_matches:
            for match in possible_matches:
                group = DuplicateGroup(
                    group_id=self._generate_group_id([record, match['record']]),
                    records=[record, match['record']],
                    confidence=match['similarity'],
                    match_fields=match['match_fields'],
                    recommended_strategy=MergeStrategy.MANUAL_REVIEW
                )
                groups.append(group)

        return groups

    def find_all_duplicates(self, records: List[Dict[str, Any]],
                           progress_callback: Callable = None) -> List[DuplicateGroup]:
        """
        Find all duplicate groups in a list of records.

        Args:
            records: List of records to check
            progress_callback: Optional callback for progress updates

        Returns:
            List of DuplicateGroups
        """
        all_groups = []
        processed_ids = set()
        total = len(records)

        for i, record in enumerate(records):
            record_id = self._get_record_id(record)

            if record_id in processed_ids:
                continue

            # Find duplicates for this record
            remaining = records[i + 1:]
            groups = self.find_duplicates(record, remaining)

            for group in groups:
                # Mark all records in group as processed
                for r in group.records:
                    processed_ids.add(self._get_record_id(r))

                all_groups.append(group)
                self.duplicate_groups[group.group_id] = group

            if progress_callback and (i + 1) % 100 == 0:
                progress_callback(i + 1, total)

        logger.info(f"Found {len(all_groups)} duplicate groups in {total} records")
        return all_groups

    def _calculate_similarity(self, record1: Dict[str, Any],
                             record2: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        Calculate similarity between two records using multi-pass matching.

        Pass 1: Exact ID match (highest confidence)
        Pass 2: Normalized name match (with nickname handling)
        Pass 3: Normalized address match (USPS standards)
        Pass 4: Fuzzy field matching

        Returns:
            Tuple of (similarity score, list of matching fields)
        """
        # Skip if same record (based on record_id)
        if self._get_record_id(record1) == self._get_record_id(record2):
            return 0.0, []

        match_fields = []
        scores = []
        weights = []

        # PASS 1: Check high-weight ID fields (exact match)
        for field in self.HIGH_WEIGHT_FIELDS:
            if field in record1 and field in record2:
                if record1[field] and record2[field]:
                    val1 = str(record1[field]).strip().lower()
                    val2 = str(record2[field]).strip().lower()
                    if val1 == val2:
                        scores.append(1.0)
                        weights.append(3.0)
                        match_fields.append(field)
                    else:
                        scores.append(0.0)
                        weights.append(3.0)

        # PASS 2: Name field matching with standardization
        if self.use_name_standardization:
            for field in self.NAME_FIELDS:
                if field in record1 and field in record2:
                    if record1[field] and record2[field]:
                        val1 = str(record1[field])
                        val2 = str(record2[field])
                        is_match, confidence = NameStandardizer.names_match(val1, val2)
                        if is_match:
                            scores.append(confidence)
                            weights.append(2.5)  # High weight for name matches
                            match_fields.append(f"{field}_normalized")
                        else:
                            # Fall back to Jaro-Winkler
                            similarity = self.entity_linker._jaro_winkler(
                                val1.lower().strip(),
                                val2.lower().strip()
                            )
                            scores.append(similarity)
                            weights.append(2.0)
                            if similarity > 0.85:
                                match_fields.append(field)

        # PASS 3: Address field matching with USPS normalization
        if self.use_address_normalization:
            for field in self.ADDRESS_FIELDS:
                if field in record1 and field in record2:
                    if record1[field] and record2[field]:
                        addr1 = str(record1[field])
                        addr2 = str(record2[field])

                        # Get city/state/zip if available
                        city1 = str(record1.get('city', ''))
                        city2 = str(record2.get('city', ''))
                        state1 = str(record1.get('state', ''))
                        state2 = str(record2.get('state', ''))
                        zip1 = str(record1.get('zip_code', record1.get('zip', '')))
                        zip2 = str(record2.get('zip_code', record2.get('zip', '')))

                        is_match, confidence = AddressNormalizer.addresses_match(
                            addr1, addr2, city1, city2, state1, state2, zip1, zip2
                        )
                        if is_match:
                            scores.append(confidence)
                            weights.append(2.5)  # High weight for address matches
                            match_fields.append(f"{field}_normalized")
                        else:
                            # Fall back to Jaro-Winkler
                            similarity = self.entity_linker._jaro_winkler(
                                addr1.lower().strip(),
                                addr2.lower().strip()
                            )
                            scores.append(similarity)
                            weights.append(2.0)
                            if similarity > 0.85:
                                match_fields.append(field)

        # PASS 4: Check remaining medium-weight fields with fuzzy matching
        # Skip fields already handled by name/address normalization
        handled_fields = set(self.NAME_FIELDS) | set(self.ADDRESS_FIELDS)
        for field in self.MEDIUM_WEIGHT_FIELDS:
            if field in handled_fields:
                continue
            if field in record1 and field in record2:
                if record1[field] and record2[field]:
                    val1 = str(record1[field])
                    val2 = str(record2[field])
                    similarity = self.entity_linker._jaro_winkler(
                        val1.lower().strip(),
                        val2.lower().strip()
                    )
                    scores.append(similarity)
                    weights.append(2.0)
                    if similarity > 0.85:
                        match_fields.append(field)

        # Check low-weight fields
        for field in self.LOW_WEIGHT_FIELDS:
            if field in record1 and field in record2:
                if record1[field] and record2[field]:
                    val1 = str(record1[field]).strip().lower()
                    val2 = str(record2[field]).strip().lower()
                    if val1 == val2:
                        scores.append(1.0)
                        match_fields.append(field)
                    else:
                        scores.append(0.0)
                    weights.append(1.0)

        if not scores:
            return 0.0, []

        # Calculate weighted average
        total_weight = sum(weights)
        weighted_score = sum(s * w for s, w in zip(scores, weights)) / total_weight

        return weighted_score, match_fields

    def merge_duplicates(self, group: DuplicateGroup,
                        strategy: MergeStrategy = None) -> MergeResult:
        """
        Merge a group of duplicate records.

        Args:
            group: DuplicateGroup to merge
            strategy: Merge strategy to use (default: use recommended)

        Returns:
            MergeResult with details of the merge
        """
        if not group.records or len(group.records) < 2:
            return MergeResult(
                success=False,
                kept_record=None,
                removed_records=[],
                strategy_used=strategy or group.recommended_strategy,
                audit_info={'error': 'Not enough records to merge'}
            )

        strategy = strategy or group.recommended_strategy

        if strategy == MergeStrategy.MANUAL_REVIEW:
            # Don't automatically merge, just mark for review
            return MergeResult(
                success=False,
                kept_record=None,
                removed_records=[],
                strategy_used=strategy,
                audit_info={'status': 'requires_manual_review', 'group_id': group.group_id}
            )

        # Select primary record based on strategy
        if strategy == MergeStrategy.KEEP_NEWEST:
            kept_record = self._select_newest(group.records)
        elif strategy == MergeStrategy.KEEP_OLDEST:
            kept_record = self._select_oldest(group.records)
        elif strategy == MergeStrategy.KEEP_MOST_COMPLETE:
            kept_record = self._select_most_complete(group.records)
        elif strategy == MergeStrategy.MERGE:
            kept_record = self._merge_records(group.records)
        else:
            kept_record = group.records[0]

        # Get list of removed record IDs
        kept_id = self._get_record_id(kept_record)
        removed_ids = [
            self._get_record_id(r) for r in group.records
            if self._get_record_id(r) != kept_id
        ]

        result = MergeResult(
            success=True,
            kept_record=kept_record,
            removed_records=removed_ids,
            strategy_used=strategy,
            audit_info={
                'group_id': group.group_id,
                'merged_at': datetime.now().isoformat(),
                'record_count': len(group.records),
                'confidence': group.confidence,
                'match_fields': group.match_fields,
            }
        )

        self.merge_history.append(result)

        logger.info(f"Merged {len(removed_ids)} records into {kept_id} using {strategy.value}")
        return result

    def _select_newest(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the most recently updated record."""
        def get_date(r):
            for field in ['updated_at', 'created_at', 'record_date', 'fetched_at']:
                if field in r and r[field]:
                    try:
                        if isinstance(r[field], datetime):
                            return r[field]
                        return datetime.fromisoformat(str(r[field]).replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        continue
            return datetime.min

        return max(records, key=get_date)

    def _select_oldest(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the oldest record."""
        def get_date(r):
            for field in ['created_at', 'record_date', 'fetched_at']:
                if field in r and r[field]:
                    try:
                        if isinstance(r[field], datetime):
                            return r[field]
                        return datetime.fromisoformat(str(r[field]).replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        continue
            return datetime.max

        return min(records, key=get_date)

    def _select_most_complete(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the record with the most non-empty fields."""
        def count_fields(r):
            return sum(1 for v in r.values() if v is not None and v != '' and v != [])

        return max(records, key=count_fields)

    def _merge_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple records, combining non-conflicting fields."""
        if not records:
            return {}

        # Start with the most complete record
        merged = self._select_most_complete(records).copy()

        # Add fields from other records if not present
        for record in records:
            for key, value in record.items():
                if key not in merged or not merged[key]:
                    if value is not None and value != '' and value != []:
                        merged[key] = value

        # Track merge sources
        merged['_merged_from'] = [self._get_record_id(r) for r in records]
        merged['_merged_at'] = datetime.now().isoformat()

        return merged

    def _get_record_id(self, record: Dict[str, Any]) -> str:
        """Get the ID of a record."""
        for field in ['record_id', 'id', 'document_id', '_id']:
            if field in record and record[field]:
                return str(record[field])

        # Generate hash-based ID if no ID field
        return hashlib.md5(
            json.dumps(record, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

    def _generate_group_id(self, records: List[Dict[str, Any]]) -> str:
        """Generate a unique ID for a duplicate group."""
        record_ids = sorted([self._get_record_id(r) for r in records])
        combined = '-'.join(record_ids)
        return hashlib.md5(combined.encode()).hexdigest()[:12]

    def get_statistics(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        total_groups = len(self.duplicate_groups)
        total_merges = len(self.merge_history)
        successful_merges = sum(1 for m in self.merge_history if m.success)
        total_removed = sum(len(m.removed_records) for m in self.merge_history if m.success)

        strategy_counts = {}
        for merge in self.merge_history:
            strategy = merge.strategy_used.value
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        return {
            'total_duplicate_groups': total_groups,
            'total_merge_operations': total_merges,
            'successful_merges': successful_merges,
            'total_records_removed': total_removed,
            'merge_by_strategy': strategy_counts,
            'duplicate_threshold': self.duplicate_threshold,
            'possible_threshold': self.possible_threshold,
        }

    def get_pending_review(self) -> List[DuplicateGroup]:
        """Get duplicate groups pending manual review."""
        return [
            g for g in self.duplicate_groups.values()
            if g.recommended_strategy == MergeStrategy.MANUAL_REVIEW
        ]

    def clear_history(self):
        """Clear merge history and duplicate groups."""
        self.duplicate_groups.clear()
        self.merge_history.clear()
        logger.info("Cleared deduplication history")


# Convenience function
def deduplicate_records(records: List[Dict[str, Any]],
                       strategy: MergeStrategy = MergeStrategy.KEEP_NEWEST,
                       threshold: float = 0.85) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Deduplicate a list of records.

    Args:
        records: List of records to deduplicate
        strategy: Merge strategy to use
        threshold: Similarity threshold for duplicates

    Returns:
        Tuple of (deduplicated records, statistics)
    """
    service = DeduplicationService(duplicate_threshold=threshold)

    # Find all duplicates
    groups = service.find_all_duplicates(records)

    # Process each group
    kept_ids = set()
    removed_ids = set()

    for group in groups:
        result = service.merge_duplicates(group, strategy)
        if result.success:
            kept_ids.add(service._get_record_id(result.kept_record))
            removed_ids.update(result.removed_records)

    # Filter to keep only non-removed records
    deduplicated = []
    for record in records:
        record_id = service._get_record_id(record)
        if record_id not in removed_ids:
            deduplicated.append(record)

    return deduplicated, service.get_statistics()
