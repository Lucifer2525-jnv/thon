import zipfile
import os
from PyPDF2 import PdfReader
from docx import Document

def extract_text(file_path: str) -> str:
    if file_path.endswith(".pdf"):
        return extract_pdf(file_path)
    elif file_path.endswith(".docx"):
        return extract_docx(file_path)
    elif file_path.endswith(".zip"):
        return extract_zip(file_path)
    else:
        return ""

def extract_pdf(file_path):
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        text = f"[Error reading PDF: {e}]"
    return text

def extract_docx(file_path):
    text = ""
    try:
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        text = f"[Error reading DOCX: {e}]"
    return text

def extract_zip(file_path):
    text = ""
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            for name in z.namelist():
                if name.endswith((".txt", ".docx", ".pdf")):
                    z.extract(name, "/tmp")  # extract to temp
                    text += extract_text(os.path.join("/tmp", name))
    except Exception as e:
        text = f"[Error reading ZIP: {e}]"
    return text