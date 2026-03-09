# ⚡ Krish Code Vault

> A production-grade Telegram bot that works as a personal source-code vault, project archive, and shareable code library.

━━━━━━━━━━━━━━

## Features

| Feature | Description |
|---------|-------------|
| 📤 Upload | Upload ZIP projects with full metadata (title, tags, date, status) |
| 📂 Browse | Paginated project listing with beautiful card UI |
| 🔎 Search | Smart ranked search across titles, tags, status, and dates |
| 🔗 Share | Generate deep-link share tokens for any project |
| 👁 Preview | Syntax-highlighted code previews inside Telegram |
| 🧠 AI Summary | GPT-powered project analysis and summaries |
| 🌐 GitHub | Import public repos directly by URL |
| 📊 Stats | Dashboard with download counts and activity tracking |
| ⭐📌 Organize | Favorites and pinned projects |
| 🔒 Security | Admin-only access, rate limiting, path-traversal protection |

━━━━━━━━━━━━━━

## Tech Stack

- **Python 3.11+** with fully async architecture
- **aiogram 3.x** — modern Telegram Bot framework
- **SQLAlchemy 2.x** + **aiosqlite** — async ORM
- **Pygments** — syntax highlighting
- **OpenAI API** — AI summaries
- **GitPython** — GitHub repo import

━━━━━━━━━━━━━━

## Quick Setup

### 1. Clone & Install

```bash
cd code-vault-bot
python -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env`:

```env
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_ID=your_telegram_user_id
OPENAI_API_KEY=sk-your-key-here      # optional
BOT_USERNAME=YourBotUsername          # without @
```

> **Tip:** Get your Telegram user ID from [@userinfobot](https://t.me/userinfobot).

### 3. Run

```bash
python -m bot.main
```

━━━━━━━━━━━━━━

## Project Structure

```
code-vault-bot/
├── bot/
│   ├── main.py          # Entry point
│   ├── config.py        # Settings & env vars
│   ├── database.py      # Async SQLAlchemy engine
│   ├── models.py        # ORM models
│   └── middlewares.py   # Auth, rate-limit, DB session
├── handlers/
│   ├── admin.py         # Dashboard, stats, favorites, pins
│   ├── upload.py        # FSM upload flow
│   ├── search.py        # Smart search
│   ├── share.py         # Share link generation
│   ├── github.py        # GitHub import
│   └── public.py        # Public download interface
├── services/
│   ├── file_manager.py  # File storage
│   ├── share_service.py # Token CRUD
│   ├── search_engine.py # Ranked search
│   ├── ai_summary.py    # OpenAI integration
│   ├── github_service.py# Repo clone & metadata
│   └── preview_generator.py
├── keyboards/
│   ├── admin_menu.py
│   ├── file_actions.py
│   └── status_buttons.py
├── utils/
│   ├── security.py      # Token gen, path guard
│   └── validators.py
├── data/
│   └── files/           # Stored ZIPs
├── .env
├── Dockerfile
├── requirements.txt
└── README.md
```

━━━━━━━━━━━━━━

## Deployment

### Docker

```bash
docker build -t code-vault-bot .
docker run -d --name vault \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  code-vault-bot
```

### Railway

1. Push your code to a GitHub repo
2. Create a new Railway project → link the repo
3. Add environment variables (`BOT_TOKEN`, `ADMIN_ID`, etc.)
4. Railway auto-detects the `Dockerfile` and deploys

### Render

1. Create a new **Background Worker** on Render
2. Connect your GitHub repo
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `python -m bot.main`
5. Add environment variables in the Render dashboard

### VPS (Ubuntu/Debian)

```bash
# Install Python & git
sudo apt update && sudo apt install -y python3.11 python3.11-venv git

# Clone & setup
git clone <your-repo-url> code-vault-bot
cd code-vault-bot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with systemd
sudo tee /etc/systemd/system/vault-bot.service << EOF
[Unit]
Description=Krish Code Vault Bot
After=network.target

[Service]
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python -m bot.main
Restart=always
RestartSec=5
EnvironmentFile=$(pwd)/.env

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable vault-bot
sudo systemctl start vault-bot
```

━━━━━━━━━━━━━━

## Attribution

Every shared file includes:

> *Shared via Krish's Code Vault — @northframe*

━━━━━━━━━━━━━━

## License

Private use. Built for Krish (@northframe).
