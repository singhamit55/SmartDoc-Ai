import os
from langchain_community.document_loaders import PyPDFLoader

def load_pdfs(directory_path="data/documents"):
    """Loads all PDF documents from the specified directory."""
    documents = []
    if not os.path.exists(directory_path):
        print(f"Directory {directory_path} not found.")
        return documents

    for filename in os.listdir(directory_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(directory_path, filename)
            loader = PyPDFLoader(file_path)
            documents.extend(loader.load())
            print(f"Loaded {filename}")
            
    return documents

def load_pdf(file_path: str) -> list:
    """Load a single PDF file and return its documents."""
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    return docs
