import logging
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
from handler import (
    start, help_command, handle_text_message, 
    get_conversation_handler, error_handler
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # Ganti dengan token bot Anda
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # Add handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(get_conversation_handler())
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text_message))
    dispatcher.add_error_handler(error_handler)
    
    # Start bot
    updater.start_polling()
    logger.info("Bot started successfully!")
    updater.idle()

if __name__ == '__main__':
    main()
