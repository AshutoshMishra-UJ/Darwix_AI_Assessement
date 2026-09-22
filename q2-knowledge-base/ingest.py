"""
Q2 — Knowledge Base Ingestion Pipeline
Arogya Shield Plus | ShieldCare Insurance

Pipeline:
  1. Load JSON source records
  2. Clean text (whitespace, PII redaction)
  3. Deduplicate (SHA-256 content hash)
  4. Chunk long records (900 chars, 120-char overlap)
  5. Embed with all-MiniLM-L6-v2 (free, local)
  6. Store in ChromaDB (local persistent)

Run:
  python q2-knowledge-base/ingest.py
"""

import hashlib
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent
DATA_FILE = Path(__file__).parent / "data" / "arogya_shield_plus.json"
CHROMA_DIR = ROOT / "data" / "chroma_db"

# ── PII redaction patterns ─────────────────────────────────────────────────────
PII_PATTERNS = [
    (re.compile(r"\b[6-9]\d{9}\b"), "[PHONE]"),                      # Indian mobile
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "[AADHAAR]"),        # Aadhaar
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[PAN]"),               # PAN card
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),
]


def clean_text(text: str) -> str:
    """Whitespace normalization + PII redaction."""
    text = " ".join(text.split())
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += chunk_size - overlap
    return chunks


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def ingest():
    print("=" * 60)
    print("  Q2 Knowledge Base Ingestion — Arogya Shield Plus")
    print("=" * 60)

    # Load source records
    records = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    print(f"\n[1] Loaded {len(records)} source records from {DATA_FILE.name}")

    # Clean + deduplicate
    seen_hashes = set()
    cleaned_chunks = []
    for record in records:
        body = clean_text(f"{record['title']}. {record['content']}")
        text_chunks = chunk_text(body)
        for i, chunk in enumerate(text_chunks):
            h = content_hash(chunk)
            if h in seen_hashes:
                print(f"  [dedup] Skipped duplicate chunk from {record['record_id']}")
                continue
            seen_hashes.add(h)
            cleaned_chunks.append({
                "id": f"{record['record_id']}-chunk{i}",
                "document": chunk,
                "metadata": {
                    "record_id": record["record_id"],
                    "category": record["category"],
                    "title": record["title"],
                    "source": record["source"],
                    "version": record["version"],
                    "chunk_index": i,
                    "content_hash": h,
                },
            })

    print(f"[2] Produced {len(cleaned_chunks)} chunks after dedup (from {len(records)} records)")

    # Embed + store in ChromaDB
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer

        print("[3] Loading embedding model: all-MiniLM-L6-v2 ...")
        model = SentenceTransformer("all-MiniLM-L6-v2")

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))

        # Drop and recreate collection for clean ingest
        try:
            client.delete_collection("arogya_shield_plus")
        except Exception:
            pass
        collection = client.create_collection(
            name="arogya_shield_plus",
            metadata={"hnsw:space": "cosine"},
        )

        print(f"[4] Embedding {len(cleaned_chunks)} chunks ...")
        documents = [c["document"] for c in cleaned_chunks]
        embeddings = model.encode(documents, show_progress_bar=True, batch_size=32).tolist()

        collection.add(
            ids=[c["id"] for c in cleaned_chunks],
            documents=documents,
            embeddings=embeddings,
            metadatas=[c["metadata"] for c in cleaned_chunks],
        )
        print(f"[5] Stored {collection.count()} vectors in ChromaDB at {CHROMA_DIR}")
        print("\n✅ Ingestion complete. Run retrieval.py to verify.")

    except ImportError as e:
        print(f"\n⚠️  ChromaDB/SentenceTransformers not installed: {e}")
        print("   Falling back to saving cleaned records as JSON for demo mode.")
        out_path = ROOT / "data" / "ingested_records.json"
        out_path.write_text(
            json.dumps([{"id": c["id"], "document": c["document"], **c["metadata"]} for c in cleaned_chunks], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"   Saved {len(cleaned_chunks)} records to {out_path}")


if __name__ == "__main__":
    ingest()
