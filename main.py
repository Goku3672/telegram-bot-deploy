import os
import time
import asyncio
import requests
import psutil
import json
from datetime import timedelta
from mimetypes import guess_extension
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
SERVICE_ACCOUNT_INFO = json.loads(os.getenv('SERVICE_ACCOUNT_JSON'))
TARGET_FOLDER_NAME = os.getenv('TARGET_FOLDER_NAME', 'botfiles')

# Initialize Google Drive service
creds = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build("drive", "v3", credentials=creds)

class UploadProgressTracker:
    # ... [Keep all existing UploadProgressTracker methods unchanged] ...

async def handle_gdrive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... [Keep existing handle_gdrive implementation unchanged] ...

def get_shared_folder_id(name):
    # ... [Keep existing get_shared_folder_id implementation unchanged] ...

async def main():
    print("Bot starting...")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("gdrive", handle_gdrive))
    
    if 'RENDER' in os.environ:
        # Webhook configuration
        await application.initialize()
        await application.start()
        await application.updater.start_webhook(
            listen="0.0.0.0",
            port=int(os.getenv('PORT', 10000)),
            url_path=BOT_TOKEN,
            webhook_url=os.getenv('WEBHOOK_URL'),
            drop_pending_updates=True
        )
        print("Webhook server started")
        while True:
            await asyncio.sleep(3600)  # Keep alive
    else:
        await application.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
