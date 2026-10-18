from ollama import Client

client = Client(host="http://localhost:11434")

EMBEDDING_MODEL = "nomic-embed-text"


def generate_embedding(text: str) -> list[float]:
    response = client.embed(
        model=EMBEDDING_MODEL,
        input=text,
    )

    embedding = response["embeddings"][0]

    if len(embedding) != 768:
        raise ValueError(
            f"Expected 768 embedding dimensions, got {len(embedding)}"
        )

    return embedding