"""
SQLite Database Module for BMW Vehicle Search
Handles all database operations for storing and retrieving vehicle data
"""
import sqlite3
import pandas as pd
import logging
from typing import Optional, List
from pathlib import Path


class BMWDatabase:
    def __init__(self, db_path: str = "bmw_vehicles.db", logger: Optional[logging.Logger] = None):
        """
        Initialize the BMW database connection
        
        Args:
            db_path: Path to the SQLite database file
            logger: Optional logger instance
        """
        self.db_path = db_path
        self.logger = logger or logging.getLogger(__name__)
        self.conn = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database and tables if they don't exist"""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # Create vehicles table with all required columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                _id TEXT PRIMARY KEY,  -- VIN as primary key
                year INTEGER,
                type TEXT,
                model TEXT,
                trimDescription TEXT,
                stockNumber TEXT,
                interior TEXT,
                exterior TEXT,
                interiorMeta TEXT,
                exteriorMeta TEXT,
                odometer INTEGER,
                vdpUrl TEXT,
                internetPrice REAL,
                msrp REAL,
                labelPrice REAL,
                packageDescriptions TEXT,
                packageOptionDescriptions TEXT,
                nonPackageOptionDescriptions TEXT,
                accessoryDescriptions TEXT,
                distance REAL,
                allCodes TEXT,
                collection_name TEXT,  -- To track which collection (X3, X4, X3_M40i, X4_M40i)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on VIN for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vin ON vehicles(_id)
        """)
        
        # Create index on model and collection for faster filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_collection 
            ON vehicles(model, collection_name)
        """)
        
        self.conn.commit()
        self.logger.info(f"Database initialized: {self.db_path}")
    
    def insert_vehicles(self, df: pd.DataFrame, collection_name: str) -> int:
        """
        Insert vehicles from DataFrame into the database
        
        Args:
            df: DataFrame containing vehicle data
            collection_name: Name of the collection (e.g., 'X3', 'X4', 'X3_M40i', 'X4_M40i')
            
        Returns:
            Number of new vehicles inserted
        """
        if df.empty:
            self.logger.info(f"Collection: {collection_name} -> 0 vehicles (empty)")
            return 0
        
        # Add collection_name column to track which collection this belongs to
        df = df.copy()
        df['collection_name'] = collection_name
        
        cursor = self.conn.cursor()
        inserted_count = 0
        duplicate_count = 0
        
        for _, row in df.iterrows():
            try:
                # Convert row to dict and handle None values
                row_dict = row.to_dict()
                
                # Prepare column names and values
                columns = ', '.join(row_dict.keys())
                placeholders = ', '.join(['?' for _ in row_dict])
                values = tuple(row_dict.values())
                
                # Insert with OR IGNORE to skip duplicates
                cursor.execute(f"""
                    INSERT OR IGNORE INTO vehicles ({columns})
                    VALUES ({placeholders})
                """, values)
                
                if cursor.rowcount > 0:
                    inserted_count += 1
                else:
                    duplicate_count += 1
                    
            except sqlite3.IntegrityError:
                duplicate_count += 1
                continue
        
        self.conn.commit()
        self.logger.info(f"Collection: {collection_name} -> {df.shape[0]} vehicles "
                        f"({inserted_count} new, {duplicate_count} duplicates)")
        
        return inserted_count
    
    def vin_exists(self, vin: str) -> bool:
        """
        Check if a VIN exists in the database
        
        Args:
            vin: Vehicle Identification Number
            
        Returns:
            True if VIN exists, False otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM vehicles WHERE _id = ? LIMIT 1", (vin,))
        return cursor.fetchone() is not None
    
    def vin_exists_in_collections(self, vin: str, collection_names: List[str]) -> bool:
        """
        Check if a VIN exists in any of the specified collections
        
        Args:
            vin: Vehicle Identification Number
            collection_names: List of collection names to search in
            
        Returns:
            True if VIN exists in any collection, False otherwise
        """
        cursor = self.conn.cursor()
        placeholders = ', '.join(['?' for _ in collection_names])
        cursor.execute(f"""
            SELECT 1 FROM vehicles 
            WHERE _id = ? AND collection_name IN ({placeholders})
            LIMIT 1
        """, (vin, *collection_names))
        return cursor.fetchone() is not None
    
    def get_vehicles(self, collection_name: Optional[str] = None, 
                     model: Optional[str] = None) -> pd.DataFrame:
        """
        Retrieve vehicles from the database
        
        Args:
            collection_name: Optional filter by collection name
            model: Optional filter by model
            
        Returns:
            DataFrame containing matching vehicles
        """
        query = "SELECT * FROM vehicles WHERE 1=1"
        params = []
        
        if collection_name:
            query += " AND collection_name = ?"
            params.append(collection_name)
        
        if model:
            query += " AND model = ?"
            params.append(model)
        
        df = pd.read_sql_query(query, self.conn, params=params)
        return df
    
    def get_stats(self) -> dict:
        """
        Get database statistics
        
        Returns:
            Dictionary with counts per collection
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT collection_name, COUNT(*) as count 
            FROM vehicles 
            GROUP BY collection_name
        """)
        
        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = row[1]
        
        return stats
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def get_database(db_path: str = "bmw_vehicles.db") -> BMWDatabase:
    """
    Convenience function to get a database instance
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        BMWDatabase instance
    """
    return BMWDatabase(db_path)


if __name__ == "__main__":
    # Test the database
    print("Testing BMW SQLite Database...")
    print("-" * 50)
    
    with BMWDatabase("test_bmw.db") as db:
        print("\n✓ Database created and initialized")
        
        # Test with sample data
        sample_data = pd.DataFrame([
            {
                '_id': 'TEST123456789',
                'year': 2023,
                'type': 'Used',
                'model': 'X4',
                'trimDescription': 'xDrive30i',
                'stockNumber': 'TEST001',
                'interior': 'Black Sensatec',
                'exterior': 'Alpine White',
                'interiorMeta': 'Black',
                'exteriorMeta': 'White',
                'odometer': 15000,
                'vdpUrl': 'https://example.com/vehicle',
                'internetPrice': 45000,
                'msrp': 50000,
                'labelPrice': 48000,
                'packageDescriptions': 'Premium Package',
                'packageOptionDescriptions': '',
                'nonPackageOptionDescriptions': '',
                'accessoryDescriptions': '',
                'distance': 25.5,
                'allCodes': ''
            }
        ])
        
        # Test insert
        db.insert_vehicles(sample_data, 'X4')
        
        # Test duplicate insert
        db.insert_vehicles(sample_data, 'X4')
        
        # Test VIN lookup
        exists = db.vin_exists('TEST123456789')
        print(f"\nVIN exists: {exists}")
        
        # Test stats
        stats = db.get_stats()
        print(f"\nDatabase stats: {stats}")
    
    print("\n✓ All tests passed!")
    
    # Clean up test database
    import os
    if os.path.exists("test_bmw.db"):
        os.remove("test_bmw.db")
        print("✓ Test database cleaned up")

