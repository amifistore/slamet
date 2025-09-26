from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler
from config import TOKEN
from handlers import (
    start, main_menu_callback, produk_pilih_callback, input_tujuan_step, konfirmasi_step,
    topup_nominal_step, admin_edit_produk_step, handle_text, cancel,
    CHOOSING_PRODUK, INPUT_TUJUAN, KONFIRMASI, TOPUP_NOMINAL, ADMIN_EDIT
)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Conversation Handler dengan logging
    def debug_conversation(update, context):
        print(f"🔍 Conversation State: {context.user_data}")
        return True

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(main_menu_callback),
        ],
        states={
            CHOOSING_PRODUK: [
                CallbackQueryHandler(produk_pilih_callback, pattern="^produk_static\\|"),
                CallbackQueryHandler(main_menu_callback, pattern="^back_"),
                MessageHandler(Filters.all, lambda u,c: u.message.reply_text("Silakan pilih produk dari menu atau ketik /batal")),
            ],
            INPUT_TUJUAN: [
                MessageHandler(Filters.text & ~Filters.command, input_tujuan_step),
                MessageHandler(Filters.all, lambda u,c: u.message.reply_text("Silakan masukkan nomor tujuan atau ketik /batal")),
            ],
            KONFIRMASI: [
                MessageHandler(Filters.text & ~Filters.command, konfirmasi_step),
                MessageHandler(Filters.all, lambda u,c: u.message.reply_text("Ketik 'YA' untuk konfirmasi atau 'BATAL' untuk batal")),
            ],
            TOPUP_NOMINAL: [
                MessageHandler(Filters.text & ~Filters.command, topup_nominal_step),
                MessageHandler(Filters.all, lambda u,c: u.message.reply_text("Masukkan nominal angka atau ketik /batal")),
            ],
            ADMIN_EDIT: [
                MessageHandler(Filters.text & ~Filters.command, admin_edit_produk_step),
                CallbackQueryHandler(main_menu_callback, pattern="^back_"),
                MessageHandler(Filters.all, lambda u,c: u.message.reply_text("Silakan masukkan input yang diminta atau ketik /batal")),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('batal', cancel),
            CommandHandler('start', start),
            CommandHandler('help', start),
            MessageHandler(Filters.regex('^(/?batal|/?BATAL|/?cancel)$'), cancel),
            MessageHandler(Filters.command, lambda u,c: u.message.reply_text("Gunakan /batal untuk membatalkan operasi saat ini")),
        ],
        allow_reentry=True,
        per_chat=True,
        per_user=True,
        per_message=False,
    )

    # Urutan handler sangat penting!
    dp.add_handler(conv_handler)
    
    # Handler untuk text messages (fallback)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    
    # Command handlers
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('cancel', cancel))
    dp.add_handler(CommandHandler('batal', cancel))
    dp.add_handler(CommandHandler('help', start))

    # Error handler
    def error_handler(update, context):
        print(f"❌ Error: {context.error}")
        if update and update.message:
            update.message.reply_text("❌ Terjadi error. Silakan coba lagi.")

    dp.add_error_handler(error_handler)

    print("=" * 50)
    print("🤖 BOT AKRAB TELEGRAM")
    print("📍 Status: RUNNING")
    print("⚡ Powered by Python-Telegram-Bot")
    print("=" * 50)
    
    updater.start_polling(drop_pending_updates=True)
    print("✅ Bot is now listening for messages...")
    updater.idle()

if __name__ == "__main__":
    main()
