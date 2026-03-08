# judge.py
# -------------------------------------------------------------------------
# PURPOSE: LLM-as-Judge eval for the AI Digest pipeline.
#          Fetches the full article text at eval time, then uses Gemini
#          as the judge (different model from summarizer = less bias).
#          Falls back to Claude if no GOOGLE_API_KEY is set.
#
# MODEL STRATEGY:
#   - Summarizer (analyzer.py): Claude
#   - Judge (judge.py):         Gemini (primary) → Claude (fallback)
#   Using a different model as judge avoids self-evaluation bias.
#
# WHAT IT EVALUATES:
#   - Faithfulness: does the summary reflect what the article actually says?
#   - Relevance: was this article worth selecting for the digest?
#
# FLOW:
#   1. Load articles from digest.json
#   2. For each article, fetch full text from the URL
#   3. Send full text + summary to Gemini judge (or Claude fallback)
#   4. Parse structured JSON scores from judge
#   5. Save results to eval_results.json
#   6. Print summary report to terminal
#
# RUN:
#   # Evaluate all articles in digest.json
#   poetry run python judge.py
#
#   # Evaluate a single article by URL (test mode)
#   poetry run python judge.py --url https://example.com/article
# -------------------------------------------------------------------------

import anthropic
import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ── Environment ───────────────────────────────────────────────────────────

load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY    = os.getenv("GOOGLE_API_KEY")

# Judge uses Gemini as primary (different model from summarizer = less bias)
# Falls back to Claude if GOOGLE_API_KEY is not set
_use_gemini_judge = bool(GOOGLE_API_KEY and GOOGLE_API_KEY != "your_google_key_here")

# ── Config ────────────────────────────────────────────────────────────────

DIGEST_FILE = "digest.json"
EVAL_RESULTS_FILE = "eval_results.json"

# Max characters of article text to send to judge
# Keeps token cost low while giving enough context
MAX_ARTICLE_CHARS = 3000

# HTTP request timeout when fetching articles
FETCH_TIMEOUT = 15


# ── Article Fetcher ───────────────────────────────────────────────────────

def fetch_article_text(url: str) -> str:
    """
    Fetch full article text from a URL at eval time.
    Uses requests + BeautifulSoup to extract readable text.
    Returns empty string if fetch fails — judge will handle gracefully.

    Args:
        url: article URL from digest.json

    Returns:
        Cleaned article text (up to MAX_ARTICLE_CHARS)
    """
    print(f"  Fetching article: {url[:80]}...")

    try:
        headers = {
            # Mimic a browser to avoid being blocked by some sites
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT)
        response.raise_for_status()

        # Parse HTML and extract readable text
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove noise: scripts, styles, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Extract text and clean up whitespace
        text = soup.get_text(separator=" ")
        text = " ".join(text.split())  # collapse whitespace

        # Cap length to control token cost
        return text[:MAX_ARTICLE_CHARS]

    except Exception as e:
        print(f"  [WARN] Could not fetch article: {e}")
        return ""


# ── Judge Prompt ──────────────────────────────────────────────────────────

def build_judge_prompt(article: dict, full_text: str) -> str:
    """
    Build the judge prompt.
    Gives the judge: headline, category, Claude's summary, and full article text.
    Asks for structured JSON output with faithfulness + relevance scores.

    Args:
        article: dict from digest.json (headline, category, why_question, why_answer)
        full_text: fetched article text (source of truth)

    Returns:
        Full prompt string for the judge Claude call
    """

    # If we couldn't fetch the article, tell the judge
    source_context = full_text if full_text else (
        "Full article text could not be fetched. "
        "Evaluate based on headline and category only. "
        "Mark fetch_failed as true in your response."
    )

    prompt = f"""
You are an expert evaluator for an AI news digest pipeline.
Your job is to evaluate whether the generated summary accurately reflects the source article.

ARTICLE DETAILS:
Headline: {article.get('headline', 'N/A')}
Category: {article.get('category', 'N/A')}
Source: {article.get('source', 'N/A')}

GENERATED SUMMARY:
Question: {article.get('why_question', 'N/A')}
Answer: {article.get('why_answer', 'N/A')}

SOURCE ARTICLE TEXT:
{source_context}

EVALUATE ON TWO DIMENSIONS:

1. FAITHFULNESS (1-5):
   Does the summary contain only information present in the source article?
   Are there any claims that cannot be verified from the article text?
   5 = Perfectly faithful, nothing made up
   4 = Mostly faithful, minor extrapolation
   3 = Some claims not clearly supported
   2 = Several unsupported claims
   1 = Significant hallucination or fabrication

2. RELEVANCE (yes/no):
   Is this a genuinely interesting and substantive article worth including?
   Would a technical reader find real value in this?
   Consider: does it match categories like engineering deep dives, AI research,
   healthcare tech, or energy? Does it avoid generic hype?

Return ONLY a valid JSON object. No markdown, no explanation, just raw JSON:
{{
  "faithfulness_score": <1-5 integer>,
  "faithfulness_reasoning": "<one sentence explaining the score>",
  "relevance": <true or false>,
  "relevance_reasoning": "<one sentence explaining why>",
  "fetch_failed": <true if article text was unavailable, false otherwise>
}}
"""
    return prompt


# ── JSON Parser (shared) ─────────────────────────────────────────────────

def _parse_judge_response(raw: str) -> dict:
    """
    Parse JSON from judge response. Shared by both Gemini and Claude judge calls.
    Strips accidental markdown fences before parsing.

    Args:
        raw: raw text response from judge model

    Returns:
        Parsed dict or error dict if parsing fails
    """
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        return json.loads(cleaned)

    except json.JSONDecodeError as e:
        print(f"  [ERROR] Judge returned invalid JSON: {e}")
        print(f"  [DEBUG] Raw response: {raw[:300]}")
        return {
            "faithfulness_score": None,
            "faithfulness_reasoning": "Parse error",
            "relevance": None,
            "relevance_reasoning": "Parse error",
            "fetch_failed": False,
            "parse_error": True
        }


# ── Judge API Calls ───────────────────────────────────────────────────────

def call_gemini_judge(prompt: str) -> dict:
    """
    Call Gemini as the judge model.
    Primary judge — different model from Claude summarizer to reduce bias.
    Dynamically discovers available models (same pattern as analyzer.py)
    so it never hardcodes a model name that may not be available.

    Gemini Flash pricing: $0.075/M input, $0.30/M output

    Args:
        prompt: full judge prompt with article + summary

    Returns:
        Parsed dict with faithfulness_score, relevance, reasoning fields
    """
    import requests as req

    base = "https://generativelanguage.googleapis.com/v1beta"

    # Discover available models dynamically — same pattern as analyzer.py
    # This avoids hardcoding a model name that may not exist for this API key
    list_resp = req.get(f"{base}/models?key={GOOGLE_API_KEY}", timeout=30)
    list_resp.raise_for_status()
    models = list_resp.json().get("models", [])

    # Pick first model that supports generateContent
    chosen = None
    for m in models:
        if "generateContent" in m.get("supportedGenerationMethods", []):
            chosen = m["name"].replace("models/", "")
            break

    if not chosen:
        raise RuntimeError("No generateContent-capable Gemini models found for this API key.")

    print(f"  Judge model: Gemini ({chosen})")

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    url = f"{base}/models/{chosen}:generateContent?key={GOOGLE_API_KEY}"

    resp = req.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    # Token usage and cost
    usage         = data.get("usageMetadata", {})
    input_tokens  = usage.get("promptTokenCount", 0)
    output_tokens = usage.get("candidatesTokenCount", 0)
    input_cost    = (input_tokens  / 1_000_000) * 0.075
    output_cost   = (output_tokens / 1_000_000) * 0.30
    total_cost    = input_cost + output_cost
    print(f"  Tokens: {input_tokens} in / {output_tokens} out — Cost: ${total_cost:.6f}")

    raw = data["candidates"][0]["content"]["parts"][0]["text"]
    return _parse_judge_response(raw)


def call_claude_judge(prompt: str) -> dict:
    """
    Call Claude as the judge model.
    Fallback — used when GOOGLE_API_KEY is not set.
    Note: same model as summarizer — less ideal but functional.

    Claude Sonnet pricing: $3.00/M input, $15.00/M output

    Args:
        prompt: full judge prompt with article + summary

    Returns:
        Parsed dict with faithfulness_score, relevance, reasoning fields
    """
    print(f"  Judge model: Claude (claude-sonnet-4-20250514) [fallback]")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    # Token usage and cost
    input_tokens  = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    input_cost    = (input_tokens  / 1_000_000) * 3.00
    output_cost   = (output_tokens / 1_000_000) * 15.00
    total_cost    = input_cost + output_cost
    print(f"  Tokens: {input_tokens} in / {output_tokens} out — Cost: ${total_cost:.6f}")

    raw = ""
    for block in response.content:
        if block.type == "text":
            raw += block.text

    return _parse_judge_response(raw)


def call_judge(prompt: str) -> dict:
    """
    Main judge dispatcher.
    Uses Gemini if GOOGLE_API_KEY is set, falls back to Claude.
    Always prints which model is being used.

    Args:
        prompt: full judge prompt with article + summary

    Returns:
        Parsed dict with faithfulness_score, relevance, reasoning fields
    """
    if _use_gemini_judge:
        return call_gemini_judge(prompt)
    else:
        print("  [INFO] No Google API key found — falling back to Claude as judge")
        return call_claude_judge(prompt)


# ── Results Writer ────────────────────────────────────────────────────────

def save_eval_result(article: dict, scores: dict):
    """
    Append a single eval result to eval_results.json.
    Creates the file if it doesn't exist.
    Each result links back to the original article via its ID and URL.

    Args:
        article: original article dict from digest.json
        scores: judge scores dict from call_judge()
    """
    # Load existing results
    if os.path.exists(EVAL_RESULTS_FILE):
        with open(EVAL_RESULTS_FILE, "r") as f:
            results = json.load(f)
    else:
        results = []

    # Build result record
    result = {
        "eval_id": str(uuid.uuid4()),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "article_id": article.get("id"),
        "article_url": article.get("url"),
        "headline": article.get("headline"),
        "source": article.get("source"),
        "category": article.get("category"),
        "faithfulness_score": scores.get("faithfulness_score"),
        "faithfulness_reasoning": scores.get("faithfulness_reasoning"),
        "relevance": scores.get("relevance"),
        "relevance_reasoning": scores.get("relevance_reasoning"),
        "fetch_failed": scores.get("fetch_failed", False),
        "parse_error": scores.get("parse_error", False)
    }

    results.append(result)

    with open(EVAL_RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)


# ── Report Printer ────────────────────────────────────────────────────────

def print_report(results: list):
    """
    Print a human-readable summary of all eval results to terminal.
    Shows per-article scores and overall averages.

    Args:
        results: list of eval result dicts from this run
    """
    print(f"\n{'='*60}")
    print(f"  EVAL REPORT — LLM-as-Judge")
    print(f"  {len(results)} article(s) evaluated")
    print(f"{'='*60}\n")

    valid_scores = []

    for i, r in enumerate(results, 1):
        score = r.get("faithfulness_score")
        relevance = r.get("relevance")
        fetch_failed = r.get("fetch_failed", False)
        parse_error = r.get("parse_error", False)

        print(f"  [{i}] {r.get('headline', 'N/A')[:60]}")
        print(f"       Source:      {r.get('source', 'N/A')}")
        print(f"       Category:    {r.get('category', 'N/A')}")

        if parse_error:
            print(f"       ⚠️  Judge returned invalid JSON — skipped")
        elif fetch_failed:
            print(f"       ⚠️  Article could not be fetched — partial eval only")
            print(f"       Faithfulness: {score}/5  |  Relevance: {relevance}")
        else:
            print(f"       Faithfulness: {score}/5  |  Relevance: {relevance}")
            print(f"       Why:          {r.get('faithfulness_reasoning', '')}")
            if score:
                valid_scores.append(score)

        print()

    # Overall averages
    if valid_scores:
        avg = sum(valid_scores) / len(valid_scores)
        passed = sum(1 for s in valid_scores if s >= 4)
        print(f"  ── Averages ─────────────────────────────")
        print(f"  Avg Faithfulness:  {avg:.2f} / 5.0")
        print(f"  Passed (≥4):       {passed} / {len(valid_scores)} articles")
        print(f"  Target:            > 4.0 / 5.0")
        print(f"  {'✅ PASS' if avg >= 4.0 else '❌ BELOW TARGET'}")
    print(f"\n{'='*60}\n")


# ── Core Eval Runner ──────────────────────────────────────────────────────

def evaluate_article(article: dict) -> dict:
    """
    Run the full judge eval on a single article.
    Modular — can be called from batch mode or single-article test mode.

    Args:
        article: dict with headline, url, category, why_question, why_answer

    Returns:
        scores dict from call_judge()
    """
    # Step 1: fetch full article text
    full_text = fetch_article_text(article["url"])

    # Step 2: build judge prompt
    prompt = build_judge_prompt(article, full_text)

    # Step 3: call judge
    scores = call_judge(prompt)

    # Step 4: save result
    save_eval_result(article, scores)

    return scores


def run_batch(articles: list) -> list:
    """
    Run judge eval on a list of articles.
    Used for batch mode (all articles in digest.json).

    Args:
        articles: list of article dicts

    Returns:
        list of score dicts from this run
    """
    results = []
    for article in articles:
        print(f"\nEvaluating: {article.get('headline', 'N/A')[:60]}...")
        scores = evaluate_article(article)
        results.append({**article, **scores})
    return results


# ── Entry Point ───────────────────────────────────────────────────────────

def main():
    """
    Main entry point. Supports two modes:
    - Batch mode (default): evaluate all articles in digest.json
    - Single mode (--url): evaluate one article by URL for quick testing
    """
    parser = argparse.ArgumentParser(description="LLM-as-Judge eval for AI Digest")
    parser.add_argument(
        "--url",
        type=str,
        help="Test mode: evaluate a single article by URL instead of full digest.json"
    )
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("[ERROR] ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)

    # ── Single article test mode ──
    if args.url:
        print(f"\nTest mode — evaluating single URL: {args.url}")

        # Look up the URL in digest.json first so we use the real summary
        if not os.path.exists(DIGEST_FILE):
            print(f"[ERROR] {DIGEST_FILE} not found. Run scraper.py and analyzer.py first.")
            sys.exit(1)

        with open(DIGEST_FILE, "r") as f:
            all_articles = json.load(f)

        # Find matching article by URL
        article = next((a for a in all_articles if a.get("url") == args.url), None)

        if not article:
            print(f"[ERROR] URL not found in {DIGEST_FILE}.")
            print(f"        Make sure the URL exactly matches one in digest.json.")
            print(f"        Run this to see all URLs:")
            print(f"        python3 -c \"import json; [print(a['url']) for a in json.load(open('digest.json'))]\"")
            sys.exit(1)

        print(f"  Found in digest.json: {article.get('headline', 'N/A')}")
        print(f"  Summary to evaluate:  {article.get('why_answer', 'N/A')[:100]}...")
        scores = evaluate_article(article)
        print_report([{**article, **scores}])
        return

    # ── Batch mode ──
    if not os.path.exists(DIGEST_FILE):
        print(f"[ERROR] {DIGEST_FILE} not found. Run scraper.py and analyzer.py first.")
        sys.exit(1)

    with open(DIGEST_FILE, "r") as f:
        all_articles = json.load(f)

    if not all_articles:
        print("[INFO] digest.json is empty. Nothing to evaluate.")
        sys.exit(0)

    # Sort by newest first, evaluate latest 5
    all_articles.sort(key=lambda x: x.get("scraped_at", ""), reverse=True)
    articles_to_eval = all_articles[:5]

    print(f"\nBatch mode — evaluating {len(articles_to_eval)} articles from digest.json")
    results = run_batch(articles_to_eval)
    print_report(results)
    print(f"Results saved to {EVAL_RESULTS_FILE}")


if __name__ == "__main__":
    main()