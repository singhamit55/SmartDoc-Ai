import os
from langchain_chroma import Chroma

def create_vectorstore(chunks, embedding_model, persist_dir):
    """Create and persist a Chroma vector store."""
    return Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=persist_dir,
    )

def load_vectorstore(embedding_model, persist_dir):
    """Load an existing Chroma vector store."""
    if not os.path.exists(persist_dir) or not os.listdir(persist_dir):
        return None
    return Chroma(
        persist_directory=persist_dir,
        embedding_function=embedding_model,
    )

def delete_document_from_vectorstore(file_path, persist_dir, embedding_model):
    """Deletes all chunks associated with a specific file from the Chroma vector store."""
    if not os.path.exists(persist_dir):
        return
        
    vectorstore = Chroma(
        persist_directory=persist_dir,
        embedding_function=embedding_model,
    )
    
    # Get the underlying chromadb collection
    collection = vectorstore._collection
    
    # Delete where metadata source matches the file path
    # Note: PyPDFLoader usually stores the exact path passed to it in the 'source' metadata
    try:
        collection.delete(where={"source": file_path})
    except Exception as e:
        print(f"Warning: Failed to delete from vectorstore: {e}")
