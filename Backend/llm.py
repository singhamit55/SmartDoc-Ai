import os
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from dotenv import load_dotenv

load_dotenv()

AVAILABLE_MODELS = {
    "Qwen 2.5 (Hugging Face)": "Qwen/Qwen2.5-72B-Instruct",
}

def get_llm(model="Qwen/Qwen2.5-72B-Instruct"):
    """
    Returns a ChatHuggingFace instance using the HF Inference API.
    Make sure HUGGINGFACEHUB_ACCESS_TOKEN is set in your .env file.
    """
    token = os.getenv("HUGGINGFACEHUB_ACCESS_TOKEN")
    if not token:
        print("WARNING: HUGGINGFACEHUB_ACCESS_TOKEN is not set in .env!")
        
    llm = HuggingFaceEndpoint(
        repo_id=model,
        temperature=0.3,
        huggingfacehub_api_token=token,
        max_new_tokens=1024,
    )
    return ChatHuggingFace(llm=llm)
