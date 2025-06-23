import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import base64
from PIL import Image
import io

def get_files_from_db():
“”“Retrieve all files from database”””
try:
conn = sqlite3.connect(‘files_database.db’)
cursor = conn.cursor()

```
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
```

def get_file_data(file_id):
“”“Get specific file data from database”””
try:
conn = sqlite3.connect(‘files_database.db’)
cursor = conn.cursor()

```
    cursor.execute('SELECT filename, file_type, file_data FROM files WHERE id = ?', (file_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result
except Exception as e:
    st.error(f"Error fetching file data: {str(e)}")
    return None
```

def delete_file(file_id):
“”“Delete a file from database”””
try:
conn = sqlite3.connect(‘files_database.db’)
cursor = conn.cursor()

```
    cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
    conn.commit()
    conn.close()
    return True
except Exception as e:
    st.error(f"Error deleting file: {str(e)}")
    return False
```

def render_file_content(filename, file_type, file_data):
“”“Render file content based on file type”””

```
if file_type.startswith('image/'):
    # Display images
    try:
        image = Image.open(io.BytesIO(file_data))
        st.image(image, caption=filename, use_column_width=True)
    except Exception as e:
        st.error(f"Error displaying image: {str(e)}")

elif file_type == 'text/plain' or filename.endswith('.txt'):
    # Display text files
    try:
        text_content = file_data.decode('utf-8')
        st.text_area("File Content:", text_content, height=400)
    except Exception as e:
        st.error(f"Error displaying text file: {str(e)}")

elif file_type == 'text/csv' or filename.endswith('.csv'):
    # Display CSV files as dataframe
    try:
        df = pd.read_csv(io.BytesIO(file_data))
        st.dataframe(df, use_container_width=True)
        
        # Show basic statistics
        st.subheader("Dataset Info:")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Rows:** {len(df)}")
            st.write(f"**Columns:** {len(df.columns)}")
        with col2:
            st.write("**Column Types:**")
            for col, dtype in df.dtypes.items():
                st.write(f"• {col}: {dtype}")
                
    except Exception as e:
        st.error(f"Error displaying CSV file: {str(e)}")

elif file_type == 'application/json' or filename.endswith('.json'):
    # Display JSON files
    try:
        import json
        json_content = json.loads(file_data.decode('utf-8'))
        st.json(json_content)
    except Exception as e:
        st.error(f"Error displaying JSON file: {str(e)}")

elif file_type == 'application/pdf':
    # For PDF files, show download option (rendering PDF requires additional libraries)
    st.info("📄 PDF file detected. Click download button below to view the PDF.")
    
else:
    # For other file types, show file info and download option
    st.info(f"📎 File type: {file_type}")
    st.write("This file type cannot be previewed directly. Use the download button below.")
```

def main():
st.set_page_config(
page_title=“File Viewer System”,
page_icon=“👁️”,
layout=“wide”
)

```
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
```

if **name** == “**main**”:
main()