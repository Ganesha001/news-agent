# Quick Start Guide - News Agent

Get your automated news agent up and running in 5 minutes! 🚀

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Twilio account (for WhatsApp)

## Step 1: Install

```bash
# Clone or download the project
cd news_agent

# Run the installation script
./install.sh
```

## Step 2: Configure

1. **Edit the environment file:**
   ```bash
   nano .env
   ```

2. **Add your API keys:**
   ```bash
   OPENAI_API_KEY=sk-your-openai-key-here
   TWILIO_ACCOUNT_SID=your-twilio-sid-here
   TWILIO_AUTH_TOKEN=your-twilio-token-here
   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
   WHATSAPP_RECIPIENT_NUMBER=whatsapp:+1234567890
   ```

## Step 3: Test

```bash
# Activate virtual environment
source venv/bin/activate

# Test configuration
python cli.py config

# Test article fetching
python cli.py test-fetch

# Test WhatsApp (optional)
python cli.py test-whatsapp
```

## Step 4: Run

```bash
# Start the news agent
python cli.py run
```

That's it! Your news agent is now running and will:
- Fetch news from trusted sources every 5 minutes
- Detect trending stories using AI
- Validate information for accuracy
- Send WhatsApp notifications for important news

## Quick Commands

```bash
# Check status
python cli.py status

# Send a test briefing
python cli.py send-briefing morning

# Stop the agent
Ctrl+C
```

## Troubleshooting

**"OpenAI API key not found"**
- Make sure you've added your OpenAI API key to `.env`

**"Twilio credentials not found"**
- Verify your Twilio account SID and auth token in `.env`

**"No articles fetched"**
- Check your internet connection
- Verify RSS feed URLs in `config/config.yaml`

**Need help?** Check the full [README.md](README.md) for detailed documentation.

---

**Happy news monitoring! 📰✨** 