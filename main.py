import logging
import uuid
from datetime import datetime
import threading

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler, CallbackContext,
)
from config import get_config
import db
import provider
from utils import rate_limiter
import webhook

cfg = get_config()

logging.basicConfig(
    filename=cfg["LOG_FILE"], 
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Conversation states
(ORDER_PILIH_PRODUK, ORDER_INPUT_TUJUAN, ORDER_KONFIRMASI, 
 ADMIN_PANEL, ADMIN_BROADCAST, TOPUP_AMOUNT, TOPUP_UPLOAD, INPUT_KODE_UNIK) = range(8)

def get_menu(uid):
    admin = uid in cfg['ADMIN_IDS']
    menu = [
        [InlineKeyboardButton("🛒 Beli Produk", callback_data='order_start')],
        [InlineKeyboardButton("💳 Top Up Saldo", callback_data='topup_start')],
        [InlineKeyboardButton("📋 Riwayat", callback_data='riwayat')],
    ]
    if admin:
        menu.append([InlineKeyboardButton("👑 Panel Admin", callback_data='admin_panel')])
    return InlineKeyboardMarkup(menu)

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    if not rate_limiter.check(user.id):
        update.message.reply_text("❗️Terlalu banyak permintaan. Coba lagi beberapa saat lagi.")
        return
    db.tambah_user(user.id, user.username or "", user.full_name)
    saldo = db.get_saldo(user.id)
    update.message.reply_text(
        f"Selamat datang, <b>{user.full_name}</b>!\n\nSaldo: <b>Rp {saldo:,.0f}</b>\nSilakan pilih menu:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_menu(user.id)
    )

def main_menu_callback(update: Update, context: CallbackContext):
    user = update.effective_user
    saldo = db.get_saldo(user.id)
    if update.callback_query:
        query = update.callback_query
        query.answer()
        query.edit_message_text(
            f"Selamat datang kembali, <b>{user.full_name}</b>!\n\nSaldo: <b>Rp {saldo:,.0f}</b>\nSilakan pilih menu:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_menu(user.id)
        )
    else:
        update.message.reply_text(
            f"Selamat datang, <b>{user.full_name}</b>!\n\nSaldo: <b>Rp {saldo:,.0f}</b>\nSilakan pilih menu:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_menu(user.id)
        )
    return ConversationHandler.END

def order_start(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text("🔄 Memuat daftar produk, mohon tunggu...")

    produk_list = provider.get_products()
    if not produk_list:
        query.edit_message_text("❌ Produk kosong/gagal load. Coba lagi nanti.", reply_markup=get_menu(query.from_user.id))
        return ConversationHandler.END

    keyboard = []
    for produk in produk_list:
        label = f"[{produk['kode']}] {produk['nama']} - Rp {float(produk['harga']):,.0f}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"order_detail|{produk['kode']}")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")])
    query.edit_message_text(
        "🛒 <b>PILIH PRODUK</b>\n\nKlik produk yang ingin dibeli:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ORDER_PILIH_PRODUK

def order_detail_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    _, kode = query.data.split('|')
    produk = next((p for p in provider.get_products() if p['kode'] == kode), None)
    if not produk:
        query.edit_message_text("❌ Produk tidak ditemukan.", reply_markup=get_menu(query.from_user.id))
        return ORDER_PILIH_PRODUK
    context.user_data['order'] = {
        "kode": kode,
        "nama": produk['nama'],
        "harga": float(produk['harga'])
    }
    msg = (
        f"<b>Detail Produk:</b>\n"
        f"Nama : {produk['nama']}\n"
        f"Kode : <code>{kode}</code>\n"
        f"Harga: Rp {float(produk['harga']):,.0f}\n\n"
        f"Silakan masukkan nomor tujuan:"
    )
    query.edit_message_text(msg, parse_mode=ParseMode.HTML)
    return ORDER_INPUT_TUJUAN

def order_input_tujuan(update: Update, context: CallbackContext):
    tujuan = update.message.text.strip()
    if not tujuan.isdigit() or len(tujuan) < 8:
        update.message.reply_text("❌ Nomor tujuan tidak valid. Masukkan ulang.")
        return ORDER_INPUT_TUJUAN
    context.user_data['order']['tujuan'] = tujuan
    order = context.user_data['order']
    msg = (
        f"<b>Konfirmasi Pesanan</b>\n\n"
        f"Produk : {order['nama']}\n"
        f"Tujuan : <code>{tujuan}</code>\n"
        f"Harga  : Rp {order['harga']:,.0f}\n\n"
        f"Klik 'Konfirmasi' untuk memproses."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Konfirmasi & Bayar", callback_data="order_confirm")],
        [InlineKeyboardButton("❌ Batal", callback_data="main_menu")]
    ])
    update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    return ORDER_KONFIRMASI

def order_confirm_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    order = context.user_data.get('order')
    if not order:
        query.edit_message_text("❌ Sesi pesanan berakhir.", reply_markup=get_menu(user.id))
        return ConversationHandler.END
    saldo = db.get_saldo(user.id)
    if saldo < order['harga']:
        query.edit_message_text(f"❌ Saldo kurang. Saldo: Rp {saldo:,.0f}", reply_markup=get_menu(user.id))
        return ConversationHandler.END
    db.kurang_saldo(user.id, order['harga'])
    query.edit_message_text("⏳ Memproses transaksi...")

    reffid = str(uuid.uuid4())
    try:
        data = provider.create_transaction(order['kode'], order['tujuan'], reffid)
        status = data.get('status', 'PENDING')
        keterangan = data.get('message', '') or 'Pesanan diproses'
    except Exception as e:
        db.tambah_saldo(user.id, order['harga'])
        logger.error(f"API error: {e}")
        query.edit_message_text("❌ Gagal hubungi provider. Saldo dikembalikan.", reply_markup=get_menu(user.id))
        return ConversationHandler.END

    db.log_riwayat(reffid, user.id, order["kode"], order["tujuan"], order["harga"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status, keterangan)
    query.edit_message_text(
        f"✅ Pesanan sedang diproses.\nRefID: <code>{reffid}</code>\nStatus: {status}\n\nSaldo sekarang: Rp {db.get_saldo(user.id):,.0f}",
        parse_mode=ParseMode.HTML,
        reply_markup=get_menu(user.id)
    )
    return ConversationHandler.END

def handle_text(update: Update, context: CallbackContext):
    update.message.reply_text("Gunakan tombol menu.", reply_markup=get_menu(update.effective_user.id))

def callback_router(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    if data == "main_menu":
        return main_menu_callback(update, context)
    elif data == "order_start":
        return order_start(update, context)
    elif data.startswith("order_detail|"):
        return order_detail_callback(update, context)
    elif data == "riwayat":
        items = db.get_riwayat_user(query.from_user.id, 10)
        msg = "📋 <b>Riwayat Transaksi</b>\n\n"
        if not items:
            msg += "Belum ada transaksi."
        else:
            for r in items:
                status = r[6].upper()
                emoji = "✅" if "SUKSES" in status else ("❌" if "GAGAL" in status else "⏳")
                msg += (
                    f"{emoji} <b>{r[5]}</b>\n"
                    f"Produk: {r[2]} ke {r[3]}\n"
                    f"Harga: Rp {r[4]:,.2f}\n"
                    f"Status: <b>{status}</b> - <i>{r[7]}</i>\n\n"
                )
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(query.from_user.id))
    # Tambahkan handler lain: topup, admin, dsb
    else:
        query.answer("Belum tersedia.")

def main():
    db.init_db()
    updater = Updater(cfg["TOKEN"], use_context=True)
    dp = updater.dispatcher

    # Order conversation
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(order_start, pattern='^order_start$')],
        states={
            ORDER_PILIH_PRODUK: [
                CallbackQueryHandler(order_detail_callback, pattern="^order_detail\\|"),
            ],
            ORDER_INPUT_TUJUAN: [MessageHandler(Filters.text & ~Filters.command, order_input_tujuan)],
            ORDER_KONFIRMASI: [
                CallbackQueryHandler(order_confirm_callback, pattern="^order_confirm$"),
                CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"),
            CommandHandler('start', start),
        ]
    )

    dp.add_handler(order_conv)
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CallbackQueryHandler(callback_router))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

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
