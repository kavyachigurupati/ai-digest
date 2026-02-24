import anthropic
from datetime import datetime
import json
from dotenv import load_dotenv
import os

load_dotenv()
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Determine which provider to use
_use_anthropic = bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != 'your_api_key_here')
def get_daily_tech_digest():
    prompt = """
        Find 5 interesting articles from the past 2-3 weeks. Prioritize variety across these topics:

        TOPICS OF INTEREST:
        - Engineering deep dives: How tech companies (Netflix, Uber, Redis, Stripe, Cloudflare, etc.) solve technical problems (architecture, scalability, databases, distributed systems)
        - LLM/AI Infrastructure: GPU developments, data center innovations, energy solutions for AI, chip advances (NVIDIA, AMD, etc.), AI hardware being deployed in unique ways
        - LLM News & Updates: New model releases, capabilities, interesting use cases, discussions from podcasts like "The AI Daily Brief" or insights from people like Chip Huyen
        - Research Papers: New architectures, training efficiency, optimization techniques, papers that challenge existing paradigms (like DeepSeek, transformers, attention mechanisms, etc.)
        - Healthcare Tech: Health monitoring devices, patient tracking systems, medical diagnostic innovations, thermal/infrared imaging applications
        - Energy & Sustainability: Solar power innovations, cooling systems, energy efficiency breakthroughs, battery technology (Tesla or other companies)
        - Team culture & AI adoption: How companies are integrating AI into workflows, organizational changes, engineering practices

        WHAT TO AVOID:
        - Startup funding announcements (unless there's a unique technical angle)
        - Generic AI hype without substance

        PREFERRED SOURCES (if available):
        - Engineering blogs: Netflix Tech Blog, Uber Engineering, Stripe, Cloudflare
        - Tech news: TechCrunch, The Verge, Ars Technica, STAT News, MedTech Dive
        - Research: arXiv, Papers with Code, company research blogs
        - Blogs/Substacks: Simon Willison, Chip Huyen, Pragmatic Engineer
        - Hacker News discussions with technical depth

        For each article, provide:
        1. A concise headline summary
        2. The source URL
        3. Category label
        4. Why it's interesting - START with a relevant question that frames the problem/context, then answer it

        FORMAT INSTRUCTIONS:

        **For Research Papers:**
        Start with: "What problem does this solve?" or "What limitation does this address?"
        Then provide: (1) The problem being solved, (2) The key innovation/technique, (3) The results/impact
        Keep it accessible (high-level to medium technical depth) and include a real-world analogy if the concept is highly technical.

        **For Articles (Engineering/Products/Infrastructure):**
        Start with a relevant question like:
        - "What scaling challenge did this solve?"
        - "Why did their old approach break?"
        - "What bottleneck does this address?"
        - "What gap does this fill?"
        Then explain the solution and why it matters in 2-3 sentences.

        Format each as:
        **[Headline]**
        Source: [URL]
        Category: [Engineering/LLM Infrastructure/Research Paper/Healthcare/Energy/etc.]
        Why: **[Relevant Question]** [Answer with specific details: problem → solution → impact. Include a real-world analogy if highly technical]

        ---

        Try to vary the categories across the 5 articles when possible, but prioritize interesting content over forced variety.
        """
    if _use_anthropic:
        # --- Anthropic path (original code) ---
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search"
            }],
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        result: str = ""
        for block in response.content:
            if block.type == "text":
                result += block.text
        return result
    else:
        # --- Google Gemini fallback (direct REST API, works on Python 3.9) ---
        print("[INFO] No Anthropic key found — falling back to Google Gemini.")
        import requests as req
        base = "https://generativelanguage.googleapis.com/v1beta"

        # 1. Discover available models
        list_resp = req.get(f"{base}/models?key={GOOGLE_API_KEY}", timeout=30)
        list_resp.raise_for_status()
        models = list_resp.json().get("models", [])
        # Pick first model that supports generateContent
        chosen = None
        for m in models:
            if "generateContent" in m.get("supportedGenerationMethods", []):
                chosen = m["name"].replace("models/", "")
                print(f"[INFO] Using model: {chosen}")
                break
        if not chosen:
            raise RuntimeError("No generateContent-capable models found for this API key.")

        # 2. Generate content
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        url = f"{base}/models/{chosen}:generateContent?key={GOOGLE_API_KEY}"
        resp = req.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

# Run it
if __name__ == "__main__":
    print(f"\nAI/Tech News Digest - {datetime.now().strftime('%B %d, %Y')}\n")
    print("=" * 70)
    digest = get_daily_tech_digest()
    print(digest)
    print("=" * 70)