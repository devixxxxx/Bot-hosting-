"""
╔══════════════════════════════════════════════════════════════╗
║          DARKNOVA AI BOT - PRODUCTION READY v2.0            ║
║          Built by @MrNewton_2                           ║
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
from datetime import datetime, timedelta
from functools import wraps
from logging.handlers import RotatingFileHandler

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.error import TelegramError, Forbidden, BadRequest
from telegram.constants import ParseMode

# ══════════════════════════════════════════════
# LOGGING SETUP
# ══════════════════════════════════════════════
logger = logging.getLogger("DarkNovaBot")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

fh = RotatingFileHandler("bot.log", maxBytes=5_000_000, backupCount=3)
fh.setFormatter(fmt)
sh = logging.StreamHandler()
sh.setFormatter(fmt)
logger.addHandler(fh)
logger.addHandler(sh)

# ══════════════════════════════════════════════
# ENVIRONMENT VARIABLES
# ══════════════════════════════════════════════
ADMIN_BOT_TOKEN = os.environ.get("ADMIN_BOT_TOKEN", "")
USER_BOT_TOKEN  = os.environ.get("USER_BOT_TOKEN", "")
ADMIN_ID        = int(os.environ.get("ADMIN_ID", "0"))
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
PORT            = int(os.environ.get("PORT", "8080"))

DATA_FILE = "bot_data.json"
data_lock = asyncio.Lock()

# ══════════════════════════════════════════════
# AI PERSONALITIES
# ══════════════════════════════════════════════
PERSONAS: dict[str, str] = {
    "default": (
        "You are DarkNova — a smart, witty, multilingual AI assistant. "
        "You speak in a casual Hindi-English (Hinglish) mix when the user uses Hindi. "
        "You are helpful, direct, and confident. You answer everything clearly. "
        "When writing code, always use ``` blocks with the language name. "
        "Never be rude unnecessarily, but always be real and honest. "
        "Created by @MrNewton_2."
    ),
    "teacher": (
        "You are DarkNova in Teacher mode. You explain concepts step by step, "
        "use simple analogies, give examples, and make sure the user truly understands. "
        "You are patient and encouraging. You adapt your language to the user's level. "
        "For code, always use proper ``` blocks."
    ),
    "hacker": (
        "You are DarkNova in Hacker mode — a skilled ethical security researcher and developer. "
        "You know systems, networks, Linux, Python, exploits (for educational/CTF purposes only). "
        "You speak with tech slang, are precise and efficient. "
        "You only discuss ethical hacking, CTFs, bug bounties, and defense. "
        "Always use ``` for code and commands."
    ),
    "philosopher": (
        "You are DarkNova in Philosopher mode. You see the deeper meaning in everything. "
        "You ask profound questions, make the user think, and offer multiple perspectives. "
        "You reference great thinkers when relevant. You speak beautifully and thoughtfully."
    ),
    "comedian": (
        "You are DarkNova in Comedian mode. Everything gets a witty twist. "
        "You use puns, dry humor, sarcasm (lightly), and clever observations. "
        "Still helpful, but you make the user smile. Hinglish jokes welcome!"
    ),
    "poet": (
        "You are DarkNova in Poet mode. You respond with beautiful language, "
        "metaphors, rhythm, and imagery. When asked for poems, you craft them with care. "
        "You can write in English, Hindi, or Hinglish. Everything feels artistic."
    ),
    "lawyer": (
        "You are DarkNova in Lawyer mode. You are precise, logical, and thorough. "
        "You break down arguments, identify loopholes, and explain legal concepts clearly. "
        "You always note: 'This is for educational purposes, not legal advice.' "
        "You are sharp and analytical."
    ),
    "doctor": (
        "You are DarkNova in Doctor mode. You provide clear health information, "
        "explain symptoms, conditions, and treatments in plain language. "
        "You always remind users to consult a real doctor for diagnosis. "
        "You are calm, caring, and thorough."
    ),
    "therapist": (
        "You are DarkNova in Therapist mode. You listen with empathy, "
        "validate the user's feelings, ask thoughtful questions, and gently guide them. "
        "You are warm, patient, and non-judgmental. "
        "You encourage professional help when needed. You never dismiss emotions."
    ),
    "tutor": (
        "You are DarkNova in Coding Tutor mode. You teach programming concepts, "
        "debug code, explain algorithms, and help with projects. "
        "You write clean code with comments. You celebrate small wins. "
        "Languages: Python, JS, C++, Java, Rust, Go, and more."
    ),
    "storyteller": (
        "You are DarkNova in Storyteller mode. You craft engaging narratives, "
        "vivid characters, and interesting plots. You can continue stories, "
        "write dialogues, and build entire worlds. You make every story immersive."
    ),
    "fitness": (
        "You are DarkNova in Fitness Coach mode. You create workout plans, "
        "explain exercises with proper form, give nutrition advice, and motivate users. "
        "You tailor advice to the user's level and goals. Always recommend warming up and recovery."
    ),
    "chef": (
        "You are DarkNova in Chef mode. You know recipes from every cuisine, "
        "cooking techniques, ingredient substitutions, and meal planning. "
        "You make cooking fun and accessible for everyone from beginners to pros."
    ),
    "interviewer": (
        "You are DarkNova in Job Interview Coach mode. You help users prepare "
        "for technical and HR interviews, practice answers, review resumes, "
        "and build confidence. You simulate mock interviews and give sharp feedback."
    ),
    "translator": (
        "You are DarkNova in Translator mode. You translate accurately between languages, "
        "explain idioms and cultural context, and help users learn new languages. "
        "You support: Hindi, English, Spanish, French, German, Japanese, Arabic, and more."
    ),
}

# ══════════════════════════════════════════════
# DEFAULT DATA STATE
# ══════════════════════════════════════════════
DEFAULT_DATA: dict = {
    "users": {},
    "banned": [],
    "convos": {},
    "maint": False,
    "force_sub": None,
    "cfg": {
        "model": "llama-3.1-8b-instant",
        "temperature": 0.9,
        "max_tokens": 4096,
        "personality": "default",
        "system_prompt": PERSONAS["default"],
    },
    "stats": {
        "total_messages": 0,
        "today_messages": 0,
        "total_broadcasts": 0,
        "total_bans": 0,
        "total_mutes": 0,
        "total_tokens": 0,
        "groq_calls": 0,
        "groq_errors": 0,
        "last_reset_date": datetime.now().strftime("%Y-%m-%d"),
    },
    "premium": {},
    "codes": {},
    "muted": {},
    "flood": {},
    "daily_counts": {},
    "chats": {},
    "ad_stats": {"sent": 0, "failed": 0},
    "welcome": (
        "👋 Welcome, {name}!\n\n"
        "🤖 I'm DarkNova AI — your powerful assistant.\n"
        "📦 Plan: {plan}\n"
        "💬 Daily Queries: {daily}/{limit}\n\n"
        "Type anything to start chatting! 🚀"
    ),
    "limits": {"free": 20, "prem": 99999},
    "antiflood": {"on": True, "max": 8, "win": 10, "mute": 5},
    "start_time": datetime.now().isoformat(),
    "broadcast_stats": {"sent": 0, "failed": 0},
    "maintenance_msg": "🔧 Bot is under maintenance. Please wait...",
}

# ══════════════════════════════════════════════
# DATA MANAGEMENT
# ══════════════════════════════════════════════
bot_data: dict = {}

def load_data() -> dict:
    global bot_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # Merge with defaults to ensure all keys exist
            merged = DEFAULT_DATA.copy()
            for k, v in loaded.items():
                if isinstance(v, dict) and isinstance(merged.get(k), dict):
                    merged[k].update(v)
                else:
                    merged[k] = v
            bot_data = merged
            logger.info("Data loaded successfully.")
        except Exception as e:
            logger.error(f"Load error: {e}, using defaults.")
            bot_data = DEFAULT_DATA.copy()
    else:
        bot_data = DEFAULT_DATA.copy()
    return bot_data


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
        logger.info("Auto-save complete.")

# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════
def get_user(uid: int) -> dict:
    uid = str(uid)
    if uid not in bot_data["users"]:
        bot_data["users"][uid] = {
            "id": int(uid),
            "name": "Unknown",
            "username": None,
            "messages": 0,
            "warnings": 0,
            "joined": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
        }
    return bot_data["users"][uid]


def is_banned(uid: int) -> bool:
    return int(uid) in [int(x) for x in bot_data.get("banned", [])]


def is_muted(uid: int) -> bool:
    uid = str(uid)
    muted = bot_data.get("muted", {})
    if uid not in muted:
        return False
    until = muted[uid].get("until")
    if until and datetime.fromisoformat(until) < datetime.now():
        del bot_data["muted"][uid]
        return False
    return True


def is_premium(uid: int) -> bool:
    uid = str(uid)
    prem = bot_data.get("premium", {})
    if uid not in prem:
        return False
    expiry = prem[uid].get("expiry")
    if expiry == "permanent":
        return True
    if expiry and datetime.fromisoformat(expiry) < datetime.now():
        del bot_data["premium"][uid]
        return False
    return True


def get_daily_count(uid: int) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    uid = str(uid)
    dc = bot_data.get("daily_counts", {})
    if uid not in dc or dc[uid].get("date") != today:
        dc[uid] = {"date": today, "count": 0}
        bot_data["daily_counts"] = dc
    return dc[uid]["count"]


def increment_daily(uid: int):
    today = datetime.now().strftime("%Y-%m-%d")
    uid = str(uid)
    dc = bot_data.get("daily_counts", {})
    if uid not in dc or dc[uid].get("date") != today:
        dc[uid] = {"date": today, "count": 0}
    dc[uid]["count"] += 1
    bot_data["daily_counts"] = dc


def get_limit(uid: int) -> int:
    return bot_data["limits"]["prem"] if is_premium(uid) else bot_data["limits"]["free"]


def split_long_message(text: str, max_len: int = 4000) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts = []
    while len(text) > max_len:
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        parts.append(text)
    return parts


def extract_code_blocks(text: str) -> tuple[list[tuple[str, str]], str]:
    """Returns ([(lang, code), ...], clean_text_without_code)"""
    pattern = r"```(\w+)?\n?([\s\S]*?)```"
    blocks = re.findall(pattern, text)
    clean = re.sub(pattern, "[CODE BLOCK]", text)
    return blocks, clean


def has_code(text: str) -> bool:
    return "```" in text


def uptime_str() -> str:
    start = datetime.fromisoformat(bot_data.get("start_time", datetime.now().isoformat()))
    delta = datetime.now() - start
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s"


def reset_daily_stats():
    today = datetime.now().strftime("%Y-%m-%d")
    if bot_data["stats"].get("last_reset_date") != today:
        bot_data["stats"]["today_messages"] = 0
        bot_data["stats"]["last_reset_date"] = today

# ══════════════════════════════════════════════
# ANTIFLOOD
# ══════════════════════════════════════════════
def check_flood(uid: int) -> bool:
    """Returns True if user is flooding"""
    af = bot_data.get("antiflood", {})
    if not af.get("on", False):
        return False
    uid = str(uid)
    now = time.time()
    flood = bot_data.get("flood", {})
    if uid not in flood:
        flood[uid] = []
    flood[uid] = [t for t in flood[uid] if now - t < af.get("win", 10)]
    flood[uid].append(now)
    bot_data["flood"] = flood
    return len(flood[uid]) > af.get("max", 8)


def apply_flood_mute(uid: int):
    af = bot_data.get("antiflood", {})
    mute_mins = af.get("mute", 5)
    until = (datetime.now() + timedelta(minutes=mute_mins)).isoformat()
    bot_data["muted"][str(uid)] = {"until": until, "reason": "antiflood"}

# ══════════════════════════════════════════════
# GROQ AI CALL
# ══════════════════════════════════════════════
async def call_groq(uid: int, user_message: str) -> tuple[str, int]:
    """Returns (response_text, tokens_used)"""
    cfg = bot_data.get("cfg", {})
    system_prompt = cfg.get("system_prompt", PERSONAS["default"])
    model         = cfg.get("model", "llama-3.1-8b-instant")
    temperature   = float(cfg.get("temperature", 0.9))
    max_tokens    = int(cfg.get("max_tokens", 4096))

    messages = [{"role": "system", "content": system_prompt}]

    if is_premium(uid):
        history = bot_data.get("convos", {}).get(str(uid), [])
        # Keep last 40 messages, expire 48h old
        cutoff = (datetime.now() - timedelta(hours=48)).isoformat()
        history = [m for m in history if m.get("ts", "9999") > cutoff][-40:]
        for m in history:
            messages.append({"role": m["role"], "content": m["content"]})

    messages.append({"role": "user", "content": user_message})

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    bot_data["stats"]["groq_calls"] = bot_data["stats"].get("groq_calls", 0) + 1

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    logger.error(f"Groq error {resp.status}: {err}")
                    bot_data["stats"]["groq_errors"] = bot_data["stats"].get("groq_errors", 0) + 1
                    return "⚠️ AI service error. Please try again.", 0
                data = await resp.json()

        reply = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        bot_data["stats"]["total_tokens"] = bot_data["stats"].get("total_tokens", 0) + tokens

        # Save to premium memory
        if is_premium(uid):
            uid_str = str(uid)
            if uid_str not in bot_data["convos"]:
                bot_data["convos"][uid_str] = []
            ts = datetime.now().isoformat()
            bot_data["convos"][uid_str].append({"role": "user", "content": user_message, "ts": ts})
            bot_data["convos"][uid_str].append({"role": "assistant", "content": reply, "ts": ts})
            bot_data["convos"][uid_str] = bot_data["convos"][uid_str][-40:]

        # Save to chat logs (last 200)
        uid_str = str(uid)
        if uid_str not in bot_data["chats"]:
            bot_data["chats"][uid_str] = []
        bot_data["chats"][uid_str].append({
            "ts": datetime.now().isoformat(),
            "user": user_message[:500],
            "ai": reply[:500],
        })
        bot_data["chats"][uid_str] = bot_data["chats"][uid_str][-200:]

        return reply, tokens

    except asyncio.TimeoutError:
        bot_data["stats"]["groq_errors"] = bot_data["stats"].get("groq_errors", 0) + 1
        return "⏱️ Request timed out. Please try again.", 0
    except Exception as e:
        bot_data["stats"]["groq_errors"] = bot_data["stats"].get("groq_errors", 0) + 1
        logger.error(f"Groq exception: {e}")
        return f"❌ Error: {str(e)[:100]}", 0

# ══════════════════════════════════════════════
# FORCE SUBSCRIBE CHECK
# ══════════════════════════════════════════════
async def check_force_sub(uid: int, bot: Bot) -> bool:
    """Returns True if user is subscribed (or force sub disabled)"""
    fs = bot_data.get("force_sub")
    if not fs:
        return True
    try:
        member = await bot.get_chat_member(fs, uid)
        return member.status not in ["left", "kicked", "banned"]
    except Exception:
        return True


def force_sub_keyboard() -> InlineKeyboardMarkup:
    fs = bot_data.get("force_sub", "@channel")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{fs.lstrip('@')}")],
        [InlineKeyboardButton("✅ Check Membership", callback_data="cs")],
    ])

# ══════════════════════════════════════════════
# ADMIN DECORATOR
# ══════════════════════════════════════════════
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        uid = None
        if update.message:
            uid = update.message.from_user.id
        elif update.callback_query:
            uid = update.callback_query.from_user.id
        if uid != ADMIN_ID:
            if update.message:
                await update.message.reply_text("🚫 Admin only.")
            elif update.callback_query:
                await update.callback_query.answer("🚫 Admin only.", show_alert=True)
            return
        return await func(update, ctx, *args, **kwargs)
    return wrapper

# ══════════════════════════════════════════════
# ADMIN INLINE MENUS
# ══════════════════════════════════════════════
def get_admin_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="a_dash"),
         InlineKeyboardButton("📈 Stats", callback_data="a_stats")],
        [InlineKeyboardButton("👥 Users", callback_data="a_users"),
         InlineKeyboardButton("🟢 Live Chats", callback_data="a_live")],
        [InlineKeyboardButton("🤖 AI Settings", callback_data="a_ai"),
         InlineKeyboardButton("📢 Broadcast", callback_data="a_bcast")],
        [InlineKeyboardButton("🚫 Ban/Unban", callback_data="a_ban"),
         InlineKeyboardButton("🔇 Mute/Unmute", callback_data="a_mute")],
        [InlineKeyboardButton("💎 Premium", callback_data="a_prem"),
         InlineKeyboardButton("🎫 Codes", callback_data="a_codes")],
        [InlineKeyboardButton("🔒 Force Sub", callback_data="a_fsub"),
         InlineKeyboardButton("🛡 Antiflood", callback_data="a_flood")],
        [InlineKeyboardButton("💬 View Chat", callback_data="a_vchat"),
         InlineKeyboardButton("🧹 Clear Memory", callback_data="a_clearmem")],
        [InlineKeyboardButton("🔧 Maintenance", callback_data="a_maint"),
         InlineKeyboardButton("🔄 Restart", callback_data="a_restart")],
        [InlineKeyboardButton("📋 Export Data", callback_data="a_export"),
         InlineKeyboardButton("⚡ Ping", callback_data="a_ping")],
        [InlineKeyboardButton("📢 Advertise", callback_data="a_ad"),
         InlineKeyboardButton("🌐 Webhook Info", callback_data="a_webhook")],
        [InlineKeyboardButton("⚙️ System Prompt", callback_data="a_sysprompt"),
         InlineKeyboardButton("🎭 Personalities", callback_data="a_pers")],
        [InlineKeyboardButton("📊 Daily Report", callback_data="a_daily"),
         InlineKeyboardButton("🗑 Clear All Logs", callback_data="a_clrlogs")],
        [InlineKeyboardButton("❌ Close Panel", callback_data="a_close")],
    ])


def get_ai_menu() -> InlineKeyboardMarkup:
    cfg = bot_data.get("cfg", {})
    temp = cfg.get("temperature", 0.9)
    mtok = cfg.get("max_tokens", 4096)
    pers = cfg.get("personality", "default")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Set Prompt", callback_data="ai_setprompt"),
         InlineKeyboardButton("👁 View Prompt", callback_data="ai_viewprompt")],
        [InlineKeyboardButton("🎭 Personality", callback_data="ai_pers"),
         InlineKeyboardButton(f"🌡 Temp: {temp}", callback_data="ai_temp")],
        [InlineKeyboardButton(f"📏 Tokens: {mtok}", callback_data="ai_tokens"),
         InlineKeyboardButton(f"🤖 Active: {pers}", callback_data="ai_active")],
        [InlineKeyboardButton("🔄 Reset Defaults", callback_data="ai_reset")],
        [InlineKeyboardButton("⬅️ Back", callback_data="a_main")],
    ])


def get_personality_menu() -> InlineKeyboardMarkup:
    current = bot_data.get("cfg", {}).get("personality", "default")
    buttons = []
    row = []
    for name in PERSONAS:
        label = f"✅ {name}" if name == current else name
        row.append(InlineKeyboardButton(label, callback_data=f"pers_{name}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="a_ai")])
    return InlineKeyboardMarkup(buttons)


def get_temperature_menu() -> InlineKeyboardMarkup:
    temps = [0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.8, 2.0]
    current = bot_data.get("cfg", {}).get("temperature", 0.9)
    buttons = []
    row = []
    for t in temps:
        label = f"✅ {t}" if t == current else str(t)
        row.append(InlineKeyboardButton(label, callback_data=f"temp_{t}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="a_ai")])
    return InlineKeyboardMarkup(buttons)


def get_tokens_menu() -> InlineKeyboardMarkup:
    options = [512, 1024, 2048, 4096, 8192, 16384, 32768]
    current = bot_data.get("cfg", {}).get("max_tokens", 4096)
    buttons = []
    row = []
    for t in options:
        label = f"✅ {t}" if t == current else str(t)
        row.append(InlineKeyboardButton(label, callback_data=f"tok_{t}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="a_ai")])
    return InlineKeyboardMarkup(buttons)

# ══════════════════════════════════════════════
# ADMIN BOT HANDLERS
# ══════════════════════════════════════════════
@admin_only
async def admin_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "╔══════════════════════════╗\n"
        "║   🤖 DarkNova Admin     ║\n"
        "║   Control Panel v2.0    ║\n"
        "╚══════════════════════════╝\n\n"
        f"👤 Admin: {update.effective_user.first_name}\n"
        f"⏱ Uptime: {uptime_str()}\n"
        f"👥 Users: {len(bot_data.get('users', {}))}\n\n"
        "Select an option below:"
    )
    await update.message.reply_text(text, reply_markup=get_admin_main_menu())


@admin_only
async def admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    # ── MAIN ──────────────────────────────────
    if data == "a_main":
        await q.edit_message_text("🏠 Main Menu", reply_markup=get_admin_main_menu())

    elif data == "a_close":
        await q.edit_message_text("✅ Panel closed.")

    # ── DASHBOARD ─────────────────────────────
    elif data == "a_dash":
        reset_daily_stats()
        users = bot_data.get("users", {})
        now = datetime.now()
        active_24h = sum(
            1 for u in users.values()
            if (now - datetime.fromisoformat(u.get("last_active", now.isoformat()))).total_seconds() < 86400
        )
        prem_count = sum(1 for uid in users if is_premium(int(uid)))
        banned_count = len(bot_data.get("banned", []))
        muted_count = len(bot_data.get("muted", {}))
        cfg = bot_data.get("cfg", {})
        stats = bot_data.get("stats", {})
        text = (
            "📊 **DASHBOARD**\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Total Users: `{len(users)}`\n"
            f"🟢 Active (24h): `{active_24h}`\n"
            f"💎 Premium: `{prem_count}`\n"
            f"🚫 Banned: `{banned_count}`\n"
            f"🔇 Muted: `{muted_count}`\n\n"
            f"💬 Total Messages: `{stats.get('total_messages', 0)}`\n"
            f"📅 Today: `{stats.get('today_messages', 0)}`\n\n"
            f"🤖 Model: `{cfg.get('model', 'N/A')}`\n"
            f"🌡 Temp: `{cfg.get('temperature', 0.9)}`\n"
            f"📏 Tokens: `{cfg.get('max_tokens', 4096)}`\n"
            f"🎭 Persona: `{cfg.get('personality', 'default')}`\n\n"
            f"🔧 Maintenance: `{'ON' if bot_data.get('maint') else 'OFF'}`\n"
            f"🔒 Force Sub: `{bot_data.get('force_sub') or 'OFF'}`\n"
            f"🛡 Antiflood: `{'ON' if bot_data.get('antiflood', {}).get('on') else 'OFF'}`\n\n"
            f"⏱ Uptime: `{uptime_str()}`\n"
            f"🪙 Tokens Used: `{stats.get('total_tokens', 0)}`"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── STATS ─────────────────────────────────
    elif data == "a_stats":
        stats = bot_data.get("stats", {})
        text = (
            "📈 **STATS**\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "**All Time:**\n"
            f"  💬 Messages: `{stats.get('total_messages', 0)}`\n"
            f"  📢 Broadcasts: `{stats.get('total_broadcasts', 0)}`\n"
            f"  🚫 Bans: `{stats.get('total_bans', 0)}`\n"
            f"  🔇 Mutes: `{stats.get('total_mutes', 0)}`\n"
            f"  🪙 Tokens: `{stats.get('total_tokens', 0)}`\n\n"
            "**Today:**\n"
            f"  💬 Messages: `{stats.get('today_messages', 0)}`\n\n"
            "**API:**\n"
            f"  ✅ Groq Calls: `{stats.get('groq_calls', 0)}`\n"
            f"  ❌ Groq Errors: `{stats.get('groq_errors', 0)}`\n\n"
            f"⏱ Uptime: `{uptime_str()}`"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── USERS ─────────────────────────────────
    elif data == "a_users":
        users = bot_data.get("users", {})
        if not users:
            text = "👥 No users yet."
        else:
            lines = [f"👥 **USERS** ({len(users)} total)\n━━━━━━━━━━━━━━━━━━━"]
            for uid, u in list(users.items())[:30]:
                tags = ""
                if is_premium(int(uid)):
                    tags += "💎"
                if is_banned(int(uid)):
                    tags += "🚫"
                if is_muted(int(uid)):
                    tags += "🔇"
                if u.get("warnings", 0) > 0:
                    tags += f"⚠️x{u['warnings']}"
                uname = f"@{u['username']}" if u.get("username") else "no username"
                lines.append(f"`{uid}` {tags} {u.get('name','?')} ({uname}) — {u.get('messages',0)} msgs")
            if len(users) > 30:
                lines.append(f"\n...and {len(users)-30} more. Use /export users for full list.")
            text = "\n".join(lines)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text[:4000], reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── LIVE CHATS ────────────────────────────
    elif data == "a_live":
        users = bot_data.get("users", {})
        chats = bot_data.get("chats", {})
        now = datetime.now()
        lines = ["🟢 **LIVE (last 30 min)**\n━━━━━━━━━━━━━━━━━━━"]
        count = 0
        for uid, u in users.items():
            last = u.get("last_active", "")
            if not last:
                continue
            try:
                delta = (now - datetime.fromisoformat(last)).total_seconds()
                if delta < 1800:
                    last_msg = ""
                    if uid in chats and chats[uid]:
                        last_msg = chats[uid][-1].get("user", "")[:60]
                    lines.append(
                        f"`{uid}` {u.get('name','?')}\n"
                        f"  Last: {last_msg or 'N/A'}\n"
                        f"  ⏰ {int(delta//60)}m ago"
                    )
                    count += 1
            except Exception:
                pass
        if count == 0:
            lines.append("No active users in last 30 minutes.")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text("\n".join(lines)[:4000], reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── AI SETTINGS ───────────────────────────
    elif data == "a_ai":
        await q.edit_message_text("🤖 **AI Settings**\nConfigure the AI behavior:", reply_markup=get_ai_menu(), parse_mode=ParseMode.MARKDOWN)

    elif data == "ai_viewprompt":
        prompt = bot_data.get("cfg", {}).get("system_prompt", "N/A")
        text = f"📝 **Current System Prompt:**\n\n`{prompt[:3500]}`"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_ai")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "ai_setprompt":
        ctx.user_data["awaiting"] = "set_prompt"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="a_ai")]])
        await q.edit_message_text(
            "📝 **Set System Prompt**\n\nSend the new system prompt as a message now:",
            reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )

    elif data == "ai_pers":
        await q.edit_message_text("🎭 **Select Personality**\n✅ = currently active:", reply_markup=get_personality_menu(), parse_mode=ParseMode.MARKDOWN)

    elif data == "ai_temp":
        await q.edit_message_text("🌡 **Select Temperature**\n✅ = current value:", reply_markup=get_temperature_menu(), parse_mode=ParseMode.MARKDOWN)

    elif data == "ai_tokens":
        await q.edit_message_text("📏 **Select Max Tokens**\n✅ = current value:", reply_markup=get_tokens_menu(), parse_mode=ParseMode.MARKDOWN)

    elif data == "ai_active":
        pers = bot_data.get("cfg", {}).get("personality", "default")
        prompt = PERSONAS.get(pers, "")
        await q.answer(f"Active: {pers}\n{prompt[:100]}", show_alert=True)

    elif data == "ai_reset":
        bot_data["cfg"]["temperature"] = 0.9
        bot_data["cfg"]["max_tokens"] = 4096
        bot_data["cfg"]["personality"] = "default"
        bot_data["cfg"]["system_prompt"] = PERSONAS["default"]
        await q.answer("✅ Reset to defaults!", show_alert=True)
        await q.edit_message_text("🤖 **AI Settings** (Reset done):", reply_markup=get_ai_menu(), parse_mode=ParseMode.MARKDOWN)

    # ── PERSONALITY SELECT ─────────────────────
    elif data.startswith("pers_"):
        name = data[5:]
        if name in PERSONAS:
            bot_data["cfg"]["personality"] = name
            bot_data["cfg"]["system_prompt"] = PERSONAS[name]
            await q.answer(f"✅ Personality set to: {name}", show_alert=True)
            await q.edit_message_text("🎭 **Personalities** (updated):", reply_markup=get_personality_menu(), parse_mode=ParseMode.MARKDOWN)

    # ── TEMPERATURE SELECT ─────────────────────
    elif data.startswith("temp_"):
        val = float(data[5:])
        bot_data["cfg"]["temperature"] = val
        await q.answer(f"✅ Temperature set to {val}", show_alert=True)
        await q.edit_message_text("🌡 **Temperature** (updated):", reply_markup=get_temperature_menu(), parse_mode=ParseMode.MARKDOWN)

    # ── TOKENS SELECT ─────────────────────────
    elif data.startswith("tok_"):
        val = int(data[4:])
        bot_data["cfg"]["max_tokens"] = val
        await q.answer(f"✅ Max tokens set to {val}", show_alert=True)
        await q.edit_message_text("📏 **Max Tokens** (updated):", reply_markup=get_tokens_menu(), parse_mode=ParseMode.MARKDOWN)

    # ── BROADCAST INFO ────────────────────────
    elif data == "a_bcast":
        bs = bot_data.get("broadcast_stats", {})
        text = (
            "📢 **BROADCAST**\n━━━━━━━━━━━━━━━━━━━\n"
            f"Last: ✅ {bs.get('sent',0)} sent | ❌ {bs.get('failed',0)} failed\n\n"
            "Use command: `/broadcast Your message here`\n"
            "This sends to ALL users via the User Bot."
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── BAN INFO ──────────────────────────────
    elif data == "a_ban":
        banned = bot_data.get("banned", [])
        text = (
            f"🚫 **BAN SYSTEM**\n━━━━━━━━━━━━━━━━━━━\n"
            f"Currently banned: `{len(banned)}`\n\n"
            "Commands:\n"
            "`/ban <user_id>` — Ban user\n"
            "`/unban <user_id>` — Unban user\n"
            "`/warn <user_id>` — Add warning (3=auto ban)"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── MUTE INFO ─────────────────────────────
    elif data == "a_mute":
        muted = bot_data.get("muted", {})
        text = (
            f"🔇 **MUTE SYSTEM**\n━━━━━━━━━━━━━━━━━━━\n"
            f"Currently muted: `{len(muted)}`\n\n"
            "Commands:\n"
            "`/mute <user_id> <minutes>` — Mute user\n"
            "`/unmute <user_id>` — Unmute user"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── PREMIUM INFO ──────────────────────────
    elif data == "a_prem":
        prem = bot_data.get("premium", {})
        limits = bot_data.get("limits", {})
        text = (
            f"💎 **PREMIUM**\n━━━━━━━━━━━━━━━━━━━\n"
            f"Active premium users: `{len(prem)}`\n"
            f"Free limit: `{limits.get('free', 20)}/day`\n"
            f"Premium limit: `{limits.get('prem', 99999)}/day`\n\n"
            "Commands:\n"
            "`/premium <id> <days>` — Grant (0=permanent)\n"
            "`/removepremium <id>` — Remove\n"
            "`/setlimit free <n>` — Set free limit\n"
            "`/setlimit prem <n>` — Set premium limit"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── CODES INFO ────────────────────────────
    elif data == "a_codes":
        codes = bot_data.get("codes", {})
        active = [c for c, v in codes.items() if not v.get("used")]
        text = (
            f"🎫 **REDEEM CODES**\n━━━━━━━━━━━━━━━━━━━\n"
            f"Total codes: `{len(codes)}`\n"
            f"Active (unused): `{len(active)}`\n\n"
        )
        if active:
            text += "**Active Codes:**\n"
            for c in active[:10]:
                text += f"`{c}` — {codes[c].get('days', '?')} days\n"
            if len(active) > 10:
                text += f"...and {len(active)-10} more\n"
        text += (
            "\nCommands:\n"
            "`/gencode <days> <amount>` — Generate codes\n"
            "`/deletecode <code>` — Delete code\n"
            "`/redeeminfo` — Full list"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── FORCE SUB ─────────────────────────────
    elif data == "a_fsub":
        fs = bot_data.get("force_sub")
        text = (
            f"🔒 **FORCE SUBSCRIBE**\n━━━━━━━━━━━━━━━━━━━\n"
            f"Status: `{'ON — ' + fs if fs else 'OFF'}`\n\n"
            "Commands:\n"
            "`/forcesub @channel` — Enable\n"
            "`/forcesub off` — Disable"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── ANTIFLOOD ─────────────────────────────
    elif data == "a_flood":
        af = bot_data.get("antiflood", {})
        text = (
            f"🛡 **ANTIFLOOD**\n━━━━━━━━━━━━━━━━━━━\n"
            f"Status: `{'ON' if af.get('on') else 'OFF'}`\n"
            f"Max msgs: `{af.get('max', 8)}` in `{af.get('win', 10)}s`\n"
            f"Auto-mute: `{af.get('mute', 5)} minutes`\n\n"
            "Commands:\n"
            "`/antiflood on` — Enable\n"
            "`/antiflood off` — Disable\n"
            "`/antiflood set <max> <secs> <mute_mins>` — Configure"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── VIEW CHAT ─────────────────────────────
    elif data == "a_vchat":
        text = (
            "💬 **VIEW CHAT**\n━━━━━━━━━━━━━━━━━━━\n\n"
            "Command: `/viewchat <user_id>`\n"
            "Shows last 15 messages of any user."
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── CLEAR MEM ─────────────────────────────
    elif data == "a_clearmem":
        text = (
            "🧹 **CLEAR MEMORY**\n━━━━━━━━━━━━━━━━━━━\n\n"
            "`/clearmem <user_id>` — Clear specific user\n"
            "`/clearmemall` — Clear ALL memories\n"
            "`/clearchats` — Clear all chat logs"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── MAINTENANCE ───────────────────────────
    elif data == "a_maint":
        current = bot_data.get("maint", False)
        bot_data["maint"] = not current
        status = "ON 🔧" if bot_data["maint"] else "OFF ✅"
        await q.answer(f"Maintenance {status}", show_alert=True)
        await q.edit_message_text("🏠 Main Menu", reply_markup=get_admin_main_menu())

    # ── RESTART ───────────────────────────────
    elif data == "a_restart":
        bot_data["convos"] = {}
        bot_data["flood"] = {}
        bot_data["stats"]["groq_calls"] = 0
        await save_data()
        await q.answer("✅ Bot memory cleared & restarted!", show_alert=True)
        await q.edit_message_text("🏠 Main Menu", reply_markup=get_admin_main_menu())

    # ── EXPORT ────────────────────────────────
    elif data == "a_export":
        text = (
            "📋 **EXPORT DATA**\n━━━━━━━━━━━━━━━━━━━\n\n"
            "`/export users` — Full user list with stats"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── PING ──────────────────────────────────
    elif data == "a_ping":
        t = time.time()
        await q.answer("🏓 Pong!")
        ms = int((time.time() - t) * 1000)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(f"⚡ **Ping Result**\n\nResponse: `{ms}ms`\nUptime: `{uptime_str()}`", reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── ADVERTISE ─────────────────────────────
    elif data == "a_ad":
        ad = bot_data.get("ad_stats", {})
        text = (
            f"📢 **ADVERTISE**\n━━━━━━━━━━━━━━━━━━━\n"
            f"Ads sent: `{ad.get('sent', 0)}`\n"
            f"Ads failed: `{ad.get('failed', 0)}`\n\n"
            "Command: `/advertise Your ad text here`"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── WEBHOOK ───────────────────────────────
    elif data == "a_webhook":
        text = (
            "🌐 **WEBHOOK INFO**\n━━━━━━━━━━━━━━━━━━━\n"
            "Mode: Polling (Render worker)\n"
            f"Uptime: `{uptime_str()}`\n"
            f"PORT: `{PORT}`"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── SYSTEM PROMPT PANEL ───────────────────
    elif data == "a_sysprompt":
        cfg = bot_data.get("cfg", {})
        prompt = cfg.get("system_prompt", "")
        persona = cfg.get("personality", "default")
        prev = prompt[:300] + ("..." if len(prompt) > 300 else "")
        text = (
            "⚙️ **SYSTEM PROMPT MANAGER**\n━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎭 Active Persona: `{persona}`\n"
            f"📏 Prompt Length: `{len(prompt)} chars`\n\n"
            f"📝 **Preview:**\n`{prev}`\n\n"
            "Choose an action:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👁 View Full Prompt", callback_data="ai_viewprompt")],
            [InlineKeyboardButton("✏️ Edit/Set New Prompt", callback_data="ai_setprompt")],
            [InlineKeyboardButton("🎭 Personality Presets", callback_data="ai_pers")],
            [InlineKeyboardButton("🔄 Reset to Default", callback_data="ai_reset")],
            [InlineKeyboardButton("💬 Set Welcome Msg", callback_data="a_setwelcome"),
             InlineKeyboardButton("🔧 Set Maint Msg", callback_data="a_setmaintmsg")],
            [InlineKeyboardButton("⬅️ Back to Main", callback_data="a_main")],
        ])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    elif data == "a_setwelcome":
        ctx.user_data["awaiting"] = "set_welcome"
        current = bot_data.get("welcome", "")[:200]
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="a_sysprompt")]])
        await q.edit_message_text(
            f"💬 **Set Welcome Message**\n\nVariables you can use:\n"
            "`{name}` — User name\n`{plan}` — Plan type\n"
            "`{daily}` — Messages used today\n`{limit}` — Daily limit\n\n"
            f"**Current:**\n`{current}`\n\n"
            "Send the new welcome message now:",
            reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )

    elif data == "a_setmaintmsg":
        ctx.user_data["awaiting"] = "set_maint_msg"
        current = bot_data.get("maintenance_msg", "")[:200]
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="a_sysprompt")]])
        await q.edit_message_text(
            f"🔧 **Set Maintenance Message**\n\n"
            f"**Current:**\n`{current}`\n\n"
            "Send the new maintenance message:",
            reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )

    # ── PERSONALITIES PANEL ───────────────────
    elif data == "a_pers":
        await q.edit_message_text("🎭 **Select Personality**\n✅ = currently active:", reply_markup=get_personality_menu(), parse_mode=ParseMode.MARKDOWN)

    # ── DAILY REPORT ─────────────────────────
    elif data == "a_daily":
        reset_daily_stats()
        stats = bot_data.get("stats", {})
        users = bot_data.get("users", {})
        today = datetime.now().strftime("%Y-%m-%d")
        new_today = sum(
            1 for u in users.values()
            if u.get("joined", "")[:10] == today
        )
        text = (
            f"📊 **DAILY REPORT — {today}**\n━━━━━━━━━━━━━━━━━━━\n"
            f"💬 Messages today: `{stats.get('today_messages', 0)}`\n"
            f"👤 New users today: `{new_today}`\n"
            f"🪙 Tokens used: `{stats.get('total_tokens', 0)}`\n"
            f"✅ API calls: `{stats.get('groq_calls', 0)}`\n"
            f"❌ API errors: `{stats.get('groq_errors', 0)}`\n"
            f"⏱ Uptime: `{uptime_str()}`"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

    # ── CLEAR ALL LOGS ────────────────────────
    elif data == "a_clrlogs":
        bot_data["chats"] = {}
        await save_data()
        await q.answer("✅ All chat logs cleared!", show_alert=True)
        await q.edit_message_text("🏠 Main Menu", reply_markup=get_admin_main_menu())


# ══════════════════════════════════════════════
# ADMIN TEXT COMMANDS
# ══════════════════════════════════════════════
@admin_only
async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    msg = " ".join(ctx.args)
    users = bot_data.get("users", {})
    sent = failed = 0
    status_msg = await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")

    user_bot = Application.builder().token(USER_BOT_TOKEN).build()
    async with user_bot:
        for uid in list(users.keys()):
            try:
                await user_bot.bot.send_message(int(uid), f"📢 **Broadcast**\n\n{msg}", parse_mode=ParseMode.MARKDOWN)
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1

    bot_data["stats"]["total_broadcasts"] = bot_data["stats"].get("total_broadcasts", 0) + 1
    bot_data["broadcast_stats"] = {"sent": sent, "failed": failed}
    await status_msg.edit_text(f"✅ Broadcast done!\nSent: {sent} | Failed: {failed}")


@admin_only
async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    try:
        uid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return
    if uid not in [int(x) for x in bot_data.get("banned", [])]:
        bot_data["banned"].append(uid)
        bot_data["stats"]["total_bans"] = bot_data["stats"].get("total_bans", 0) + 1
    await update.message.reply_text(f"🚫 User `{uid}` banned.", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    try:
        uid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return
    bot_data["banned"] = [x for x in bot_data.get("banned", []) if int(x) != uid]
    await update.message.reply_text(f"✅ User `{uid}` unbanned.", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_warn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /warn <user_id>")
        return
    try:
        uid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return
    u = get_user(uid)
    u["warnings"] = u.get("warnings", 0) + 1
    if u["warnings"] >= 3:
        if uid not in [int(x) for x in bot_data.get("banned", [])]:
            bot_data["banned"].append(uid)
        await update.message.reply_text(f"⚠️ User `{uid}` has {u['warnings']} warnings. **AUTO-BANNED.**", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"⚠️ User `{uid}` warned. Warnings: {u['warnings']}/3", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_mute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /mute <user_id> <minutes>")
        return
    try:
        uid = int(ctx.args[0])
        mins = int(ctx.args[1])
    except ValueError:
        await update.message.reply_text("Invalid args.")
        return
    until = (datetime.now() + timedelta(minutes=mins)).isoformat()
    bot_data["muted"][str(uid)] = {"until": until, "reason": "admin"}
    bot_data["stats"]["total_mutes"] = bot_data["stats"].get("total_mutes", 0) + 1
    await update.message.reply_text(f"🔇 User `{uid}` muted for {mins} minutes.", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_unmute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /unmute <user_id>")
        return
    uid = str(ctx.args[0])
    bot_data["muted"].pop(uid, None)
    await update.message.reply_text(f"✅ User `{uid}` unmuted.", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_premium(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /premium <user_id> <days> (0=permanent)")
        return
    try:
        uid = int(ctx.args[0])
        days = int(ctx.args[1])
    except ValueError:
        await update.message.reply_text("Invalid args.")
        return
    expiry = "permanent" if days == 0 else (datetime.now() + timedelta(days=days)).isoformat()
    bot_data["premium"][str(uid)] = {"expiry": expiry, "granted": datetime.now().isoformat()}
    label = "permanent" if days == 0 else f"{days} days"
    await update.message.reply_text(f"💎 User `{uid}` granted premium ({label}).", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_removepremium(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /removepremium <user_id>")
        return
    uid = str(ctx.args[0])
    bot_data["premium"].pop(uid, None)
    await update.message.reply_text(f"✅ Premium removed from `{uid}`.", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_setlimit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /setlimit <free/prem> <number>")
        return
    plan = ctx.args[0].lower()
    try:
        n = int(ctx.args[1])
    except ValueError:
        await update.message.reply_text("Invalid number.")
        return
    if plan not in ("free", "prem"):
        await update.message.reply_text("Plan must be 'free' or 'prem'.")
        return
    bot_data["limits"][plan] = n
    await update.message.reply_text(f"✅ {plan} limit set to {n}/day.", parse_mode=ParseMode.MARKDOWN)


import secrets
import string

@admin_only
async def cmd_gencode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /gencode <days> <amount>")
        return
    try:
        days = int(ctx.args[0])
        amount = min(int(ctx.args[1]), 50)
    except ValueError:
        await update.message.reply_text("Invalid args.")
        return
    codes = []
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(amount):
        code = "DN-" + "".join(secrets.choice(alphabet) for _ in range(8))
        bot_data["codes"][code] = {"days": days, "used": False, "created": datetime.now().isoformat()}
        codes.append(code)
    text = f"🎫 Generated {amount} code(s) ({days} days):\n\n" + "\n".join(f"`{c}`" for c in codes)
    await update.message.reply_text(text[:4000], parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_deletecode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /deletecode <code>")
        return
    code = ctx.args[0].upper()
    if code in bot_data.get("codes", {}):
        del bot_data["codes"][code]
        await update.message.reply_text(f"✅ Code `{code}` deleted.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("Code not found.")


@admin_only
async def cmd_redeeminfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    codes = bot_data.get("codes", {})
    if not codes:
        await update.message.reply_text("No codes generated yet.")
        return
    lines = ["🎫 **All Codes:**\n"]
    for c, v in codes.items():
        status = "✅ Used" if v.get("used") else "🟢 Active"
        lines.append(f"`{c}` — {v.get('days','?')}d — {status}")
    await update.message.reply_text("\n".join(lines)[:4000], parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_forcesub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /forcesub @channel OR /forcesub off")
        return
    if ctx.args[0].lower() == "off":
        bot_data["force_sub"] = None
        await update.message.reply_text("✅ Force subscribe disabled.")
    else:
        ch = ctx.args[0] if ctx.args[0].startswith("@") else "@" + ctx.args[0]
        bot_data["force_sub"] = ch
        await update.message.reply_text(f"✅ Force subscribe set to {ch}")


@admin_only
async def cmd_antiflood(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /antiflood on|off|set <max> <win> <mute>")
        return
    af = bot_data.get("antiflood", {})
    sub = ctx.args[0].lower()
    if sub == "on":
        af["on"] = True
        await update.message.reply_text("✅ Antiflood enabled.")
    elif sub == "off":
        af["on"] = False
        await update.message.reply_text("✅ Antiflood disabled.")
    elif sub == "set" and len(ctx.args) >= 4:
        try:
            af["max"] = int(ctx.args[1])
            af["win"] = int(ctx.args[2])
            af["mute"] = int(ctx.args[3])
            await update.message.reply_text(f"✅ Antiflood: {af['max']} msgs/{af['win']}s, mute {af['mute']}min")
        except ValueError:
            await update.message.reply_text("Invalid values.")
    bot_data["antiflood"] = af


@admin_only
async def cmd_viewchat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /viewchat <user_id>")
        return
    uid = str(ctx.args[0])
    chats = bot_data.get("chats", {}).get(uid, [])
    if not chats:
        await update.message.reply_text("No chat history for this user.")
        return
    lines = [f"💬 **Chat Log — User {uid}** (last 15)\n━━━━━━━━━━━━━━━━━━━"]
    for c in chats[-15:]:
        ts = c.get("ts", "")[:16]
        lines.append(f"\n⏰ {ts}\n👤 {c.get('user','')[:100]}\n🤖 {c.get('ai','')[:100]}")
    await update.message.reply_text("\n".join(lines)[:4000], parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_clearmem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /clearmem <user_id>")
        return
    uid = str(ctx.args[0])
    bot_data["convos"].pop(uid, None)
    await update.message.reply_text(f"✅ Memory cleared for user `{uid}`.", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_clearmemall(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_data["convos"] = {}
    await update.message.reply_text("✅ All memories cleared.")


@admin_only
async def cmd_clearchats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_data["chats"] = {}
    await update.message.reply_text("✅ All chat logs cleared.")


@admin_only
async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or ctx.args[0] != "users":
        await update.message.reply_text("Usage: /export users")
        return
    users = bot_data.get("users", {})
    lines = [f"📋 **USER EXPORT** ({len(users)} users)\n━━━━━━━━━━━━━━━━━━━"]
    for uid, u in users.items():
        plan = "💎" if is_premium(int(uid)) else "🆓"
        status = "🚫" if is_banned(int(uid)) else ("🔇" if is_muted(int(uid)) else "✅")
        lines.append(
            f"{status}{plan} `{uid}` | {u.get('name','?')} | "
            f"@{u.get('username','N/A')} | {u.get('messages',0)} msgs | "
            f"⚠️{u.get('warnings',0)}"
        )
    for chunk in split_long_message("\n".join(lines)):
        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_sysprompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /sysprompt <new system prompt text>")
        return
    new_prompt = " ".join(ctx.args)
    bot_data["cfg"]["system_prompt"] = new_prompt
    await update.message.reply_text(f"✅ System prompt updated!\n\nPreview:\n`{new_prompt[:300]}`", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_advertise(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /advertise <ad message>")
        return
    msg = " ".join(ctx.args)
    users = bot_data.get("users", {})
    sent = failed = 0
    user_bot = Application.builder().token(USER_BOT_TOKEN).build()
    async with user_bot:
        for uid in list(users.keys()):
            try:
                await user_bot.bot.send_message(
                    int(uid),
                    f"📢 **Advertisement**\n\n{msg}\n\n_— DarkNova AI_",
                    parse_mode=ParseMode.MARKDOWN
                )
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1
    bot_data["ad_stats"]["sent"] = bot_data["ad_stats"].get("sent", 0) + sent
    bot_data["ad_stats"]["failed"] = bot_data["ad_stats"].get("failed", 0) + failed
    await update.message.reply_text(f"📢 Ad sent! ✅{sent} | ❌{failed}")


@admin_only
async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = time.time()
    msg = await update.message.reply_text("🏓 Pong!")
    ms = int((time.time() - t) * 1000)
    await msg.edit_text(f"⚡ **Ping:** `{ms}ms`\n⏱ Uptime: `{uptime_str()}`", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_admin_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle awaiting states from admin panel"""
    awaiting = ctx.user_data.get("awaiting")
    text = update.message.text.strip()

    if awaiting == "set_prompt":
        bot_data["cfg"]["system_prompt"] = text
        bot_data["cfg"]["personality"] = "custom"
        ctx.user_data.pop("awaiting", None)
        await save_data()
        reply = (
            "✅ *System Prompt Updated!*\n\n"
            f"📝 *Preview:*\n```\n{text[:400]}\n```\n\n"
            f"📏 Length: {len(text)} chars\n"
            "🤖 AI will use this for all users."
        )
        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN, reply_markup=get_admin_main_menu())

    elif awaiting == "set_maint_msg":
        bot_data["maintenance_msg"] = text
        ctx.user_data.pop("awaiting", None)
        await save_data()
        await update.message.reply_text(
            f"✅ Maintenance message updated!\n`{text[:200]}`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=get_admin_main_menu()
        )

    elif awaiting == "set_welcome":
        bot_data["welcome"] = text
        ctx.user_data.pop("awaiting", None)
        await save_data()
        await update.message.reply_text(
            f"✅ Welcome message updated!\n`{text[:200]}`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=get_admin_main_menu()
        )

    else:
        await update.message.reply_text("🏠 Use /start to open the admin panel.", reply_markup=get_admin_main_menu())

# ══════════════════════════════════════════════
# USER BOT HANDLERS
# ══════════════════════════════════════════════
USER_KEYBOARD = ReplyKeyboardMarkup(
    [["💬 Chat", "🧹 Reset"], ["ℹ️ About", "📊 Plan"], ["🎫 Redeem", "📞 Contact"]],
    resize_keyboard=True
)


async def user_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid):
        await update.message.reply_text("🚫 You are banned.")
        return

    # Handle /start CODE (redeem via start)
    if ctx.args:
        code = ctx.args[0].upper()
        await _redeem_code(update, uid, code)
        return

    # Force sub check
    if not await check_force_sub(uid, update.get_bot()):
        await update.message.reply_text(
            "🔒 You must join our channel first!",
            reply_markup=force_sub_keyboard()
        )
        return

    # Register user
    u = get_user(uid)
    u["name"] = update.effective_user.first_name or "User"
    u["username"] = update.effective_user.username
    u["last_active"] = datetime.now().isoformat()

    plan = "💎 Premium" if is_premium(uid) else "🆓 Free"
    daily = get_daily_count(uid)
    limit = get_limit(uid)
    welcome = bot_data.get("welcome", DEFAULT_DATA["welcome"])
    text = welcome.format(
        name=u["name"],
        plan=plan,
        daily=daily,
        limit=limit if limit < 99999 else "∞"
    )
    await update.message.reply_text(text, reply_markup=USER_KEYBOARD, parse_mode=ParseMode.MARKDOWN)


async def user_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid):
        return
    text = (
        "🤖 **DarkNova AI — Commands**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "/start — Welcome & info\n"
        "/help — This list\n"
        "/reset — Clear your memory\n"
        "/about — About this bot\n"
        "/plan — Check your plan\n"
        "/redeem <code> — Activate premium\n"
        "/contact — Reach admin\n"
        "/ping — Check latency\n"
        "/speed — Test AI speed\n"
        "/model — Show AI model\n\n"
        "💬 Just send any message to chat with AI!"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def user_about(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg = bot_data.get("cfg", {})
    text = (
        "🤖 **DarkNova AI Bot**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "A powerful AI assistant built on Groq's lightning-fast API.\n\n"
        f"🧠 Model: `{cfg.get('model', 'llama-3.1-8b-instant')}`\n"
        f"🎭 Persona: `{cfg.get('personality', 'default')}`\n"
        f"💎 Features: Memory, Code, Multilingual\n\n"
        "👨‍💻 Created by: **@MrNewton_2**\n"
        "🔥 Powered by: Groq AI + Python"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def user_plan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid):
        return
    plan = "💎 Premium" if is_premium(uid) else "🆓 Free"
    daily = get_daily_count(uid)
    limit = get_limit(uid)
    prem_info = ""
    if is_premium(uid):
        p = bot_data.get("premium", {}).get(str(uid), {})
        expiry = p.get("expiry", "Unknown")
        prem_info = f"\n⏳ Expires: `{expiry}`" if expiry != "permanent" else "\n♾️ Permanent"
    text = (
        f"📊 **Your Plan**\n━━━━━━━━━━━━━━━━━━━\n"
        f"Plan: {plan}{prem_info}\n"
        f"Today: `{daily}/{limit if limit < 99999 else '∞'}`\n"
        f"Memory: `{'40 msgs (48h)' if is_premium(uid) else 'Off (Free plan)'}`\n\n"
        "🎫 Use `/redeem <code>` to upgrade!"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def user_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid):
        return
    if not is_premium(uid):
        await update.message.reply_text("⚠️ Memory is a 💎 Premium feature. Upgrade to use it!")
        return
    bot_data["convos"].pop(str(uid), None)
    await update.message.reply_text("🧹 Your memory has been cleared!")


async def user_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📞 **Contact Admin**\n\n"
        f"Admin ID: `{ADMIN_ID}`\n"
        f"For support, reach out directly.",
        parse_mode=ParseMode.MARKDOWN
    )


async def user_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = time.time()
    msg = await update.message.reply_text("🏓 Pinging...")
    ms = int((time.time() - t) * 1000)
    await msg.edit_text(f"⚡ Pong! `{ms}ms`", parse_mode=ParseMode.MARKDOWN)


async def user_speed(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid):
        return
    msg = await update.message.reply_text("⏱ Testing AI speed...")
    t = time.time()
    reply, _ = await call_groq(uid, "Say 'Speed test OK' in exactly 3 words.")
    elapsed = round(time.time() - t, 2)
    await msg.edit_text(f"⚡ AI Response Time: `{elapsed}s`\n\n_{reply}_", parse_mode=ParseMode.MARKDOWN)


async def user_model(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg = bot_data.get("cfg", {})
    await update.message.reply_text(
        f"🤖 **Current AI Model**\n\n"
        f"Model: `{cfg.get('model', 'N/A')}`\n"
        f"Temp: `{cfg.get('temperature', 0.9)}`\n"
        f"Max Tokens: `{cfg.get('max_tokens', 4096)}`\n"
        f"Persona: `{cfg.get('personality', 'default')}`",
        parse_mode=ParseMode.MARKDOWN
    )


async def _redeem_code(update: Update, uid: int, code: str):
    codes = bot_data.get("codes", {})
    if code not in codes:
        await update.message.reply_text("❌ Invalid code.")
        return
    c = codes[code]
    if c.get("used"):
        await update.message.reply_text("❌ Code already used.")
        return
    days = c.get("days", 30)
    expiry = "permanent" if days == 0 else (datetime.now() + timedelta(days=days)).isoformat()
    bot_data["premium"][str(uid)] = {"expiry": expiry, "granted": datetime.now().isoformat()}
    codes[code]["used"] = True
    codes[code]["used_by"] = uid
    label = "permanent" if days == 0 else f"{days} days"
    await update.message.reply_text(
        f"✅ Code redeemed successfully!\n💎 You now have Premium ({label})!",
        parse_mode=ParseMode.MARKDOWN
    )


async def user_redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid):
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /redeem <code>")
        return
    await _redeem_code(update, uid, ctx.args[0].upper())


async def user_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    # Force sub check
    if data == "cs":
        uid = q.from_user.id
        if await check_force_sub(uid, q.get_bot()):
            await q.edit_message_text("✅ Verified! You can now use the bot. Send /start")
        else:
            await q.answer("❌ You haven't joined yet!", show_alert=True)
        return

    # Copy code
    if data.startswith("copy_"):
        code_text = data[5:]
        await q.message.reply_text(f"`{code_text}`", parse_mode=ParseMode.MARKDOWN)
        await q.answer("Code sent!")
        return


async def user_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Main message handler for user bot"""
    if not update.message or not update.message.text:
        return

    uid = update.effective_user.id
    text = update.message.text.strip()

    # Ban check
    if is_banned(uid):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    # Maintenance check
    if bot_data.get("maint"):
        await update.message.reply_text(bot_data.get("maintenance_msg", "🔧 Under maintenance..."))
        return

    # Force sub check
    if not await check_force_sub(uid, update.get_bot()):
        await update.message.reply_text("🔒 Join our channel first!", reply_markup=force_sub_keyboard())
        return

    # Mute check
    if is_muted(uid):
        muted_info = bot_data["muted"].get(str(uid), {})
        until = muted_info.get("until", "")
        remaining = ""
        if until:
            try:
                rem = int((datetime.fromisoformat(until) - datetime.now()).total_seconds() / 60)
                remaining = f" ({rem} min remaining)"
            except Exception:
                pass
        await update.message.reply_text(f"🔇 You are muted{remaining}.")
        return

    # Antiflood
    if check_flood(uid):
        apply_flood_mute(uid)
        await update.message.reply_text("🛡 Slow down! You've been muted for flooding.")
        return

    # Register/update user
    u = get_user(uid)
    u["name"] = update.effective_user.first_name or "User"
    u["username"] = update.effective_user.username
    u["last_active"] = datetime.now().isoformat()

    # Keyboard shortcuts
    if text == "💬 Chat":
        await update.message.reply_text("💬 Just type your message and I'll respond!")
        return
    elif text == "🧹 Reset":
        await user_reset(update, ctx)
        return
    elif text == "ℹ️ About":
        await user_about(update, ctx)
        return
    elif text == "📊 Plan":
        await user_plan(update, ctx)
        return
    elif text == "🎫 Redeem":
        await update.message.reply_text("🎫 Use: /redeem <your-code>")
        return
    elif text == "📞 Contact":
        await user_contact(update, ctx)
        return

    # Daily limit check
    daily = get_daily_count(uid)
    limit = get_limit(uid)
    if daily >= limit:
        await update.message.reply_text(
            f"⚠️ Daily limit reached! ({daily}/{limit})\n"
            "💎 Upgrade to Premium for unlimited queries!\n"
            "🎫 Get a code from the admin."
        )
        return

    # Group: only respond to mentions/replies
    if update.message.chat.type in ["group", "supergroup"]:
        bot_user = await update.get_bot().get_me()
        is_mention = f"@{bot_user.username}" in text
        is_reply = (
            update.message.reply_to_message and
            update.message.reply_to_message.from_user and
            update.message.reply_to_message.from_user.id == bot_user.id
        )
        if not is_mention and not is_reply:
            return

    # Typing indicator
    await update.message.chat.send_action("typing")

    # AI call
    response, tokens = await call_groq(uid, text)

    # Update stats
    u["messages"] = u.get("messages", 0) + 1
    bot_data["stats"]["total_messages"] = bot_data["stats"].get("total_messages", 0) + 1
    bot_data["stats"]["today_messages"] = bot_data["stats"].get("today_messages", 0) + 1
    increment_daily(uid)
    reset_daily_stats()

    # Send response
    if has_code(response):
        code_blocks, clean_text = extract_code_blocks(response)

        # Send non-code text first
        clean_text = clean_text.replace("[CODE BLOCK]", "").strip()
        if clean_text:
            for chunk in split_long_message(clean_text):
                await update.message.reply_text(chunk)

        # Send each code block
        for lang, code in code_blocks:
            lang = lang or "text"
            code_msg = f"```{lang}\n{code}\n```"
            safe_code = code[:200].replace("`", "'")
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 Copy Code", callback_data=f"copy_{safe_code}")
            ]])
            for chunk in split_long_message(code_msg, 4000):
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    else:
        for chunk in split_long_message(response):
            await update.message.reply_text(chunk)

    await save_data()

# ══════════════════════════════════════════════
# ERROR HANDLER
# ══════════════════════════════════════════════
async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception: {ctx.error}", exc_info=ctx.error)

# ══════════════════════════════════════════════
# AIOHTTP WEB SERVER (for Render health check)
# ══════════════════════════════════════════════
async def health_check(request):
    from aiohttp.web import Response
    return Response(
        text=json.dumps({
            "status": "ok",
            "uptime": uptime_str(),
            "users": len(bot_data.get("users", {})),
            "messages": bot_data.get("stats", {}).get("total_messages", 0),
        }),
        content_type="application/json"
    )


async def start_web_server():
    from aiohttp.web import Application as WebApp, AppRunner, TCPSite
    web_app = WebApp()
    web_app.router.add_get("/", health_check)
    runner = AppRunner(web_app)
    await runner.setup()
    site = TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")

# ══════════════════════════════════════════════
# BUILD APPLICATIONS
# ══════════════════════════════════════════════
def build_admin_app() -> Application:
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", admin_start))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("warn", cmd_warn))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("unmute", cmd_unmute))
    app.add_handler(CommandHandler("premium", cmd_premium))
    app.add_handler(CommandHandler("removepremium", cmd_removepremium))
    app.add_handler(CommandHandler("setlimit", cmd_setlimit))
    app.add_handler(CommandHandler("gencode", cmd_gencode))
    app.add_handler(CommandHandler("deletecode", cmd_deletecode))
    app.add_handler(CommandHandler("redeeminfo", cmd_redeeminfo))
    app.add_handler(CommandHandler("forcesub", cmd_forcesub))
    app.add_handler(CommandHandler("antiflood", cmd_antiflood))
    app.add_handler(CommandHandler("viewchat", cmd_viewchat))
    app.add_handler(CommandHandler("clearmem", cmd_clearmem))
    app.add_handler(CommandHandler("clearmemall", cmd_clearmemall))
    app.add_handler(CommandHandler("clearchats", cmd_clearchats))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("sysprompt", cmd_sysprompt))
    app.add_handler(CommandHandler("advertise", cmd_advertise))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CallbackQueryHandler(admin_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_admin_text))
    app.add_error_handler(error_handler)

    return app


def build_user_app() -> Application:
    app = Application.builder().token(USER_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", user_start))
    app.add_handler(CommandHandler("help", user_help))
    app.add_handler(CommandHandler("about", user_about))
    app.add_handler(CommandHandler("plan", user_plan))
    app.add_handler(CommandHandler("reset", user_reset))
    app.add_handler(CommandHandler("contact", user_contact))
    app.add_handler(CommandHandler("ping", user_ping))
    app.add_handler(CommandHandler("speed", user_speed))
    app.add_handler(CommandHandler("model", user_model))
    app.add_handler(CommandHandler("redeem", user_redeem))
    app.add_handler(CallbackQueryHandler(user_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_message))
    app.add_error_handler(error_handler)

    return app

# ══════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════
async def main():
    if not ADMIN_BOT_TOKEN or not USER_BOT_TOKEN:
        logger.error("ADMIN_BOT_TOKEN or USER_BOT_TOKEN not set!")
        return
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not set!")
        return

    load_data()
    bot_data["start_time"] = datetime.now().isoformat()

    logger.info("Starting DarkNova AI Bot v2.0...")

    admin_app = build_admin_app()
    user_app  = build_user_app()

    await start_web_server()
    asyncio.create_task(periodic_save())

    # Initialize both apps
    await admin_app.initialize()
    await user_app.initialize()

    await admin_app.start()
    await user_app.start()

    # Start polling for both
    await admin_app.updater.start_polling(drop_pending_updates=True)
    await user_app.updater.start_polling(drop_pending_updates=True)

    logger.info("Both bots are running! Press Ctrl+C to stop.")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        await save_data()
        await admin_app.updater.stop()
        await user_app.updater.stop()
        await admin_app.stop()
        await user_app.stop()
        await admin_app.shutdown()
        await user_app.shutdown()
        logger.info("Bots stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
