import time
import psutil
import platform
from datetime import timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

start_time = time.time()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = str(timedelta(seconds=int(time.time() - start_time)))
    cpu_usage = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    total_ram = ram.total // (1024 * 1024)
    used_ram = ram.used // (1024 * 1024)
    ram_percent = ram.percent

    system_info = platform.uname()

    message = (
        f"**System Info**\n"
        f"Device: `{system_info.node}`\n"
        f"OS: `{system_info.system} {system_info.release}`\n\n"
        f"**CPU Usage**: `{cpu_usage}%`\n"
        f"**RAM**: `{used_ram}MB / {total_ram}MB` ({ram_percent}%)\n"
        f"**Uptime**: `{uptime}`"
    )
    await update.message.reply_text(message, parse_mode="Markdown")

if __name__ == '__main__':
    app = ApplicationBuilder().token("7982271214:AAEu_F_9EPyOxuWAsE6umLT8EiZUuVy8KFU").build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
