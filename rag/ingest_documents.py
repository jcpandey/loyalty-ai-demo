import os
from pathlib import Path

import chromadb
import requests
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from requests import exceptions as requests_exceptions
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
GUIDE_PATH = BASE_DIR.parent / "Download the end-to-end implementation guide.md"
DB_DIR = str(BASE_DIR / "rag" / "chroma_db")
COLLECTION = "loyalty_knowledge"
EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"

load_dotenv(BASE_DIR / ".env")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_TLS_NO_VERIFY = os.getenv("OPENAI_TLS_NO_VERIFY", "false").lower() in {
    "1",
    "true",
    "yes",
}
OPENAI_TRUSTED_CA_FILE = os.getenv("OPENAI_TRUSTED_CA_FILE") or None

if OPENAI_TLS_NO_VERIFY:
    disable_warnings(InsecureRequestWarning)


def markdown_paths() -> list[Path]:
    paths = sorted(DOCS_DIR.glob("*.md"))
    if GUIDE_PATH.exists():
        paths.append(GUIDE_PATH)
    return paths


def load_markdown_documents() -> list[Document]:
    documents = []
    for path in markdown_paths():
        documents.append(
            Document(
                page_content=path.read_text(encoding="utf-8"),
                metadata={"source": str(path), "document_name": path.name},
            )
        )
    return documents


def embed_texts(texts: list[str]) -> list[list[float]]:
    try:
        response = requests.post(
            OPENAI_EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": EMBEDDING_MODEL, "input": texts},
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
    return [item["embedding"] for item in payload["data"]]


def main() -> None:
    documents = load_markdown_documents()
    if not documents:
        raise RuntimeError(f"No markdown documents found in {DOCS_DIR}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(documents)

    client = chromadb.PersistentClient(path=DB_DIR)
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.get_or_create_collection(COLLECTION)

    texts = [chunk.page_content for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]
    ids = [
        f"{chunk.metadata.get('document_name', 'document')}-{index}"
        for index, chunk in enumerate(chunks)
    ]
    embeddings = embed_texts(texts)
    collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
    print(f"Indexed {len(chunks)} chunks from {len(documents)} documents")


if __name__ == "__main__":
    main()
