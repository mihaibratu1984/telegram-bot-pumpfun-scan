import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import time

# ==========================================================
# CONFIG
# ==========================================================
TELEGRAM_TOKEN = "8311905393:AAFBQ7FDj5rzn5Wo3fVazWomXMM3xklHh3E"
PUMPFUN_NEW_API = "https://api.pump.fun/v1/tokens/new"
SOLSCAN_API = "https://api.solscan.io/token/"

AUTO_SCAN_INTERVAL = 10  # secunde

# Anti-spam memory
reported_tokens = set()

# ==========================================================
# ADVANCED FILTERS
# ==========================================================
def analyze_token(token, sol_data):
    score = 0
    reasons = []

    # 1) Social Links
    socials = token.get("socials", {})
    if socials:
        score += 1
        reasons.append("Socials OK ✔️")
    else:
        reasons.append("Fără socials ❌")

    # 2) Burn
    if token.get("burned", False):
        score += 1
        reasons.append("Burn detectat 🔥")
    else:
        reasons.append("No burn ❌")

    # 3) Dev Holdings
    dev_hold = token.get("dev_holdings", 0)
    if dev_hold <= 0.1:
        score += 1
        reasons.append(f"Dev holdings OK ({dev_hold*100:.1f}%) ✔️")
    else:
        reasons.append(f"Dev holders prea mari ({dev_hold*100:.1f}%) ❌")

    # 4) LP Locked
    if token.get("lp_locked", False):
        score += 1
        reasons.append("LP Locked ✔️")
    else:
        reasons.append("LP unlocked ❌")

    # 5) Renounce
    if token.get("owner_renounced", False):
        score += 1
        reasons.append("Ownership renounced ✔️")
    else:
        reasons.append("Owner activ ❌")

    # 6) Top Holder
    th = token.get("top_holder_percentage", 0)
    if th <= 0.3:
        score += 1
        reasons.append(f"Distribuție OK ({th*100:.1f}%) ✔️")
    else:
        reasons.append(f"Top holder mare ({th*100:.1f}%) ❌")

    # Solscan supply check
    if sol_data and "tokenInfo" in sol_data:
        supply = float(sol_data["tokenInfo"].get("supply", 0))
        if supply > 0:
            score += 1
            reasons.append("Supply valid @Solscan ✔️")

    return score, reasons

# ==========================================================
# SOLSCAN DATA FETCH
# ==========================================================
def get_solscan(address):
    try:
        r = requests.get(SOLSCAN_API + address)
        return r.json()
    except:
        return None

# ==========================================================
# BOT UI (MENU)
# ==========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("▶ Start Auto-Scan", callback_data="autoscan")],
        [InlineKeyboardButton("⛔ Stop Auto-Scan", callback_data="stopscan")]
    ]
    await update.message.reply_text(
        "🤖 PumpFun Auto-Scanner Bot\nAlege opțiunea:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==========================================================
# AUTO-SCAN LOGIC
# ==========================================================
async def auto_scan(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data

    try:
        response = requests.get(PUMPFUN_NEW_API)
        tokens = response.json().get("tokens", [])
    except:
        return

    for token in tokens:
        address = token.get("address")
        if not address or address in reported_tokens:
            continue

        sol = get_solscan(address)
        score, reasons = analyze_token(token, sol)

        if score >= 5:
            reported_tokens.add(address)

            msg = f"🚨 *Token nou detectat!*\n"
            msg += f"{token.get('name')} ({token.get('symbol')})\n"
            msg += f"CA: `{address}`\n\n"
            for r in reasons:
                msg += f"• {r}\n"
            await context.bot.send_message(chat_id, msg, parse_mode="Markdown")

# ==========================================================
# START/STOP AUTO-SCAN
# ==========================================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "autoscan":
        context.job_queue.run_repeating(
            auto_scan,
            interval=AUTO_SCAN_INTERVAL,
            first=5,
            data=query.message.chat_id,
            name=str(query.message.chat_id)
        )
        await query.edit_message_text("✅ Auto-scan pornit! Interval: 10 secunde.")

    elif query.data == "stopscan":
        context.job_queue.stop()
        await query.edit_message_text("⛔ Auto-scan oprit.")

# ==========================================================
# MAIN
# ==========================================================
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
