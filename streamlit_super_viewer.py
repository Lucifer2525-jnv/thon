import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import base64
from PIL import Image
import io
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import zipfile
import tempfile
import os

def get_files_from_db():
    """Retrieve all files from database"""
    try:
        conn = sqlite3.connect('files_database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, file_type, file_size, upload_date 
            FROM files 
            ORDER BY upload_date DESC
        ''')
        
        files = cursor.fetchall()
        conn.close()
        return files
    except Exception as e:
        st.error(f"Error fetching files: {str(e)}")
        return []

def get_file_data(file_id):
    """Get specific file data from database"""
    try:
        conn = sqlite3.connect('files_database.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT filename, file_type, file_data FROM files WHERE id = ?', (file_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result
    except Exception as e:
        st.error(f"Error fetching file data: {str(e)}")
        return None

def delete_file(file_id):
    """Delete a file from database"""
    try:
        conn = sqlite3.connect('files_database.db')
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error deleting file: {str(e)}")
        return False

def render_file_content(filename, file_type, file_data):
    """Render file content based on file type"""
    
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    
    # IMAGE FILES
    if file_type.startswith('image/') or file_extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff']:
        try:
            image = Image.open(io.BytesIO(file_data))
            st.image(image, caption=filename, use_column_width=True)
            
            # Image info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Format:** {image.format}")
            with col2:
                st.write(f"**Size:** {image.size[0]} x {image.size[1]}")
            with col3:
                st.write(f"**Mode:** {image.mode}")
                
        except Exception as e:
            st.error(f"Error displaying image: {str(e)}")
    
    # TEXT FILES
    elif (file_type.startswith('text/') or 
          file_extension in ['txt', 'md', 'py', 'js', 'html', 'css', 'sql', 'log', 'ini', 'cfg', 'conf']):
        try:
            # Try different encodings
            text_content = None
            encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']
            
            for encoding in encodings:
                try:
                    text_content = file_data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if text_content:
                # Determine language for syntax highlighting
                language = 'text'
                if file_extension in ['py']: language = 'python'
                elif file_extension in ['js']: language = 'javascript'
                elif file_extension in ['html']: language = 'html'
                elif file_extension in ['css']: language = 'css'
                elif file_extension in ['sql']: language = 'sql'
                elif file_extension in ['json']: language = 'json'
                elif file_extension in ['xml']: language = 'xml'
                elif file_extension in ['md']: language = 'markdown'
                
                # Display content with syntax highlighting
                st.code(text_content, language=language)
                
                # File statistics
                lines = text_content.split('\n')
                st.write(f"**Lines:** {len(lines)} | **Characters:** {len(text_content)} | **Words:** {len(text_content.split())}")
            else:
                st.error("Could not decode text file with any supported encoding")
                
        except Exception as e:
            st.error(f"Error displaying text file: {str(e)}")
    
    # CSV FILES
    elif file_type == 'text/csv' or file_extension == 'csv':
        try:
            df = pd.read_csv(io.BytesIO(file_data))
            
            # Display options
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader("📊 Data Preview")
            with col2:
                show_full = st.checkbox("Show all rows", value=False)
            
            # Display dataframe
            if show_full:
                st.dataframe(df, use_container_width=True)
            else:
                st.dataframe(df.head(100), use_container_width=True)
                if len(df) > 100:
                    st.info(f"Showing first 100 rows of {len(df)} total rows")
            
            # Dataset statistics
            st.subheader("📈 Dataset Statistics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Rows", len(df))
                st.metric("Columns", len(df.columns))
            
            with col2:
                st.write("**Column Types:**")
                for col, dtype in df.dtypes.items():
                    st.write(f"• {col}: {dtype}")
            
            with col3:
                st.write("**Missing Values:**")
                missing = df.isnull().sum()
                for col, count in missing.items():
                    if count > 0:
                        st.write(f"• {col}: {count}")
                if missing.sum() == 0:
                    st.write("✅ No missing values")
            
            # Show basic statistics for numerical columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                st.subheader("🔢 Numerical Statistics")
                st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                    
        except Exception as e:
            st.error(f"Error displaying CSV file: {str(e)}")
    
    # JSON FILES
    elif file_type == 'application/json' or file_extension == 'json':
        try:
            json_content = json.loads(file_data.decode('utf-8'))
            
            # Display options
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader("📄 JSON Content")
            with col2:
                view_mode = st.selectbox("View Mode", ["Pretty JSON", "Raw Text", "Tree View"])
            
            if view_mode == "Pretty JSON":
                st.json(json_content)
            elif view_mode == "Raw Text":
                st.code(json.dumps(json_content, indent=2), language='json')
            else:  # Tree View
                st.write("**JSON Structure:**")
                def display_json_tree(obj, level=0):
                    indent = "  " * level
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if isinstance(value, (dict, list)):
                                st.write(f"{indent}📁 **{key}** ({type(value).__name__})")
                                display_json_tree(value, level + 1)
                            else:
                                st.write(f"{indent}📄 **{key}**: {type(value).__name__}")
                    elif isinstance(obj, list):
                        st.write(f"{indent}📋 Array with {len(obj)} items")
                        if len(obj) > 0:
                            display_json_tree(obj[0], level + 1)
                
                display_json_tree(json_content)
                
        except Exception as e:
            st.error(f"Error displaying JSON file: {str(e)}")
    
    # XML FILES
    elif file_type in ['application/xml', 'text/xml'] or file_extension in ['xml', 'xsl', 'xsd']:
        try:
            xml_content = file_data.decode('utf-8')
            
            # Display options
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader("📄 XML Content")
            with col2:
                view_mode = st.selectbox("View Mode", ["Formatted XML", "Raw XML", "Tree Structure"])
            
            if view_mode == "Formatted XML":
                # Pretty print XML
                try:
                    root = ET.fromstring(xml_content)
                    pretty_xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
                    st.code(pretty_xml, language='xml')
                except:
                    st.code(xml_content, language='xml')
            elif view_mode == "Raw XML":
                st.code(xml_content, language='xml')
            else:  # Tree Structure
                try:
                    root = ET.fromstring(xml_content)
                    st.write("**XML Tree Structure:**")
                    
                    def display_xml_tree(element, level=0):
                        indent = "  " * level
                        st.write(f"{indent}📁 **{element.tag}**")
                        if element.text and element.text.strip():
                            st.write(f"{indent}  📝 Text: {element.text.strip()[:100]}...")
                        for child in element:
                            display_xml_tree(child, level + 1)
                    
                    display_xml_tree(root)
                except Exception as e:
                    st.error(f"Error parsing XML structure: {str(e)}")
                    
        except Exception as e:
            st.error(f"Error displaying XML file: {str(e)}")
    
    # EXCEL FILES
    elif file_extension in ['xlsx', 'xls'] or 'spreadsheet' in file_type:
        try:
            # Read Excel file with all sheets
            excel_data = pd.read_excel(io.BytesIO(file_data), sheet_name=None)
            
            st.subheader("📊 Excel Workbook Viewer")
            
            # Workbook overview
            sheet_names = list(excel_data.keys())
            st.info(f"📋 **Workbook contains {len(sheet_names)} sheet(s):** {', '.join(sheet_names)}")
            
            # Sheet selection
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_sheet = st.selectbox("🔍 Select Sheet to View:", sheet_names, key="excel_sheet_selector")
            with col2:
                view_mode = st.selectbox("View Mode:", ["Full View", "Preview (100 rows)", "Summary Only"])
            
            if selected_sheet:
                df = excel_data[selected_sheet]
                
                # Sheet header with info
                st.markdown(f"### 📄 Sheet: **{selected_sheet}**")
                
                # Sheet statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📊 Rows", f"{len(df):,}")
                with col2:
                    st.metric("📋 Columns", len(df.columns))
                with col3:
                    st.metric("📈 Data Cells", f"{df.count().sum():,}")
                with col4:
                    memory_usage = df.memory_usage(deep=True).sum()
                    st.metric("💾 Memory", f"{memory_usage/1024:.1f} KB")
                
                # Display options
                if view_mode == "Summary Only":
                    # Show only summary information
                    st.subheader("📈 Data Summary")
                    
                    # Column information
                    col_info = []
                    for col in df.columns:
                        col_data = {
                            'Column': col,
                            'Type': str(df[col].dtype),
                            'Non-Null Count': df[col].count(),
                            'Null Count': df[col].isnull().sum(),
                            'Unique Values': df[col].nunique()
                        }
                        
                        # Add sample values for non-numeric columns
                        if df[col].dtype == 'object':
                            unique_vals = df[col].dropna().unique()[:3]
                            col_data['Sample Values'] = ', '.join([str(v) for v in unique_vals])
                        
                        col_info.append(col_data)
                    
                    summary_df = pd.DataFrame(col_info)
                    st.dataframe(summary_df, use_container_width=True)
                    
                else:
                    # Show actual data
                    st.subheader("📋 Sheet Data")
                    
                    # Display controls
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        show_index = st.checkbox("Show Row Numbers", value=True)
                    with col2:
                        if len(df) > 1000:
                            st.warning(f"⚠️ Large dataset ({len(df):,} rows). Consider using Preview mode for better performance.")
                    
                    # Display dataframe based on view mode
                    if view_mode == "Preview (100 rows)":
                        display_df = df.head(100)
                        st.dataframe(display_df, use_container_width=True, hide_index=not show_index)
                        if len(df) > 100:
                            st.info(f"📝 Showing first 100 rows of {len(df):,} total rows")
                    else:  # Full View
                        st.dataframe(df, use_container_width=True, hide_index=not show_index)
                
                # Data Analysis Section
                st.markdown("---")
                st.subheader("🔍 Data Analysis")
                
                # Analysis tabs
                analysis_tab1, analysis_tab2, analysis_tab3 = st.tabs(["📊 Column Info", "📈 Numeric Stats", "🔍 Data Quality"])
                
                with analysis_tab1:
                    # Column information
                    st.write("**Column Details:**")
                    for i, col in enumerate(df.columns):
                        with st.expander(f"📋 {col} ({df[col].dtype})"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Non-null values:** {df[col].count():,}")
                                st.write(f"**Null values:** {df[col].isnull().sum():,}")
                                st.write(f"**Unique values:** {df[col].nunique():,}")
                            with col2:
                                if df[col].dtype in ['object']:
                                    # Show most common values for text columns
                                    top_values = df[col].value_counts().head(5)
                                    st.write("**Most common values:**")
                                    for val, count in top_values.items():
                                        st.write(f"• {val}: {count}")
                                elif df[col].dtype in ['int64', 'float64']:
                                    # Show basic stats for numeric columns
                                    st.write(f"**Min:** {df[col].min()}")
                                    st.write(f"**Max:** {df[col].max()}")
                                    st.write(f"**Mean:** {df[col].mean():.2f}")
                
                with analysis_tab2:
                    # Numeric statistics
                    numeric_cols = df.select_dtypes(include=['number']).columns
                    if len(numeric_cols) > 0:
                        st.write("**Statistical Summary for Numeric Columns:**")
                        st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                        
                        # Correlation matrix for numeric columns
                        if len(numeric_cols) > 1:
                            st.write("**Correlation Matrix:**")
                            corr_matrix = df[numeric_cols].corr()
                            st.dataframe(corr_matrix, use_container_width=True)
                    else:
                        st.info("No numeric columns found for statistical analysis.")
                
                with analysis_tab3:
                    # Data quality assessment
                    st.write("**Data Quality Report:**")
                    
                    # Missing values analysis
                    missing_data = df.isnull().sum()
                    missing_percent = (missing_data / len(df)) * 100
                    
                    quality_df = pd.DataFrame({
                        'Column': df.columns,
                        'Missing Count': missing_data.values,
                        'Missing %': missing_percent.values,
                        'Data Type': [str(dtype) for dtype in df.dtypes],
                        'Unique Values': [df[col].nunique() for col in df.columns]
                    })
                    
                    st.dataframe(quality_df, use_container_width=True)
                    
                    # Overall quality metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_cells = len(df) * len(df.columns)
                        missing_cells = df.isnull().sum().sum()
                        completeness = ((total_cells - missing_cells) / total_cells) * 100
                        st.metric("📊 Data Completeness", f"{completeness:.1f}%")
                    
                    with col2:
                        duplicate_rows = df.duplicated().sum()
                        st.metric("🔄 Duplicate Rows", duplicate_rows)
                    
                    with col3:
                        empty_cols = sum(df[col].isnull().all() for col in df.columns)
                        st.metric("📋 Empty Columns", empty_cols)
                
                # Export options
                st.markdown("---")
                st.subheader("💾 Export Options")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Export current sheet as CSV
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download as CSV",
                        data=csv_data,
                        file_name=f"{selected_sheet}.csv",
                        mime="text/csv"
                    )
                
                with col2:
                    # Export summary as CSV
                    if 'summary_df' in locals():
                        summary_csv = summary_df.to_csv(index=False)
                        st.download_button(
                            label="📊 Download Summary",
                            data=summary_csv,
                            file_name=f"{selected_sheet}_summary.csv",
                            mime="text/csv"
                        )
                
                with col3:
                    # Original Excel download
                    st.download_button(
                        label="📗 Download Original Excel",
                        data=file_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
        except Exception as e:
            st.error(f"Error displaying Excel file: {str(e)}")
            st.info("💡 **Tip:** Make sure the file is a valid Excel file (.xlsx or .xls)")
            
            # Try to show basic file info even if Excel reading fails
            st.write("**File Information:**")
            st.write(f"• File size: {len(file_data):,} bytes")
            st.write(f"• File type: {file_type}")
            st.write(f"• File extension: .{file_extension}")
    
    # ZIP FILES
    elif file_extension in ['zip', 'rar', '7z'] or 'zip' in file_type:
        try:
            st.subheader("📦 Archive Contents")
            
            with zipfile.ZipFile(io.BytesIO(file_data), 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                st.write(f"**Files in archive:** {len(file_list)}")
                
                # Display file list
                for file in file_list:
                    file_info = zip_ref.getinfo(file)
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"📄 {file}")
                    with col2:
                        st.write(f"{file_info.file_size} bytes")
                    with col3:
                        st.write(f"{file_info.compress_size} compressed")
                        
        except Exception as e:
            st.error(f"Error reading archive: {str(e)}")
    
    # PDF FILES
    elif file_type == 'application/pdf' or file_extension == 'pdf':
        st.subheader("📄 PDF Document")
        st.info("PDF preview requires additional libraries. Use the download button to view the full PDF.")
        
        # PDF info
        st.write(f"**File Size:** {len(file_data):,} bytes")
        
        # Create download link
        b64_data = base64.b64encode(file_data).decode()
        href = f'data:application/pdf;base64,{b64_data}'
        st.markdown(
            f'<a href="{href}" download="{filename}" target="_blank"><button style="background-color:#FF6B6B;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;">📄 Open PDF in New Tab</button></a>',
            unsafe_allow_html=True
        )
    
    # WORD DOCUMENTS
    elif file_extension in ['doc', 'docx'] or 'document' in file_type:
        st.subheader("📝 Word Document")
        st.info("Word document preview requires additional libraries. Use the download button to view the document.")
        st.write(f"**File Size:** {len(file_data):,} bytes")
    
    # POWERPOINT FILES
    elif file_extension in ['ppt', 'pptx'] or 'presentation' in file_type:
        st.subheader("📊 PowerPoint Presentation")
        st.info("PowerPoint preview requires additional libraries. Use the download button to view the presentation.")
        st.write(f"**File Size:** {len(file_data):,} bytes")
    
    # AUDIO FILES
    elif file_type.startswith('audio/') or file_extension in ['mp3', 'wav', 'ogg', 'm4a', 'flac']:
        st.subheader("🎵 Audio File")
        
        # Create temporary file for audio playback
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as tmp_file:
                tmp_file.write(file_data)
                tmp_file_path = tmp_file.name
            
            # Display audio player
            st.audio(file_data, format=f'audio/{file_extension}')
            
            # Cleanup
            os.unlink(tmp_file_path)
            
        except Exception as e:
            st.error(f"Error playing audio: {str(e)}")
        
        st.write(f"**File Size:** {len(file_data):,} bytes")
    
    # VIDEO FILES
    elif file_type.startswith('video/') or file_extension in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm']:
        st.subheader("🎬 Video File")
        
        try:
            # Display video player
            st.video(file_data)
        except Exception as e:
            st.error(f"Error playing video: {str(e)}")
        
        st.write(f"**File Size:** {len(file_data):,} bytes")
    
    # UNKNOWN FILE TYPES
    else:
        st.subheader("📎 File Information")
        st.info(f"**File Type:** {file_type}")
        st.info(f"**File Extension:** .{file_extension}")
        st.write(f"**File Size:** {len(file_data):,} bytes")
        
        # Try to display as text if it's small enough
        if len(file_data) < 10000:  # Less than 10KB
            st.subheader("🔍 Raw Content Preview")
            try:
                text_content = file_data.decode('utf-8')
                st.code(text_content[:1000], language='text')
                if len(text_content) > 1000:
                    st.info("Showing first 1000 characters...")
            except:
                st.write("Binary file - cannot display as text")
        else:
            st.write("File is too large for content preview. Use the download button to access the file.")

def main():
    st.set_page_config(
        page_title="File Viewer System",
        page_icon="👁️",
        layout="wide"
    )
    
    st.title("👁️ File Viewer System")
    st.markdown("---")
    
    # Get files from database
    files = get_files_from_db()
    
    if not files:
        st.info("📂 No files found in the database. Upload some files first using the upload script!")
        return
    
    # Sidebar for file selection
    st.sidebar.header("📁 Available Files")
    
    # Convert to DataFrame for better display
    files_df = pd.DataFrame(files, columns=['ID', 'Filename', 'Type', 'Size (bytes)', 'Upload Date'])
    files_df['Size (KB)'] = (files_df['Size (bytes)'] / 1024).round(2)
    files_df['Upload Date'] = pd.to_datetime(files_df['Upload Date']).dt.strftime('%Y-%m-%d %H:%M')
    
    # File selection
    selected_file_id = st.sidebar.selectbox(
        "Select a file to view:",
        options=[None] + [f[0] for f in files],
        format_func=lambda x: "Choose a file..." if x is None else next(f[1] for f in files if f[0] == x),
        key="file_selector"
    )
    
    # Display files table
    st.header("📋 Files Database")
    display_df = files_df[['Filename', 'Type', 'Size (KB)', 'Upload Date']].copy()
    st.dataframe(display_df, use_container_width=True)
    
    # File viewer section
    if selected_file_id:
        st.markdown("---")
        st.header("📖 File Viewer")
        
        # Get file data
        file_data_result = get_file_data(selected_file_id)
        
        if file_data_result:
            filename, file_type, file_data = file_data_result
            
            # File info header
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.subheader(f"📄 {filename}")
            with col2:
                # Download button
                b64_data = base64.b64encode(file_data).decode()
                href = f'data:application/octet-stream;base64,{b64_data}'
                st.markdown(
                    f'<a href="{href}" download="{filename}"><button style="background-color:#4CAF50;color:white;padding:8px 16px;border:none;border-radius:4px;cursor:pointer;">⬇️ Download</button></a>',
                    unsafe_allow_html=True
                )
            with col3:
                # Delete button
                if st.button("🗑️ Delete", key=f"delete_{selected_file_id}"):
                    if delete_file(selected_file_id):
                        st.success("File deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete file!")
            
            st.write(f"**File Type:** {file_type}")
            st.write(f"**File Size:** {len(file_data):,} bytes")
            
            st.markdown("---")
            
            # Render file content
            st.subheader("📄 File Content Preview")
            render_file_content(filename, file_type, file_data)
            
        else:
            st.error("Failed to load file data!")
    
    # Database statistics
    st.markdown("---")
    st.header("📊 Database Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Files", len(files))
    
    with col2:
        total_size = sum(f[3] for f in files)
        st.metric("Total Storage", f"{total_size:,} bytes")
    
    with col3:
        # Most common file type
        file_types = [f[2] for f in files]
        if file_types:
            most_common = max(set(file_types), key=file_types.count)
            st.metric("Most Common Type", most_common)
    
    # File type distribution
    if files:
        st.subheader("📈 File Type Distribution")
        type_counts = {}
        for f in files:
            file_type = f[2]
            type_counts[file_type] = type_counts.get(file_type, 0) + 1
        
        chart_df = pd.DataFrame(list(type_counts.items()), columns=['File Type', 'Count'])
        st.bar_chart(chart_df.set_index('File Type'))

if __name__ == "__main__":
    main()