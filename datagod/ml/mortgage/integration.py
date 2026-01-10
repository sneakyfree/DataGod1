"""
Mortgage Neural Network Integration Module
This module integrates the neural network with the main application
"""

import logging
from typing import Dict, List, Any
from datagod.ml.mortgage.neural_network import MortgageDataGatheringNeuralNetwork, MortgageDataPoint
from datagod.ml.mortgage.config import MORTGAGE_NN_CONFIG
from datagod.scrapers.mortgage_scraper import MortgageDataScraper
from datagod.models.record import Record
from datagod.models.entity import Entity
from datagod.models.relationship import Relationship
from sqlalchemy.orm import Session
import json

logger = logging.getLogger(__name__)

class MortgageNeuralNetworkIntegration:
    """Integration layer between the neural network and the main application"""
    
    def __init__(self):
        self.neural_network = MortgageDataGatheringNeuralNetwork()
        self.config = MORTGAGE_NN_CONFIG
        self.logger = logging.getLogger(__name__)
        
    def process_mortgage_data(self, raw_data: str, source_type: str, 
                            jurisdiction_id: int = None) -> List[Dict[str, Any]]:
        """
        Process mortgage data through the neural network
        
        Args:
            raw_data: Raw data string to process
            source_type: Type of data source (property_records, court_records, etc.)
            jurisdiction_id: Jurisdiction ID for the data
            
        Returns:
            List of processed mortgage data points
        """
        self.logger.info(f"Processing mortgage data from {source_type}")
        
        # Extract data using the neural network
        extracted_data = self.neural_network.extract_mortgage_data(raw_data, source_type)
        
        # Filter by quality score and convert to dictionaries
        filtered_data = []
        for data_point in extracted_data:
            quality_score = self.neural_network.get_data_quality_score(data_point)
            if quality_score >= self.config.min_data_quality_score:
                data_point.quality_score = quality_score
                filtered_data.append(data_point.__dict__)
        
        self.logger.info(f"Processed {len(filtered_data)} data points with quality score >= {self.config.min_data_quality_score}")
        return filtered_data
    
    def store_processed_data(self, db: Session, processed_data: List[Dict[str, Any]], 
                           jurisdiction_id: int) -> List[Dict[str, Any]]:
        """
        Store processed mortgage data in the database
        
        Args:
            db: Database session
            processed_data: List of processed data points
            jurisdiction_id: Jurisdiction ID for the data
            
        Returns:
            List of stored records
        """
        stored_records = []
        
        for data_point in processed_data:
            try:
                # Create a record from the mortgage data
                record_data = {
                    "jurisdiction_id": jurisdiction_id,
                    "data_source_id": 1,  # Default data source ID
                    "title": f"Mortgage Record - {data_point.get('property_id', 'Unknown')}",
                    "description": f"Mortgage data for property {data_point.get('property_id', 'Unknown')}",
                    "amount": data_point.get('loan_amount', 0.0),
                    "date": data_point.get('loan_date'),
                    "url": f"https://example.com/property/{data_point.get('property_id', 'unknown')}",
                    "data": data_point,
                    "record_type": "mortgage",
                    "status": data_point.get('status', 'active')
                }
                
                # Create the record in the database
                record = Record(**record_data)
                db.add(record)
                db.commit()
                db.refresh(record)
                
                stored_records.append({
                    "record_id": record.id,
                    "property_id": data_point.get('property_id'),
                    "loan_amount": data_point.get('loan_amount'),
                    "status": data_point.get('status'),
                    "quality_score": data_point.get('quality_score', 0)
                })
                
            except Exception as e:
                logger.error(f"Error storing mortgage data: {str(e)}")
                db.rollback()
                continue
        
        return stored_records
    
    def train_neural_network(self, training_data: List[Dict[str, Any]]):
        """
        Train the neural network with new data
        
        Args:
            training_data: List of data points to train on
        """
        self.logger.info(f"Training neural network with {len(training_data)} data points")
        
        # Convert to MortgageDataPoint objects for training
        data_points = []
        for data_point in training_data:
            mortgage_point = MortgageDataPoint(
                property_id=data_point.get('property_id', 'Unknown'),
                borrower_name=data_point.get('borrower_name', 'Unknown'),
                lender_name=data_point.get('lender_name', 'Unknown'),
                loan_amount=data_point.get('loan_amount', 0.0),
                loan_type=data_point.get('loan_type', 'Unknown'),
                interest_rate=data_point.get('interest_rate', 0.0),
                loan_term=data_point.get('loan_term', 30),
                loan_date=data_point.get('loan_date', ''),
                property_address=data_point.get('property_address', 'Unknown'),
                property_value=data_point.get('property_value', 0.0),
                status=data_point.get('status', 'active'),
                data_source=data_point.get('data_source', 'unknown'),
                scraped_at=data_point.get('scraped_at', '')
            )
            data_points.append(mortgage_point)
        
        # Train the neural network
        self.neural_network.learn_patterns(data_points)
        self.logger.info("Neural network training completed")
    
    def get_data_quality_report(self, processed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a quality report for the processed data
        
        Args:
            processed_data: List of processed data points
            
        Returns:
            Quality report dictionary
        """
        if not processed_data:
            return {"total_records": 0, "average_quality_score": 0.0}
        
        total_score = sum(data.get('quality_score', 0) for data in processed_data)
        average_score = total_score / len(processed_data)
        
        return {
            "total_records": len(processed_data),
            "average_quality_score": round(average_score, 2),
            "min_quality_score": min(data.get('quality_score', 0) for data in processed_data),
            "max_quality_score": max(data.get('quality_score', 0) for data in processed_data)
        }
    
    def create_entity_relationships(self, db: Session, processed_data: List[Dict[str, Any]]):
        """
        Create entity relationships in the database
        
        Args:
            db: Database session
            processed_data: List of processed data points
        """
        for data_point in processed_data:
            try:
                # Create entities for borrower and lender if they don't exist
                borrower_name = data_point.get('borrower_name', 'Unknown')
                lender_name = data_point.get('lender_name', 'Unknown')
                
                # Create borrower entity
                borrower_entity = self._create_or_get_entity(db, borrower_name, 'person')
                
                # Create lender entity
                lender_entity = self._create_or_get_entity(db, lender_name, 'company')
                
                # Create property entity
                property_address = data_point.get('property_address', 'Unknown')
                property_entity = self._create_or_get_entity(db, property_address, 'property')
                
                # Create relationships
                self._create_relationship(db, borrower_entity.id, property_entity.id, 'owns')
                self._create_relationship(db, lender_entity.id, property_entity.id, 'lends_to')
                
            except Exception as e:
                logger.error(f"Error creating relationships: {str(e)}")
                db.rollback()
                continue
    
    def _create_or_get_entity(self, db: Session, entity_name: str, entity_type: str) -> Entity:
        """Create or retrieve an entity from the database"""
        # Check if entity already exists
        existing_entity = db.query(Entity).filter(
            Entity.entity_name == entity_name,
            Entity.entity_type == entity_type
        ).first()
        
        if existing_entity:
            return existing_entity
        
        # Create new entity
        new_entity = Entity(
            entity_name=entity_name,
            entity_type=entity_type,
            description=f"{entity_type} entity for {entity_name}"
        )
        db.add(new_entity)
        db.commit()
        db.refresh(new_entity)
        return new_entity
    
    def _create_relationship(self, db: Session, source_entity_id: int, target_entity_id: int, 
                           relationship_type: str):
        """Create a relationship between two entities"""
        relationship = Relationship(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            description=f"{relationship_type} relationship"
        )
        db.add(relationship)
        db.commit()
        return relationship
