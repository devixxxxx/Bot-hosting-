# 🤖 DarkNova AI Bot v5.0

> **Advanced Dual-Bot Telegram AI System**
> Built by [@MrNewton_2](https://t.me/MrNewton_2)
> Groq + OpenRouter | Agent System | Full Admin Panel | ZIP Code Generation

---

## 📋 Table of Contents

1. [Features](#features)
2. [Project Structure](#project-structure)
3. [Installation Guide](#installation-guide)
4. [Environment Variables](#environment-variables)
5. [Deployment Guides](#deployment-guides)
   - [Render](#render-deployment)
   - [Railway](#railway-deployment)
   - [VPS](#vps-deployment)
6. [How It Works](#how-it-works)
7. [Admin Commands](#admin-commands)
8. [User Commands](#user-commands)
9. [Troubleshooting](#troubleshooting)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 Dual Bot System | Separate Admin Bot + User Bot |
| ⚡ Groq AI | Ultra-fast inference (llama, mixtral, gemma) |
| 🌐 OpenRouter | Access to 100+ free/paid models |
| 🧠 AI Agent | Web search, code execution, weather, calculator |
| 📦 ZIP Generation | Auto-packages multi-file projects as ZIP |
| 💎 Premium System | Daily limits, premium plans, redeem codes |
| 🔒 Force Subscribe | Require channel membership |
| 🛡 Antiflood | Auto-mute flood protection |
| 💬 Memory | Premium users get 40-message conversation memory |
| 🎭 15 Personalities | Switch AI persona instantly from admin panel |
| 🔗 Model Switcher | Change model from admin panel — no code edit needed |
| 📢 Broadcast | Send to all users via User Bot |

---

## 📁 Project Structure

```
darknova-bot/
├── main.py           # Complete bot code (1800+ lines)
├── requirements.txt  # Python dependencies
├── Procfile          # Render/Railway process config
├── runtime.txt       # Python version specification
├── .env.example      # Environment variables template
├── README.md         # This file
└── bot_data.json     # Auto-created: persistent data storage
```

---

## 🛠 Installation Guide

### Prerequisites
- Python 3.11+
- Two Telegram Bot tokens (from @BotFather)
- Groq API key (free at console.groq.com)
- OpenRouter API key (optional, free at openrouter.ai)

### Local Setup

```bash
# 1. Clone or download the files
git clone https://github.com/yourusername/darknova-bot
cd darknova-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment template
cp .env.example .env

# 4. Edit .env with your values
nano .env

# 5. Run the bot
python main.py
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ADMIN_BOT_TOKEN` | ✅ Yes | Admin bot token from @BotFather |
| `USER_BOT_TOKEN` | ✅ Yes | User bot token from @BotFather |
| `ADMIN_ID` | ✅ Yes | Your Telegram user ID |
| `GROQ_API_KEY` | ✅ Yes | Groq API key (free) |
| `OPENROUTER_API_KEY` | ⭕ Optional | OpenRouter key for Agent + OR models |
| `PORT` | ⭕ Optional | Web server port (default: 8080) |

### How to get each value:

**ADMIN_BOT_TOKEN & USER_BOT_TOKEN:**
```
1. Open Telegram → Search @BotFather
2. Send /newbot
3. Follow prompts (name, username)
4. Copy the token → paste in .env
5. Repeat for second bot
```

**ADMIN_ID:**
```
1. Open Telegram → Search @userinfobot
2. Send /start
3. Copy your "Id" number
```

**GROQ_API_KEY:**
```
1. Go to console.groq.com
2. Sign up free
3. API Keys → Create API Key
4. Copy and paste
```

**OPENROUTER_API_KEY:**
```
1. Go to openrouter.ai
2. Sign up free
3. Keys → Create Key
4. Copy and paste
```

---

## 🚀 Deployment Guides

### Render Deployment

> Recommended — Free tier available

**Step 1: Push to GitHub**
```bash
git init
git add .
git commit -m "DarkNova Bot v5.0"
git branch -M main
git remote add origin https://github.com/yourusername/darknova-bot.git
git push -u origin main
```

**Step 2: Create Render Service**
```
1. Go to dashboard.render.com
2. Click "New +" → "Background Worker"
3. Connect your GitHub repository
4. Configure:
   - Name: darknova-bot
   - Runtime: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: python main.py
```

**Step 3: Add Environment Variables**
```
In Render Dashboard → Environment:
ADMIN_BOT_TOKEN = your_value
USER_BOT_TOKEN  = your_value
ADMIN_ID        = your_value
GROQ_API_KEY    = your_value
OPENROUTER_API_KEY = your_value (optional)
PORT            = 8080
```

**Step 4: Deploy**
```
Click "Create Background Worker"
Wait 2-3 minutes for build
Check logs for: "✅ DarkNova v5.0 — Both bots running!"
```

**Health Check URL:**
```
https://your-service-name.onrender.com/
Returns: {"status": "ok", "uptime": "...", "users": N}
```

---

### Railway Deployment

**Step 1: Install Railway CLI**
```bash
npm install -g @railway/cli
railway login
```

**Step 2: Deploy**
```bash
cd darknova-bot
railway init
railway up
```

**Step 3: Set Environment Variables**
```bash
railway variables set ADMIN_BOT_TOKEN=your_value
railway variables set USER_BOT_TOKEN=your_value
railway variables set ADMIN_ID=your_value
railway variables set GROQ_API_KEY=your_value
railway variables set OPENROUTER_API_KEY=your_value
railway variables set PORT=8080
```

**Step 4: Check Logs**
```bash
railway logs
```

---

### VPS Deployment

> For Ubuntu 20.04/22.04 VPS

**Step 1: Server Setup**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-pip python3.11-venv -y

# Install screen (for background running)
sudo apt install screen -y
```

**Step 2: Upload Files**
```bash
# Using SCP
scp -r ./darknova-bot user@your-server-ip:/home/user/

# Or using git
git clone https://github.com/yourusername/darknova-bot
cd darknova-bot
```

**Step 3: Setup Virtual Environment**
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Step 4: Create .env File**
```bash
cp .env.example .env
nano .env
# Fill in your values, save with Ctrl+X
```

**Step 5: Run with Screen**
```bash
screen -S darknova
source venv/bin/activate
python main.py

# Detach: Ctrl+A then D
# Reattach: screen -r darknova
```

**Step 6: Auto-start with Systemd (Optional)**
```bash
sudo nano /etc/systemd/system/darknova.service
```
```ini
[Unit]
Description=DarkNova AI Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/darknova-bot
Environment=PATH=/home/ubuntu/darknova-bot/venv/bin
ExecStart=/home/ubuntu/darknova-bot/venv/bin/python main.py
EnvironmentFile=/home/ubuntu/darknova-bot/.env
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable darknova
sudo systemctl start darknova
sudo systemctl status darknova
```

---

## ⚙️ How It Works

### 1. Project Structure

The bot uses a **dual-bot system**:
- **Admin Bot** — Only accessible by ADMIN_ID. Full control panel.
- **User Bot** — Public facing. Users interact with AI here.

Both bots share the same `bot_data` dictionary (saved to `bot_data.json`).

### 2. User Bot Flow

```
User sends message
       ↓
Check: Banned? Muted? Maintenance? Force Sub?
       ↓
Check: Daily limit reached?
       ↓
Detect: Needs Agent? (search/weather/calculate keywords)
       ↓
   Agent Mode          Normal AI Mode
       ↓                    ↓
Run OpenRouter         Call Groq/OR
with 5 tools           with history
       ↓                    ↓
Return result          Detect code blocks
                            ↓
                    2+ files or 50+ lines?
                       ↓           ↓
                   Send ZIP    Send inline
                               with Copy btn
```

### 3. Admin Panel

Access via `/start` in Admin Bot. Features:
- 📊 Dashboard — real-time stats
- 🤖 AI Settings — model, temp, tokens, persona
- 🔗 AI Provider — switch Groq/OpenRouter, change model ID
- 🧠 Agent Setup — enable/disable, custom agent prompt
- ⚙️ System Prompt — set/view/reset AI personality
- 📢 Broadcast — send to all users
- 💎 Premium — manage premium users
- 🎫 Codes — generate/delete redeem codes
- 🚫 Ban/Warn/Mute system
- 🔒 Force subscribe management
- 🛡 Antiflood configuration

### 4. AI Settings

From admin panel → 🤖 AI Settings:
- **Provider**: Groq (fast) or OpenRouter (more models)
- **Model**: Choose from preset list OR set custom model ID
- **Temperature**: 0.3 (focused) to 2.0 (creative)
- **Max Tokens**: 512 to 32768
- **Personality**: 15 presets or custom system prompt

**To change model without editing code:**
```
Admin Panel → 🔗 AI Provider → Select model
OR
Admin Panel → 🔗 AI Provider → Set Custom Groq/OR Model ID
→ Type: meta-llama/llama-3.3-70b-instruct:free
→ Send → Saved instantly!
```

### 5. Premium System

| Feature | Free | Premium |
|---------|------|---------|
| Daily messages | 20 | Unlimited |
| Conversation memory | ❌ | ✅ 40 msgs |
| Memory duration | — | 48 hours |
| /reset command | ❌ | ✅ |

**Grant premium:**
```
/premium <user_id> <days>    # e.g: /premium 123456 30
/premium <user_id> 0         # 0 = permanent
/removepremium <user_id>     # Remove premium
/setlimit free 30            # Change free limit
/setlimit prem 500           # Change premium limit
```

### 6. Force Subscribe

```
/forcesub @yourchannel    # Enable
/forcesub off             # Disable
```
Users who haven't joined see Join + Check buttons. Bot verifies membership before responding.

### 7. Antiflood

Automatically mutes users who send too many messages too fast.
```
/antiflood on                        # Enable
/antiflood off                       # Disable
/antiflood set 8 10 5                # 8 msgs per 10 sec → mute 5 min
```
Default: 8 messages in 10 seconds → 5 minute mute.

### 8. Memory System

Premium users get conversation context:
- Last 40 messages saved
- Expires after 48 hours
- Manual clear: `/clearmem <user_id>` or `/clearmemall`
- User can clear own: `/reset`

Free users: No memory. Each message is independent.

### 9. Redeem Codes

```bash
# Generate codes
/gencode 30 10     # 10 codes, each valid for 30 days
/gencode 0 5       # 5 permanent codes

# View all codes
/redeeminfo

# Delete a code
/deletecode DN-XXXXXXXX
```

Users redeem via:
```
/redeem DN-XXXXXXXX
```
Or via `/start DN-XXXXXXXX` (deep link).

### 10. Agent System

The AI Agent uses tools for real-world tasks:

| Tool | Trigger Words | Example |
|------|--------------|---------|
| web_search | search, find, news, latest | "search latest iPhone news" |
| calculate | calculate, math, how much | "calculate 15% of 8500" |
| run_python | run code, execute | "run: print(sum(range(100)))" |
| get_weather | weather, mausam | "weather in Mumbai" |
| analyze_task | steps to, plan, how to | "steps to build an app" |

Force agent mode: `/agent <query>`

---

## 📟 Admin Commands

```
/start              Open admin panel
/broadcast <msg>    Send to all users
/ban <id>           Ban user
/unban <id>         Unban user
/warn <id>          Warn user (3 = auto ban)
/mute <id> <mins>   Mute user
/unmute <id>        Unmute user
/premium <id> <days> Grant premium (0=permanent)
/removepremium <id> Remove premium
/setlimit free <n>  Set free daily limit
/setlimit prem <n>  Set premium daily limit
/gencode <days> <n> Generate redeem codes
/deletecode <code>  Delete a code
/redeeminfo         List all codes
/forcesub @channel  Enable force subscribe
/forcesub off       Disable force subscribe
/antiflood on|off   Toggle antiflood
/antiflood set <max> <secs> <mute_mins>
/viewchat <id>      View user chat history
/clearmem <id>      Clear user memory
/clearmemall        Clear all memories
/clearchats         Clear all chat logs
/sysprompt <text>   Set system prompt
/advertise <msg>    Send ad to all users
/export             Export user list
/ping               Check bot latency
```

---

## 👤 User Commands

```
/start              Welcome message
/help               Command list
/about              Bot information
/plan               Check your plan & limits
/reset              Clear conversation memory (Premium)
/redeem <code>      Activate premium code
/contact            Contact admin
/ping               Check latency
/speed              Test AI response speed
/model              Show current AI model
/agent <query>      Force AI Agent mode
```

---

## 🔧 Troubleshooting

### Bot not starting
```bash
# Check all env vars are set
echo $ADMIN_BOT_TOKEN
echo $GROQ_API_KEY

# Check logs
tail -f bot.log
```

### "Conflict: terminated by other getUpdates"
```
This means two instances are running.
Solution: Stop all instances, wait 30 seconds, restart once.

On Render: Manual Deploy → Clear build cache
On VPS: pkill -f "python main.py" → restart
```

### "AI error (401)"
```
Your API key is invalid or expired.
Groq: console.groq.com → regenerate key
OpenRouter: openrouter.ai → create new key
Update env var in Render → Manual deploy
```

### "AI error (429)"
```
Rate limit hit. Solutions:
1. Switch provider (Groq ↔ OpenRouter)
2. Change model from admin panel
3. Reduce user traffic temporarily
```

### Broadcast shows "Sent: 0"
```
Users must have started the User Bot first.
The bot cannot message users who never started it.
```

### Bot responses stopped working
```
1. Check if maintenance mode is ON (Admin → Dashboard)
2. Check if API key is valid
3. Check logs: tail -f bot.log
4. Restart: Admin Panel → 🔄 Restart
```

### Model not working
```
Admin Panel → 🔗 AI Provider → Change model
OR
Admin Panel → 🔗 AI Provider → Set Custom Model ID
→ Enter new working model ID
→ No code changes needed!
```

---

## 🏭 Production Optimization

```python
# Already implemented in v5.0:
# ✅ Async throughout (no blocking calls)
# ✅ Auto-save every 60 seconds
# ✅ RotatingFileHandler (max 5MB, 3 backups)
# ✅ Webhook deletion on startup (prevents conflicts)
# ✅ drop_pending_updates=True (skips old messages)
# ✅ Flood protection (antiflood system)
# ✅ Data locking (asyncio.Lock for thread safety)
# ✅ Error handler (all exceptions logged)
# ✅ Graceful shutdown (saves data on exit)
# ✅ Health check endpoint (/)
# ✅ Premium expiry auto-check
# ✅ Mute expiry auto-check
# ✅ Daily count reset at midnight
```

---

## 📞 Support

Built by [@MrNewton_2](https://t.me/MrNewton_2)

---

*DarkNova AI Bot v5.0 — Production Ready*
