"""
╔══════════════════════════════════════════════════════════════╗
║         DARKNOVA AI BOT — PRODUCTION READY v5.0             ║
║              Built by @MrNewton_2                            ║
║   Groq + OpenRouter | Agent System | Full Admin Panel        ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, re, time, asyncio, logging, aiohttp, aiohttp.web
import secrets, string, zipfile, io, math
from datetime import datetime, timedelta
from functools import wraps
from logging.handlers import RotatingFileHandler
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, Bot,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
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
# ENVIRONMENT VARIABLES
# ══════════════════════════════════════════════
ADMIN_BOT_TOKEN = os.environ.get("ADMIN_BOT_TOKEN", "")
USER_BOT_TOKEN  = os.environ.get("USER_BOT_TOKEN",  "")
ADMIN_ID        = int(os.environ.get("ADMIN_ID", "0"))
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
HF_TOKEN        = os.environ.get("HF_TOKEN", "")
PORT            = int(os.environ.get("PORT", "8080"))

DATA_FILE    = "bot_data.json"
data_lock    = asyncio.Lock()
user_bot_obj: Bot = None

# ══════════════════════════════════════════════
# MODEL REGISTRY — Admin can change from panel
# ══════════════════════════════════════════════
GROQ_MODELS = {
    "lightning": {"id": "llama-3.1-8b-instant",     "label": "⚡ Lightning (Fast)"},
    "smart":     {"id": "llama-3.3-70b-versatile",  "label": "🧠 Smart (Balanced)"},
    "powerful":  {"id": "llama-3.1-70b-versatile",  "label": "💪 Powerful (Strong)"},
    "mixtral":   {"id": "mixtral-8x7b-32768",        "label": "🔀 Mixtral (Long ctx)"},
    "gemma":     {"id": "gemma2-9b-it",              "label": "💎 Gemma2 (Google)"},
}

OPENROUTER_MODELS = {
    "llama70b":   {"id": "meta-llama/llama-3.3-70b-instruct:free",  "label": "🦙 Llama 3.3 70B (Free)"},
    "llama8b":    {"id": "meta-llama/llama-3.1-8b-instruct:free",   "label": "🦙 Llama 3.1 8B (Free)"},
    "deepseek":   {"id": "deepseek/deepseek-r1:free",                "label": "🔬 DeepSeek R1 (Free)"},
    "gemma9b":    {"id": "google/gemma-2-9b-it:free",               "label": "💎 Gemma 2 9B (Free)"},
    "qwen":       {"id": "qwen/qwen-2.5-72b-instruct:free",         "label": "🌟 Qwen 2.5 72B (Free)"},
    "mistral":    {"id": "mistralai/mistral-7b-instruct:free",       "label": "🌪 Mistral 7B (Free)"},
}

HF_MODELS = {
    "gemma2_abliterated": {
        "id":    "IlyaGusev/gemma-2-2b-it-abliterated:featherless-ai",
        "label": "🤗 Gemma2 Abliterated (HF)",
    },
    "hf_custom": {
        "id":    "",
        "label": "⚙️ Custom HF Model",
    },
}

# ══════════════════════════════════════════════
# AI PERSONALITIES
# ══════════════════════════════════════════════
PERSONAS = {
    "default": (
        "You are DarkNova — a smart, witty AI assistant built by @MrNewton_2. "
        "Speak Hinglish when user uses Hindi, otherwise English. "
        "Be helpful, direct, confident. Answer everything clearly. "
        "For multi-file projects, put EACH file in its OWN ```lang block and mention filename before it."
    ),
    "teacher":     "You are DarkNova Teacher. Explain step-by-step with examples. Patient, encouraging, adaptive.",
    "hacker":      "You are DarkNova Hacker — ethical security expert. CTFs, bug bounties, Linux, Python. Precise and technical.",
    "philosopher": "You are DarkNova Philosopher. Deep wisdom, multiple perspectives, beautiful thoughtful language.",
    "comedian":    "You are DarkNova Comedian. Witty, punny, clever humor. Still helpful but always fun. Hinglish jokes welcome!",
    "poet":        "You are DarkNova Poet. Beautiful metaphors, rhythm, imagery. English, Hindi, or Hinglish.",
    "lawyer":      "You are DarkNova Lawyer. Precise, logical, thorough. Educational only — not legal advice.",
    "doctor":      "You are DarkNova Doctor. Clear health info. Always remind users to consult a real doctor.",
    "therapist":   "You are DarkNova Therapist. Empathetic listener. Validate feelings, guide gently. Suggest professional help when needed.",
    "tutor":       "You are DarkNova Coding Tutor. Teach programming, debug code, explain algorithms. Clean commented code.",
    "storyteller": "You are DarkNova Storyteller. Engaging narratives, vivid characters, interesting plots.",
    "fitness":     "You are DarkNova Fitness Coach. Workout plans, proper form, nutrition advice, motivation.",
    "chef":        "You are DarkNova Chef. Recipes from every cuisine, techniques, substitutions, meal planning.",
    "interviewer": "You are DarkNova Interview Coach. Mock interviews, resume review, sharp feedback.",
    "translator":  "You are DarkNova Translator. Accurate translations with cultural context. 20+ languages.",
}

AGENT_SYSTEM_PROMPT = """You are DarkNova Agent — an advanced AI with real-world tools.
Built by @MrNewton_2.

You have these tools:
1. web_search(query) — Search internet for real-time info, news, events
2. calculate(expression) — Math, unit conversion, statistics
3. run_python(code) — Execute Python code, get output
4. get_weather(location) — Live weather for any city
5. analyze_task(task, steps) — Break complex tasks into plans

RULES:
- Use tools proactively — don't guess what you can search/calculate
- Chain multiple tools when needed
- For current events → web_search
- For math → calculate
- For complex tasks → analyze_task first, then execute
- Always respond in user's language (Hindi/English/Hinglish)
- Be concise, accurate, and helpful
- Show tool usage transparently
"""

# ══════════════════════════════════════════════
# DEFAULT DATA
# ══════════════════════════════════════════════
def _default():
    return {
        "users": {}, "banned": [], "convos": {}, "maint": False,
        "force_sub": None,
        "cfg": {
            "provider":       "groq",
            "groq_model_key": "lightning",
            "or_model_key":   "llama70b",
            "hf_model_key":   "gemma2_abliterated",
            "custom_groq_id": "",
            "custom_or_id":   "",
            "custom_hf_id":   "",
            "temperature":    0.9,
            "max_tokens":     4096,
            "personality":    "default",
            "system_prompt":  PERSONAS["default"],
            "agent_prompt":   AGENT_SYSTEM_PROMPT,
            "agent_enabled":  True,
        },
        "stats": {
            "total_messages": 0, "today_messages": 0,
            "total_broadcasts": 0, "total_bans": 0,
            "total_mutes": 0, "total_tokens": 0,
            "groq_calls": 0, "groq_errors": 0,
            "or_calls": 0, "or_errors": 0,
            "agent_calls": 0,
            "hf_calls": 0, "hf_errors": 0,
            "last_reset": datetime.now().strftime("%Y-%m-%d"),
        },
        "premium": {}, "codes": {}, "muted": {}, "flood": {},
        "daily_counts": {}, "chats": {},
        "ad_stats": {"sent": 0, "failed": 0},
        "broadcast_stats": {"sent": 0, "failed": 0},
        "welcome": (
            "👋 Welcome, {name}!\n\n"
            "🤖 I'm DarkNova AI — your powerful assistant.\n"
            "📦 Plan: {plan}\n"
            "💬 Daily Queries: {daily}/{limit}\n\n"
            "Type anything to start! 🚀"
        ),
        "limits": {"free": 20, "prem": 99999},
        "antiflood": {"on": True, "max": 8, "win": 10, "mute": 5},
        "start_time": datetime.now().isoformat(),
        "maintenance_msg": "🔧 Bot under maintenance. Please wait...",
    }

bot_data: dict = {}

# ══════════════════════════════════════════════
# DATA I/O
# ══════════════════════════════════════════════
def load_data():
    global bot_data
    base = _default()
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
    logger.info(f"Loaded. Users: {len(bot_data['users'])}")

async def save_data():
    async with data_lock:
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(bot_data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Save: {e}")

async def periodic_save():
    while True:
        await asyncio.sleep(60)
        await save_data()

# ══════════════════════════════════════════════
# MODEL HELPERS
# ══════════════════════════════════════════════
def get_active_model_id() -> str:
    cfg = bot_data.get("cfg", {})
    provider = cfg.get("provider", "groq")
    if provider == "groq":
        custom = cfg.get("custom_groq_id", "").strip()
        if custom: return custom
        key = cfg.get("groq_model_key", "lightning")
        return GROQ_MODELS.get(key, GROQ_MODELS["lightning"])["id"]
    elif provider == "huggingface":
        custom = cfg.get("custom_hf_id", "").strip()
        if custom: return custom
        key = cfg.get("hf_model_key", "gemma2_abliterated")
        return HF_MODELS.get(key, HF_MODELS["gemma2_abliterated"])["id"]
    else:
        custom = cfg.get("custom_or_id", "").strip()
        if custom: return custom
        key = cfg.get("or_model_key", "llama70b")
        return OPENROUTER_MODELS.get(key, OPENROUTER_MODELS["llama70b"])["id"]

def get_active_model_label() -> str:
    cfg = bot_data.get("cfg", {})
    provider = cfg.get("provider", "groq")
    if provider == "groq":
        if cfg.get("custom_groq_id"): return "⚙️ Custom Groq Model"
        key = cfg.get("groq_model_key", "lightning")
        return GROQ_MODELS.get(key, GROQ_MODELS["lightning"])["label"]
    elif provider == "huggingface":
        if cfg.get("custom_hf_id"): return "⚙️ Custom HF Model"
        key = cfg.get("hf_model_key", "gemma2_abliterated")
        return HF_MODELS.get(key, HF_MODELS["gemma2_abliterated"])["label"]
    else:
        if cfg.get("custom_or_id"): return "⚙️ Custom OR Model"
        key = cfg.get("or_model_key", "llama70b")
        return OPENROUTER_MODELS.get(key, OPENROUTER_MODELS["llama70b"])["label"]

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
    k = str(uid); m = bot_data.get("muted", {})
    if k not in m: return False
    until = m[k].get("until")
    if until and datetime.fromisoformat(until) < datetime.now():
        del bot_data["muted"][k]; return False
    return True

def is_premium(uid: int) -> bool:
    k = str(uid); p = bot_data.get("premium", {})
    if k not in p: return False
    exp = p[k].get("expiry")
    if exp == "permanent": return True
    if exp and datetime.fromisoformat(exp) < datetime.now():
        del bot_data["premium"][k]; return False
    return True

def get_daily(uid: int) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    k = str(uid); dc = bot_data.setdefault("daily_counts", {})
    if k not in dc or dc[k].get("date") != today:
        dc[k] = {"date": today, "count": 0}
    return dc[k]["count"]

def inc_daily(uid: int):
    today = datetime.now().strftime("%Y-%m-%d")
    k = str(uid); dc = bot_data.setdefault("daily_counts", {})
    if k not in dc or dc[k].get("date") != today:
        dc[k] = {"date": today, "count": 0}
    dc[k]["count"] += 1

def get_limit(uid: int) -> int:
    return bot_data["limits"]["prem"] if is_premium(uid) else bot_data["limits"]["free"]

def uptime() -> str:
    s = datetime.fromisoformat(bot_data.get("start_time", datetime.now().isoformat()))
    d = datetime.now() - s
    h, r = divmod(int(d.total_seconds()), 3600)
    m, s2 = divmod(r, 60)
    return f"{h}h {m}m {s2}s"

def reset_today():
    today = datetime.now().strftime("%Y-%m-%d")
    if bot_data["stats"].get("last_reset") != today:
        bot_data["stats"]["today_messages"] = 0
        bot_data["stats"]["last_reset"] = today

def split_text(text: str, n: int = 4000) -> list:
    if len(text) <= n: return [text]
    parts = []
    while len(text) > n:
        i = text.rfind("\n", 0, n)
        if i == -1: i = n
        parts.append(text[:i]); text = text[i:].lstrip("\n")
    if text: parts.append(text)
    return parts

# ══════════════════════════════════════════════
# ANTIFLOOD
# ══════════════════════════════════════════════
def check_flood(uid: int) -> bool:
    af = bot_data.get("antiflood", {})
    if not af.get("on"): return False
    k = str(uid); now = time.time()
    fl = bot_data.setdefault("flood", {})
    fl.setdefault(k, [])
    fl[k] = [t for t in fl[k] if now - t < af.get("win", 10)]
    fl[k].append(now)
    return len(fl[k]) > af.get("max", 8)

def apply_mute(uid: int):
    mins = bot_data.get("antiflood", {}).get("mute", 5)
    until = (datetime.now() + timedelta(minutes=mins)).isoformat()
    bot_data["muted"][str(uid)] = {"until": until, "reason": "antiflood"}

# ══════════════════════════════════════════════
# CODE / ZIP HELPERS
# ══════════════════════════════════════════════
def extract_blocks(text: str):
    pattern = r"```(\w*)\n?([\s\S]*?)```"
    blocks = re.findall(pattern, text)
    clean  = re.sub(pattern, "\n[CODE]\n", text)
    return blocks, clean

def has_code(text: str) -> bool:
    return "```" in text

def detect_fname(lang: str, idx: int, ai_text: str) -> str:
    lang = (lang or "txt").lower()
    emap = {
        "python":"py","py":"py","javascript":"js","js":"js","typescript":"ts","ts":"ts",
        "html":"html","css":"css","json":"json","sql":"sql","bash":"sh","shell":"sh",
        "sh":"sh","java":"java","cpp":"cpp","c":"c","php":"php","ruby":"rb",
        "go":"go","rust":"rs","kotlin":"kt","swift":"swift","yaml":"yaml","yml":"yml",
        "markdown":"md","md":"md","xml":"xml",
    }
    ext = emap.get(lang, lang or "txt")
    for pat in [r"`([\w\-./]+\." + ext + r")`", r"\*\*([\w\-./]+\." + ext + r")\*\*"]:
        m = re.search(pat, ai_text, re.IGNORECASE)
        if m: return m.group(1)
    defaults = {
        "html":["index.html","about.html","contact.html","shop.html","product.html"],
        "css": ["style.css","main.css","shop.css"],
        "js":  ["script.js","main.js","app.js","cart.js"],
        "py":  ["main.py","app.py","server.py","bot.py"],
        "json":["package.json","data.json","config.json"],
        "sh":  ["setup.sh","run.sh"], "sql":["database.sql"],
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
    return len(blocks) == 1 and blocks[0][1].count("\n") > 50

# ══════════════════════════════════════════════
# GROQ AI CALL
# ══════════════════════════════════════════════
async def call_groq(uid: int, user_msg: str) -> tuple:
    cfg    = bot_data.get("cfg", {})
    prompt = cfg.get("system_prompt") or PERSONAS["default"]
    model  = get_active_model_id()
    temp   = float(cfg.get("temperature", 0.9))
    maxt   = int(cfg.get("max_tokens", 4096))
    msgs   = [{"role": "system", "content": prompt}]
    if is_premium(uid):
        hist = bot_data.get("convos", {}).get(str(uid), [])
        cut  = (datetime.now() - timedelta(hours=48)).isoformat()
        hist = [m for m in hist if m.get("ts","") > cut][-40:]
        msgs += [{"role": m["role"], "content": m["content"]} for m in hist]
    msgs.append({"role": "user", "content": user_msg})
    provider = cfg.get("provider", "groq")
    if provider == "groq":
        url     = "https://api.groq.com/openai/v1/chat/completions"
        api_key = GROQ_API_KEY
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        stat_ok  = "groq_calls"; stat_err = "groq_errors"
    elif provider == "huggingface":
        url     = "https://router.huggingface.co/v1/chat/completions"
        api_key = HF_TOKEN
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        stat_ok  = "hf_calls"; stat_err = "hf_errors"
    else:
        url     = "https://openrouter.ai/api/v1/chat/completions"
        api_key = OPENROUTER_KEY
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://t.me/DarkNovaBot",
            "X-Title": "DarkNova Bot",
        }
        stat_ok  = "or_calls"; stat_err = "or_errors"
    bot_data["stats"][stat_ok] = bot_data["stats"].get(stat_ok, 0) + 1
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                url, headers=headers,
                json={"model": model, "messages": msgs, "temperature": temp, "max_tokens": maxt},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as r:
                if r.status != 200:
                    err = await r.text()
                    logger.error(f"AI {r.status}: {err[:200]}")
                    bot_data["stats"][stat_err] = bot_data["stats"].get(stat_err, 0) + 1
                    return f"⚠️ AI error ({r.status}). Try again.", 0
                data = await r.json()
        reply  = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        bot_data["stats"]["total_tokens"] = bot_data["stats"].get("total_tokens", 0) + tokens
        if is_premium(uid):
            k = str(uid); c = bot_data.setdefault("convos", {})
            c.setdefault(k, []); ts = datetime.now().isoformat()
            c[k] += [{"role":"user","content":user_msg,"ts":ts},{"role":"assistant","content":reply,"ts":ts}]
            c[k] = c[k][-40:]
        k = str(uid); ch = bot_data.setdefault("chats", {})
        ch.setdefault(k, [])
        ch[k].append({"ts":datetime.now().isoformat(),"user":user_msg[:500],"ai":reply[:500]})
        ch[k] = ch[k][-200:]
        return reply, tokens
    except asyncio.TimeoutError:
        bot_data["stats"][stat_err] = bot_data["stats"].get(stat_err, 0) + 1
        return "⏱️ Timeout. Try again.", 0
    except Exception as e:
        bot_data["stats"][stat_err] = bot_data["stats"].get(stat_err, 0) + 1
        logger.error(f"AI call: {e}")
        return f"❌ Error: {str(e)[:80]}", 0

# ══════════════════════════════════════════════
# AGENT TOOLS
# ══════════════════════════════════════════════
AGENT_TOOLS = [
    {"type":"function","function":{"name":"web_search","description":"Search internet for real-time info, news, events, prices, scores.","parameters":{"type":"object","properties":{"query":{"type":"string","description":"Search query"}},"required":["query"]}}},
    {"type":"function","function":{"name":"calculate","description":"Math calculations, unit conversions, statistics.","parameters":{"type":"object","properties":{"expression":{"type":"string","description":"Math expression"}},"required":["expression"]}}},
    {"type":"function","function":{"name":"run_python","description":"Execute Python code and return output.","parameters":{"type":"object","properties":{"code":{"type":"string","description":"Python code to run"}},"required":["code"]}}},
    {"type":"function","function":{"name":"get_weather","description":"Get live weather for any city or location.","parameters":{"type":"object","properties":{"location":{"type":"string","description":"City or location name"}},"required":["location"]}}},
    {"type":"function","function":{"name":"analyze_task","description":"Break complex task into steps and plan.","parameters":{"type":"object","properties":{"task":{"type":"string"},"steps":{"type":"array","items":{"type":"string"}}},"required":["task","steps"]}}},
]

async def exec_tool(name: str, args: dict) -> str:
    if name == "web_search":
        q = args.get("query", "")
        try:
            url = f"https://api.duckduckgo.com/?q={q.replace(' ','+')}&format=json&no_html=1&skip_disambig=1"
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 200:
                        d = await r.json(content_type=None)
                        ans  = d.get("Answer","")
                        abst = d.get("AbstractText","")
                        rels = d.get("RelatedTopics",[])
                        result = ans or abst
                        if not result and rels:
                            result = "\n".join(t.get("Text","") for t in rels[:3] if isinstance(t,dict) and t.get("Text"))
                        return f"Search results for '{q}':\n{result}" if result else f"No direct results for '{q}'. Try more specific terms."
        except Exception as e:
            return f"Search error: {str(e)[:100]}"

    elif name == "calculate":
        expr = args.get("expression","")
        try:
            safe = {
                "__builtins__": {}, "math": math,
                "abs":abs,"round":round,"min":min,"max":max,"sum":sum,
                "int":int,"float":float,"pow":pow,"sqrt":math.sqrt,
                "pi":math.pi,"e":math.e,"sin":math.sin,"cos":math.cos,
                "tan":math.tan,"log":math.log,"log10":math.log10,"ceil":math.ceil,"floor":math.floor,
            }
            result = eval(expr, safe)
            return f"Result: {expr} = {result}"
        except Exception as ex:
            return f"Calc error: {ex}"

    elif name == "run_python":
        code = args.get("code","")
        try:
            import sys; from io import StringIO
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = StringIO()
            local_vars = {}
            try:
                exec(compile(code,"<agent>","exec"),{"__builtins__":__builtins__},local_vars)
                out = sys.stdout.getvalue()
                err = sys.stderr.getvalue()
            except Exception as ex:
                out = ""; err = str(ex)
            finally:
                sys.stdout = old_out; sys.stderr = old_err
            parts = []
            if out: parts.append(f"Output:\n{out}")
            if err: parts.append(f"Error:\n{err}")
            return "\n".join(parts)[:1500] if parts else "Executed (no output)."
        except Exception as e:
            return f"Exec error: {e}"

    elif name == "get_weather":
        loc = args.get("location","")
        try:
            loc_enc = loc.replace(" ","+")
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://wttr.in/{loc_enc}?format=j1", timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 200:
                        d = await r.json()
                        cur  = d["current_condition"][0]
                        area = d["nearest_area"][0]
                        city = area["areaName"][0]["value"]
                        cntry= area["country"][0]["value"]
                        return (
                            f"Weather in {city}, {cntry}:\n"
                            f"Temp: {cur['temp_C']}°C / {cur['temp_F']}°F\n"
                            f"Feels: {cur['FeelsLikeC']}°C\n"
                            f"Condition: {cur['weatherDesc'][0]['value']}\n"
                            f"Humidity: {cur['humidity']}%\n"
                            f"Wind: {cur['windspeedKmph']} km/h"
                        )
                    return f"Weather unavailable for {loc}."
        except Exception as e:
            return f"Weather error: {str(e)[:80]}"

    elif name == "analyze_task":
        task  = args.get("task","")
        steps = args.get("steps",[])
        plan  = "\n".join(f"{i+1}. {s}" for i,s in enumerate(steps))
        return f"Task: {task}\n\nPlan ({len(steps)} steps):\n{plan}"

    return f"Unknown tool: {name}"

AGENT_TRIGGERS = [
    "search","find","look up","latest","news","today","weather","mausam",
    "calculate","compute","solve","math","convert","how much","kitna",
    "run code","execute","debug","test code","kya hai aaj",
    "research","compare","analyze","plan","steps to","abhi","current",
    "right now","live","price","rate","score","result","dhundho",
]

def wants_agent(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in AGENT_TRIGGERS)

async def run_agent(uid: int, user_msg: str) -> str:
    cfg = bot_data.get("cfg",{})
    if not cfg.get("agent_enabled", True):
        return await call_groq(uid, user_msg)
    key = OPENROUTER_KEY or GROQ_API_KEY or HF_TOKEN
    if not key:
        return "⚠️ No API key configured."
    provider = cfg.get("provider", "groq")
    if provider == "huggingface" and HF_TOKEN:
        url = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        model = HF_MODELS.get(cfg.get("hf_model_key","gemma2_abliterated"),HF_MODELS["gemma2_abliterated"])["id"]
        if cfg.get("custom_hf_id"): model = cfg["custom_hf_id"]
    elif OPENROUTER_KEY:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://t.me/DarkNovaBot",
            "X-Title": "DarkNova Agent",
        }
        model = OPENROUTER_MODELS.get(cfg.get("or_model_key","llama70b"),OPENROUTER_MODELS["llama70b"])["id"]
        if cfg.get("custom_or_id"): model = cfg["custom_or_id"]
    else:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        model = GROQ_MODELS.get(cfg.get("groq_model_key","lightning"),GROQ_MODELS["lightning"])["id"]
        if cfg.get("custom_groq_id"): model = cfg["custom_groq_id"]

    agent_prompt = cfg.get("agent_prompt") or AGENT_SYSTEM_PROMPT
    messages = [
        {"role":"system","content": agent_prompt},
        {"role":"user","content": user_msg}
    ]
    tools_used = []
    bot_data["stats"]["agent_calls"] = bot_data["stats"].get("agent_calls",0)+1

    for step in range(6):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    url, headers=headers,
                    json={"model":model,"messages":messages,"tools":AGENT_TOOLS,"tool_choice":"auto","max_tokens":2048,"temperature":0.7},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as r:
                    if r.status != 200:
                        logger.error(f"Agent {r.status}: {await r.text()}")
                        return "⚠️ Agent error. Try again."
                    data = await r.json()
        except asyncio.TimeoutError:
            return "⏱️ Agent timed out."
        except Exception as e:
            return f"❌ Agent error: {str(e)[:80]}"

        choice  = data["choices"][0]
        msg_obj = choice["message"]

        if not msg_obj.get("tool_calls"):
            final = msg_obj.get("content","").strip()
            if tools_used:
                tool_log = "\n".join(f"  🔧 `{t}`" for t in tools_used)
                final = f"🤖 *Tools used:*\n{tool_log}\n\n━━━━━━━━━━━━━━━━━━━\n{final}"
            return final or "Agent completed."

        messages.append({"role":"assistant","content":msg_obj.get("content") or "","tool_calls":msg_obj["tool_calls"]})
        for tc in msg_obj["tool_calls"]:
            tname = tc["function"]["name"]
            try:   targs = json.loads(tc["function"]["arguments"])
            except: targs = {}
            first_val = list(targs.values())[0][:40] if targs else ""
            tools_used.append(f"{tname}({first_val})")
            logger.info(f"Agent tool: {tname} {targs}")
            result = await exec_tool(tname, targs)
            messages.append({"role":"tool","tool_call_id":tc["id"],"name":tname,"content":result})

    return "⚠️ Agent reached max steps. Try a simpler query."

# ══════════════════════════════════════════════
# FORCE SUBSCRIBE
# ══════════════════════════════════════════════
async def check_fsub(uid: int, bot: Bot) -> bool:
    fs = bot_data.get("force_sub")
    if not fs: return True
    try:
        m = await bot.get_chat_member(fs, uid)
        return m.status not in ["left","kicked","banned"]
    except Exception:
        return True

def fsub_kb() -> InlineKeyboardMarkup:
    fs = bot_data.get("force_sub","@channel")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{fs.lstrip('@')}")],
        [InlineKeyboardButton("✅ Check", callback_data="cs")],
    ])

# ══════════════════════════════════════════════
# BROADCAST
# ══════════════════════════════════════════════
async def bcast_all(msg: str, tag: str = "📢 *Broadcast*") -> tuple:
    global user_bot_obj
    sent = failed = 0
    for uid_s in list(bot_data.get("users",{}).keys()):
        try:
            await user_bot_obj.send_message(int(uid_s), f"{tag}\n\n{msg}", parse_mode=ParseMode.MARKDOWN)
            sent += 1; await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Bcast fail {uid_s}: {e}"); failed += 1
    return sent, failed

# ══════════════════════════════════════════════
# ADMIN DECORATOR
# ══════════════════════════════════════════════
def admin_only(fn):
    @wraps(fn)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE, *a, **kw):
        uid = (update.message or update.callback_query).from_user.id
        if uid != ADMIN_ID:
            if update.message: await update.message.reply_text("🚫 Admin only.")
            else: await update.callback_query.answer("🚫 Admin only.", show_alert=True)
            return
        return await fn(update, ctx, *a, **kw)
    return wrapper

# ══════════════════════════════════════════════
# ADMIN MENUS
# ══════════════════════════════════════════════
def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard",      callback_data="a_dash"),
         InlineKeyboardButton("📈 Stats",          callback_data="a_stats")],
        [InlineKeyboardButton("👥 Users",          callback_data="a_users"),
         InlineKeyboardButton("🟢 Live Chats",     callback_data="a_live")],
        [InlineKeyboardButton("🤖 AI Settings",    callback_data="a_ai"),
         InlineKeyboardButton("🔗 AI Provider",    callback_data="a_provider")],
        [InlineKeyboardButton("⚙️ System Prompt",  callback_data="a_sysprompt"),
         InlineKeyboardButton("🧠 Agent Setup",    callback_data="a_agent")],
        [InlineKeyboardButton("📢 Broadcast",      callback_data="a_bcast"),
         InlineKeyboardButton("📣 Advertise",      callback_data="a_ad")],
        [InlineKeyboardButton("🚫 Ban System",     callback_data="a_ban"),
         InlineKeyboardButton("🔇 Mute System",    callback_data="a_mute")],
        [InlineKeyboardButton("💎 Premium",        callback_data="a_prem"),
         InlineKeyboardButton("🎫 Codes",          callback_data="a_codes")],
        [InlineKeyboardButton("🔒 Force Sub",      callback_data="a_fsub"),
         InlineKeyboardButton("🛡 Antiflood",      callback_data="a_flood")],
        [InlineKeyboardButton("💬 View Chat",      callback_data="a_vchat"),
         InlineKeyboardButton("🧹 Clear Memory",   callback_data="a_mem")],
        [InlineKeyboardButton("🔧 Maintenance",    callback_data="a_maint"),
         InlineKeyboardButton("🔄 Restart",        callback_data="a_restart")],
        [InlineKeyboardButton("📋 Export Users",   callback_data="a_export"),
         InlineKeyboardButton("📊 Daily Report",   callback_data="a_daily")],
        [InlineKeyboardButton("⚡ Ping",           callback_data="a_ping"),
         InlineKeyboardButton("🗑 Clear Logs",     callback_data="a_clrlogs")],
        [InlineKeyboardButton("❌ Close Panel",     callback_data="a_close")],
    ])

BACK = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])

def ai_menu() -> InlineKeyboardMarkup:
    cfg  = bot_data.get("cfg",{})
    temp = cfg.get("temperature",0.9)
    mtok = cfg.get("max_tokens",4096)
    pers = cfg.get("personality","default")
    prov = cfg.get("provider","groq").upper()
    model_lbl = get_active_model_label()
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔗 Provider: {prov}", callback_data="a_provider")],
        [InlineKeyboardButton(f"🤖 {model_lbl}",      callback_data="a_models")],
        [InlineKeyboardButton("📝 Set System Prompt",  callback_data="ai_setprompt")],
        [InlineKeyboardButton("👁 View Prompt",        callback_data="ai_viewprompt")],
        [InlineKeyboardButton("🎭 Personalities",      callback_data="ai_pers"),
         InlineKeyboardButton(f"✅ {pers}",            callback_data="ai_curpers")],
        [InlineKeyboardButton(f"🌡 Temp: {temp}",      callback_data="ai_temp"),
         InlineKeyboardButton(f"📏 Tokens: {mtok}",    callback_data="ai_tokens")],
        [InlineKeyboardButton("🔄 Reset Defaults",     callback_data="ai_reset")],
        [InlineKeyboardButton("⬅️ Back",               callback_data="a_main")],
    ])

def provider_menu() -> InlineKeyboardMarkup:
    cur = bot_data.get("cfg",{}).get("provider","groq")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{'✅ ' if cur=='groq' else ''}⚡ Groq", callback_data="prov_groq"),
         InlineKeyboardButton(f"{'✅ ' if cur=='openrouter' else ''}🌐 OpenRouter", callback_data="prov_or"),
         InlineKeyboardButton(f"{'✅ ' if cur=='huggingface' else ''}🤗 HuggingFace", callback_data="prov_hf")],
        [InlineKeyboardButton("📋 Groq Models",   callback_data="a_models_groq"),
         InlineKeyboardButton("📋 OR Models",     callback_data="a_models_or"),
         InlineKeyboardButton("📋 HF Models",     callback_data="a_models_hf")],
        [InlineKeyboardButton("🔑 Custom Groq ID",callback_data="set_custom_groq"),
         InlineKeyboardButton("🔑 Custom OR ID",  callback_data="set_custom_or")],
        [InlineKeyboardButton("🔑 Custom HF ID",  callback_data="set_custom_hf"),
         InlineKeyboardButton("🗑 Clear HF ID",   callback_data="clr_custom_hf")],
        [InlineKeyboardButton("🗑 Clear Groq ID", callback_data="clr_custom_groq"),
         InlineKeyboardButton("🗑 Clear OR ID",   callback_data="clr_custom_or")],
        [InlineKeyboardButton("⬅️ Back",           callback_data="a_ai")],
    ])

def hf_models_menu() -> InlineKeyboardMarkup:
    cur  = bot_data.get("cfg",{}).get("hf_model_key","gemma2_abliterated")
    btns = []
    for k, v in HF_MODELS.items():
        if not v["id"]: continue
        lbl = f"✅ {v['label']}" if k==cur else v["label"]
        btns.append([InlineKeyboardButton(lbl, callback_data=f"hfm_{k}")])
    btns.append([InlineKeyboardButton("⬅️ Back", callback_data="a_provider")])
    return InlineKeyboardMarkup(btns)

def groq_models_menu() -> InlineKeyboardMarkup:
    cur = bot_data.get("cfg",{}).get("groq_model_key","lightning")
    btns = []
    for k, v in GROQ_MODELS.items():
        lbl = f"✅ {v['label']}" if k==cur else v["label"]
        btns.append([InlineKeyboardButton(lbl, callback_data=f"gm_{k}")])
    btns.append([InlineKeyboardButton("⬅️ Back", callback_data="a_provider")])
    return InlineKeyboardMarkup(btns)

def or_models_menu() -> InlineKeyboardMarkup:
    cur = bot_data.get("cfg",{}).get("or_model_key","llama70b")
    btns = []
    for k, v in OPENROUTER_MODELS.items():
        lbl = f"✅ {v['label']}" if k==cur else v["label"]
        btns.append([InlineKeyboardButton(lbl, callback_data=f"orm_{k}")])
    btns.append([InlineKeyboardButton("⬅️ Back", callback_data="a_provider")])
    return InlineKeyboardMarkup(btns)

def pers_menu() -> InlineKeyboardMarkup:
    cur = bot_data.get("cfg",{}).get("personality","default")
    btns, row = [], []
    for name in PERSONAS:
        lbl = f"✅{name}" if name==cur else name
        row.append(InlineKeyboardButton(lbl, callback_data=f"pers_{name}"))
        if len(row)==2: btns.append(row); row=[]
    if row: btns.append(row)
    btns.append([InlineKeyboardButton("⬅️ Back", callback_data="a_ai")])
    return InlineKeyboardMarkup(btns)

def temp_menu() -> InlineKeyboardMarkup:
    cur = float(bot_data.get("cfg",{}).get("temperature",0.9))
    btns, row = [], []
    for t in [0.3,0.5,0.7,0.9,1.1,1.3,1.5,1.8,2.0]:
        row.append(InlineKeyboardButton(f"✅{t}" if t==cur else str(t), callback_data=f"temp_{t}"))
        if len(row)==3: btns.append(row); row=[]
    if row: btns.append(row)
    btns.append([InlineKeyboardButton("⬅️ Back", callback_data="a_ai")])
    return InlineKeyboardMarkup(btns)

def tok_menu() -> InlineKeyboardMarkup:
    cur = int(bot_data.get("cfg",{}).get("max_tokens",4096))
    btns, row = [], []
    for t in [512,1024,2048,4096,8192,16384,32768]:
        row.append(InlineKeyboardButton(f"✅{t}" if t==cur else str(t), callback_data=f"tok_{t}"))
        if len(row)==3: btns.append(row); row=[]
    if row: btns.append(row)
    btns.append([InlineKeyboardButton("⬅️ Back", callback_data="a_ai")])
    return InlineKeyboardMarkup(btns)

# ══════════════════════════════════════════════
# ADMIN /start
# ══════════════════════════════════════════════
@admin_only
async def adm_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg = bot_data.get("cfg",{})
    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "║  🤖 DarkNova Admin  ║\n"
        "║  Control Panel v5.0 ║\n"
        "╚══════════════════════╝\n\n"
        f"👤 {update.effective_user.first_name}\n"
        f"⏱ Uptime: {uptime()}\n"
        f"👥 Users: {len(bot_data.get('users',{}))}\n"
        f"🔗 Provider: {cfg.get('provider','groq').upper()}\n"
        f"🤖 Model: {get_active_model_label()}\n\n"
        "Choose an option:",
        reply_markup=main_menu()
    )

# ══════════════════════════════════════════════
# ADMIN CALLBACK HANDLER
# ══════════════════════════════════════════════
@admin_only
async def adm_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data
    await q.answer()

    if d == "a_main":
        await q.edit_message_text("🏠 Main Menu", reply_markup=main_menu()); return
    if d == "a_close":
        await q.edit_message_text("✅ Closed. /start to reopen."); return

    # ── DASHBOARD ──────────────────────────────
    if d == "a_dash":
        reset_today()
        users = bot_data.get("users",{})
        now   = datetime.now()
        act24 = sum(1 for u in users.values() if (now-datetime.fromisoformat(u.get("last_active",now.isoformat()))).total_seconds()<86400)
        prems = sum(1 for uid in users if is_premium(int(uid)))
        s     = bot_data.get("stats",{})
        cfg   = bot_data.get("cfg",{})
        txt = (
            "📊 DASHBOARD\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"Users: {len(users)} | Active 24h: {act24}\n"
            f"Premium: {prems} | Banned: {len(bot_data.get('banned',[]))}\n"
            f"Muted: {len(bot_data.get('muted',{}))}\n\n"
            f"Messages Today: {s.get('today_messages',0)}\n"
            f"Total Messages: {s.get('total_messages',0)}\n"
            f"Tokens Used: {s.get('total_tokens',0)}\n"
            f"Agent Calls: {s.get('agent_calls',0)}\n\n"
            f"Provider: {cfg.get('provider','groq').upper()}\n"
            f"Model: {get_active_model_label()}\n"
            f"Temp: {cfg.get('temperature',0.9)} | Tokens: {cfg.get('max_tokens',4096)}\n"
            f"Persona: {cfg.get('personality','default')}\n\n"
            f"Maintenance: {'ON' if bot_data.get('maint') else 'OFF'}\n"
            f"Force Sub: {bot_data.get('force_sub') or 'OFF'}\n"
            f"Antiflood: {'ON' if bot_data.get('antiflood',{}).get('on') else 'OFF'}\n"
            f"Agent: {'ON' if cfg.get('agent_enabled',True) else 'OFF'}\n\n"
            f"Uptime: {uptime()}"
        )
        await q.edit_message_text(txt, reply_markup=BACK); return

    # ── STATS ──────────────────────────────────
    if d == "a_stats":
        s = bot_data.get("stats",{})
        txt = (
            "📈 STATS\n━━━━━━━━━━━━━━━━━━━\n"
            f"Messages: {s.get('total_messages',0)} (Today: {s.get('today_messages',0)})\n"
            f"Broadcasts: {s.get('total_broadcasts',0)}\n"
            f"Bans: {s.get('total_bans',0)} | Mutes: {s.get('total_mutes',0)}\n"
            f"Tokens: {s.get('total_tokens',0)}\n\n"
            f"Groq: {s.get('groq_calls',0)} calls | {s.get('groq_errors',0)} errors\n"
            f"OpenRouter: {s.get('or_calls',0)} calls | {s.get('or_errors',0)} errors\n"
            f"Agent calls: {s.get('agent_calls',0)}\n\n"
            f"Uptime: {uptime()}"
        )
        await q.edit_message_text(txt, reply_markup=BACK); return

    # ── USERS ──────────────────────────────────
    if d == "a_users":
        users = bot_data.get("users",{})
        lines = [f"👥 USERS ({len(users)} total)\n━━━━━━━━━━━━━━━━━━━"]
        for uid, u in list(users.items())[:25]:
            tags = ("💎" if is_premium(int(uid)) else "🆓") + \
                   ("🚫" if is_banned(int(uid)) else "") + \
                   ("🔇" if is_muted(int(uid)) else "") + \
                   (f"⚠️{u.get('warnings',0)}" if u.get("warnings",0) else "")
            lines.append(f"{tags} {uid} | {u.get('name','?')} @{u.get('username','—')} | {u.get('messages',0)}msgs")
        if len(users)>25: lines.append(f"...+{len(users)-25} more")
        await q.edit_message_text("\n".join(lines)[:4000], reply_markup=BACK); return

    # ── LIVE ───────────────────────────────────
    if d == "a_live":
        users = bot_data.get("users",{}); chats = bot_data.get("chats",{})
        now = datetime.now(); lines = ["🟢 LIVE (last 30 min)\n━━━━━━━━━━━━━━━━━━━"]; count=0
        for uid, u in users.items():
            try:
                delta = (now-datetime.fromisoformat(u.get("last_active",now.isoformat()))).total_seconds()
                if delta < 1800:
                    last = chats.get(uid,[""])[-1].get("user","")[:50] if uid in chats and chats[uid] else ""
                    lines.append(f"{uid} | {u.get('name','?')}\n  {last}\n  {int(delta//60)}m ago"); count+=1
            except Exception: pass
        if not count: lines.append("No active users.")
        await q.edit_message_text("\n".join(lines)[:4000], reply_markup=BACK); return

    # ── AI SETTINGS ────────────────────────────
    if d == "a_ai":
        await q.edit_message_text("🤖 AI Settings", reply_markup=ai_menu()); return
    if d == "ai_viewprompt":
        p = bot_data.get("cfg",{}).get("system_prompt","Not set")
        await q.edit_message_text(f"📝 Current Prompt:\n\n{p[:3800]}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="a_ai")]])); return
    if d == "ai_setprompt":
        ctx.user_data["await"] = "set_prompt"
        await q.edit_message_text("📝 Send your new system prompt now:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel",callback_data="a_ai")]])); return
    if d == "ai_pers":
        await q.edit_message_text("🎭 Select Personality (✅=active):", reply_markup=pers_menu()); return
    if d == "ai_curpers":
        await q.answer(f"Active: {bot_data.get('cfg',{}).get('personality','default')}", show_alert=True); return
    if d == "ai_temp":
        await q.edit_message_text("🌡 Select Temperature (✅=current):", reply_markup=temp_menu()); return
    if d == "ai_tokens":
        await q.edit_message_text("📏 Select Max Tokens (✅=current):", reply_markup=tok_menu()); return
    if d == "ai_reset":
        bot_data["cfg"].update({"temperature":0.9,"max_tokens":4096,"personality":"default","system_prompt":PERSONAS["default"]})
        await save_data(); await q.answer("✅ Reset done!", show_alert=True)
        await q.edit_message_text("🤖 AI Settings (reset):", reply_markup=ai_menu()); return

    if d.startswith("pers_"):
        name = d[5:]
        if name in PERSONAS:
            bot_data["cfg"]["personality"] = name
            bot_data["cfg"]["system_prompt"] = PERSONAS[name]
            await save_data(); await q.answer(f"✅ {name}", show_alert=True)
            await q.edit_message_text("🎭 Personalities (updated):", reply_markup=pers_menu()); return
    if d.startswith("temp_"):
        v = float(d[5:]); bot_data["cfg"]["temperature"] = v
        await save_data(); await q.answer(f"✅ Temp → {v}", show_alert=True)
        await q.edit_message_text("🌡 Temperature (updated):", reply_markup=temp_menu()); return
    if d.startswith("tok_"):
        v = int(d[4:]); bot_data["cfg"]["max_tokens"] = v
        await save_data(); await q.answer(f"✅ Tokens → {v}", show_alert=True)
        await q.edit_message_text("📏 Max Tokens (updated):", reply_markup=tok_menu()); return

    # ── PROVIDER ───────────────────────────────
    if d == "a_provider":
        cfg = bot_data.get("cfg",{})
        cg  = cfg.get("custom_groq_id","") or "Not set"
        cor = cfg.get("custom_or_id","")   or "Not set"
        chf = cfg.get("custom_hf_id","")   or "Not set"
        hf_status = "✅ Configured" if HF_TOKEN else "❌ HF_TOKEN not set"
        prov = cfg.get('provider','groq').upper()
        mlbl = get_active_model_label()
        g_st = 'YES' if GROQ_API_KEY else 'NO'
        o_st = 'YES' if OPENROUTER_KEY else 'NO'
        txt = (
            'AI PROVIDER\n'
            '---\n'
            'Active: ' + prov + '\n'
            'Model: ' + mlbl + '\n\n'
            'Groq: ' + g_st + '\n'
            'OpenRouter: ' + o_st + '\n'
            'HuggingFace: ' + hf_status + '\n\n'
            'Custom Groq: ' + cg + '\n'
            'Custom OR: ' + cor + '\n'
            'Custom HF: ' + chf
        )
        await q.edit_message_text(txt, reply_markup=provider_menu()); return

    if d == "prov_groq":
        bot_data["cfg"]["provider"] = "groq"
        await save_data(); await q.answer("✅ Switched to Groq!", show_alert=True)
        await q.edit_message_text("🔗 Provider: GROQ", reply_markup=provider_menu()); return
    if d == "prov_or":
        bot_data["cfg"]["provider"] = "openrouter"
        await save_data(); await q.answer("✅ Switched to OpenRouter!", show_alert=True)
        await q.edit_message_text("🔗 Provider: OpenRouter", reply_markup=provider_menu()); return
    if d == "prov_hf":
        if not HF_TOKEN:
            await q.answer("⚠️ HF_TOKEN not set in env vars!", show_alert=True); return
        bot_data["cfg"]["provider"] = "huggingface"
        await save_data(); await q.answer("✅ Switched to HuggingFace!", show_alert=True)
        await q.edit_message_text("🔗 Provider: HuggingFace", reply_markup=provider_menu()); return
    if d.startswith("hfm_"):
        k = d[4:]
        if k in HF_MODELS and HF_MODELS[k]["id"]:
            bot_data["cfg"]["hf_model_key"] = k
            bot_data["cfg"]["custom_hf_id"] = ""
            await save_data(); await q.answer(f"✅ {HF_MODELS[k]['label']}", show_alert=True)
            await q.edit_message_text("🤗 HF Models (updated):", reply_markup=hf_models_menu()); return

    if d in ("a_models","a_models_groq"):
        await q.edit_message_text("⚡ Select Groq Model:", reply_markup=groq_models_menu()); return
    if d == "a_models_or":
        await q.edit_message_text("🌐 Select OpenRouter Model:", reply_markup=or_models_menu()); return
    if d == "a_models_hf":
        await q.edit_message_text("🤗 Select HuggingFace Model:", reply_markup=hf_models_menu()); return

    if d.startswith("gm_"):
        k = d[3:]
        if k in GROQ_MODELS:
            bot_data["cfg"]["groq_model_key"] = k
            bot_data["cfg"]["custom_groq_id"] = ""
            await save_data(); await q.answer(f"✅ {GROQ_MODELS[k]['label']}", show_alert=True)
            await q.edit_message_text("⚡ Groq Models (updated):", reply_markup=groq_models_menu()); return

    if d.startswith("orm_"):
        k = d[4:]
        if k in OPENROUTER_MODELS:
            bot_data["cfg"]["or_model_key"] = k
            bot_data["cfg"]["custom_or_id"] = ""
            await save_data(); await q.answer(f"✅ {OPENROUTER_MODELS[k]['label']}", show_alert=True)
            await q.edit_message_text("🌐 OR Models (updated):", reply_markup=or_models_menu()); return

    if d == "set_custom_groq":
        ctx.user_data["await"] = "set_custom_groq"
        await q.edit_message_text(
            "🔑 Send your custom Groq model ID:\nExample: llama-3.1-8b-instant",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel",callback_data="a_provider")]])); return
    if d == "set_custom_or":
        ctx.user_data["await"] = "set_custom_or"
        await q.edit_message_text(
            "🔑 Send your custom OpenRouter model ID:\nExample: meta-llama/llama-3.3-70b-instruct:free",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel",callback_data="a_provider")]])); return
    if d == "set_custom_hf":
        ctx.user_data["await"] = "set_custom_hf"
        await q.edit_message_text(
            "🤗 Send your custom HuggingFace model ID:\nExample: IlyaGusev/gemma-2-2b-it-abliterated:featherless-ai\n\nGet model IDs from: huggingface.co/models",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel",callback_data="a_provider")]])); return
    if d == "clr_custom_hf":
        bot_data["cfg"]["custom_hf_id"] = ""
        await save_data(); await q.answer("✅ Custom HF ID cleared!", show_alert=True)
        await q.edit_message_text("🔗 Provider", reply_markup=provider_menu()); return
    if d == "clr_custom_groq":
        bot_data["cfg"]["custom_groq_id"] = ""
        await save_data(); await q.answer("✅ Custom Groq ID cleared!", show_alert=True)
        await q.edit_message_text("🔗 Provider", reply_markup=provider_menu()); return
    if d == "clr_custom_or":
        bot_data["cfg"]["custom_or_id"] = ""
        await save_data(); await q.answer("✅ Custom OR ID cleared!", show_alert=True)
        await q.edit_message_text("🔗 Provider", reply_markup=provider_menu()); return

    # ── SYSTEM PROMPT ──────────────────────────
    if d == "a_sysprompt":
        cfg  = bot_data.get("cfg",{}); p = cfg.get("system_prompt",""); prev = p[:200]+"..." if len(p)>200 else p
        await q.edit_message_text(
            f"⚙️ SYSTEM PROMPT\n━━━━━━━━━━━━━━━━━━━\n"
            f"Persona: {cfg.get('personality','default')}\nLength: {len(p)} chars\n\nPreview:\n{prev}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👁 View Full",          callback_data="ai_viewprompt")],
                [InlineKeyboardButton("✏️ Set Custom Prompt",  callback_data="ai_setprompt")],
                [InlineKeyboardButton("🎭 Personality Presets",callback_data="ai_pers")],
                [InlineKeyboardButton("🔄 Reset Default",      callback_data="ai_reset")],
                [InlineKeyboardButton("💬 Set Welcome Msg",    callback_data="a_setwelcome"),
                 InlineKeyboardButton("🔧 Maint Message",      callback_data="a_setmaintmsg")],
                [InlineKeyboardButton("⬅️ Back",               callback_data="a_main")],
            ])); return

    if d == "a_setwelcome":
        ctx.user_data["await"] = "set_welcome"
        cur = bot_data.get("welcome","")[:200]
        await q.edit_message_text(
            f"💬 Set Welcome Message\nVariables: {{name}} {{plan}} {{daily}} {{limit}}\n\nCurrent:\n{cur}\n\nSend new message:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel",callback_data="a_sysprompt")]])); return
    if d == "a_setmaintmsg":
        ctx.user_data["await"] = "set_maint_msg"
        cur = bot_data.get("maintenance_msg","")
        await q.edit_message_text(
            f"🔧 Set Maintenance Message\n\nCurrent:\n{cur}\n\nSend new message:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel",callback_data="a_sysprompt")]])); return

    # ── AGENT SETUP ────────────────────────────
    if d == "a_agent":
        cfg = bot_data.get("cfg",{}); enabled = cfg.get("agent_enabled",True)
        txt = (
            f"🧠 AGENT SYSTEM\n━━━━━━━━━━━━━━━━━━━\n"
            f"Status: {'✅ ENABLED' if enabled else '❌ DISABLED'}\n\n"
            "Tools Available:\n"
            "- web_search: Internet search\n"
            "- calculate: Math & conversions\n"
            "- run_python: Execute Python\n"
            "- get_weather: Live weather\n"
            "- analyze_task: Task planning\n\n"
            "Auto-triggers: search, weather, calculate, news, latest, find...\n\n"
            "User command: /agent <query>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Enable Agent" if not enabled else "❌ Disable Agent", callback_data="a_agent_toggle")],
            [InlineKeyboardButton("📝 Set Agent Prompt", callback_data="a_agent_prompt")],
            [InlineKeyboardButton("👁 View Agent Prompt",callback_data="a_agent_viewprompt")],
            [InlineKeyboardButton("🔄 Reset Agent Prompt",callback_data="a_agent_reset")],
            [InlineKeyboardButton("⬅️ Back", callback_data="a_main")],
        ])
        await q.edit_message_text(txt, reply_markup=kb); return

    if d == "a_agent_toggle":
        cur = bot_data.get("cfg",{}).get("agent_enabled",True)
        bot_data["cfg"]["agent_enabled"] = not cur
        await save_data(); status = "ENABLED" if not cur else "DISABLED"
        await q.answer(f"Agent {status}!", show_alert=True)
        await adm_cb(update, ctx); return

    if d == "a_agent_prompt":
        ctx.user_data["await"] = "set_agent_prompt"
        await q.edit_message_text("🧠 Send your custom Agent System Prompt now:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel",callback_data="a_agent")]])); return

    if d == "a_agent_viewprompt":
        p = bot_data.get("cfg",{}).get("agent_prompt",AGENT_SYSTEM_PROMPT)
        await q.edit_message_text(f"🧠 Agent Prompt:\n\n{p[:3800]}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back",callback_data="a_agent")]])); return

    if d == "a_agent_reset":
        bot_data["cfg"]["agent_prompt"] = AGENT_SYSTEM_PROMPT
        await save_data(); await q.answer("✅ Agent prompt reset!", show_alert=True)
        await q.edit_message_text("🧠 AGENT SYSTEM", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back",callback_data="a_agent")]])); return

    # ── BROADCAST & AD ─────────────────────────
    if d == "a_bcast":
        bs = bot_data.get("broadcast_stats",{})
        await q.edit_message_text(
            f"📢 BROADCAST\n━━━━━━━━━━━━━━━━━━━\nLast: Sent {bs.get('sent',0)} | Failed {bs.get('failed',0)}\n\nUse: /broadcast <message>",
            reply_markup=BACK); return
    if d == "a_ad":
        ad = bot_data.get("ad_stats",{})
        await q.edit_message_text(
            f"📣 ADVERTISE\n━━━━━━━━━━━━━━━━━━━\nSent: {ad.get('sent',0)} | Failed: {ad.get('failed',0)}\n\nUse: /advertise <text>",
            reply_markup=BACK); return

    # ── BAN & MUTE ─────────────────────────────
    if d == "a_ban":
        await q.edit_message_text(
            f"🚫 BAN SYSTEM\n━━━━━━━━━━━━━━━━━━━\nBanned: {len(bot_data.get('banned',[]))}\n\n"
            "/ban <id> | /unban <id> | /warn <id> (3=auto ban)",
            reply_markup=BACK); return
    if d == "a_mute":
        muted = bot_data.get("muted",{})
        lines = [f"🔇 MUTE SYSTEM\n━━━━━━━━━━━━━━━━━━━\nMuted: {len(muted)}\n"]
        for uid, info in list(muted.items())[:8]:
            u = bot_data.get("users",{}).get(uid,{})
            lines.append(f"{uid} | {u.get('name','?')} | until {info.get('until','')[:16]}")
        lines.append("\n/mute <id> <mins> | /unmute <id>")
        await q.edit_message_text("\n".join(lines), reply_markup=BACK); return

    # ── PREMIUM & CODES ────────────────────────
    if d == "a_prem":
        prem = bot_data.get("premium",{}); lims = bot_data.get("limits",{})
        lines = [f"💎 PREMIUM\n━━━━━━━━━━━━━━━━━━━\nActive: {len(prem)} | Free: {lims.get('free',20)}/day | Prem: {lims.get('prem',99999)}/day\n"]
        for uid, info in list(prem.items())[:8]:
            u = bot_data.get("users",{}).get(uid,{})
            exp = info.get("expiry","?")
            lines.append(f"💎 {uid} | {u.get('name','?')} | {'♾️' if exp=='permanent' else exp[:10]}")
        lines.append("\n/premium <id> <days> (0=perm) | /removepremium <id> | /setlimit free|prem <n>")
        await q.edit_message_text("\n".join(lines), reply_markup=BACK); return
    if d == "a_codes":
        codes = bot_data.get("codes",{}); active = [c for c,v in codes.items() if not v.get("used")]
        lines = [f"🎫 CODES\n━━━━━━━━━━━━━━━━━━━\nTotal:{len(codes)} Active:{len(active)}\n"]
        for c in active[:12]: lines.append(f"{c} — {codes[c].get('days','?')}d")
        if len(active)>12: lines.append(f"...+{len(active)-12} more")
        lines.append("\n/gencode <days> <amount> | /deletecode <code> | /redeeminfo")
        await q.edit_message_text("\n".join(lines)[:4000], reply_markup=BACK); return

    # ── FORCE SUB & FLOOD ──────────────────────
    if d == "a_fsub":
        fs = bot_data.get("force_sub")
        await q.edit_message_text(
            f"🔒 FORCE SUB\n━━━━━━━━━━━━━━━━━━━\nStatus: {'ON — '+fs if fs else 'OFF'}\n\n/forcesub @channel | /forcesub off",
            reply_markup=BACK); return
    if d == "a_flood":
        af = bot_data.get("antiflood",{})
        await q.edit_message_text(
            f"🛡 ANTIFLOOD\n━━━━━━━━━━━━━━━━━━━\nStatus: {'ON' if af.get('on') else 'OFF'}\n"
            f"Limit: {af.get('max',8)} msgs/{af.get('win',10)}s | Auto-mute: {af.get('mute',5)} min\n\n"
            "/antiflood on|off | /antiflood set <max> <secs> <mute_mins>",
            reply_markup=BACK); return

    # ── MEMORY & CHAT ──────────────────────────
    if d == "a_vchat":
        await q.edit_message_text(
            "💬 VIEW CHAT\n\nUse: /viewchat <user_id>\nShows last 15 messages.",
            reply_markup=BACK); return
    if d == "a_mem":
        await q.edit_message_text(
            "🧹 CLEAR MEMORY\n\n/clearmem <id> | /clearmemall | /clearchats",
            reply_markup=BACK); return

    # ── MAINTENANCE & RESTART ──────────────────
    if d == "a_maint":
        bot_data["maint"] = not bot_data.get("maint",False)
        await save_data(); s = "ON" if bot_data["maint"] else "OFF"
        await q.answer(f"Maintenance {s}", show_alert=True)
        await q.edit_message_text("🏠 Main Menu", reply_markup=main_menu()); return
    if d == "a_restart":
        bot_data["convos"] = {}; bot_data["flood"] = {}
        await save_data(); await q.answer("✅ Memory cleared!", show_alert=True)
        await q.edit_message_text("🏠 Main Menu", reply_markup=main_menu()); return

    # ── EXPORT ─────────────────────────────────
    if d == "a_export":
        users = bot_data.get("users",{})
        lines = [f"📋 EXPORT ({len(users)} users)\n━━━━━━━━━━━━━━━━━━━"]
        for uid, u in users.items():
            pl = "💎" if is_premium(int(uid)) else "🆓"
            st = "🚫" if is_banned(int(uid)) else ("🔇" if is_muted(int(uid)) else "✅")
            lines.append(f"{st}{pl} {uid} | {u.get('name','?')} @{u.get('username','—')} | {u.get('messages',0)}msgs ⚠️{u.get('warnings',0)}")
        for chunk in split_text("\n".join(lines)):
            await q.message.reply_text(chunk)
        await q.edit_message_text("📋 Export sent above.", reply_markup=BACK); return

    # ── DAILY REPORT ───────────────────────────
    if d == "a_daily":
        reset_today(); s = bot_data.get("stats",{}); users = bot_data.get("users",{})
        today = datetime.now().strftime("%Y-%m-%d")
        new   = sum(1 for u in users.values() if u.get("joined","")[:10]==today)
        await q.edit_message_text(
            f"📊 DAILY REPORT — {today}\n━━━━━━━━━━━━━━━━━━━\n"
            f"Messages: {s.get('today_messages',0)} | New Users: {new}\n"
            f"Tokens: {s.get('total_tokens',0)} | Agent: {s.get('agent_calls',0)}\n"
            f"Groq: {s.get('groq_calls',0)} calls | OR: {s.get('or_calls',0)} calls\n"
            f"Errors: Groq {s.get('groq_errors',0)} | OR {s.get('or_errors',0)}\n"
            f"Uptime: {uptime()}",
            reply_markup=BACK); return

    # ── PING & LOGS ────────────────────────────
    if d == "a_ping":
        t = time.time(); await q.answer("🏓")
        ms = int((time.time()-t)*1000)
        await q.edit_message_text(f"Ping: {ms}ms | Uptime: {uptime()}", reply_markup=BACK); return
    if d == "a_clrlogs":
        bot_data["chats"] = {}; await save_data()
        await q.answer("✅ Logs cleared!", show_alert=True)
        await q.edit_message_text("🏠 Main Menu", reply_markup=main_menu()); return

# ══════════════════════════════════════════════
# ADMIN TEXT (awaiting input)
# ══════════════════════════════════════════════
@admin_only
async def adm_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    aw = ctx.user_data.get("await"); text = update.message.text.strip()
    if not aw:
        await update.message.reply_text("Use /start to open admin panel.", reply_markup=main_menu()); return

    if aw == "set_prompt":
        bot_data["cfg"]["system_prompt"] = text; bot_data["cfg"]["personality"] = "custom"
        ctx.user_data.pop("await",None); await save_data()
        await update.message.reply_text(f"✅ Prompt updated! ({len(text)} chars)\n\nPreview:\n{text[:200]}", reply_markup=main_menu())

    elif aw == "set_welcome":
        bot_data["welcome"] = text; ctx.user_data.pop("await",None); await save_data()
        await update.message.reply_text(f"✅ Welcome message updated!\n\n{text[:200]}", reply_markup=main_menu())

    elif aw == "set_maint_msg":
        bot_data["maintenance_msg"] = text; ctx.user_data.pop("await",None); await save_data()
        await update.message.reply_text(f"✅ Maintenance message updated!\n\n{text[:200]}", reply_markup=main_menu())

    elif aw == "set_agent_prompt":
        bot_data["cfg"]["agent_prompt"] = text; ctx.user_data.pop("await",None); await save_data()
        await update.message.reply_text(f"✅ Agent prompt updated! ({len(text)} chars)", reply_markup=main_menu())

    elif aw == "set_custom_groq":
        bot_data["cfg"]["custom_groq_id"] = text.strip(); bot_data["cfg"]["provider"] = "groq"
        ctx.user_data.pop("await",None); await save_data()
        await update.message.reply_text(f"✅ Custom Groq model set: {text.strip()}", reply_markup=main_menu())

    elif aw == "set_custom_or":
        bot_data["cfg"]["custom_or_id"] = text.strip(); bot_data["cfg"]["provider"] = "openrouter"
        ctx.user_data.pop("await",None); await save_data()
        await update.message.reply_text(f"✅ Custom OR model set: {text.strip()}", reply_markup=main_menu())
    elif aw == "set_custom_hf":
        bot_data["cfg"]["custom_hf_id"] = text.strip(); bot_data["cfg"]["provider"] = "huggingface"
        ctx.user_data.pop("await",None); await save_data()
        await update.message.reply_text(
            "HuggingFace model set! Provider switched to HuggingFace.",
            reply_markup=main_menu()
        )

    else:
        ctx.user_data.pop("await",None)
        await update.message.reply_text("Use /start to open admin panel.", reply_markup=main_menu())

# ══════════════════════════════════════════════
# ADMIN COMMANDS
# ══════════════════════════════════════════════
@admin_only
async def adm_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /broadcast <message>"); return
    msg = " ".join(ctx.args)
    st  = await update.message.reply_text(f"📢 Sending to {len(bot_data.get('users',{}))} users...")
    s, f = await bcast_all(msg)
    bot_data["stats"]["total_broadcasts"] = bot_data["stats"].get("total_broadcasts",0)+1
    bot_data["broadcast_stats"] = {"sent":s,"failed":f}
    await save_data(); await st.edit_text(f"✅ Done! Sent:{s} | Failed:{f}")

@admin_only
async def adm_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /ban <id>"); return
    try: uid = int(ctx.args[0])
    except ValueError: await update.message.reply_text("Invalid ID."); return
    if uid not in [int(x) for x in bot_data.get("banned",[])]:
        bot_data["banned"].append(uid)
        bot_data["stats"]["total_bans"] = bot_data["stats"].get("total_bans",0)+1
    await save_data(); await update.message.reply_text(f"🚫 {uid} banned.")

@admin_only
async def adm_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /unban <id>"); return
    try: uid = int(ctx.args[0])
    except ValueError: await update.message.reply_text("Invalid ID."); return
    bot_data["banned"] = [x for x in bot_data.get("banned",[]) if int(x)!=uid]
    await save_data(); await update.message.reply_text(f"✅ {uid} unbanned.")

@admin_only
async def adm_warn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /warn <id>"); return
    try: uid = int(ctx.args[0])
    except ValueError: await update.message.reply_text("Invalid ID."); return
    u = get_user(uid); u["warnings"] = u.get("warnings",0)+1
    if u["warnings"] >= 3:
        if uid not in [int(x) for x in bot_data.get("banned",[])]: bot_data["banned"].append(uid)
        await save_data(); await update.message.reply_text(f"⚠️ {uid} — {u['warnings']} warns → AUTO BANNED!")
    else:
        await save_data(); await update.message.reply_text(f"⚠️ {uid} warned. {u['warnings']}/3")

@admin_only
async def adm_mute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args)<2: await update.message.reply_text("Usage: /mute <id> <mins>"); return
    try: uid,mins = int(ctx.args[0]),int(ctx.args[1])
    except ValueError: await update.message.reply_text("Invalid args."); return
    until = (datetime.now()+timedelta(minutes=mins)).isoformat()
    bot_data["muted"][str(uid)] = {"until":until,"reason":"admin"}
    bot_data["stats"]["total_mutes"] = bot_data["stats"].get("total_mutes",0)+1
    await save_data(); await update.message.reply_text(f"🔇 {uid} muted {mins} min.")

@admin_only
async def adm_unmute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /unmute <id>"); return
    bot_data["muted"].pop(str(ctx.args[0]),None); await save_data()
    await update.message.reply_text(f"✅ {ctx.args[0]} unmuted.")

@admin_only
async def adm_premium(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args)<2: await update.message.reply_text("Usage: /premium <id> <days> (0=perm)"); return
    try: uid,days = int(ctx.args[0]),int(ctx.args[1])
    except ValueError: await update.message.reply_text("Invalid args."); return
    exp = "permanent" if days==0 else (datetime.now()+timedelta(days=days)).isoformat()
    bot_data["premium"][str(uid)] = {"expiry":exp,"granted":datetime.now().isoformat()}
    await save_data(); await update.message.reply_text(f"💎 {uid} premium — {'permanent' if days==0 else str(days)+' days'}")

@admin_only
async def adm_remprem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /removepremium <id>"); return
    bot_data["premium"].pop(str(ctx.args[0]),None); await save_data()
    await update.message.reply_text(f"✅ Premium removed from {ctx.args[0]}")

@admin_only
async def adm_setlimit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args)<2: await update.message.reply_text("Usage: /setlimit free|prem <n>"); return
    plan = ctx.args[0].lower()
    try: n = int(ctx.args[1])
    except ValueError: await update.message.reply_text("Invalid number."); return
    if plan not in ("free","prem"): await update.message.reply_text("Use: free or prem"); return
    bot_data["limits"][plan] = n; await save_data()
    await update.message.reply_text(f"✅ {plan} limit → {n}/day")

@admin_only
async def adm_gencode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args)<2: await update.message.reply_text("Usage: /gencode <days> <amount>"); return
    try: days,amt = int(ctx.args[0]),min(int(ctx.args[1]),50)
    except ValueError: await update.message.reply_text("Invalid args."); return
    ab = string.ascii_uppercase+string.digits; codes = []
    for _ in range(amt):
        c = "DN-"+"".join(secrets.choice(ab) for _ in range(8))
        bot_data["codes"][c] = {"days":days,"used":False,"created":datetime.now().isoformat()}
        codes.append(c)
    await save_data()
    txt = f"🎫 {amt} code(s) — {days} days:\n\n" + "\n".join(f"`{c}`" for c in codes)
    await update.message.reply_text(txt[:4000], parse_mode=ParseMode.MARKDOWN)

@admin_only
async def adm_delcode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /deletecode <code>"); return
    c = ctx.args[0].upper()
    if c in bot_data.get("codes",{}):
        del bot_data["codes"][c]; await save_data()
        await update.message.reply_text(f"✅ Code {c} deleted.")
    else: await update.message.reply_text("Code not found.")

@admin_only
async def adm_redeeminfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    codes = bot_data.get("codes",{})
    if not codes: await update.message.reply_text("No codes yet."); return
    lines = ["🎫 All Codes:\n"]
    for c,v in codes.items():
        lines.append(f"{c} — {v.get('days','?')}d — {'Used' if v.get('used') else 'Active'}")
    for chunk in split_text("\n".join(lines)):
        await update.message.reply_text(chunk)

@admin_only
async def adm_forcesub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /forcesub @ch OR /forcesub off"); return
    if ctx.args[0].lower()=="off": bot_data["force_sub"]=None
    else: bot_data["force_sub"] = ctx.args[0] if ctx.args[0].startswith("@") else "@"+ctx.args[0]
    await save_data(); await update.message.reply_text(f"✅ Force sub → {bot_data['force_sub'] or 'OFF'}")

@admin_only
async def adm_antiflood(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /antiflood on|off|set <max> <win> <mute>"); return
    af = bot_data.setdefault("antiflood",{}); sub = ctx.args[0].lower()
    if sub=="on":    af["on"]=True;  await update.message.reply_text("✅ Antiflood ON.")
    elif sub=="off": af["on"]=False; await update.message.reply_text("✅ Antiflood OFF.")
    elif sub=="set" and len(ctx.args)>=4:
        try:
            af["max"]=int(ctx.args[1]); af["win"]=int(ctx.args[2]); af["mute"]=int(ctx.args[3])
            await update.message.reply_text(f"✅ {af['max']} msgs/{af['win']}s → mute {af['mute']}min")
        except ValueError: await update.message.reply_text("Invalid values.")
    await save_data()

@admin_only
async def adm_viewchat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /viewchat <id>"); return
    uid = str(ctx.args[0]); chats = bot_data.get("chats",{}).get(uid,[])
    if not chats: await update.message.reply_text("No history."); return
    lines = [f"Chat Log — {uid} (last 15)\n━━━━━━━━━━━━━━━━━━━"]
    for c in chats[-15:]:
        lines.append(f"\n{c.get('ts','')[:16]}\nUser: {c.get('user','')[:100]}\nAI: {c.get('ai','')[:100]}")
    for chunk in split_text("\n".join(lines)):
        await update.message.reply_text(chunk)

@admin_only
async def adm_clearmem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /clearmem <id>"); return
    bot_data["convos"].pop(str(ctx.args[0]),None); await save_data()
    await update.message.reply_text(f"✅ Memory cleared for {ctx.args[0]}")

@admin_only
async def adm_clearmemall(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_data["convos"]={};  await save_data(); await update.message.reply_text("✅ All memories cleared.")

@admin_only
async def adm_clearchats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_data["chats"]={}; await save_data(); await update.message.reply_text("✅ All chat logs cleared.")

@admin_only
async def adm_sysprompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /sysprompt <text>"); return
    p = " ".join(ctx.args); bot_data["cfg"]["system_prompt"]=p; bot_data["cfg"]["personality"]="custom"
    await save_data(); await update.message.reply_text(f"✅ Prompt updated! ({len(p)} chars)\n\n{p[:200]}")

@admin_only
async def adm_advertise(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: await update.message.reply_text("Usage: /advertise <text>"); return
    msg = " ".join(ctx.args); st = await update.message.reply_text("📣 Sending...")
    s,f = await bcast_all(msg,"📣 Advertisement")
    bot_data["ad_stats"]["sent"] = bot_data["ad_stats"].get("sent",0)+s
    bot_data["ad_stats"]["failed"] = bot_data["ad_stats"].get("failed",0)+f
    await save_data(); await st.edit_text(f"📣 Done! Sent:{s} | Failed:{f}")

@admin_only
async def adm_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t=time.time(); m=await update.message.reply_text("🏓")
    ms=int((time.time()-t)*1000); await m.edit_text(f"Ping: {ms}ms | Uptime: {uptime()}")

@admin_only
async def adm_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users = bot_data.get("users",{})
    lines = [f"USER EXPORT ({len(users)} users)\n━━━━━━━━━━━━━━━━━━━"]
    for uid,u in users.items():
        pl = "💎" if is_premium(int(uid)) else "🆓"
        st = "🚫" if is_banned(int(uid)) else ("🔇" if is_muted(int(uid)) else "✅")
        lines.append(f"{st}{pl} {uid} | {u.get('name','?')} @{u.get('username','—')} | {u.get('messages',0)}msgs")
    for chunk in split_text("\n".join(lines)):
        await update.message.reply_text(chunk)

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
    if ctx.args: await _redeem(update, uid, ctx.args[0].upper()); return
    if not await check_fsub(uid, update.get_bot()):
        await update.message.reply_text("🔒 Join our channel first!", reply_markup=fsub_kb()); return
    u = get_user(uid)
    u["name"] = update.effective_user.first_name or "User"
    u["username"] = update.effective_user.username
    u["last_active"] = datetime.now().isoformat()
    plan = "💎 Premium" if is_premium(uid) else "🆓 Free"
    daily = get_daily(uid); limit = get_limit(uid)
    welcome = bot_data.get("welcome","")
    try:
        text = welcome.format(name=u["name"],plan=plan,daily=daily,limit=limit if limit<99999 else "∞")
    except Exception:
        text = f"👋 Welcome {u['name']}! Plan: {plan} | {daily}/{limit if limit<99999 else '∞'}"
    await update.message.reply_text(text, reply_markup=USER_KB)
    await save_data()

async def usr_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_banned(update.effective_user.id): return
    has_key = bool(OPENROUTER_KEY or GROQ_API_KEY)
    await update.message.reply_text(
        "🤖 DarkNova AI — Commands\n━━━━━━━━━━━━━━━━━━━\n"
        "/start — Welcome\n/help — This list\n/reset — Clear memory\n"
        "/about — About bot\n/plan — Your plan\n/redeem <code> — Premium\n"
        "/contact — Admin\n/ping — Latency\n/speed — AI speed\n"
        "/model — Model info\n/agent <query> — AI Agent mode\n\n"
        "💬 Just type to chat!\n"
        "🔍 Auto-agent on: search, weather, calculate, news..."
    )

async def usr_about(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg = bot_data.get("cfg",{})
    await update.message.reply_text(
        "🤖 DarkNova AI Bot\n━━━━━━━━━━━━━━━━━━━\n"
        f"Provider: {cfg.get('provider','groq').upper()}\n"
        f"Persona: {cfg.get('personality','default')}\n"
        f"Features: Memory, Code/ZIP, Agent, Multilingual\n\n"
        "Built by @MrNewton_2\n"
        "Powered by Groq + OpenRouter"
    )

async def usr_plan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    plan = "💎 Premium" if is_premium(uid) else "🆓 Free"
    daily = get_daily(uid); limit = get_limit(uid)
    exp = ""
    if is_premium(uid):
        e = bot_data.get("premium",{}).get(str(uid),{}).get("expiry","?")
        exp = "\nPermanent" if e=="permanent" else f"\nExpires: {e[:10]}"
    await update.message.reply_text(
        f"📊 Your Plan\n━━━━━━━━━━━━━━━━━━━\n"
        f"Plan: {plan}{exp}\n"
        f"Today: {daily}/{limit if limit<99999 else '∞'}\n"
        f"Memory: {'40 msgs (48h)' if is_premium(uid) else 'Off — Upgrade!'}\n\n"
        "Use /redeem <code> to upgrade!"
    )

async def usr_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    if not is_premium(uid): await update.message.reply_text("⚠️ Memory is a 💎 Premium feature!"); return
    bot_data["convos"].pop(str(uid),None); await save_data()
    await update.message.reply_text("🧹 Memory cleared!")

async def usr_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📞 Contact\n\n@MrNewton_2\nAdmin ID: {ADMIN_ID}")

async def usr_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t=time.time(); m=await update.message.reply_text("🏓")
    ms=int((time.time()-t)*1000); await m.edit_text(f"Ping: {ms}ms")

async def usr_speed(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    m=await update.message.reply_text("Testing AI speed...")
    t=time.time(); r,_ = await call_groq(uid,"Reply: Speed OK")
    await m.edit_text(f"AI speed: {round(time.time()-t,2)}s\n{r}")

async def usr_model(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg = bot_data.get("cfg",{})
    provider = cfg.get("provider","groq").upper()
    provider_name = cfg.get("provider","groq").upper()
    agent_on = "ON" if cfg.get("agent_enabled",True) else "OFF"
    model_info = (
        "AI Info\n"
        "---\n"
        "Provider: " + provider_name + "\n"
        "Temp: " + str(cfg.get("temperature",0.9)) + "\n"
        "Max Tokens: " + str(cfg.get("max_tokens",4096)) + "\n"
        "Persona: " + cfg.get("personality","default") + "\n"
        "Agent: " + agent_on
    )
    await update.message.reply_text(model_info)

async def usr_agent_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_banned(uid): return
    if not ctx.args:
        await update.message.reply_text(
            "🤖 Agent Mode\n\nUsage: /agent <query>\n\n"
            "Examples:\n"
            "• /agent weather in Mumbai\n"
            "• /agent latest AI news\n"
            "• /agent calculate 15% of 8500\n"
            "• /agent steps to build a todo app\n"
            "• /agent run: print sum of 1 to 100"
        ); return
    if get_daily(uid) >= get_limit(uid):
        await update.message.reply_text("⚠️ Daily limit reached! Upgrade to Premium."); return
    query = " ".join(ctx.args)
    thinking = await update.message.reply_text(f"🤖 Agent working...\nQuery: {query[:60]}")
    response = await run_agent(uid, query)
    try: await thinking.delete()
    except Exception: pass
    for chunk in split_text(response):
        try: await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        except Exception: await update.message.reply_text(chunk)
    u = get_user(uid); u["messages"] = u.get("messages",0)+1
    bot_data["stats"]["total_messages"] = bot_data["stats"].get("total_messages",0)+1
    inc_daily(uid); await save_data()

async def _redeem(update: Update, uid: int, code: str):
    codes = bot_data.get("codes",{})
    if code not in codes: await update.message.reply_text("❌ Invalid code."); return
    if codes[code].get("used"): await update.message.reply_text("❌ Already used."); return
    days = codes[code].get("days",30)
    exp  = "permanent" if days==0 else (datetime.now()+timedelta(days=days)).isoformat()
    bot_data["premium"][str(uid)] = {"expiry":exp,"granted":datetime.now().isoformat()}
    codes[code]["used"]=True; codes[code]["used_by"]=uid
    await save_data()
    await update.message.reply_text(f"✅ Redeemed! Premium — {'permanent' if days==0 else str(days)+' days'}!")

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
        code = q.data[5:]
        try: await q.message.reply_text(f"`{code}`", parse_mode=ParseMode.MARKDOWN)
        except Exception: await q.message.reply_text(code)
        await q.answer("✅ Sent!")

async def usr_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    uid  = update.effective_user.id
    text = update.message.text.strip()

    if is_banned(uid): await update.message.reply_text("🚫 You are banned."); return
    if bot_data.get("maint"): await update.message.reply_text(bot_data.get("maintenance_msg","🔧 Maintenance...")); return
    if not await check_fsub(uid, update.get_bot()):
        await update.message.reply_text("🔒 Join channel first!", reply_markup=fsub_kb()); return
    if is_muted(uid):
        info=bot_data["muted"].get(str(uid),{}); until=info.get("until","")
        rem=""
        if until:
            try: rem=f" ({int((datetime.fromisoformat(until)-datetime.now()).total_seconds()//60)} min left)"
            except Exception: pass
        await update.message.reply_text(f"🔇 You are muted{rem}."); return
    if check_flood(uid): apply_mute(uid); await update.message.reply_text("🛡 Flooding! Muted."); return

    u = get_user(uid)
    u["name"] = update.effective_user.first_name or "User"
    u["username"] = update.effective_user.username
    u["last_active"] = datetime.now().isoformat()

    shortcuts = {
        "💬 Chat":    lambda: update.message.reply_text("💬 Just type!"),
        "🧹 Reset":   lambda: usr_reset(update, ctx),
        "ℹ️ About":   lambda: usr_about(update, ctx),
        "📊 Plan":    lambda: usr_plan(update, ctx),
        "🎫 Redeem":  lambda: update.message.reply_text("Use /redeem <code>"),
        "📞 Contact": lambda: usr_contact(update, ctx),
    }
    if text in shortcuts: await shortcuts[text](); return

    if update.message.chat.type in ["group","supergroup"]:
        me = await update.get_bot().get_me()
        is_mention = f"@{me.username}" in text
        is_reply   = (update.message.reply_to_message and
                      update.message.reply_to_message.from_user and
                      update.message.reply_to_message.from_user.id == me.id)
        if not is_mention and not is_reply: return

    if get_daily(uid) >= get_limit(uid):
        await update.message.reply_text(
            f"⚠️ Daily limit reached! ({get_daily(uid)}/{get_limit(uid)})\n💎 Upgrade to Premium!"); return

    await update.message.chat.send_action("typing")

    cfg = bot_data.get("cfg",{})
    use_agent = wants_agent(text) and cfg.get("agent_enabled",True)

    if use_agent:
        thinking = await update.message.reply_text("🤖 Searching & processing...")
        response = await run_agent(uid, text)
        try: await thinking.delete()
        except Exception: pass
        for chunk in split_text(response):
            try: await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
            except Exception: await update.message.reply_text(chunk)
    else:
        response, _ = await call_groq(uid, text)
        if has_code(response):
            blocks, clean = extract_blocks(response)
            clean = clean.replace("\n[CODE]\n","").strip()
            if needs_zip(blocks):
                files = {}; used = set()
                for i,(lang,code) in enumerate(blocks):
                    fname = detect_fname(lang,i,response)
                    if fname in used:
                        base,ext = (fname.rsplit(".",1) if "." in fname else (fname,"txt"))
                        fname = f"{base}_{i+1}.{ext}"
                    used.add(fname); files[fname] = code
                flist = "\n".join(f"  {f}" for f in files)
                files["README.md"] = (
                    "# Project\nGenerated by DarkNova AI\nBuilt by @MrNewton_2\n\n## Files\n\n"
                    + "\n".join(f"- {f}" for f in files if f!="README.md")
                )
                all_langs = [b[0].lower() for b in blocks]
                ptype = "Web Project" if "html" in all_langs else \
                        "Python Project" if any(l in all_langs for l in ["py","python"]) else \
                        "JS Project" if any(l in all_langs for l in ["js","javascript"]) else "Code Project"
                if clean:
                    for chunk in split_text(clean): await update.message.reply_text(chunk)
                pname = re.sub(r"[^a-z0-9_]","",text[:25].lower().replace(" ","_")) or "project"
                await update.message.reply_document(
                    document=make_zip(files), filename=f"{pname}.zip",
                    caption=f"📦 {ptype}\n\n{flist}\n  README.md\n\nBuilt by @MrNewton_2"
                )
            else:
                if clean:
                    for chunk in split_text(clean): await update.message.reply_text(chunk)
                for lang,code in blocks:
                    lang = lang or "text"; safe = code[:190].replace("`","'")
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📋 Copy Code",callback_data=f"copy_{safe}")]])
                    for chunk in split_text(f"```{lang}\n{code}\n```",4000):
                        try: await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
                        except Exception: await update.message.reply_text(chunk)
        else:
            for chunk in split_text(response): await update.message.reply_text(chunk)

    u["messages"] = u.get("messages",0)+1
    bot_data["stats"]["total_messages"] = bot_data["stats"].get("total_messages",0)+1
    bot_data["stats"]["today_messages"] = bot_data["stats"].get("today_messages",0)+1
    inc_daily(uid); reset_today(); await save_data()

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
            "status": "ok", "uptime": uptime(),
            "users": len(bot_data.get("users",{})),
            "msgs":  bot_data.get("stats",{}).get("total_messages",0),
            "provider": bot_data.get("cfg",{}).get("provider","groq"),
        }),
        content_type="application/json"
    )

async def start_web():
    from aiohttp.web import Application, AppRunner, TCPSite
    app = Application(); app.router.add_get("/", health)
    runner = AppRunner(app); await runner.setup()
    await TCPSite(runner,"0.0.0.0",PORT).start()
    logger.info(f"Web server :{PORT}")

# ══════════════════════════════════════════════
# BUILD APPS
# ══════════════════════════════════════════════
def build_admin() -> Application:
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    for cmd, fn in [
        ("start",adm_start),("broadcast",adm_broadcast),("ban",adm_ban),("unban",adm_unban),
        ("warn",adm_warn),("mute",adm_mute),("unmute",adm_unmute),("premium",adm_premium),
        ("removepremium",adm_remprem),("setlimit",adm_setlimit),("gencode",adm_gencode),
        ("deletecode",adm_delcode),("redeeminfo",adm_redeeminfo),("forcesub",adm_forcesub),
        ("antiflood",adm_antiflood),("viewchat",adm_viewchat),("clearmem",adm_clearmem),
        ("clearmemall",adm_clearmemall),("clearchats",adm_clearchats),("export",adm_export),
        ("sysprompt",adm_sysprompt),("advertise",adm_advertise),("ping",adm_ping),
    ]:
        app.add_handler(CommandHandler(cmd, fn))
    app.add_handler(CallbackQueryHandler(adm_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, adm_text))
    app.add_error_handler(on_error)
    return app

def build_user() -> Application:
    app = Application.builder().token(USER_BOT_TOKEN).build()
    for cmd, fn in [
        ("start",usr_start),("help",usr_help),("about",usr_about),("plan",usr_plan),
        ("reset",usr_reset),("contact",usr_contact),("ping",usr_ping),("speed",usr_speed),
        ("model",usr_model),("redeem",usr_redeem),("agent",usr_agent_cmd),
    ]:
        app.add_handler(CommandHandler(cmd, fn))
    app.add_handler(CallbackQueryHandler(usr_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, usr_msg))
    app.add_error_handler(on_error)
    return app

# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════
async def main():
    global user_bot_obj
    if not all([ADMIN_BOT_TOKEN, USER_BOT_TOKEN]):
        logger.error("Missing ADMIN_BOT_TOKEN or USER_BOT_TOKEN!"); return
    if not GROQ_API_KEY and not OPENROUTER_KEY and not HF_TOKEN:
        logger.error("Need at least one: GROQ_API_KEY, OPENROUTER_API_KEY, or HF_TOKEN!"); return

    load_data()
    bot_data["start_time"] = datetime.now().isoformat()
    user_bot_obj = Bot(token=USER_BOT_TOKEN)

    if GROQ_API_KEY:   logger.info("Groq API: configured")
    if OPENROUTER_KEY: logger.info("OpenRouter API: configured")
    if HF_TOKEN:       logger.info("HuggingFace API: configured")
    logger.info(f"Default provider: {bot_data['cfg'].get('provider','groq').upper()}")
    logger.info("Starting DarkNova AI Bot v5.0...")

    admin_app = build_admin()
    user_app  = build_user()

    await start_web()
    asyncio.create_task(periodic_save())

    await admin_app.initialize()
    await user_app.initialize()

    logger.info("Clearing old webhooks...")
    await admin_app.bot.delete_webhook(drop_pending_updates=True)
    await user_app.bot.delete_webhook(drop_pending_updates=True)

    await admin_app.start()
    await user_app.start()
    await admin_app.updater.start_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
    await user_app.updater.start_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

    logger.info("✅ DarkNova v5.0 — Both bots running!")
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        await save_data()
        try: await user_bot_obj.close()
        except Exception: pass
        await admin_app.updater.stop(); await user_app.updater.stop()
        await admin_app.stop(); await user_app.stop()
        await admin_app.shutdown(); await user_app.shutdown()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())
