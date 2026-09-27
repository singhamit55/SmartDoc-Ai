---
title: SmartDoc AI
emoji: 🤖
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# 🍃 SmartDoc AI

SmartDoc AI is an intelligent, multi-tenant Document Chat Assistant that leverages Retrieval-Augmented Generation (RAG) to allow users to interact with their PDF documents naturally. Powered by FastAPI and cutting-edge open-source LLMs, it offers a secure, isolated environment where each user's data and vector databases are completely sandboxed.

## ✨ Key Features

- **🧠 Interactive RAG Engine:** Upload complex PDFs and ask contextual questions. The AI semantically searches your documents to provide precise, referenced answers.
- **🌐 Intelligent Web Fallback:** If the answer is not found within your documents, the system automatically falls back to an integrated DuckDuckGo web search to provide up-to-date internet answers.
- **🔒 Multi-Tenant Data Privacy:** Enterprise-grade security through strict multi-tenancy. Every user has their own isolated SQLite chat history, file storage directory, and ChromaDB vector space. No user can ever see another user's data.
- **🛡️ Google OAuth Authentication:** Seamless, secure, and passwordless login using Google Sign-In identity verification.
- **📱 Fully Responsive UI:** A premium, modern, glassmorphic UI that flawlessly adapts to mobile devices via slide-out sidebar drawers and fluid flex layouts.

## 🛠️ Technology Stack

- **Backend Architecture:** Python, FastAPI, Uvicorn
- **AI & Orchestration:** LangChain, Hugging Face Transformers (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`)
- **Language Models (LLM):** DeepSeek (via Hugging Face Serverless Inference API).
- **Vector Database:** ChromaDB (Multi-tenant setup with distinct user collections)
- **Persistent Storage:** SQLite3 (Chat history), Local File System (Documents)
- **Frontend UI:** Vanilla HTML5, CSS3 (Custom Glassmorphism Design), JavaScript, FontAwesome 6

## 📁 System Architecture & Directory Structure

```text
smartdoc-ai/
├── Backend/                 # Core AI and Logic Modules
│   ├── chat.py              # WebSocket/HTTP chat endpoints
│   ├── chunker.py           # Text chunking for optimal RAG context
│   ├── db.py                # Multi-tenant SQLite database operations
│   ├── embeddings.py        # Hugging Face embedding generation
│   ├── llm.py               # Groq LLM integration & prompt engineering
│   ├── memory.py            # LangChain conversational memory
│   ├── pdf_loader.py        # PyPDF2 extraction and OCR setup
│   ├── retriever.py         # Semantic search and Web Search fallback
│   └── vectorstore.py       # User-isolated ChromaDB management
├── frontend/                # Static Web Assets
│   ├── index.html           # Main Chat Interface
│   ├── manage-documents.html# Document Upload & Management Dashboard
│   ├── script.js            # OAuth, API calls, and UI logic
│   └── style.css            # Responsive styles and animations
├── data/                    # Automatically generated storage
│   ├── chroma/              # Isolated Vector DBs (e.g. data/chroma/{user_id}/)
│   └── docs/                # Uploaded PDFs (e.g. data/docs/{user_id}/)
├── main.py                  # FastAPI Application Entrypoint
├── Dockerfile               # Hugging Face Spaces & Container setup
└── requirements.txt         # Python dependencies
```

## 🚀 Setup & Installation (Local)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/singhamit55/SmartDoc-Ai.git
   cd SmartDoc-Ai
   ```

2. **Create a virtual environment & install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   HUGGINGFACEHUB_ACCESS_TOKEN=your_hf_token_here
   ```

4. **Run the Application:**
   ```bash
   python -m uvicorn main:app --reload --port 8000
   ```
   *Visit `http://localhost:8000` in your browser.*

## ☁️ Deployment (Hugging Face Spaces)

This repository includes a ready-to-deploy `Dockerfile` configured for Hugging Face Spaces.
1. Create a new **Docker** Space on Hugging Face.
2. In the Space Settings, add `HUGGINGFACEHUB_ACCESS_TOKEN` as a Secret.
3. Update your Google Cloud OAuth credentials to whitelist your new `https://yourusername-spacename.hf.space` URL.
4. Push this repository to your Space remote!
