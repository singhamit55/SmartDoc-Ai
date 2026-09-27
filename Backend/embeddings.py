import os
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from dotenv import load_dotenv

load_dotenv()

def get_embeddings():
    """Returns the HuggingFace embedding model via the Serverless Inference API."""
    token = os.getenv("HUGGINGFACEHUB_ACCESS_TOKEN")
    if not token:
        print("WARNING: HUGGINGFACEHUB_ACCESS_TOKEN is not set in .env!")
        
    return HuggingFaceEndpointEmbeddings(
        model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        huggingfacehub_api_token=token
    )
