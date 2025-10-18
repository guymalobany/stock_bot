import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.error import BadRequest

# NVIDIA LangChain
from langchain_nvidia_ai_endpoints import ChatNVIDIA

TOKEN = os.environ.get("TG_TOKEN")
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")

# --- Safe edit helper ---
async def safe_edit(message, text):
    try:
        await message.edit_text(text)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            return
        await message.reply_text(text)

# --- Streaming with NVIDIA ---
async def ask_nvidia_stream(question: str, message):
    llm = ChatNVIDIA(
        model_name="nemo-chat",
        streaming=True,
        api_key=NVIDIA_API_KEY,
        temperature=0.7,
    )

    accum = ""

    def generator_loop():
        nonlocal accum
        for chunk in llm.stream([{"role": "user", "content": question}]):
            # chunk is an AIMessageChunk; append its content
            accum += getattr(chunk, "content", "")

    # Run the blocking generator in a thread
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, generator_loop)

    # Send the accumulated response
    await safe_edit(message, accum)
    return accum

# --- Telegram command ---
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = " ".join(context.args)
    if not question:
        await update.message.reply_text("Send a question after /ask, e.g. `/ask Hello`")
        return

    loading_msg = await update.message.reply_text("⏳ Thinking...")
    await ask_nvidia_stream(question, loading_msg)

# --- Main ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("ask", ask))
    print("🚀 Bot running...")
    app.run_polling()
