import os
import html
import asyncio
import contextlib
import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    Defaults
)
from telegram.helpers import escape_markdown
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest
from ai import (
    ask_nvidia_ai,
    ask_nvidia_ai_stream,
    prepare_stock_data,
    analyze_from_data,
    system_prompt,
    short_system_prompt,
    chat_system_prompt
)
from finhub_api import get_latest_company_news_last_two_weeks

TOKEN = os.environ.get("TG_TOKEN")
ACL_ALLOWED_IDS = os.environ.get("TG_ALLOWED_IDS", "")
LOGGER = logging.getLogger("stock_bot")

# --- STOCK LOGIC ---
def get_stock_info(symbol: str) -> str:
    try:
        data = prepare_stock_data(symbol)
        return analyze_from_data(data,short_system_prompt)
    except Exception as e:
        return f"⚠️ Error while processing '{symbol}': {e}"


# --- ACL ---
_ALLOWED_ID_SET = {int(x.strip()) for x in ACL_ALLOWED_IDS.split(",") if x.strip()}


def is_authorized(user_id: int) -> bool:
    if _ALLOWED_ID_SET is None:
        return True
    return user_id in _ALLOWED_ID_SET


def _user_label(user):
    if not user:
        return "<unknown>"
    username = f"@{user.username}" if user.username else "<no-username>"
    return f"id={user.id} {username} name=\"{user.first_name or ''} {user.last_name or ''}\"".strip()


def log_access(user, allowed: bool, action: str, reason: str = ""):
    status = "ALLOWED" if allowed else "DENIED"
    msg = f"ACL {status} | {action} | user: {_user_label(user)}"
    if reason:
        msg = f"{msg} | reason: {reason}"
    if allowed:
        LOGGER.info(msg)
    else:
        LOGGER.warning(msg)


# --- STREAM HELPERS ---
# Chat Typing.
async def _send_typing(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        while True:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        return

# --- MENUS ---
# --- REPLY KEYBOARD (persistent bottom menu) ---
def reply_menu():
    keyboard = [
        [
            KeyboardButton("📰 Latest 2w News"),
            KeyboardButton("🆘 Help"),
            KeyboardButton("🤔 Deep Dive")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_authorized(user.id if user else 0):
        return
    log_access(user, True, "start")
    msg = (
        "👋 *Hello there!* I'm your AI assistant bot.\n\n"
        "Use the menu below or type a stock symbol (e.g. `AMD`) to get info."
    )
    await update.message.reply_text(
        escape_markdown(msg, version=2),
        reply_markup=reply_menu()
    )

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_authorized(user.id if user else 0):
        log_access(user, False, "echo_message", "user not in ACL")
        return
    log_access(user, True, "echo_message")
    raw_text = update.message.text.strip()
    text = raw_text.upper()
    safe_text = escape_markdown(text, version=2)

    # Handle reply keyboard buttons by text (we compare upper-cased)
    if text == "📰 LATEST 2W NEWS":
        symbol = (context.user_data.get("last_symbol") or "").upper()
        if symbol and symbol.isalpha() and 1 <= len(symbol) <= 5:
            try:
                news = get_latest_company_news_last_two_weeks(symbol, limit=10)
                if isinstance(news, list) and news:
                    lines = [f"📰 Latest news for {symbol} (last 2w):\n"]
                    for item in news[:10]:
                        title = str(item.get("headline") or item.get("title") or "(no title)")
                        url = str(item.get("url") or "")
                        lines.append(f"• {title}")
                        if url:
                            lines.append(url)
                    text_out = "\n".join(lines)
                else:
                    text_out = f"No recent news found for {symbol}."
            except Exception as exc:
                text_out = f"Failed to fetch news for {symbol}: {exc}"
            try:            
                await update.message.reply_text(text_out, parse_mode=None, reply_markup=reply_menu())
            except Exception as e:
                logging.error(f"Error sending Telegram message Trying again")
                await update.message.reply_text(text_out, parse_mode=None, reply_markup=reply_menu())
        else:
            await update.message.reply_text("Send a stock ticker (e.g. AMD) first, then press ‘Latest 2w News’.", parse_mode=None, reply_markup=reply_menu())
        return
    if text == "🆘 HELP":
        await update.message.reply_text("Send a stock ticker like `AMD` or `NVDA` to get info, or go fuck yourself.", parse_mode=None, reply_markup=reply_menu())
        return
    if text == "🤔 DEEP DIVE":
        await update.message.reply_text("Let's go!.", parse_mode=None, reply_markup=reply_menu())
        symbol = (context.user_data.get("last_symbol") or "").upper()
        if symbol:
            # fetch stock info for deep dive
            data = await asyncio.to_thread(prepare_stock_data, symbol)
            await update.message.reply_text(f"🤖 Go Go Power Rangers\! \n Feeding the beast with {text} data ", reply_markup=reply_menu())
            result = await asyncio.to_thread(analyze_from_data, data , system_prompt)  # type: ignore[name-defined]
            await update.message.reply_text("Generating response!", parse_mode=ParseMode.MARKDOWN)
            await update.message.reply_text(result, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("No stock provided, run a quick search before deep diving. 🤿", parse_mode=ParseMode.MARKDOWN)
        return 

    # Detect stock ticker format
    if text.isalpha() and 1 <= len(text) <= 5:
        # remember last symbol for quick callbacks
        context.user_data["last_symbol"] = text
        # Let user know bot is working
        loading_text = escape_markdown("⏳ Request started...", version=2)
        loading_msg = await update.message.reply_text(loading_text, reply_markup=reply_menu())

        # Show typing indicator while we compute the response
        typing_task = asyncio.create_task(_send_typing(update.effective_chat.id, context))

        accum = ""
        last_sent = None
        last_edit = asyncio.get_event_loop().time()
        message_editable = False
        try:

            # Stage: fetching data
            try:
                # send notification message to user
                loading_msg = await update.message.reply_text(f"Fetching data for {text} ", reply_markup=reply_menu())
            except BadRequest:
                pass
            # Fetch once before streaming
            data = await asyncio.to_thread(prepare_stock_data, text)

            # Stage: analyzing
            try:
                loading_msg = await update.message.reply_text(f"🤖 Go Go Power Rangers\! \n Feeding the beast with {text} data ", reply_markup=reply_menu())
            except BadRequest as e:
                print(e)
                pass
            try:
                # send data to AI
                result = await asyncio.to_thread(analyze_from_data, data , short_system_prompt)  # type: ignore[name-defined]
            except Exception:
                # If data wasn't fetched yet for any reason, fetch once now
                data_fallback = await asyncio.to_thread(prepare_stock_data, text)
                result = await asyncio.to_thread(analyze_from_data, data_fallback , short_system_prompt)
            accum = result
        finally:
            # Notification
            loading_msg = await update.message.reply_text(f"Generating response\!", reply_markup=reply_menu())
            typing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await typing_task
        if not message_editable:
            # Send final as new message with safe parse fallbacks
            try:
                await update.message.reply_text(accum, parse_mode=ParseMode.MARKDOWN)
            except BadRequest:
                try:
                    safe_mdv2 = escape_markdown(accum, version=2)
                    await update.message.reply_text(safe_mdv2, parse_mode=ParseMode.MARKDOWN_V2)
                except BadRequest:
                    await update.message.reply_text(accum, parse_mode=None)
    elif raw_text.startswith("!"): 
        typing_task = asyncio.create_task(_send_typing(update.effective_chat.id, context))
        # Send a placeholder/loading message to be edited
        loading_msg = await update.message.reply_text("🤖 Generating response...", parse_mode=ParseMode.HTML)
        ai_response = ""
        last_edit_time = asyncio.get_event_loop().time()
        edit_interval = 0.2  # seconds between edits to prevent rate limits
        try:
            stream = await asyncio.to_thread(ask_nvidia_ai_stream, raw_text, chat_system_prompt)  # type: ignore[name-defined]
            for token in stream:
                ai_response += token
                now = asyncio.get_event_loop().time()
                if now - last_edit_time > edit_interval:
                    try:
                        await loading_msg.edit_text(ai_response or "🤖 Generating response...", parse_mode=ParseMode.HTML)
                        last_edit_time = now
                    except Exception as e:
                        # Optionally log or handle edit errors due to Telegram rate limits
                        pass
            typing_task.cancel()
            # Final edit to ensure all content is updated
            #await loading_msg.edit_text(ai_response, parse_mode=ParseMode.HTML)
        except Exception as e:
            await loading_msg.edit_text(f"⚠️ Error generating response: {e}", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"🪞 You said: *{safe_text}*", reply_markup=reply_menu())


# --- MAIN ---
if __name__ == "__main__":
    # Basic logging setup
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if _ALLOWED_ID_SET is None:
        LOGGER.info("ACL disabled (TG_ALLOWED_IDS not set); allowing all users")
    else:
        LOGGER.info(f"ACL enabled; allowed ids: {_ALLOWED_ID_SET}")

    # Reduce noisy third-party logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    defaults = Defaults(parse_mode="MarkdownV2")

    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .defaults(defaults)  # 👈 sets MarkdownV2 globally
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))

    print("🚀 Bot is running with MarkdownV2 support...")
    app.run_polling()
