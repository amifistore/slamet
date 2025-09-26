from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler
from config import TOKEN
from handlers import (
    start, main_menu_callback, produk_pilih_callback, input_tujuan_step, konfirmasi_step,
    topup_nominal_step, admin_edit_produk_step, handle_text,
    CHOOSING_PRODUK, INPUT_TUJUAN, KONFIRMASI, TOPUP_NOMINAL, ADMIN_EDIT
)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # PENTING: mapping ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(main_menu_callback, pattern="^(beli_produk|topup|manajemen_produk)$"),
        ],
        states={
            CHOOSING_PRODUK: [CallbackQueryHandler(produk_pilih_callback, pattern="^produk_static\\|\\d+$")],
            INPUT_TUJUAN: [MessageHandler(Filters.text & ~Filters.command, input_tujuan_step)],
            KONFIRMASI: [MessageHandler(Filters.text & ~Filters.command, konfirmasi_step)],
            TOPUP_NOMINAL: [MessageHandler(Filters.text & ~Filters.command, topup_nominal_step)],
            ADMIN_EDIT: [MessageHandler(Filters.text & ~Filters.command, admin_edit_produk_step)],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True,
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler)  # <--- HARUS di atas MessageHandler global
    dp.add_handler(CallbackQueryHandler(main_menu_callback))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))  # fallback pesan di luar percakapan

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
