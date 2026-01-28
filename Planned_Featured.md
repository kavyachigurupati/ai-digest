# Create comprehensive README with all features

cat > README.md << 'EOF'

# AI Digest

A daily AI/Tech news digest tool that uses Claude API to fetch and summarize the latest AI news and automatically post to Microsoft Teams.

## Table of Contents

- [Initial Setup](#initial-setup)
- [Running the Script](#running-the-script)
- [Automation Options](#automation-options)
- [Teams Integration](#teams-integration)
- [Troubleshooting](#troubleshooting)

---

## Initial Setup

### 1. Prerequisites

- Python 3.9+
- Poetry (Python package manager)
- Anthropic API Key
- Microsoft Teams account

### 2. Check Poetry Installation

```bash
poetry --version
```

If not installed, visit: https://python-poetry.org/docs/#installation

### 3. Install Dependencies

**Option A: Using existing pyproject.toml**

```bash
poetry install
```

**Option B: Starting from scratch**

```bash
poetry init
poetry add anthropic python-dotenv requests
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Required: Anthropic API Key
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: For Teams Webhook (Channel posting)
TEAMS_WEBHOOK_URL=https://your-org.webhook.office.com/webhookb2/...

# Optional: For Teams Graph API (Group chat posting)
AZURE_CLIENT_ID=your_client_id
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_SECRET=your_client_secret
TEAMS_CHAT_ID=your_group_chat_id
```

**Getting your Anthropic API Key:**

1. Go to https://console.anthropic.com/
2. Sign in or create an account
3. Navigate to API Keys section
4. Create a new key and copy it

### 5. Activate Virtual Environment

```bash
poetry shell
```

---

## Running the Script

### Basic Usage (Console Output Only)

```bash
python ai-digest.py
```

This will:

- Fetch the latest AI/tech news from the past 24 hours
- Display formatted digest in your terminal

### With Teams Integration

```bash
# Post to Teams channel (webhook)
python post-to-teams-channel.py

# Post to Teams group chat (Graph API)
python post-to-teams-chat.py
```

---

## Automation Options

### Option 1: Cron Job (Local Machine - macOS/Linux)

**Best for:** Personal use, testing, when your computer is always on

#### Setup Instructions

1. **Find your Poetry path:**

```bash
which poetry
# Example output: /usr/local/bin/poetry or /opt/homebrew/bin/poetry
```

2. **Find your project path:**

```bash
pwd
# Example: /Users/kavya/Desktop/DEV_MODE/ai_digest
```

3. **Open crontab editor:**

```bash
crontab -e
```

4. **Add automation schedule:**

Replace paths with your actual paths from steps 1 and 2:

```bash
# Run every 2 days at 9 AM
0 9 */2 * * cd /Users/kavya/Desktop/DEV_MODE/ai_digest && /usr/local/bin/poetry run python ai-digest.py

# With Teams webhook (channel)
0 9 */2 * * cd /Users/kavya/Desktop/DEV_MODE/ai_digest && /usr/local/bin/poetry run python post-to-teams-channel.py

# With Teams Graph API (group chat)
0 9 */2 * * cd /Users/kavya/Desktop/DEV_MODE/ai_digest && /usr/local/bin/poetry run python post-to-teams-chat.py
```

#### Cron Schedule Examples

| Schedule        | Description                          |
| --------------- | ------------------------------------ |
| `0 9 */2 * *`   | Every 2 days at 9:00 AM              |
| `0 9 * * 1,3,5` | Monday, Wednesday, Friday at 9:00 AM |
| `0 9 * * *`     | Every day at 9:00 AM                 |
| `0 9 * * 1`     | Every Monday at 9:00 AM              |
| `0 9,15 * * *`  | Every day at 9:00 AM and 3:00 PM     |
| `0 9 1 * *`     | First day of every month at 9:00 AM  |

**Cron Format:** `minute hour day month day_of_week`

5. **Save and exit** (in vim: press `Esc`, type `:wq`, press `Enter`)

6. **Verify your cron jobs:**

```bash
crontab -l
```

7. **View cron logs (macOS):**

```bash
# Check if your cron job ran
log show --predicate 'process == "cron"' --last 1d

# Or redirect output to a log file in your cron command:
0 9 */2 * * cd /path/to/ai_digest && /usr/local/bin/poetry run python ai-digest.py >> /path/to/digest.log 2>&1
```

#### Pros

- ✅ Simple setup
- ✅ Free
- ✅ No external dependencies
- ✅ Direct control

#### Cons

- ❌ Computer must be on and awake
- ❌ No automatic failure notifications
- ❌ Manual log checking required
- ❌ Not suitable for production

---

### Option 2: GitHub Actions (Cloud-based)

**Best for:** Production use, reliability, when you want automation without keeping your computer on

#### Setup Instructions

1. **Push your code to GitHub:**

```bash
git init
git add .
git commit -m "Initial commit: AI digest automation"
git remote add origin https://github.com/YOUR_USERNAME/ai-digest.git
git push -u origin main
```

2. **Add secrets to GitHub:**
   - Go to your repository on GitHub
   - Settings → Secrets and variables → Actions → New repository secret
   - Add these secrets:
     - `ANTHROPIC_API_KEY`
     - `TEAMS_WEBHOOK_URL` (if using webhook)
     - `AZURE_CLIENT_ID` (if using Graph API)
     - `AZURE_TENANT_ID` (if using Graph API)
     - `AZURE_CLIENT_SECRET` (if using Graph API)
     - `TEAMS_CHAT_ID` (if using Graph API)

3. **Create workflow file:**

Create `.github/workflows/ai-digest.yml`:

```yaml
name: AI Digest Automation

on:
  schedule:
    # Runs every 2 days at 9:00 AM UTC
    - cron: "0 9 */2 * *"
  workflow_dispatch: # Allows manual trigger

jobs:
  run-digest:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.9"

      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Install dependencies
        run: poetry install

      - name: Run AI Digest (Console)
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: poetry run python ai-digest.py

      # Optional: Post to Teams Channel
      - name: Post to Teams Channel
        if: success()
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          TEAMS_WEBHOOK_URL: ${{ secrets.TEAMS_WEBHOOK_URL }}
        run: poetry run python post-to-teams-channel.py

    # Optional: Post to Teams Group Chat
    # - name: Post to Teams Group Chat
    #   if: success()
    #   env:
    #     ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    #     AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
    #     AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
    #     AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
    #     TEAMS_CHAT_ID: ${{ secrets.TEAMS_CHAT_ID }}
    #   run: poetry run python post-to-teams-chat.py
```

4. **Commit and push the workflow:**

```bash
git add .github/workflows/ai-digest.yml
git commit -m "Add GitHub Actions automation"
git push
```

5. **Test the workflow:**
   - Go to GitHub → Actions tab
   - Click "AI Digest Automation"
   - Click "Run workflow" → "Run workflow"

#### GitHub Actions Schedule Examples

```yaml
# Every 2 days at 9 AM UTC
- cron: "0 9 */2 * *"

# Monday, Wednesday, Friday at 9 AM UTC
- cron: "0 9 * * 1,3,5"

# Every day at 9 AM UTC
- cron: "0 9 * * *"

# Every Monday at 9 AM UTC
- cron: "0 9 * * 1"

# Every day at 9 AM and 3 PM UTC
- cron: "0 9,15 * * *"
```

**Note:** GitHub Actions uses UTC time. Adjust for your timezone.

#### Pros

- ✅ Runs even when your computer is off
- ✅ Free for public repositories (2,000 minutes/month for private)
- ✅ Automatic logs and notifications
- ✅ Version controlled automation
- ✅ Professional CI/CD approach
- ✅ Can send failure notifications via email

#### Cons

- ❌ Requires GitHub account
- ❌ Need to manage secrets properly
- ❌ Slightly more complex setup
- ❌ 10-15 minute schedule delay (GitHub limitation)

---

## Teams Integration

### Method 1: Teams Webhook (Posts to Channel) - SIMPLE

**Use case:** Post digest to a Teams channel (e.g., #ai-digest, #lunch-and-learn)

#### Setup Steps

1. **In Microsoft Teams:**
   - Go to the channel where you want to post
   - Click the "..." next to the channel name
   - Select "Connectors" or "Manage channel"
   - Search for "Incoming Webhook"
   - Click "Configure"

2. **Configure the webhook:**
   - Name: "AI Digest Bot"
   - Upload an icon (optional)
   - Click "Create"
   - **Copy the webhook URL** (you'll need this!)

3. **Add to `.env` file:**

```env
TEAMS_WEBHOOK_URL=https://your-org.webhook.office.com/webhookb2/xxxxx
```

4. **Install requests library (if not already installed):**

```bash
poetry add requests
```

5. **Test the webhook:**

```bash
poetry run python post-to-teams-channel.py
```

#### Webhook Features

- ✅ Very simple setup (5 minutes)
- ✅ No authentication/OAuth required
- ✅ Reliable message delivery
- ✅ Supports basic formatting (Markdown, cards)
- ❌ Only posts to channels (not group chats)
- ❌ Cannot read messages
- ❌ Limited interactive features

#### Message Format

The webhook supports:

- Plain text
- Markdown formatting (**bold**, _italic_, [links](url))
- Adaptive Cards (rich formatting)
- Mentions (limited)

---

### Method 2: Microsoft Graph API (Posts to Group Chat) - COMPLEX

**Use case:** Post digest to a Teams group chat (private conversation between specific people)

**Important:** This is significantly more complex than webhooks. Only use if you specifically need group chat functionality.

#### Prerequisites

- Azure AD account (free)
- Admin consent for API permissions (may require IT department approval)
- Understanding of OAuth 2.0 flows

#### Setup Steps

##### Step 1: Azure App Registration

1. **Go to Azure Portal:**
   - Visit https://portal.azure.com
   - Sign in with your Microsoft account

2. **Register a new application:**
   - Navigate to "Azure Active Directory"
   - Click "App registrations" in the left menu
   - Click "New registration"
3. **Configure registration:**
   - Name: `AI-Digest-Bot`
   - Supported account types: "Accounts in this organizational directory only"
   - Redirect URI: Leave blank (not needed for daemon apps)
   - Click "Register"

##### Step 2: Get Application Credentials

1. **Copy Application (client) ID:**
   - In the app Overview page
   - Copy the "Application (client) ID"
   - Save as `AZURE_CLIENT_ID`

2. **Copy Directory (tenant) ID:**
   - Also on the Overview page
   - Copy the "Directory (tenant) ID"
   - Save as `AZURE_TENANT_ID`

3. **Create client secret:**
   - Click "Certificates & secrets" in left menu
   - Click "New client secret"
   - Description: "AI Digest Secret"
   - Expires: Choose duration (recommended: 24 months)
   - Click "Add"
   - **IMPORTANT:** Copy the secret VALUE immediately (only shown once!)
   - Save as `AZURE_CLIENT_SECRET`

##### Step 3: Configure API Permissions

1. **Add permissions:**
   - Click "API permissions" in left menu
   - Click "Add a permission"
   - Select "Microsoft Graph"
   - Select "Application permissions" (not Delegated)

2. **Add these specific permissions:**
   - `Chat.ReadWrite.All` - Read and write to all chats
   - `ChatMessage.Send` - Send messages in chats
3. **Grant admin consent:**
   - Click "Grant admin consent for [Your Organization]"
   - Click "Yes" to confirm
   - **Note:** This may require IT admin approval in corporate environments

##### Step 4: Get Group Chat ID

**Method A: Using Microsoft Graph Explorer (Recommended)**

1. Go to https://developer.microsoft.com/en-us/graph/graph-explorer
2. Sign in with your account
3. Run this query:

```
GET https://graph.microsoft.com/v1.0/me/chats
```

4. Find your group chat in the results
5. Copy the `id` field

**Method B: Using PowerShell**

```powershell
# Install Microsoft Graph module
Install-Module Microsoft.Graph -Scope CurrentUser

# Connect
Connect-MgGraph -Scopes "Chat.Read"

# List chats
Get-MgChat | Select-Object Id, Topic, ChatType
```

**Method C: Using Python script**

```python
# You'll need to create a helper script to list chats
# (We can create this together if needed)
```

##### Step 5: Add Credentials to `.env`

```env
# Azure AD App Registration
AZURE_CLIENT_ID=12345678-1234-1234-1234-123456789abc
AZURE_TENANT_ID=87654321-4321-4321-4321-cba987654321
AZURE_CLIENT_SECRET=your_secret_value_here

# Teams Group Chat ID
TEAMS_CHAT_ID=19:abcdef123456789@thread.v2
```

##### Step 6: Install Required Dependencies

```bash
poetry add requests msal
```

- `requests`: HTTP client for API calls
- `msal`: Microsoft Authentication Library (handles OAuth tokens)

##### Step 7: Test the Integration

```bash
poetry run python post-to-teams-chat.py
```

#### Graph API Features

- ✅ Full Teams functionality
- ✅ Post to group chats, channels, and DMs
- ✅ Read message history
- ✅ React to messages
- ✅ Advanced formatting and interactive cards
- ✅ Production-grade solution
- ❌ Complex setup and maintenance
- ❌ Requires token management
- ❌ May need IT approval

#### Authentication Flow

The Microsoft Graph API uses OAuth 2.0 Client Credentials flow:

1. App requests access token from Azure AD
2. Azure AD validates client ID and secret
3. Azure AD returns access token (valid ~60 minutes)
4. App includes token in API requests
5. Token expires → request new token

#### Rate Limits

Microsoft Graph API has rate limits:

- **Per app per tenant:** ~2,000 requests per second
- **Per user:** ~200 requests per minute

For a digest that runs every 2 days, you're well within limits.

#### Troubleshooting Graph API

**Common Issues:**

1. **"Insufficient privileges" error:**
   - Solution: Ensure admin consent was granted
   - Check permissions in Azure Portal

2. **"Invalid client secret":**
   - Solution: Regenerate secret in Azure Portal
   - Update `.env` with new secret

3. **"Chat not found":**
   - Solution: Verify the `TEAMS_CHAT_ID` is correct
   - Ensure the app has access to the chat

4. **Token errors:**
   - Solution: Check `AZURE_TENANT_ID` and `AZURE_CLIENT_ID`
   - Verify secret hasn't expired

---

## Project Structure

```
ai_digest/
├── .env                        # Environment variables (DO NOT COMMIT)
├── .gitignore                  # Git ignore file
├── README.md                   # This file
├── pyproject.toml              # Poetry dependencies
├── poetry.lock                 # Locked dependencies
├── ai-digest.py                # Main digest script (console output)
├── post-to-teams-channel.py    # Teams webhook integration (FUTURE)
├── post-to-teams-chat.py       # Teams Graph API integration (FUTURE)
└── .github/
    └── workflows/
        └── ai-digest.yml       # GitHub Actions automation (FUTURE)
```

---

## Troubleshooting

### Common Issues

#### 1. "ModuleNotFoundError: No module named 'anthropic'"

**Solution:**

```bash
poetry install
poetry shell
```

#### 2. "API key not found"

**Solution:**

- Verify `.env` file exists
- Check `ANTHROPIC_API_KEY` is set correctly
- Ensure no extra spaces or quotes around the key

#### 3. Cron job not running

**Solution:**

```bash
# Check cron is running
sudo systemctl status cron  # Linux
# or
launchctl list | grep cron  # macOS

# Check cron logs
tail -f /var/log/syslog | grep CRON  # Linux
log show --predicate 'process == "cron"' --last 1h  # macOS

# Verify paths are absolute in crontab
which poetry
pwd
```

#### 4. GitHub Actions failing

**Solution:**

- Check Actions tab for error logs
- Verify secrets are set correctly
- Ensure pyproject.toml is committed
- Check workflow syntax at https://crontab.guru/

#### 5. Teams webhook not posting

**Solution:**

- Test webhook URL with curl:

```bash
curl -H "Content-Type: application/json" -d '{"text":"Test"}' YOUR_WEBHOOK_URL
```

- Verify webhook URL hasn't been regenerated
- Check Teams connector is still enabled

#### 6. Graph API authentication errors

**Solution:**

- Verify all Azure credentials in `.env`
- Check admin consent was granted
- Regenerate client secret if expired
- Test credentials with Graph Explorer

---

## Security Best Practices

### 1. Never Commit `.env` File

The `.gitignore` file already includes `.env`, but double-check:

```bash
git status
# .env should NOT appear in untracked or staged files
```

### 2. Rotate Secrets Regularly

- Anthropic API keys: Rotate every 6-12 months
- Azure client secrets: Set expiration, rotate before expiry
- Teams webhook URLs: Regenerate if compromised

### 3. Use Minimum Required Permissions

- For Graph API, only request permissions you actually need
- Regularly review and audit permissions

### 4. Secure Your Machine

- Use disk encryption
- Lock screen when away
- Keep OS and software updated

### 5. GitHub Secrets

- Use repository secrets (not environment secrets for sensitive data)
- Never print secrets in logs
- Use `if: success()` to prevent leaking secrets on failure

---

## Feature Roadmap

### Current Features

- ✅ Fetch latest AI/ML news
- ✅ Console output
- ✅ Environment-based configuration
- ✅ Poetry dependency management

### Planned Features

- ⏳ Teams channel integration (webhook)
- ⏳ Teams group chat integration (Graph API)
- ⏳ GitHub Actions automation
- ⏳ Customizable news categories
- ⏳ Email digest option
- ⏳ Slack integration
- ⏳ RSS feed generation
- ⏳ Digest history/archive
- ⏳ Web UI for configuration

---

## Contributing

This is a personal project, but suggestions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## License

MIT License - Feel free to use and modify

---

## Support

For issues or questions:

- Check the Troubleshooting section above
- Review Anthropic API docs: https://docs.anthropic.com
- Review Microsoft Graph docs: https://docs.microsoft.com/graph
- Open an issue on GitHub

---

## Changelog

### v1.0.0 (Current)

- Initial release
- Basic digest functionality
- Console output
- Documentation for Teams integration
- Documentation for automation options

---

## Acknowledgments

- **Anthropic** - For the Claude API
- **Microsoft** - For Graph API and Teams integration
- **Poetry** - For dependency management
  EOF

# Add and commit the updated README

git add README.md
git commit -m "Add comprehensive documentation for automation and Teams integration"
git push origin master
