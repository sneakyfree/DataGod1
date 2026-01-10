"""
Database Manager for DataGod Project
Handles all database operations for the DataGod application
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database operations for the DataGod project."""
    
    def __init__(self, db_path: str = "datagod.db"):
        """
        Initialize the DatabaseManager.
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the database and create tables if they don't exist."""
        try:
            with self.get_connection() as conn:
                # Create jurisdictions table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS jurisdictions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        state TEXT,
                        country TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create data_sources table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS data_sources (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        url TEXT,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create records table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        jurisdiction_id INTEGER,
                        data_source_id INTEGER,
                        title TEXT,
                        description TEXT,
                        amount REAL,
                        date DATE,
                        url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions (id),
                        FOREIGN KEY (data_source_id) REFERENCES data_sources (id)
                    )
                ''')
                
                # Create indexes for better performance
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_records_jurisdiction 
                    ON records(jurisdiction_id)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_records_data_source 
                    ON records(data_source_id)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_records_date 
                    ON records(date)
                ''')
                
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    # Jurisdiction methods
    def create_jurisdiction(self, name: str, state: str = None, country: str = None) -> int:
        """
        Create a new jurisdiction.
        
        Args:
            name (str): Name of the jurisdiction
            state (str): State of the jurisdiction
            country (str): Country of the jurisdiction
            
        Returns:
            int: ID of the created jurisdiction
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT OR IGNORE INTO jurisdictions (name, state, country)
                    VALUES (?, ?, ?)
                ''', (name, state, country))
                
                jurisdiction_id = cursor.lastrowid
                
                # If jurisdiction already exists, get its ID
                if jurisdiction_id == 0:
                    cursor = conn.execute('''
                        SELECT id FROM jurisdictions 
                        WHERE name = ? AND state = ? AND country = ?
                    ''', (name, state, country))
                    result = cursor.fetchone()
                    if result:
                        jurisdiction_id = result['id']
                
                conn.commit()  # Explicitly commit the transaction
                logger.info(f"Created jurisdiction with ID: {jurisdiction_id}")
                return jurisdiction_id
                
        except sqlite3.Error as e:
            logger.error(f"Error creating jurisdiction: {e}")
            raise
    
    def get_jurisdiction(self, jurisdiction_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a jurisdiction by ID.
        
        Args:
            jurisdiction_id (int): ID of the jurisdiction
            
        Returns:
            Dict: Jurisdiction data or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM jurisdictions WHERE id = ?
                ''', (jurisdiction_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Error getting jurisdiction: {e}")
            raise
    
    def get_jurisdiction_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a jurisdiction by name.
        
        Args:
            name (str): Name of the jurisdiction
            
        Returns:
            Dict: Jurisdiction data or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM jurisdictions WHERE name = ?
                ''', (name,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Error getting jurisdiction by name: {e}")
            raise
    
    def get_all_jurisdictions(self) -> List[Dict[str, Any]]:
        """
        Get all jurisdictions.
        
        Returns:
            List[Dict]: List of all jurisdictions
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('SELECT * FROM jurisdictions')
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting all jurisdictions: {e}")
            raise
    
    # Data Source methods
    def create_data_source(self, name: str, url: str = None, description: str = None) -> int:
        """
        Create a new data source.
        
        Args:
            name (str): Name of the data source
            url (str): URL of the data source
            description (str): Description of the data source
            
        Returns:
            int: ID of the created data source
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT OR IGNORE INTO data_sources (name, url, description)
                    VALUES (?, ?, ?)
                ''', (name, url, description))
                
                data_source_id = cursor.lastrowid
                
                # If data source already exists, get its ID
                if data_source_id == 0:
                    cursor = conn.execute('''
                        SELECT id FROM data_sources 
                        WHERE name = ? AND url = ? AND description = ?
                    ''', (name, url, description))
                    result = cursor.fetchone()
                    if result:
                        data_source_id = result['id']
                
                logger.info(f"Created data source with ID: {data_source_id}")
                return data_source_id
                
        except sqlite3.Error as e:
            logger.error(f"Error creating data source: {e}")
            raise
    
    def get_data_source(self, data_source_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a data source by ID.
        
        Args:
            data_source_id (int): ID of the data source
            
        Returns:
            Dict: Data source data or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM data_sources WHERE id = ?
                ''', (data_source_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Error getting data source: {e}")
            raise
    
    def get_all_data_sources(self) -> List[Dict[str, Any]]:
        """
        Get all data sources.
        
        Returns:
            List[Dict]: List of all data sources
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('SELECT * FROM data_sources')
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting all data sources: {e}")
            raise
    
    # Record methods
    def create_record(self, jurisdiction_id: int, data_source_id: int, 
                     title: str, description: str = None, amount: float = None, 
                     date: str = None, url: str = None) -> int:
        """
        Create a new record.
        
        Args:
            jurisdiction_id (int): ID of the jurisdiction
            data_source_id (int): ID of the data source
            title (str): Title of the record
            description (str): Description of the record
            amount (float): Amount of the record
            date (str): Date of the record
            url (str): URL of the record
            
        Returns:
            int: ID of the created record
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    INSERT INTO records 
                    (jurisdiction_id, data_source_id, title, description, amount, date, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    jurisdiction_id,
                    data_source_id,
                    title,
                    description,
                    amount,
                    date,
                    url
                ))
                
                record_id = cursor.lastrowid
                logger.info(f"Created record with ID: {record_id}")
                return record_id
                
        except sqlite3.Error as e:
            logger.error(f"Error creating record: {e}")
            raise
    
    def get_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a record by ID.
        
        Args:
            record_id (int): ID of the record
            
        Returns:
            Dict: Record data or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM records WHERE id = ?
                ''', (record_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Error getting record: {e}")
            raise
    
    def get_records_by_jurisdiction(self, jurisdiction_id: int) -> List[Dict[str, Any]]:
        """
        Get all records for a jurisdiction.
        
        Args:
            jurisdiction_id (int): ID of the jurisdiction
            
        Returns:
            List[Dict]: List of records for the jurisdiction
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM records WHERE jurisdiction_id = ?
                ''', (jurisdiction_id,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting records by jurisdiction: {e}")
            raise
    
    def get_records_by_data_source(self, data_source_id: int) -> List[Dict[str, Any]]:
        """
        Get all records for a data source.
        
        Args:
            data_source_id (int): ID of the data source
            
        Returns:
            List[Dict]: List of records for the data source
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM records WHERE data_source_id = ?
                ''', (data_source_id,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting records by data source: {e}")
            raise
    
    def search_records(self, search_term: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search records by title or description.
        
        Args:
            search_term (str): Term to search for
            limit (int): Maximum number of results
            
        Returns:
            List[Dict]: List of matching records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM records 
                    WHERE title LIKE ? OR description LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (f'%{search_term}%', f'%{search_term}%', limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error searching records: {e}")
            raise
    
    def get_all_records(self) -> List[Dict[str, Any]]:
        """
        Get all records.
        
        Returns:
            List[Dict]: List of all records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('SELECT * FROM records ORDER BY created_at DESC')
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting all records: {e}")
            raise
    
    def update_record(self, record_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update a record.
        
        Args:
            record_id (int): ID of the record to update
            updates (Dict[str, Any]): Dictionary of fields to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                # Build update query dynamically
                set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
                values = list(updates.values()) + [record_id]
                
                query = f"UPDATE records SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                
                cursor = conn.execute(query, values)
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            logger.error(f"Error updating record: {e}")
            raise
    
    def delete_record(self, record_id: int) -> bool:
        """
        Delete a record.
        
        Args:
            record_id (int): ID of the record to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute('DELETE FROM records WHERE id = ?', (record_id,))
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            logger.error(f"Error deleting record: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dict[str, Any]: Statistics about the database
        """
        try:
            with self.get_connection() as conn:
                # Get counts
                jurisdiction_count = conn.execute('SELECT COUNT(*) as count FROM jurisdictions').fetchone()['count']
                data_source_count = conn.execute('SELECT COUNT(*) as count FROM data_sources').fetchone()['count']
                record_count = conn.execute('SELECT COUNT(*) as count FROM records').fetchone()['count']
                
                # Get recent records
                recent_records = conn.execute('''
                    SELECT * FROM records 
                    ORDER BY created_at DESC 
                    LIMIT 5
                ''').fetchall()
                
                return {
                    'jurisdiction_count': jurisdiction_count,
                    'data_source_count': data_source_count,
                    'record_count': record_count,
                    'recent_records': [dict(row) for row in recent_records]
                }
                
        except sqlite3.Error as e:
            logger.error(f"Error getting database statistics: {e}")
            raise

# Create a global instance for easy access
db_manager = DatabaseManager()
