from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
TOKEN = os.getenv("TELEGRAM_TOKEN")

from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from db import init_db, get_saldo
from user import start, handle_text, get_menu, cek_stok_menu
from admin import (
    admin_panel, admin_add_produk, admin_list_produk, admin_edit_produk,
    admin_edit_nama, admin_edit_harga, admin_edit_desk, admin_toggle, admin_del,
    cmd_produkbaru, cmd_editnama, cmd_editharga, cmd_editdesk,
    admin_cekuser, lihat_saldo
)

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
    elif data == "admin_add_produk" and is_admin:
        return admin_add_produk(update, context)
    elif data == "admin_list_produk" and is_admin:
        return admin_list_produk(update, context)
    elif data.startswith("admin_edit_produk_") and is_admin:
        return admin_edit_produk(update, context)
    elif data.startswith("admin_edit_nama_") and is_admin:
        return admin_edit_nama(update, context)
    elif data.startswith("admin_edit_harga_") and is_admin:
        return admin_edit_harga(update, context)
    elif data.startswith("admin_edit_desk_") and is_admin:
        return admin_edit_desk(update, context)
    elif data.startswith("admin_toggle_") and is_admin:
        return admin_toggle(update, context)
    elif data.startswith("admin_del_") and is_admin:
        return admin_del(update, context)
    elif data == "admin_cekuser" and is_admin:
        return admin_cekuser(update, context)
    elif data == "lihat_saldo" and is_admin:
        return lihat_saldo(update, context)

def main():
    init_db()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CallbackQueryHandler(menu_router))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_handler(CommandHandler('produkbaru', cmd_produkbaru))
    dp.add_handler(CommandHandler('editnama', cmd_editnama))
    dp.add_handler(CommandHandler('editharga', cmd_editharga))
    dp.add_handler(CommandHandler('editdesk', cmd_editdesk))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
