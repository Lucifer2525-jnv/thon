import streamlit as st
import pandas as pd
import io
import base64
from PIL import Image
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Optional
import mimetypes

# Import your custom modules (make sure they're in the same directory)
from database_manager import DatabaseManager
from models import FileMetadata, DatabaseStats, FileType, AppConfig

# Configure Streamlit page
st.set_page_config(
    page_title=AppConfig.PAGE_TITLE,
    page_icon=AppConfig.PAGE_ICON,
    layout=AppConfig.LAYOUT
)

class StreamlitFileManager:
    """Main Streamlit application class for file management"""
    
    def __init__(self):
        self.db_manager = DatabaseManager(AppConfig.DATABASE_PATH)
        
    def run(self):
        """Main application runner"""
        st.title("📁 File Upload & Management System")
        
        # Create tabs for different functionalities
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📤 Upload Files", 
            "📋 View Files", 
            "📊 Analytics", 
            "🔍 Search & Filter",
            "⚙️ Settings"
        ])
        
        with tab1:
            self.upload_files_tab()
        
        with tab2:
            self.view_files_tab()
        
        with tab3:
            self.analytics_tab()
        
        with tab4:
            self.search_filter_tab()
        
        with tab5:
            self.settings_tab()

    def upload_files_tab(self):
        """File upload interface"""
        st.header("Upload Files")
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            accept_multiple_files=True,
            help=f"Maximum file size: {AppConfig.MAX_FILE_SIZE // (1024*1024)}MB"
        )
        
        if uploaded_files:
            # Display upload summary
            st.write(f"**Selected {len(uploaded_files)} file(s) for upload:**")
            
            upload_data = []
            total_size = 0
            
            for file in uploaded_files:
                file_size = len(file.getvalue())
                total_size += file_size
                
                # Check file size
                if file_size > AppConfig.MAX_FILE_SIZE:
                    st.error(f"❌ {file.name}: File too large ({file_size/(1024*1024):.1f}MB)")
                    continue
                
                # Get file extension
                extension = file.name.split('.')[-1].lower() if '.' in file.name else ''
                
                upload_data.append({
                    'Filename': file.name,
                    'Size (KB)': f"{file_size/1024:.1f}",
                    'Type': file.type or 'Unknown',
                    'Extension': extension,
                    'Status': '✅ Ready' if AppConfig.is_extension_allowed(extension) else '⚠️ Unknown type'
                })
            
            # Display upload preview
            if upload_data:
                df = pd.DataFrame(upload_data)
                st.dataframe(df, use_container_width=True)
                
                st.write(f"**Total size:** {total_size/(1024*1024):.2f} MB")
                
                # Upload button
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("🚀 Upload All Files", type="primary"):
                        self.process_file_uploads(uploaded_files)

    def process_file_uploads(self, uploaded_files):
        """Process and save uploaded files"""
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        
        success_count = 0
        error_count = 0
        
        for i, file in enumerate(uploaded_files):
            status_placeholder.text(f"Uploading {file.name}...")
            
            try:
                file_data = file.getvalue()
                file_size = len(file_data)
                file_type = file.type or 'application/octet-stream'
                
                # Save to database
                if self.db_manager.save_file(file_data, file.name, file_type, file_size):
                    success_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                st.error(f"Error uploading {file.name}: {str(e)}")
                error_count += 1
            
            # Update progress
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        # Show results
        status_placeholder.empty()
        progress_bar.empty()
        
        if success_count > 0:
            st.success(f"✅ Successfully uploaded {success_count} file(s)")
        if error_count > 0:
            st.error(f"❌ Failed to upload {error_count} file(s)")
        
        # Refresh the page data
        st.rerun()

    def view_files_tab(self):
        """View and manage uploaded files"""
        st.header("Uploaded Files")
        
        # Get all files
        files_data = self.db_manager.get_all_files()
        
        if not files_data:
            st.info("No files uploaded yet. Go to the Upload tab to add some files!")
            return
        
        # Convert to FileMetadata objects
        files = []
        for file_data in files_data:
            file_id, filename, file_type, file_size, upload_date = file_data
            # Parse datetime string
            upload_datetime = datetime.fromisoformat(upload_date.replace('Z', '+00:00')) if isinstance(upload_date, str) else upload_date
            
            files.append(FileMetadata(
                id=file_id,
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                upload_date=upload_datetime
            ))
        
        # Create DataFrame for display
        df_data = []
        for file in files:
            df_data.append({
                'ID': file.id,
                'Filename': file.filename,
                'Category': file.category.value.title(),
                'Size (KB)': file.size_kb,
                'Size (MB)': file.size_mb,
                'Upload Date': file.upload_date.strftime('%Y-%m-%d %H:%M:%S'),
                'Extension': file.file_extension.upper()
            })
        
        df = pd.DataFrame(df_data)
        
        # Display files table
        st.dataframe(df, use_container_width=True)
        
        # File actions
        st.subheader("File Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # File preview
            selected_id = st.selectbox(
                "Select file to preview:",
                options=[f.id for f in files],
                format_func=lambda x: next(f.filename for f in files if f.id == x)
            )
            
            if st.button("👁️ Preview File"):
                self.preview_file(selected_id)
        
        with col2:
            # File download
            download_id = st.selectbox(
                "Select file to download:",
                options=[f.id for f in files],
                format_func=lambda x: next(f.filename for f in files if f.id == x),
                key="download_select"
            )
            
            if st.button("⬇️ Download File"):
                self.download_file(download_id)
        
        with col3:
            # File deletion
            delete_id = st.selectbox(
                "Select file to delete:",
                options=[f.id for f in files],
                format_func=lambda x: next(f.filename for f in files if f.id == x),
                key="delete_select"
            )
            
            if st.button("🗑️ Delete File", type="secondary"):
                if st.session_state.get('confirm_delete', False):
                    if self.db_manager.delete_file(delete_id):
                        st.success("File deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete file")
                else:
                    st.session_state.confirm_delete = True
                    st.warning("Click again to confirm deletion")

    def preview_file(self, file_id: int):
        """Preview file content"""
        file_data = self.db_manager.get_file_data(file_id)
        
        if not file_data:
            st.error("File not found")
            return
        
        filename, file_type, data = file_data
        
        st.subheader(f"Preview: {filename}")
        
        try:
            # Image preview
            if file_type.startswith('image/'):
                image = Image.open(io.BytesIO(data))
                st.image(image, caption=filename, use_column_width=True)
            
            # Text file preview
            elif file_type.startswith('text/') or filename.endswith(('.txt', '.py', '.md', '.html', '.css', '.js')):
                text_content = data.decode('utf-8', errors='ignore')
                if len(text_content) > AppConfig.MAX_TEXT_PREVIEW_SIZE:
                    text_content = text_content[:AppConfig.MAX_TEXT_PREVIEW_SIZE] + "\n... (truncated)"
                st.code(text_content, language=self.get_language_from_extension(filename))
            
            # CSV preview
            elif filename.endswith('.csv') or file_type == 'text/csv':
                df = pd.read_csv(io.BytesIO(data))
                st.write(f"**Shape:** {df.shape[0]} rows × {df.shape[1]} columns")
                st.dataframe(df.head(AppConfig.DEFAULT_CSV_PREVIEW_ROWS))
            
            # JSON preview
            elif filename.endswith('.json') or file_type == 'application/json':
                json_data = json.loads(data.decode('utf-8'))
                st.json(json_data)
            
            # XML preview
            elif filename.endswith('.xml') or 'xml' in file_type:
                xml_content = data.decode('utf-8', errors='ignore')
                st.code(xml_content, language='xml')
            
            else:
                st.info("Preview not available for this file type")
                st.write(f"**File type:** {file_type}")
                st.write(f"**File size:** {len(data)} bytes")
        
        except Exception as e:
            st.error(f"Error previewing file: {str(e)}")

    def download_file(self, file_id: int):
        """Download file"""
        file_data = self.db_manager.get_file_data(file_id)
        
        if not file_data:
            st.error("File not found")
            return
        
        filename, file_type, data = file_data
        
        st.download_button(
            label=f"📥 Download {filename}",
            data=data,
            file_name=filename,
            mime=file_type
        )

    def analytics_tab(self):
        """Analytics and statistics"""
        st.header("File Analytics")
        
        # Get database stats
        stats_data = self.db_manager.get_database_stats()
        stats = DatabaseStats(
            total_files=stats_data['total_files'],
            total_size=stats_data['total_size'],
            file_types=stats_data['file_types']
        )
        
        if stats.total_files == 0:
            st.info("No files to analyze yet.")
            return
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Files", stats.total_files)
        
        with col2:
            st.metric("Total Size", f"{stats.total_size_mb:.2f} MB")
        
        with col3:
            st.metric("Average File Size", f"{stats.average_file_size/1024:.1f} KB")
        
        with col4:
            largest_type = max(stats.file_types, key=lambda x: x[1])[0] if stats.file_types else "N/A"
            st.metric("Most Common Type", largest_type)
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # File type distribution pie chart
            if stats.file_types:
                fig = px.pie(
                    values=[count for _, count in stats.file_types],
                    names=[file_type for file_type, _ in stats.file_types],
                    title="File Type Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Upload timeline
            files_data = self.db_manager.get_all_files()
            if files_data:
                dates = [datetime.fromisoformat(f[4].replace('Z', '+00:00')) if isinstance(f[4], str) else f[4] for f in files_data]
                df_timeline = pd.DataFrame({'date': dates})
                df_timeline['date'] = pd.to_datetime(df_timeline['date']).dt.date
                timeline_counts = df_timeline.groupby('date').size().reset_index(name='count')
                
                fig = px.line(
                    timeline_counts, 
                    x='date', 
                    y='count',
                    title="Upload Timeline",
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)

    def search_filter_tab(self):
        """Search and filter files"""
        st.header("Search & Filter Files")
        
        # Search inputs
        col1, col2 = st.columns(2)
        
        with col1:
            search_term = st.text_input("🔍 Search by filename:", placeholder="Enter filename...")
        
        with col2:
            file_type_filter = st.selectbox(
                "Filter by file type:",
                options=["All"] + [ft.value for ft in FileType],
                index=0
            )
        
        # Date range filter
        st.subheader("Date Range Filter")
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("From:", value=datetime.now().date() - timedelta(days=30))
        
        with col2:
            end_date = st.date_input("To:", value=datetime.now().date())
        
        # Size filter
        min_size = st.slider("Minimum file size (KB):", 0, 10000, 0)
        
        # Apply filters
        if st.button("🔍 Apply Filters"):
            self.apply_filters(search_term, file_type_filter, start_date, end_date, min_size)

    def apply_filters(self, search_term: str, file_type_filter: str, start_date, end_date, min_size: int):
        """Apply search and filter criteria"""
        files_data = self.db_manager.get_all_files()
        
        if not files_data:
            st.info("No files to filter.")
            return
        
        # Convert to FileMetadata objects and apply filters
        filtered_files = []
        
        for file_data in files_data:
            file_id, filename, file_type, file_size, upload_date = file_data
            upload_datetime = datetime.fromisoformat(upload_date.replace('Z', '+00:00')) if isinstance(upload_date, str) else upload_date
            
            file_meta = FileMetadata(
                id=file_id,
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                upload_date=upload_datetime
            )
            
            # Apply filters
            if search_term and search_term.lower() not in filename.lower():
                continue
            
            if file_type_filter != "All" and file_meta.category.value != file_type_filter:
                continue
            
            if upload_datetime.date() < start_date or upload_datetime.date() > end_date:
                continue
            
            if file_meta.size_kb < min_size:
                continue
            
            filtered_files.append(file_meta)
        
        # Display filtered results
        if filtered_files:
            st.success(f"Found {len(filtered_files)} matching file(s)")
            
            df_data = []
            for file in filtered_files:
                df_data.append({
                    'ID': file.id,
                    'Filename': file.filename,
                    'Category': file.category.value.title(),
                    'Size (KB)': file.size_kb,
                    'Upload Date': file.upload_date.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No files match your search criteria.")

    def settings_tab(self):
        """Application settings and maintenance"""
        st.header("Settings & Maintenance")
        
        # Database maintenance
        st.subheader("Database Maintenance")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🧹 Cleanup Database"):
                if self.db_manager.cleanup_database():
                    st.success("Database cleanup completed successfully!")
                else:
                    st.error("Database cleanup failed!")
        
        with col2:
            if st.button("📊 Refresh Statistics"):
                st.rerun()
        
        # Configuration display
        st.subheader("Current Configuration")
        
        config_info = {
            "Database Path": AppConfig.DATABASE_PATH,
            "Max File Size": f"{AppConfig.MAX_FILE_SIZE // (1024*1024)} MB",
            "Items Per Page": AppConfig.ITEMS_PER_PAGE,
            "Max Preview Size": f"{AppConfig.MAX_TEXT_PREVIEW_SIZE // 1024} KB",
            "Allowed Extensions": len(AppConfig.get_all_allowed_extensions())
        }
        
        for key, value in config_info.items():
            st.write(f"**{key}:** {value}")
        
        # Allowed extensions
        st.subheader("Allowed File Extensions")
        for category, extensions in AppConfig.ALLOWED_EXTENSIONS.items():
            st.write(f"**{category.title()}:** {', '.join(extensions)}")

    @staticmethod
    def get_language_from_extension(filename: str) -> str:
        """Get syntax highlighting language from file extension"""
        extension = filename.split('.')[-1].lower()
        
        language_map = {
            'py': 'python',
            'js': 'javascript',
            'html': 'html',
            'css': 'css',
            'sql': 'sql',
            'json': 'json',
            'xml': 'xml',
            'md': 'markdown',
            'yml': 'yaml',
            'yaml': 'yaml',
            'sh': 'bash',
            'bat': 'batch'
        }
        
        return language_map.get(extension, 'text')

def main():
    """Main application entry point"""
    try:
        app = StreamlitFileManager()
        app.run()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.write("Please check your database connection and file permissions.")

if __name__ == "__main__":
    main()