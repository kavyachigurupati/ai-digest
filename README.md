# Update the README.md file

cat > README.md << 'EOF'

# AI Digest

A daily AI/Tech news digest tool that uses Claude API to fetch and summarize the latest AI news.

## Setup

### 1. Check Poetry Version

```bash
poetry --version
```

### 2. Install Dependencies

```bash
poetry install
```

If starting fresh:

```bash
poetry init
poetry add anthropic python-dotenv
```

### 3. Configure API Key

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your_api_key_here
```

### 4. Activate Virtual Environment

```bash
poetry shell
```

### 5. Run the Script

```bash
python ai-digest.py
```

## Features

- Fetches latest AI/ML news from the past 24 hours
- Covers AI research, startup news, new tools, and big tech AI developments
- Uses Claude's web search capabilities for real-time information
  EOF

# Add and commit

git add README.md
git commit -m "Update README with setup instructions"
git push origin master
