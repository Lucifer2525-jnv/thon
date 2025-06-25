import os
import re
import hashlib
import sqlite3
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from datetime import datetime

@dataclass
class DocumentChunk:
    chunk_id: str
    document_path: str
    document_title: str
    chunk_index: int
    chunk_type: str  # 'heading', 'paragraph', 'code', 'list', 'table'
    content: str
    raw_content: str  # preserves original markdown formatting
    heading_hierarchy: str  # e.g., "Introduction > Setup > Prerequisites"
    metadata: Dict[str, Any]
    word_count: int
    char_count: int
    created_at: str

class ConfluenceChunker:
    def __init__(self, db_path: str = "confluence_chunks.db"):
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Initialize SQLite database with chunks table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_chunks (
                chunk_id TEXT PRIMARY KEY,
                document_path TEXT NOT NULL,
                document_title TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_type TEXT NOT NULL,
                content TEXT NOT NULL,
                raw_content TEXT NOT NULL,
                heading_hierarchy TEXT,
                metadata TEXT,  -- JSON string
                word_count INTEGER,
                char_count INTEGER,
                created_at TEXT,
                UNIQUE(document_path, chunk_index)
            )
        ''')
        
        # Create indexes for better query performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_document_path ON document_chunks(document_path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunk_type ON document_chunks(chunk_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_heading_hierarchy ON document_chunks(heading_hierarchy)')
        
        conn.commit()
        conn.close()
    
    def extract_document_metadata(self, content: str, file_path: str) -> Dict[str, Any]:
        """Extract metadata from document content and file"""
        metadata = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
        }
        
        # Extract title (first H1 or filename)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
        else:
            metadata['title'] = Path(file_path).stem
        
        # Extract all headings for document structure
        headings = re.findall(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
        metadata['headings'] = [{'level': len(h[0]), 'text': h[1].strip()} for h in headings]
        
        # Extract tags/labels (common in Confluence exports)
        tags = re.findall(r'(?:^|\s)#(\w+)', content)
        metadata['tags'] = list(set(tags))
        
        # Count various elements
        metadata['total_headings'] = len(headings)
        metadata['code_blocks'] = len(re.findall(r'```[\s\S]*?```', content))
        metadata['tables'] = len(re.findall(r'\|.*\|', content))
        metadata['links'] = len(re.findall(r'\[.*?\]\(.*?\)', content))
        metadata['images'] = len(re.findall(r'!\[.*?\]\(.*?\)', content))
        
        return metadata
    
    def build_heading_hierarchy(self, headings: List[Dict], current_index: int) -> str:
        """Build hierarchical path for current position in document"""
        if current_index >= len(headings):
            return ""
        
        current_level = headings[current_index]['level']
        hierarchy = [headings[current_index]['text']]
        
        # Look backwards for parent headings
        for i in range(current_index - 1, -1, -1):
            if headings[i]['level'] < current_level:
                hierarchy.insert(0, headings[i]['text'])
                current_level = headings[i]['level']
                if current_level == 1:  # Stop at top level
                    break
        
        return " > ".join(hierarchy)
    
    def smart_chunk_content(self, content: str, doc_metadata: Dict) -> List[Dict]:
        """
        Intelligent chunking strategy that preserves document structure
        """
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_type = 'paragraph'
        current_heading_context = []
        chunk_index = 0
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines but preserve them in chunks
            if not line:
                if current_chunk:
                    current_chunk.append('')
                i += 1
                continue
            
            # Detect content type
            if re.match(r'^#{1,6}\s+', line):
                # Heading - finalize previous chunk and start new one
                if current_chunk:
                    chunks.append(self.create_chunk_dict(
                        current_chunk, current_type, chunk_index, 
                        current_heading_context, doc_metadata
                    ))
                    chunk_index += 1
                
                # Extract heading info
                heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                
                # Update heading context
                current_heading_context = self.update_heading_context(
                    current_heading_context, level, heading_text
                )
                
                current_chunk = [line]
                current_type = 'heading'
                
            elif line.startswith('```'):
                # Code block - handle as single chunk
                if current_chunk and current_type != 'code':
                    chunks.append(self.create_chunk_dict(
                        current_chunk, current_type, chunk_index, 
                        current_heading_context, doc_metadata
                    ))
                    chunk_index += 1
                    current_chunk = []
                
                # Collect entire code block
                code_block = [line]
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_block.append(lines[i])
                    i += 1
                if i < len(lines):
                    code_block.append(lines[i])  # closing ```
                
                chunks.append(self.create_chunk_dict(
                    code_block, 'code', chunk_index, 
                    current_heading_context, doc_metadata
                ))
                chunk_index += 1
                current_chunk = []
                current_type = 'paragraph'
                
            elif re.match(r'^\s*\|.*\|', line):
                # Table row
                if current_type != 'table':
                    if current_chunk:
                        chunks.append(self.create_chunk_dict(
                            current_chunk, current_type, chunk_index, 
                            current_heading_context, doc_metadata
                        ))
                        chunk_index += 1
                    current_chunk = []
                    current_type = 'table'
                current_chunk.append(line)
                
            elif re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
                # List item
                if current_type != 'list':
                    if current_chunk:
                        chunks.append(self.create_chunk_dict(
                            current_chunk, current_type, chunk_index, 
                            current_heading_context, doc_metadata
                        ))
                        chunk_index += 1
                    current_chunk = []
                    current_type = 'list'
                current_chunk.append(line)
                
            else:
                # Regular paragraph
                if current_type != 'paragraph':
                    if current_chunk:
                        chunks.append(self.create_chunk_dict(
                            current_chunk, current_type, chunk_index, 
                            current_heading_context, doc_metadata
                        ))
                        chunk_index += 1
                    current_chunk = []
                    current_type = 'paragraph'
                current_chunk.append(line)
                
                # Check if paragraph is getting too long (split at ~500 words)
                if len(' '.join(current_chunk).split()) > 500:
                    chunks.append(self.create_chunk_dict(
                        current_chunk, current_type, chunk_index, 
                        current_heading_context, doc_metadata
                    ))
                    chunk_index += 1
                    current_chunk = []
            
            i += 1
        
        # Handle remaining content
        if current_chunk:
            chunks.append(self.create_chunk_dict(
                current_chunk, current_type, chunk_index, 
                current_heading_context, doc_metadata
            ))
        
        return chunks
    
    def update_heading_context(self, current_context: List, level: int, text: str) -> List:
        """Update the hierarchical heading context"""
        # Remove headings at same or deeper level
        context = [h for h in current_context if h['level'] < level]
        # Add current heading
        context.append({'level': level, 'text': text})
        return context
    
    def create_chunk_dict(self, chunk_lines: List[str], chunk_type: str, 
                         index: int, heading_context: List, doc_metadata: Dict) -> Dict:
        """Create a structured chunk dictionary"""
        raw_content = '\n'.join(chunk_lines)
        content = raw_content.strip()
        
        # Build heading hierarchy
        hierarchy = " > ".join([h['text'] for h in heading_context])
        
        # Extract chunk-specific metadata
        chunk_metadata = {
            'has_links': bool(re.search(r'\[.*?\]\(.*?\)', content)),
            'has_images': bool(re.search(r'!\[.*?\]\(.*?\)', content)),
            'has_code_inline': bool(re.search(r'`[^`]+`', content)),
            'heading_level': heading_context[-1]['level'] if heading_context else 0,
        }
        
        if chunk_type == 'code':
            # Extract code language
            lang_match = re.match(r'^```(\w+)', content)
            chunk_metadata['code_language'] = lang_match.group(1) if lang_match else 'unknown'
        
        return {
            'chunk_type': chunk_type,
            'content': content,
            'raw_content': raw_content,
            'heading_hierarchy': hierarchy,
            'chunk_metadata': chunk_metadata,
            'word_count': len(content.split()),
            'char_count': len(content),
            'chunk_index': index
        }
    
    def generate_chunk_id(self, doc_path: str, chunk_index: int, content: str) -> str:
        """Generate unique chunk ID"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{Path(doc_path).stem}_{chunk_index}_{content_hash}"
    
    def process_document(self, file_path: str) -> List[DocumentChunk]:
        """Process a single markdown document"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []
        
        # Extract document metadata
        doc_metadata = self.extract_document_metadata(content, file_path)
        
        # Chunk the content
        chunk_dicts = self.smart_chunk_content(content, doc_metadata)
        
        # Create DocumentChunk objects
        chunks = []
        for chunk_dict in chunk_dicts:
            chunk_id = self.generate_chunk_id(
                file_path, chunk_dict['chunk_index'], chunk_dict['content']
            )
            
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_path=file_path,
                document_title=doc_metadata['title'],
                chunk_index=chunk_dict['chunk_index'],
                chunk_type=chunk_dict['chunk_type'],
                content=chunk_dict['content'],
                raw_content=chunk_dict['raw_content'],
                heading_hierarchy=chunk_dict['heading_hierarchy'],
                metadata={**doc_metadata, **chunk_dict['chunk_metadata']},
                word_count=chunk_dict['word_count'],
                char_count=chunk_dict['char_count'],
                created_at=datetime.now().isoformat()
            )
            chunks.append(chunk)
        
        return chunks
    
    def store_chunks(self, chunks: List[DocumentChunk]):
        """Store chunks in SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for chunk in chunks:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO document_chunks 
                    (chunk_id, document_path, document_title, chunk_index, chunk_type,
                     content, raw_content, heading_hierarchy, metadata, word_count,
                     char_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chunk.chunk_id,
                    chunk.document_path,
                    chunk.document_title,
                    chunk.chunk_index,
                    chunk.chunk_type,
                    chunk.content,
                    chunk.raw_content,
                    chunk.heading_hierarchy,
                    json.dumps(chunk.metadata),
                    chunk.word_count,
                    chunk.char_count,
                    chunk.created_at
                ))
            except Exception as e:
                print(f"Error storing chunk {chunk.chunk_id}: {e}")
        
        conn.commit()
        conn.close()
    
    def process_directory(self, directory_path: str, pattern: str = "*.md"):
        """Process all markdown files in a directory"""
        directory = Path(directory_path)
        markdown_files = list(directory.glob(pattern))
        
        total_chunks = 0
        for file_path in markdown_files:
            print(f"Processing: {file_path}")
            chunks = self.process_document(str(file_path))
            if chunks:
                self.store_chunks(chunks)
                total_chunks += len(chunks)
                print(f"  -> Created {len(chunks)} chunks")
        
        print(f"\nTotal chunks created: {total_chunks}")
        return total_chunks
    
    def query_chunks(self, query_type: str = "all", **filters) -> List[Dict]:
        """Query chunks from database with various filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        base_query = """
            SELECT chunk_id, document_path, document_title, chunk_index, chunk_type,
                   content, raw_content, heading_hierarchy, metadata, word_count,
                   char_count, created_at
            FROM document_chunks
        """
        
        conditions = []
        params = []
        
        if query_type == "by_type" and "chunk_type" in filters:
            conditions.append("chunk_type = ?")
            params.append(filters["chunk_type"])
        
        if "document_path" in filters:
            conditions.append("document_path = ?")
            params.append(filters["document_path"])
        
        if "heading_hierarchy" in filters:
            conditions.append("heading_hierarchy LIKE ?")
            params.append(f"%{filters['heading_hierarchy']}%")
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        base_query += " ORDER BY document_path, chunk_index"
        
        cursor.execute(base_query, params)
        results = cursor.fetchall()
        
        # Convert to dictionaries
        columns = [desc[0] for desc in cursor.description]
        chunks = []
        for row in results:
            chunk_dict = dict(zip(columns, row))
            chunk_dict['metadata'] = json.loads(chunk_dict['metadata'])
            chunks.append(chunk_dict)
        
        conn.close()
        return chunks

# Example usage
if __name__ == "__main__":
    # Initialize chunker
    chunker = ConfluenceChunker("confluence_chunks.db")
    
    # Process all markdown files in a directory
    document_directory = "./confluence_docs"  # Update this path
    chunker.process_directory(document_directory)
    
    # Query examples
    print("\n=== Query Examples ===")
    
    # Get all code chunks
    code_chunks = chunker.query_chunks("by_type", chunk_type="code")
    print(f"Found {len(code_chunks)} code chunks")
    
    # Get chunks from specific document
    # doc_chunks = chunker.query_chunks(document_path="./confluence_docs/setup.md")
    # print(f"Found {len(doc_chunks)} chunks in setup.md")
    
    # Get chunks under specific heading
    # heading_chunks = chunker.query_chunks(heading_hierarchy="Installation")
    # print(f"Found {len(heading_chunks)} chunks under Installation sections")