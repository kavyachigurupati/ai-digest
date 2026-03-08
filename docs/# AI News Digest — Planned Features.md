# AI News Digest — Planned Features

This document tracks features planned for future versions of the digest tool.
Current version is a personal prototype: scrape → analyze → display.

---

## Currently Working (v1.0)

- ✅ RSS feed scraping from multiple sources
- ✅ Hacker News API integration (filtered by score)
- ✅ Claude API summarization (no web search — cheap)
- ✅ Gemini fallback if no Anthropic key
- ✅ Token usage and cost printed after each run
- ✅ Append-only digest.json history
- ✅ Deduplication (skips already-seen URLs)
- ✅ Flask web server showing latest 5 articles
- ✅ Cloudflare tunnel for sharing with testers

---

## Planned Features

---

### 🔁 User Article Rating & Feedback Loop (High Priority)

**What it does:**
Allow users to rate each of the 5 articles shown in the browser.
The ratings are saved and used to automatically improve what gets fetched and selected next time.

**How it would work — end to end:**

1. Each article card in the browser shows a thumbs up / thumbs down (or 1–5 star) rating
2. User clicks a rating → saved to `feedback.json` alongside the article URL, source, and category
3. When scraper runs next time, it reads `feedback.json` and:
   - Boosts sources/categories the user rated highly → fetches more from those
   - Reduces or skips sources/categories the user consistently rated poorly
4. When analyzer runs, it passes the user's preference profile to Claude in the prompt:
   - "User prefers: Engineering deep dives, Research Papers"
   - "User dislikes: Generic AI news, Healthcare"
   - Claude uses this to pick better articles from the scraped batch

**Files it would touch:**
- `app.py` — add rating buttons to each article card, add `/rate` POST endpoint
- `feedback.json` — new file, stores all ratings
- `scraper.py` — read feedback to adjust source weighting
- `analyzer.py` — pass preference summary to Claude prompt

**Why this is valuable:**
The tool gets smarter the more you use it. After a week of ratings, it stops showing
articles you don't care about and surfaces more of what you actually read.

---

### ⏰ Scheduled Auto-Run (Medium Priority)

**What it does:**
Automatically run the scraper + analyzer every 24 or 48 hours without manual triggering.

**Options:**
- Simple cron job (Mac/Linux)
- GitHub Actions (cloud-based, runs even when laptop is off)
- APScheduler inside Flask (everything in one process)

**Cron example (runs daily at 8am):**
```
0 8 * * * cd /path/to/digest && poetry run python scraper.py && poetry run python analyzer.py
```

---

### 📧 Email Digest Delivery (Medium Priority)

**What it does:**
Instead of visiting the browser, receive the 5 articles as a formatted email.

**How:** Use SendGrid or Gmail SMTP to send a daily HTML email with the digest.

---

### 💬 Slack Integration (Low Priority)

**What it does:**
Post the digest to a Slack channel automatically after each run.

**How:** Use Slack Incoming Webhooks (similar to Teams webhooks, very simple).

---

### 🗂 Category Filtering in Browser (Low Priority)

**What it does:**
Add filter buttons to the Flask UI so users can view articles by category
(e.g., show only "Research Paper" or only "Engineering").

---

### 📊 Digest History / Archive Page (Low Priority)

**What it does:**
Add a second page to the Flask app that shows all past digests, not just the latest 5.
Useful for browsing older articles you may have missed.

---

### 🌐 Teams Integration (Low Priority)

**What it does:**
Post the digest to a Microsoft Teams channel or group chat.

**Two options:**
- Teams Webhook (simple — channel only)
- Microsoft Graph API (complex — group chats, DMs)

---

### 🔒 GitHub Actions Cloud Automation (Low Priority)

**What it does:**
Run the scraper + analyzer on a schedule in the cloud via GitHub Actions,
so it works even when your laptop is off. Store digest.json as a GitHub artifact
or commit it back to the repo.

---

## Version Roadmap

| Version | Focus |
|---|---|
| v1.0 (now) | Core pipeline working locally |
| v1.1 | User rating system + feedback loop |
| v1.2 | Scheduled auto-run (cron or GitHub Actions) |
| v1.3 | Email or Slack delivery |
| v2.0 | Multi-user support, PostgreSQL, full web UI |