def get_retriever(vectorstore, k=6, score_threshold=0.5):
    """Return a retriever that fetches top-k relevant chunks passing a similarity threshold."""
    return vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": k, "score_threshold": score_threshold}
    )
