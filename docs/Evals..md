# Evals — AI Digest Pipeline

**Status:** Planning
**Goal:** Make sure Claude is picking the right articles and summarizing them accurately.

---

## What We're Measuring

### 1. LLM-as-Judge
A second Claude call that reads the source article + generated summary and checks:
- Is the summary faithful? (nothing made up) — rated 1–5
- Was this article worth selecting? — Yes/No

**Target:** Faithfulness > 4.0 / 5.0

---

### 2. BERTScore
Compare Claude's summary against a manually written reference summary using semantic similarity.
Run this when the prompt changes, not on every article.

**Target:** F1 > 0.85

---

### 3. Relevance Precision & Recall
Build a small labeled test set (~50 articles, manually tagged relevant/not relevant).
Check how well Claude's filtering performs against it.
- **Precision** — of what Claude picked, how many were actually good?
- **Recall** — of all the good articles, how many did Claude find?

**Target:** Precision > 80%, Recall > 75%

---

### 4. Consistency Testing
Run the same article through the pipeline 3–5 times.
Compare outputs using BERTScore. If they vary too much, the prompt is unstable.

**Target:** F1 across runs > 0.90

---

### 5. Human Feedback
Thumbs up / down on each article in the browser.
Saved to `feedback.json` with source, category, and timestamp.
Used later to tune which sources Claude prefers.

**Target:** Thumbs-up rate > 70% over time

---

## Results

| Component | Status | Score |
|---|---|---|
| LLM-as-Judge | 🔲 Not started | — |
| BERTScore | 🔲 Not started | — |
| Relevance Precision/Recall | 🔲 Not started | — |
| Consistency Testing | 🔲 Not started | — |
| Human Feedback | 🔲 Not started | — |

*Results will be updated as each component is built.*