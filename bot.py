import os
import re
import requests
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ================= CONFIGURATION =================
BOT_TOKEN = '8620790590:AAEovcplZZoxBKRTGCgFXXtbSGcMTXXi1jo'
API_URL = 'https://patel-number-api.vercel.app/number'

FORCE_CHANNELS = [
    {'username': '@modxpatel', 'link': 'https://t.me/modxpatel'},
    {'username': '@patelchatting_gc', 'link': 'https://t.me/patelchatting_gc'}
]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= HELPER FUNCTIONS =================
def extract_number(text: str) -> str:
    """Extract Indian phone number from ANY format"""
    text = re.sub(r'[\s\-\(\)\+]', '', text)
    patterns = [
        r'(?:91|0)?[6-9]\d{9}',
        r'[6-9]\d{9}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group()
    return None

def clean_address(address: str) -> str:
    """Clean address for display"""
    if not address or address == 'null':
        return 'N/A'
    address = address.replace('!', ' ')
    address = re.sub(r'\s+', ' ', address).strip()
    return address

def format_response(data: dict, requested_number: str) -> str:
    """Format response in black quote style with ALL records"""
    if not data.get('success'):
        return (
            "<blockquote>❌ Invalid number or API error\n"
            "Please try again with valid number\n"
            "\n"
            "📱 Example: 9693615642\n"
            "\n"
            "╭━━[ 𓃵 𝐏𝐀𝐓𝐄𝐋 𓃵 ]━━╮💀</blockquote>"
        )
    
    records = data.get('records', [])
    if not records:
        return (
            f"<blockquote>🔍 No records found\n"
            f"📱 Number: {requested_number}\n"
            f"\n"
            f"Try another number\n"
            f"\n"
            f"╭━━[ 𓃵 𝐏𝐀𝐓𝐄𝐋 𓃵 ]━━╮💀</blockquote>"
        )
    
    # Build black quote response - SHOW ALL RECORDS
    lines = []
    lines.append(f"📱 NUMBER: {requested_number}")
    lines.append(f"📊 TOTAL RECORDS: {data.get('total_records')}")
    lines.append("")
    
    # Show ALL records (no limit)
    for idx, record in enumerate(records, 1):
        name = record.get('NAME', 'N/A')
        fname = record.get('fname', 'N/A')
        alt = record.get('alt', 'N/A')
        circle = record.get('circle', 'N/A')
        address = clean_address(record.get('ADDRESS', 'N/A'))
        record_id = record.get('id', 'N/A')
        email = record.get('email', 'N/A')
        
        lines.append(f"📌 RECORD #{idx}")
        lines.append(f"👤 NAME: {name}")
        if fname and fname != 'N/A':
            lines.append(f"👨 FATHER: {fname}")
        if record_id and record_id != 'N/A':
            lines.append(f"🆔 ID: {record_id}")
        if alt and alt != 'N/A':
            lines.append(f"📞 ALTERNATE: {alt}")
        if circle and circle != 'N/A':
            lines.append(f"📡 CARRIER: {circle}")
        if address and address != 'N/A':
            lines.append(f"📍 ADDRESS: {address}")
        if email and email != 'N/A':
            lines.append(f"✉️ EMAIL: {email}")
        lines.append("")
    
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("╭━━[ 𓃵 𝐏𝐀𝐓𝐄𝐋 𓃵 ]━━╮💀")
    lines.append("👨‍💻 API BY PATEL")
    lines.append(f"🕐 {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")
    
    return f"<blockquote>{chr(10).join(lines)}</blockquote>"

# ================= BOT COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Force join check
    user_id = update.effective_user.id
    for channel in FORCE_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel['username'], user_id)
            if member.status in ['left', 'kicked']:
                keyboard = [[InlineKeyboardButton("🔔 Join Channel", url=channel['link'])]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"<blockquote>⚠️ Please join {channel['username']} to use this bot!</blockquote>",
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                return
        except Exception as e:
            logger.error(f"Force join check failed: {e}")
            continue
    
    welcome = (
        f"<blockquote>ʜᴇʟʟᴏ {user.first_name}! 👋\n"
        f"\n"
        f"🔍 Send me any Indian phone number\n"
        f"   to get details instantly!\n"
        f"\n"
        f"📱 Examples:\n"
        f"   /num 9693615642\n"
        f"   9693615642\n"
        f"   +919693615642\n"
        f"   91 96936 15642\n"
        f"\n"
        f"⚠️ Join channels to use:\n"
        f"   @modxpatel\n"
        f"   @patelchatting_gc\n"
        f"\n"
        f"╭━━[ 𓃵 𝐏𝐀𝐓𝐄𝐋 𓃵 ]━━╮💀</blockquote>"
    )
    await update.message.reply_text(welcome, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all messages with reply mode"""
    
    # Force join check
    user_id = update.effective_user.id
    for channel in FORCE_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel['username'], user_id)
            if member.status in ['left', 'kicked']:
                keyboard = [[InlineKeyboardButton("🔔 Join Channel", url=channel['link'])]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"<blockquote>⚠️ Please join {channel['username']} to use this bot!</blockquote>",
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                return
        except Exception as e:
            logger.error(f"Force join check failed: {e}")
            continue
    
    text = update.message.text
    
    # Extract number from any format
    number = None
    
    # Check if it's /num command
    if text.startswith('/num'):
        number_text = text.replace('/num', '').strip()
        number = extract_number(number_text)
        if not number:
            await update.message.reply_text(
                f"<blockquote>❌ Please provide a valid number\n"
                f"Usage: /num 9693615642\n"
                f"\n"
                f"Example: /num 9693615642\n"
                f"\n"
                f"╭━━[ 𓃵 𝐏𝐀𝐓𝐄𝐋 𓃵 ]━━╮💀</blockquote>",
                parse_mode='HTML'
            )
            return
    else:
        number = extract_number(text)
        if not number:
            return
    
    # Clean number for API
    clean_number = re.sub(r'[^0-9]', '', number)
    if len(clean_number) > 10:
        clean_number = clean_number[-10:]
    
    # Show processing message with REPLY to user's message
    processing_msg = await update.message.reply_text(
        f"<blockquote>⏳ Searching for {number}...\n"
        f"Please wait...\n"
        f"\n"
        f"╭━━[ 𓃵 𝐏𝐀𝐓𝐄𝐋 𓃵 ]━━╮💀</blockquote>",
        parse_mode='HTML'
    )
    
    # Call API
    try:
        logger.info(f"Calling API for number: {clean_number}")
        response = requests.get(f"{API_URL}?number={clean_number}", timeout=15)
        response.raise_for_status()
        data = response.json()
        
        formatted_response = format_response(data, number)
        # EDIT the processing message with REPLY mode
        await processing_msg.edit_text(formatted_response, parse_mode='HTML')
        
    except requests.exceptions.Timeout:
        await processing_msg.edit_text(
            f"<blockquote>⏰ API request timed out\n"
            f"Please try again later\n"
            f"\n"
            f"📱 Number: {number}\n"
            f"\n"
            f"╭━━[ 𓃵 𝐏𝐀𝐓𝐄𝐋 𓃵 ]━━╮💀</blockquote>",
            parse_mode='HTML'
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"API error: {e}")
        await processing_msg.edit_text(
            f"<blockquote>❌ API request failed\n"
            f"Please try again later\n"
            f"\n"
            f"📱 Number: {number}\n"
            f"\n"
            f"╭━━[ 𓃵 𝐏𝐀𝐓𝐄𝐋 𓃵 ]━━╮💀</blockquote>",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await processing_msg.edit_text(
            f"<blockquote>❌ Unexpected error occurred\n"
            f"Please try again later\n"
            f"\n"
            f"╭━━[ 𓃵 𝐏𝐀𝐓𝐄𝐋 𓃵 ]━━╮💀</blockquote>",
            parse_mode='HTML'
        )

# ================= MAIN =================
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('num', handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🚀 Patel Number Bot Started...")
    logger.info("📱 Bot is ready to detect numbers in any format!")
    logger.info("🔹 Force join enabled: @modxpatel & @patelchatting_gc")
    app.run_polling()
