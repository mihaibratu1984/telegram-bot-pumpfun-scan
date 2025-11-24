import asyncio
import nest_asyncio
import os
import aiohttp
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# Compatibilitate cu event loop Render
nest_asyncio.apply()

# Token Telegram din environment variable
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Interval scanare (secunde)
SCAN_INTERVAL = 10

# ==========================
# Funcție scanare tokeni PumpFun
# ==========================
async def scan_tokens(context: ContextTypes.DEFAULT_TYPE):
    url = "https://pumpfun.com/new-tokens"  # înlocuiește cu pagina reală PumpFun
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                tokens = soup.find_all("div", class_="token-card")  # selector fictiv

                for token in tokens:
                    name = token.find("span", class_="token-name").text
                    supply = token.find("span", class_="token-supply").text
                    social = token.find("a", class_="social-link")
                    burn = token.find("span", class_="burned").text

                    # Filtrare anti-scam
                    if not social or int(burn.replace(",", "")) == 0:
                        continue

                    # Mesaj Telegram
                    msg = f"🚀 {name} - Supply: {supply} - Burn: {burn}"
                    await context.bot.send_message(chat_id=context.job.chat_id, text=msg)
    except Exception as e:
        print(f"Error scan_tokens: {e}")

# ==========================
# Comanda /start
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("▶ Start Auto-Scan", callback_data='start')],
        [InlineKeyboardButton("⛔ Stop Auto-Scan", callback_data='stop')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Bun venit! Alege opțiunea:', reply_markup=reply_markup)

# ==========================
# Butoane meniu
# ==========================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    job_queue = context.application.job_queue

    if query.data == 'start':
        job_queue.run_repeating(
            scan_tokens,
            interval=SCAN_INTERVAL,
            first=0,
            chat_id=query.message.chat_id,
            name=str(query.message.chat_id)
        )
        await query.edit_message_text(text="Auto-Scan pornit ✅")
    elif query.data == 'stop':
        jobs = job_queue.get_jobs_by_name(str(query.message.chat_id))
        for job in jobs:
            job.schedule_removal()
        await query.edit_message_text(text="Auto-Scan oprit ⛔")

# ==========================
# Funcția principală
# ==========================
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.job_queue.start()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    await app.run_polling()

# ==========================
# Compatibilitate Render
# ==========================
if __name__ == "__main__":
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        asyncio.create_task(main())
        import time
        while True:
            time.sleep(1)
    else:
        asyncio.run(main())
