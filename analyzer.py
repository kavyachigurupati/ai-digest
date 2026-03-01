# analyzer.py
# -------------------------------------------------------------------------
# PURPOSE: Read raw articles from scraper.py, send them to Claude API
#          for selection and summarization, append results to digest.json.
#
# IMPORTANT DIFFERENCE FROM aidigest.py:
#   - Old approach: Claude searches the web itself (expensive)
#   - New approach: We feed Claude pre-scraped articles, Claude only
#                   selects the best 5 and summarizes them (cheap)
#
# FLOW:
#   1. Load raw_articles.json (output from scraper.py)
#   2. Build a prompt with article list embedded
#   3. Call Claude API (same client setup as aidigest.py)
#   4. Parse Claude's JSON response
#   5. Append 5 summarized articles to digest.json
#
# RUN:
#   poetry run python analyzer.py
#   (Always run scraper.py first)
# -------------------------------------------------------------------------

import anthropic
import json
import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv

# ── Environment Setup ─────────────────────────────────────────────────────

# Load .env file (same as aidigest.py)
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Same logic as aidigest.py: use Anthropic if key exists, else fall back to Gemini
_use_anthropic = bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your_api_key_here")

# ── Config ────────────────────────────────────────────────────────────────

RAW_INPUT_FILE = "raw_articles.json"   # written by scraper.py
DIGEST_FILE = "digest.json"            # append-only history file


# ── Prompt Builder ────────────────────────────────────────────────────────

def build_prompt(articles: list) -> str:
    """
    Build the Claude prompt with scraped articles embedded.
    Claude does NOT search the web — it works only with what we provide.

    Args:
        articles: list of raw article dicts from scraper.py

    Returns:
        Full prompt string to send to Claude
    """
    # Format articles as a numbered list for Claude to read
    article_list = ""
    for i, article in enumerate(articles, 1):
        article_list += f"""
{i}. Title: {article['title']}
   URL: {article['url']}
   Source: {article['source']}
   Category: {article['category']}
   Description: {article['description']}
"""

    # Same topic interests and format as original aidigest.py prompt
    # Key difference: we tell Claude NOT to search, only use provided articles
    prompt = f"""
You are a technical content curator. Below is a list of articles fetched from RSS feeds and Hacker News.
DO NOT search the web. Only work with the articles provided below.

Your job:
1. Select the 5 most interesting articles from the list
2. Return a JSON array with exactly 5 objects

TOPICS OF INTEREST (use these to pick the best 5):
- Engineering deep dives: How tech companies (Netflix, Uber, Redis, Stripe, Cloudflare) solve technical problems
- LLM/AI Infrastructure: GPU developments, data center innovations, chip advances
- LLM News & Updates: New model releases, capabilities, interesting use cases
- Research Papers: New architectures, training efficiency, optimization techniques
- Healthcare Tech: Health monitoring devices, diagnostics, imaging
- Energy & Sustainability: Solar, cooling systems, battery technology
- Team culture & AI adoption: How companies integrate AI into workflows

WHAT TO AVOID:
- Startup funding announcements (unless unique technical angle)
- Generic AI hype without substance

ARTICLES TO CHOOSE FROM:
{article_list}

Return ONLY a valid JSON array. No markdown, no backticks, no explanation — just the raw JSON.
Each object must have exactly these fields:
{{
  "headline": "concise title summarizing the article",
  "url": "exact URL from the article list above",
  "source": "source name from the article list",
  "category": "Engineering / LLM Infrastructure / Research Paper / Healthcare / Energy / Culture",
  "why_question": "A relevant question like: What scaling challenge did this solve? or What problem does this address?",
  "why_answer": "2-3 sentences: problem → solution → impact. Include a real-world analogy if highly technical."
}}

For Research Papers, why_question should be: "What problem does this solve?" or "What limitation does this address?"
For Engineering articles, use: "What scaling challenge did this solve?" or "Why did their old approach break?"

Remember: return ONLY the JSON array, nothing else.
"""
    return prompt


# ── Claude API Call (same pattern as aidigest.py) ─────────────────────────

def call_anthropic(prompt: str) -> str:
    """
    Call Anthropic Claude API.
    Uses the same client setup as aidigest.py.
    NOTE: No web_search tool here — Claude only reads what we send it.

    Args:
        prompt: the full prompt string

    Returns:
        Raw text response from Claude
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,   # same as aidigest.py
        messages=[{
            "role": "user",
            "content": prompt
        }]
        # No web_search tool — this is intentional.
        # Scraper.py already fetched the articles; Claude just selects and summarizes.
    )

    # ── Token usage & cost calculation ────────────────────────────────────
    # Pricing for claude-sonnet-4-20250514 (as of 2025):
    #   Input:  $3.00 per million tokens
    #   Output: $15.00 per million tokens
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    total_tokens = input_tokens + output_tokens

    input_cost  = (input_tokens  / 1_000_000) * 3.00
    output_cost = (output_tokens / 1_000_000) * 15.00
    total_cost  = input_cost + output_cost

    print(f"\n  ── Token Usage ──────────────────────────")
    print(f"  Input tokens:   {input_tokens:,}")
    print(f"  Output tokens:  {output_tokens:,}")
    print(f"  Total tokens:   {total_tokens:,}")
    print(f"  ── Cost (USD) ───────────────────────────")
    print(f"  Input cost:     ${input_cost:.6f}")
    print(f"  Output cost:    ${output_cost:.6f}")
    print(f"  Total cost:     ${total_cost:.6f}")
    print(f"  ─────────────────────────────────────────\n")

    # Extract text from response (same loop as aidigest.py)
    result = ""
    for block in response.content:
        if block.type == "text":
            result += block.text

    return result


def call_gemini_fallback(prompt: str) -> str:
    """
    Gemini fallback — same pattern as aidigest.py.
    Used when ANTHROPIC_API_KEY is not set.

    Args:
        prompt: the full prompt string

    Returns:
        Raw text response from Gemini
    """
    import requests as req

    print("[INFO] No Anthropic key found — falling back to Google Gemini.")
    base = "https://generativelanguage.googleapis.com/v1beta"

    # Discover available models (same as aidigest.py)
    list_resp = req.get(f"{base}/models?key={GOOGLE_API_KEY}", timeout=30)
    list_resp.raise_for_status()
    models = list_resp.json().get("models", [])

    # Pick first model that supports generateContent
    chosen = None
    for m in models:
        if "generateContent" in m.get("supportedGenerationMethods", []):
            chosen = m["name"].replace("models/", "")
            print(f"[INFO] Using Gemini model: {chosen}")
            break

    if not chosen:
        raise RuntimeError("No generateContent-capable Gemini models found.")

    # Generate content
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    url = f"{base}/models/{chosen}:generateContent?key={GOOGLE_API_KEY}"
    resp = req.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    # Token usage & cost (Gemini Flash pricing: $0.075/M input, $0.30/M output)
    usage = data.get("usageMetadata", {})
    input_tokens  = usage.get("promptTokenCount", 0)
    output_tokens = usage.get("candidatesTokenCount", 0)
    total_tokens  = usage.get("totalTokenCount", input_tokens + output_tokens)

    input_cost  = (input_tokens  / 1_000_000) * 0.075
    output_cost = (output_tokens / 1_000_000) * 0.30
    total_cost  = input_cost + output_cost

    print(f"\n  ── Token Usage (Gemini) ─────────────────")
    print(f"  Input tokens:   {input_tokens:,}")
    print(f"  Output tokens:  {output_tokens:,}")
    print(f"  Total tokens:   {total_tokens:,}")
    print(f"  ── Cost (USD, estimated) ────────────────")
    print(f"  Input cost:     ${input_cost:.6f}")
    print(f"  Output cost:    ${output_cost:.6f}")
    print(f"  Total cost:     ${total_cost:.6f}")
    print(f"  Note: verify pricing at ai.google.dev for your exact model")
    print(f"  ─────────────────────────────────────────\n")

    return data["candidates"][0]["content"]["parts"][0]["text"]


# ── Digest Writer ─────────────────────────────────────────────────────────

def append_to_digest(articles: list):
    """
    Append new articles to digest.json.
    If digest.json doesn't exist, create it.
    Each article gets a unique ID and timestamp.

    Args:
        articles: list of 5 summarized article dicts from Claude
    """
    # Load existing digest if it exists
    if os.path.exists(DIGEST_FILE):
        with open(DIGEST_FILE, "r") as f:
            digest = json.load(f)
    else:
        digest = []  # start fresh

    # Add metadata to each article and append
    for article in articles:
        article["id"] = str(uuid.uuid4())                          # unique ID
        article["scraped_at"] = datetime.now(timezone.utc).isoformat()  # timestamp

        digest.append(article)

    # Write back the full digest (append-only — old entries are preserved)
    with open(DIGEST_FILE, "w") as f:
        json.dump(digest, f, indent=2)

    print(f"  Appended {len(articles)} articles to {DIGEST_FILE}")
    print(f"  Total articles in digest: {len(digest)}")


# ── Main ──────────────────────────────────────────────────────────────────

def run_analyzer():
    """
    Main analyzer function.
    Reads raw articles, calls Claude, appends results to digest.json.
    """
    print(f"\n{'='*60}")
    print(f"  Analyzer started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Step 1: Load raw articles from scraper.py
    if not os.path.exists(RAW_INPUT_FILE):
        print(f"[ERROR] {RAW_INPUT_FILE} not found. Run scraper.py first.")
        return

    with open(RAW_INPUT_FILE, "r") as f:
        raw_articles = json.load(f)

    if not raw_articles:
        print("[INFO] No new articles to process. Run scraper.py first.")
        return

    print(f"Loaded {len(raw_articles)} raw articles from {RAW_INPUT_FILE}")

    # Step 2: Build prompt with articles embedded
    prompt = build_prompt(raw_articles)

    # Step 3: Call Claude (or Gemini fallback)
    print("\nCalling Claude API ...")
    if _use_anthropic:
        raw_response = call_anthropic(prompt)
    else:
        raw_response = call_gemini_fallback(prompt)

    print("  Claude responded.")

    # Step 4: Parse Claude's JSON response
    # Claude is instructed to return ONLY JSON — strip any accidental whitespace
    try:
        # Remove markdown code fences if Claude accidentally adds them
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            # Strip ```json ... ``` wrapper
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        summarized_articles = json.loads(cleaned)

        if not isinstance(summarized_articles, list):
            raise ValueError("Expected a JSON array from Claude")

    except (json.JSONDecodeError, ValueError) as e:
        print(f"[ERROR] Failed to parse Claude's response as JSON: {e}")
        print(f"[DEBUG] Raw response:\n{raw_response[:500]}")
        return

    print(f"  Parsed {len(summarized_articles)} summarized articles from Claude\n")

    # Step 5: Append to digest.json
    append_to_digest(summarized_articles)

    print(f"\n{'='*60}")
    print(f"  Analyzer done. digest.json updated.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_analyzer()