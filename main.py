"""
╔══════════════════════════════════════════════════════════════╗
║          DARKNOVA AI BOT - PRODUCTION READY v4.0            ║
║               Built by @MrNewton_2                          ║
║          Admin Bot + User Bot — Fully Working               ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import json
import re
import time
import asyncio
import logging
import aiohttp
import aiohttp.web
import secrets
import string
import zipfile
import io
from datetime import datetime, timedelta
from functools import wraps
from logging.handlers import RotatingFileHandler

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Bot,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

# ══════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════
logger = logging.getLogger("DarkNova")
logger.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
_fh  = RotatingFileHandler("bot.log", maxBytes=5_000_000, backupCount=3)
_fh.setFormatter(_fmt)
_sh  = logging.StreamHandler()
_sh.setFormatter(_fmt)
logger.addHandler(_fh)
logger.addHandler(_sh)

# ══════════════════════════════════════════════
# ENV
# ══════════════════════════════════════════════
ADMIN_BOT_TOKEN = os.environ.get("ADMIN_BOT_TOKEN", "")
USER_BOT_TOKEN  = os.environ.get("USER_BOT_TOKEN",  "")
ADMIN_ID        = int(os.environ.get("ADMIN_ID", "0"))
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
PORT            = int(os.environ.get("PORT", "8080"))

DATA_FILE = "bot_data.json"
data_lock = asyncio.Lock()
user_bot_obj: Bot = None   # global Bot for broadcast

# ══════════════════════════════════════════════
# PERSONALITIES
# ══════════════════════════════════════════════
PERSONAS = {
    "default": (
        "You are DarkNova — a smart, witty AI assistant built by @MrNewton_2. "
        "You speak Hinglish (Hindi+English mix) when user uses Hindi, otherwise English. "
        "You are helpful, direct, and confident. Always answer clearly. "
        "When building websites/apps/projects with multiple files, provide EACH file in its OWN "
        "separate ```language code block, and mention the filename before each block like **index.html**. "
        "For code always use ``` blocks with the language name."
    ),
    "teacher": (
        "You are DarkNova Teacher. Explain step by step with simple analogies and examples. "
        "Patient and encouraging. Adapt to user's level. Always use ``` for code blocks."
    ),
    "hacker": (
        "You are DarkNova Hacker — an ethical security researcher. "
        "Expert in CTFs, bug bounties, Linux, networking, Python. "
        "Tech slang, precise, efficient. Only ethical/educational content. "
        "Always use ``` for code and commands."
    ),
    "philosopher": (
        "You are DarkNova Philosopher. See deeper meaning in everything. "
        "Ask profound questions, multiple perspectives, beautiful thoughtful language."
    ),
    "comedian": (
        "You are DarkNova Comedian. Witty, punny, dry humor, clever observations. "
        "Still helpful but always fun. Hinglish jokes welcome!"
    ),
    "poet": (
        "You are DarkNova Poet. Beautiful language, metaphors, rhythm, imagery. "
        "Write poems in English, Hindi, or Hinglish. Everything feels artistic."
    ),
    "lawyer": (
        "You are DarkNova Lawyer. Precise, logical, thorough. Break down arguments, "
        "explain legal concepts clearly. Note: educational only, not legal advice."
    ),
    "doctor": (
        "You are DarkNova Doctor. Clear health information, symptoms, conditions, treatments. "
        "Always remind users to consult a real doctor. Calm, caring, thorough."
    ),
    "therapist": (
        "You are DarkNova Therapist. Listen with empathy, validate feelings, ask thoughtful "
        "questions, gently guide. Warm, patient, non-judgmental. "
        "Encourage professional help when needed."
    ),
    "tutor": (
        "You are DarkNova Coding Tutor. Teach programming, debug code, explain algorithms. "
        "Write clean commented code. Python, JS, C++, Java, Rust, Go and more."
    ),
    "storyteller": (
        "You are DarkNova Storyteller. Craft engaging narratives, vivid characters, "
        "interesting plots. Continue stories, write dialogues, build worlds."
    ),
    "fitness": (
        "You are DarkNova Fitness Coach. Workout plans, exercises with proper form, "
        "nutrition advice, motivation. Tailor to level and goals."
    ),
    "chef": (
        "You are DarkNova Chef. Recipes from every cuisine, cooking techniques, "
        "ingredient substitutions, meal planning. Make cooking fun for everyone."
    ),
    "interviewer": (
        "You are DarkNova Interview Coach. Help prepare for technical and HR interviews, "
        "practice answers, review resumes, simulate mock interviews, give sharp feedback."
    ),
    "translator": (
        "You are DarkNova Translator. Translate accurately, explain idioms and cultural context. "
        "Support: Hindi, English, Spanish, French, German, Japanese, Arabic, and more."
    ),
}

# ══════════════════════════════════════════════
# DEFAULT DATA
# ══════════════════════════════════════════════
def _default_data():
    return {
        "users":        {},
        "banned":       [],
        "convos":       {},
        "maint":        False,
        "force_sub":    None,
        "cfg": {
            "model":         "llama-3.1-8b-instant",
            "temperature":   0.9,
            "max_tokens":    4096,
            "personality":   "default",
            "system_prompt": PERSONAS["default"],
        },
        "stats": {
            "total_messages":  0,
            "today_messages":  0,
            "total_broadcasts":0,
            "total_bans":      0,
            "total_mutes":     0,
            "total_tokens":    0,
            "groq_calls":      0,
            "groq_errors":     0,
            "last_reset_date": datetime.now().strftime("%Y-%m-%d"),
        },
        "premium":        {},
        "codes":          {},
        "muted":          {},
        "flood":          {},
        "daily_counts":   {},
        "chats":          {},
        "ad_stats":       {"sent": 0, "failed": 0},
        "broadcast_stats":{"sent": 0, "failed": 0},
        "welcome": (
            "👋 Welcome, {name}!\n\n"
            "🤖 I'm DarkNova AI — your powerful assistant.\n"
            "📦 Plan: {plan}\n"
            "💬 Daily Queries: {daily}/{limit}\n\n"
            "Type anything to start chatting! 🚀"
        ),
        "limits":    {"free": 20, "prem": 99999},
        "antiflood": {"on": True, "max": 8, "win": 10, "mute": 5},
        "start_time": datetime.now().isoformat(),
        "maintenance_msg": "🔧 Bot is under maintenance. Please wait...",
    }

bot_data: dict = {}

# ══════════════════════════════════════════════
# DATA I/O
# ══════════════════════════════════════════════
def load_data():
    global bot_data
    base = _default_data()
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for k, v in saved.items():
                if isinstance(v, dict) and isinstance(base.get(k), dict):
                    base[k] = {**base[k], **v}
                else:
                    base[k] = v
        except Exception as e:
            logger.error(f"Load error: {e}")
    bot_data = base
    if not bot_data["cfg"].get("system_prompt"):
        bot_data["cfg"]["system_prompt"] = PERSONAS["default"]
    logger.info(f"Data loaded. Users: {len(bot_data['users'])}")


async def save_data():
    async with data_lock:
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(bot_data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Save error: {e}")


async def periodic_save():
    while True:
        await asyncio.sleep(60)
        await save_data()

# ══════════════════════════════════════════════
# USER HELPERS
# ══════════════════════════════════════════════
def get_user(uid: int) -> dict:
    k = str(uid)
    if k not in bot_data["users"]:
        bot_data["users"][k] = {
            "id": uid, "name": "User", "username": None,
            "messages": 0, "warnings": 0,
            "joined": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
        }
    return bot_data["users"][k]

def is_banned(uid: int) -> bool:
    return int(uid) in [int(x) for x in bot_data.get("banned", [])]

def is_muted(uid: int) -> bool:
    k = str(uid)
    m = bot_data.get("muted", {})
    if k not in m:
        return False
    until = m[k].get("until")
    if until and datetime.fromisoformat(until) < datetime.now():
        del bot_data["muted"][k]
        return False
    return True

def is_premium(uid: int) -> bool:
    k = str(uid)
    p = bot_data.get("premium", {})
    if k not in p:
        return False
    exp = p[k].get("expiry")
    if exp == "permanent":
        return True
    if exp and datetime.fromisoformat(exp) < datetime.now():
        del bot_data["premium"][k]
        return False
    return True

def get_daily_count(uid: int) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    k  = str(uid)
    dc = bot_data.setdefault("daily_counts", {})
    if k not in dc or dc[k].get("date") != today:
        dc[k] = {"date": today, "count": 0}
    return dc[k]["count"]

def inc_daily(uid: int):
    today = datetime.now().strftime("%Y-%m-%d")
    k  = str(uid)
    dc = bot_data.setdefault("daily_counts", {})
    if k not in dc or dc[k].get("date") != today:
        dc[k] = {"date": today, "count": 0}
    dc[k]["count"] += 1

def get_limit(uid: int) -> int:
    return bot_data["limits"]["prem"] if is_premium(uid) else bot_data["limits"]["free"]

def uptime() -> str:
    s = datetime.fromisoformat(bot_data.get("start_time", datetime.now().isoformat()))
    d = datetime.now() - s
    h, r = divmod(int(d.total_seconds()), 3600)
    m, s = divmod(r, 60)
    return f"{h}h {m}m {s}s"

def reset_today():
    today = datetime.now().strftime("%Y-%m-%d")
    if bot_data["stats"].get("last_reset_date") != today:
        bot_data["stats"]["today_messages"]  = 0
        bot_data["stats"]["last_reset_date"] = today

def split_text(text: str, n: int = 4000) -> list:
    if len(text) <= n:
        return [text]
    parts = []
    while len(text) > n:
        i = text.rfind("\n", 0, n)
        if i == -1: i = n
        parts.append(text[:i])
        text = text[i:].lstrip("\n")
    if text: parts.append(text)
    return parts

# ══════════════════════════════════════════════
# ANTIFLOOD
# ══════════════════════════════════════════════
def check_flood(uid: int) -> bool:
    af = bot_data.get("antiflood", {})
    if not af.get("on"): return False
    k   = str(uid)
    now = time.time()
    fl  = bot_data.setdefault("flood", {})
    fl.setdefault(k, [])
    fl[k] = [t for t in fl[k] if now - t < af.get("win", 10)]
    fl[k].append(now)
    return len(fl[k]) > af.get("max", 8)

def apply_mute_flood(uid: int):
    mins  = bot_data.get("antiflood", {}).get("mute", 5)
    until = (datetime.now() + timedelta(minutes=mins)).isoformat()
    bot_data["muted"][str(uid)] = {"until": until, "reason": "antiflood"}

# ══════════════════════════════════════════════
# CODE / ZIP HELPERS
# ══════════════════════════════════════════════
def extract_blocks(text: str):
    pattern = r"```(\w*)\n?([\s\S]*?)```"
    blocks  = re.findall(pattern, text)
    clean   = re.sub(pattern, "\n[CODE]\n", text)
    return blocks, clean

def has_code(text: str) -> bool:
    return "```" in text

def detect_fname(lang: str, idx: int, ai_text: str) -> str:
    lang = (lang or "txt").lower()
    emap = {
        "python":"py","py":"py","javascript":"js","js":"js",
        "typescript":"ts","ts":"ts","html":"html","css":"css",
        "json":"json","sql":"sql","bash":"sh","shell":"sh","sh":"sh",
        "java":"java","cpp":"cpp","c":"c","php":"php","ruby":"rb",
        "go":"go","rust":"rs","kotlin":"kt","swift":"swift",
        "yaml":"yaml","yml":"yml","markdown":"md","md":"md","xml":"xml",
    }
    ext = emap.get(lang, lang or "txt")
    for pat in [
        r"`([\w\-./]+\." + ext + r")`",
        r"\*\*([\w\-./]+\." + ext + r")\*\*",
        r"(?:file|named?)[:\s]+`?([\w\-./]+\." + ext + r")`?",
    ]:
        m = re.search(pat, ai_text, re.IGNORECASE)
        if m: return m.group(1)
    defaults = {
        "html":["index.html","about.html","contact.html","shop.html","product.html"],
        "css": ["style.css","main.css","shop.css"],
        "js":  ["script.js","main.js","app.js","cart.js"],
        "py":  ["main.py","app.py","server.py","bot.py"],
        "json":["package.json","data.json","config.json"],
        "sh":  ["setup.sh","run.sh"],
        "sql": ["database.sql","schema.sql"],
        "md":  ["README.md"],
    }
    lst = defaults.get(ext, [])
    return lst[idx] if idx < len(lst) else f"file_{idx+1}.{ext}"

def make_zip(files: dict) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buf.seek(0)
    return buf

def needs_zip(blocks: list) -> bool:
    if len(blocks) >= 2: return True
    if len(blocks) == 1 and blocks[0][1].count("\n") > 50: return True
    return False

# ══════════════════════════════════════════════
# GROQ AI
# ══════════════════════════════════════════════
async def call_groq(uid: int, user_msg: str):
    cfg    = bot_data.get("cfg", {})
    prompt = cfg.get("system_prompt") or PERSONAS["default"]
    model  = cfg.get("model", "llama-3.1-8b-instant")
    temp   = float(cfg.get("temperature", 0.9))
    maxt   = int(cfg.get("max_tokens", 4096))

    msgs = [{"role": "system", "content": prompt}]
    if is_premium(uid):
        hist   = bot_data.get("convos", {}).get(str(uid), [])
        cutoff = (datetime.now() - timedelta(hours=48)).isoformat()
        hist   = [m for m in hist if m.get("ts","") > cutoff][-40:]
        msgs  += [{"role": m["role"], "content": m["content"]} for m in hist]
    msgs.append({"role": "user", "content": user_msg})

    bot_data["stats"]["groq_calls"] = bot_data["stats"].get("groq_calls", 0) + 1
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": model, "messages": msgs, "temperature": temp, "max_tokens": maxt},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as r:
                if r.status != 200:
                    bot_data["stats"]["groq_errors"] = bot_data["stats"].get("groq_errors", 0) + 1
                    return "⚠️ AI error. Try again.", 0
                data = await r.json()

        reply  = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        bot_data["stats"]["total_tokens"] = bot_data["stats"].get("total_tokens", 0) + tokens

        if is_premium(uid):
            k = str(uid)
            c = bot_data.setdefault("convos", {})
            c.setdefault(k, [])
            ts = datetime.now().isoformat()
            c[k] += [{"role":"user","content":user_msg,"ts":ts},
                     {"role":"assistant","content":reply,"ts":ts}]
            c[k] = c[k][-40:]

        k = str(uid)
        ch = bot_data.setdefault("chats", {})
        ch.setdefault(k, [])
        ch[k].append({"ts": datetime.now().isoformat(),
                      "user": user_msg[:500], "ai": reply[:500]})
        ch[k] = ch[k][-200:]
        return reply, tokens

    except asyncio.TimeoutError:
        bot_data["stats"]["groq_errors"] = bot_data["stats"].get("groq_errors", 0) + 1
        return "⏱️ Timeout. Try again.", 0
    except Exception as e:
        bot_data["stats"]["groq_errors"] = bot_data["stats"].get("groq_errors", 0) + 1
        logger.error(f"Groq: {e}")
        return f"❌ Error: {str(e)[:80]}", 0

# ══════════════════════════════════════════════
# FORCE SUBSCRIBE
# ══════════════════════════════════════════════
async def check_fsub(uid: int, bot: Bot) -> bool:
    fs = bot_data.get("force_sub")
    if not fs: return True
    try:
        m = await bot.get_chat_member(fs, uid)
        return m.status not in ["left", "kicked", "banned"]
    except Exception:
        return True

def fsub_kb() -> InlineKeyboardMarkup:
    fs = bot_data.get("force_sub", "@channel")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{fs.lstrip('@')}")],
        [InlineKeyboardButton("✅ Check Membership", callback_data="cs")],
    ])

# ══════════════════════════════════════════════
# BROADCAST HELPER
# ══════════════════════════════════════════════
async def broadcast_all(msg: str, tag: str = "📢 *Broadcast*") -> tuple:
    global user_bot_obj
    sent = failed = 0
    for uid_s in list(bot_data.get("users", {}).keys()):
        try:
            await user_bot_obj.send_message(
                int(uid_s), f"{tag}\n\n{msg}", parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Broadcast fail {uid_s}: {e}")
            failed += 1
    return sent, failed

# ══════════════════════════════════════════════
# ADMIN DECORATOR
# ══════════════════════════════════════════════
def admin_only(fn):
    @wraps(fn)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE, *a, **kw):
        uid = (update.message or update.callback_query).from_user.id
        if uid != ADMIN_ID:
            if update.message:
                await update.message.reply_text("🚫 Admin only.")
            else:
                await update.callback_query.answer("🚫 Admin only.", show_alert=True)
            return
        return await fn(update, ctx, *a, **kw)
    return wrapper

# ══════════════════════════════════════════════
# ADMIN MENUS
# ══════════════════════════════════════════════
def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard",     callback_data="a_dash"),
         InlineKeyboardButton("📈 Stats",         callback_data="a_stats")],
        [InlineKeyboardButton("👥 Users",         callback_data="a_users"),
         InlineKeyboardButton("🟢 Live Chats",    callback_data="a_live")],
        [InlineKeyboardButton("🤖 AI Settings",   callback_data="a_ai"),
         InlineKeyboardButton("⚙️ System Prompt", callback_data="a_sysprompt")],
        [InlineKeyboardButton("📢 Broadcast",     callback_data="a_bcast"),
         InlineKeyboardButton("📣 Advertise",     callback_data="a_adinfo")],
        [InlineKeyboardButton("🚫 Ban/Unban",     callback_data="a_baninfo"),
         InlineKeyboardButton("🔇 Mute/Unmute",   callback_data="a_muteinfo")],
        [InlineKeyboardButton("💎 Premium",       callback_data="a_preminfo"),
         InlineKeyboardButton("🎫 Codes",         callback_data="a_codesinfo")],
        [InlineKeyboardButton("🔒 Force Sub",     callback_data="a_fsubinfo"),
         InlineKeyboardButton("🛡 Antiflood",     callback_data="a_floodinfo")],
        [InlineKeyboardButton("💬 View Chat",     callback_data="a_vchat"),
         InlineKeyboardButton("🧹 Clear Memory",  callback_data="a_meminfo")],
        [InlineKeyboardButton("🔧 Maintenance",   callback_data="a_maint"),
         InlineKeyboardButton("🔄 Restart",       callback_data="a_restart")],
        [InlineKeyboardButton("📋 Export Users",  callback_data="a_export"),
         InlineKeyboardButton("⚡ Ping",          callback_data="a_ping")],
        [InlineKeyboardButton("📊 Daily Report",  callback_data="a_daily"),
         InlineKeyboardButton("🗑 Clear Logs",    callback_data="a_clrlogs")],
        [InlineKeyboardButton("🤖 Agent Status",  callback_data="a_agent"),
         InlineKeyboardButton("🔑 Agent Model",   callback_data="a_agentmodel")],
        [InlineKeyboardButton("❌ Close Panel",    callback_data="a_close")],
    ])

def ai_menu() -> InlineKeyboardMarkup:
    cfg  = bot_data.get("cfg", {})
    temp = cfg.get("temperature", 0.9)
    mtok = cfg.get("max_tokens", 4096)
    pers = cfg.get("personality", "default")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Set System Prompt",  callback_data="ai_setprompt")],
        [InlineKeyboardButton("👁 View Current Prompt", callback_data="ai_viewprompt")],
        [InlineKeyboardButton("🎭 Personalities",      callback_data="ai_pers"),
         InlineKeyboardButton(f"✅ {pers}",            callback_data="ai_active")],
        [InlineKeyboardButton(f"🌡 Temp: {temp}",      callback_data="ai_temp"),
         InlineKeyboardButton(f"📏 Tokens: {mtok}",    callback_data="ai_tokens")],
        [InlineKeyboardButton("🔄 Reset Defaults",     callback_data="ai_reset")],
        [InlineKeyboardButton("⬅️ Back",               callback_data="a_main")],
    ])

def pers_menu() -> InlineKeyboardMarkup:
    cur  = bot_data.get("cfg", {}).get("personality", "default")
    btns, row = [], []
    for name in PERSONAS:
        lbl = f"✅ {name}" if name == cur else name
        row.append(InlineKeyboardButton(lbl, callback_data=f"pers_{name}"))
        if len(row) == 2:
            btns.append(row); row = []
    if row: btns.append(row)
    btns.append([InlineKeyboardButton("⬅️ Back", callback_data="a_ai")])
    return InlineKeyboardMarkup(btns)

def temp_menu() -> InlineKeyboardMarkup:
    cur  = float(bot_data.get("cfg", {}).get("temperature", 0.9))
    btns, row = [], []
    for t in [0.3,0.5,0.7,0.9,1.1,1.3,1.5,1.8,2.0]:
        row.append(InlineKeyboardButton(f"✅{t}" if t==cur else str(t), callback_data=f"temp_{t}"))
        if len(row) == 3: btns.append(row); row = []
    if row: btns.append(row)
    btns.append([InlineKeyboardButton("⬅️ Back", callback_data="a_ai")])
    return InlineKeyboardMarkup(btns)

def tok_menu() -> InlineKeyboardMarkup:
    cur  = int(bot_data.get("cfg", {}).get("max_tokens", 4096))
    btns, row = [], []
    for t in [512,1024,2048,4096,8192,16384,32768]:
        row.append(InlineKeyboardButton(f"✅{t}" if t==cur else str(t), callback_data=f"tok_{t}"))
        if len(row) == 3: btns.append(row); row = []
    if row: btns.append(row)
    btns.append([InlineKeyboardButton("⬅️ Back", callback_data="a_ai")])
    return InlineKeyboardMarkup(btns)

BACK = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])

# ══════════════════════════════════════════════
# ADMIN /start
# ══════════════════════════════════════════════
@admin_only
async def adm_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "║  🤖 DarkNova Admin  ║\n"
        "║  Control Panel v4.0 ║\n"
        "╚══════════════════════╝\n\n"
        f"👤 {update.effective_user.first_name}\n"
        f"⏱ Uptime: {uptime()}\n"
        f"👥 Users: {len(bot_data.get('users',{}))}\n\n"
        "Choose an option:",
        reply_markup=main_menu()
    )

# ══════════════════════════════════════════════
# ADMIN CALLBACKS
# ══════════════════════════════════════════════
@admin_only
async def adm_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q  = update.callback_query
    d  = q.data
    await q.answer()

    # ── NAVIGATION ──────────────────────────
    if d == "a_main":
        await q.edit_message_text("🏠 Main Menu", reply_markup=main_menu())
        return
    if d == "a_close":
        await q.edit_message_text("✅ Panel closed. /start to reopen.")
        return

    # ── DASHBOARD ──────────────────────────
    if d == "a_dash":
        reset_today()
        users  = bot_data.get("users", {})
        now    = datetime.now()
        act24  = sum(1 for u in users.values()
                     if (now - datetime.fromisoformat(u.get("last_active", now.isoformat()))).total_seconds() < 86400)
        prems  = sum(1 for uid in users if is_premium(int(uid)))
        stats  = bot_data.get("stats", {})
        cfg    = bot_data.get("cfg", {})
        await q.edit_message_text(
            "📊 *DASHBOARD*\n━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Total Users: `{len(users)}`\n"
            f"🟢 Active 24h: `{act24}`\n"
            f"💎 Premium: `{prems}`\n"
            f"🚫 Banned: `{len(bot_data.get('banned',[]))}`\n"
            f"🔇 Muted: `{len(bot_data.get('muted',{}))}`\n\n"
            f"💬 Total Msgs: `{stats.get('total_messages',0)}`\n"
            f"📅 Today: `{stats.get('today_messages',0)}`\n\n"
            f"🤖 Model: `{cfg.get('model','N/A')}`\n"
            f"🎭 Persona: `{cfg.get('personality','default')}`\n"
            f"🌡 Temp: `{cfg.get('temperature',0.9)}`\n"
            f"📏 Tokens: `{cfg.get('max_tokens',4096)}`\n\n"
            f"🔧 Maintenance: `{'ON' if bot_data.get('maint') else 'OFF'}`\n"
            f"🔒 Force Sub: `{bot_data.get('force_sub') or 'OFF'}`\n"
            f"🛡 Antiflood: `{'ON' if bot_data.get('antiflood',{}).get('on') else 'OFF'}`\n\n"
            f"🪙 Tokens Used: `{stats.get('total_tokens',0)}`\n"
            f"⏱ Uptime: `{uptime()}`\n"
            f"🤖 Agent: `{'✅ Active' if OPENROUTER_API_KEY else '❌ Not set'}`\n"
            f"🧠 Agent Model: `{OPENROUTER_MODEL}`",
            reply_markup=BACK, parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── STATS ──────────────────────────────
    if d == "a_stats":
        s = bot_data.get("stats", {})
        await q.edit_message_text(
            "📈 *STATS*\n━━━━━━━━━━━━━━━━━━━\n"
            f"💬 Messages: `{s.get('total_messages',0)}`\n"
            f"📅 Today: `{s.get('today_messages',0)}`\n"
            f"📢 Broadcasts: `{s.get('total_broadcasts',0)}`\n"
            f"🚫 Bans: `{s.get('total_bans',0)}`\n"
            f"🔇 Mutes: `{s.get('total_mutes',0)}`\n"
            f"🪙 Tokens: `{s.get('total_tokens',0)}`\n"
            f"✅ Groq Calls: `{s.get('groq_calls',0)}`\n"
            f"❌ Groq Errors: `{s.get('groq_errors',0)}`\n"
            f"⏱ Uptime: `{uptime()}`\n"
            f"🤖 Agent: `{'✅ Active' if OPENROUTER_API_KEY else '❌ Not set'}`\n"
            f"🧠 Agent Model: `{OPENROUTER_MODEL}`",
            reply_markup=BACK, parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── USERS ──────────────────────────────
    if d == "a_users":
        users = bot_data.get("users", {})
        lines = [f"👥 *USERS* ({len(users)} total)\n━━━━━━━━━━━━━━━━━━━"]
        for uid, u in list(users.items())[:25]:
            tags = ("💎" if is_premium(int(uid)) else "") + \
                   ("🚫" if is_banned(int(uid)) else "") + \
                   ("🔇" if is_muted(int(uid)) else "") + \
                   (f"⚠️{u.get('warnings',0)}" if u.get("warnings",0) else "")
            lines.append(f"`{uid}` {tags} {u.get('name','?')} @{u.get('username','—')} {u.get('messages',0)}msgs")
        if len(users) > 25:
            lines.append(f"\n...+{len(users)-25} more")
        await q.edit_message_text("\n".join(lines)[:4000], reply_markup=BACK, parse_mode=ParseMode.MARKDOWN)
        return

    # ── LIVE CHATS ──────────────────────────
    if d == "a_live":
        users = bot_data.get("users", {})
        chats = bot_data.get("chats", {})
        now   = datetime.now()
        lines = ["🟢 *LIVE (last 30 min)*\n━━━━━━━━━━━━━━━━━━━"]
        count = 0
        for uid, u in users.items():
            try:
                delta = (now - datetime.fromisoformat(u.get("last_active", now.isoformat()))).total_seconds()
                if delta < 1800:
                    last = ""
                    if uid in chats and chats[uid]:
                        last = chats[uid][-1].get("user", "")[:50]
                    lines.append(f"`{uid}` {u.get('name','?')}\n  💬 {last}\n  ⏰ {int(delta//60)}m ago")
                    count += 1
            except Exception:
                pass
        if not count: lines.append("No active users.")
        await q.edit_message_text("\n".join(lines)[:4000], reply_markup=BACK, parse_mode=ParseMode.MARKDOWN)
        return

    # ── AI MENU ─────────────────────────────
    if d == "a_ai":
        await q.edit_message_text("🤖 *AI Settings*\nConfigure the AI:", reply_markup=ai_menu(), parse_mode=ParseMode.MARKDOWN)
        return
    if d == "ai_viewprompt":
        p = bot_data.get("cfg", {}).get("system_prompt", "Not set")
        await q.edit_message_text(f"📝 *Current Prompt:*\n\n`{p[:3500]}`",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_ai")]]),
                                  parse_mode=ParseMode.MARKDOWN)
        return
    if d == "ai_setprompt":
        ctx.user_data["await"] = "set_prompt"
        await q.edit_message_text(
            "📝 *Set System Prompt*\n\nSend your new system prompt now:\n\n"
            "_Tip: Each personality preset also changes the prompt._",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="a_ai")]]),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if d == "ai_pers":
        await q.edit_message_text("🎭 *Personalities* (✅=active):", reply_markup=pers_menu(), parse_mode=ParseMode.MARKDOWN)
        return
    if d == "ai_temp":
        await q.edit_message_text("🌡 *Temperature* (✅=current):", reply_markup=temp_menu(), parse_mode=ParseMode.MARKDOWN)
        return
    if d == "ai_tokens":
        await q.edit_message_text("📏 *Max Tokens* (✅=current):", reply_markup=tok_menu(), parse_mode=ParseMode.MARKDOWN)
        return
    if d == "ai_active":
        p = bot_data.get("cfg", {}).get("personality", "default")
        await q.answer(f"Active persona: {p}", show_alert=True)
        return
    if d == "ai_reset":
        bot_data["cfg"]["temperature"]   = 0.9
        bot_data["cfg"]["max_tokens"]    = 4096
        bot_data["cfg"]["personality"]   = "default"
        bot_data["cfg"]["system_prompt"] = PERSONAS["default"]
        await save_data()
        await q.answer("✅ Reset to defaults!", show_alert=True)
        await q.edit_message_text("🤖 *AI Settings* (reset done):", reply_markup=ai_menu(), parse_mode=ParseMode.MARKDOWN)
        return
    if d.startswith("pers_"):
        name = d[5:]
        if name in PERSONAS:
            bot_data["cfg"]["personality"]   = name
            bot_data["cfg"]["system_prompt"] = PERSONAS[name]
            await save_data()
            await q.answer(f"✅ Personality → {name}", show_alert=True)
            await q.edit_message_text("🎭 *Personalities* (updated):", reply_markup=pers_menu(), parse_mode=ParseMode.MARKDOWN)
        return
    if d.startswith("temp_"):
        v = float(d[5:])
        bot_data["cfg"]["temperature"] = v
        await save_data()
        await q.answer(f"✅ Temperature → {v}", show_alert=True)
        await q.edit_message_text("🌡 *Temperature* (updated):", reply_markup=temp_menu(), parse_mode=ParseMode.MARKDOWN)
        return
    if d.startswith("tok_"):
        v = int(d[4:])
        bot_data["cfg"]["max_tokens"] = v
        await save_data()
        await q.answer(f"✅ Max Tokens → {v}", show_alert=True)
        await q.edit_message_text("📏 *Max Tokens* (updated):", reply_markup=tok_menu(), parse_mode=ParseMode.MARKDOWN)
        return

    # ── SYSTEM PROMPT ────────────────────────
    if d == "a_sysprompt":
        cfg  = bot_data.get("cfg", {})
        p    = cfg.get("system_prompt", "")
        prev = p[:250] + ("..." if len(p) > 250 else "")
        await q.edit_message_text(
            "⚙️ *SYSTEM PROMPT*\n━━━━━━━━━━━━━━━━━━━\n"
            f"🎭 Persona: `{cfg.get('personality','default')}`\n"
            f"📏 Length: `{len(p)} chars`\n\n"
            f"📝 Preview:\n`{prev}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👁 View Full",        callback_data="ai_viewprompt")],
                [InlineKeyboardButton("✏️ Set Custom Prompt",callback_data="ai_setprompt")],
                [InlineKeyboardButton("🎭 Personality Presets",callback_data="ai_pers")],
                [InlineKeyboardButton("🔄 Reset to Default", callback_data="ai_reset")],
                [InlineKeyboardButton("💬 Set Welcome Msg",  callback_data="a_setwelcome"),
                 InlineKeyboardButton("🔧 Maint Message",    callback_data="a_setmaintmsg")],
                [InlineKeyboardButton("⬅️ Back",             callback_data="a_main")],
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if d == "a_setwelcome":
        ctx.user_data["await"] = "set_welcome"
        cur = bot_data.get("welcome", "")[:200]
        await q.edit_message_text(
            "💬 *Set Welcome Message*\n\nVariables: `{name}` `{plan}` `{daily}` `{limit}`\n\n"
            f"Current:\n`{cur}`\n\nSend new message now:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="a_sysprompt")]]),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if d == "a_setmaintmsg":
        ctx.user_data["await"] = "set_maint_msg"
        cur = bot_data.get("maintenance_msg", "")
        await q.edit_message_text(
            f"🔧 *Set Maintenance Message*\n\nCurrent:\n`{cur}`\n\nSend new message now:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="a_sysprompt")]]),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── BROADCAST ───────────────────────────
    if d == "a_bcast":
        bs = bot_data.get("broadcast_stats", {})
        await q.edit_message_text(
            "📢 *BROADCAST*\n━━━━━━━━━━━━━━━━━━━\n"
            f"Last: ✅`{bs.get('sent',0)}` | ❌`{bs.get('failed',0)}`\n\n"
            "Use: `/broadcast your message`\nSends to ALL users.",
            reply_markup=BACK, parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── ADVERTISE ───────────────────────────
    if d == "a_adinfo":
        ad = bot_data.get("ad_stats", {})
        await q.edit_message_text(
            "📣 *ADVERTISE*\n━━━━━━━━━━━━━━━━━━━\n"
            f"Sent: `{ad.get('sent',0)}` | Failed: `{ad.get('failed',0)}`\n\n"
            "Use: `/advertise your ad text`",
            reply_markup=BACK, parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── BAN ─────────────────────────────────
    if d == "a_baninfo":
        await q.edit_message_text(
            f"🚫 *BAN SYSTEM*\n━━━━━━━━━━━━━━━━━━━\n"
            f"Banned: `{len(bot_data.get('banned',[]))}`\n\n"
            "`/ban <id>` — Ban user\n`/unban <id>` — Unban\n`/warn <id>` — Warn (3=auto ban)",
            reply_markup=BACK, parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── MUTE ─────────────────────────────────
    if d == "a_muteinfo":
        muted = bot_data.get("muted", {})
        lines = [f"🔇 *MUTE SYSTEM*\n━━━━━━━━━━━━━━━━━━━\nMuted: `{len(muted)}`\n"]
        for uid, info in list(muted.items())[:10]:
            u = bot_data.get("users",{}).get(uid,{})
            lines.append(f"`{uid}` {u.get('name','?')} until `{info.get('until','')[:16]}`")
        lines.append("\n`/mute <id> <mins>` | `/unmute <id>`")
        await q.edit_message_text("\n".join(lines), reply_markup=BACK, parse_mode=ParseMode.MARKDOWN)
        return

    # ── PREMIUM ──────────────────────────────
    if d == "a_preminfo":
        prem = bot_data.get("premium", {})
        lims = bot_data.get("limits", {})
        lines = [f"💎 *PREMIUM*\n━━━━━━━━━━━━━━━━━━━\nActive: `{len(prem)}`\n"
                 f"Free limit: `{lims.get('free',20)}/day`\nPrem limit: `{lims.get('prem',99999)}/day`\n"]
        for uid, info in list(prem.items())[:8]:
            u   = bot_data.get("users",{}).get(uid,{})
            exp = info.get("expiry","?")
            lines.append(f"💎 `{uid}` {u.get('name','?')} — {'♾️' if exp=='permanent' else exp[:10]}")
        lines.append("\n`/premium <id> <days>` (0=perm)\n`/removepremium <id>`\n`/setlimit free|prem <n>`")
        await q.edit_message_text("\n".join(lines), reply_markup=BACK, parse_mode=ParseMode.MARKDOWN)
        return

    # ── CODES ────────────────────────────────
    if d == "a_codesinfo":
        codes  = bot_data.get("codes", {})
        active = [c for c,v in codes.items() if not v.get("used")]
        lines  = [f"🎫 *CODES*\n━━━━━━━━━━━━━━━━━━━\nTotal:`{len(codes)}` Active:`{len(active)}`\n"]
        for c in active[:12]:
            lines.append(f"`{c}` — {codes[c].get('days','?')}d")
        if len(active) > 12: lines.append(f"...+{len(active)-12} more")
        lines.append("\n`/gencode <days> <amount>`\n`/deletecode <code>`\n`/redeeminfo`")
        await q.edit_message_text("\n".join(lines)[:4000], reply_markup=BACK, parse_mode=ParseMode.MARKDOWN)
        return

    # ── FORCE SUB ────────────────────────────
    if d == "a_fsubinfo":
        fs = bot_data.get("force_sub")
        await q.edit_message_text(
            f"🔒 *FORCE SUB*\n━━━━━━━━━━━━━━━━━━━\nStatus: `{'ON — '+fs if fs else 'OFF'}`\n\n"
            "`/forcesub @channel` | `/forcesub off`",
            reply_markup=BACK, parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── ANTIFLOOD ────────────────────────────
    if d == "a_floodinfo":
        af = bot_data.get("antiflood", {})
        await q.edit_message_text(
            f"🛡 *ANTIFLOOD*\n━━━━━━━━━━━━━━━━━━━\n"
            f"Status: `{'ON' if af.get('on') else 'OFF'}`\n"
            f"Limit: `{af.get('max',8)} msgs` / `{af.get('win',10)}s`\n"
            f"Auto-mute: `{af.get('mute',5)} min`\n\n"
            "`/antiflood on|off`\n`/antiflood set <max> <secs> <mute_mins>`",
            reply_markup=BACK, parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── VIEW CHAT ────────────────────────────
    if d == "a_vchat":
        await q.edit_message_text(
            "💬 *VIEW CHAT*\n━━━━━━━━━━━━━━━━━━━\n\nUse: `/viewchat <user_id>`\nShows last 15 messages.",
            reply_markup=BACK, parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── MEMORY INFO ──────────────────────────
    if d == "a_meminfo":
        await q.edit_message_text(
            "🧹 *CLEAR MEMORY*\n━━━━━━━━━━━━━━━━━━━\n\n"
            "`/clearmem <id>` — One user\n`/clearmemall` — All memories\n`/clearchats` — All logs",
            reply_markup=BACK, parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── MAINTENANCE TOGGLE ───────────────────
    if d == "a_maint":
        bot_data["maint"] = not bot_data.get("maint", False)
        await save_data()
        s = "ON 🔧" if bot_data["maint"] else "OFF ✅"
        await q.answer(f"Maintenance {s}", show_alert=True)
        await q.edit_message_text("🏠 Main Menu", reply_markup=main_menu())
        return

    # ── RESTART ──────────────────────────────
    if d == "a_restart":
        bot_data["convos"] = {}
        bot_data["flood"]  = {}
        await save_data()
        await q.answer("✅ Memory cleared!", show_alert=True)
        await q.edit_message_text("🏠 Main Menu", reply_markup=main_menu())
        return

    # ── EXPORT ───────────────────────────────
    if d == "a_export":
        users = bot_data.get("users", {})
        lines = [f"📋 *EXPORT* ({len(users)} users)\n━━━━━━━━━━━━━━━━━━━"]
        for uid, u in users.items():
            pl = "💎" if is_premium(int(uid)) else "🆓"
            st = "🚫" if is_banned(int(uid)) else ("🔇" if is_muted(int(uid)) else "✅")
            lines.append(f"{st}{pl} `{uid}` {u.get('name','?')} @{u.get('username','—')} {u.get('messages',0)}msgs")
        for chunk in split_text("\n".join(lines)):
            await q.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        await q.edit_message_text("📋 Export sent above ⬆️", reply_markup=BACK)
        return

    # ── PING ─────────────────────────────────
    if d == "a_ping":
        t  = time.time()
        await q.answer("🏓 Pong!")
        ms = int((time.time()-t)*1000)
        await q.edit_message_text(f"⚡ *Ping:* `{ms}ms`\n⏱ Uptime: `{uptime()}`",
                                   reply_markup=BACK, parse_mode=ParseMode.MARKDOWN)
        return

    # ── DAILY REPORT ─────────────────────────
    if d == "a_daily":
        reset_today()
        stats = bot_data.get("stats", {})
        users = bot_data.get("users", {})
        today = datetime.now().strftime("%Y-%m-%d")
        new   = sum(1 for u in users.values() if u.get("joined","")[:10]==today)
        await q.edit_message_text(
            f"📊 *DAILY — {today}*\n━━━━━━━━━━━━━━━━━━━\n"
            f"💬 Messages: `{stats.get('today_messages',0)}`\n"
            f"👤 New users: `{new}`\n"
            f"🪙 Tokens: `{stats.get('total_tokens',0)}`\n"
            f"✅ API calls: `{stats.get('groq_calls',0)}`\n"
            f"❌ Errors: `{stats.get('groq_errors',0)}`\n"
            f"⏱ Uptime: `{uptime()}`\n"
            f"🤖 Agent: `{'✅ Active' if OPENROUTER_API_KEY else '❌ Not set'}`\n"
            f"🧠 Agent Model: `{OPENROUTER_MODEL}`",
            reply_markup=BACK, parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── CLEAR LOGS ───────────────────────────
    if d == "a_clrlogs":
        bot_data["chats"] = {}
        await save_data()
        await q.answer("✅ Logs cleared!", show_alert=True)
        await q.edit_message_text("🏠 Main Menu", reply_markup=main_menu())
        return

    # ── AGENT STATUS ──────────────────────────
    if d == "a_agent":
        key_set = bool(OPENROUTER_API_KEY)
        tools_list = (
            "Available Tools:\n"
            "- web_search: Internet search\n"
            "- run_code: Python execution\n"
            "- analyze_task: Multi-step planning\n"
            "- get_weather: Live weather\n"
            "- calculate: Math calculations"
        )
        status_txt = "ACTIVE" if key_set else "NOT CONFIGURED"
        txt = (
            f"Agent Status: {status_txt}\n"
            f"Model: {OPENROUTER_MODEL}\n\n"
            f"{tools_list}\n\n"
            "Auto-triggers: search, weather, calculate, news, latest, find...\n\n"
            "To enable: set OPENROUTER_API_KEY in Render env vars."
        )
        await q.edit_message_text(txt, reply_markup=BACK)
        return

    if d == "a_agentmodel":
        txt = (
            f"Agent Model: {OPENROUTER_MODEL}\n\n"
            "Free models on OpenRouter:\n"
            "- meta-llama/llama-3.3-70b-instruct:free\n"
            "- meta-llama/llama-3.1-8b-instruct:free\n"
            "- google/gemma-2-9b-it:free\n"
            "- microsoft/phi-3-mini-128k-instruct:free\n\n"
            "To change: set OPENROUTER_MODEL in Render env vars."
        )
        await q.edit_message_text(txt, reply_markup=BACK)
        return

# ══════════════════════════════════════════════
# ADMIN TEXT (awaiting input)
# ══════════════════════════════════════════════
@admin_only
async def adm_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    aw   = ctx.user_data.get("await")
    text = update.message.text.strip()

    if aw == "set_prompt":
        bot_data["cfg"]["system_prompt"] = text
        bot_data["cfg"]["personality"]   = "custom"
        ctx.user_data.pop("await", None)
        await save_data()
        await update.message.reply_text(
            f"✅ *Prompt updated!*\n\nPreview:\n```\n{text[:300]}\n```\nLength: {len(text)} chars",
            parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu()
        )
    elif aw == "set_welcome":
        bot_data["welcome"] = text
        ctx.user_data.pop("await", None)
        await save_data()
        await update.message.reply_text(
            f"✅ *Welcome updated!*\n\n`{text[:200]}`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu()
        )
    elif aw == "set_maint_msg":
        bot_data["maintenance_msg"] = text
        ctx.user_data.pop("await", None)
        await save_data()
        await update.message.reply_text(
            f"✅ *Maintenance msg updated!*\n\n`{text[:200]}`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu()
        )
    else:
        await update.message.reply_text("Use /start to open admin panel.", reply_markup=main_menu())

# ══════════════════════════════════════════════
# ADMIN COMMANDS
# ══════════════════════════════════════════════
@admin_only
async def adm_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /broadcast <message>"); return
    msg = " ".join(ctx.args)
    st  = await update.message.reply_text(f"📢 Sending to {len(bot_data.get('users',{}))} users...")
    s, f = await broadcast_all(msg)
    bot_data["stats"]["total_broadcasts"] = bot_data["stats"].get("total_broadcasts",0)+1
    bot_data["broadcast_stats"] = {"sent":s,"failed":f}
    await save_data()
    await st.edit_text(f"✅ Done! Sent:`{s}` Failed:`{f}`", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /ban <id>"); return
    try: uid = int(ctx.args[0])
    except ValueError: await update.message.reply_text("Invalid ID."); return
    if uid not in [int(x) for x in bot_data.get("banned",[])]:
        bot_data["banned"].append(uid)
        bot_data["stats"]["total_bans"] = bot_data["stats"].get("total_bans",0)+1
    await save_data()
    await update.message.reply_text(f"🚫 User `{uid}` banned.", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /unban <id>"); return
    try: uid = int(ctx.args[0])
    except ValueError: await update.message.reply_text("Invalid ID."); return
    bot_data["banned"] = [x for x in bot_data.get("banned",[]) if int(x)!=uid]
    await save_data()
    await update.message.reply_text(f"✅ User `{uid}` unbanned.", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_warn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /warn <id>"); return
    try: uid = int(ctx.args[0])
    except ValueError: await update.message.reply_text("Invalid ID."); return
    u = get_user(uid)
    u["warnings"] = u.get("warnings",0)+1
    if u["warnings"] >= 3:
        if uid not in [int(x) for x in bot_data.get("banned",[])]:
            bot_data["banned"].append(uid)
        await save_data()
        await update.message.reply_text(f"⚠️ `{uid}` — {u['warnings']} warnings → *AUTO BANNED!*", parse_mode=ParseMode.MARKDOWN)
    else:
        await save_data()
        await update.message.reply_text(f"⚠️ Warned `{uid}`. Warnings: `{u['warnings']}/3`", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_mute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args)<2: await update.message.reply_text("Usage: /mute <id> <mins>"); return
    try: uid,mins = int(ctx.args[0]),int(ctx.args[1])
    except ValueError: await update.message.reply_text("Invalid args."); return
    until = (datetime.now()+timedelta(minutes=mins)).isoformat()
    bot_data["muted"][str(uid)] = {"until":until,"reason":"admin"}
    bot_data["stats"]["total_mutes"] = bot_data["stats"].get("total_mutes",0)+1
    await save_data()
    await update.message.reply_text(f"🔇 User `{uid}` muted `{mins}` min.", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_unmute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /unmute <id>"); return
    bot_data["muted"].pop(str(ctx.args[0]),None)
    await save_data()
    await update.message.reply_text(f"✅ User `{ctx.args[0]}` unmuted.", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_premium(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args)<2: await update.message.reply_text("Usage: /premium <id> <days> (0=perm)"); return
    try: uid,days = int(ctx.args[0]),int(ctx.args[1])
    except ValueError: await update.message.reply_text("Invalid args."); return
    exp = "permanent" if days==0 else (datetime.now()+timedelta(days=days)).isoformat()
    bot_data["premium"][str(uid)] = {"expiry":exp,"granted":datetime.now().isoformat()}
    await save_data()
    await update.message.reply_text(f"💎 `{uid}` premium granted ({'♾️ permanent' if days==0 else str(days)+' days'}).", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_remprem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /removepremium <id>"); return
    bot_data["premium"].pop(str(ctx.args[0]),None)
    await save_data()
    await update.message.reply_text(f"✅ Premium removed from `{ctx.args[0]}`.", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_setlimit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args)<2: await update.message.reply_text("Usage: /setlimit free|prem <n>"); return
    plan = ctx.args[0].lower()
    try: n = int(ctx.args[1])
    except ValueError: await update.message.reply_text("Invalid number."); return
    if plan not in ("free","prem"): await update.message.reply_text("Plan: free or prem"); return
    bot_data["limits"][plan] = n
    await save_data()
    await update.message.reply_text(f"✅ `{plan}` limit → `{n}/day`", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_gencode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args)<2: await update.message.reply_text("Usage: /gencode <days> <amount>"); return
    try: days,amt = int(ctx.args[0]),min(int(ctx.args[1]),50)
    except ValueError: await update.message.reply_text("Invalid args."); return
    ab    = string.ascii_uppercase+string.digits
    codes = []
    for _ in range(amt):
        c = "DN-"+"".join(secrets.choice(ab) for _ in range(8))
        bot_data["codes"][c] = {"days":days,"used":False,"created":datetime.now().isoformat()}
        codes.append(c)
    await save_data()
    txt = f"🎫 `{amt}` code(s) — `{days}` days:\n\n" + "\n".join(f"`{c}`" for c in codes)
    await update.message.reply_text(txt[:4000], parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_delcode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /deletecode <code>"); return
    c = ctx.args[0].upper()
    if c in bot_data.get("codes",{}):
        del bot_data["codes"][c]; await save_data()
        await update.message.reply_text(f"✅ Code `{c}` deleted.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Code not found.")

@admin_only
async def adm_redeeminfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    codes = bot_data.get("codes",{})
    if not codes: await update.message.reply_text("No codes yet."); return
    lines = ["🎫 *All Codes:*\n"]
    for c,v in codes.items():
        lines.append(f"`{c}` — {v.get('days','?')}d — {'✅Used' if v.get('used') else '🟢Active'}")
    for chunk in split_text("\n".join(lines)):
        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_forcesub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /forcesub @ch OR /forcesub off"); return
    if ctx.args[0].lower()=="off":
        bot_data["force_sub"]=None
    else:
        bot_data["force_sub"] = ctx.args[0] if ctx.args[0].startswith("@") else "@"+ctx.args[0]
    await save_data()
    await update.message.reply_text(f"✅ Force sub → `{bot_data['force_sub'] or 'OFF'}`", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_antiflood(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /antiflood on|off|set <max> <win> <mute>"); return
    af  = bot_data.setdefault("antiflood",{})
    sub = ctx.args[0].lower()
    if sub=="on":   af["on"]=True;  await update.message.reply_text("✅ Antiflood ON.")
    elif sub=="off": af["on"]=False; await update.message.reply_text("✅ Antiflood OFF.")
    elif sub=="set" and len(ctx.args)>=4:
        try:
            af["max"]=int(ctx.args[1]); af["win"]=int(ctx.args[2]); af["mute"]=int(ctx.args[3])
            await update.message.reply_text(f"✅ `{af['max']}` msgs/`{af['win']}`s → mute `{af['mute']}`min", parse_mode=ParseMode.MARKDOWN)
        except ValueError: await update.message.reply_text("Invalid values.")
    await save_data()

@admin_only
async def adm_viewchat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /viewchat <id>"); return
    uid   = str(ctx.args[0])
    chats = bot_data.get("chats",{}).get(uid,[])
    if not chats: await update.message.reply_text("No history."); return
    lines = [f"💬 *Chat — {uid}* (last 15)\n━━━━━━━━━━━━━━━━━━━"]
    for c in chats[-15:]:
        lines.append(f"\n⏰ `{c.get('ts','')[:16]}`\n👤 {c.get('user','')[:100]}\n🤖 {c.get('ai','')[:100]}")
    for chunk in split_text("\n".join(lines)):
        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_clearmem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /clearmem <id>"); return
    bot_data["convos"].pop(str(ctx.args[0]),None)
    await save_data()
    await update.message.reply_text(f"✅ Memory cleared for `{ctx.args[0]}`.", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_clearmemall(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_data["convos"]={}; await save_data()
    await update.message.reply_text("✅ All memories cleared.")

@admin_only
async def adm_clearchats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_data["chats"]={}; await save_data()
    await update.message.reply_text("✅ All chat logs cleared.")

@admin_only
async def adm_sysprompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /sysprompt <prompt text>"); return
    p = " ".join(ctx.args)
    bot_data["cfg"]["system_prompt"] = p
    bot_data["cfg"]["personality"]   = "custom"
    await save_data()
    await update.message.reply_text(f"✅ Prompt updated!\n```\n{p[:300]}\n```", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_advertise(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /advertise <text>"); return
    msg = " ".join(ctx.args)
    st  = await update.message.reply_text("📣 Sending ad...")
    s,f = await broadcast_all(msg, "📣 *Advertisement*")
    bot_data["ad_stats"]["sent"]   = bot_data["ad_stats"].get("sent",0)+s
    bot_data["ad_stats"]["failed"] = bot_data["ad_stats"].get("failed",0)+f
    await save_data()
    await st.edit_text(f"📣 Done! ✅`{s}` ❌`{f}`", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t=time.time(); msg=await update.message.reply_text("🏓...")
    ms=int((time.time()-t)*1000)
    await msg.edit_text(f"⚡ `{ms}ms` | ⏱ `{uptime()}`", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users = bot_data.get("users",{})
    lines = [f"📋 *EXPORT* ({len(users)} users)\n━━━━━━━━━━━━━━━━━━━"]
    for uid,u in users.items():
        pl = "💎" if is_premium(int(uid)) else "🆓"
        st = "🚫" if is_banned(int(uid)) else ("🔇" if is_muted(int(uid)) else "✅")
        lines.append(f"{st}{pl} `{uid}` {u.get('name','?')} @{u.get('username','—')} {u.get('messages',0)}msgs ⚠️{u.get('warnings',0)}")
    for chunk in split_text("\n".join(lines)):
        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


# ══════════════════════════════════════════════
# OPENROUTER AGENT SYSTEM
# Full Agent: Web Search + Code + Multi-step
# Model: meta-llama/llama-3.3-70b-instruct:free
# ══════════════════════════════════════════════

OPENROUTER_API_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL    = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── AGENT TOOLS DEFINITION ─────────────────
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the internet for real-time information, news, current events, "
                "prices, weather, sports scores, or anything that needs up-to-date data. "
                "Use this when user asks about recent events or live information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on the web"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_code",
            "description": (
                "Execute Python code and return the output. Use this to: "
                "calculate math, process data, solve algorithms, test code snippets, "
                "convert units, generate charts data, or any computation task."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (default: python)",
                        "enum": ["python"]
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_task",
            "description": (
                "Break down a complex task into step-by-step plan and execute it. "
                "Use this for multi-step problems that need planning before execution, "
                "like building a project, research tasks, or complex analysis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The complex task to analyze and plan"
                    },
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of steps to complete the task"
                    }
                },
                "required": ["task", "steps"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather information for a city or location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or location to get weather for"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Perform mathematical calculations, unit conversions, currency estimates, "
                "statistics, or any numerical computation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression or calculation to perform"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]

AGENT_SYSTEM_PROMPT = """You are DarkNova Agent — an advanced AI assistant with real tools.
Built by @MrNewton_2.

You have access to these tools:
1. web_search — Search internet for real-time info
2. run_code — Execute Python code
3. analyze_task — Plan and break down complex tasks
4. get_weather — Get weather for any city
5. calculate — Math calculations

RULES:
- Always use tools when needed instead of guessing
- For current events/news → use web_search
- For math/computation → use calculate or run_code
- For complex tasks → use analyze_task first
- Chain multiple tools if needed
- Respond in the same language as the user (Hindi/English/Hinglish)
- Be concise and helpful
"""


# ── TOOL EXECUTOR ──────────────────────────
async def execute_tool(tool_name: str, tool_args: dict) -> str:
    """Execute a tool and return string result"""

    if tool_name == "web_search":
        query = tool_args.get("query", "")
        try:
            url = f"https://ddg-api.herokuapp.com/search?query={aiohttp.helpers.quote(query)}&limit=5"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data    = await resp.json()
                        results = []
                        for item in data[:5]:
                            results.append(
                                f"**{item.get('title','')}**\n"
                                f"{item.get('snippet','')}\n"
                                f"Source: {item.get('link','')}"
                            )
                        return "Web Search Results:\n\n" + "\n\n".join(results) if results else "No results found."
                    else:
                        # Fallback: DuckDuckGo instant answer
                        url2 = f"https://api.duckduckgo.com/?q={aiohttp.helpers.quote(query)}&format=json&no_html=1"
                        async with session.get(url2, timeout=aiohttp.ClientTimeout(total=10)) as r2:
                            if r2.status == 200:
                                d2 = await r2.json(content_type=None)
                                abstract = d2.get("AbstractText","")
                                answer   = d2.get("Answer","")
                                result   = answer or abstract or "No direct answer found. Try rephrasing."
                                return f"Search Result for '{query}':\n{result}"
                            return f"Search completed for: {query}\nCould not fetch live results."
        except Exception as e:
            return f"Search for '{query}' completed. (Live search unavailable: {str(e)[:50]})"

    elif tool_name == "run_code":
        code = tool_args.get("code", "")
        try:
            import sys
            from io import StringIO
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            local_vars = {}
            try:
                exec(compile(code, "<agent>", "exec"), {"__builtins__": __builtins__}, local_vars)
                output = sys.stdout.getvalue()
                errors = sys.stderr.getvalue()
            except Exception as exec_err:
                output = ""
                errors = str(exec_err)
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            result = ""
            if output: result += f"Output:\n{output}"
            if errors: result += f"\nErrors:\n{errors}"
            if not result: result = "Code executed successfully (no output)."
            return result[:2000]
        except Exception as e:
            return f"Code execution error: {str(e)[:200]}"

    elif tool_name == "analyze_task":
        task  = tool_args.get("task", "")
        steps = tool_args.get("steps", [])
        result = f"Task Analysis: {task}\n\nStep-by-step plan:\n"
        for i, step in enumerate(steps, 1):
            result += f"{i}. {step}\n"
        result += f"\nTotal steps: {len(steps)}"
        return result

    elif tool_name == "get_weather":
        location = tool_args.get("location", "")
        try:
            url = f"https://wttr.in/{aiohttp.helpers.quote(location)}?format=j1"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data    = await resp.json()
                        current = data["current_condition"][0]
                        area    = data["nearest_area"][0]
                        city    = area["areaName"][0]["value"]
                        country = area["country"][0]["value"]
                        temp_c  = current["temp_C"]
                        temp_f  = current["temp_F"]
                        feels   = current["FeelsLikeC"]
                        desc    = current["weatherDesc"][0]["value"]
                        humidity= current["humidity"]
                        wind    = current["windspeedKmph"]
                        return (
                            f"Weather in {city}, {country}:\n"
                            f"🌡 Temperature: {temp_c}°C ({temp_f}°F)\n"
                            f"🤔 Feels like: {feels}°C\n"
                            f"☁️ Condition: {desc}\n"
                            f"💧 Humidity: {humidity}%\n"
                            f"💨 Wind: {wind} km/h"
                        )
                    return f"Could not get weather for {location}."
        except Exception as e:
            return f"Weather service error: {str(e)[:100]}"

    elif tool_name == "calculate":
        expr = tool_args.get("expression", "")
        try:
            import math
            safe_globals = {
                "__builtins__": {},
                "math": math,
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "len": len, "pow": pow, "int": int,
                "float": float, "str": str, "sqrt": math.sqrt,
                "pi": math.pi, "e": math.e,
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "log": math.log, "log10": math.log10,
            }
            result = eval(expr, safe_globals)
            return f"Calculation: {expr}\nResult: {result}"
        except Exception as ex:
            return f"Calculation error for '{expr}': {str(ex)}"

    return f"Unknown tool: {tool_name}"


# ── MAIN AGENT RUNNER ──────────────────────
async def run_agent(uid: int, user_message: str, max_steps: int = 5) -> str:
    """
    Full agentic loop:
    1. Send message + tools to OpenRouter
    2. If tool_calls → execute tools → feed results back
    3. Repeat until final text response
    4. Return final answer
    """
    if not OPENROUTER_API_KEY:
        return "⚠️ OPENROUTER_API_KEY not set. Please add it to environment variables."

    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user",   "content": user_message}
    ]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://t.me/DarkNovaBot",
        "X-Title":       "DarkNova Agent Bot",
    }

    steps_taken    = []
    tool_call_log  = []

    for step in range(max_steps):
        payload = {
            "model":       OPENROUTER_MODEL,
            "messages":    messages,
            "tools":       AGENT_TOOLS,
            "tool_choice": "auto",
            "max_tokens":  2048,
            "temperature": 0.7,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OPENROUTER_BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        err = await resp.text()
                        logger.error(f"OpenRouter error {resp.status}: {err}")
                        return f"⚠️ Agent error (step {step+1}). Try again."
                    data = await resp.json()

        except asyncio.TimeoutError:
            return "⏱️ Agent timed out. Try a simpler query."
        except Exception as e:
            logger.error(f"Agent request error: {e}")
            return f"❌ Agent error: {str(e)[:100]}"

        choice  = data["choices"][0]
        message = choice["message"]
        reason  = choice.get("finish_reason", "")

        # No tool calls → final answer
        if not message.get("tool_calls"):
            final_text = message.get("content", "").strip()
            if tool_call_log:
                summary = "\n".join([f"  🔧 `{t}`" for t in tool_call_log])
                final_text = f"🤖 *Agent used {len(tool_call_log)} tool(s):*\n{summary}\n\n━━━━━━━━━━━━━━━━━━━\n{final_text}"
            return final_text or "Agent completed with no response."

        # Has tool calls → execute them
        messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": message["tool_calls"]})

        for tc in message["tool_calls"]:
            tool_id   = tc["id"]
            tool_name = tc["function"]["name"]
            try:
                tool_args = json.loads(tc["function"]["arguments"])
            except Exception:
                tool_args = {}

            logger.info(f"Agent executing tool: {tool_name} args={tool_args}")
            tool_call_log.append(f"{tool_name}({list(tool_args.values())[0] if tool_args else ''})")

            tool_result = await execute_tool(tool_name, tool_args)

            messages.append({
                "role":         "tool",
                "tool_call_id": tool_id,
                "name":         tool_name,
                "content":      tool_result,
            })

    return "⚠️ Agent reached max steps. Try a more specific question."


# ── AGENT TRIGGER DETECTION ────────────────
AGENT_KEYWORDS = [
    "search", "find", "look up", "latest", "news", "today", "weather",
    "calculate", "compute", "solve", "math", "convert", "how much",
    "run code", "execute", "debug", "test this code",
    "research", "compare", "analyze", "plan", "steps to",
    "dhundho", "khojo", "aaj ka", "mausam", "calculate kar",
    "news kya hai", "abhi", "current", "right now", "live",
    "price", "rate", "score", "result", "kya hai aaj",
]

def should_use_agent(text: str) -> bool:
    """Detect if message needs agent (tools) vs normal AI"""
    text_lower = text.lower()
    return any(kw in text_lower for kw in AGENT_KEYWORDS)



# ══════════════════════════════════════════════
# USER BOT
# ══════════════════════════════════════════════
USER_KB = ReplyKeyboardMarkup(
    [["💬 Chat","🧹 Reset"],["ℹ️ About","📊 Plan"],["🎫 Redeem","📞 Contact"]],
    resize_keyboard=True
)

async def usr_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): await update.message.reply_text("🚫 You are banned."); return
    if ctx.args:
        await _redeem(update, uid, ctx.args[0].upper()); return
    if not await check_fsub(uid, update.get_bot()):
        await update.message.reply_text("🔒 Join our channel first!", reply_markup=fsub_kb()); return
    u = get_user(uid)
    u["name"]        = update.effective_user.first_name or "User"
    u["username"]    = update.effective_user.username
    u["last_active"] = datetime.now().isoformat()
    plan    = "💎 Premium" if is_premium(uid) else "🆓 Free"
    daily   = get_daily_count(uid)
    limit   = get_limit(uid)
    welcome = bot_data.get("welcome","")
    try:
        text = welcome.format(name=u["name"], plan=plan, daily=daily,
                               limit=limit if limit<99999 else "∞")
    except Exception:
        text = f"👋 Welcome {u['name']}! Plan: {plan} | Queries: {daily}/{limit if limit<99999 else '∞'}"
    await update.message.reply_text(text, reply_markup=USER_KB)
    await save_data()

async def usr_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id): return
    agent_status = "✅ Active" if OPENROUTER_API_KEY else "❌ Not set"
    await update.message.reply_text(
        "🤖 *DarkNova AI — Commands*\n━━━━━━━━━━━━━━━━━━━\n"
        "/start — Welcome\n/help — This list\n/reset — Clear memory\n"
        "/about — About\n/plan — Your plan\n/redeem <code> — Premium\n"
        "/contact — Admin\n/ping — Latency\n/speed — AI speed\n/model — Model info\n"
        f"/agent <query> — Agent Mode ({agent_status})\n\n"
        "💬 Just type to chat!\n"
        "🔍 Auto-agent on: search, weather, calculate, news...",
        parse_mode=ParseMode.MARKDOWN
    )


async def usr_agent(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Force agent mode — /agent <query>"""
    uid = update.effective_user.id
    if is_banned(uid): return
    if not ctx.args:
        await update.message.reply_text(
            "🤖 *Agent Mode*\n\nUsage: `/agent <query>`\n\nExamples:\n"
            "• `/agent weather in Mumbai`\n"
            "• `/agent latest AI news`\n"
            "• `/agent calculate 15% of 8500`\n"
            "• `/agent steps to build a todo app`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if not OPENROUTER_API_KEY:
        await update.message.reply_text("⚠️ Agent not configured. Add OPENROUTER_API_KEY."); return
    if get_daily_count(uid) >= get_limit(uid):
        await update.message.reply_text("⚠️ Daily limit reached!"); return
    query    = " ".join(ctx.args)
    thinking = await update.message.reply_text(
        f"🤖 *Agent thinking...*\n🔍 `{query[:60]}`",
        parse_mode=ParseMode.MARKDOWN
    )
    response = await run_agent(uid, query)
    try: await thinking.delete()
    except Exception: pass
    for chunk in split_text(response):
        try:   await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        except Exception: await update.message.reply_text(chunk)
    u = get_user(uid)
    u["messages"] = u.get("messages", 0) + 1
    bot_data["stats"]["total_messages"] = bot_data["stats"].get("total_messages", 0) + 1
    inc_daily(uid)
    await save_data()

async def usr_about(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg = bot_data.get("cfg",{})
    await update.message.reply_text(
        "🤖 *DarkNova AI*\n━━━━━━━━━━━━━━━━━━━\n"
        "Powerful AI on Groq's lightning-fast API.\n\n"
        f"🧠 Model: `{cfg.get('model','llama-3.1-8b-instant')}`\n"
        f"🎭 Persona: `{cfg.get('personality','default')}`\n"
        "💎 Memory, Code, Multilingual\n\n"
        "👨‍💻 Built by: *@MrNewton_2*\n"
        "🔥 Powered by: Groq AI", parse_mode=ParseMode.MARKDOWN
    )

async def usr_plan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    plan  = "💎 Premium" if is_premium(uid) else "🆓 Free"
    daily = get_daily_count(uid)
    limit = get_limit(uid)
    exp   = ""
    if is_premium(uid):
        e = bot_data.get("premium",{}).get(str(uid),{}).get("expiry","?")
        exp = "\n♾️ Permanent" if e=="permanent" else f"\n⏳ Expires: `{e[:10]}`"
    await update.message.reply_text(
        f"📊 *Your Plan*\n━━━━━━━━━━━━━━━━━━━\n"
        f"Plan: {plan}{exp}\n"
        f"Today: `{daily}/{limit if limit<99999 else '∞'}`\n"
        f"Memory: `{'40 msgs (48h)' if is_premium(uid) else 'Off — Upgrade!'}`\n\n"
        "🎫 Use `/redeem <code>` to upgrade!",
        parse_mode=ParseMode.MARKDOWN
    )

async def usr_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    if not is_premium(uid):
        await update.message.reply_text("⚠️ Memory is a 💎 Premium feature!"); return
    bot_data["convos"].pop(str(uid),None)
    await save_data()
    await update.message.reply_text("🧹 Memory cleared!")

async def usr_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📞 *Contact*\n\n👤 @MrNewton_2\nAdmin ID: `{ADMIN_ID}`",
        parse_mode=ParseMode.MARKDOWN
    )

async def usr_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t=time.time(); m=await update.message.reply_text("🏓...")
    ms=int((time.time()-t)*1000)
    await m.edit_text(f"⚡ `{ms}ms`", parse_mode=ParseMode.MARKDOWN)

async def usr_speed(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    m = await update.message.reply_text("⏱ Testing...")
    t = time.time()
    r,_ = await call_groq(uid, "Reply with exactly 3 words: Speed test OK")
    await m.edit_text(f"⚡ `{round(time.time()-t,2)}s`\n_{r}_", parse_mode=ParseMode.MARKDOWN)

async def usr_model(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg = bot_data.get("cfg",{})
    await update.message.reply_text(
        f"🤖 *Model Info*\n\n"
        f"Model: `{cfg.get('model','N/A')}`\n"
        f"Temp: `{cfg.get('temperature',0.9)}`\n"
        f"Tokens: `{cfg.get('max_tokens',4096)}`\n"
        f"Persona: `{cfg.get('personality','default')}`",
        parse_mode=ParseMode.MARKDOWN
    )

async def _redeem(update: Update, uid: int, code: str):
    codes = bot_data.get("codes",{})
    if code not in codes:
        await update.message.reply_text("❌ Invalid code."); return
    if codes[code].get("used"):
        await update.message.reply_text("❌ Already used."); return
    days   = codes[code].get("days",30)
    exp    = "permanent" if days==0 else (datetime.now()+timedelta(days=days)).isoformat()
    bot_data["premium"][str(uid)] = {"expiry":exp,"granted":datetime.now().isoformat()}
    codes[code]["used"]=True; codes[code]["used_by"]=uid
    await save_data()
    await update.message.reply_text(
        f"✅ *Redeemed!*\n💎 Premium — {'♾️ permanent' if days==0 else str(days)+' days'}!",
        parse_mode=ParseMode.MARKDOWN
    )

async def usr_redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    if not ctx.args: await update.message.reply_text("Usage: /redeem <code>"); return
    await _redeem(update, uid, ctx.args[0].upper())

async def usr_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "cs":
        if await check_fsub(q.from_user.id, q.get_bot()):
            await q.edit_message_text("✅ Verified! Send /start")
        else:
            await q.answer("❌ Not joined yet!", show_alert=True)
    elif q.data.startswith("copy_"):
        await q.message.reply_text(f"`{q.data[5:]}`", parse_mode=ParseMode.MARKDOWN)
        await q.answer("✅ Sent!")

async def usr_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    uid  = update.effective_user.id
    text = update.message.text.strip()

    if is_banned(uid):   await update.message.reply_text("🚫 You are banned."); return
    if bot_data.get("maint"): await update.message.reply_text(bot_data.get("maintenance_msg","🔧 Maintenance...")); return
    if not await check_fsub(uid, update.get_bot()):
        await update.message.reply_text("🔒 Join channel first!", reply_markup=fsub_kb()); return
    if is_muted(uid):
        info  = bot_data["muted"].get(str(uid),{})
        until = info.get("until","")
        rem   = ""
        if until:
            try: rem = f" ({int((datetime.fromisoformat(until)-datetime.now()).total_seconds()//60)} min left)"
            except Exception: pass
        await update.message.reply_text(f"🔇 You are muted{rem}."); return
    if check_flood(uid):
        apply_mute_flood(uid)
        await update.message.reply_text("🛡 Flooding! You've been muted."); return

    u = get_user(uid)
    u["name"]=""; u["name"] = update.effective_user.first_name or "User"
    u["username"]    = update.effective_user.username
    u["last_active"] = datetime.now().isoformat()

    # Keyboard shortcuts
    if text == "💬 Chat":    await update.message.reply_text("💬 Just type!"); return
    if text == "🧹 Reset":   await usr_reset(update, ctx); return
    if text == "ℹ️ About":   await usr_about(update, ctx); return
    if text == "📊 Plan":    await usr_plan(update, ctx); return
    if text == "🎫 Redeem":  await update.message.reply_text("Use: /redeem <code>"); return
    if text == "📞 Contact": await usr_contact(update, ctx); return

    # Group: only respond to mentions/replies
    if update.message.chat.type in ["group","supergroup"]:
        me         = await update.get_bot().get_me()
        is_mention = f"@{me.username}" in text
        is_reply   = (update.message.reply_to_message and
                      update.message.reply_to_message.from_user and
                      update.message.reply_to_message.from_user.id == me.id)
        if not is_mention and not is_reply: return

    # Daily limit
    if get_daily_count(uid) >= get_limit(uid):
        await update.message.reply_text(
            f"⚠️ Daily limit reached! (`{get_daily_count(uid)}/{get_limit(uid)}`)\n"
            "💎 Upgrade to Premium for unlimited!", parse_mode=ParseMode.MARKDOWN
        ); return

    await update.message.chat.send_action("typing")

    # ── Agent or Normal AI? ───────────────────
    if should_use_agent(text) and OPENROUTER_API_KEY:
        thinking_msg = await update.message.reply_text("🤖 Agent thinking... 🔍")
        response = await run_agent(uid, text)
        try:
            await thinking_msg.delete()
        except Exception:
            pass
        # Agent response is final text, send directly
        for chunk in split_text(response):
            await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        # Update stats
        u["messages"] = u.get("messages",0)+1
        bot_data["stats"]["total_messages"] = bot_data["stats"].get("total_messages",0)+1
        bot_data["stats"]["today_messages"] = bot_data["stats"].get("today_messages",0)+1
        inc_daily(uid); reset_today()
        await save_data()
        return

    response, _ = await call_groq(uid, text)

    u["messages"] = u.get("messages",0)+1
    bot_data["stats"]["total_messages"] = bot_data["stats"].get("total_messages",0)+1
    bot_data["stats"]["today_messages"] = bot_data["stats"].get("today_messages",0)+1
    inc_daily(uid); reset_today()

    # ── Smart response: ZIP or inline ─────────
    if has_code(response):
        blocks, clean = extract_blocks(response)
        clean = clean.replace("\n[CODE]\n","").strip()

        if needs_zip(blocks):
            files     = {}
            used      = set()
            for i,(lang,code) in enumerate(blocks):
                fname = detect_fname(lang, i, response)
                if fname in used:
                    base,ext = (fname.rsplit(".",1) if "." in fname else (fname,"txt"))
                    fname = f"{base}_{i+1}.{ext}"
                used.add(fname)
                files[fname] = code
            flist = "\n".join(f"  📄 `{f}`" for f in files)
            files["README.md"] = (
                "# Project\n\nGenerated by DarkNova AI\nBuilt by @MrNewton_2\n\n"
                "## Files\n\n" + "\n".join(f"- `{f}`" for f in files if f!="README.md")
            )
            all_langs = [b[0].lower() for b in blocks]
            if "html" in all_langs:           ptype = "🌐 Web Project"
            elif any(l in all_langs for l in ["py","python"]): ptype = "🐍 Python Project"
            elif any(l in all_langs for l in ["js","javascript","ts"]): ptype = "⚡ JS Project"
            else:                              ptype = "📁 Code Project"

            if clean:
                for chunk in split_text(clean):
                    await update.message.reply_text(chunk)

            pname  = re.sub(r"[^a-z0-9_]","",text[:25].lower().replace(" ","_")) or "project"
            zipbuf = make_zip(files)
            await update.message.reply_document(
                document=zipbuf,
                filename=f"{pname}.zip",
                caption=(
                    f"📦 *{ptype}*\n━━━━━━━━━━━━━━━━━━━\n"
                    f"{flist}\n  📄 `README.md`\n\n"
                    f"🤖 _DarkNova AI_ | 👨‍💻 _@MrNewton_2_"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            if clean:
                for chunk in split_text(clean):
                    await update.message.reply_text(chunk)
            for lang,code in blocks:
                lang = lang or "text"
                safe = code[:190].replace("`","'")
                kb   = InlineKeyboardMarkup([[InlineKeyboardButton("📋 Copy Code", callback_data=f"copy_{safe}")]])
                for chunk in split_text(f"```{lang}\n{code}\n```", 4000):
                    await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    else:
        for chunk in split_text(response):
            await update.message.reply_text(chunk)

    await save_data()

# ══════════════════════════════════════════════
# ERROR HANDLER
# ══════════════════════════════════════════════
async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {ctx.error}", exc_info=ctx.error)

# ══════════════════════════════════════════════
# WEB SERVER
# ══════════════════════════════════════════════
async def health(request):
    from aiohttp.web import Response
    return Response(
        text=json.dumps({
            "status": "ok",
            "uptime": uptime(),
            "users":  len(bot_data.get("users",{})),
            "msgs":   bot_data.get("stats",{}).get("total_messages",0),
        }),
        content_type="application/json"
    )

async def start_web():
    from aiohttp.web import Application, AppRunner, TCPSite
    app    = Application()
    app.router.add_get("/", health)
    runner = AppRunner(app)
    await runner.setup()
    await TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info(f"Web server on :{PORT}")

# ══════════════════════════════════════════════
# BUILD APPS
# ══════════════════════════════════════════════
def build_admin() -> Application:
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",         adm_start))
    app.add_handler(CommandHandler("broadcast",     adm_broadcast))
    app.add_handler(CommandHandler("ban",           adm_ban))
    app.add_handler(CommandHandler("unban",         adm_unban))
    app.add_handler(CommandHandler("warn",          adm_warn))
    app.add_handler(CommandHandler("mute",          adm_mute))
    app.add_handler(CommandHandler("unmute",        adm_unmute))
    app.add_handler(CommandHandler("premium",       adm_premium))
    app.add_handler(CommandHandler("removepremium", adm_remprem))
    app.add_handler(CommandHandler("setlimit",      adm_setlimit))
    app.add_handler(CommandHandler("gencode",       adm_gencode))
    app.add_handler(CommandHandler("deletecode",    adm_delcode))
    app.add_handler(CommandHandler("redeeminfo",    adm_redeeminfo))
    app.add_handler(CommandHandler("forcesub",      adm_forcesub))
    app.add_handler(CommandHandler("antiflood",     adm_antiflood))
    app.add_handler(CommandHandler("viewchat",      adm_viewchat))
    app.add_handler(CommandHandler("clearmem",      adm_clearmem))
    app.add_handler(CommandHandler("clearmemall",   adm_clearmemall))
    app.add_handler(CommandHandler("clearchats",    adm_clearchats))
    app.add_handler(CommandHandler("export",        adm_export))
    app.add_handler(CommandHandler("sysprompt",     adm_sysprompt))
    app.add_handler(CommandHandler("advertise",     adm_advertise))
    app.add_handler(CommandHandler("ping",          adm_ping))
    app.add_handler(CallbackQueryHandler(adm_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, adm_text))
    app.add_error_handler(on_error)
    return app

def build_user() -> Application:
    app = Application.builder().token(USER_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",   usr_start))
    app.add_handler(CommandHandler("help",    usr_help))
    app.add_handler(CommandHandler("about",   usr_about))
    app.add_handler(CommandHandler("plan",    usr_plan))
    app.add_handler(CommandHandler("reset",   usr_reset))
    app.add_handler(CommandHandler("contact", usr_contact))
    app.add_handler(CommandHandler("ping",    usr_ping))
    app.add_handler(CommandHandler("speed",   usr_speed))
    app.add_handler(CommandHandler("model",   usr_model))
    app.add_handler(CommandHandler("redeem",  usr_redeem))
    app.add_handler(CommandHandler("agent",   usr_agent))
    app.add_handler(CallbackQueryHandler(usr_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, usr_msg))
    app.add_error_handler(on_error)
    return app

# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════
async def main():
    global user_bot_obj

    if not all([ADMIN_BOT_TOKEN, USER_BOT_TOKEN, GROQ_API_KEY]):
        logger.error("Missing env vars! Set ADMIN_BOT_TOKEN, USER_BOT_TOKEN, GROQ_API_KEY"); return

    load_data()
    bot_data["start_time"] = datetime.now().isoformat()

    user_bot_obj = Bot(token=USER_BOT_TOKEN)
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set — Agent features disabled.")
    else:
        logger.info(f"Agent enabled: {OPENROUTER_MODEL}")
    logger.info("Starting DarkNova AI Bot v4.0...")

    admin_app = build_admin()
    user_app  = build_user()

    await start_web()
    asyncio.create_task(periodic_save())

    await admin_app.initialize()
    await user_app.initialize()

    # Clear any old webhooks/polling conflicts
    logger.info("Clearing old webhooks...")
    await admin_app.bot.delete_webhook(drop_pending_updates=True)
    await user_app.bot.delete_webhook(drop_pending_updates=True)

    await admin_app.start()
    await user_app.start()

    await admin_app.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )
    await user_app.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )

    logger.info("✅ DarkNova v4.0 — Both bots running!")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        await save_data()
        try: await user_bot_obj.close()
        except Exception: pass
        await admin_app.updater.stop()
        await user_app.updater.stop()
        await admin_app.stop()
        await user_app.stop()
        await admin_app.shutdown()
        await user_app.shutdown()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())
