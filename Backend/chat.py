from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

def create_qa_chain(llm, retriever):
    system_prompt = (
        "You are SmartDoc AI, a helpful and knowledgeable AI assistant.\n"
        "Use the following context to answer the user's question.\n"
        "If the context contains the answer from PDF documents, answer directly and cite the source inline (e.g., [1]).\n"
        "If the context contains Web Search Results, use them to answer the question.\n"
        "CRITICAL: If you used any information from the context (PDFs or Web Search), you MUST add a new line at the very end of your response starting with 'Sources: ' followed by the document names or 'Web Search' as appropriate.\n"
        "If the user is making small talk (like 'hello', 'thank you', 'how are you'), respond politely without citing sources.\n"
        "If no relevant context is provided, answer the question using your own general knowledge — do NOT say you cannot answer.\n"
        "CRITICAL: Always reply in the EXACT SAME language that the user used in their message.\n\n"
        "Previous Conversation History:\n"
        "{history}\n\n"
        "Context:\n{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])
    
    def format_docs(docs):
        formatted = []
        for i, doc in enumerate(docs, 1):
            import os
            source = doc.metadata.get('source', 'Unknown Document')
            filename = os.path.basename(source)
            page = doc.metadata.get('page', 'Unknown')
            # Assuming page metadata is 0-indexed from PyPDFLoader
            page_display = int(page) + 1 if isinstance(page, (int, str)) and str(page).isdigit() else page
            formatted.append(f"--- Citation [{i}] (File: {filename}, Page: {page_display}) ---\n{doc.page_content}")
        return "\n\n".join(formatted)
        
    return prompt, llm, retriever, format_docs
