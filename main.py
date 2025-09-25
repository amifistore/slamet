import os
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from db import init_db, get_saldo
from user import start, handle_text, get_menu, cek_stok_menu
from admin import admin_panel, admin_edit_produk, admin_edit_produk_detail, edit_harga, edit_deskripsi
from utils import rate_limiter

# Ubah ADMIN_IDS agar mudah diimport
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]

def menu_router(update, context):
    query = update.callback_query
    data = query.data
    user = query.from_user
    is_admin = user.id in ADMIN_IDS

    if data == "main_menu":
        saldo = get_saldo(user.id)
        query.edit_message_text(
            f"🏠 <b>MENU UTAMA</b>\nSaldo kamu: <b>Rp {saldo:,.0f}</b>",
            parse_mode="HTML",
            reply_markup=get_menu(user.id)
        )
    elif data == "cek_stok":
        return cek_stok_menu(update, context)
    elif data == "admin_panel" and is_admin:
        return admin_panel(update, context)
    elif data == "admin_edit_produk" and is_admin:
        return admin_edit_produk(update, context)
    elif data.startswith("admin_edit_produk_") and is_admin:
        return admin_edit_produk_detail(update, context)
    # ... lanjutkan menu lain ...

def main():
    init_db()
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CallbackQueryHandler(menu_router))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_handler(CommandHandler('editharga', edit_harga))
    dp.add_handler(CommandHandler('editdesk', edit_deskripsi))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
