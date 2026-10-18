from functools import lru_cache

from sentence_transformers import CrossEncoder


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    """Load the cross-encoder once and reuse it."""
    return CrossEncoder(MODEL_NAME)


def rerank_documents(
    query: str,
    documents: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """
    Rank retrieved documents by query-document relevance.

    Each document must contain a 'content' field.
    """
    if not query.strip() or not documents:
        return []

    model = get_reranker()

    pairs = [
        (query, document["content"])
        for document in documents
    ]

    scores = model.predict(pairs)

    ranked_documents = []

    for document, score in zip(documents, scores):
        item = dict(document)
        item["rerank_score"] = float(score)
        ranked_documents.append(item)

    ranked_documents.sort(
        key=lambda item: item["rerank_score"],
        reverse=True,
    )

    return ranked_documents[:top_k]