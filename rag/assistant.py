import os
from dataclasses import dataclass
from pathlib import Path

import chromadb
import requests
from dotenv import load_dotenv
from requests import exceptions as requests_exceptions
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from databricks_retriever import DatabricksQueryError, DatabricksRetriever

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = str(BASE_DIR / "rag" / "chroma_db")
COLLECTION = "loyalty_knowledge"
EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

load_dotenv(BASE_DIR / ".env")
MODEL = os.environ["OPENAI_CHAT_MODEL"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_TLS_NO_VERIFY = os.getenv("OPENAI_TLS_NO_VERIFY", "false").lower() in {
    "1",
    "true",
    "yes",
}
OPENAI_TRUSTED_CA_FILE = os.getenv("OPENAI_TRUSTED_CA_FILE") or None

if OPENAI_TLS_NO_VERIFY:
    disable_warnings(InsecureRequestWarning)

chroma_client = chromadb.PersistentClient(path=DB_DIR)
collection = chroma_client.get_collection(COLLECTION)
databricks_retriever = DatabricksRetriever.from_env()

SYSTEM_INSTRUCTION = """You are the support assistant for a synthetic loyalty platform.
Answer only from the supplied context. If the answer is not in the context, say that you
cannot find it in the knowledge base. Clearly label synthetic policies as demo policies.
Cite the source names used in your answer. Treat databricks_sql as the authoritative source for
live metrics, balances, freshness, and quarantine counts. Use document sources for policy,
schema, and runbook explanations. Never reveal secrets or invent production facts.
"""


@dataclass
class RetrievedContext:
    blocks: list[str]
    source_labels: list[str]
    sql_error: str | None = None


def embed_text(text: str) -> list[float]:
    try:
        response = requests.post(
            OPENAI_EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": EMBEDDING_MODEL, "input": text},
            timeout=60,
            verify=False if OPENAI_TLS_NO_VERIFY else OPENAI_TRUSTED_CA_FILE or True,
        )
    except requests_exceptions.SSLError as exc:
        raise RuntimeError(
            "OpenAI TLS verification failed. Configure OPENAI_TRUSTED_CA_FILE with your corporate CA bundle, "
            "or temporarily set OPENAI_TLS_NO_VERIFY=true for connectivity testing."
        ) from exc
    response.raise_for_status()
    payload = response.json()
    return payload["data"][0]["embedding"]


def similarity_search(question: str, limit: int = 4) -> list[dict[str, object]]:
    query_result = collection.query(
        query_embeddings=[embed_text(question)],
        n_results=limit,
        include=["documents", "metadatas", "distances"],
    )
    documents = query_result.get("documents", [[]])[0]
    metadatas = query_result.get("metadatas", [[]])[0]
    return [
        {"document": document, "metadata": metadata or {}}
        for document, metadata in zip(documents, metadatas)
    ]


def complete(prompt: str) -> str:
    try:
        response = requests.post(
            OPENAI_CHAT_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=90,
            verify=False if OPENAI_TLS_NO_VERIFY else OPENAI_TRUSTED_CA_FILE or True,
        )
    except requests_exceptions.SSLError as exc:
        raise RuntimeError(
            "OpenAI TLS verification failed. Configure OPENAI_TRUSTED_CA_FILE with your corporate CA bundle, "
            "or temporarily set OPENAI_TLS_NO_VERIFY=true for connectivity testing."
        ) from exc
    response.raise_for_status()
    payload = response.json()
    return payload["choices"][0]["message"]["content"]


def gather_context(question: str) -> RetrievedContext:
    blocks: list[str] = []
    source_labels: list[str] = []
    sql_error = None

    retrieved = similarity_search(question, limit=4)
    for index, item in enumerate(retrieved, start=1):
        metadata = item["metadata"]
        source = metadata.get("document_name") or metadata.get("source", "unknown")
        blocks.append(f"[Context {index}; source={source}]\n{item['document']}")
        source_labels.append(str(source))

    if databricks_retriever is not None:
        try:
            sql_context = databricks_retriever.retrieve(question)
        except DatabricksQueryError as exc:
            sql_error = str(exc)
        else:
            if sql_context:
                blocks.append(f"[Structured data; source=databricks_sql]\n{sql_context}")
                source_labels.append("databricks_sql")

    return RetrievedContext(blocks=blocks, source_labels=source_labels, sql_error=sql_error)


def answer(question: str) -> str:
    context = gather_context(question)
    if not context.blocks:
        if context.sql_error:
            return f"I could not query Databricks for this question: {context.sql_error}"
        return "I cannot find that in the knowledge base."

    prompt = f"""Context:
{chr(10).join(context.blocks)}

Question: {question}

Sources available: {', '.join(context.source_labels)}
"""
    content = complete(prompt)
    if context.sql_error:
        content = f"{content}\n\nNote: Databricks structured retrieval was unavailable: {context.sql_error}"
    return content


def main() -> None:
    print("Synthetic Loyalty RAG Assistant. Type 'exit' to stop.")
    while True:
        question = input("\nYou: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if question:
            print("\nAssistant:", answer(question))


if __name__ == "__main__":
    main()
