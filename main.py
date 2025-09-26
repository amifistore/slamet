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

    # ✅ VERSI FIXED - Pattern matching yang benar
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(main_menu_callback, pattern="^(lihat_produk|beli_produk|topup|cek_status|riwayat|stock_akrab|semua_riwayat|lihat_saldo|tambah_saldo|manajemen_produk|admin_edit_produk|editharga|editdeskripsi|resetcustom|back_admin|back_main)$"),
        ],
        states={
            CHOOSING_PRODUK: [
                CallbackQueryHandler(produk_pilih_callback, pattern="^produk_static\\|"),
                CallbackQueryHandler(main_menu_callback, pattern="^back_main$"),
            ],
            INPUT_TUJUAN: [
                MessageHandler(Filters.text & ~Filters.command, input_tujuan_step),
            ],
            KONFIRMASI: [
                MessageHandler(Filters.text & ~Filters.command, konfirmasi_step),
            ],
            TOPUP_NOMINAL: [
                MessageHandler(Filters.text & ~Filters.command, topup_nominal_step),
            ],
            ADMIN_EDIT: [
                MessageHandler(Filters.text & ~Filters.command, admin_edit_produk_step),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("batal", cancel),
            CommandHandler("start", start),
            MessageHandler(Filters.regex('^(batal|BATAL|cancel)$'), cancel),
        ],
        allow_reentry=True,
    )

    # ✅ Handler untuk callback query yang tidak tertangkap conversation
    dp.add_handler(conv_handler)
    
    # ✅ Fallback callback handler untuk menangani semua callback lainnya
    dp.add_handler(CallbackQueryHandler(main_menu_callback))
    
    # ✅ Handler untuk command
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("cancel", cancel))
    dp.add_handler(CommandHandler("batal", cancel))
    
    # ✅ Handler untuk pesan teks
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    print("🚀 Bot Akrab Started Successfully!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
