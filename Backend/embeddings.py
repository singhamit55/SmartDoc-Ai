import os
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

load_dotenv()

def get_embeddings():
    """Returns the local HuggingFace embedding model for much faster searching."""
    
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        # Optionally, you can specify model_kwargs={'device': 'cpu'} 
    )
