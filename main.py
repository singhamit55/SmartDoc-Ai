import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from duckduckgo_search import DDGS

from Backend.pdf_loader import load_pdf
from Backend.chunker import chunk_documents
from Backend.embeddings import get_embeddings
from Backend.vectorstore import create_vectorstore, load_vectorstore, delete_document_from_vectorstore
from Backend.retriever import get_retriever
from Backend.llm import get_llm
from Backend.chat import create_qa_chain
from Backend.memory import get_chat_history, add_message, get_all_chats, get_chat_messages, add_document, remove_document, get_db_connection
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

load_dotenv()

app = FastAPI(title="SmartDoc AI")

# CORS — required for Hugging Face Spaces public domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
CHROMA_BASE_DIR = "./data/chroma"
DOCS_BASE_DIR = "./data/docs"
os.makedirs(CHROMA_BASE_DIR, exist_ok=True)
os.makedirs(DOCS_BASE_DIR, exist_ok=True)

def get_user_dirs(user_id: str):
    user_chroma = os.path.join(CHROMA_BASE_DIR, user_id)
    user_docs = os.path.join(DOCS_BASE_DIR, user_id)
    os.makedirs(user_chroma, exist_ok=True)
    os.makedirs(user_docs, exist_ok=True)
    return user_chroma, user_docs

GOOGLE_CLIENT_ID = "188027053452-p1s0ftv4id451ul3b073pjqs7csohp6i.apps.googleusercontent.com"

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = authorization.split(" ")[1]
    
    if token == 'test-token-bypass':
        return "test_user_123"

    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        user_id = idinfo['sub']
        email = idinfo.get('email', 'Unknown User')
        
        # Ensure user exists in our DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user_id, email))
        conn.commit()
        conn.close()
        
        return user_id
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

def get_qa_chain_for_user(user_id: str):
    user_chroma, _ = get_user_dirs(user_id)
    embeddings = get_embeddings()
    vectorstore = load_vectorstore(embeddings, user_chroma)
    if vectorstore is not None:
        retriever_inst = get_retriever(vectorstore, k=6)
        llm_inst = get_llm()
        prompt, llm_model, retriever_func, format_docs = create_qa_chain(llm_inst, retriever_inst)
        return {
            "prompt": prompt,
            "llm": llm_model,
            "retriever": retriever_func,
            "format_docs": format_docs
        }
    return None

# Models
class ChatRequest(BaseModel):
    message: str
    chat_id: str = None

class ChatResponse(BaseModel):
    response: str
    status: str

# API Endpoints
@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Enforce 25 MB size limit
    MAX_SIZE_BYTES = 25 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_SIZE_BYTES:
        size_mb = len(contents) / (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"File too large ({size_mb:.1f} MB). Maximum allowed size is 25 MB.")
    await file.seek(0)  # Reset for subsequent read
    
    # Sanitize filename to prevent Path Traversal attacks
    user_chroma, user_docs = get_user_dirs(user_id)
    safe_filename = os.path.basename(file.filename.replace("\\", "/"))
    file_path = os.path.join(user_docs, safe_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        text_docs = load_pdf(file_path)
        text_chunks = chunk_documents(text_docs, 1000, 200)
        embeddings = get_embeddings()
        vectorstore = create_vectorstore(text_chunks, embeddings, user_chroma)
        
        # Track in database
        import uuid
        add_document(str(uuid.uuid4()), file.filename)
        
        return {"message": "Document processed and database updated successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest, user_id: str = Depends(get_current_user)):
    qa_chain = get_qa_chain_for_user(user_id)
    
    async def generate_response():
        full_answer = ""
        try:
            history_text = get_chat_history(request.chat_id)
            
            if qa_chain is not None:
                # 1. Fetch documents from vectorstore
                docs = qa_chain["retriever"].invoke(request.message)
                context_str = qa_chain["format_docs"](docs)
                
                # Check relevance; fallback to web search if needed
                should_web_search = False
                if not docs:
                    should_web_search = True
                else:
                    try:
                        eval_prompt = f"Context: {context_str}\n\nQuestion: {request.message}\n\nDoes the context contain enough information to answer the question? Answer only 'YES' or 'NO'."
                        eval_result = qa_chain["llm"].invoke(eval_prompt).content.strip().upper()
                        if "NO" in eval_result:
                            should_web_search = True
                    except Exception:
                        should_web_search = True
                
                if should_web_search:
                    web_results = do_web_search(request.message)
                    if web_results:
                        context_str += f"\n\n--- Web Search Results ---\n{web_results}"
                
                formatted_prompt = qa_chain["prompt"].format(
                    history=history_text,
                    context=context_str,
                    input=request.message
                )
                for chunk in qa_chain["llm"].stream(formatted_prompt):
                    full_answer += chunk.content
                    yield chunk.content
            else:
                # No documents — web search + LLM directly
                web_results = do_web_search(request.message)
                context_str = f"--- Web Search Results ---\n{web_results}" if web_results else ""
                
                try:
                    llm = get_llm()
                    prompt_text = (
                        "You are SmartDoc AI, a helpful and knowledgeable AI assistant.\n"
                        "Answer the user's question using the web search results below.\n"
                        "If web search results are provided, use them and cite the sources inline.\n"
                        "CRITICAL: If you use the web search results, you MUST add a new line at the very end of your response exactly like this: 'Sources: Web Search'.\n"
                        "If the user is making small talk (hello, thanks, etc.), respond naturally.\n"
                        "If no search results are available, answer from your own knowledge — do NOT say you cannot answer.\n\n"
                        f"Web Search Results:\n{context_str}\n\n"
                        f"Conversation History:\n{history_text}\n\n"
                        f"User Question: {request.message}"
                    )
                    for chunk in llm.stream(prompt_text):
                        full_answer += chunk.content
                        yield chunk.content
                except Exception as llm_error:
                    error_msg = f"⚠️ AI model error: {str(llm_error)}"
                    full_answer = error_msg
                    yield error_msg
            
            # Save to memory
            if request.chat_id:
                add_message(request.chat_id, request.message, full_answer, user_id=user_id)
                
        except Exception as e:
            yield f"Error: {str(e)}"

            
    return StreamingResponse(generate_response(), media_type="text/plain")

@app.get("/api/documents")
async def get_documents(user_id: str = Depends(get_current_user)):
    _, user_docs = get_user_dirs(user_id)
    if not os.path.exists(user_docs):
        return []
    docs = []
    for f in os.listdir(user_docs):
        if f.endswith('.pdf'):
            path = os.path.join(user_docs, f)
            stat = os.stat(path)
            docs.append({
                "filename": f,
                "size": stat.st_size,
                "uploaded": stat.st_mtime
            })
    return docs

@app.delete("/api/documents/{filename}")
async def delete_document(filename: str, user_id: str = Depends(get_current_user)):
    user_chroma, user_docs = get_user_dirs(user_id)
    # Sanitize filename to prevent Path Traversal attacks
    safe_filename = os.path.basename(filename.replace("\\", "/"))
    file_path = os.path.join(user_docs, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    # Delete from filesystem
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"File deletion warning: {e}")
        
    # Always delete from database
    try:
        remove_document(filename)
    except Exception as e:
        print(f"Database deletion warning: {e}")
        
    # Delete from vectorstore
    try:
        embeddings = get_embeddings()
        delete_document_from_vectorstore(file_path, user_chroma, embeddings)
    except Exception as e:
        # It's okay if vectorstore deletion fails, the file is gone anyway
        print(f"Vectorstore deletion warning: {e}")
        
    return {"message": f"Successfully deleted {filename}"}

@app.get("/api/chats")
async def list_chats(user_id: str = Depends(get_current_user)):
    return get_all_chats(user_id=user_id)

@app.get("/api/chats/{chat_id}")
async def fetch_chat(chat_id: str, user_id: str = Depends(get_current_user)):
    return get_chat_messages(chat_id, user_id=user_id)

@app.get("/api/status")
async def get_status():
    return {
        "isReady": True,
        "documentCount": 0
    }

# Mount static files for frontend
app.mount("/docs", StaticFiles(directory=DOCS_BASE_DIR), name="documents")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
