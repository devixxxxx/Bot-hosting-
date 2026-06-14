"""
╔══════════════════════════════════════════════════════════════╗
║          DARKNOVA AI BOT - PRODUCTION READY v3.0            ║
║               Built by @MrNewton_2                          ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, re, time, asyncio, logging, aiohttp, secrets, string, zipfile, io
import aiohttp.web
from datetime import datetime, timedelta
from functools import wraps
from logging.handlers import RotatingFileHandler

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, Bot
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

# ══════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════
logger = logging.getLogger("DarkNovaBot")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
fh = RotatingFileHandler("bot.log", maxBytes=5_000_000, backupCount=3)
fh.setFormatter(fmt)
sh = logging.StreamHandler()
sh.setFormatter(fmt)
logger.addHandler(fh)
logger.addHandler(sh)

# ══════════════════════════════════════════════
# ENV VARIABLES
# ══════════════════════════════════════════════
ADMIN_BOT_TOKEN = os.environ.get("ADMIN_BOT_TOKEN", "")
USER_BOT_TOKEN  = os.environ.get("USER_BOT_TOKEN", "")
ADMIN_ID        = int(os.environ.get("ADMIN_ID", "0"))
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
PORT            = int(os.environ.get("PORT", "8080"))

DATA_FILE  = "bot_data.json"
data_lock  = asyncio.Lock()

# Global Bot object for sending messages (broadcast etc.)
user_bot_instance: Bot = None

# ══════════════════════════════════════════════
# AI PERSONALITIES
# ══════════════════════════════════════════════
PERSONAS: dict = {
    "default": (
        "You are DarkNova — a smart, witty, multilingual AI assistant. "
        "You speak in casual Hindi-English (Hinglish) mix when user uses Hindi. "
        "You are helpful, direct, confident. Answer everything clearly. "
        "For code always use ``` blocks with language name. "
        "Never be unnecessarily rude, but always be real and honest. "
        "Created by @MrNewton_2."
    ),
    "teacher": (
        "You are DarkNova Teacher. Explain step by step, use simple analogies, "
        "give examples, make sure user truly understands. Patient and encouraging. "
        "Adapt language to user's level. For code always use ``` blocks."
    ),
    "hacker": (
        "You are DarkNova Hacker — skilled ethical security researcher and developer. "
        "You know systems, networks, Linux, Python, CTFs, bug bounties, defense. "
        "Speak with tech slang, precise and efficient. Always use ``` for code/commands."
    ),
    "philosopher": (
        "You are DarkNova Philosopher. See deeper meaning in everything. "
        "Ask profound questions, give multiple perspectives. Speak beautifully and thoughtfully."
    ),
    "comedian": (
        "You are DarkNova Comedian. Everything gets a witty twist. "
        "Puns, dry humor, sarcasm (lightly), clever observations. Still helpful but fun. "
        "Hinglish jokes welcome!"
    ),
    "poet": (
        "You are DarkNova Poet. Respond with beautiful language, metaphors, rhythm, imagery. "
        "Write poems in English, Hindi, or Hinglish. Everything feels artistic."
    ),
    "lawyer": (
        "You are DarkNova Lawyer. Precise, logical, thorough. Break down arguments, "
        "identify loopholes, explain legal concepts clearly. "
        "Always note: 'This is educational, not legal advice.' Sharp and analytical."
    ),
    "doctor": (
        "You are DarkNova Doctor. Clear health information, explain symptoms, conditions, "
        "treatments in plain language. Always remind users to consult a real doctor. "
        "Calm, caring, thorough."
    ),
    "therapist": (
        "You are DarkNova Therapist. Listen with empathy, validate feelings, ask thoughtful "
        "questions, gently guide. Warm, patient, non-judgmental. "
        "Encourage professional help when needed."
    ),
    "tutor": (
        "You are DarkNova Coding Tutor. Teach programming, debug code, explain algorithms, "
        "help with projects. Write clean commented code. Celebrate small wins. "
        "Python, JS, C++, Java, Rust, Go and more."
    ),
    "storyteller": (
        "You are DarkNova Storyteller. Craft engaging narratives, vivid characters, "
        "interesting plots. Continue stories, write dialogues, build entire worlds. "
        "Make every story immersive."
    ),
    "fitness": (
        "You are DarkNova Fitness Coach. Create workout plans, explain exercises with proper "
        "form, give nutrition advice, motivate users. Tailor advice to level and goals. "
        "Always recommend warming up and recovery."
    ),
    "chef": (
        "You are DarkNova Chef. Know recipes from every cuisine, cooking techniques, "
        "ingredient substitutions, meal planning. Make cooking fun for everyone."
    ),
    "interviewer": (
        "You are DarkNova Interview Coach. Help users prepare for technical and HR interviews, "
        "practice answers, review resumes, build confidence. Simulate mock interviews, "
        "give sharp feedback."
    ),
    "translator": (
        "You are DarkNova Translator. Translate accurately between languages, explain idioms "
        "and cultural context, help learn new languages. Support: Hindi, English, Spanish, "
        "French, German, Japanese, Arabic, and more."
    ),
}

# ══════════════════════════════════════════════
# DEFAULT DATA
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
        "system_prompt": "",
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

bot_data: dict = {}

# ══════════════════════════════════════════════
# DATA MANAGEMENT
# ══════════════════════════════════════════════
def load_data() -> dict:
    global bot_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            merged = DEFAULT_DATA.copy()
            for k, v in loaded.items():
                if isinstance(v, dict) and isinstance(merged.get(k), dict):
                    merged[k] = {**merged[k], **v}
                else:
                    merged[k] = v
            bot_data = merged
            logger.info("Data loaded.")
        except Exception as e:
            logger.error(f"Load error: {e}")
            bot_data = DEFAULT_DATA.copy()
    else:
        bot_data = DEFAULT_DATA.copy()
    # Set default system prompt if empty
    if not bot_data["cfg"].get("system_prompt"):
        bot_data["cfg"]["system_prompt"] = PERSONAS["default"]
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

# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════
def get_user(uid: int) -> dict:
    key = str(uid)
    if key not in bot_data["users"]:
        bot_data["users"][key] = {
            "id": uid, "name": "Unknown", "username": None,
            "messages": 0, "warnings": 0,
            "joined": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
        }
    return bot_data["users"][key]


def is_banned(uid: int) -> bool:
    return int(uid) in [int(x) for x in bot_data.get("banned", [])]


def is_muted(uid: int) -> bool:
    key = str(uid)
    muted = bot_data.get("muted", {})
    if key not in muted:
        return False
    until = muted[key].get("until")
    if until and datetime.fromisoformat(until) < datetime.now():
        del bot_data["muted"][key]
        return False
    return True


def is_premium(uid: int) -> bool:
    key = str(uid)
    prem = bot_data.get("premium", {})
    if key not in prem:
        return False
    expiry = prem[key].get("expiry")
    if expiry == "permanent":
        return True
    if expiry and datetime.fromisoformat(expiry) < datetime.now():
        del bot_data["premium"][key]
        return False
    return True


def get_daily_count(uid: int) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    key = str(uid)
    dc = bot_data.setdefault("daily_counts", {})
    if key not in dc or dc[key].get("date") != today:
        dc[key] = {"date": today, "count": 0}
    return dc[key]["count"]


def increment_daily(uid: int):
    today = datetime.now().strftime("%Y-%m-%d")
    key = str(uid)
    dc = bot_data.setdefault("daily_counts", {})
    if key not in dc or dc[key].get("date") != today:
        dc[key] = {"date": today, "count": 0}
    dc[key]["count"] += 1


def get_limit(uid: int) -> int:
    return bot_data["limits"]["prem"] if is_premium(uid) else bot_data["limits"]["free"]


def split_msg(text: str, max_len: int = 4000) -> list:
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


def extract_code_blocks(text: str):
    pattern = r"```(\w*)\n?([\s\S]*?)```"
    blocks = re.findall(pattern, text)
    clean = re.sub(pattern, "\n[CODE BLOCK]\n", text)
    return blocks, clean


def has_code(text: str) -> bool:
    return "```" in text


def detect_filename(lang, index, ai_text, code):
    """Smart filename detection from AI response"""
    lang = (lang or "txt").lower()
    ext_map = {
        "python":"py","py":"py","javascript":"js","js":"js",
        "typescript":"ts","ts":"ts","html":"html","css":"css",
        "json":"json","sql":"sql","bash":"sh","shell":"sh","sh":"sh",
        "java":"java","cpp":"cpp","c":"c","php":"php","ruby":"rb",
        "go":"go","rust":"rs","kotlin":"kt","swift":"swift",
        "yaml":"yaml","yml":"yml","markdown":"md","md":"md",
        "xml":"xml","txt":"txt",
    }
    ext = ext_map.get(lang, lang if lang else "txt")
    for pat in [
        r'`([\w\-./]+\.' + ext + r')`',
        r'\*\*([\w\-./]+\.' + ext + r')\*\*',
        r'(?:file|named?|called?)[:\s]+`?([\w\-./]+\.' + ext + r')`?',
    ]:
        m = re.search(pat, ai_text, re.IGNORECASE)
        if m:
            return m.group(1)
    defaults = {
        "html": ["index.html","about.html","contact.html","shop.html","product.html"],
        "css":  ["style.css","styles.css","main.css","shop.css"],
        "js":   ["script.js","main.js","app.js","cart.js"],
        "py":   ["main.py","app.py","server.py","bot.py"],
        "json": ["package.json","data.json","config.json"],
        "sh":   ["setup.sh","install.sh","run.sh"],
        "sql":  ["database.sql","schema.sql"],
        "md":   ["README.md","DOCS.md"],
    }
    names = defaults.get(ext, [])
    if index < len(names):
        return names[index]
    return f"file_{index+1}.{ext}"


def should_make_zip(code_blocks):
    """Return True if response should be sent as ZIP"""
    if len(code_blocks) >= 2:
        return True
    if len(code_blocks) == 1 and code_blocks[0][1].count("\n") > 50:
        return True
    return False


def make_project_zip(files):
    """Build ZIP from dict of {filename: content}"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, fcontent in files.items():
            zf.writestr(fname, fcontent)
    buf.seek(0)
    return buf



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
    af = bot_data.get("antiflood", {})
    if not af.get("on", False):
        return False
    key = str(uid)
    now = time.time()
    flood = bot_data.setdefault("flood", {})
    flood.setdefault(key, [])
    flood[key] = [t for t in flood[key] if now - t < af.get("win", 10)]
    flood[key].append(now)
    return len(flood[key]) > af.get("max", 8)


def apply_flood_mute(uid: int):
    af = bot_data.get("antiflood", {})
    mins = af.get("mute", 5)
    until = (datetime.now() + timedelta(minutes=mins)).isoformat()
    bot_data["muted"][str(uid)] = {"until": until, "reason": "antiflood"}

# ══════════════════════════════════════════════
# GROQ AI
# ══════════════════════════════════════════════
async def call_groq(uid: int, user_message: str) -> tuple:
    cfg = bot_data.get("cfg", {})
    system_prompt = cfg.get("system_prompt") or PERSONAS["default"]
    model       = cfg.get("model", "llama-3.1-8b-instant")
    temperature = float(cfg.get("temperature", 0.9))
    max_tokens  = int(cfg.get("max_tokens", 4096))

    messages = [{"role": "system", "content": system_prompt}]

    if is_premium(uid):
        history = bot_data.get("convos", {}).get(str(uid), [])
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
            async with session.post(url, headers=headers, json=payload,
                                    timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    logger.error(f"Groq {resp.status}: {err}")
                    bot_data["stats"]["groq_errors"] += 1
                    return "⚠️ AI error. Try again.", 0
                data = await resp.json()

        reply  = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        bot_data["stats"]["total_tokens"] = bot_data["stats"].get("total_tokens", 0) + tokens

        if is_premium(uid):
            key = str(uid)
            convos = bot_data.setdefault("convos", {})
            convos.setdefault(key, [])
            ts = datetime.now().isoformat()
            convos[key].append({"role": "user",      "content": user_message, "ts": ts})
            convos[key].append({"role": "assistant", "content": reply,        "ts": ts})
            convos[key] = convos[key][-40:]

        key = str(uid)
        chats = bot_data.setdefault("chats", {})
        chats.setdefault(key, [])
        chats[key].append({
            "ts": datetime.now().isoformat(),
            "user": user_message[:500],
            "ai": reply[:500],
        })
        chats[key] = chats[key][-200:]

        return reply, tokens

    except asyncio.TimeoutError:
        bot_data["stats"]["groq_errors"] = bot_data["stats"].get("groq_errors", 0) + 1
        return "⏱️ Timeout. Try again.", 0
    except Exception as e:
        bot_data["stats"]["groq_errors"] = bot_data["stats"].get("groq_errors", 0) + 1
        logger.error(f"Groq exception: {e}")
        return f"❌ Error: {str(e)[:100]}", 0

# ══════════════════════════════════════════════
# FORCE SUBSCRIBE
# ══════════════════════════════════════════════
async def check_force_sub(uid: int, bot: Bot) -> bool:
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
# BROADCAST HELPER — uses global Bot instance
# ══════════════════════════════════════════════
async def send_to_all(message: str, tag: str = "📢 Broadcast") -> tuple:
    global user_bot_instance
    users = bot_data.get("users", {})
    sent = failed = 0
    for uid_str in list(users.keys()):
        try:
            await user_bot_instance.send_message(
                int(uid_str),
                f"{tag}\n\n{message}",
                parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Send to {uid_str} failed: {e}")
            failed += 1
    return sent, failed

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
# ADMIN MENUS
# ══════════════════════════════════════════════
def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard",    callback_data="a_dash"),
         InlineKeyboardButton("📈 Stats",        callback_data="a_stats")],
        [InlineKeyboardButton("👥 Users",        callback_data="a_users"),
         InlineKeyboardButton("🟢 Live Chats",   callback_data="a_live")],
        [InlineKeyboardButton("🤖 AI Settings",  callback_data="a_ai"),
         InlineKeyboardButton("📢 Broadcast",    callback_data="a_bcast_info")],
        [InlineKeyboardButton("🚫 Ban/Unban",    callback_data="a_ban_info"),
         InlineKeyboardButton("🔇 Mute/Unmute",  callback_data="a_mute_info")],
        [InlineKeyboardButton("💎 Premium",      callback_data="a_prem_info"),
         InlineKeyboardButton("🎫 Codes",        callback_data="a_codes_info")],
        [InlineKeyboardButton("🔒 Force Sub",    callback_data="a_fsub_info"),
         InlineKeyboardButton("🛡 Antiflood",    callback_data="a_flood_info")],
        [InlineKeyboardButton("💬 View Chat",    callback_data="a_vchat_info"),
         InlineKeyboardButton("🧹 Clear Memory", callback_data="a_mem_info")],
        [InlineKeyboardButton("🔧 Maintenance",  callback_data="a_maint"),
         InlineKeyboardButton("🔄 Restart Bot",  callback_data="a_restart")],
        [InlineKeyboardButton("📋 Export Users", callback_data="a_export"),
         InlineKeyboardButton("⚡ Ping",         callback_data="a_ping")],
        [InlineKeyboardButton("📢 Advertise",    callback_data="a_ad_info"),
         InlineKeyboardButton("📊 Daily Report", callback_data="a_daily")],
        [InlineKeyboardButton("⚙️ System Prompt",callback_data="a_sysprompt"),
         InlineKeyboardButton("🗑 Clear Logs",   callback_data="a_clrlogs")],
        [InlineKeyboardButton("❌ Close Panel",   callback_data="a_close")],
    ])


def get_ai_menu() -> InlineKeyboardMarkup:
    cfg = bot_data.get("cfg", {})
    temp = cfg.get("temperature", 0.9)
    mtok = cfg.get("max_tokens", 4096)
    pers = cfg.get("personality", "default")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Set System Prompt", callback_data="ai_setprompt")],
        [InlineKeyboardButton("👁 View Current Prompt",callback_data="ai_viewprompt")],
        [InlineKeyboardButton("🎭 Personalities",     callback_data="ai_pers"),
         InlineKeyboardButton(f"🤖 {pers}",           callback_data="ai_active")],
        [InlineKeyboardButton(f"🌡 Temp: {temp}",     callback_data="ai_temp"),
         InlineKeyboardButton(f"📏 Tokens: {mtok}",   callback_data="ai_tokens")],
        [InlineKeyboardButton("🔄 Reset Defaults",    callback_data="ai_reset")],
        [InlineKeyboardButton("⬅️ Back",              callback_data="a_main")],
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


def get_temp_menu() -> InlineKeyboardMarkup:
    temps   = [0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.8, 2.0]
    current = float(bot_data.get("cfg", {}).get("temperature", 0.9))
    buttons, row = [], []
    for t in temps:
        label = f"✅{t}" if t == current else str(t)
        row.append(InlineKeyboardButton(label, callback_data=f"temp_{t}"))
        if len(row) == 3:
            buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="a_ai")])
    return InlineKeyboardMarkup(buttons)


def get_tokens_menu() -> InlineKeyboardMarkup:
    opts    = [512, 1024, 2048, 4096, 8192, 16384, 32768]
    current = int(bot_data.get("cfg", {}).get("max_tokens", 4096))
    buttons, row = [], []
    for t in opts:
        label = f"✅{t}" if t == current else str(t)
        row.append(InlineKeyboardButton(label, callback_data=f"tok_{t}"))
        if len(row) == 3:
            buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="a_ai")])
    return InlineKeyboardMarkup(buttons)

# ══════════════════════════════════════════════
# ADMIN START
# ══════════════════════════════════════════════
@admin_only
async def admin_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "╔══════════════════════════╗\n"
        "║   🤖 DarkNova Admin     ║\n"
        "║   Control Panel v3.0    ║\n"
        "╚══════════════════════════╝\n\n"
        f"👤 Admin: {update.effective_user.first_name}\n"
        f"⏱ Uptime: {uptime_str()}\n"
        f"👥 Users: {len(bot_data.get('users', {}))}\n\n"
        "Select an option:"
    )
    await update.message.reply_text(text, reply_markup=get_main_menu())

# ══════════════════════════════════════════════
# ADMIN CALLBACK — ALL BUTTONS
# ══════════════════════════════════════════════
@admin_only
async def admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data
    await q.answer()

    # ── NAVIGATION ────────────────────────────
    if data == "a_main":
        await q.edit_message_text("🏠 Main Menu", reply_markup=get_main_menu())
        return

    if data == "a_close":
        await q.edit_message_text("✅ Panel closed. Send /start to reopen.")
        return

    # ── DASHBOARD ─────────────────────────────
    if data == "a_dash":
        reset_daily_stats()
        users = bot_data.get("users", {})
        now   = datetime.now()
        active_24h  = sum(
            1 for u in users.values()
            if (now - datetime.fromisoformat(u.get("last_active", now.isoformat()))).total_seconds() < 86400
        )
        prem_count  = sum(1 for uid in users if is_premium(int(uid)))
        banned_cnt  = len(bot_data.get("banned", []))
        muted_cnt   = len(bot_data.get("muted", {}))
        cfg         = bot_data.get("cfg", {})
        stats       = bot_data.get("stats", {})
        text = (
            "📊 *DASHBOARD*\n━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Total Users: `{len(users)}`\n"
            f"🟢 Active 24h: `{active_24h}`\n"
            f"💎 Premium: `{prem_count}`\n"
            f"🚫 Banned: `{banned_cnt}`\n"
            f"🔇 Muted: `{muted_cnt}`\n\n"
            f"💬 Total Msgs: `{stats.get('total_messages',0)}`\n"
            f"📅 Today Msgs: `{stats.get('today_messages',0)}`\n\n"
            f"🤖 Model: `{cfg.get('model','N/A')}`\n"
            f"🎭 Persona: `{cfg.get('personality','default')}`\n"
            f"🌡 Temp: `{cfg.get('temperature',0.9)}`\n"
            f"📏 Max Tokens: `{cfg.get('max_tokens',4096)}`\n\n"
            f"🔧 Maintenance: `{'ON' if bot_data.get('maint') else 'OFF'}`\n"
            f"🔒 Force Sub: `{bot_data.get('force_sub') or 'OFF'}`\n"
            f"🛡 Antiflood: `{'ON' if bot_data.get('antiflood',{}).get('on') else 'OFF'}`\n\n"
            f"🪙 Tokens Used: `{stats.get('total_tokens',0)}`\n"
            f"⏱ Uptime: `{uptime_str()}`"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── STATS ─────────────────────────────────
    if data == "a_stats":
        stats = bot_data.get("stats", {})
        text  = (
            "📈 *STATS*\n━━━━━━━━━━━━━━━━━━━\n"
            "*All Time:*\n"
            f"  💬 Messages: `{stats.get('total_messages',0)}`\n"
            f"  📢 Broadcasts: `{stats.get('total_broadcasts',0)}`\n"
            f"  🚫 Bans: `{stats.get('total_bans',0)}`\n"
            f"  🔇 Mutes: `{stats.get('total_mutes',0)}`\n"
            f"  🪙 Tokens: `{stats.get('total_tokens',0)}`\n\n"
            "*Today:*\n"
            f"  💬 Messages: `{stats.get('today_messages',0)}`\n\n"
            "*API:*\n"
            f"  ✅ Groq Calls: `{stats.get('groq_calls',0)}`\n"
            f"  ❌ Groq Errors: `{stats.get('groq_errors',0)}`\n\n"
            f"⏱ Uptime: `{uptime_str()}`"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── USERS LIST ────────────────────────────
    if data == "a_users":
        users = bot_data.get("users", {})
        if not users:
            text = "👥 No users yet."
        else:
            lines = [f"👥 *USERS* ({len(users)} total)\n━━━━━━━━━━━━━━━━━━━"]
            for uid, u in list(users.items())[:25]:
                tags = ""
                if is_premium(int(uid)): tags += "💎"
                if is_banned(int(uid)):  tags += "🚫"
                if is_muted(int(uid)):   tags += "🔇"
                w = u.get("warnings", 0)
                if w: tags += f"⚠️{w}"
                uname = f"@{u['username']}" if u.get("username") else "—"
                lines.append(f"`{uid}` {tags} {u.get('name','?')} {uname} — {u.get('messages',0)}msgs")
            if len(users) > 25:
                lines.append(f"\n...+{len(users)-25} more. Use /export users")
            text = "\n".join(lines)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text[:4000], reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── LIVE CHATS ────────────────────────────
    if data == "a_live":
        users = bot_data.get("users", {})
        chats = bot_data.get("chats", {})
        now   = datetime.now()
        lines = ["🟢 *LIVE (last 30 min)*\n━━━━━━━━━━━━━━━━━━━"]
        count = 0
        for uid, u in users.items():
            last = u.get("last_active", "")
            if not last: continue
            try:
                delta = (now - datetime.fromisoformat(last)).total_seconds()
                if delta < 1800:
                    last_msg = ""
                    if uid in chats and chats[uid]:
                        last_msg = chats[uid][-1].get("user", "")[:60]
                    lines.append(
                        f"`{uid}` {u.get('name','?')}\n"
                        f"  📝 {last_msg or 'N/A'}\n"
                        f"  ⏰ {int(delta//60)}m ago"
                    )
                    count += 1
            except Exception:
                pass
        if count == 0:
            lines.append("No active users in last 30 min.")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text("\n".join(lines)[:4000], reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── AI MENU ───────────────────────────────
    if data == "a_ai":
        await q.edit_message_text("🤖 *AI Settings*", reply_markup=get_ai_menu(), parse_mode=ParseMode.MARKDOWN)
        return

    if data == "ai_viewprompt":
        prompt = bot_data.get("cfg", {}).get("system_prompt", "Not set")
        text   = f"📝 *Current System Prompt:*\n\n`{prompt[:3500]}`"
        kb     = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_ai")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    if data == "ai_setprompt":
        ctx.user_data["awaiting"] = "set_prompt"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="a_ai")]])
        await q.edit_message_text(
            "📝 *Set System Prompt*\n\nSend your new system prompt as a message now:\n\n"
            "_Tip: This will override all personality presets. "
            "To go back to a preset, use 🎭 Personalities._",
            reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "ai_pers":
        await q.edit_message_text(
            "🎭 *Select Personality*\n✅ = currently active:",
            reply_markup=get_personality_menu(), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "ai_temp":
        await q.edit_message_text(
            "🌡 *Select Temperature*\n✅ = current:",
            reply_markup=get_temp_menu(), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "ai_tokens":
        await q.edit_message_text(
            "📏 *Select Max Tokens*\n✅ = current:",
            reply_markup=get_tokens_menu(), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "ai_active":
        pers   = bot_data.get("cfg", {}).get("personality", "default")
        prompt = PERSONAS.get(pers, "Custom prompt")
        await q.answer(f"Active: {pers}", show_alert=True)
        return

    if data == "ai_reset":
        bot_data["cfg"]["temperature"]   = 0.9
        bot_data["cfg"]["max_tokens"]    = 4096
        bot_data["cfg"]["personality"]   = "default"
        bot_data["cfg"]["system_prompt"] = PERSONAS["default"]
        await save_data()
        await q.answer("✅ Reset to defaults!", show_alert=True)
        await q.edit_message_text("🤖 *AI Settings* (reset done)", reply_markup=get_ai_menu(), parse_mode=ParseMode.MARKDOWN)
        return

    if data.startswith("pers_"):
        name = data[5:]
        if name in PERSONAS:
            bot_data["cfg"]["personality"]   = name
            bot_data["cfg"]["system_prompt"] = PERSONAS[name]
            await save_data()
            await q.answer(f"✅ Set to: {name}", show_alert=True)
            await q.edit_message_text(
                "🎭 *Personalities* (updated):",
                reply_markup=get_personality_menu(), parse_mode=ParseMode.MARKDOWN
            )
        return

    if data.startswith("temp_"):
        val = float(data[5:])
        bot_data["cfg"]["temperature"] = val
        await save_data()
        await q.answer(f"✅ Temperature → {val}", show_alert=True)
        await q.edit_message_text("🌡 *Temperature* (updated):", reply_markup=get_temp_menu(), parse_mode=ParseMode.MARKDOWN)
        return

    if data.startswith("tok_"):
        val = int(data[4:])
        bot_data["cfg"]["max_tokens"] = val
        await save_data()
        await q.answer(f"✅ Max Tokens → {val}", show_alert=True)
        await q.edit_message_text("📏 *Max Tokens* (updated):", reply_markup=get_tokens_menu(), parse_mode=ParseMode.MARKDOWN)
        return

    # ── BROADCAST INFO ────────────────────────
    if data == "a_bcast_info":
        bs   = bot_data.get("broadcast_stats", {})
        text = (
            "📢 *BROADCAST*\n━━━━━━━━━━━━━━━━━━━\n"
            f"Last result: ✅`{bs.get('sent',0)}` sent | ❌`{bs.get('failed',0)}` failed\n\n"
            "Command: `/broadcast your message`\n"
            "Sends to ALL users via User Bot."
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── BAN INFO ──────────────────────────────
    if data == "a_ban_info":
        banned = bot_data.get("banned", [])
        text   = (
            f"🚫 *BAN SYSTEM*\n━━━━━━━━━━━━━━━━━━━\n"
            f"Currently banned: `{len(banned)}`\n\n"
            "Commands:\n"
            "`/ban <user_id>` — Ban user\n"
            "`/unban <user_id>` — Unban user\n"
            "`/warn <user_id>` — Warn (3 = auto ban)"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── MUTE INFO ─────────────────────────────
    if data == "a_mute_info":
        muted = bot_data.get("muted", {})
        lines = [f"🔇 *MUTE SYSTEM*\n━━━━━━━━━━━━━━━━━━━\nCurrently muted: `{len(muted)}`\n"]
        for uid, info in list(muted.items())[:10]:
            until = info.get("until", "")[:16]
            u = bot_data.get("users", {}).get(uid, {})
            lines.append(f"`{uid}` {u.get('name','?')} until `{until}`")
        lines.append("\nCommands:\n`/mute <id> <mins>` — Mute\n`/unmute <id>` — Unmute")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text("\n".join(lines), reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── PREMIUM INFO ──────────────────────────
    if data == "a_prem_info":
        prem   = bot_data.get("premium", {})
        limits = bot_data.get("limits", {})
        lines  = [
            f"💎 *PREMIUM*\n━━━━━━━━━━━━━━━━━━━\n"
            f"Active: `{len(prem)}`\n"
            f"Free limit: `{limits.get('free',20)}/day`\n"
            f"Prem limit: `{limits.get('prem',99999)}/day`\n"
        ]
        for uid, info in list(prem.items())[:10]:
            u = bot_data.get("users", {}).get(uid, {})
            exp = info.get("expiry", "?")
            lines.append(f"💎 `{uid}` {u.get('name','?')} — {exp[:10] if exp != 'permanent' else '♾️'}")
        lines.append("\nCommands:\n`/premium <id> <days>` (0=perm)\n`/removepremium <id>`\n`/setlimit free|prem <n>`")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text("\n".join(lines), reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── CODES INFO ────────────────────────────
    if data == "a_codes_info":
        codes  = bot_data.get("codes", {})
        active = [c for c, v in codes.items() if not v.get("used")]
        lines  = [
            f"🎫 *REDEEM CODES*\n━━━━━━━━━━━━━━━━━━━\n"
            f"Total: `{len(codes)}` | Active: `{len(active)}`\n"
        ]
        for c in active[:12]:
            lines.append(f"`{c}` — {codes[c].get('days','?')}d")
        if len(active) > 12:
            lines.append(f"...+{len(active)-12} more")
        lines.append("\nCommands:\n`/gencode <days> <amount>`\n`/deletecode <code>`\n`/redeeminfo`")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text("\n".join(lines)[:4000], reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── FORCE SUB ─────────────────────────────
    if data == "a_fsub_info":
        fs   = bot_data.get("force_sub")
        text = (
            f"🔒 *FORCE SUBSCRIBE*\n━━━━━━━━━━━━━━━━━━━\n"
            f"Status: `{'ON — ' + fs if fs else 'OFF'}`\n\n"
            "Commands:\n`/forcesub @channel` — Enable\n`/forcesub off` — Disable"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── ANTIFLOOD ─────────────────────────────
    if data == "a_flood_info":
        af   = bot_data.get("antiflood", {})
        text = (
            f"🛡 *ANTIFLOOD*\n━━━━━━━━━━━━━━━━━━━\n"
            f"Status: `{'ON' if af.get('on') else 'OFF'}`\n"
            f"Limit: `{af.get('max',8)} msgs` in `{af.get('win',10)}s`\n"
            f"Auto-mute: `{af.get('mute',5)} minutes`\n\n"
            "Commands:\n`/antiflood on` / `off`\n"
            "`/antiflood set <max> <secs> <mute_mins>`"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── VIEW CHAT INFO ────────────────────────
    if data == "a_vchat_info":
        text = (
            "💬 *VIEW CHAT HISTORY*\n━━━━━━━━━━━━━━━━━━━\n\n"
            "Command: `/viewchat <user_id>`\n"
            "Shows last 15 messages of any user."
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── MEMORY INFO ───────────────────────────
    if data == "a_mem_info":
        text = (
            "🧹 *CLEAR MEMORY*\n━━━━━━━━━━━━━━━━━━━\n\n"
            "`/clearmem <user_id>` — Clear one user\n"
            "`/clearmemall` — Clear ALL memories\n"
            "`/clearchats` — Clear all chat logs"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── MAINTENANCE TOGGLE ────────────────────
    if data == "a_maint":
        bot_data["maint"] = not bot_data.get("maint", False)
        status = "ON 🔧" if bot_data["maint"] else "OFF ✅"
        await save_data()
        await q.answer(f"Maintenance {status}", show_alert=True)
        await q.edit_message_text("🏠 Main Menu", reply_markup=get_main_menu())
        return

    # ── RESTART ───────────────────────────────
    if data == "a_restart":
        bot_data["convos"] = {}
        bot_data["flood"]  = {}
        bot_data["stats"]["groq_calls"] = 0
        await save_data()
        await q.answer("✅ Memory cleared & restarted!", show_alert=True)
        await q.edit_message_text("🏠 Main Menu", reply_markup=get_main_menu())
        return

    # ── EXPORT ────────────────────────────────
    if data == "a_export":
        users = bot_data.get("users", {})
        lines = [f"📋 *USER EXPORT* ({len(users)} users)\n━━━━━━━━━━━━━━━━━━━"]
        for uid, u in users.items():
            plan   = "💎" if is_premium(int(uid)) else "🆓"
            status = "🚫" if is_banned(int(uid)) else ("🔇" if is_muted(int(uid)) else "✅")
            lines.append(
                f"{status}{plan} `{uid}` {u.get('name','?')} "
                f"@{u.get('username','—')} {u.get('messages',0)}msgs ⚠️{u.get('warnings',0)}"
            )
        text = "\n".join(lines)
        kb   = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        for chunk in split_msg(text):
            await q.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        await q.edit_message_text("📋 Export sent above ⬆️", reply_markup=kb)
        return

    # ── PING ──────────────────────────────────
    if data == "a_ping":
        t  = time.time()
        await q.answer("🏓 Pong!")
        ms = int((time.time() - t) * 1000)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(
            f"⚡ *Ping*\n\nResponse: `{ms}ms`\nUptime: `{uptime_str()}`",
            reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── ADVERTISE INFO ────────────────────────
    if data == "a_ad_info":
        ad   = bot_data.get("ad_stats", {})
        text = (
            f"📢 *ADVERTISE*\n━━━━━━━━━━━━━━━━━━━\n"
            f"Total sent: `{ad.get('sent',0)}`\n"
            f"Total failed: `{ad.get('failed',0)}`\n\n"
            "Command: `/advertise your ad text`"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── DAILY REPORT ─────────────────────────
    if data == "a_daily":
        reset_daily_stats()
        stats = bot_data.get("stats", {})
        users = bot_data.get("users", {})
        today = datetime.now().strftime("%Y-%m-%d")
        new_today = sum(1 for u in users.values() if u.get("joined","")[:10] == today)
        text  = (
            f"📊 *DAILY REPORT — {today}*\n━━━━━━━━━━━━━━━━━━━\n"
            f"💬 Messages today: `{stats.get('today_messages',0)}`\n"
            f"👤 New users today: `{new_today}`\n"
            f"🪙 Tokens used: `{stats.get('total_tokens',0)}`\n"
            f"✅ API calls: `{stats.get('groq_calls',0)}`\n"
            f"❌ API errors: `{stats.get('groq_errors',0)}`\n"
            f"⏱ Uptime: `{uptime_str()}`"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    # ── SYSTEM PROMPT MANAGER ─────────────────
    if data == "a_sysprompt":
        cfg    = bot_data.get("cfg", {})
        prompt = cfg.get("system_prompt", "")
        pers   = cfg.get("personality", "default")
        prev   = prompt[:250] + ("..." if len(prompt) > 250 else "")
        text   = (
            "⚙️ *SYSTEM PROMPT MANAGER*\n━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎭 Active Persona: `{pers}`\n"
            f"📏 Length: `{len(prompt)} chars`\n\n"
            f"📝 Preview:\n`{prev}`"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👁 View Full Prompt",   callback_data="ai_viewprompt")],
            [InlineKeyboardButton("✏️ Set Custom Prompt",  callback_data="ai_setprompt")],
            [InlineKeyboardButton("🎭 Personality Presets",callback_data="ai_pers")],
            [InlineKeyboardButton("🔄 Reset to Default",   callback_data="ai_reset")],
            [InlineKeyboardButton("💬 Set Welcome Msg",    callback_data="a_setwelcome"),
             InlineKeyboardButton("🔧 Maint Message",      callback_data="a_setmaintmsg")],
            [InlineKeyboardButton("⬅️ Back",               callback_data="a_main")],
        ])
        await q.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        return

    if data == "a_setwelcome":
        ctx.user_data["awaiting"] = "set_welcome"
        current = bot_data.get("welcome", "")[:200]
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="a_sysprompt")]])
        await q.edit_message_text(
            "💬 *Set Welcome Message*\n\n"
            "Variables: `{name}` `{plan}` `{daily}` `{limit}`\n\n"
            f"Current:\n`{current}`\n\n"
            "Send new welcome message now:",
            reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "a_setmaintmsg":
        ctx.user_data["awaiting"] = "set_maint_msg"
        current = bot_data.get("maintenance_msg", "")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="a_sysprompt")]])
        await q.edit_message_text(
            f"🔧 *Set Maintenance Message*\n\n"
            f"Current:\n`{current}`\n\n"
            "Send new maintenance message:",
            reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── CLEAR LOGS ────────────────────────────
    if data == "a_clrlogs":
        bot_data["chats"] = {}
        await save_data()
        await q.answer("✅ All chat logs cleared!", show_alert=True)
        await q.edit_message_text("🏠 Main Menu", reply_markup=get_main_menu())
        return

# ══════════════════════════════════════════════
# ADMIN TEXT — awaiting states handler
# ══════════════════════════════════════════════
@admin_only
async def cmd_admin_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    awaiting = ctx.user_data.get("awaiting")
    text     = update.message.text.strip()

    if awaiting == "set_prompt":
        bot_data["cfg"]["system_prompt"] = text
        bot_data["cfg"]["personality"]   = "custom"
        ctx.user_data.pop("awaiting", None)
        await save_data()
        await update.message.reply_text(
            f"✅ *System Prompt Updated!*\n\n"
            f"📝 Preview:\n```\n{text[:400]}\n```\n"
            f"📏 Length: {len(text)} chars",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_menu()
        )

    elif awaiting == "set_welcome":
        bot_data["welcome"] = text
        ctx.user_data.pop("awaiting", None)
        await save_data()
        await update.message.reply_text(
            f"✅ *Welcome message updated!*\n\n`{text[:300]}`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu()
        )

    elif awaiting == "set_maint_msg":
        bot_data["maintenance_msg"] = text
        ctx.user_data.pop("awaiting", None)
        await save_data()
        await update.message.reply_text(
            f"✅ *Maintenance message updated!*\n\n`{text[:300]}`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu()
        )

    else:
        await update.message.reply_text("🏠 Use /start to open admin panel.", reply_markup=get_main_menu())

# ══════════════════════════════════════════════
# ADMIN COMMANDS
# ══════════════════════════════════════════════
@admin_only
async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    msg      = " ".join(ctx.args)
    users    = bot_data.get("users", {})
    status   = await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
    sent, failed = await send_to_all(msg, "📢 *Broadcast*")
    bot_data["stats"]["total_broadcasts"] = bot_data["stats"].get("total_broadcasts", 0) + 1
    bot_data["broadcast_stats"] = {"sent": sent, "failed": failed}
    await save_data()
    await status.edit_text(f"✅ Broadcast done!\nSent: `{sent}` | Failed: `{failed}`", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /ban <user_id>"); return
    try: uid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Invalid ID."); return
    if uid not in [int(x) for x in bot_data.get("banned", [])]:
        bot_data["banned"].append(uid)
        bot_data["stats"]["total_bans"] = bot_data["stats"].get("total_bans", 0) + 1
    await save_data()
    await update.message.reply_text(f"🚫 User `{uid}` banned.", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /unban <user_id>"); return
    try: uid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Invalid ID."); return
    bot_data["banned"] = [x for x in bot_data.get("banned", []) if int(x) != uid]
    await save_data()
    await update.message.reply_text(f"✅ User `{uid}` unbanned.", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_warn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /warn <user_id>"); return
    try: uid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Invalid ID."); return
    u = get_user(uid)
    u["warnings"] = u.get("warnings", 0) + 1
    if u["warnings"] >= 3:
        if uid not in [int(x) for x in bot_data.get("banned", [])]:
            bot_data["banned"].append(uid)
        await save_data()
        await update.message.reply_text(f"⚠️ User `{uid}` has {u['warnings']} warnings — *AUTO BANNED!*", parse_mode=ParseMode.MARKDOWN)
    else:
        await save_data()
        await update.message.reply_text(f"⚠️ Warned `{uid}`. Warnings: `{u['warnings']}/3`", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_mute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /mute <user_id> <minutes>"); return
    try: uid, mins = int(ctx.args[0]), int(ctx.args[1])
    except ValueError:
        await update.message.reply_text("Invalid args."); return
    until = (datetime.now() + timedelta(minutes=mins)).isoformat()
    bot_data["muted"][str(uid)] = {"until": until, "reason": "admin"}
    bot_data["stats"]["total_mutes"] = bot_data["stats"].get("total_mutes", 0) + 1
    await save_data()
    await update.message.reply_text(f"🔇 User `{uid}` muted for `{mins}` min.", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_unmute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /unmute <user_id>"); return
    bot_data["muted"].pop(str(ctx.args[0]), None)
    await save_data()
    await update.message.reply_text(f"✅ User `{ctx.args[0]}` unmuted.", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_premium(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /premium <user_id> <days> (0=permanent)"); return
    try: uid, days = int(ctx.args[0]), int(ctx.args[1])
    except ValueError:
        await update.message.reply_text("Invalid args."); return
    expiry = "permanent" if days == 0 else (datetime.now() + timedelta(days=days)).isoformat()
    bot_data["premium"][str(uid)] = {"expiry": expiry, "granted": datetime.now().isoformat()}
    await save_data()
    label = "permanent ♾️" if days == 0 else f"{days} days"
    await update.message.reply_text(f"💎 User `{uid}` granted premium ({label}).", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_removepremium(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /removepremium <user_id>"); return
    bot_data["premium"].pop(str(ctx.args[0]), None)
    await save_data()
    await update.message.reply_text(f"✅ Premium removed from `{ctx.args[0]}`.", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_setlimit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /setlimit <free|prem> <number>"); return
    plan = ctx.args[0].lower()
    try: n = int(ctx.args[1])
    except ValueError:
        await update.message.reply_text("Invalid number."); return
    if plan not in ("free", "prem"):
        await update.message.reply_text("Plan must be 'free' or 'prem'."); return
    bot_data["limits"][plan] = n
    await save_data()
    await update.message.reply_text(f"✅ `{plan}` limit → `{n}/day`", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_gencode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /gencode <days> <amount>"); return
    try: days, amount = int(ctx.args[0]), min(int(ctx.args[1]), 50)
    except ValueError:
        await update.message.reply_text("Invalid args."); return
    alphabet = string.ascii_uppercase + string.digits
    codes    = []
    for _ in range(amount):
        code = "DN-" + "".join(secrets.choice(alphabet) for _ in range(8))
        bot_data["codes"][code] = {"days": days, "used": False, "created": datetime.now().isoformat()}
        codes.append(code)
    await save_data()
    text = f"🎫 Generated `{amount}` code(s) — `{days}` days each:\n\n" + "\n".join(f"`{c}`" for c in codes)
    await update.message.reply_text(text[:4000], parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_deletecode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /deletecode <code>"); return
    code = ctx.args[0].upper()
    if code in bot_data.get("codes", {}):
        del bot_data["codes"][code]
        await save_data()
        await update.message.reply_text(f"✅ Code `{code}` deleted.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Code not found.")


@admin_only
async def cmd_redeeminfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    codes = bot_data.get("codes", {})
    if not codes:
        await update.message.reply_text("No codes yet."); return
    lines = ["🎫 *All Codes:*\n"]
    for c, v in codes.items():
        status = "✅ Used" if v.get("used") else "🟢 Active"
        lines.append(f"`{c}` — {v.get('days','?')}d — {status}")
    for chunk in split_msg("\n".join(lines)):
        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_forcesub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /forcesub @channel OR /forcesub off"); return
    if ctx.args[0].lower() == "off":
        bot_data["force_sub"] = None
        await save_data()
        await update.message.reply_text("✅ Force subscribe disabled.")
    else:
        ch = ctx.args[0] if ctx.args[0].startswith("@") else "@" + ctx.args[0]
        bot_data["force_sub"] = ch
        await save_data()
        await update.message.reply_text(f"✅ Force subscribe → {ch}")


@admin_only
async def cmd_antiflood(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /antiflood on|off|set <max> <win> <mute>"); return
    af  = bot_data.setdefault("antiflood", {})
    sub = ctx.args[0].lower()
    if sub == "on":
        af["on"] = True
        await update.message.reply_text("✅ Antiflood enabled.")
    elif sub == "off":
        af["on"] = False
        await update.message.reply_text("✅ Antiflood disabled.")
    elif sub == "set" and len(ctx.args) >= 4:
        try:
            af["max"] = int(ctx.args[1]); af["win"] = int(ctx.args[2]); af["mute"] = int(ctx.args[3])
            await update.message.reply_text(f"✅ Flood: `{af['max']}` msgs/`{af['win']}`s → mute `{af['mute']}`min", parse_mode=ParseMode.MARKDOWN)
        except ValueError:
            await update.message.reply_text("Invalid values.")
    await save_data()


@admin_only
async def cmd_viewchat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /viewchat <user_id>"); return
    uid   = str(ctx.args[0])
    chats = bot_data.get("chats", {}).get(uid, [])
    if not chats:
        await update.message.reply_text("No chat history for this user."); return
    lines = [f"💬 *Chat Log — {uid}* (last 15)\n━━━━━━━━━━━━━━━━━━━"]
    for c in chats[-15:]:
        lines.append(f"\n⏰ `{c.get('ts','')[:16]}`\n👤 {c.get('user','')[:100]}\n🤖 {c.get('ai','')[:100]}")
    for chunk in split_msg("\n".join(lines)):
        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_clearmem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /clearmem <user_id>"); return
    bot_data["convos"].pop(str(ctx.args[0]), None)
    await save_data()
    await update.message.reply_text(f"✅ Memory cleared for `{ctx.args[0]}`.", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_clearmemall(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_data["convos"] = {}
    await save_data()
    await update.message.reply_text("✅ All memories cleared.")


@admin_only
async def cmd_clearchats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_data["chats"] = {}
    await save_data()
    await update.message.reply_text("✅ All chat logs cleared.")


@admin_only
async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users = bot_data.get("users", {})
    lines = [f"📋 *USER EXPORT* ({len(users)} users)\n━━━━━━━━━━━━━━━━━━━"]
    for uid, u in users.items():
        plan   = "💎" if is_premium(int(uid)) else "🆓"
        status = "🚫" if is_banned(int(uid)) else ("🔇" if is_muted(int(uid)) else "✅")
        lines.append(
            f"{status}{plan} `{uid}` {u.get('name','?')} "
            f"@{u.get('username','—')} {u.get('messages',0)}msgs ⚠️{u.get('warnings',0)}"
        )
    for chunk in split_msg("\n".join(lines)):
        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_sysprompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /sysprompt <new prompt text>"); return
    new_prompt = " ".join(ctx.args)
    bot_data["cfg"]["system_prompt"] = new_prompt
    bot_data["cfg"]["personality"]   = "custom"
    await save_data()
    await update.message.reply_text(
        f"✅ *System prompt updated!*\n\nPreview:\n```\n{new_prompt[:300]}\n```",
        parse_mode=ParseMode.MARKDOWN
    )


@admin_only
async def cmd_advertise(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /advertise <ad text>"); return
    msg    = " ".join(ctx.args)
    status = await update.message.reply_text("📢 Sending ad...")
    sent, failed = await send_to_all(msg, "📢 *Advertisement*")
    bot_data["ad_stats"]["sent"]   = bot_data["ad_stats"].get("sent", 0) + sent
    bot_data["ad_stats"]["failed"] = bot_data["ad_stats"].get("failed", 0) + failed
    await save_data()
    await status.edit_text(f"📢 Ad done! ✅`{sent}` | ❌`{failed}`", parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t   = time.time()
    msg = await update.message.reply_text("🏓 Pong!")
    ms  = int((time.time() - t) * 1000)
    await msg.edit_text(f"⚡ *Ping:* `{ms}ms`\n⏱ Uptime: `{uptime_str()}`", parse_mode=ParseMode.MARKDOWN)

# ══════════════════════════════════════════════
# USER BOT HANDLERS
# ══════════════════════════════════════════════
USER_KB = ReplyKeyboardMarkup(
    [["💬 Chat", "🧹 Reset"], ["ℹ️ About", "📊 Plan"], ["🎫 Redeem", "📞 Contact"]],
    resize_keyboard=True
)


async def user_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid):
        await update.message.reply_text("🚫 You are banned."); return
    if ctx.args:
        await _redeem_code(update, uid, ctx.args[0].upper()); return
    if not await check_force_sub(uid, update.get_bot()):
        await update.message.reply_text("🔒 Join our channel first!", reply_markup=force_sub_keyboard()); return
    u = get_user(uid)
    u["name"] = update.effective_user.first_name or "User"
    u["username"] = update.effective_user.username
    u["last_active"] = datetime.now().isoformat()
    plan    = "💎 Premium" if is_premium(uid) else "🆓 Free"
    daily   = get_daily_count(uid)
    limit   = get_limit(uid)
    welcome = bot_data.get("welcome", DEFAULT_DATA["welcome"])
    text    = welcome.format(name=u["name"], plan=plan, daily=daily,
                              limit=limit if limit < 99999 else "∞")
    await update.message.reply_text(text, reply_markup=USER_KB, parse_mode=ParseMode.MARKDOWN)
    await save_data()


async def user_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id): return
    await update.message.reply_text(
        "🤖 *DarkNova AI — Commands*\n━━━━━━━━━━━━━━━━━━━\n"
        "/start — Welcome\n/help — This list\n/reset — Clear memory\n"
        "/about — About bot\n/plan — Your plan\n/redeem <code> — Activate premium\n"
        "/contact — Admin contact\n/ping — Latency\n/speed — AI speed test\n/model — AI model info\n\n"
        "💬 Just type to chat!",
        parse_mode=ParseMode.MARKDOWN
    )


async def user_about(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg = bot_data.get("cfg", {})
    await update.message.reply_text(
        "🤖 *DarkNova AI Bot*\n━━━━━━━━━━━━━━━━━━━\n"
        "A powerful AI assistant on Groq's lightning-fast API.\n\n"
        f"🧠 Model: `{cfg.get('model','llama-3.1-8b-instant')}`\n"
        f"🎭 Persona: `{cfg.get('personality','default')}`\n"
        "💎 Features: Memory, Code, Multilingual\n\n"
        "👨‍💻 Created by: *@MrNewton_2*\n"
        "🔥 Powered by: Groq AI + Python",
        parse_mode=ParseMode.MARKDOWN
    )


async def user_plan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    plan     = "💎 Premium" if is_premium(uid) else "🆓 Free"
    daily    = get_daily_count(uid)
    limit    = get_limit(uid)
    prem_exp = ""
    if is_premium(uid):
        p      = bot_data.get("premium", {}).get(str(uid), {})
        expiry = p.get("expiry", "?")
        prem_exp = "\n♾️ Permanent" if expiry == "permanent" else f"\n⏳ Expires: `{expiry[:10]}`"
    await update.message.reply_text(
        f"📊 *Your Plan*\n━━━━━━━━━━━━━━━━━━━\n"
        f"Plan: {plan}{prem_exp}\n"
        f"Today: `{daily}/{limit if limit < 99999 else '∞'}`\n"
        f"Memory: `{'40 msgs (48h)' if is_premium(uid) else 'Off — Upgrade!'}`\n\n"
        "🎫 Use `/redeem <code>` to upgrade!",
        parse_mode=ParseMode.MARKDOWN
    )


async def user_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    if not is_premium(uid):
        await update.message.reply_text("⚠️ Memory is a 💎 Premium feature!"); return
    bot_data["convos"].pop(str(uid), None)
    await save_data()
    await update.message.reply_text("🧹 Your memory cleared!")


async def user_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📞 *Contact Admin*\n\n👤 @MrNewton_2\nAdmin ID: `{ADMIN_ID}`",
        parse_mode=ParseMode.MARKDOWN
    )


async def user_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t   = time.time()
    msg = await update.message.reply_text("🏓...")
    ms  = int((time.time() - t) * 1000)
    await msg.edit_text(f"⚡ Pong! `{ms}ms`", parse_mode=ParseMode.MARKDOWN)


async def user_speed(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    msg = await update.message.reply_text("⏱ Testing AI speed...")
    t   = time.time()
    reply, _ = await call_groq(uid, "Say exactly: 'Speed OK'")
    elapsed  = round(time.time() - t, 2)
    await msg.edit_text(f"⚡ AI Response: `{elapsed}s`\n_{reply}_", parse_mode=ParseMode.MARKDOWN)


async def user_model(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg = bot_data.get("cfg", {})
    await update.message.reply_text(
        f"🤖 *AI Model Info*\n\n"
        f"Model: `{cfg.get('model','N/A')}`\n"
        f"Temp: `{cfg.get('temperature',0.9)}`\n"
        f"Max Tokens: `{cfg.get('max_tokens',4096)}`\n"
        f"Persona: `{cfg.get('personality','default')}`",
        parse_mode=ParseMode.MARKDOWN
    )


async def _redeem_code(update: Update, uid: int, code: str):
    codes = bot_data.get("codes", {})
    if code not in codes:
        await update.message.reply_text("❌ Invalid code."); return
    c = codes[code]
    if c.get("used"):
        await update.message.reply_text("❌ Code already used."); return
    days   = c.get("days", 30)
    expiry = "permanent" if days == 0 else (datetime.now() + timedelta(days=days)).isoformat()
    bot_data["premium"][str(uid)] = {"expiry": expiry, "granted": datetime.now().isoformat()}
    codes[code]["used"]    = True
    codes[code]["used_by"] = uid
    await save_data()
    label = "permanent ♾️" if days == 0 else f"{days} days"
    await update.message.reply_text(
        f"✅ *Code redeemed!*\n💎 Premium activated — {label}!",
        parse_mode=ParseMode.MARKDOWN
    )


async def user_redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    if not ctx.args:
        await update.message.reply_text("Usage: /redeem <code>"); return
    await _redeem_code(update, uid, ctx.args[0].upper())


async def user_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data
    await q.answer()

    if data == "cs":
        uid = q.from_user.id
        if await check_force_sub(uid, q.get_bot()):
            await q.edit_message_text("✅ Verified! Send /start")
        else:
            await q.answer("❌ Not joined yet!", show_alert=True)
        return

    if data.startswith("copy_"):
        code_text = data[5:]
        await q.message.reply_text(f"`{code_text}`", parse_mode=ParseMode.MARKDOWN)
        await q.answer("✅ Code sent!")
        return


async def user_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    uid  = update.effective_user.id
    text = update.message.text.strip()

    if is_banned(uid):
        await update.message.reply_text("🚫 You are banned."); return
    if bot_data.get("maint"):
        await update.message.reply_text(bot_data.get("maintenance_msg", "🔧 Maintenance...")); return
    if not await check_force_sub(uid, update.get_bot()):
        await update.message.reply_text("🔒 Join channel first!", reply_markup=force_sub_keyboard()); return
    if is_muted(uid):
        info = bot_data["muted"].get(str(uid), {})
        until = info.get("until", "")
        rem   = ""
        if until:
            try:
                rem = f" ({int((datetime.fromisoformat(until)-datetime.now()).total_seconds()//60)} min left)"
            except Exception: pass
        await update.message.reply_text(f"🔇 You are muted{rem}."); return
    if check_flood(uid):
        apply_flood_mute(uid)
        await update.message.reply_text("🛡 Slow down! You've been muted for flooding."); return

    # Register user
    u             = get_user(uid)
    u["name"]     = update.effective_user.first_name or "User"
    u["username"] = update.effective_user.username
    u["last_active"] = datetime.now().isoformat()

    # Keyboard shortcuts
    shortcuts = {
        "💬 Chat":    lambda: update.message.reply_text("💬 Just type your message!"),
        "🧹 Reset":   lambda: user_reset(update, ctx),
        "ℹ️ About":   lambda: user_about(update, ctx),
        "📊 Plan":    lambda: user_plan(update, ctx),
        "🎫 Redeem":  lambda: update.message.reply_text("Use: /redeem <code>"),
        "📞 Contact": lambda: user_contact(update, ctx),
    }
    if text in shortcuts:
        await shortcuts[text]()
        return

    # Group: only respond to mentions/replies
    if update.message.chat.type in ["group", "supergroup"]:
        bot_user    = await update.get_bot().get_me()
        is_mention  = f"@{bot_user.username}" in text
        is_reply    = (
            update.message.reply_to_message and
            update.message.reply_to_message.from_user and
            update.message.reply_to_message.from_user.id == bot_user.id
        )
        if not is_mention and not is_reply:
            return

    # Daily limit
    daily = get_daily_count(uid)
    limit = get_limit(uid)
    if daily >= limit:
        await update.message.reply_text(
            f"⚠️ Daily limit reached! (`{daily}/{limit}`)\n"
            "💎 Upgrade to Premium for unlimited queries!",
            parse_mode=ParseMode.MARKDOWN
        ); return

    await update.message.chat.send_action("typing")

    response, tokens = await call_groq(uid, text)

    # Update stats
    u["messages"] = u.get("messages", 0) + 1
    bot_data["stats"]["total_messages"]  = bot_data["stats"].get("total_messages", 0) + 1
    bot_data["stats"]["today_messages"]  = bot_data["stats"].get("today_messages", 0) + 1
    increment_daily(uid)
    reset_daily_stats()

    # Send response — smart ZIP or inline
    if has_code(response):
        code_blocks, clean_text = extract_code_blocks(response)
        clean_text = clean_text.replace("\n[CODE BLOCK]\n", "").strip()

        if should_make_zip(code_blocks):
            project_files = {}
            used_names = set()
            for i, (lang, code) in enumerate(code_blocks):
                fname = detect_filename(lang, i, response, code)
                if fname in used_names:
                    base, ext = (fname.rsplit(".", 1) if "." in fname else (fname, "txt"))
                    fname = f"{base}_{i+1}.{ext}"
                used_names.add(fname)
                project_files[fname] = code
            file_list_md = "\n".join(f"- `{f}`" for f in project_files)
            project_files["README.md"] = (
                "# Project\n\nGenerated by DarkNova AI\n"
                "Built by @MrNewton_2\n\n## Files\n\n" + file_list_md
            )
            zip_buf = make_project_zip(project_files)
            all_langs = [b[0].lower() for b in code_blocks]
            if "html" in all_langs:
                proj_type = "\U0001f310 Web Project"
            elif any(l in all_langs for l in ["py", "python"]):
                proj_type = "\U0001f40d Python Project"
            elif any(l in all_langs for l in ["js", "javascript", "ts"]):
                proj_type = "\u26a1 JS Project"
            else:
                proj_type = "\U0001f4c1 Code Project"
            flist = "\n".join(f"  \U0001f4c4 {f}" for f in project_files)
            caption = (
                f"\U0001f4e6 *{proj_type}*\n"
                f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
                f"{flist}\n\n"
                f"\U0001f916 _Generated by DarkNova AI_\n"
                f"\U0001f468\u200d\U0001f4bb _Built by @MrNewton_2_"
            )
            if clean_text:
                for chunk in split_msg(clean_text):
                    await update.message.reply_text(chunk)
            pname = re.sub(r"[^a-z0-9_]", "", text[:30].lower().replace(" ", "_")) or "project"
            await update.message.reply_document(
                document=zip_buf,
                filename=f"{pname}.zip",
                caption=caption,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            if clean_text:
                for chunk in split_msg(clean_text):
                    await update.message.reply_text(chunk)
            for lang, code in code_blocks:
                lang = lang or "text"
                safe = code[:190].replace("`", "'")
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f4cb Copy Code", callback_data=f"copy_{safe}")]])
                for chunk in split_msg(f"```{lang}\n{code}\n```", 4000):
                    await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    else:
        for chunk in split_msg(response):
            await update.message.reply_text(chunk)

    await save_data()

# ══════════════════════════════════════════════
# ERROR HANDLER
# ══════════════════════════════════════════════
async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception: {ctx.error}", exc_info=ctx.error)

# ══════════════════════════════════════════════
# WEB SERVER (Render health check)
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
    runner  = AppRunner(web_app)
    await runner.setup()
    site = TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server on port {PORT}")

# ══════════════════════════════════════════════
# BUILD APPS
# ══════════════════════════════════════════════
def build_admin_app() -> Application:
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",         admin_start))
    app.add_handler(CommandHandler("broadcast",     cmd_broadcast))
    app.add_handler(CommandHandler("ban",           cmd_ban))
    app.add_handler(CommandHandler("unban",         cmd_unban))
    app.add_handler(CommandHandler("warn",          cmd_warn))
    app.add_handler(CommandHandler("mute",          cmd_mute))
    app.add_handler(CommandHandler("unmute",        cmd_unmute))
    app.add_handler(CommandHandler("premium",       cmd_premium))
    app.add_handler(CommandHandler("removepremium", cmd_removepremium))
    app.add_handler(CommandHandler("setlimit",      cmd_setlimit))
    app.add_handler(CommandHandler("gencode",       cmd_gencode))
    app.add_handler(CommandHandler("deletecode",    cmd_deletecode))
    app.add_handler(CommandHandler("redeeminfo",    cmd_redeeminfo))
    app.add_handler(CommandHandler("forcesub",      cmd_forcesub))
    app.add_handler(CommandHandler("antiflood",     cmd_antiflood))
    app.add_handler(CommandHandler("viewchat",      cmd_viewchat))
    app.add_handler(CommandHandler("clearmem",      cmd_clearmem))
    app.add_handler(CommandHandler("clearmemall",   cmd_clearmemall))
    app.add_handler(CommandHandler("clearchats",    cmd_clearchats))
    app.add_handler(CommandHandler("export",        cmd_export))
    app.add_handler(CommandHandler("sysprompt",     cmd_sysprompt))
    app.add_handler(CommandHandler("advertise",     cmd_advertise))
    app.add_handler(CommandHandler("ping",          cmd_ping))
    app.add_handler(CallbackQueryHandler(admin_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_admin_text))
    app.add_error_handler(error_handler)
    return app


def build_user_app() -> Application:
    app = Application.builder().token(USER_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",   user_start))
    app.add_handler(CommandHandler("help",    user_help))
    app.add_handler(CommandHandler("about",   user_about))
    app.add_handler(CommandHandler("plan",    user_plan))
    app.add_handler(CommandHandler("reset",   user_reset))
    app.add_handler(CommandHandler("contact", user_contact))
    app.add_handler(CommandHandler("ping",    user_ping))
    app.add_handler(CommandHandler("speed",   user_speed))
    app.add_handler(CommandHandler("model",   user_model))
    app.add_handler(CommandHandler("redeem",  user_redeem))
    app.add_handler(CallbackQueryHandler(user_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_message))
    app.add_error_handler(error_handler)
    return app

# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════
async def main():
    global user_bot_instance

    if not ADMIN_BOT_TOKEN or not USER_BOT_TOKEN:
        logger.error("Missing bot tokens!"); return
    if not GROQ_API_KEY:
        logger.error("Missing GROQ_API_KEY!"); return

    load_data()
    bot_data["start_time"] = datetime.now().isoformat()

    # Create global user bot instance for broadcast/advertise
    user_bot_instance = Bot(token=USER_BOT_TOKEN)

    logger.info("Starting DarkNova AI Bot v3.0...")

    admin_app = build_admin_app()
    user_app  = build_user_app()

    await start_web_server()
    asyncio.create_task(periodic_save())

    await admin_app.initialize()
    await user_app.initialize()

    # ── Delete any existing webhooks to avoid Conflict error ──
    logger.info("Deleting old webhooks...")
    await admin_app.bot.delete_webhook(drop_pending_updates=True)
    await user_app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhooks cleared.")

    await admin_app.start()
    await user_app.start()

    # drop_pending_updates=True clears old webhook/polling conflicts
    await admin_app.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )
    await user_app.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )

    logger.info("✅ Both bots running!")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        await save_data()
        try:
            await user_bot_instance.close()
        except Exception:
            pass
        await admin_app.updater.stop()
        await user_app.updater.stop()
        await admin_app.stop()
        await user_app.stop()
        await admin_app.shutdown()
        await user_app.shutdown()
        logger.info("Clean shutdown done.")


if __name__ == "__main__":
    asyncio.run(main())
