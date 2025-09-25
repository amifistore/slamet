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
    # ... [import dan bagian di atas tetap]

from telegram import InputMediaPhoto

# Tambahan state
(TOPUP_AMOUNT, TOPUP_UPLOAD, ADMIN_TOPUP_PENDING, ADMIN_APPROVE_TOPUP) = range(8, 12)

def topup_start(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "💳 <b>TOP UP SALDO</b>\n\nMasukkan nominal top up (contoh: 50000):",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")]])
    )
    context.user_data['topup_method'] = 'qris'
    return TOPUP_AMOUNT

def topup_amount_step(update: Update, context: CallbackContext):
    try:
        nominal = int(update.message.text.replace(".", "").replace(",", ""))
        if nominal < 10000:
            raise ValueError
    except ValueError:
        update.message.reply_text("❌ Nominal tidak valid. Min. 10.000. Ulangi.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")]]))
        return TOPUP_AMOUNT

    user = update.effective_user
    kode_unik = uuid.uuid4().hex[:3]
    nominal_final = nominal + int(kode_unik)
    topup_id = str(uuid.uuid4())

    # ---- SIMULASI QRIS ----
    # Kamu bisa ganti ini dengan API QRIS sesungguhnya
    fake_qris_img = open("qris_sample.png", "rb") if os.path.exists("qris_sample.png") else None

    db.insert_topup_pending(
        topup_id, user.id, user.username or "", user.full_name,
        nominal_final, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "pending"
    )

    update.message.reply_photo(
        photo=fake_qris_img if fake_qris_img else None,
        caption=f"Transfer tepat sebesar <b>Rp {nominal_final:,.0f}</b> ke QRIS di atas.\nKirim bukti transfer dengan upload foto di sini.",
        parse_mode=ParseMode.HTML
    )
    context.user_data['pending_topup_id'] = topup_id
    return TOPUP_UPLOAD

def topup_upload_step(update: Update, context: CallbackContext):
    user = update.effective_user
    topup_id = context.user_data.get('pending_topup_id')
    if not topup_id:
        update.message.reply_text("❌ Sesi top up tidak ditemukan.", reply_markup=get_menu(user.id))
        return ConversationHandler.END

    if not update.message.photo:
        update.message.reply_text("❌ Kirim bukti berupa foto.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")]]))
        return TOPUP_UPLOAD

    file_id = update.message.photo[-1].file_id
    db.update_topup_bukti(topup_id, file_id, "")

    # Notifikasi admin
    for admin_id in cfg["ADMIN_IDS"]:
        try:
            context.bot.send_message(
                admin_id,
                f"🔔 Bukti transfer baru dari {user.full_name} (@{user.username or 'N/A'}). Approve di menu admin."
            )
        except Exception as e:
            logger.error(f"Gagal kirim notif admin: {e}")

    update.message.reply_text("✅ Bukti transfer terkirim. Tunggu konfirmasi admin.", reply_markup=get_menu(user.id))
    context.user_data.pop('pending_topup_id', None)
    return ConversationHandler.END

# -------- ADMIN ---------
def admin_panel(update: Update, context: CallbackContext):
    query = update.callback_query
    query.edit_message_text(
        "👑 <b>PANEL ADMIN</b>\n\nPilih menu:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve Top Up", callback_data="admin_topup_pending")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")]
        ])
    )
    return ADMIN_PANEL

def admin_topup_pending(update: Update, context: CallbackContext):
    query = update.callback_query
    items = db.get_topup_pending_all(10)
    keyboard = []
    if not items:
        keyboard.append([InlineKeyboardButton("✅ Tidak ada permintaan", callback_data="main_menu")])
    for r in items:
        label = f"{r[3]} - Rp {r[4]:,.2f}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"admin_topup_detail|{r[0]}")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="admin_panel")])
    query.edit_message_text(
        "📋 <b>PERMINTAAN TOP UP PENDING</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_TOPUP_PENDING

def admin_topup_detail(update: Update, context: CallbackContext):
    query = update.callback_query
    topup_id = query.data.split("|")[1]
    r = db.get_topup_by_id(topup_id)
    if not r:
        query.answer("❌ Data tidak ditemukan.", show_alert=True)
        return admin_topup_pending(update, context)
    caption = (
        f"<b>Detail Top Up</b>\n\n"
        f"User: {r[3]} (@{r[2]})\n"
        f"ID: <code>{r[1]}</code>\n"
        f"Nominal: Rp {r[4]:,.2f}\n"
        f"Waktu: {r[5]}"
    )
    actions = [
        [InlineKeyboardButton("✅ Setujui", callback_data=f"admin_topup_action|approve|{topup_id}"),
         InlineKeyboardButton("❌ Tolak", callback_data=f"admin_topup_action|reject|{topup_id}")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="admin_topup_pending")]
    ]
    if r[7]: # bukti_file_id
        query.edit_message_media(
            InputMediaPhoto(r[7], caption=caption, parse_mode=ParseMode.HTML),
            reply_markup=InlineKeyboardMarkup(actions)
        )
    else:
        query.edit_message_text(caption + "\n\n(Belum ada bukti transfer)", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(actions))
    return ADMIN_APPROVE_TOPUP

def admin_topup_action(update: Update, context: CallbackContext):
    query = update.callback_query
    _, action, topup_id = query.data.split("|")
    r = db.get_topup_by_id(topup_id)
    if not r:
        query.answer("❌ Data tidak ditemukan.", show_alert=True)
        return admin_topup_pending(update, context)
    user_id, nominal = r[1], r[4]
    if action == "approve":
        db.tambah_saldo(user_id, nominal)
        db.update_topup_status(topup_id, "approved")
        query.answer("✅ Top up disetujui.", show_alert=True)
        context.bot.send_message(user_id, f"✅ Top up Rp {nominal:,.2f} telah disetujui.")
    elif action == "reject":
        db.update_topup_status(topup_id, "rejected")
        query.answer("❌ Top up ditolak.", show_alert=True)
        context.bot.send_message(user_id, f"❌ Top up Rp {nominal:,.2f} ditolak.")
    return admin_topup_pending(update, context)

# -------- Tambahkan pada ConversationHandler states di main() --------
# ...
    topup_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(topup_start, pattern='^topup_start$')],
        states={
            TOPUP_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, topup_amount_step)],
            TOPUP_UPLOAD: [MessageHandler(Filters.photo, topup_upload_step)],
        },
        fallbacks=[
            CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"),
            CommandHandler('start', start),
        ]
    )
    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_panel, pattern='^admin_panel$')],
        states={
            ADMIN_PANEL: [CallbackQueryHandler(admin_topup_pending, pattern='^admin_topup_pending$')],
            ADMIN_TOPUP_PENDING: [CallbackQueryHandler(admin_topup_detail, pattern='^admin_topup_detail\\|')],
            ADMIN_APPROVE_TOPUP: [CallbackQueryHandler(admin_topup_action, pattern='^admin_topup_action\\|')],
        },
        fallbacks=[
            CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"),
            CommandHandler('start', start),
        ]
    )
    dp.add_handler(topup_conv)
    dp.add_handler(admin_conv)
# ... [handler lain tetap]
   # ... [import dan fungsi di atas tetap seperti punyamu] ...

def cekstatus(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Format: /cekstatus <reffid>")
        return
    reffid = context.args[0]
    from provider import get_history
    try:
        data = get_history(reffid)
        status = data.get("data", {}).get("status", "-")
        ket = data.get("data", {}).get("message", "-")
        update.message.reply_text(
            f"Status transaksi:\nRefID: <code>{reffid}</code>\nStatus: {status}\nKeterangan: {ket}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        update.message.reply_text(f"Gagal cek status: {e}")

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

    topup_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(topup_start, pattern='^topup_start$')],
        states={
            TOPUP_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, topup_amount_step)],
            TOPUP_UPLOAD: [MessageHandler(Filters.photo, topup_upload_step)],
        },
        fallbacks=[
            CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"),
            CommandHandler('start', start),
        ]
    )

    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_panel, pattern='^admin_panel$')],
        states={
            ADMIN_PANEL: [CallbackQueryHandler(admin_topup_pending, pattern='^admin_topup_pending$')],
            ADMIN_TOPUP_PENDING: [CallbackQueryHandler(admin_topup_detail, pattern='^admin_topup_detail\\|')],
            ADMIN_APPROVE_TOPUP: [CallbackQueryHandler(admin_topup_action, pattern='^admin_topup_action\\|')],
        },
        fallbacks=[
            CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"),
            CommandHandler('start', start),
        ]
    )

    dp.add_handler(order_conv)
    dp.add_handler(topup_conv)
    dp.add_handler(admin_conv)
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('cekstatus', cekstatus))
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
