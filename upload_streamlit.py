import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database_manager import DatabaseManager
from models import AppConfig, FileMetadata, FileType, DatabaseStats
import base64
import io
from PIL import Image
import json

# Configure page
st.set_page_config(
    page_title=f"{AppConfig.PAGE_TITLE} - View Files",
    page_icon=AppConfig.PAGE_ICON,
    layout=AppConfig.LAYOUT
)

# Initialize database manager
@st.cache_resource
def get_database_manager():
    return DatabaseManager(AppConfig.DATABASE_PATH)

db_manager = get_database_manager()

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def get_file_category_emoji(file_type):
    """Get emoji for file category"""
    file_type_lower = file_type.lower()
    
    if file_type_lower.startswith('image/'):
        return "🖼️"
    elif file_type_lower.startswith('text/') or 'text' in file_type_lower:
        return "📄"
    elif file_type_lower.startswith('video/'):
        return "🎥"
    elif file_type_lower.startswith('audio/'):
        return "🎵"
    elif 'pdf' in file_type_lower:
        return "📕"
    elif 'spreadsheet' in file_type_lower or 'excel' in file_type_lower:
        return "📊"
    elif 'zip' in file_type_lower or 'archive' in file_type_lower:
        return "🗜️"
    elif 'json' in file_type_lower:
        return "🔧"
    else:
        return "📁"

def create_download_link(file_data, filename, file_type):
    """Create a download link for file data"""
    b64_data = base64.b64encode(file_data).decode()
    href = f'<a href="data:{file_type};base64,{b64_data}" download="{filename}">⬇️ Download</a>'
    return href

@st.cache_data
def load_files_data():
    """Load files data from database with caching"""
    files = db_manager.get_all_files()
    return files

def preview_file_content(file_data, filename, file_type):
    """Preview file content based on file type"""
    try:
        # Image preview
        if file_type.startswith('image/'):
            try:
                image = Image.open(io.BytesIO(file_data))
                st.image(image, caption=filename, use_container_width=True)
                
                # Image info
                st.info(f"**Dimensions:** {image.size[0]} x {image.size[1]} pixels")
                st.info(f"**Mode:** {image.mode}")
            except Exception as e:
                st.error(f"Could not preview image: {str(e)}")
        
        # Text file preview
        elif file_type.startswith('text/') or filename.lower().endswith(('.txt', '.py', '.js', '.html', '.css', '.sql', '.log', '.md')):
            try:
                text_content = file_data.decode('utf-8')
                
                # Limit preview size
                if len(text_content) > AppConfig.MAX_TEXT_PREVIEW_SIZE:
                    text_content = text_content[:AppConfig.MAX_TEXT_PREVIEW_SIZE] + "\n\n... (Content truncated for preview)"
                
                st.code(text_content, language=None)
                st.info(f"**Lines:** {text_content.count(chr(10)) + 1}")
            except UnicodeDecodeError:
                st.warning("Cannot preview: File contains non-text data")
            except Exception as e:
                st.error(f"Could not preview text: {str(e)}")
        
        # JSON preview
        elif file_type == 'application/json' or filename.lower().endswith('.json'):
            try:
                json_content = json.loads(file_data.decode('utf-8'))
                st.json(json_content)
                st.info(f"**Type:** {type(json_content).__name__}")
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                st.error(f"Could not preview JSON: {str(e)}")
        
        # CSV preview
        elif file_type == 'text/csv' or filename.lower().endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(file_data))
                st.dataframe(df.head(AppConfig.DEFAULT_CSV_PREVIEW_ROWS), use_container_width=True)
                st.info(f"**Shape:** {df.shape[0]} rows × {df.shape[1]} columns")
                st.info(f"**Columns:** {', '.join(df.columns.tolist())}")
            except Exception as e:
                st.error(f"Could not preview CSV: {str(e)}")
        
        # PDF preview (basic info only)
        elif file_type == 'application/pdf':
            st.info("📕 PDF file - Download to view content")
            st.info(f"**Size:** {format_file_size(len(file_data))}")
        
        # Archive preview (basic info only)
        elif 'zip' in file_type.lower() or filename.lower().endswith(('.zip', '.rar', '.7z')):
            st.info("🗜️ Archive file - Download to extract content")
            st.info(f"**Size:** {format_file_size(len(file_data))}")
        
        # Media files (basic info only)
        elif file_type.startswith(('audio/', 'video/')):
            media_type = "🎵 Audio" if file_type.startswith('audio/') else "🎥 Video"
            st.info(f"{media_type} file - Download to play")
            st.info(f"**Size:** {format_file_size(len(file_data))}")
        
        else:
            st.info("📁 Binary file - Download to view content")
            st.info(f"**Size:** {format_file_size(len(file_data))}")
    
    except Exception as e:
        st.error(f"Error previewing file: {str(e)}")

def main():
    st.title("📁 File Management System")
    st.markdown("---")
    
    # Sidebar with filters and stats
    with st.sidebar:
        st.header("🔍 Filters & Search")
        
        # Search functionality
        search_term = st.text_input("Search files", placeholder="Enter filename...")
        
        # File type filter
        all_files = load_files_data()
        if all_files:
            file_types = list(set([file[2] for file in all_files]))
            selected_file_type = st.selectbox("Filter by file type", ["All"] + file_types)
        else:
            selected_file_type = "All"
        
        # Date range filter
        st.subheader("📅 Date Range")
        date_filter = st.selectbox("Filter by date", [
            "All time",
            "Last 24 hours",
            "Last 7 days",
            "Last 30 days",
            "Custom range"
        ])
        
        date_from = None
        date_to = None
        
        if date_filter == "Custom range":
            col1, col2 = st.columns(2)
            with col1:
                date_from = st.date_input("From")
            with col2:
                date_to = st.date_input("To")
        elif date_filter != "All time":
            now = datetime.now()
            if date_filter == "Last 24 hours":
                date_from = now - timedelta(days=1)
            elif date_filter == "Last 7 days":
                date_from = now - timedelta(days=7)
            elif date_filter == "Last 30 days":
                date_from = now - timedelta(days=30)
        
        # Database statistics
        st.markdown("---")
        st.subheader("📊 Database Stats")
        stats = db_manager.get_database_stats()
        st.metric("Total Files", stats['total_files'])
        st.metric("Total Storage", format_file_size(stats['total_size']))
        
        # File type distribution
        if stats['file_types']:
            st.subheader("📋 File Types")
            for file_type, count in stats['file_types'][:5]:  # Show top 5
                st.write(f"{get_file_category_emoji(file_type)} {file_type.split('/')[-1]}: {count}")
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["📋 File List", "📊 Analytics", "🛠️ Management"])
    
    with tab1:
        st.header("📋 All Files")
        
        # Load and filter files
        files = load_files_data()
        
        if not files:
            st.info("📭 No files found in the database. Upload some files to get started!")
            if st.button("📤 Go to Upload", type="primary"):
                st.switch_page("upload_files.py")
            return
        
        # Apply filters
        filtered_files = files
        
        # Search filter
        if search_term:
            filtered_files = [f for f in filtered_files if search_term.lower() in f[1].lower()]
        
        # File type filter
        if selected_file_type != "All":
            filtered_files = [f for f in filtered_files if f[2] == selected_file_type]
        
        # Date filter
        if date_from:
            date_from_str = date_from.strftime('%Y-%m-%d')
            filtered_files = [f for f in filtered_files if f[4] >= date_from_str]
        
        if date_to:
            date_to_str = date_to.strftime('%Y-%m-%d')
            filtered_files = [f for f in filtered_files if f[4] <= date_to_str]
        
        st.write(f"Found {len(filtered_files)} file(s)")
        
        # Pagination
        items_per_page = AppConfig.ITEMS_PER_PAGE
        total_pages = (len(filtered_files) + items_per_page - 1) // items_per_page
        
        if total_pages > 1:
            page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            filtered_files = filtered_files[start_idx:end_idx]
        
        # Display files
        for file_info in filtered_files:
            file_id, filename, file_type, file_size, upload_date = file_info
            
            with st.expander(f"{get_file_category_emoji(file_type)} {filename}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**File ID:** {file_id}")
                    st.write(f"**Type:** {file_type}")
                    st.write(f"**Size:** {format_file_size(file_size)}")
                    st.write(f"**Upload Date:** {upload_date}")
                
                with col2:
                    # Download button
                    file_data_result = db_manager.get_file_data(file_id)
                    if file_data_result:
                        _, _, file_data = file_data_result
                        download_link = create_download_link(file_data, filename, file_type)
                        st.markdown(download_link, unsafe_allow_html=True)
                    
                    # Delete button
                    if st.button(f"🗑️ Delete", key=f"delete_{file_id}"):
                        if db_manager.delete_file(file_id):
                            st.success("File deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete file!")
                
                # Preview section
                if st.button(f"👀 Preview", key=f"preview_{file_id}"):
                    if file_data_result:
                        st.markdown("### 👀 File Preview")
                        preview_file_content(file_data, filename, file_type)
    
    with tab2:
        st.header("📊 File Analytics")
        
        if not all_files:
            st.info("No data available for analytics")
            return
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(all_files, columns=['ID', 'Filename', 'File Type', 'File Size', 'Upload Date'])
        df['Upload Date'] = pd.to_datetime(df['Upload Date'])
        df['File Category'] = df['File Type'].apply(lambda x: x.split('/')[0])
        
        # File size distribution
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 File Size Distribution")
            size_bins = ['< 1KB', '1KB-100KB', '100KB-1MB', '1MB-10MB', '> 10MB']
            size_counts = [
                len(df[df['File Size'] < 1024]),
                len(df[(df['File Size'] >= 1024) & (df['File Size'] < 100*1024)]),
                len(df[(df['File Size'] >= 100*1024) & (df['File Size'] < 1024*1024)]),
                len(df[(df['File Size'] >= 1024*1024) & (df['File Size'] < 10*1024*1024)]),
                len(df[df['File Size'] >= 10*1024*1024])
            ]
            
            size_df = pd.DataFrame({'Size Range': size_bins, 'Count': size_counts})
            st.bar_chart(size_df.set_index('Size Range'))
        
        with col2:
            st.subheader("📋 File Type Distribution")
            type_counts = df['File Category'].value_counts()
            st.bar_chart(type_counts)
        
        # Upload timeline
        st.subheader("📅 Upload Timeline")
        df['Upload Date Only'] = df['Upload Date'].dt.date
        daily_uploads = df.groupby('Upload Date Only').size()
        st.line_chart(daily_uploads)
        
        # Summary statistics
        st.subheader("📈 Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Files", len(df))
        with col2:
            st.metric("Average File Size", format_file_size(df['File Size'].mean()))
        with col3:
            st.metric("Largest File", format_file_size(df['File Size'].max()))
        with col4:
            st.metric("Total Storage", format_file_size(df['File Size'].sum()))
    
    with tab3:
        st.header("🛠️ Database Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🧹 Maintenance")
            
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.cache_data.clear()
                st.success("Data cache cleared!")
                st.rerun()
            
            if st.button("🗑️ Cleanup Database", use_container_width=True):
                if db_manager.cleanup_database():
                    st.success("Database optimized successfully!")
                else:
                    st.error("Database cleanup failed!")
        
        with col2:
            st.subheader("⚠️ Danger Zone")
            
            st.warning("These actions cannot be undone!")
            
            # Bulk delete by file type
            if all_files:
                file_types = list(set([file[2] for file in all_files]))
                delete_file_type = st.selectbox("Delete all files of type:", ["Select..."] + file_types)
                
                if delete_file_type != "Select...":
                    files_to_delete = [f for f in all_files if f[2] == delete_file_type]
                    st.write(f"This will delete {len(files_to_delete)} file(s)")
                    
                    if st.button(f"🗑️ Delete All {delete_file_type}", type="secondary"):
                        deleted_count = 0
                        for file_info in files_to_delete:
                            if db_manager.delete_file(file_info[0]):
                                deleted_count += 1
                        
                        st.success(f"Deleted {deleted_count} file(s)")
                        st.rerun()

if __name__ == "__main__":
    main()