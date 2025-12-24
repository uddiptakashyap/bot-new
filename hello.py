import asyncio
import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

players = set()
completed = set()
task_active = False
warning_task = None

web = Flask(__name__)

@web.route("/")
def home():
    return "Bot is running"

def run_web():
    web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )
    return member.status in ["administrator", "creator"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "VSA Tournament Bot\n\n"
        "Admin Commands:\n"
        "/add user1 user2\n"
        "/remove user1 user2\n"
        "/list\n"
        "/start_task\n"
        "/pending\n"
        "/end_task\n"
        "/reset\n\n"
        "Player Command:\n"
        "/done"
    )

async def add_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    for arg in context.args:
        players.add(arg.replace("@", ""))
    await update.message.reply_text("Players added")

async def remove_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    for arg in context.args:
        players.discard(arg.replace("@", ""))
    await update.message.reply_text("Players removed")

async def list_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if players:
        await update.message.reply_text("\n".join(f"@{p}" for p in players))
    else:
        await update.message.reply_text("No players added")

async def start_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global task_active, completed, warning_task
    if not await is_admin(update, context):
        return
    if not players:
        await update.message.reply_text("No players added")
        return

    task_active = True
    completed.clear()

    await update.message.reply_text(
        "VSA Round Started\n"
        "Players must type /done after completing VSA"
    )

    warning_task = asyncio.create_task(warning_scheduler(update, context))

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not task_active:
        return
    user = update.effective_user.username
    if user in players:
        completed.add(user)
        await update.message.reply_text("Marked done")

async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not task_active:
        await update.message.reply_text("No active tournament")
        return
    pending_players = [f"@{p}" for p in players if p not in completed]
    if pending_players:
        await update.message.reply_text(
            "VSA pending for following players\n" +
            "\n".join(pending_players)
        )
    else:
        await update.message.reply_text("All players completed VSA")

async def end_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global task_active, warning_task
    if not await is_admin(update, context):
        return
    if not task_active:
        return

    pending_players = [f"@{p}" for p in players if p not in completed]
    if pending_players:
        await update.message.reply_text(
            "Tournament ended\nPending players\n" +
            "\n".join(pending_players)
        )
    else:
        await update.message.reply_text("Tournament ended\nAll players completed")

    task_active = False
    completed.clear()
    if warning_task:
        warning_task.cancel()

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global task_active, completed
    if not await is_admin(update, context):
        return
    task_active = False
    completed.clear()
    await update.message.reply_text("Reset done")

async def warning_scheduler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    times = [6, 12, 18, 24]
    for i, h in enumerate(times, 1):
        await asyncio.sleep(h * 3600)
        if not task_active:
            return
        pending_players = [f"@{p}" for p in players if p not in completed]
        if pending_players:
            await update.message.reply_text(
                f"Warning {i}/4\nVSA pending for\n" +
                "\n".join(pending_players)
            )

def main():
    threading.Thread(target=run_web, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_player))
    app.add_handler(CommandHandler("remove", remove_player))
    app.add_handler(CommandHandler("list", list_players))
    app.add_handler(CommandHandler("start_task", start_task))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CommandHandler("end_task", end_task))
    app.add_handler(CommandHandler("reset", reset))

    app.run_polling()

if __name__ == "__main__":
    main()
