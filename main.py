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
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Must be HTTPS!

# Initialize Google Drive service
creds = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build("drive", "v3", credentials=creds)

class UploadProgressTracker:
    # [Keep all existing UploadProgressTracker methods unchanged]
    # ...

async def handle_gdrive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # [Keep existing handle_gdrive implementation unchanged]
    # ...

def get_shared_folder_id(name):
    # [Keep existing get_shared_folder_id implementation unchanged]
    # ...

async def main():
    print("Bot starting...")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("gdrive", handle_gdrive))
    
    if 'RENDER' in os.environ:
        if not WEBHOOK_URL.startswith('https://'):
            raise ValueError("WEBHOOK_URL must start with https://")
            
        await application.initialize()
        await application.start()
        
        try:
            await application.updater.start_webhook(
                listen="0.0.0.0",
                port=int(os.getenv('PORT', 10000)),
                url_path=BOT_TOKEN,
                webhook_url=WEBHOOK_URL,
                drop_pending_updates=True,
                secret_token=os.getenv('WEBHOOK_SECRET', '')
            )
            print(f"Webhook server started at {WEBHOOK_URL}")
            
            # Keep application running
            while True:
                await asyncio.sleep(3600)
                
        except Exception as e:
            print(f"Webhook setup failed: {e}")
            await application.stop()
            raise
    else:
        await application.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped gracefully")
    except Exception as e:
        print(f"Bot crashed: {e}")
