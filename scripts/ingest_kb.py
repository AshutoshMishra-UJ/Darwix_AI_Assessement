"""Ingest approved PDF, TXT, or HTML sources into versioned KB chunks.

Place approved files in data/sources, then run:
    python scripts/ingest_kb.py

Optional dependencies: pypdf for PDFs and sentence-transformers/numpy for embeddings.
The script never claims a source is approved; provenance is copied from the input file.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "sources"
OUTPUT = ROOT / "data" / "ingested_records.json"
CHUNK_SIZE = 900
OVERLAP = 120
PII_PATTERNS = [
    (re.compile(r"\b\d{10}\b"), "[PHONE_REDACTED]"),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[PAN_REDACTED]"),
    (re.compile(r"\b\d{12}\b"), "[ID_REDACTED]"),
    (re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"), "[EMAIL_REDACTED]"),
]


def extract_text(path):
    if path.suffix.lower() in {".txt", ".md", ".html", ".htm"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as error:
            raise RuntimeError("Install pypdf to ingest PDF sources") from error
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return ""


def clean(text):
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return re.sub(r"\s+", " ", text).strip()


def chunks(text):
    start = 0
    while start < len(text):
        end = min(len(text), start + CHUNK_SIZE)
        yield text[start:end]
        if end == len(text):
            break
        start = end - OVERLAP


def main():
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    output = []
    seen_hashes = set()
    for path in sorted(SOURCE_DIR.iterdir()):
        if not path.is_file() or path.name.startswith(".") or path.name.lower() == "readme.md":
            continue
        raw = extract_text(path)
        content = clean(raw)
        if not content:
            continue
        for index, chunk in enumerate(chunks(content)):
            digest = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            output.append({
                "record_id": f"{path.stem}-{index + 1:03d}",
                "title": path.stem.replace("_", " ").title(),
                "content": chunk,
                "category": "source_document",
                "source": path.name,
                "source_type": path.suffix.lower().lstrip("."),
                "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "version": "1.0",
                "pii_redacted": "[" in chunk and "_REDACTED]" in chunk,
                "chunk_index": index,
                "chunk_size": CHUNK_SIZE,
                "overlap": OVERLAP,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })
    OUTPUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({"sources": len(list(SOURCE_DIR.iterdir())), "chunks": len(output), "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
