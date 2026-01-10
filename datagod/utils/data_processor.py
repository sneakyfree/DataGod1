import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        self.processing_steps = []
    
    def validate_and_clean(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean data"""
        try:
            # Remove null values
            cleaned_data = {k: v for k, v in data.items() if v is not None}
            
            # Convert data types
            for key, value in cleaned_data.items():
                if isinstance(value, str) and value.lower() in ['null', 'none']:
                    cleaned_data[key] = None
                elif isinstance(value, str) and value.isdigit():
                    cleaned_data[key] = int(value)
                elif isinstance(value, str) and value.replace('.', '').isdigit():
                    cleaned_data[key] = float(value)
            
            return cleaned_data
        except Exception as e:
            logger.error(f"Data validation/cleaning failed: {str(e)}")
            return data
    
    def deduplicate_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate records based on hash"""
        seen_hashes = set()
        unique_records = []
        
        for record in records:
            # Create hash of record data for comparison
            record_str = json.dumps(record, sort_keys=True)
            record_hash = hashlib.md5(record_str.encode(), usedforsecurity=False).hexdigest()
            
            if record_hash not in seen_hashes:
                seen_hashes.add(record_hash)
                unique_records.append(record)
            else:
                logger.info("Duplicate record found and removed")
        
        return unique_records
    
    def enrich_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich data with additional information"""
        try:
            # Add timestamp
            if 'created_at' not in data:
                data['created_at'] = datetime.utcnow().isoformat()
            
            # Add data quality score
            if 'confidence_score' not in data:
                data['confidence_score'] = self._calculate_confidence_score(data)
            
            # Add hash for deduplication
            if 'hash_value' not in data:
                record_str = json.dumps(data, sort_keys=True)
                data['hash_value'] = hashlib.md5(record_str.encode(), usedforsecurity=False).hexdigest()
            
            return data
        except Exception as e:
            logger.error(f"Data enrichment failed: {str(e)}")
            return data
    
    def _calculate_confidence_score(self, data: Dict[str, Any]) -> str:
        """Calculate confidence score based on data completeness"""
        if not data:
            return "Low"
        
        total_fields = len(data)
        filled_fields = sum(1 for v in data.values() if v is not None and v != '')
        
        completeness = filled_fields / total_fields if total_fields > 0 else 0.0
        
        if completeness >= 0.9:
            return "High"
        elif completeness >= 0.7:
            return "Medium"
        else:
            return "Low"
    
    def transform_data(self, data: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """Transform data according to mapping rules"""
        transformed_data = {}
        
        for source_field, target_field in mapping.items():
            if source_field in data:
                transformed_data[target_field] = data[source_field]
        
        return transformed_data
    
    def validate_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data quality metrics"""
        metrics = {
            'completeness': self._calculate_completeness(data),
            'accuracy': self._calculate_accuracy(data),
            'consistency': self._calculate_consistency(data),
            'timeliness': self._calculate_timeliness(data),
            'overall_score': 0.0
        }
        
        # Calculate overall score
        total_score = (
            metrics['completeness'] * 0.3 +
            metrics['accuracy'] * 0.3 +
            metrics['consistency'] * 0.2 +
            metrics['timeliness'] * 0.2
        )
        metrics['overall_score'] = total_score
        
        return metrics
    
    def _calculate_completeness(self, data: Dict[str, Any]) -> float:
        """Calculate completeness score"""
        if not data:
            return 0.0
            
        total_fields = len(data)
        filled_fields = sum(1 for v in data.values() if v is not None and v != '')
        return filled_fields / total_fields if total_fields > 0 else 0.0
    
    def _calculate_accuracy(self, data: Dict[str, Any]) -> float:
        """Calculate accuracy score"""
        # Placeholder - would implement actual accuracy checks
        return 0.95  # Assume 95% accuracy for now
    
    def _calculate_consistency(self, data: Dict[str, Any]) -> float:
        """Calculate consistency score"""
        # Placeholder - would implement actual consistency checks
        return 0.90  # Assume 90% consistency for now
    
    def _calculate_timeliness(self, data: Dict[str, Any]) -> float:
        """Calculate timeliness score"""
        # Placeholder - would implement actual timeliness checks
        return 0.85  # Assume 85% timeliness for now

# Global processor instance
processor = DataProcessor()
