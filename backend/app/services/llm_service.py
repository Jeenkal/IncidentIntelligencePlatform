import json
import os

from ollama import Client

client = Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))

MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def generate_json(prompt: str) -> dict:
    response = client.chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an incident investigation assistant. "
                    "Use only the supplied evidence for factual findings. "
                    "Do not invent logs, events, citations, or root causes. "
                    "Distinguish hypotheses from confirmed findings. "
                    "If evidence is insufficient, say so explicitly. "
                    "Return valid JSON only."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        format="json",
        options={"temperature": 0},
    )

    content = response.message.content

    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("Ollama returned invalid JSON.") from exc

    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object from Ollama.")

    return result