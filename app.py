# app.py
# -------------------------------------------------------------------------
# PURPOSE: Flask web server that reads digest.json and displays the
#          latest 5 articles in the browser.
#
# FLOW:
#   1. On each page request, read digest.json
#   2. Sort entries by scraped_at (newest first)
#   3. Take the top 5
#   4. Render them as HTML
#
# RUN:
#   poetry run python app.py
#   Then open: http://localhost:5000
#   Or via Cloudflare tunnel: your public URL
# -------------------------------------------------------------------------

import json
import os
from datetime import datetime
from flask import Flask, render_template_string

app = Flask(__name__)

# Path to the digest file (same directory as app.py)
DIGEST_FILE = "digest.json"

# Number of articles to show on the page
ARTICLES_TO_SHOW = 5


# ── HTML Template ─────────────────────────────────────────────────────────

# Inline HTML template — no separate template file needed for this prototype
# Uses minimal CSS for clean, readable layout
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Tech Digest</title>
    <style>
        /* ── Base ── */
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #1a1a1a;
            line-height: 1.6;
        }

        /* ── Header ── */
        header {
            background: #1a1a2e;
            color: white;
            padding: 24px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        header h1 { font-size: 22px; font-weight: 600; }
        header .date { font-size: 13px; color: #aaa; }

        /* ── Container ── */
        .container { max-width: 820px; margin: 32px auto; padding: 0 16px; }

        /* ── Article Card ── */
        .card {
            background: white;
            border-radius: 10px;
            padding: 24px;
            margin-bottom: 20px;
            border-left: 4px solid #4f8ef7;
            box-shadow: 0 1px 4px rgba(0,0,0,0.07);
        }

        /* Category badge */
        .badge {
            display: inline-block;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 3px 10px;
            border-radius: 20px;
            background: #eef2ff;
            color: #4f8ef7;
            margin-bottom: 10px;
        }

        /* Headline link */
        .card h2 { font-size: 17px; font-weight: 600; margin-bottom: 6px; }
        .card h2 a { color: #1a1a1a; text-decoration: none; }
        .card h2 a:hover { color: #4f8ef7; }

        /* Source label */
        .source { font-size: 12px; color: #888; margin-bottom: 14px; }

        /* Why section */
        .why-question {
            font-size: 14px;
            font-weight: 600;
            color: #333;
            margin-bottom: 4px;
        }
        .why-answer {
            font-size: 14px;
            color: #555;
        }

        /* ── Empty State ── */
        .empty {
            text-align: center;
            padding: 60px 20px;
            color: #888;
        }
        .empty h2 { font-size: 18px; margin-bottom: 10px; }
        .empty code {
            background: #f0f0f0;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 13px;
        }

        /* ── Footer ── */
        footer {
            text-align: center;
            font-size: 12px;
            color: #bbb;
            padding: 32px 0 48px;
        }
    </style>
</head>
<body>

<header>
    <h1>🗞 AI Tech Digest</h1>
    <span class="date">Last updated: {{ last_updated }}</span>
</header>

<div class="container">

    {% if articles %}
        <p style="font-size:13px; color:#888; margin-bottom:20px;">
            Showing {{ articles|length }} most recent articles
        </p>

        {% for article in articles %}
        <div class="card">
            <div class="badge">{{ article.category }}</div>
            <h2><a href="{{ article.url }}" target="_blank" rel="noopener">{{ article.headline }}</a></h2>
            <div class="source">{{ article.source }}</div>
            <div class="why-question">{{ article.why_question }}</div>
            <div class="why-answer">{{ article.why_answer }}</div>
        </div>
        {% endfor %}

    {% else %}
        <div class="empty">
            <h2>No articles yet</h2>
            <p>Run the scraper and analyzer to populate the digest:</p>
            <br>
            <p><code>poetry run python scraper.py</code></p>
            <p><code>poetry run python analyzer.py</code></p>
        </div>
    {% endif %}

</div>

<footer>
    Powered by Claude API · Personal digest tool
</footer>

</body>
</html>
"""


# ── Routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """
    Main page route.
    Reads digest.json, sorts by date, returns latest 5.
    """
    articles = []
    last_updated = "Never"

    if os.path.exists(DIGEST_FILE):
        with open(DIGEST_FILE, "r") as f:
            all_articles = json.load(f)

        # Sort by scraped_at descending (newest first)
        # The scraped_at field is an ISO timestamp string — string sort works correctly for ISO format
        all_articles.sort(key=lambda x: x.get("scraped_at", ""), reverse=True)

        # Take only the latest N articles
        articles = all_articles[:ARTICLES_TO_SHOW]

        # Format the timestamp of the most recent article for display
        if articles:
            raw_ts = articles[0].get("scraped_at", "")
            try:
                dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                last_updated = dt.strftime("%B %d, %Y at %I:%M %p UTC")
            except Exception:
                last_updated = raw_ts  # fallback: show raw string

    return render_template_string(HTML_TEMPLATE, articles=articles, last_updated=last_updated)


@app.route("/health")
def health():
    """
    Simple health check endpoint.
    Cloudflare and monitoring tools can ping this to verify the server is up.
    """
    return {"status": "ok", "digest_exists": os.path.exists(DIGEST_FILE)}, 200


# ── Entry Point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # debug=True: auto-reloads on code changes — useful during development
    # host="0.0.0.0": makes server accessible on your local network and via Cloudflare tunnel
    # port=5000: default Flask port
    app.run(debug=True, host="0.0.0.0", port=5000)