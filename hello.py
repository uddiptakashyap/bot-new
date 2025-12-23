import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

players = set()
completed = set()
task_active = False
warning_task = None


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in ["administrator", "creator"]


async def add_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return

    if not context.args:
        await update.message.reply_text("Usage: /add @user1 @user2 ...")
        return

    added = []
    for arg in context.args:
        username = arg.replace("@", "")
        players.add(username)
        added.append(f"@{username}")

    await update.message.reply_text("Added:\n" + "\n".join(added))


async def remove_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return

    if not context.args:
        await update.message.reply_text("Usage: /remove @user1 @user2 ...")
        return

    removed = []
    for arg in context.args:
        username = arg.replace("@", "")
        players.discard(username)
        removed.append(f"@{username}")

    await update.message.reply_text("Removed:\n" + "\n".join(removed))


async def list_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return

    if not players:
        await update.message.reply_text("No players added")
        return

    await update.message.reply_text("\n".join(f"@{p}" for p in players))


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

    user = update.effective_user
    if user.username in players:
        completed.add(user.username)
        await update.message.reply_text("Marked done")


async def warning_scheduler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    times = [6, 12, 18, 24]

    for i, h in enumerate(times, 1):
        await asyncio.sleep(h * 3600)

        if not task_active:
            return

        pending = [f"@{p}" for p in players if p not in completed]
        if pending:
            await update.message.reply_text(
                f"Warning {i}/4\n"
                "VSA pending for following players\n" +
                "\n".join(pending)
            )


async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return

    if not task_active:
        await update.message.reply_text("No active tournament")
        return

    pending = [f"@{p}" for p in players if p not in completed]
    if pending:
        await update.message.reply_text(
            "VSA pending for following players\n" +
            "\n".join(pending)
        )
    else:
        await update.message.reply_text("All players completed VSA")


async def end_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global task_active, warning_task

    if not await is_admin(update, context):
        return

    if not task_active:
        await update.message.reply_text("No active tournament")
        return

    pending = [f"@{p}" for p in players if p not in completed]

    if pending:
        await update.message.reply_text(
            "Tournament ended\n"
            "VSA pending for following players\n" +
            "\n".join(pending)
        )
    else:
        await update.message.reply_text(
            "Tournament ended\n"
            "All players completed VSA"
        )

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/add @user1 @user2 ...\n"
        "/remove @user1 @user2 ...\n"
        "/list\n"
        "/start_task\n"
        "/done\n"
        "/pending\n"
        "/end_task\n"
        "/reset"
    )


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



