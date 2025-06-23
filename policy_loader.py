import os
from langchain.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings

def load_policy_documents(folder_path: str):
    documents = []
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if file_name.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        elif file_name.endswith(".docx"):
            loader = Docx2txtLoader(file_path)
        elif file_name.endswith(".txt"):
            loader = TextLoader(file_path)
        else:
            continue
        docs = loader.load()
        documents.extend(docs)
    return documents

def chunk_documents(documents, chunk_size=1000, chunk_overlap=150):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(documents)

def build_policy_vectorstore(folder_path: str, persist_path="policy_index"):
    documents = load_policy_documents(folder_path)
    chunks = chunk_documents(documents)
    embedding = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(chunks, embedding)
    vectorstore.save_local(persist_path)
    return vectorstore

def load_policy_vectorstore(persist_path="policy_index"):
    embedding = OpenAIEmbeddings()
    return FAISS.load_local(persist_path, embedding)