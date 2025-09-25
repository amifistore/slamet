import logging
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from config import get_config
from db import init_db
from utils import rate_limiter
import threading
import webhook

cfg = get_config()

logging.basicConfig(
    filename=cfg["LOG_FILE"], 
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    if not rate_limiter.check(user.id):
        update.message.reply_text("❗️Terlalu banyak permintaan. Coba lagi beberapa saat lagi.")
        return
    # TODO: register user, tampilkan dashboard, dsb.
    update.message.reply_text("Halo! Bot siap digunakan.", parse_mode=ParseMode.HTML)

def main():
    init_db()
    updater = Updater(cfg["TOKEN"], use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    # TODO: Tambah handler lain

    # Jalankan webhook Flask di thread terpisah
    flask_thread = threading.Thread(target=webhook.app.run, kwargs={
        "host": "0.0.0.0",
        "port": cfg["WEBHOOK_PORT"]
    })
    flask_thread.daemon = True
    flask_thread.start()

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
