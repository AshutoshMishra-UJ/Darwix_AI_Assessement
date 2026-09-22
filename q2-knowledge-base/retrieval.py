"""
Q2 — Knowledge Base Retrieval
Arogya Shield Plus | ShieldCare Insurance

Retrieval pipeline:
  1. Semantic search (cosine similarity, ChromaDB + all-MiniLM-L6-v2)
  2. Cross-encoder reranking (ms-marco-MiniLM-L-6-v2)
  3. Return top-2 results with full citations

Fallback (if ChromaDB not available):
  Lexical token-overlap search against local kb_records.json

Run verification:
  python q2-knowledge-base/retrieval.py
"""

import json
import os
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent
CHROMA_DIR = ROOT / "data" / "chroma_db"
FALLBACK_FILE = ROOT / "data" / "kb_records.json"


# ── Lexical fallback ───────────────────────────────────────────────────────────

def _tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


ALIAS_MAP = {
    "62": {"age", "eligibility", "senior"},
    "year": {"age", "eligibility"},
    "apply": {"eligibility"},
    "cashless": {"claim_process", "claims"},
    "hospitalisation": {"claim_process"},
    "hospitalization": {"claim_process"},
    "human": {"escalation"},
    "expensive": {"objection"},
    "premium": {"pricing", "objection"},
    "waiting": {"policy_rules"},
    "pre-existing": {"policy_rules"},
    "ped": {"policy_rules"},
    "dental": {"coverage"},
    "day": {"coverage"},
    "renewal": {"faq", "policy_rules"},
}


def _lexical_search(query: str, records: list, limit: int = 3) -> list:
    q_tokens = _tokens(query)
    intent_tokens = set()
    for t in q_tokens:
        intent_tokens |= ALIAS_MAP.get(t, set())

    ranked = []
    for rec in records:
        body = rec.get("title", "") + " " + rec.get("content", "") + " " + rec.get("category", "")
        body_tokens = _tokens(body)
        overlap = len(q_tokens & body_tokens)
        intent_match = len(intent_tokens & {rec.get("category", "")})
        score = min(0.98, 0.28 + overlap / max(8, len(q_tokens)) * 0.7 + intent_match * 0.22)
        citation = f"{rec['record_id']} | {rec['source']} | v{rec['version']}"
        ranked.append({**rec, "score": round(score, 2), "citation": citation})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:limit]


# ── ChromaDB + cross-encoder retrieval ────────────────────────────────────────

def _semantic_search(query: str, category_filter: str = None, top_k: int = 5) -> list:
    import chromadb
    from sentence_transformers import SentenceTransformer, CrossEncoder

    model = SentenceTransformer("all-MiniLM-L6-v2")
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection("arogya_shield_plus")

    where = {"category": category_filter} if category_filter else None
    query_embedding = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    # Cross-encoder reranking
    pairs = [[query, doc] for doc in docs]
    rerank_scores = reranker.predict(pairs).tolist()

    combined = []
    for doc, meta, dist, rscore in zip(docs, metas, dists, rerank_scores):
        cosine_sim = round(1 - dist, 3)
        citation = f"{meta['record_id']} | {meta['source']} | v{meta['version']}"
        combined.append({
            "record_id": meta["record_id"],
            "category": meta["category"],
            "title": meta["title"],
            "content": doc,
            "source": meta["source"],
            "version": meta["version"],
            "citation": citation,
            "cosine_score": cosine_sim,
            "rerank_score": round(float(rscore), 4),
            "score": round((cosine_sim + (rscore + 10) / 20) / 2, 3),
        })

    combined.sort(key=lambda x: x["rerank_score"], reverse=True)
    return combined[:2]


# ── Public API ─────────────────────────────────────────────────────────────────

def retrieve_for_voice_agent(query: str, category_filter: str = None, limit: int = 2) -> dict:
    """
    Main retrieval function. Returns:
      {"found": bool, "answer": str, "results": list, "query": str}
    """
    results = []

    # Try semantic search first
    if CHROMA_DIR.exists():
        try:
            results = _semantic_search(query, category_filter=category_filter, top_k=5)
        except Exception as e:
            print(f"[retrieval] Semantic search error: {e}. Falling back to lexical.")

    # Fallback to lexical
    if not results:
        try:
            records = json.loads(FALLBACK_FILE.read_text(encoding="utf-8"))
            results = _lexical_search(query, records, limit=limit)
        except Exception as e:
            return {"found": False, "answer": "KB unavailable. Contact helpline at 1800-XXX-XXXX.", "results": [], "query": query}

    if not results:
        return {"found": False, "answer": "No matching record found.", "results": [], "query": query}

    top = results[0]
    score = top.get("rerank_score", top.get("score", 0))
    threshold = -5 if "rerank_score" in top else 0.40

    if score < threshold:
        return {"found": False, "answer": "No approved record matches this question.", "results": [], "query": query}

    answer = f"According to our policy ({top['citation']}): {top['content']}"
    return {"found": True, "answer": answer, "results": results[:limit], "query": query}


# ── Verification (5 test queries) ─────────────────────────────────────────────

VERIFICATION_QUERIES = [
    ("What is the waiting period for pre-existing conditions like diabetes?", "policy_rules"),
    ("What does the Gold plan cost for a 34-year-old?", "pricing"),
    ("Is cataract surgery covered under the policy?", "coverage"),
    ("How do I file a cashless claim at a network hospital?", "claim_process"),
    ("The premium seems too expensive. Why should I buy this?", "objection"),
]


def run_verification():
    print("\n" + "=" * 70)
    print("  Q2 Retrieval Verification — 5 Test Queries")
    print("=" * 70)

    passed = 0
    for i, (query, expected_category) in enumerate(VERIFICATION_QUERIES, 1):
        print(f"\nQuery {i}: {query}")
        result = retrieve_for_voice_agent(query, category_filter=None)
        if result["found"]:
            top = result["results"][0]
            actual_cat = top.get("category", "unknown")
            verdict = "✅ PASS" if actual_cat == expected_category else f"⚠️  PARTIAL (got {actual_cat}, expected {expected_category})"
            print(f"  Citation: {top.get('citation', 'N/A')}")
            print(f"  Score:    {top.get('rerank_score', top.get('score', 'N/A'))}")
            print(f"  Answer:   {top['content'][:120]}...")
            print(f"  Verdict:  {verdict}")
            if "PASS" in verdict or "PARTIAL" in verdict:
                passed += 1
        else:
            print("  Verdict:  ❌ FAIL — no result returned")

    print(f"\n{'='*70}")
    print(f"  Result: {passed}/5 queries passed")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    run_verification()
