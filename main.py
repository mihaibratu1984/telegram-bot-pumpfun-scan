import asyncio
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
import os

# Aplicăm nest_asyncio pentru compatibilitate Render
nest_asyncio.apply()

# Token Telegram din environment variable
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Interval scanare (secunde)
SCAN_INTERVAL = 10

# ==========================
# Funcție scanare tokeni
# ==========================
async def scan_tokens(context: ContextTypes.DEFAULT_TYPE):
    try:
        # Exemplu: trimitem mesaj în chat
        await context.bot.send_message(chat_id=context.job.chat_id, text="Scanare tokeni... 🚀")
        # TODO: aici integrează logica reală PumpFun + Solscan + filtre
    except Exception as e:
        print(f"Error in scan_tokens: {e}")

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

    # JobQueue este deja integrat în application
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
# Funcția principală async
# ==========================
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Start JobQueue (integrat)
    app.job_queue.start()

    # Handlere
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    # Pornim polling
    await app.run_polling()

# ==========================
# Compatibilitate Render / event loop existent
# ==========================
if __name__ == "__main__":
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        asyncio.create_task(main())
        # Menține scriptul activ
        import time
        while True:
            time.sleep(1)
    else:
        asyncio.run(main())
