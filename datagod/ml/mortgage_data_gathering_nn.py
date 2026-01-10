"""
Mortgage Data Gathering Neural Network
This module implements a new neural network approach for gathering and processing mortgage data
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import re
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class MortgageDataPoint:
    """Represents a single mortgage data point with comprehensive mortgage information"""
    
    # Core identifiers
    property_id: str
    """Unique identifier for the property"""
    
    # Borrower information
    borrower_name: str
    """Name of the borrower/owner"""
    
    # Lender information
    lender_name: str
    """Name of the lending institution"""
    
    # Loan details
    loan_amount: float
    """Total loan amount"""
    
    loan_type: str
    """Type of loan (e.g., Conventional, FHA, VA)"""
    
    interest_rate: float
    """Interest rate percentage"""
    
    loan_term: int
    """Loan term in years"""
    
    loan_date: str
    """Date the loan was originated"""
    
    # Property details
    property_address: str
    """Full property address"""
    
    property_value: float
    """Estimated property value"""
    
    # Status and metadata
    status: str
    """Current status of the loan (active, paid, delinquent, etc.)"""
    
    data_source: str
    """Source of the data (property_records, court_records, etc.)"""
    
    scraped_at: str
    """Timestamp when data was scraped"""
    
    # Quality metrics (added dynamically)
    quality_score: Optional[float] = None
    """Data quality score (0-100)"""
    
    # Confidence metrics (added dynamically)
    confidence_score: Optional[float] = None
    """Confidence score for the extracted data (0-100)"""

class MortgageDataGatheringNeuralNetwork:
    """Neural network for gathering mortgage data from various sources"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.learning_patterns = defaultdict(list)
        self.data_quality_scores = {}
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.similarity_threshold = 0.7
        
        # Define patterns for different mortgage data extraction
        self.patterns = {
            'loan_amount': [
                r'\$(\d+(?:,\d+)*)',
                r'loan amount.*?(\d+(?:,\d+)*)',
                r'principal.*?(\d+(?:,\d+)*)',
                r'amount.*?(\d+(?:,\d+)*)'
            ],
            'interest_rate': [
                r'(\d+(?:\.\d+)?)%.*?interest',
                r'rate.*?(\d+(?:\.\d+)?)%',
                r'interest.*?(\d+(?:\.\d+)?)%',
                r'apr.*?(\d+(?:\.\d+)?)%'
            ],
            'loan_term': [
                r'(\d+).*?year',
                r'(\d+).*?term',
                r'loan.*?(\d+).*?year',
                r'term.*?(\d+).*?year'
            ],
            'property_value': [
                r'\$(\d+(?:,\d+)*)',
                r'property.*?value.*?(\d+(?:,\d+)*)',
                r'appraisal.*?(\d+(?:,\d+)*)',
                r'assessed.*?(\d+(?:,\d+)*)'
            ],
            'loan_date': [
                r'\d{4}-\d{2}-\d{2}',
                r'\d{1,2}/\d{1,2}/\d{4}',
                r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*.*?\d{4}',
                r'\d{1,2}.*?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*.*?\d{4}'
            ]
        }
        
        # Define loan type patterns
        self.loan_type_patterns = {
            'conventional': [r'conventional', r' conventional'],
            'fha': [r'fha', r'federal housing administration'],
            'va': [r'va', r'veterans affairs'],
            'usda': [r'usda', r'farmers home administration'],
            'cd': [r'cd', r'certificate of deposit'],
            'pif': [r'pif', r'private investor fund'],
        }
    
    def extract_mortgage_data(self, raw_data: str, source_type: str) -> List[MortgageDataPoint]:
        """Extract mortgage data using pattern matching and similarity analysis"""
        self.logger.info(f"Extracting mortgage data from {source_type}")
        
        # Normalize the raw data for better matching
        normalized_data = raw_data.lower().strip()
        
        # Apply different extraction strategies based on source type
        if source_type == 'property_records':
            return self._extract_from_property_records(normalized_data)
        elif source_type == 'court_records':
            return self._extract_from_court_records(normalized_data)
        elif source_type == 'government_api':
            return self._extract_from_government_api(normalized_data)
        else:
            return self._extract_generic_mortgage_data(normalized_data)
    
    def _extract_from_property_records(self, data: str) -> List[MortgageDataPoint]:
        """Extract mortgage data from property records"""
        mortgage_data = []
        
        # Look for key mortgage information patterns
        borrower_names = self._extract_by_pattern(data, 'borrower_name', [
            r'borrower.*?([a-zA-Z\s]+)',
            r'owner.*?([a-zA-Z\s]+)',
            r'buyer.*?([a-zA-Z\s]+)',
            r'loan.*?holder.*?([a-zA-Z\s]+)'
        ])
        
        lender_names = self._extract_by_pattern(data, 'lender_name', [
            r'lender.*?([a-zA-Z\s]+)',
            r'bank.*?([a-zA-Z\s]+)',
            r'financial.*?([a-zA-Z\s]+)',
            r'credit.*?([a-zA-Z\s]+)'
        ])
        
        loan_amounts = self._extract_by_pattern(data, 'loan_amount', self.patterns['loan_amount'])
        interest_rates = self._extract_by_pattern(data, 'interest_rate', self.patterns['interest_rate'])
        loan_terms = self._extract_by_pattern(data, 'loan_term', self.patterns['loan_term'])
        property_values = self._extract_by_pattern(data, 'property_value', self.patterns['property_value'])
        loan_dates = self._extract_by_pattern(data, 'loan_date', self.patterns['loan_date'])
        
        # Extract loan types
        loan_types = self._extract_loan_types(data)
        
        # Create data points based on what we found
        data_points = []
        
        # Get the maximum number of data points we can create
        max_count = max(
            len(borrower_names),
            len(lender_names),
            len(loan_amounts),
            len(interest_rates),
            len(loan_terms),
            len(property_values),
            len(loan_dates),
            len(loan_types)
        )
        
        for i in range(max_count):
            borrower = borrower_names[i] if i < len(borrower_names) else "Unknown"
            lender = lender_names[i] if i < len(lender_names) else "Unknown"
            loan_amount = self._parse_amount(loan_amounts[i]) if i < len(loan_amounts) else 0.0
            interest_rate = self._parse_percentage(interest_rates[i]) if i < len(interest_rates) else 0.0
            loan_term = self._parse_number(loan_terms[i]) if i < len(loan_terms) else 30
            property_value = self._parse_amount(property_values[i]) if i < len(property_values) else 0.0
            loan_date = loan_dates[i] if i < len(loan_dates) else datetime.now().strftime("%Y-%m-%d")
            loan_type = loan_types[i] if i < len(loan_types) else "Unknown"
            
            # Generate property ID
            property_id = f"PROP-{hash(data + str(i)) % 1000000}"
            
            data_point = MortgageDataPoint(
                property_id=property_id,
                borrower_name=borrower,
                lender_name=lender,
                loan_amount=loan_amount,
                loan_type=loan_type,
                interest_rate=interest_rate,
                loan_term=loan_term,
                loan_date=loan_date,
                property_address="Unknown",
                property_value=property_value,
                status="active",
                data_source="property_records",
                scraped_at=datetime.now().isoformat()
            )
            data_points.append(data_point)
        
        return data_points
    
    def _extract_from_court_records(self, data: str) -> List[MortgageDataPoint]:
        """Extract mortgage data from court records"""
        mortgage_data = []
        
        # Court records often contain foreclosure information
        foreclosure_patterns = [
            r'foreclosure.*?loan.*?(\d+(?:,\d+)*)',
            r'judgment.*?amount.*?(\$[\d,]+)',
            r'court.*?order.*?(\d+(?:,\d+)*)',
            r'foreclosure.*?(\d+(?:,\d+)*)'
        ]
        
        # Extract property information
        property_patterns = [
            r'property.*?address.*?([a-zA-Z0-9\s,]+)',
            r'location.*?([a-zA-Z0-9\s,]+)',
            r'property.*?([a-zA-Z0-9\s,]+)'
        ]
        
        # Extract borrower information
        borrower_patterns = [
            r'borrower.*?([a-zA-Z\s]+)',
            r'owner.*?([a-zA-Z\s]+)',
            r'debtor.*?([a-zA-Z\s]+)'
        ]
        
        # Extract lender information
        lender_patterns = [
            r'lender.*?([a-zA-Z\s]+)',
            r'bank.*?([a-zA-Z\s]+)',
            r'financial.*?([a-zA-Z\s]+)'
        ]
        
        # Try to find mortgage data
        loan_amounts = self._extract_by_pattern(data, 'loan_amount', self.patterns['loan_amount'])
        borrower_names = self._extract_by_pattern(data, 'borrower_name', borrower_patterns)
        lender_names = self._extract_by_pattern(data, 'lender_name', lender_patterns)
        loan_dates = self._extract_by_pattern(data, 'loan_date', self.patterns['loan_date'])
        
        # Create data points
        data_points = []
        
        max_count = max(
            len(loan_amounts),
            len(borrower_names),
            len(lender_names),
            len(loan_dates)
        )
        
        for i in range(max_count):
            loan_amount = self._parse_amount(loan_amounts[i]) if i < len(loan_amounts) else 0.0
            borrower = borrower_names[i] if i < len(borrower_names) else "Unknown"
            lender = lender_names[i] if i < len(lender_names) else "Unknown"
            loan_date = loan_dates[i] if i < len(loan_dates) else datetime.now().strftime("%Y-%m-%d")
            
            # Generate property ID
            property_id = f"PROP-{hash(data + str(i)) % 1000000}"
            
            data_point = MortgageDataPoint(
                property_id=property_id,
                borrower_name=borrower,
                lender_name=lender,
                loan_amount=loan_amount,
                loan_type="Foreclosure",
                interest_rate=0.0,
                loan_term=0,
                loan_date=loan_date,
                property_address="Unknown",
                property_value=0.0,
                status="active",
                data_source="court_records",
                scraped_at=datetime.now().isoformat()
            )
            data_points.append(data_point)
        
        return data_points
    
    def _extract_from_government_api(self, data: str) -> List[MortgageDataPoint]:
        """Extract mortgage data from government APIs"""
        mortgage_data = []
        
        try:
            # Try to parse as JSON if it's API data
            parsed_data = json.loads(data)
            
            # Look for mortgage-specific fields
            if isinstance(parsed_data, dict):
                # Extract loan information from API response
                loan_info = parsed_data.get('loan_info', {})
                property_info = parsed_data.get('property_info', {})
                
                data_point = MortgageDataPoint(
                    property_id=loan_info.get('property_id', 'Unknown'),
                    borrower_name=loan_info.get('borrower_name', 'Unknown'),
                    lender_name=loan_info.get('lender_name', 'Unknown'),
                    loan_amount=loan_info.get('loan_amount', 0.0),
                    loan_type=loan_info.get('loan_type', 'Unknown'),
                    interest_rate=loan_info.get('interest_rate', 0.0),
                    loan_term=loan_info.get('loan_term', 30),
                    loan_date=loan_info.get('loan_date', datetime.now().strftime("%Y-%m-%d")),
                    property_address=property_info.get('address', 'Unknown'),
                    property_value=property_info.get('property_value', 0.0),
                    status=loan_info.get('status', 'active'),
                    data_source="government_api",
                    scraped_at=datetime.now().isoformat()
                )
                mortgage_data.append(data_point)
                
        except json.JSONDecodeError:
            # If it's not JSON, fall back to pattern matching
            return self._extract_generic_mortgage_data(data)
        
        return mortgage_data
    
    def _extract_generic_mortgage_data(self, data: str) -> List[MortgageDataPoint]:
        """Generic extraction for any data source"""
        mortgage_data = []
        
        # Generic pattern matching for mortgage data
        loan_amounts = self._extract_by_pattern(data, 'loan_amount', self.patterns['loan_amount'])
        interest_rates = self._extract_by_pattern(data, 'interest_rate', self.patterns['interest_rate'])
        loan_terms = self._extract_by_pattern(data, 'loan_term', self.patterns['loan_term'])
        property_values = self._extract_by_pattern(data, 'property_value', self.patterns['property_value'])
        loan_dates = self._extract_by_pattern(data, 'loan_date', self.patterns['loan_date'])
        
        # Extract loan types
        loan_types = self._extract_loan_types(data)
        
        # Create data points
        data_points = []
        
        max_count = max(
            len(loan_amounts),
            len(interest_rates),
            len(loan_terms),
            len(property_values),
            len(loan_dates),
            len(loan_types)
        )
        
        for i in range(max_count):
            loan_amount = self._parse_amount(loan_amounts[i]) if i < len(loan_amounts) else 0.0
            interest_rate = self._parse_percentage(interest_rates[i]) if i < len(interest_rates) else 0.0
            loan_term = self._parse_number(loan_terms[i]) if i < len(loan_terms) else 30
            property_value = self._parse_amount(property_values[i]) if i < len(property_values) else 0.0
            loan_date = loan_dates[i] if i < len(loan_dates) else datetime.now().strftime("%Y-%m-%d")
            loan_type = loan_types[i] if i < len(loan_types) else "Unknown"
            
            # Generate property ID
            property_id = f"PROP-{hash(data + str(i)) % 1000000}"
            
            data_point = MortgageDataPoint(
                property_id=property_id,
                borrower_name="Unknown",
                lender_name="Unknown",
                loan_amount=loan_amount,
                loan_type=loan_type,
                interest_rate=interest_rate,
                loan_term=loan_term,
                loan_date=loan_date,
                property_address="Unknown",
                property_value=property_value,
                status="active",
                data_source="generic",
                scraped_at=datetime.now().isoformat()
            )
            data_points.append(data_point)
        
        return data_points
    
    def _extract_by_pattern(self, text: str, pattern_type: str, patterns: List[str]) -> List[str]:
        """Extract data using specific patterns"""
        results = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            results.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        for result in results:
            if result not in seen:
                seen.add(result)
                unique_results.append(result)
        
        return unique_results
    
    def _extract_loan_types(self, text: str) -> List[str]:
        """Extract loan types from text"""
        loan_types = []
        
        for loan_type, patterns in self.loan_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    loan_types.append(loan_type.capitalize())
                    break  # Only add once per type
        
        return loan_types if loan_types else ["Unknown"]
    
    def _parse_amount(self, text: str) -> float:
        """Parse amount from text"""
        if not text:
            return 0.0
        
        # Extract numbers from text
        numbers = re.findall(r'\d+(?:,\d+)*', text)
        if numbers:
            # Convert first number to float
            number = numbers[0].replace(',', '')
            return float(number)
        
        return 0.0
    
    def _parse_percentage(self, text: str) -> float:
        """Parse percentage from text"""
        if not text:
            return 0.0
        
        # Extract numbers from text
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        if numbers:
            return float(numbers[0])
        
        return 0.0
    
    def _parse_number(self, text: str) -> int:
        """Parse number from text"""
        if not text:
            return 30
        
        # Extract numbers from text
        numbers = re.findall(r'\d+', text)
        if numbers:
            return int(numbers[0])
        
        return 30
    
    def validate_mortgage_data(self, data_point: MortgageDataPoint) -> bool:
        """Validate that the mortgage data point is reasonable"""
        # Basic validation
        if not data_point.property_id or data_point.property_id == "Unknown":
            return False
        
        if data_point.loan_amount <= 0:
            return False
            
        if data_point.loan_term <= 0:
            return False
            
        # Validate date format
        try:
            if data_point.loan_date and data_point.loan_date != "Unknown":
                datetime.strptime(data_point.loan_date, "%Y-%m-%d")
        except ValueError:
            # If date format is wrong, try to parse it
            pass
            
        return True
    
    def enhance_data_quality(self, data_points: List[MortgageDataPoint]) -> List[MortgageDataPoint]:
        """Enhance data quality using learned patterns and similarity analysis"""
        enhanced_data = []
        
        # Create a vector representation of data points for similarity analysis
        text_representations = []
        for data_point in data_points:
            # Create a text representation for vectorization
            text = f"{data_point.borrower_name} {data_point.lender_name} {data_point.property_address} {data_point.loan_type}"
            text_representations.append(text)
        
        # Vectorize the text representations
        if len(text_representations) > 1:
            try:
                vectors = self.vectorizer.fit_transform(text_representations)
                
                # Compare similarity between data points
                for i, vector in enumerate(vectors):
                    # Find similar data points
                    similarities = cosine_similarity(vector, vectors)
                    similar_indices = [j for j, sim in enumerate(similarities[0]) if sim > self.similarity_threshold and j != i]
                    
                    # If we found similar points, potentially merge or enhance
                    if similar_indices:
                        # For now, just enhance the quality score
                        data_points[i].quality_score = min(100.0, data_points[i].quality_score + 10 if data_points[i].quality_score else 10)
            
            except Exception as e:
                logger.warning(f"Error in similarity analysis: {str(e)}")
        
        # Apply quality checks and enhancements
        for data_point in data_points:
            if self.validate_mortgage_data(data_point):
                enhanced_data.append(data_point)
        
        return enhanced_data
    
    def learn_patterns(self, training_data: List[MortgageDataPoint]):
        """Learn from training data to improve future extractions"""
        for data_point in training_data:
            # Store patterns for future learning
            pattern_key = f"{data_point.loan_type}_{data_point.status}"
            self.learning_patterns[pattern_key].append(data_point)
        
        self.logger.info(f"Learned patterns from {len(training_data)} data points")
    
    def get_data_quality_score(self, data_point: MortgageDataPoint) -> float:
        """Calculate quality score for the data point"""
        score = 0.0
        
        # Score based on completeness
        if data_point.property_id != "Unknown":
            score += 20
        if data_point.borrower_name != "Unknown":
            score += 15
        if data_point.lender_name != "Unknown":
            score += 15
        if data_point.loan_amount > 0:
            score += 20
        if data_point.property_address != "Unknown":
            score += 15
        if data_point.loan_date != "Unknown":
            score += 10
        if data_point.loan_type != "Unknown":
            score += 10
            
        return min(score, 100.0)
    
    def get_data_insights(self, data_points: List[MortgageDataPoint]) -> Dict[str, Any]:
        """Get insights from the data points"""
        insights = {
            "total_records": len(data_points),
            "average_loan_amount": 0.0,
            "average_interest_rate": 0.0,
            "average_loan_term": 0.0,
            "loan_type_distribution": {},
            "status_distribution": {},
            "property_value_range": [0.0, 0.0]
        }
        
        if not data_points:
            return insights
        
        # Calculate averages
        total_loan_amount = sum(dp.loan_amount for dp in data_points if dp.loan_amount > 0)
        total_interest_rate = sum(dp.interest_rate for dp in data_points if dp.interest_rate > 0)
        total_loan_term = sum(dp.loan_term for dp in data_points if dp.loan_term > 0)
        
        insights["average_loan_amount"] = total_loan_amount / len(data_points) if data_points else 0.0
        insights["average_interest_rate"] = total_interest_rate / len(data_points) if data_points else 0.0
        insights["average_loan_term"] = total_loan_term / len(data_points) if data_points else 0.0
        
        # Calculate distributions
        loan_types = [dp.loan_type for dp in data_points]
        statuses = [dp.status for dp in data_points]
        
        insights["loan_type_distribution"] = {lt: loan_types.count(lt) for lt in set(loan_types)}
        insights["status_distribution"] = {s: statuses.count(s) for s in set(statuses)}
        
        # Property value range
        property_values = [dp.property_value for dp in data_points if dp.property_value > 0]
        if property_values:
            insights["property_value_range"] = [min(property_values), max(property_values)]
        
        return insights
    
    def process_mortgage_data(self, raw_data: str, source_type: str,
                            integration: "MortgageNeuralNetworkIntegration" = None) -> List[MortgageDataPoint]:
        """
        Process mortgage data using the neural network and optionally integrate with database
        
        Args:
            raw_data: Raw data to process
            source_type: Type of source (property_records, court_records, etc.)
            integration: Optional integration object for database operations
            
        Returns:
            List of processed MortgageDataPoint objects
        """
        # Extract data using the neural network
        data_points = self.extract_mortgage_data(raw_data, source_type)
        
        # Enhance data quality
        enhanced_data = self.enhance_data_quality(data_points)
        
        # Add quality scores
        for data_point in enhanced_data:
            data_point.quality_score = self.get_data_quality_score(data_point)
        
        # If integration is provided, store the data
        if integration:
            # Store in database
            for data_point in enhanced_data:
                integration.store_processed_data(data_point)
        
        return enhanced_data
