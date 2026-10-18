from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.chunking import chunk_text
from app.services.embeddings import generate_embedding


def ingest_text(
    db: Session,
    title: str,
    content: str,
    domain: str,
    source_url: str | None = None,
) -> dict:
    if not content.strip():
        raise ValueError("Document content cannot be empty")

    allowed_domains = {
        "devops",
        "ai_engineering",
        "postgresql",
        "enterprise_it",
        "security",
    }

    if domain not in allowed_domains:
        raise ValueError(f"Unsupported domain: {domain}")

    try:
        document_result = db.execute(
            text("""
                INSERT INTO knowledge_documents
                    (title, domain, source_type, source_url)
                VALUES
                    (:title, :domain, 'document', :source_url)
                RETURNING id
            """),
            {
                "title": title,
                "domain": domain,
                "source_url": source_url,
            },
        )

        document_id = document_result.scalar_one()

        chunks = chunk_text(content)

        for index, chunk in enumerate(chunks):
            embedding = generate_embedding(chunk)

            db.execute(
                text("""
                    INSERT INTO knowledge_chunks
                        (document_id, content, chunk_index, embedding, metadata)
                    VALUES
                        (
                            :document_id,
                            :content,
                            :chunk_index,
                            CAST(:embedding AS vector),
                            CAST(:metadata AS jsonb)
                        )
                """),
                {
                    "document_id": document_id,
                    "content": chunk,
                    "chunk_index": index,
                    "embedding": str(embedding),
                    "metadata": (
                        '{"domain": "' + domain + '"}'
                    ),
                },
            )

        db.commit()

        return {
            "document_id": document_id,
            "title": title,
            "domain": domain,
            "chunks_created": len(chunks),
        }

    except Exception:
        db.rollback()
        raise