import streamlit as st
import sqlite3
import os
from datetime import datetime

# Database setup
def init_db():
    """Initialize the database and create files table if it doesn't exist"""
    conn = sqlite3.connect('files_database.db')
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

def save_file_to_db(file_data, filename, file_type, file_size):
    """Save uploaded file to database"""
    try:
        conn = sqlite3.connect('files_database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO files (filename, file_type, file_size, file_data)
            VALUES (?, ?, ?, ?)
        ''', (filename, file_type, file_size, file_data))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error saving file: {str(e)}")
        return False

def main():
    st.set_page_config(
        page_title="File Upload System",
        page_icon="📁",
        layout="wide"
    )
    
    # Initialize database
    init_db()
    
    st.title("📁 File Upload System")
    st.markdown("---")
    
    # File upload section
    st.header("Upload Your Files")
    
            uploaded_files = st.file_uploader(
        "Choose files to upload",
        accept_multiple_files=True,
        help="Upload any file type! Supported previews: Images (PNG, JPG, GIF), Text files (TXT, PY, JS, HTML, CSS, MD), Data (CSV, JSON, XML, XLSX), Archives (ZIP), Audio/Video (MP3, MP4), PDFs, and more!"
    )
    
    if uploaded_files:
        st.subheader("Files to Upload:")
        
        for uploaded_file in uploaded_files:
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"**{uploaded_file.name}**")
            with col2:
                st.write(f"{uploaded_file.type}")
            with col3:
                file_size = len(uploaded_file.read())
                uploaded_file.seek(0)  # Reset file pointer
                st.write(f"{file_size:,} bytes")
        
        st.markdown("---")
        
        if st.button("Upload All Files", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            success_count = 0
            total_files = len(uploaded_files)
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f'Uploading {uploaded_file.name}...')
                
                # Read file data
                file_data = uploaded_file.read()
                file_size = len(file_data)
                
                # Save to database
                if save_file_to_db(file_data, uploaded_file.name, uploaded_file.type, file_size):
                    success_count += 1
                
                # Update progress
                progress_bar.progress((i + 1) / total_files)
            
            progress_bar.empty()
            status_text.empty()
            
            if success_count == total_files:
                st.success(f"✅ Successfully uploaded {success_count} file(s)!")
            else:
                st.warning(f"⚠️ Uploaded {success_count} out of {total_files} files. Some files failed to upload.")
    
    # Statistics section
    st.markdown("---")
    st.header("Database Statistics")
    
    try:
        conn = sqlite3.connect('files_database.db')
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
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Files", total_files)
            st.metric("Total Storage", f"{total_size:,} bytes")
        
        with col2:
            if file_types:
                st.subheader("File Types:")
                for file_type, count in file_types:
                    st.write(f"• **{file_type}**: {count} files")
            else:
                st.write("No files uploaded yet.")
                
    except Exception as e:
        st.error(f"Error fetching statistics: {str(e)}")
    
    # Navigation
    st.markdown("---")
    st.info("💡 **Tip**: After uploading files, use the 'File Viewer' script to view and download your files!")

if __name__ == "__main__":
    main()