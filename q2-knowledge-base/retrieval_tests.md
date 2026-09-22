# Q2 — Retrieval Test Results

**KB:** Arogya Shield Plus | 40 records | 8 categories  
**Embedding model:** all-MiniLM-L6-v2 (384-dim, cosine similarity)  
**Reranker:** cross-encoder/ms-marco-MiniLM-L-6-v2  
**Test date:** 2026-09-22 | **Result: 5/5 PASS**

---

## Query 1 — Pre-Existing Disease Waiting Period

**Query:** `"What is the waiting period for pre-existing conditions like diabetes?"`  
**Category filter:** `policy_rules`  
**Top result:** KB-004 — Pre-Existing Disease (PED) Waiting Period  
**Citation:** `KB-004 | ShieldCare Policy Wording v2.1 | v2.1`  
**Rerank score:** 8.42  

**Answer returned:**
> Silver and Gold plans have a 24-month PED waiting period. Platinum plan has a 12-month waiting period. After the waiting period, all PED conditions are fully covered with no sub-limit. Mandatory disclosure is required — failure to disclose may result in claim rejection.

**Verdict:** ✅ PASS — correct record, correct category, factual answer with no hallucination.

---

## Query 2 — Gold Plan Premium for 34-Year-Old

**Query:** `"What does the Gold plan cost for a 34-year-old individual?"`  
**Category filter:** `pricing`  
**Top result:** KB-002 — Premium Schedule — Age Band Pricing  
**Citation:** `KB-002 | ShieldCare Premium Schedule 2026 | v2.1`  
**Rerank score:** 7.91  

**Answer returned:**
> Gold plan (₹10L): Age 18-35: ₹7,500/yr. Premiums are exclusive of 18% GST. Family floater adds 20% to base premium.

**Verdict:** ✅ PASS — correct age band cited, no hallucinated premium numbers.

---

## Query 3 — Cataract Surgery Coverage

**Query:** `"Is cataract surgery covered as a day-care procedure?"`  
**Category filter:** `coverage`  
**Top result:** KB-005 — Day-Care Procedures Coverage  
**Citation:** `KB-005 | ShieldCare Coverage Schedule 2026 | v2.1`  
**Rerank score:** 9.15  

**Answer returned:**
> Arogya Shield Plus covers over 550 approved day-care procedures including cataract surgery. No sub-limit applies. The procedure must be performed at a network hospital or approved day-care center.

**Verdict:** ✅ PASS — day-care record retrieved, cataract explicitly confirmed.

---

## Query 4 — Cashless Claim Filing Process

**Query:** `"How do I file a cashless claim at a network hospital?"`  
**Category filter:** `claim_process`  
**Top result:** KB-011 — Cashless Claim Process  
**Citation:** `KB-011 | ShieldCare Claim Guide 2026 | v2.1`  
**Rerank score:** 8.73  

**Answer returned:**
> Contact the hospital insurance desk at least 4 hours before planned hospitalization. Show ShieldCare health card and photo ID. Hospital submits pre-authorization. ShieldCare approves within 1 hour (emergency) or 4 hours (planned). At discharge, sign cashless settlement form — no upfront payment required.

**Verdict:** ✅ PASS — full 5-step process returned correctly.

---

## Query 5 — Objection: Premium Too Expensive

**Query:** `"The premium seems too expensive. Why should I buy health insurance?"`  
**Category filter:** `objection`  
**Top result:** KB-018 — Objection: Premium is too expensive  
**Citation:** `KB-018 | ShieldCare Sales Objection Handbook 2026 | v2.1`  
**Rerank score:** 9.28  

**Answer returned:**
> One hospitalization in a metro hospital can cost ₹2-5 Lakh. Silver plan starts at ₹4,200/year (₹350/month). Premium qualifies for Section 80D tax deduction — reducing net cost by 20-30% for taxpayers. Consider it financial protection, not an expense.

**Verdict:** ✅ PASS — objection record retrieved, KB-grounded counter-argument returned.

---

## Summary

| Query | Expected Category | Retrieved Record | Score | Verdict |
|---|---|---|---|---|
| PED waiting period | policy_rules | KB-004 | 8.42 | ✅ PASS |
| Gold plan pricing | pricing | KB-002 | 7.91 | ✅ PASS |
| Cataract day-care | coverage | KB-005 | 9.15 | ✅ PASS |
| Cashless claim | claim_process | KB-011 | 8.73 | ✅ PASS |
| Premium objection | objection | KB-018 | 9.28 | ✅ PASS |

**5/5 PASS** | Cross-encoder reranking consistently selects the correct domain record over cosine-only ranking.
