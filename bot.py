import os
from dotenv import load_dotenv
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from db import (
    init_db,
    add_subscriber,
    get_all_subscribers,
    create_bid,
    list_active_bids,
    add_participant,
    get_bid_details,
    end_auction,
)

# Load environment variables from .env
load_dotenv()

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
print(os.getenv("BOT_TOKEN"))
ADMINS = [5680376833]  # Add multiple admin IDs
# ----------------------------------------

user_states = {}  # user_id → bid_id they are bidding on


# 👋 /start - Add subscriber
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Received /start from {update.message.from_user.id}")
    user = update.message.from_user
    await add_subscriber(user.id, user.username or user.full_name)
    await update.message.reply_text(
        "👋 Welcome! You’ll receive auction updates when admin broadcasts."
    )


# 🟢 /broadcast - Admin creates a new auction
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("⛔ You are not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast <auction title>")
        return

    title = " ".join(context.args)
    bid = await create_bid(title)
    bid_id = bid["bid_id"]
    created_at = bid["created_at"].strftime("%Y-%m-%d %H:%M:%S")

    keyboard = [[InlineKeyboardButton(f"💰 Place Bid on #{bid_id}", callback_data=f"bid_{bid_id}")]]
    markup = InlineKeyboardMarkup(keyboard)

    subs = await get_all_subscribers()
    success = 0
    for user_id in subs:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 *New Auction!*\n\n🆔 *Bid #{bid_id}*\n📦 {title}\n🕒 Created: {created_at}\n\nClick below to bid 👇",
                parse_mode="Markdown",
                reply_markup=markup,
            )
            success += 1
        except Exception as e:
            print(f"Failed to send broadcast to {user_id}: {e}")

    await update.message.reply_text(f"✅ Broadcast sent to {success} users.\nAuction ID: {bid_id}")


# 💬 User selects a bid button
async def select_bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    bid_id = int(query.data.replace("bid_", ""))
    user_states[user_id] = bid_id
    await query.message.reply_text(f"You selected *Bid #{bid_id}*.\nPlease enter your bid amount:", parse_mode="Markdown")


# 💰 User enters a bid amount
async def handle_bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    bid_amount = update.message.text

    if user_id not in user_states:
        await update.message.reply_text("Please select a bid first using the 💰 button.")
        return

    if not bid_amount.replace(".", "", 1).isdigit():
        await update.message.reply_text("❌ Invalid amount. Enter a numeric value.")
        return

    bid_id = user_states[user_id]
    await add_participant(bid_id, user_id, user.username or user.full_name, float(bid_amount))
    await update.message.reply_text(f"✅ Your bid of {bid_amount} has been recorded for Bid #{bid_id}.")

    # Notify Admins
    for admin_id in ADMINS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"📥 *New Bid Received*\n\n🆔 Bid #{bid_id}\n👤 @{user.username or user.full_name}\n💰 Amount: {bid_amount}",
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"Admin notify failed: {e}")


# 📋 /list - List all active bids
async def list_bids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("⛔ Not authorized.")
        return

    rows = await list_active_bids()
    if not rows:
        await update.message.reply_text("No active bids yet.")
        return

    message = "📜 *All Active Auctions:*\n\n"
    for r in rows:
        message += f"🆔 #{r['bid_id']} — {r['title']} ({r['status']})\n"
    await update.message.reply_text(message, parse_mode="Markdown")


# 🔍 /bid <id> - Show details for a specific bid
async def bid_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("⛔ Not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /bid <bid_id>")
        return

    bid_id = int(context.args[0])
    bid, participants = await get_bid_details(bid_id)
    if not bid:
        await update.message.reply_text("❌ Bid not found.")
        return

    message = (
        f"📦 *Bid #{bid['bid_id']}*\n"
        f"🏷 Title: {bid['title']}\n"
        f"🕒 Created: {bid['created_at']}\n"
        f"📊 Status: {bid['status']}\n\n"
    )

    if participants:
        for p in participants:
            message += f"👤 {p['username']} — 💰 {p['amount']} (⏰ {p['bid_time']})\n"
    else:
        message += "_No participants yet._"

    await update.message.reply_text(message, parse_mode="Markdown")


# 🛑 /end <bid_id> - End a specific auction
async def end_specific_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("⛔ Not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /end <bid_id>")
        return

    bid_id = int(context.args[0])
    await end_auction(bid_id)
    await update.message.reply_text(f"✅ Auction #{bid_id} has been ended.")


# 🚀 Main
async def main():
    await init_db()
    print("Database initialized ✅")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("list", list_bids))
    app.add_handler(CommandHandler("bid", bid_details))
    app.add_handler(CommandHandler("end", end_specific_auction))
    app.add_handler(CallbackQueryHandler(select_bid, pattern="^bid_"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_bid))

    # Initialize and start bot
    await app.initialize()
    await app.start()

    print("🤖 Bot running...")

    # Keep bot running
    await app.updater.start_polling()
    await app.updater.idle()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
