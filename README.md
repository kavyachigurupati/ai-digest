# AI Digest

A daily AI/Tech news digest tool that fetches and summarizes the latest AI news. It supports both Anthropic's Claude and Google's Gemini as fallback.

## Setup

### 1. Install Dependencies

This project uses [Poetry](https://python-poetry.org/) for dependency management.

```bash
poetry install
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your_anthropic_key_here
GOOGLE_API_KEY=your_google_key_here
```
*(If the Anthropic key is missing or set to `your_api_key_here`, the app will automatically fall back to Google Gemini).*

---

## Usage

### Option 1: Run via Terminal

To generate the digest directly in your terminal:

```bash
poetry run python ai-digest.py
```

### Option 2: Run via Web Server (Live UI)

We have a Flask server that provides a terminal-like streaming UI in the browser.

1. **Start the server:**
   ```bash
   poetry run python server.py
   ```
2. **Open in browser:**
   Go to [http://localhost:3000](http://localhost:3000). The digest will automatically run and stream output to the page on visit.

### Option 3: Publicly Share (Cloudflare Tunnel)

To share the running server with others over the public internet, you can use a free Cloudflare Tunnel.

1. Install Cloudflared (Mac via Homebrew):
   ```bash
   brew install cloudflare/cloudflare/cloudflared
   ```
2. While `server.py` is running, open a **new terminal tab** and run:
   ```bash
   cloudflared tunnel --url http://localhost:3000
   ```
3. Look for the output line containing `trycloudflare.com`. Share that URL! Anyone visiting the link will trigger a fresh run of the AI digest.
