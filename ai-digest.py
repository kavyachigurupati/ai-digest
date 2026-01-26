import anthropic
from datetime import datetime
import json



def get_daily_tech_digest():

    client = anthropic.Anthropic(api_key="")
    prompt = """
    Find 5 interesting articles from the past 24 hours about:
    - AI/ML research papers or breakthroughs
    - AI startup news or funding
    - New AI tools or products
    - How big tech companies (Google, Meta, Amazon, Microsoft, OpenAI, Anthropic) are handling AI
    - Interesting software engineering news related to AI
    For each article, provide:
    1. A one-line headline summary (what it's about)
    2. The source URL
    3. Why it's interesting (1 sentence)
    Format each as:
    **[Headline]**
    Source: [URL]
    Why: [One sentence]
    ---
    """
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
    # Extract the text response
    result = ""
    for block in response.content:
        if block.type == "text":
            result += block.text

    return result

# Run it
if __name__ == "__main__":
    print(f"\nAI/Tech News Digest - {datetime.now().strftime('%B %d, %Y')}\n")
    print("=" * 70)
    digest = get_daily_tech_digest()
    print(digest)
    print("=" * 70)