import sqlite3
import os
from datetime import datetime
from typing import List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all database operations for the file upload system"""
    
    def __init__(self, db_path: str = 'files_database.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self) -> None:
        """Initialize the database and create files table if it doesn't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_data BLOB NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
    
    def save_file(self, file_data: bytes, filename: str, file_type: str, file_size: int) -> bool:
        """Save uploaded file to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO files (filename, file_type, file_size, file_data)
                VALUES (?, ?, ?, ?)
            ''', (filename, file_type, file_size, file_data))
            
            conn.commit()
            conn.close()
            logger.info(f"File '{filename}' saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving file '{filename}': {str(e)}")
            return False
    
    def get_all_files(self) -> List[Tuple]:
        """Retrieve all files metadata from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, filename, file_type, file_size, upload_date
                FROM files
                ORDER BY upload_date DESC
            ''')
            
            files = cursor.fetchall()
            conn.close()
            logger.info(f"Retrieved {len(files)} files from database")
            return files
        except Exception as e:
            logger.error(f"Error fetching files: {str(e)}")
            return []
    
    def get_file_data(self, file_id: int) -> Optional[Tuple[str, str, bytes]]:
        """Get specific file data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT filename, file_type, file_data FROM files WHERE id = ?', (file_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                logger.info(f"Retrieved file data for ID: {file_id}")
            else:
                logger.warning(f"No file found with ID: {file_id}")
            
            return result
        except Exception as e:
            logger.error(f"Error fetching file data for ID {file_id}: {str(e)}")
            return None
    
    def delete_file(self, file_id: int) -> bool:
        """Delete a file from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # First check if file exists
            cursor.execute('SELECT filename FROM files WHERE id = ?', (file_id,))
            file_info = cursor.fetchone()
            
            if not file_info:
                logger.warning(f"No file found with ID: {file_id}")
                conn.close()
                return False
            
            cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
            conn.commit()
            conn.close()
            
            logger.info(f"File '{file_info[0]}' deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting file with ID {file_id}: {str(e)}")
            return False
    
    def get_database_stats(self) -> dict:
        """Get database statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total files count
            cursor.execute("SELECT COUNT(*) FROM files")
            total_files = cursor.fetchone()[0]
            
            # Get total storage used
            cursor.execute("SELECT SUM(file_size) FROM files")
            total_size = cursor.fetchone()[0] or 0
            
            # Get file types distribution
            cursor.execute("SELECT file_type, COUNT(*) FROM files GROUP BY file_type ORDER BY COUNT(*) DESC")
            file_types = cursor.fetchall()
            
            conn.close()
            
            stats = {
                'total_files': total_files,
                'total_size': total_size,
                'file_types': file_types
            }
            
            logger.info("Database statistics retrieved successfully")
            return stats
        except Exception as e:
            logger.error(f"Error fetching database statistics: {str(e)}")
            return {
                'total_files': 0,
                'total_size': 0,
                'file_types': []
            }
    
    def cleanup_database(self) -> bool:
        """Clean up the database (optional maintenance function)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Run VACUUM to optimize database
            cursor.execute("VACUUM")
            
            conn.close()
            logger.info("Database cleanup completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error during database cleanup: {str(e)}")
            return False