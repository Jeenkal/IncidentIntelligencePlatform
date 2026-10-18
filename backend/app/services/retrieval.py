import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.embeddings import generate_embedding

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "after", "was",
    "were", "has", "have", "not", "yet", "are", "but", "its", "into",
    "when", "then", "than", "been", "issue", "affects",
}


def build_or_tsquery(query: str, max_terms: int = 12) -> str:
    """Turn free text into an OR query: 'api | http | 502 | deployment'.

    Only alphanumeric terms are kept, so the result is always a valid
    to_tsquery string.
    """
    terms, seen = [], set()

    for term in re.findall(r"[a-z0-9]{3,}", query.lower()):
        if term in STOPWORDS or term in seen:
            continue
        seen.add(term)
        terms.append(term)

    return " | ".join(terms[:max_terms])


def hybrid_search(
    db: Session,
    query: str,
    domain: str,
    top_k: int = 5,
) -> list[dict]:
    if not query.strip():
        return []

    query_embedding = generate_embedding(query)

    # If no usable keywords remain, use a term that matches nothing so the
    # keyword half is empty and the search falls back to vector-only.
    ts_query = build_or_tsquery(query) or "zzznomatch"

    # Each branch fetches a larger pool than the final cut so fusion
    # has something to combine.
    candidate_limit = max(top_k * 3, 20)

    sql = text("""
        WITH vector_results AS (
            SELECT
                c.id,
                c.document_id,
                c.content,
                d.title,
                d.source_url,
                c.metadata,
                ROW_NUMBER() OVER (
                    ORDER BY c.embedding <=> CAST(:embedding AS vector)
                ) AS vector_rank
            FROM knowledge_chunks c
            JOIN knowledge_documents d
                ON d.id = c.document_id
            WHERE d.domain = :domain
              AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> CAST(:embedding AS vector)
            LIMIT :candidate_limit
        ),
        keyword_results AS (
            SELECT
                c.id,
                ROW_NUMBER() OVER (
                    ORDER BY ts_rank_cd(
                        c.search_vector,
                        to_tsquery('english', :ts_query)
                    ) DESC
                ) AS keyword_rank
            FROM knowledge_chunks c
            JOIN knowledge_documents d
                ON d.id = c.document_id
            WHERE d.domain = :domain
              AND c.search_vector @@
                  to_tsquery('english', :ts_query)
            ORDER BY ts_rank_cd(
                c.search_vector,
                to_tsquery('english', :ts_query)
            ) DESC
            LIMIT :candidate_limit
        ),
        combined AS (
            SELECT
                v.id,
                v.document_id,
                v.content,
                v.title,
                v.source_url,
                v.metadata,
                1.0 / (60 + v.vector_rank) AS vector_score,
                COALESCE(
                    1.0 / (60 + k.keyword_rank),
                    0.0
                ) AS keyword_score
            FROM vector_results v
            LEFT JOIN keyword_results k ON k.id = v.id

            UNION ALL

            SELECT
                k.id,
                c.document_id,
                c.content,
                d.title,
                d.source_url,
                c.metadata,
                0.0 AS vector_score,
                1.0 / (60 + k.keyword_rank) AS keyword_score
            FROM keyword_results k
            JOIN knowledge_chunks c ON c.id = k.id
            JOIN knowledge_documents d ON d.id = c.document_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM vector_results v
                WHERE v.id = k.id
            )
        )
        SELECT
            id,
            document_id,
            content,
            title,
            source_url,
            metadata,
            SUM(vector_score + keyword_score) AS score
        FROM combined
        GROUP BY
            id, document_id, content, title, source_url, metadata
        ORDER BY score DESC
        LIMIT :top_k
    """)

    rows = db.execute(
        sql,
        {
            "embedding": str(query_embedding),
            "ts_query": ts_query,
            "domain": domain,
            "candidate_limit": candidate_limit,
            "top_k": top_k,
        },
    ).mappings().all()

    return [dict(row) for row in rows]