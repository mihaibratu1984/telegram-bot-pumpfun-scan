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

# Compatibilitate Render / asyncio
nest_asyncio.apply()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SOLSCAN_API = os.environ.get("SOLSCAN_API")  # opțional

SCAN_INTERVAL = 10  # secunde

# ==========================
# Verificare token pe Solscan (optional)
# ==========================
async def check_token_solscan(token_address):
    if not SOLSCAN_API:
        return True
    url = f"https://api.solscan.io/account/tokens?address={token_address}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                for t in data.get("tokens", []):
                    if int(t.get("amount", 0)) > 0:
                        return True
    except Exception as e:
        print(f"Solscan error: {e}")
    return False

# ==========================
# Scanare tokeni PumpFun
# ==========================
async def scan_tokens(context: ContextTypes.DEFAULT_TYPE):
    url = "https://pumpfun.com/new-tokens"  # înlocuiește cu pagina reală
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
                    contract = token.get("data-contract")

                    # Filtrare anti-scam
                    if not social or int(burn.replace(",", "")) == 0:
                        continue

                    valid = await check_token_solscan(contract)
                    if not valid:
                        continue

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
        # șterge job-uri vechi înainte de a crea altele noi
        for job in job_queue.get_jobs_by_name(str(query.message.chat_id)):
            job.schedule_removal()

        job_queue.run_repeating(
            scan_tokens,
            interval=SCAN_INTERVAL,
            first=0,
            chat_id=query.message.chat_id,
            name=str(query.message.chat_id)
        )
        await query.edit_message_text(text="Auto-Scan pornit ✅")

    elif query.data == 'stop':
        for job in job_queue.get_jobs_by_name(str(query.message.chat_id)):
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
    # Run polling doar o dată, fără conflict
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
