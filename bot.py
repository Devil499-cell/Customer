import logging
import asyncio
import aiohttp
import sqlite3
import re
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8676061817:AAFDWfE9Y7dkNfHQ6_h3GHsp8dgTgKDmwaY"
ADMIN_ID = 8934836047
UPI_ID = "shashixpatel@fam"
API_CONFIG = {
    "phone": "https://patel-number-api.vercel.app/number?number=",
    "tg": "https://felix-info-x-bot.onrender.com/key=felix67&tg=",
}
BOMBER_API = "https://all-sigma-pad-api-damo-5-day.vercel.app/api"
BOMBER_KEY = "RAJAN99"
PHOTO_URL = "https://t.me/photo_for_bot45/2"
BANNER_FILE_ID = None

LINE = "═" * 20

E_STAR   = '⭐'
E_SEARCH = '🌟'
E_MONEY  = '💰'
E_GIFT   = '🎁'
E_CHECK  = '✅'
E_CROSS  = '❌'
E_WARN   = '⚠️'
E_PHONE  = '📱'
E_FAMILY = '👨‍👩‍👧‍👦'
E_ARROW  = '➡️'
E_ADMIN  = '⚙️'
E_USERS  = '👥'
E_BROAD  = '📢'
E_CROWN  = '👑'
E_BELL   = '🔔'
E_TG     = '✈️'

def BQ(text):
    return f"<blockquote>{text}</blockquote>"

FONT_MAP = {
    'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ꜰ','g':'ɢ','h':'ʜ',
    'i':'ɪ','j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ',
    'q':'ǫ','r':'ʀ','s':'s','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x',
    'y':'ʏ','z':'ᴢ',
    'A':'ᴀ','B':'ʙ','C':'ᴄ','D':'ᴅ','E':'ᴇ','F':'ꜰ','G':'ɢ','H':'ʜ',
    'I':'ɪ','J':'ᴊ','K':'ᴋ','L':'ʟ','M':'ᴍ','N':'ɴ','O':'ᴏ','P':'ᴘ',
    'Q':'ǫ','R':'ʀ','S':'s','T':'ᴛ','U':'ᴜ','V':'ᴠ','W':'ᴡ','X':'x',
    'Y':'ʏ','Z':'ᴢ',
}
def m(text):
    return ''.join(FONT_MAP.get(c, c) for c in str(text))

class StyledKeyboardButton(KeyboardButton):
    def __init__(self, text, style=None, **kwargs):
        super().__init__(text, **kwargs)
        self._style = style
    def to_dict(self, recursive=True):
        d = super().to_dict(recursive=recursive)
        if self._style:
            d['style'] = self._style
        return d

def KB(text, style=None, **kwargs):
    try:
        return StyledKeyboardButton(text, style=style, **kwargs)
    except Exception:
        return KeyboardButton(text, **kwargs)

class StyledInlineKeyboardButton(InlineKeyboardButton):
    def __init__(self, text, style=None, **kwargs):
        super().__init__(text, **kwargs)
        self._style = 'success' if style == 'active' else style
    def to_dict(self, recursive=True):
        d = super().to_dict(recursive=recursive)
        if self._style:
            d['style'] = self._style
        return d

def IKB(text, style=None, **kwargs):
    try:
        return StyledInlineKeyboardButton(text, style=style, **kwargs)
    except Exception:
        try:
            return InlineKeyboardButton(text, **kwargs)
        except Exception:
            if 'url' in kwargs:
                return InlineKeyboardButton(text, url=kwargs['url'])
            return InlineKeyboardButton(text, callback_data=kwargs.get('callback_data', 'noop'))

ADMINS = {ADMIN_ID}
FORCE_CHANNELS = []

WAITING_NUMBER       = "WAITING_NUMBER"
WAITING_BOMBER_INPUT = "WAITING_BOMBER_INPUT"
WAITING_GIFT_CODE    = "WAITING_GIFT_CODE"
WAITING_BROADCAST    = "WAITING_BROADCAST"
WAITING_ADD_BAL_ID   = "WAITING_ADD_BAL_ID"
WAITING_ADD_BAL_AMT  = "WAITING_ADD_BAL_AMT"
WAITING_REM_BAL_ID   = "WAITING_REM_BAL_ID"
WAITING_REM_BAL_AMT  = "WAITING_REM_BAL_AMT"
WAITING_GIFT_CODE_C  = "WAITING_GIFT_CODE_C"
WAITING_GIFT_AMT     = "WAITING_GIFT_AMT"
WAITING_SECURE_NUM   = "WAITING_SECURE_NUM"
WAITING_UNSECURE_NUM = "WAITING_UNSECURE_NUM"
WAITING_ADD_ADMIN    = "WAITING_ADD_ADMIN"
WAITING_ADD_CHANNEL  = "WAITING_ADD_CHANNEL"
WAITING_REM_CHANNEL  = "WAITING_REM_CHANNEL"
WAITING_REM_ADMIN    = "WAITING_REM_ADMIN"
WAITING_ADD_PHONE_API   = "WAITING_ADD_PHONE_API"
WAITING_ADD_TG_API      = "WAITING_ADD_TG_API"
WAITING_PAY_UTR      = "WAITING_PAY_UTR"
WAITING_SCREENSHOT   = "WAITING_SCREENSHOT"
WAITING_PLAN_SELECT  = "WAITING_PLAN_SELECT"
WAITING_TG_INPUT     = "WAITING_TG_INPUT"

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT,
        balance REAL DEFAULT 0, premium_until TEXT,
        referred_by INTEGER, last_bonus TEXT, join_date TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS gift_codes (
        code TEXT PRIMARY KEY, per_amount REAL, max_users INTEGER,
        created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS gift_claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT, user_id INTEGER, claimed_at TEXT,
        UNIQUE(code, user_id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        plan TEXT, utr TEXT, screenshot_file_id TEXT,
        status TEXT DEFAULT 'pending', created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS protected_numbers (
        number TEXT PRIMARY KEY)""")
    conn.commit(); conn.close()

def get_user(uid):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    row = c.fetchone(); conn.close(); return row

def ensure_user(uid, username):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id,username,join_date) VALUES (?,?,?)",
              (uid, username, datetime.now().isoformat()))
    conn.commit(); conn.close()

def update_balance(uid, amt):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, uid))
    conn.commit(); conn.close()

def set_premium(uid, days):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT premium_until FROM users WHERE user_id=?", (uid,))
    row = c.fetchone(); now = datetime.now(); base = now
    if row and row[0]:
        try:
            cur = datetime.fromisoformat(row[0])
            if cur > now: base = cur
        except: pass
    new_until = base + timedelta(days=days)
    c.execute("UPDATE users SET premium_until=? WHERE user_id=?", (new_until.isoformat(), uid))
    conn.commit(); conn.close()

def is_premium(uid):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT premium_until FROM users WHERE user_id=?", (uid,))
    row = c.fetchone(); conn.close()
    if row and row[0]:
        try: return datetime.fromisoformat(row[0]) > datetime.now()
        except: return False
    return False

def premium_days_left(uid):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT premium_until FROM users WHERE user_id=?", (uid,))
    row = c.fetchone(); conn.close()
    if row and row[0]:
        try:
            delta = datetime.fromisoformat(row[0]) - datetime.now()
            return max(0, delta.days)
        except: return 0
    return 0

def get_total_users():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]; conn.close(); return count

def get_all_user_ids():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    ids = [r[0] for r in c.fetchall()]; conn.close(); return ids

def get_refer_count(uid):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (uid,))
    n = c.fetchone()[0]; conn.close(); return n

def load_protected():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT number FROM protected_numbers")
    rows = c.fetchall(); conn.close()
    return set(r[0] for r in rows)

def add_protected(number):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO protected_numbers (number) VALUES (?)", (number,))
    conn.commit(); conn.close()

def remove_protected(number):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("DELETE FROM protected_numbers WHERE number=?", (number,))
    conn.commit(); conn.close()

def main_keyboard(uid):
    buttons = [
        [KB(f"🔍 {m('Search')}", style="primary")],
        [KB(f"💰 {m('Balance')}", style="primary"), KB(f"🎁 {m('Refer Earn')}", style="primary")],
        [KB(f"🎉 {m('Bonus')}", style="primary"), KB(f"❓ {m('Help')}", style="primary")],
        [KB(f"🎁 {m('Claim Gift')}", style="success"), KB(f"👑 {m('Buy Premium')}", style="primary")],
        [KB(f"🏡 {m('Home')}", style="primary")],
    ]
    if uid in ADMINS:
        buttons.append([KB(f"⚙️ {m('Admin Panel')}", style="danger")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)

def search_keyboard():
    return ReplyKeyboardMarkup([
        [KB(f"{E_PHONE} {m('Search Number')}", style="primary")],
        [KB(f"{E_TG} {m('Telegram to Num')}", style="primary")],
        [KB(f"💣 {m('Bomber')}", style="danger")],
        [KB(f"🏡 {m('Home')}", style="success")],
    ], resize_keyboard=True)

def cancel_keyboard():
    return ReplyKeyboardMarkup(
        [[KB(f"🏡 {m('Home')}", style="danger")]],
        resize_keyboard=True
    )

def plan_keyboard():
    return ReplyKeyboardMarkup([
        [KB(f"🎄 {m('1 Day')} — Rs.5", style="primary")],
        [KB(f"😎 {m('1 Week')} — Rs.19", style="success")],
        [KB(f"🗓 {m('2 Weeks')} — Rs.35", style="success")],
        [KB(f"👑 {m('permanet unlimited')} — Rs.299", style="danger")],
        [KB(f"🏡 {m('Home')}", style="danger")],
    ], resize_keyboard=True)

def admin_keyboard():
    return ReplyKeyboardMarkup([
        [KB(f"{E_BROAD} {m('Broadcast')}", style="success"),      KB(f"{E_USERS} {m('Total Users')}", style="primary")],
        [KB(f"➕ {m('Add Balance')}", style="success"),            KB(f"➖ {m('Remove Balance')}", style="primary")],
        [KB(f"🔒 {m('Secure Number')}", style="success"),          KB(f"🔓 {m('Unsecure Number')}", style="primary")],
        [KB(f"👉 {m('Add Admin')}", style="success"),              KB(f"🗑 {m('Remove Admin')}", style="primary")],
        [KB(f"📡 {m('Add Channel')}", style="success"),            KB(f"❌ {m('Remove Channel')}", style="primary")],
        [KB(f"📞 {m('Add Phone Api')}", style="success"),          KB(f"🗑️ {m('Remove Phone Api')}", style="primary")],
        [KB(f"{E_TG} {m('Add Tg Api')}", style="success"),         KB(f"🗑️ {m('Remove Tg Api')}", style="primary")],
        [KB(f"{E_GIFT} {m('Create Gift Code')}", style="danger")],
        [KB(f"🏡 {m('Home')}", style="danger")],
    ], resize_keyboard=True)

async def fetch_number_data(number):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_CONFIG['phone']}{number}"
            logger.info(f"Fetching: {url}")
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"API Response for {number}: {data}")
                    return data
                else:
                    logger.error(f"API returned status {resp.status}")
                    return None
    except Exception as e:
        logger.error(f"API Error: {e}")
        return None

async def fetch_tg_data(query):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_CONFIG['tg']}{query}"
            logger.info(f"Fetching TG: {url}")
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"TG API Response: {data}")
                    return data
                else:
                    logger.error(f"TG API returned status {resp.status}")
                    return None
    except Exception as e:
        logger.error(f"TG API Error: {e}")
        return None

async def fetch_bomber(number, count):
    try:
        if count < 1: count = 1
        if count > 100: count = 100
        term = f"{number}|{count}"
        params = {"key": BOMBER_KEY, "type": "BOMBER", "term": term}
        async with aiohttp.ClientSession() as s:
            async with s.get(BOMBER_API, params=params, timeout=aiohttp.ClientTimeout(total=30)) as r:
                txt = await r.text()
                logger.info(f"Bomber {term} -> {r.status} {txt[:300]}")
                try:
                    return r.status, await r.json()
                except:
                    return r.status, {"raw": txt}
    except Exception as e:
        logger.error(f"Bomber error: {e}")
        return None, None

def clean_address(addr):
    if not addr or addr in ("null", "N/A", "None"):
        return "N/A"
    addr = str(addr).replace("!", " ")
    addr = re.sub(r"\s+", " ", addr).strip()
    return addr

def format_number_response(data_json, query_number):
    records = data_json.get("records", [])
    total_records = data_json.get("total_records", len(records))

    if not records:
        return BQ(
            f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('No Data Found!')}</b>\n"
            f"\n📱 {m('Number')}: {query_number}\n"
            f"\n╭━━[ 𓃵 𝐏𝐀𝐓𝐄𝐋 𓃵 ]━━╮"
        )

    lines = []
    lines.append(f"📱 {m('NUMBER')}: {query_number}")
    lines.append(f"📊 {m('TOTAL RECORDS')}: {total_records}")
    lines.append("")

    for idx, record in enumerate(records, 1):
        name = record.get("NAME", "N/A")
        fname = record.get("fname", "N/A")
        alt = record.get("alt", "N/A")
        circle = record.get("circle", "N/A")
        address = clean_address(record.get("ADDRESS", "N/A"))
        record_id = record.get("id", "N/A")
        email = record.get("email", "N/A")
        mobile = record.get("MOBILE", "N/A")

        lines.append(f"📌 {m('RECORD')} #{idx}")
        lines.append(f"👤 {m('NAME')}: {name}")
        if mobile and mobile not in ("N/A", "None", "null"):
            lines.append(f"📲 {m('MOBILE')}: {mobile}")
        if fname and fname not in ("N/A", "None", "null"):
            lines.append(f"👨 {m('FATHER')}: {fname}")
        if record_id and record_id not in ("N/A", "None", "null"):
            lines.append(f"🆔 {m('AADHAAR')}: {record_id}")
        if alt and alt not in ("N/A", "None", "null"):
            lines.append(f"📞 {m('ALTERNATE')}: {alt}")
        if circle and circle not in ("N/A", "None", "null"):
            lines.append(f"📡 {m('OPERATOR')}: {circle}")
        if address and address != "N/A":
            lines.append(f"📍 {m('ADDRESS')}: {address}")
        if email and email not in ("N/A", "None", "null"):
            lines.append(f"✉️ {m('EMAIL')}: {email}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("╭━━[ 𓃵 𝐏𝐀𝐓𝐄𝐋 𓃵 ]━━╮")
    lines.append(f"👨‍💻 {m('API BY PATEL')}")
    lines.append(f"🕐 {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")

    body = "\n".join(lines)

    MAX = 3900
    if len(body) > MAX:
        cut = body[:MAX].rsplit("\n", 1)[0]
        body = cut + f"\n\n… {m('truncated')} ({total_records} {m('records total')})"

    return BQ(body)

def format_tg_response(data_json, query):
    if data_json.get("msg") != "Details fetched" and not data_json.get("number"):
        return BQ(f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('No Data Found!')}</b>")

    number = data_json.get("number", "N/A")
    tg_id_raw = data_json.get("tg_id", "N/A")
    username = data_json.get("username", query)
    country = data_json.get("country", "N/A")
    country_code = data_json.get("country_code", "N/A")
    rt = data_json.get("response_time_ms", "N/A")

    tg_id_clean = str(tg_id_raw).split()[0] if tg_id_raw else "N/A"

    dev = "@KINGITACHI18"

    output = BQ(
        f"<tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji>\n"
        f"✈️ {m('TELEGRAM TO NUMBER')}\n"
        f"<tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji>\n\n"
        f"├<tg-emoji emoji-id='6239790794719370356'>🔍</tg-emoji> {m('Query')}   : {query}\n"
        f"└<tg-emoji emoji-id='6138914494111291882'>🤩</tg-emoji> {m('Record')}  : {m('Found')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"├🆔 {m('Telegram ID')} : {tg_id_clean}\n"
        f"├<tg-emoji emoji-id='6122805733936342496'>👤</tg-emoji> {m('Username')}    : {username}\n"
        f"├📱 {m('Phone')}       : {number}\n"
        f"├🌐 {m('Country')}     : {country} ({country_code})\n"
        f"├⚡ {m('Latency')}     : {rt} ms\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"├ {m('Developer')} : {dev}\n"
        f"<tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji><tg-emoji emoji-id='6316321369562814897'>➖</tg-emoji>"
    )
    return output

async def warm_banner(app):
    global BANNER_FILE_ID
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(PHOTO_URL, timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status != 200:
                    logger.error(f"banner fetch HTTP {r.status}")
                    return
                ct = r.headers.get("Content-Type", "")
                if "image" not in ct:
                    logger.error(f"banner content-type {ct} — not an image")
                    return
                data = await r.read()
        path = "/tmp/banner_cache.jpg"
        with open(path, "wb") as f:
            f.write(data)
        msg = await app.bot.send_photo(chat_id=ADMIN_ID, photo=open(path, "rb"))
        BANNER_FILE_ID = msg.photo[-1].file_id
        logger.info(f"banner cached file_id={BANNER_FILE_ID}")
        try:
            import os as _os
            _os.remove(path)
        except: pass
    except Exception as e:
        logger.error(f"warm_banner error: {e}")

async def send_menu(update, context):
    user = update.effective_user
    if update.effective_chat.type != "private":
        return
    ensure_user(user.id, user.username or user.first_name)

    context.user_data.clear()
    kb = main_keyboard(user.id)

    row = get_user(user.id)
    bal = row[2] if row else 0
    refers = get_refer_count(user.id)
    prem = is_premium(user.id)
    status_word = "PREMIUM" if prem else "FREE USER"
    me = await context.bot.get_me()

    name_display = user.first_name or "USER"

    msg = BQ(
        f"╭── [  ꜱ ʏ ꜱ ᴛ ᴇ ᴍ  ɪ ɴ ɪ ᴛ ɪ ᴀ ᴛ ᴇ ᴅ  ]\n"
        f"│\n"
        f"├──  ⇛ ʜᴇʏ — ͟͞͞༯{name_display.upper()}\n"
        f"├──  ⇛ ɪ ᴀᴍ @{me.username}\n"
        f"├──  ⇛ ᴍᴏꜱᴛ ᴩᴏᴡᴇʀꜰᴜʟʟ ᴏꜱɪɴᴛ\n"
        f"│\n"
        f"├── [  ʏ ᴏ ᴜ ʀ  ꜱ ᴛ ᴀ ᴛ ᴜ ꜱ ]\n"
        f"├──  ⇛ Cʀᴇᴅɪᴛ :- {bal}\n"
        f"├──  ⇛ Rᴇꜰᴇʀꜱ :- {refers}\n"
        f"├──  ⇛ Sᴛᴀᴛᴜꜱ :- {status_word}\n"
        f"├──  ⇛ Dᴇᴠʟᴏᴩᴇʀ :- @SOCIALBANNERR\n"
        f"│\n"
        f"╰── ᴩʀᴇꜱꜱ ʜᴇʟᴩ ᴛᴏ ᴇxᴩʟᴏʀᴇ ᴍᴏʀᴇ ᴄᴏᴍᴍᴀɴᴅꜱ !"
    )

    banner = BANNER_FILE_ID or PHOTO_URL
    try:
        await update.effective_message.reply_photo(
            photo=banner, caption=msg, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.error(f"reply_photo failed: {e}")
        await update.effective_message.reply_text(msg, reply_markup=kb, parse_mode="HTML")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type in ("group", "supergroup"):
        await update.effective_message.reply_text(
            BQ(
                f"<tg-emoji emoji-id='6156937559864778682'>👋</tg-emoji> <b>{m('Luffy Osient Bot')}</b>\n\n"
                f"{LINE}\n"
                f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> {m('Bot added to group successfully!')}\n"
                f"<tg-emoji emoji-id='6159208403563454586'>💬</tg-emoji> {m('Start me in private to use all features')}:\n"
                f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> @{(await context.bot.get_me()).username}\n"
                f"{LINE}"
            ),
            parse_mode="HTML"
        )
        return

    ensure_user(user.id, user.username or user.first_name)
    if context.args:
        ref = context.args[0]
        if ref.isdigit() and int(ref) != user.id:
            conn = sqlite3.connect("bot.db")
            c = conn.cursor()
            c.execute("SELECT referred_by FROM users WHERE user_id=?", (user.id,))
            row = c.fetchone()
            if row and row[0] is None:
                c.execute("UPDATE users SET referred_by=? WHERE user_id=?", (int(ref), user.id))
                conn.commit()
                update_balance(int(ref), 3)
                try:
                    await context.bot.send_message(int(ref),
                        BQ(
                            f"<tg-emoji emoji-id='6158989888512334518'>🎁</tg-emoji> <b>{m('New Referral!')}</b>\n\n"
                            f"{LINE}\n"
                            f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> {m('Someone joined via your link!')}\n"
                            f"🤑 {m('+3 Points Added!')}\n"
                            f"{LINE}"
                        ), parse_mode="HTML")
                except: pass
            conn.close()
    await send_menu(update, context)

async def group_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_user = await context.bot.get_me()
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == bot_user.id:
                await update.message.reply_text(
                    BQ(
                        f"╔══════════════════════╗\n"
                        f"║  🤖 <b>LUFFY OSIENT BOT</b>  ║\n"
                        f"╚══════════════════════╝\n\n"
                        f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> <b>Bot Group mein Add Ho Gaya!</b>\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"<tg-emoji emoji-id='6156660766402421161'>🔍</tg-emoji> <b>GROUP COMMANDS</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"\n"
                        f"<tg-emoji emoji-id='6159161068728885766'>📱</tg-emoji> <b>Number Search:</b>\n"
                        f"┗━ <code>/search 9876543210</code>\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"<tg-emoji emoji-id='6159208403563454586'>💬</tg-emoji> <b>Private Chat (Full Features):</b>\n"
                        f"┗━ 👉 @{bot_user.username}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"\n⚡ <i>Powered by Luffy Bot</i>"
                    ),
                    parse_mode="HTML"
                )

async def inline_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    data = query.data

    if data.startswith("approve_"):
        if user.id not in ADMINS: return
        pay_id = int(data.split("_")[1])
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id, plan FROM payments WHERE id=?", (pay_id,))
        row = c.fetchone()
        if row:
            uid, plan_name = row
            plan_days = {"1 Day": 1, "1 Week": 7, "2 Weeks": 14, "1 Month": 30}
            days = plan_days.get(plan_name, 1)
            set_premium(uid, days)
            c.execute("UPDATE payments SET status='approved' WHERE id=?", (pay_id,))
            conn.commit()
            try:
                await context.bot.send_message(uid,
                    BQ(
                        f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> <b>{m('Payment Approved!')}</b>\n\n"
                        f"{LINE}\n"
                        f"<tg-emoji emoji-id='6156660766402421161'>⭐</tg-emoji> {m('Premium Activated!')}\n"
                        f"📦 {m('Plan')}: <b>{m(plan_name)}</b>\n"
                        f"🔥 {m('Enjoy Unlimited Search!')}\n"
                        f"{LINE}"
                    ), parse_mode="HTML")
            except: pass
            try:
                old = query.message.caption or query.message.text or ""
                new_text = old + f"\n\n{LINE}\n✅ <b>APPROVED by Admin</b>"
                if query.message.caption:
                    await query.message.edit_caption(new_text, parse_mode="HTML")
                else:
                    await query.message.edit_text(new_text, parse_mode="HTML")
            except: pass
        conn.close()

    elif data.startswith("reject_"):
        if user.id not in ADMINS: return
        pay_id = int(data.split("_")[1])
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM payments WHERE id=?", (pay_id,))
        row = c.fetchone()
        if row:
            uid = row[0]
            c.execute("UPDATE payments SET status='rejected' WHERE id=?", (pay_id,))
            conn.commit()
            try:
                await context.bot.send_message(uid,
                    BQ(
                        f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('Payment Rejected!')}</b>\n\n"
                        f"{LINE}\n"
                        f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> {m('Payment not verified.')}\n"
                        f"<tg-emoji emoji-id='6159208403563454586'>💬</tg-emoji> {m('Contact admin for help.')}\n"
                        f"{LINE}"
                    ), parse_mode="HTML")
            except: pass
            try:
                old = query.message.caption or query.message.text or ""
                new_text = old + f"\n\n{LINE}\n❌ <b>REJECTED by Admin</b>"
                if query.message.caption:
                    await query.message.edit_caption(new_text, parse_mode="HTML")
                else:
                    await query.message.edit_text(new_text, parse_mode="HTML")
            except: pass
        conn.close()

async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    text = (update.message.text or "").strip()

    if chat.type in ("group", "supergroup"):
        bot_user = await context.bot.get_me()
        if text in ["/start", f"/start@{bot_user.username}"]:
            await update.message.reply_text(
                BQ(
                    f"╔══════════════════════╗\n"
                    f"║  🤖 <b>LUFFY OSIENT BOT</b>  ║\n"
                    f"╚══════════════════════╝\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"<tg-emoji emoji-id='6156660766402421161'>🔍</tg-emoji> <b>GROUP COMMANDS</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"\n"
                    f"<tg-emoji emoji-id='6159161068728885766'>📱</tg-emoji> <b>Number Search:</b>\n"
                    f"┗━ <code>/search 9876543210</code>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"<tg-emoji emoji-id='6159208403563454586'>💬</tg-emoji> <b>Private Chat (Full Features):</b>\n"
                    f"┗━ 👉 @{bot_user.username}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"\n⚡ <i>Powered by Luffy Bot</i>"
                ), parse_mode="HTML")
        return

    ensure_user(user.id, user.username or user.first_name)

    state = context.user_data.get("state")

    if text == f"🏡 {m('Home')}":
        await send_menu(update, context); return

    if not state:
        if text == f"🔍 {m('Search')}":
            msg = BQ(
                f"<tg-emoji emoji-id='6156660766402421161'>🔍</tg-emoji> <b>{m('Search Menu')}</b>\n\n"
                f"{LINE}\n"
                f"<tg-emoji emoji-id='6159161068728885766'>📱</tg-emoji> {m('Search Number')} — {m('Single number info')}\n"
                f"<tg-emoji emoji-id='6156937559864778682'>✈️</tg-emoji> {m('Telegram to Num')} — {m('Get phone from TG ID/username')}\n"
                f"<tg-emoji emoji-id='6156660766402421161'>💣</tg-emoji> {m('Bomber')} — {m('SMS/Call flood (abuse)')}\n"
                f"{LINE}\n\n"
                f"👇 {m('Choose an option below')}"
            )
            try:
                await update.message.reply_photo(
                    photo=BANNER_FILE_ID or PHOTO_URL, caption=msg,
                    reply_markup=search_keyboard(), parse_mode="HTML")
            except Exception as e:
                logger.error(f"reply_photo search failed: {e}")
                await update.message.reply_text(msg, reply_markup=search_keyboard(), parse_mode="HTML")

        elif text == f"📱 {m('Search Number')}":
            context.user_data["state"] = WAITING_NUMBER
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6156660766402421161'>🔍</tg-emoji> <b>{m('Number Search')}</b>\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6159161068728885766'>📱</tg-emoji> {m('Send 10 digit number')}:\n\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Format: 9876543210')}\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> {m('No spaces | No +91 | 10 digits only')}"
                ),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"✈️ {m('Telegram to Num')}":
            context.user_data["state"] = WAITING_TG_INPUT
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6156937559864778682'>✈️</tg-emoji> <b>{m('Telegram to Number')}</b>\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Send Telegram ID or username')}:\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Example: @drouv or 8501177393')}\n"
                    f"{LINE}"
                ),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"💣 {m('Bomber')}":
            context.user_data["state"] = WAITING_BOMBER_INPUT
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6156660766402421161'>💣</tg-emoji> <b>{m('BOMBER')}</b>\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6159161068728885766'>📱</tg-emoji> {m('Send number and count')}:\n\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Format')}: 7948845515|10\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Count range')}: 1 - 100\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Cost')}: 1 {m('credit per run')}\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> {m('Abuse carries legal consequence. Yours.')}"
                ),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"💰 {m('Balance')}":
            row = get_user(user.id)
            bal = row[2] if row else 0
            days = premium_days_left(user.id)
            prem = f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> {m(str(days) + ' Days Left')}" if days > 0 else f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> {m('Not Premium')}"
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6158943747678674305'>💰</tg-emoji> <b>{m('Your Balance')}</b>\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('User ID')}: {user.id}\n"
                    f"💵 {m('Balance')}: <b>{bal} {m('Points')}</b>\n"
                    f"<tg-emoji emoji-id='6287034086355639532'>👑</tg-emoji> {m('Premium')}: {prem}\n"
                    f"{LINE}"
                ),
                reply_markup=main_keyboard(user.id), parse_mode="HTML")

        elif text == f"🎁 {m('Refer Earn')}":
            me = await context.bot.get_me()
            ref_link = f"https://t.me/{me.username}?start={user.id}"
            row = get_user(user.id)
            bal = row[2] if row else 0
            refs = get_refer_count(user.id)
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6158989888512334518'>🎁</tg-emoji> <b>{m('Refer & Earn')}</b>\n\n"
                    f"{LINE}\n"
                    f"🤑 {m('Earn')} <b>3 {m('Points')}</b> {m('per referral!')}\n\n"
                    f"🔗 {m('Your Referral Link')}:\n"
                    f"{ref_link}\n\n"
                    f"<tg-emoji emoji-id='6158943747678674305'>💰</tg-emoji> {m('Total Balance')}: <b>{bal} {m('Points')}</b>\n"
                    f"<tg-emoji emoji-id='6159105792499785038'>👥</tg-emoji> {m('Total Refers')}: <b>{refs}</b>\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6159169740267855509'>🔔</tg-emoji> {m('Share & Earn!')}"
                ),
                reply_markup=main_keyboard(user.id), parse_mode="HTML")

        elif text == f"❓ {m('Help')}":
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6158951427080199970'>❓</tg-emoji> <b>{m('How To Use Bot')}</b>\n\n"
                    f"{LINE}\n\n"
                    f"<tg-emoji emoji-id='6156660766402421161'>🔍</tg-emoji> <b>{m('Search Number')}</b>\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Send 10 digit number')}\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('No +91 | No Spaces')}\n\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>✈️</tg-emoji> <b>{m('Telegram to Num')}</b>\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Send @username or numeric ID')}\n\n"
                    f"<tg-emoji emoji-id='6156660766402421161'>💣</tg-emoji> <b>{m('Bomber')}</b>\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Send number|count  e.g. 7879954664|10')}\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Cost 1 credit per run')}\n\n"
                    f"{LINE}\n\n"
                    f"<tg-emoji emoji-id='6158943747678674305'>💰</tg-emoji> <b>{m('Balance')}</b>\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Check points & premium status')}\n\n"
                    f"{LINE}\n\n"
                    f"<tg-emoji emoji-id='6158989888512334518'>🎁</tg-emoji> <b>{m('Refer & Earn')}</b>\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Share link = +3 points per join')}\n\n"
                    f"{LINE}\n\n"
                    f"<tg-emoji emoji-id='6159121997411395585'>🎉</tg-emoji> <b>{m('Daily Bonus')}</b>\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Claim 10 points every 24 hours')}\n\n"
                    f"{LINE}\n\n"
                    f"<tg-emoji emoji-id='6159155528221072436'>🎁</tg-emoji> <b>{m('Claim Gift')}</b>\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Enter gift code from admin')}\n\n"
                    f"{LINE}\n\n"
                    f"<tg-emoji emoji-id='6156660766402421161'>⭐</tg-emoji> <b>{m('Buy Premium')}</b>\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Unlimited search access')}\n\n"
                    f"{LINE}"
                ),
                reply_markup=main_keyboard(user.id), parse_mode="HTML")

        elif text == f"🎉 {m('Bonus')}":
            row = get_user(user.id)
            last_bonus = row[5] if row else None
            now = datetime.now()
            can_claim = True; hrs = 0; mins = 0
            if last_bonus:
                try:
                    last_dt = datetime.fromisoformat(last_bonus)
                    diff = (now - last_dt).total_seconds()
                    if diff < 86400:
                        can_claim = False
                        rem = 86400 - diff
                        hrs = int(rem // 3600); mins = int((rem % 3600) // 60)
                except: pass
            if can_claim:
                conn = sqlite3.connect("bot.db")
                c = conn.cursor()
                c.execute("UPDATE users SET balance=balance+10, last_bonus=? WHERE user_id=?",
                          (now.isoformat(), user.id))
                conn.commit(); conn.close()
                await update.message.reply_text(
                    BQ(
                        f"<tg-emoji emoji-id='6159121997411395585'>🎉</tg-emoji> <b>{m('Daily Bonus Claimed!')}</b>\n\n"
                        f"{LINE}\n"
                        f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> {m('+10 Points Added!')}\n"
                        f"<tg-emoji emoji-id='6159169740267855509'>🔔</tg-emoji> {m('Come back in 24 hours!')}\n"
                        f"{LINE}"
                    ),
                    reply_markup=main_keyboard(user.id), parse_mode="HTML")
            else:
                await update.message.reply_text(
                    BQ(
                        f"⏳ <b>{m('Already Claimed!')}</b>\n\n"
                        f"{LINE}\n"
                        f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> {m('Next bonus in')}: <b>{m(str(hrs))}h {m(str(mins))}m</b>\n"
                        f"{LINE}"
                    ),
                    reply_markup=main_keyboard(user.id), parse_mode="HTML")

        elif text == f"🎁 {m('Claim Gift')}":
            context.user_data["state"] = WAITING_GIFT_CODE
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6159155528221072436'>🎁</tg-emoji> <b>{m('Claim Gift Code')}</b>\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6158989888512334518'>🎁</tg-emoji> {m('Enter your gift code')}:\n"
                    f"{LINE}"
                ),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"👑 {m('Buy Premium')}":
            context.user_data["state"] = WAITING_PLAN_SELECT
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6156660766402421161'>⭐</tg-emoji> <b>{m('Buy Premium')}</b>\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6159223405884219526'>✨</tg-emoji> <b>{m('Premium Benefits')}:</b>\n\n"
                    f"⚡ {m('UNLIMITED SEARCH')}\n"
                    f"🔥 {m('INSTANT RESULTS')}\n"
                    f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> {m('NO DELAY')}\n"
                    f"🌐 {m('24/7 WORKING ON BOT')}\n"
                    f"{LINE}\n\n"
                    f"<tg-emoji emoji-id='6287034086355639532'>👑</tg-emoji> <b>{m('Choose Your Plan Dear')}:</b>"
                ),
                reply_markup=plan_keyboard(), parse_mode="HTML")

        elif text == f"⚙️ {m('Admin Panel')}":
            if user.id not in ADMINS:
                await update.message.reply_text(BQ(f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> {m('Access Denied!')}")); return
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6159118767595986018'>⚙️</tg-emoji> <b>{m('Admin Panel')}</b>\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6138914494111291882'>🤩</tg-emoji> {m('Welcome Admin!')} 👑\n"
                    f"{LINE}"
                ),
                reply_markup=admin_keyboard(), parse_mode="HTML")

        elif text == f"📢 {m('Broadcast')}" and user.id in ADMINS:
            context.user_data["state"] = WAITING_BROADCAST
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6159069693299662043'>📢</tg-emoji> {m('Send broadcast message')}:"),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"👥 {m('Total Users')}" and user.id in ADMINS:
            total = get_total_users()
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6159105792499785038'>👥</tg-emoji> <b>{m('Total Users')}: {total}</b>"),
                reply_markup=admin_keyboard(), parse_mode="HTML")

        elif text == f"➕ {m('Add Balance')}" and user.id in ADMINS:
            context.user_data["state"] = WAITING_ADD_BAL_ID
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6287149066925121984'>➕</tg-emoji> {m('Send User ID')}:"),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"➖ {m('Remove Balance')}" and user.id in ADMINS:
            context.user_data["state"] = WAITING_REM_BAL_ID
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6287149066925121984'>➖</tg-emoji> {m('Send User ID')}:"),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"{E_GIFT} {m('Create Gift Code')}" and user.id in ADMINS:
            context.user_data["state"] = WAITING_GIFT_CODE_C
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6158989888512334518'>🎁</tg-emoji> {m('Send gift code text')}:"),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"🔒 {m('Secure Number')}" and user.id in ADMINS:
            context.user_data["state"] = WAITING_SECURE_NUM
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6158957891005980158'>🔒</tg-emoji> {m('Send number to protect')}:"),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"🔓 {m('Unsecure Number')}" and user.id in ADMINS:
            context.user_data["state"] = WAITING_UNSECURE_NUM
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6158957891005980158'>🔓</tg-emoji> {m('Send number to unprotect')}:"),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"👉 {m('Add Admin')}" and user.id in ADMINS:
            context.user_data["state"] = WAITING_ADD_ADMIN
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('Send User ID to add as admin')}:"),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"📡 {m('Add Channel')}" and user.id in ADMINS:
            context.user_data["state"] = WAITING_ADD_CHANNEL
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6158774792255184370'>📡</tg-emoji> {m('Send channel username e.g. @channel')}:"),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"❌ {m('Remove Channel')}" and user.id in ADMINS:
            if len(FORCE_CHANNELS) == 0:
                await update.message.reply_text(BQ(f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> {m('No channels added!')}"), reply_markup=admin_keyboard(), parse_mode="HTML")
            else:
                ch_list = "\n".join(f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {ch}" for ch in FORCE_CHANNELS)
                context.user_data["state"] = WAITING_REM_CHANNEL
                await update.message.reply_text(
                    BQ(
                        f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('Remove Channel')}</b>\n\n{LINE}\n{m('Current Channels')}:\n{ch_list}\n\n{LINE}\n{m('Send channel username to remove')}:"
                    ),
                    reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"🗑 {m('Remove Admin')}" and user.id in ADMINS:
            admin_list = "\n".join(f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {a}" for a in ADMINS if a != ADMIN_ID)
            if not admin_list:
                await update.message.reply_text(BQ(f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> {m('No extra admins added!')}"), reply_markup=admin_keyboard(), parse_mode="HTML")
            else:
                context.user_data["state"] = WAITING_REM_ADMIN
                await update.message.reply_text(
                    BQ(
                        f"<tg-emoji emoji-id='6159076625376876979'>🗑</tg-emoji> <b>{m('Remove Admin')}</b>\n\n{LINE}\n{m('Current Admins')}:\n{admin_list}\n\n{LINE}\n{m('Send User ID to remove')}:"
                    ),
                    reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"📞 {m('Add Phone Api')}" and user.id in ADMINS:
            context.user_data["state"] = WAITING_ADD_PHONE_API
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6159161068728885766'>📞</tg-emoji> <b>{m('Add Phone API')}</b>\n\n"
                    f"{LINE}\n"
                    f"🔗 {m('Current API')}:\n{API_CONFIG['phone']}\n\n"
                    f"{LINE}\n"
                    f"✏️ {m('Send new Phone API URL')}:"
                ),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"🗑️ {m('Remove Phone Api')}" and user.id in ADMINS:
            API_CONFIG["phone"] = "https://luffy-number-info-api.onrender.com/num?q="
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> <b>{m('Phone API Reset!')}</b>\n\n"
                    f"{LINE}\n"
                    f"🔗 {m('Reset to default API')}\n"
                    f"{LINE}"
                ),
                reply_markup=admin_keyboard(), parse_mode="HTML")

        elif text == f"✈️ {m('Add Tg Api')}" and user.id in ADMINS:
            context.user_data["state"] = WAITING_ADD_TG_API
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6156937559864778682'>✈️</tg-emoji> <b>{m('Add TG API')}</b>\n\n"
                    f"{LINE}\n"
                    f"🔗 {m('Current API')}:\n{API_CONFIG['tg']}\n\n"
                    f"{LINE}\n"
                    f"✏️ {m('Send new TG API URL')}:"
                ),
                reply_markup=cancel_keyboard(), parse_mode="HTML")

        elif text == f"🗑️ {m('Remove Tg Api')}" and user.id in ADMINS:
            API_CONFIG["tg"] = "https://osint.invalidayushh.workers.dev/tg?key=free-hai&q="
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> <b>{m('TG API Reset!')}</b>\n\n"
                    f"{LINE}\n"
                    f"🔗 {m('Reset to default API')}\n"
                    f"{LINE}"
                ),
                reply_markup=admin_keyboard(), parse_mode="HTML")
        return

    if state == WAITING_BOMBER_INPUT:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)

        raw = text.strip()
        if "|" in raw:
            npart, cpart = raw.split("|", 1)
        else:
            npart, cpart = raw, "10"
        number = re.sub(r"\D", "", npart)
        if len(number) > 10: number = number[-10:]
        if len(number) != 10:
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('Invalid Number!')}</b>\n\n"
                    f"{LINE}\n⚠️ {m('10 digits required')}\n{LINE}"
                ),
                reply_markup=main_keyboard(user.id), parse_mode="HTML"); return
        try:
            count = int(re.sub(r"\D", "", cpart) or "10")
        except:
            count = 10
        if count < 1: count = 1
        if count > 100: count = 100

        protected = load_protected()
        if number in protected or f"+91{number}" in protected:
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6158957891005980158'>🔒</tg-emoji> <b>{m('Protected Number!')}</b>"),
                reply_markup=main_keyboard(user.id), parse_mode="HTML"); return

        prem = is_premium(user.id)
        if not prem:
            row = get_user(user.id)
            bal = row[2] if row else 0
            if bal < 1:
                await update.message.reply_text(
                    BQ(
                        f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> <b>{m('No Access!')}</b>\n\n"
                        f"{LINE}\n"
                        f"<tg-emoji emoji-id='6158943747678674305'>💰</tg-emoji> {m('Bomber costs 1 credit')}\n"
                        f"<tg-emoji emoji-id='6287034086355639532'>👑</tg-emoji> {m('Buy Premium for unlimited')}\n"
                        f"{LINE}"
                    ),
                    reply_markup=main_keyboard(user.id), parse_mode="HTML"); return

        msg = await update.message.reply_text(
            BQ(f"💣 {m('Activating Bomber')}…\n\n📱 {number}\n🔢 {count}\n\n⏳ {m('Please wait')}…"),
            parse_mode="HTML")
        await asyncio.sleep(0.5)

        status, data = await fetch_bomber(number, count)

        if not prem:
            update_balance(user.id, -1)

        await msg.delete()

        if status == 200 and data and data.get("success", True) is not False:
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> <b>{m('Bomber Activated')}</b>\n\n"
                    f"{LINE}\n"
                    f"📱 {m('Target')}: <code>{number}</code>\n"
                    f"🔢 {m('Count')}: <b>{count}</b>\n"
                    f"💣 {m('Status')}: {m('Delivered')}\n"
                    f"💰 {m('Charged')}: <b>1</b> {m('credit')}\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> {m('Abuse carries legal consequence. Yours.')}"
                ),
                reply_markup=main_keyboard(user.id), parse_mode="HTML")
        else:
            if not prem:
                update_balance(user.id, +1)
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('Bomber Failed')}</b>\n\n"
                    f"{LINE}\n"
                    f"{m('API')}: {status}\n"
                    f"{m('Response')}: {str(data)[:200]}\n"
                    f"💰 {m('Credit refunded')}\n"
                    f"{LINE}"
                ),
                reply_markup=main_keyboard(user.id), parse_mode="HTML")
        return

    if state == WAITING_PLAN_SELECT:
        plans = {
            f"🎄 {m('1 Day')} — Rs.5":   ("1 Day",   1, "Rs.5"),
            f"😎 {m('1 Week')} — Rs.19":  ("1 Week",  7, "Rs.19"),
            f"🗓 {m('2 Weeks')} — Rs.35": ("2 Weeks", 14, "Rs.35"),
            f"👑 {m('permanet unlimited')} — Rs.299": ("1 Month", 30, "Rs.299"),
        }
        plan = plans.get(text)
        if plan:
            context.user_data["plan"] = plan
            context.user_data["state"] = WAITING_PAY_UTR
            await update.message.reply_text(
                BQ(
                    f"💳 <b>{m('Payment Details')}</b>\n\n"
                    f"{LINE}\n"
                    f"📦 {m('Plan')}: <b>{m(plan[0])}</b>\n"
                    f"<tg-emoji emoji-id='6158943747678674305'>💰</tg-emoji> {m('Amount')}: <b>{plan[2]}</b>\n"
                    f"{LINE}\n\n"
                    f"<tg-emoji emoji-id='6159105792499785038'>🇮🇳</tg-emoji> {m('UPI ID')}:\n"
                    f"{UPI_ID}\n\n"
                    f"{LINE}\n"
                    f"📸 {m('After payment send Screenshot + UTR')}\n\n"
                    f"❗ {m('Send UTR number first')}:"
                ),
                reply_markup=cancel_keyboard(), parse_mode="HTML")
        elif text == f"🏡 {m('Home')}":
            await send_menu(update, context)
        return

    if state == WAITING_TG_INPUT:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)
        query = text.strip()
        prem = is_premium(user.id)
        if not prem:
            row = get_user(user.id)
            bal = row[2] if row else 0
            if bal < 1:
                await update.message.reply_text(
                    BQ(
                        f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> <b>{m('No Access!')}</b>\n\n"
                        f"{LINE}\n"
                        f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> {m('No balance & No premium')}\n"
                        f"<tg-emoji emoji-id='6158943747678674305'>💰</tg-emoji> {m('Each search costs 1 point')}\n"
                        f"<tg-emoji emoji-id='6287034086355639532'>👑</tg-emoji> {m('Or buy Premium for unlimited!')}\n"
                        f"{LINE}"
                    ),
                    reply_markup=main_keyboard(user.id), parse_mode="HTML"); return
            update_balance(user.id, -1)

        msg = await update.message.reply_text(BQ(f"✈️ {m('Searching TG data')}..."), parse_mode="HTML")
        await asyncio.sleep(0.4)
        await msg.edit_text(BQ(f"⚡ {m('Fetching details')}..."), parse_mode="HTML")
        await asyncio.sleep(0.4)
        await msg.edit_text(BQ(f"🌐 {m('Connecting to server')}..."), parse_mode="HTML")
        await asyncio.sleep(0.4)

        data = await fetch_tg_data(query)
        if data:
            await msg.delete()
            success = (data.get("msg") == "Details fetched") or bool(data.get("number")) or data.get("success", False)
            if success:
                formatted = format_tg_response(data, query)
                await update.message.reply_text(formatted, reply_markup=main_keyboard(user.id), parse_mode="HTML")
            else:
                await update.message.reply_text(
                    BQ(
                        f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('No Data Found!')}</b>\n\n{LINE}\n{m('TG ID/username not found.')}\n{LINE}"
                    ),
                    reply_markup=main_keyboard(user.id), parse_mode="HTML")
        else:
            await msg.edit_text(
                BQ(
                    f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> <b>{m('Server Error!')}</b>\n\n{LINE}\n{m('Try again later.')}\n{LINE}"
                ),
                parse_mode="HTML")
        return

    if state == WAITING_NUMBER:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)
        number = text.replace(" ", "").replace("+91", "").replace("-", "")
        if not number.isdigit() or len(number) != 10:
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('Invalid Number!')}</b>\n\n"
                    f"{LINE}\n⚠️ {m('Send exactly 10 digits | No +91')}\n{LINE}"
                ),
                reply_markup=main_keyboard(user.id), parse_mode="HTML"); return

        protected = load_protected()
        if number in protected or f"+91{number}" in protected:
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6158957891005980158'>🔒</tg-emoji> <b>{m('Protected Number!')}</b>\n\n"
                    f"{LINE}\n🛡️ {m('This number is protected by Owner')}\n{LINE}"
                ),
                reply_markup=main_keyboard(user.id), parse_mode="HTML"); return

        prem = is_premium(user.id)
        if not prem:
            row = get_user(user.id)
            bal = row[2] if row else 0
            if bal < 1:
                await update.message.reply_text(
                    BQ(
                        f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> <b>{m('No Access!')}</b>\n\n"
                        f"{LINE}\n"
                        f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> {m('No balance & No premium')}\n"
                        f"<tg-emoji emoji-id='6158943747678674305'>💰</tg-emoji> {m('Each search costs 1 point')}\n"
                        f"<tg-emoji emoji-id='6287034086355639532'>👑</tg-emoji> {m('Or buy Premium for unlimited!')}\n"
                        f"{LINE}"
                    ),
                    reply_markup=main_keyboard(user.id), parse_mode="HTML"); return
            update_balance(user.id, -1)

        msg = await update.message.reply_text(BQ(f"<tg-emoji emoji-id='6239790794719370356'>🔍</tg-emoji> {m('Searching Number')}..."), parse_mode="HTML")
        await asyncio.sleep(0.4)
        await msg.edit_text(BQ(f"⚡ {m('Fetching data')}..."), parse_mode="HTML")
        await asyncio.sleep(0.4)
        await msg.edit_text(BQ(f"🌐 {m('Connecting to server')}..."), parse_mode="HTML")
        await asyncio.sleep(0.4)

        data = await fetch_number_data(number)
        if data:
            await msg.delete()
            if data.get("success", False):
                if data.get("records"):
                    out = format_number_response(data, number)
                    await update.message.reply_text(out, reply_markup=main_keyboard(user.id), parse_mode="HTML")
                else:
                    await update.message.reply_text(
                        BQ(
                            f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('No Data Found!')}</b>\n\n{LINE}\n{m('Number not in database.')}\n{LINE}"
                        ),
                        reply_markup=main_keyboard(user.id), parse_mode="HTML")
            else:
                await update.message.reply_text(
                    BQ(
                        f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('No Data Found!')}</b>\n\n{LINE}\n{m('Number not in database.')}\n{LINE}"
                    ),
                    reply_markup=main_keyboard(user.id), parse_mode="HTML")
        else:
            await msg.edit_text(
                BQ(
                    f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> <b>{m('Server Error!')}</b>\n\n{LINE}\n{m('Try again later.')}\n{LINE}"
                ),
                parse_mode="HTML")

    elif state == WAITING_GIFT_CODE:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)
        code = text.upper()
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        c.execute("SELECT per_amount, max_users FROM gift_codes WHERE code=?", (code,))
        row = c.fetchone()
        if not row:
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('Invalid Gift Code!')}</b>"),
                reply_markup=main_keyboard(user.id), parse_mode="HTML")
        else:
            per_amount, max_users = row
            c.execute("SELECT id FROM gift_claims WHERE code=? AND user_id=?", (code, user.id))
            already = c.fetchone()
            if already:
                await update.message.reply_text(
                    BQ(
                        f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('Already Claimed!')}</b>\n\n{LINE}\n{m('You already used this code.')}\n{LINE}"
                    ),
                    reply_markup=main_keyboard(user.id), parse_mode="HTML")
            else:
                c.execute("SELECT COUNT(*) FROM gift_claims WHERE code=?", (code,))
                claimed_count = c.fetchone()[0]
                if claimed_count >= max_users:
                    await update.message.reply_text(
                        BQ(
                            f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('Code Expired!')}</b>\n\n{LINE}\n{m('Max users limit reached.')}\n{LINE}"
                        ),
                        reply_markup=main_keyboard(user.id), parse_mode="HTML")
                else:
                    c.execute("INSERT INTO gift_claims (code, user_id, claimed_at) VALUES (?,?,?)",
                              (code, user.id, datetime.now().isoformat()))
                    conn.commit()
                    update_balance(user.id, per_amount)
                    remaining = max_users - claimed_count - 1
                    await update.message.reply_text(
                        BQ(
                            f"🎉 <b>{m('Gift Code Claimed!')}</b>\n\n"
                            f"{LINE}\n"
                            f"🤑 {m('+' + str(int(per_amount)) + ' Points Added!')}\n"
                            f"<tg-emoji emoji-id='6159105792499785038'>👥</tg-emoji> {m('Remaining slots')}: <b>{remaining}</b>\n"
                            f"{LINE}"
                        ),
                        reply_markup=main_keyboard(user.id), parse_mode="HTML")
        conn.close()

    elif state == WAITING_PAY_UTR:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data["utr"] = text
        context.user_data["state"] = WAITING_SCREENSHOT
        await update.message.reply_text(
            BQ(f"📸 <b>{m('Now send payment screenshot')}:</b>"),
            reply_markup=cancel_keyboard(), parse_mode="HTML")

    elif state == WAITING_BROADCAST and user.id in ADMINS:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)
        all_ids = get_all_user_ids()
        sent = 0
        for uid in all_ids:
            try:
                await context.bot.send_message(uid,
                    BQ(
                        f"<tg-emoji emoji-id='6159069693299662043'>📢</tg-emoji> <b>{m('Broadcast')}</b>\n\n{LINE}\n{text}\n{LINE}"
                    ), parse_mode="HTML")
                sent += 1
            except: pass
        await update.message.reply_text(
            BQ(f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> {m('Sent to')} <b>{sent}</b> {m('users!')}"),
            reply_markup=admin_keyboard(), parse_mode="HTML")

    elif state == WAITING_ADD_BAL_ID and user.id in ADMINS:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data["tid"] = text
        context.user_data["state"] = WAITING_ADD_BAL_AMT
        await update.message.reply_text(BQ(f"<tg-emoji emoji-id='6287149066925121984'>➕</tg-emoji> {m('Send amount to add')}:"), parse_mode="HTML")

    elif state == WAITING_ADD_BAL_AMT and user.id in ADMINS:
        context.user_data.pop("state", None)
        try:
            tid = int(context.user_data.pop("tid"))
            amt = float(text)
            update_balance(tid, amt)
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> {m('Added')} <b>{amt}</b> {m('to')} {tid}"),
                reply_markup=admin_keyboard(), parse_mode="HTML")
        except:
            await update.message.reply_text(BQ(f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> {m('Error!')}"), parse_mode="HTML")

    elif state == WAITING_REM_BAL_ID and user.id in ADMINS:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data["tid"] = text
        context.user_data["state"] = WAITING_REM_BAL_AMT
        await update.message.reply_text(BQ(f"<tg-emoji emoji-id='6287149066925121984'>➖</tg-emoji> {m('Send amount to remove')}:"), parse_mode="HTML")

    elif state == WAITING_REM_BAL_AMT and user.id in ADMINS:
        context.user_data.pop("state", None)
        try:
            tid = int(context.user_data.pop("tid"))
            amt = float(text)
            update_balance(tid, -amt)
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> {m('Removed')} <b>{amt}</b> {m('from')} {tid}"),
                reply_markup=admin_keyboard(), parse_mode="HTML")
        except:
            await update.message.reply_text(BQ(f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> {m('Error!')}"), parse_mode="HTML")

    elif state == WAITING_GIFT_CODE_C and user.id in ADMINS:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)
        try:
            parts = text.strip().upper().split("--")
            if len(parts) != 2:
                raise ValueError
            max_users = int(parts[1].strip())
            left = parts[0].strip().split("-")
            if len(left) < 2:
                raise ValueError
            per_amount = float(left[-1])
            code = "-".join(left[:-1])
            conn = sqlite3.connect("bot.db")
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO gift_codes (code, per_amount, max_users, created_at) VALUES (?,?,?,?)",
                      (code, per_amount, max_users, datetime.now().isoformat()))
            conn.commit(); conn.close()
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> <b>{m('Gift Code Created!')}</b>\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6158989888512334518'>🎁</tg-emoji> {m('Code')}: {code}\n"
                    f"<tg-emoji emoji-id='6158943747678674305'>💰</tg-emoji> {m('Per User Amount')}: <b>{int(per_amount)} {m('Points')}</b>\n"
                    f"<tg-emoji emoji-id='6159105792499785038'>👥</tg-emoji> {m('Max Users')}: <b>{max_users}</b>\n"
                    f"{LINE}\n\n"
                    f"📤 {m('Share this code with users')}!"
                ),
                reply_markup=admin_keyboard(), parse_mode="HTML")
        except:
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('Wrong Format!')}</b>\n\n"
                    f"{LINE}\n"
                    f"✏️ {m('Correct format')}:\n"
                    f"GIFTNAME-AMOUNT--MAXUSERS\n\n"
                    f"📌 {m('Example')}:\n"
                    f"KINGBOTZ-2--10\n"
                    f"{LINE}"
                ),
                reply_markup=admin_keyboard(), parse_mode="HTML")

    elif state == WAITING_SECURE_NUM and user.id in ADMINS:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)
        num = text.strip().replace("+91", "").replace(" ", "")
        if not num.isdigit() or len(num) != 10:
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('Invalid Number!')}</b>\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> {m('Only 10 digits allowed')}\n"
                    f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> {m('No letters | No +91 | No spaces')}\n"
                    f"{LINE}"
                ),
                reply_markup=admin_keyboard(), parse_mode="HTML"); return
        protected = load_protected()
        if num in protected:
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> <b>{m('Already Secured!')}</b>\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6158957891005980158'>🔒</tg-emoji> {num}\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('This number is already in secured list')}\n"
                    f"{LINE}"
                ),
                reply_markup=admin_keyboard(), parse_mode="HTML"); return
        add_protected(num)
        await update.message.reply_text(
            BQ(
                f"<tg-emoji emoji-id='6158957891005980158'>🔒</tg-emoji> <b>{m('Number Secured!')}</b>\n\n"
                f"{LINE}\n"
                f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> {num} {m('added to protected list!')}\n"
                f"{LINE}"
            ),
            reply_markup=admin_keyboard(), parse_mode="HTML")

    elif state == WAITING_UNSECURE_NUM and user.id in ADMINS:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)
        remove_protected(text)
        await update.message.reply_text(
            BQ(f"<tg-emoji emoji-id='6158957891005980158'>🔓</tg-emoji> {text} {m('unprotected!')}"),
            reply_markup=admin_keyboard(), parse_mode="HTML")

    elif state == WAITING_ADD_ADMIN and user.id in ADMINS:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)
        num_only = text.strip()
        if not num_only.isdigit():
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('Invalid ID!')}</b>\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> {m('Only numbers allowed')}\n"
                    f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> {m('No letters | No spaces | No symbols')}\n"
                    f"{LINE}"
                ),
                reply_markup=admin_keyboard(), parse_mode="HTML"); return
        new_admin = int(num_only)
        if new_admin in ADMINS:
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> <b>{m('Already Admin!')}</b>\n\n"
                    f"{LINE}\n"
                    f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {new_admin} {m('is already an admin')}\n"
                    f"{LINE}"
                ),
                reply_markup=admin_keyboard(), parse_mode="HTML"); return
        ADMINS.add(new_admin)
        await update.message.reply_text(
            BQ(
                f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> <b>{m('Admin Added!')}</b>\n\n"
                f"{LINE}\n"
                f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {new_admin} {m('added as Admin!')}\n"
                f"{LINE}"
            ),
            reply_markup=admin_keyboard(), parse_mode="HTML")

    elif state == WAITING_ADD_CHANNEL and user.id in ADMINS:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)
        ch = text if text.startswith("@") else "@" + text
        FORCE_CHANNELS.append(ch)
        await update.message.reply_text(
            BQ(f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> {ch} {m('added!')}"),
            reply_markup=admin_keyboard(), parse_mode="HTML")

    elif state == WAITING_REM_CHANNEL and user.id in ADMINS:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)
        ch = text if text.startswith("@") else "@" + text
        if ch in FORCE_CHANNELS:
            FORCE_CHANNELS.remove(ch)
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> {ch} {m('removed from force join!')}"),
                reply_markup=admin_keyboard(), parse_mode="HTML")
        else:
            await update.message.reply_text(
                BQ(f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> {m('Channel not found')}: {ch}"),
                reply_markup=admin_keyboard(), parse_mode="HTML")

    elif state == WAITING_REM_ADMIN and user.id in ADMINS:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)
        try:
            rem_id = int(text.strip())
            if rem_id == ADMIN_ID:
                await update.message.reply_text(
                    BQ(
                        f"🛡️ <b>{m('Cannot Remove!')}</b>\n\n"
                        f"{LINE}\n"
                        f"<tg-emoji emoji-id='6156660766402421161'>⭐</tg-emoji> {rem_id}\n"
                        f"<tg-emoji emoji-id='6287034086355639532'>👑</tg-emoji> {m('This is Master Owner')}\n"
                        f"{LINE}"
                    ),
                    reply_markup=admin_keyboard(), parse_mode="HTML")
            elif rem_id in ADMINS:
                ADMINS.remove(rem_id)
                await update.message.reply_text(
                    BQ(f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> {rem_id} {m('removed from admins!')}"),
                    reply_markup=admin_keyboard(), parse_mode="HTML")
            else:
                await update.message.reply_text(
                    BQ(f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> {m('User not in admin list!')}"),
                    reply_markup=admin_keyboard(), parse_mode="HTML")
        except:
            await update.message.reply_text(BQ(f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> {m('Invalid ID!')}"), parse_mode="HTML")

    elif state == WAITING_ADD_PHONE_API and user.id in ADMINS:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)
        API_CONFIG["phone"] = text.strip()
        await update.message.reply_text(
            BQ(
                f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> <b>{m('Phone API Updated!')}</b>\n\n"
                f"{LINE}\n"
                f"🔗 {m('New API')}:\n{API_CONFIG['phone']}\n"
                f"{LINE}"
            ),
            reply_markup=admin_keyboard(), parse_mode="HTML")

    elif state == WAITING_ADD_TG_API and user.id in ADMINS:
        if text == f"🏡 {m('Home')}":
            await send_menu(update, context); return
        context.user_data.pop("state", None)
        API_CONFIG["tg"] = text.strip()
        await update.message.reply_text(
            BQ(
                f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> <b>{m('TG API Updated!')}</b>\n\n"
                f"{LINE}\n"
                f"🔗 {m('New API')}:\n{API_CONFIG['tg']}\n"
                f"{LINE}"
            ),
            reply_markup=admin_keyboard(), parse_mode="HTML")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type != "private": return
    if context.user_data.get("state") != WAITING_SCREENSHOT: return
    context.user_data.pop("state", None)
    utr = context.user_data.pop("utr", "N/A")
    plan = context.user_data.get("plan", ("Unknown", 1, "?"))
    photo_fid = update.message.photo[-1].file_id

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO payments (user_id,plan,utr,screenshot_file_id,created_at) VALUES (?,?,?,?,?)",
              (user.id, plan[0], utr, photo_fid, datetime.now().isoformat()))
    pay_id = c.lastrowid
    conn.commit(); conn.close()

    caption = BQ(
        f"💳 <b>{m('New Payment Request')}</b>\n\n"
        f"{LINE}\n"
        f"<tg-emoji emoji-id='6156937559864778682'>👉</tg-emoji> {m('User')}: <a href='tg://user?id={user.id}'>{m(user.first_name)}</a>\n"
        f"🆔 {m('ID')}: {user.id}\n"
        f"📦 {m('Plan')}: <b>{m(plan[0])}</b>\n"
        f"<tg-emoji emoji-id='6158943747678674305'>💰</tg-emoji> {m('Amount')}: <b>{plan[2]}</b>\n"
        f"🧾 {m('UTR')}: {utr}\n"
        f"{LINE}"
    )
    kb = InlineKeyboardMarkup([[
        IKB(f"✅ {m('Approve')}", style="success", callback_data=f"approve_{pay_id}"),
        IKB(f"❌ {m('Reject')}", style="danger", callback_data=f"reject_{pay_id}")
    ]])
    for admin_id in ADMINS:
        try:
            await context.bot.send_photo(admin_id, photo=photo_fid, caption=caption, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Admin notify error: {e}")

    await update.message.reply_text(
        BQ(
            f"<tg-emoji emoji-id='6159223405884219526'>✅</tg-emoji> <b>{m('Payment Submitted!')}</b>\n\n"
            f"{LINE}\n"
            f"<tg-emoji emoji-id='6159169740267855509'>🔔</tg-emoji> {m('Admin will verify shortly.')}\n"
            f"⏳ {m('Please wait...')}\n"
            f"{LINE}"
        ),
        reply_markup=main_keyboard(user.id), parse_mode="HTML")

async def _do_group_search(update, context, number):
    user = update.effective_user
    ensure_user(user.id, user.username or user.first_name)

    number = number.replace(" ", "").replace("+91", "").replace("-", "")
    if not number.isdigit() or len(number) != 10:
        await update.message.reply_text(
            BQ(
                f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('Invalid Number!')}</b>\n\n"
                f"{LINE}\n"
                f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> 10 digit number bhejo | No +91 | No spaces\n"
                f"{LINE}"
            ), parse_mode="HTML")
        return

    protected = load_protected()
    if number in protected or f"+91{number}" in protected:
        await update.message.reply_text(
            BQ(
                f"<tg-emoji emoji-id='6158957891005980158'>🔒</tg-emoji> <b>{m('Protected Number!')}</b>\n\n"
                f"{LINE}\n"
                f"🛡️ {m('This number is protected by Owner')}\n"
                f"{LINE}"
            ), parse_mode="HTML")
        return

    prem = is_premium(user.id)
    if not prem:
        row = get_user(user.id)
        bal = row[2] if row else 0
        if bal < 1:
            bot_user = await context.bot.get_me()
            await update.message.reply_text(
                BQ(
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> <b>ACCESS DENIED</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>Balance ya Premium nahi hai!</b>\n\n"
                    f"<tg-emoji emoji-id='6158943747678674305'>💰</tg-emoji> Har search = <b>1 Point</b>\n"
                    f"<tg-emoji emoji-id='6287034086355639532'>👑</tg-emoji> Premium = <b>Unlimited Search</b>\n\n"
                    f"<tg-emoji emoji-id='6159161068728885766'>📱</tg-emoji> <b>Balance Add / Premium Lo:</b>\n"
                    f"┗━ 👉 @{bot_user.username}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━"
                ), parse_mode="HTML")
            return
        update_balance(user.id, -1)

    msg = await update.message.reply_text(BQ(f"🔍 {m('Searching')}..."), parse_mode="HTML")
    await asyncio.sleep(0.4)
    await msg.edit_text(BQ(f"⚡ {m('Fetching data')}..."), parse_mode="HTML")
    await asyncio.sleep(0.4)
    await msg.edit_text(BQ(f"🌐 {m('Connecting to server')}..."), parse_mode="HTML")
    await asyncio.sleep(0.4)

    data = await fetch_number_data(number)
    if data:
        await msg.delete()
        if data.get("success", False) and data.get("records"):
            out = format_number_response(data, number)
            await update.message.reply_text(out, parse_mode="HTML")
        else:
            await update.message.reply_text(
                BQ(
                    f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>{m('No Data Found!')}</b>\n\n{LINE}\n{m('Number not in database.')}\n{LINE}"
                ), parse_mode="HTML")
    else:
        await msg.edit_text(
            BQ(
                f"<tg-emoji emoji-id='6159118767595986018'>⚠️</tg-emoji> <b>{m('Server Error!')}</b>\n\n{LINE}\n{m('Try again later.')}\n{LINE}"
            ), parse_mode="HTML")

async def group_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        return
    if not context.args:
        await update.message.reply_text(
            BQ(
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"<tg-emoji emoji-id='6156660766402421161'>🔍</tg-emoji> <b>NUMBER SEARCH</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<tg-emoji emoji-id='6156942524846973028'>❌</tg-emoji> <b>Number nahi diya!</b>\n\n"
                f"<tg-emoji emoji-id='6159161068728885766'>📱</tg-emoji> <b>Sahi format:</b>\n"
                f"┗━ <code>/search 9876543210</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━"
            ), parse_mode="HTML")
        return
    await _do_group_search(update, context, context.args[0])

async def _post_init(app):
    await warm_banner(app)

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", group_search))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_added))
    app.add_handler(CallbackQueryHandler(inline_btn))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))
    print("🤖 Bot is running...")

    import asyncio as _asyncio
    try:
        _asyncio.get_event_loop()
    except RuntimeError:
        _asyncio.set_event_loop(_asyncio.new_event_loop())

    app.post_init = _post_init
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
