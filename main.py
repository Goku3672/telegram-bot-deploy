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

# ========== CONFIGURATION ==========
BOT_TOKEN = os.getenv('BOT_TOKEN')
SERVICE_ACCOUNT_JSON = json.loads(os.getenv('SERVICE_ACCOUNT_JSON'))
TARGET_FOLDER_NAME = os.getenv('TARGET_FOLDER_NAME', 'botfiles')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Must be HTTPS!
PORT = int(os.getenv('PORT', 10000))

# ========== GOOGLE DRIVE SETUP ==========
creds = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_JSON,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build("drive", "v3", credentials=creds)

# ========== PROGRESS TRACKER ==========
class UploadProgressTracker:
    def __init__(self, total_size, msg, file_name):
        self.start_time = time.time()
        self.last_update = self.start_time
        self.total_size = total_size
        self.uploaded = 0
        self.msg = msg
        self.file_name = file_name
        
    async def update_progress(self, chunk_size):
        self.uploaded = min(self.uploaded + chunk_size, self.total_size)
        now = time.time()
        if now - self.last_update >= 2:
            self.last_update = now
            await self._update_status()
    
    async def _update_status(self):
        percent = (self.uploaded / self.total_size) * 100
        elapsed = time.time() - self.start_time
        speed = self.uploaded / elapsed if elapsed > 0 else 0
        remaining = max(self.total_size - self.uploaded, 0)
        eta = remaining / speed if speed > 0 else 0
        
        cpu, ram, disk, uptime = self._get_system_stats()
        
        text = (
            f"📤 Uploading: {self.file_name}\n"
            f"{self._build_status_bar(percent)}\n"
            f"📦 Processed: {self._format_size(self.uploaded)}/{self._format_size(self.total_size)}\n"
            f"🚀 Speed: {self._format_size(speed)}/s | ETA: {self._format_time(eta)}\n"
            f"⏱️ Elapsed: {self._format_time(elapsed)}\n\n"
            f"💻 System\n"
            f"🖥️ CPU: {cpu}% | 💾 Free: {disk:.1f}GB\n"
            f"🧠 RAM: {ram}% | ⏱️ Uptime: {str(uptime).split('.')[0]}"
        )
        
        try:
            await self.msg.edit_text(text)
        except Exception as e:
            print(f"Status update error: {e}")

    def _format_size(self, bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.1f}{unit}"
            bytes /= 1024
        return f"{bytes:.1f}PB"

    def _format_time(self, seconds):
        return str(timedelta(seconds=int(seconds)))

    def _build_status_bar(self, percent):
        percent = min(percent, 100)
        bar = "█" * int(percent // 5) + "░" * (20 - int(percent // 5))
        return f"{bar} {percent:.1f}%"

    def _get_system_stats(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').free / (1024**3)
        uptime = timedelta(seconds=int(time.time() - psutil.boot_time()))
        return cpu, ram, disk, uptime

# ========== CORE FUNCTIONALITY ==========
def get_proper_filename(url, response):
    """Determine the correct filename with extension"""
    # 1. Check Content-Disposition header first
    content_disposition = response.headers.get('Content-Disposition', '')
    if 'filename=' in content_disposition:
        filename = content_disposition.split('filename=')[1].split(';')[0].strip('"\'')
        return filename
    
    # 2. Get base name from URL
    url_name = url.split('/')[-1].split('?')[0]
    
    # 3. Check Content-Type for extension
    content_type = response.headers.get('Content-Type', '').split(';')[0].strip()
    extension = guess_extension(content_type) or ''
    
    # 4. Special cases for common types
    if not extension:
        if 'pdf' in content_type.lower():
            extension = '.pdf'
        elif 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
            extension = '.jpg'
        elif 'png' in content_type.lower():
            extension = '.png'
        elif 'zip' in content_type.lower():
            extension = '.zip'
    
    # 5. Combine name and extension
    if '.' in url_name:
        return url_name
    return f"{url_name}{extension}"

async def handle_gdrive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /gdrive <direct_download_link>")
        return

    url = context.args[0]
    msg = await update.message.reply_text("🔄 Starting download...")

    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            file_name = get_proper_filename(url, response)
            temp_file = f"temp_{file_name}"
            
            total = int(response.headers.get("content-length", 0))
            downloaded = 0
            start_time = time.time()
            last_update = start_time

            with open(temp_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        now = time.time()
                        if now - last_update >= 2:
                            percent = min((downloaded / total) * 100, 100)
                            speed = downloaded / (now - start_time + 0.1)
                            remaining = max(total - downloaded, 0)
                            eta = remaining / speed if speed > 0 else 0
                            bar = "█" * int(percent // 5) + "░" * (20 - int(percent // 5))
                            bar = f"{bar} {percent:.1f}%"
                            cpu, ram, disk, uptime = UploadProgressTracker._get_system_stats(None)

                            text = (
                                f"🔄 Downloading: {file_name}\n"
                                f"{bar}\n"
                                f"📦 Processed: {UploadProgressTracker._format_size(None, downloaded)}/{UploadProgressTracker._format_size(None, total)}\n"
                                f"🚀 Speed: {UploadProgressTracker._format_size(None, speed)}/s | ETA: {UploadProgressTracker._format_time(None, eta)}\n"
                                f"⏱️ Elapsed: {UploadProgressTracker._format_time(None, now - start_time)}\n\n"
                                f"💻 System\n"
                                f"🖥️ CPU: {cpu}% | 💾 Free: {disk:.1f}GB\n"
                                f"🧠 RAM: {ram}% | ⏱️ Uptime: {str(uptime).split('.')[0]}"
                            )

                            try:
                                await msg.edit_text(text)
                            except:
                                pass
                            last_update = now

        await msg.edit_text("📤 Preparing upload to Google Drive...")
        folder_id = get_shared_folder_id(TARGET_FOLDER_NAME)
        file_size = os.path.getsize(temp_file)
        tracker = UploadProgressTracker(file_size, msg, file_name)

        try:
            media = MediaFileUpload(temp_file, resumable=True, chunksize=1024*1024)
            request = drive_service.files().create(
                body={'name': file_name, 'parents': [folder_id]},
                media_body=media,
                fields='id, webViewLink'
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = min(status.resumable_progress, file_size)
                    await tracker.update_progress(progress - tracker.uploaded)

            await msg.edit_text(f"✅ File uploaded:\n{response['webViewLink']}")
        finally:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass

    except Exception as e:
        try:
            if 'temp_file' in locals() and os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass
        await msg.edit_text(f"❌ Error: {str(e)}")

def get_shared_folder_id(name):
    results = drive_service.files().list(
        q=f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces='drive',
        fields="files(id)"
    ).execute()
    items = results.get("files", [])
    if not items:
        raise Exception(f"Folder '{name}' not found or not shared with service account.")
    return items[0]["id"]

# ========== APPLICATION SETUP ==========
async def run_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("gdrive", handle_gdrive))
    
    if 'RENDER' in os.environ:
        if not WEBHOOK_URL.startswith('https://'):
            raise ValueError("WEBHOOK_URL must be HTTPS (e.g., https://your-service.onrender.com)")
            
        await application.initialize()
        await application.start()
        
        await application.updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=WEBHOOK_URL,
            drop_pending_updates=True
        )
        print(f"✅ Bot running in webhook mode at {WEBHOOK_URL}")
        
        # Keep the application running
        while True:
            await asyncio.sleep(3600)
    else:
        await application.run_polling()
        print("✅ Bot running in polling mode")

# ========== ENTRY POINT ==========
if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
