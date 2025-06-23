import streamlit as st
import os
from datetime import datetime
from database_manager import DatabaseManager
from models import AppConfig, FileMetadata, FileType
import mimetypes

# Configure page
st.set_page_config(
    page_title=f"{AppConfig.PAGE_TITLE} - Upload",
    page_icon=AppConfig.PAGE_ICON,
    layout=AppConfig.LAYOUT
)

# Initialize database manager
@st.cache_resource
def get_database_manager():
    return DatabaseManager(AppConfig.DATABASE_PATH)

db_manager = get_database_manager()

def get_file_type(uploaded_file):
    """Get MIME type of uploaded file"""
    if uploaded_file.type:
        return uploaded_file.type
    
    # Fallback to guessing based on extension
    mime_type, _ = mimetypes.guess_type(uploaded_file.name)
    return mime_type if mime_type else "application/octet-stream"

def validate_file(uploaded_file):
    """Validate uploaded file"""
    errors = []
    
    # Check file size
    if uploaded_file.size > AppConfig.MAX_FILE_SIZE:
        errors.append(f"File size ({uploaded_file.size / (1024*1024):.2f} MB) exceeds maximum allowed size ({AppConfig.MAX_FILE_SIZE / (1024*1024):.0f} MB)")
    
    # Check file extension
    file_extension = uploaded_file.name.lower().split('.')[-1] if '.' in uploaded_file.name else ''
    if file_extension and not AppConfig.is_extension_allowed(file_extension):
        errors.append(f"File extension '.{file_extension}' is not allowed")
    
    return errors

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

def main():
    st.title("📁 File Upload System")
    st.markdown("---")
    
    # Sidebar with information
    with st.sidebar:
        st.header("ℹ️ Upload Information")
        st.write(f"**Maximum file size:** {AppConfig.MAX_FILE_SIZE / (1024*1024):.0f} MB")
        
        st.subheader("📋 Allowed File Types")
        for category, extensions in AppConfig.ALLOWED_EXTENSIONS.items():
            with st.expander(f"{category.title()}"):
                st.write(", ".join([f".{ext}" for ext in extensions]))
        
        # Database stats
        st.subheader("📊 Database Statistics")
        stats = db_manager.get_database_stats()
        st.metric("Total Files", stats['total_files'])
        st.metric("Total Storage", format_file_size(stats['total_size']))
    
    # Main upload interface
    st.header("📤 Upload Files")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        accept_multiple_files=True,
        help="You can upload multiple files at once"
    )
    
    if uploaded_files:
        st.subheader("📋 Selected Files")
        
        # Display selected files with validation
        valid_files = []
        total_size = 0
        
        for uploaded_file in uploaded_files:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            
            with col1:
                st.write(f"**{uploaded_file.name}**")
            
            with col2:
                st.write(format_file_size(uploaded_file.size))
                total_size += uploaded_file.size
            
            with col3:
                file_type = get_file_type(uploaded_file)
                st.write(file_type.split('/')[0].title())
            
            with col4:
                # Validate file
                validation_errors = validate_file(uploaded_file)
                if validation_errors:
                    st.error("❌ Invalid")
                    for error in validation_errors:
                        st.error(f"• {error}")
                else:
                    st.success("✅ Valid")
                    valid_files.append(uploaded_file)
        
        # Summary
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Files", len(uploaded_files))
        with col2:
            st.metric("Valid Files", len(valid_files))
        with col3:
            st.metric("Total Size", format_file_size(total_size))
        
        # Upload button
        if valid_files:
            st.markdown("---")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🚀 Upload Files", type="primary", use_container_width=True):
                    upload_files(valid_files)
        else:
            if uploaded_files:  # Files selected but none valid
                st.error("❌ No valid files to upload. Please check the validation errors above.")

def upload_files(valid_files):
    """Upload valid files to database"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    success_count = 0
    error_count = 0
    
    for i, uploaded_file in enumerate(valid_files):
        # Update progress
        progress = (i + 1) / len(valid_files)
        progress_bar.progress(progress)
        status_text.text(f"Uploading {uploaded_file.name}... ({i + 1}/{len(valid_files)})")
        
        try:
            # Read file data
            file_data = uploaded_file.read()
            file_type = get_file_type(uploaded_file)
            
            # Save to database
            success = db_manager.save_file(
                file_data=file_data,
                filename=uploaded_file.name,
                file_type=file_type,
                file_size=uploaded_file.size
            )
            
            if success:
                success_count += 1
            else:
                error_count += 1
                
        except Exception as e:
            st.error(f"Error uploading {uploaded_file.name}: {str(e)}")
            error_count += 1
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    # Show results
    st.markdown("---")
    st.subheader("📊 Upload Results")
    
    col1, col2 = st.columns(2)
    with col1:
        if success_count > 0:
            st.success(f"✅ Successfully uploaded {success_count} file(s)")
    
    with col2:
        if error_count > 0:
            st.error(f"❌ Failed to upload {error_count} file(s)")
    
    # Show success message and option to view files
    if success_count > 0:
        st.success("🎉 Upload completed successfully!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📁 View Uploaded Files", type="secondary"):
                st.switch_page("view_files.py")
        
        with col2:
            if st.button("🔄 Upload More Files", type="secondary"):
                st.rerun()

if __name__ == "__main__":
    main()