from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

class FileType(Enum):
    """Enumeration of supported file types for better categorization"""
    IMAGE = "image"
    TEXT = "text"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    ARCHIVE = "archive"
    AUDIO = "audio"
    VIDEO = "video"
    PDF = "pdf"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    UNKNOWN = "unknown"

@dataclass
class FileMetadata:
    """Data class for file metadata"""
    id: Optional[int]
    filename: str
    file_type: str
    file_size: int
    upload_date: datetime
    
    @property
    def size_kb(self) -> float:
        """Return file size in KB"""
        return round(self.file_size / 1024, 2)
    
    @property
    def size_mb(self) -> float:
        """Return file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def file_extension(self) -> str:
        """Extract file extension from filename"""
        return self.filename.lower().split('.')[-1] if '.' in self.filename else ''
    
    @property
    def category(self) -> FileType:
        """Categorize file based on type and extension"""
        file_type_lower = self.file_type.lower()
        extension = self.file_extension
        
        # Image files
        if file_type_lower.startswith('image/') or extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff']:
            return FileType.IMAGE
        
        # Text files
        elif (file_type_lower.startswith('text/') or 
              extension in ['txt', 'md', 'py', 'js', 'html', 'css', 'sql', 'log', 'ini', 'cfg', 'conf']):
            return FileType.TEXT
        
        # CSV files
        elif file_type_lower == 'text/csv' or extension == 'csv':
            return FileType.CSV
        
        # JSON files
        elif file_type_lower == 'application/json' or extension == 'json':
            return FileType.JSON
        
        # XML files
        elif file_type_lower in ['application/xml', 'text/xml'] or extension in ['xml', 'xsl', 'xsd']:
            return FileType.XML
        
        # Excel/Spreadsheet files
        elif extension in ['xlsx', 'xls'] or 'spreadsheet' in file_type_lower:
            return FileType.SPREADSHEET
        
        # Archive files
        elif extension in ['zip', 'rar', '7z'] or 'zip' in file_type_lower:
            return FileType.ARCHIVE
        
        # PDF files
        elif file_type_lower == 'application/pdf' or extension == 'pdf':
            return FileType.PDF
        
        # Document files
        elif (extension in ['doc', 'docx', 'ppt', 'pptx'] or 
              'document' in file_type_lower or 'presentation' in file_type_lower):
            return FileType.DOCUMENT
        
        # Audio files
        elif file_type_lower.startswith('audio/') or extension in ['mp3', 'wav', 'ogg', 'm4a', 'flac']:
            return FileType.AUDIO
        
        # Video files
        elif file_type_lower.startswith('video/') or extension in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm']:
            return FileType.VIDEO
        
        else:
            return FileType.UNKNOWN

@dataclass
class DatabaseStats:
    """Data class for database statistics"""
    total_files: int
    total_size: int
    file_types: List[tuple]
    
    @property
    def total_size_mb(self) -> float:
        """Return total size in MB"""
        return round(self.total_size / (1024 * 1024), 2)
    
    @property
    def average_file_size(self) -> float:
        """Return average file size in bytes"""
        return self.total_size / self.total_files if self.total_files > 0 else 0
    
    @property
    def file_type_distribution(self) -> Dict[str, int]:
        """Return file type distribution as dictionary"""
        return {file_type: count for file_type, count in self.file_types}

class DatabaseSchema:
    """Database schema configuration"""
    
    # Table definitions
    FILES_TABLE = """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_data BLOB NOT NULL,
            UNIQUE(filename, upload_date)
        )
    """
    
    # Index definitions for better performance
    INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_filename ON files(filename)",
        "CREATE INDEX IF NOT EXISTS idx_file_type ON files(file_type)",
        "CREATE INDEX IF NOT EXISTS idx_upload_date ON files(upload_date)",
        "CREATE INDEX IF NOT EXISTS idx_file_size ON files(file_size)"
    ]
    
    # Common queries
    QUERIES = {
        'insert_file': '''
            INSERT INTO files (filename, file_type, file_size, file_data)
            VALUES (?, ?, ?, ?)
        ''',
        'select_all_files': '''
            SELECT id, filename, file_type, file_size, upload_date
            FROM files
            ORDER BY upload_date DESC
        ''',
        'select_file_data': '''
            SELECT filename, file_type, file_data
            FROM files
            WHERE id = ?
        ''',
        'delete_file': '''
            DELETE FROM files
            WHERE id = ?
        ''',
        'count_files': '''
            SELECT COUNT(*) FROM files
        ''',
        'total_size': '''
            SELECT SUM(file_size) FROM files
        ''',
        'file_types_distribution': '''
            SELECT file_type, COUNT(*) as count
            FROM files
            GROUP BY file_type
            ORDER BY count DESC
        ''',
        'search_files': '''
            SELECT id, filename, file_type, file_size, upload_date
            FROM files
            WHERE filename LIKE ? OR file_type LIKE ?
            ORDER BY upload_date DESC
        ''',
        'files_by_date_range': '''
            SELECT id, filename, file_type, file_size, upload_date
            FROM files
            WHERE upload_date BETWEEN ? AND ?
            ORDER BY upload_date DESC
        ''',
        'large_files': '''
            SELECT id, filename, file_type, file_size, upload_date
            FROM files
            WHERE file_size > ?
            ORDER BY file_size DESC
        '''
    }

class AppConfig:
    """Application configuration"""
    
    # Database settings
    DATABASE_PATH = 'files_database.db'
    
    # File upload settings
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {
        'images': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff'],
        'text': ['txt', 'md', 'py', 'js', 'html', 'css', 'sql', 'log', 'ini', 'cfg', 'conf'],
        'documents': ['pdf', 'doc', 'docx', 'ppt', 'pptx'],
        'spreadsheets': ['xlsx', 'xls', 'csv'],
        'data': ['json', 'xml', 'csv'],
        'archives': ['zip', 'rar', '7z'],
        'media': ['mp3', 'wav', 'ogg', 'm4a', 'flac', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm']
    }
    
    # UI settings
    PAGE_TITLE = "File Upload System"
    PAGE_ICON = "📁"
    LAYOUT = "wide"
    
    # Preview settings
    MAX_TEXT_PREVIEW_SIZE = 10000  # 10KB
    MAX_PREVIEW_LINES = 1000
    DEFAULT_CSV_PREVIEW_ROWS = 100
    
    # Display settings
    ITEMS_PER_PAGE = 20
    
    @classmethod
    def get_all_allowed_extensions(cls) -> List[str]:
        """Get all allowed file extensions as a flat list"""
        extensions = []
        for ext_list in cls.ALLOWED_EXTENSIONS.values():
            extensions.extend(ext_list)
        return extensions
    
    @classmethod
    def is_extension_allowed(cls, extension: str) -> bool:
        """Check if a file extension is allowed"""
        return extension.lower() in cls.get_all_allowed_extensions()
    
    @classmethod
    def get_category_for_extension(cls, extension: str) -> Optional[str]:
        """Get the category for a given file extension"""
        extension = extension.lower()
        for category, extensions in cls.ALLOWED_EXTENSIONS.items():
            if extension in extensions:
                return category
        return None