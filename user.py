import uuid
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode

from db import tambah_user, get_saldo, get_all_produk, insert_topup_pending, get_topup_pending_by_user, update_topup_bukti

def get_menu(uid):
    menu = [
        [InlineKeyboardButton("🛒 Beli Produk", callback_data='order_start')],
        [InlineKeyboardButton("💳 Top Up Saldo", callback_data='topup_start')],
        [InlineKeyboardButton("🧾 Riwayat Top Up", callback_data='topup_riwayat')],
        [InlineKeyboardButton("📋 Riwayat", callback_data='riwayat')],
        [InlineKeyboardButton("📦 Info Stok", callback_data='cek_stok')],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(menu)

def start(update, context):
    user = update.effective_user
    tambah_user(user.id, user.username or "", user.full_name)
    saldo = get_saldo(user.id)
    update.message.reply_text(
        f"👋 <b>Hi, {user.full_name}!</b>\n💰 Saldo: <b>Rp {saldo:,.0f}</b>\nSilakan pilih menu di bawah.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_menu(user.id)
    )

def handle_text(update, context):
    update.message.reply_text(
        "Gunakan tombol menu di bawah ini.",
        reply_markup=get_menu(update.effective_user.id)
    )

def cek_stok_menu(update, context):
    query = update.callback_query
    rows = get_all_produk(show_nonaktif=False)
    msg = "📦 <b>Info Stok Produk (Aktif)</b>\n\n"
    if not rows:
        msg += "Tidak ada produk aktif."
    else:
        for kode, nama, harga, deskripsi, aktif in rows:
            msg += f"🟢 <b>{nama}</b>\nKode: <code>{kode}</code>\nHarga: <b>Rp {float(harga):,.0f}</b>\nDesk: {deskripsi or '-'}\n\n"
    try:
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(query.from_user.id))
    except Exception as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

def topup_start(update, context):
    query = update.callback_query
    query.answer()
    qris_admin = "00020101021126610014COM.GO-JEK.WWW01189360091434506469550210G4506469550303UMI51440014ID.CO.QRIS"
    query.edit_message_text(
        f"💳 <b>TOP UP SALDO</b>\n\n"
        f"Silakan transfer ke QRIS berikut (atau admin):\n"
        f"<code>{qris_admin}</code>\n\n"
        f"Upload bukti transfer di sini.\n"
        f"Tulis nominal pada caption bukti (contoh: 100000)",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")]])
    )

def handle_photo(update, context):
    user = update.effective_user
    photo = update.message.photo[-1]
    caption = update.message.caption or ""
    nominal = None
    # Cari nominal dari caption, contoh: "nominal 100000"
    for word in caption.split():
        if word.isdigit():
            nominal = float(word)
            break

    if not nominal:
        update.message.reply_text("Tulis nominal top up di caption, misal: 100000")
        return

    topup_id = str(uuid.uuid4())
    waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    insert_topup_pending(topup_id, user.id, user.username or "", user.full_name, nominal, waktu, "pending")
    update_topup_bukti(topup_id, photo.file_id, caption)
    update.message.reply_text("✅ Bukti top up diterima, tunggu admin verifikasi.")

def riwayat_topup_menu(update, context):
    query = update.callback_query
    items = get_topup_pending_by_user(query.from_user.id, 10)
    msg = "🧾 <b>Riwayat Top Up</b>\n\n"
    if not items:
        msg += "Belum ada riwayat top up."
    else:
        for r in items:
            emoji = "✅" if r[6] == "approved" else ("❌" if r[6] == "rejected" else "⏳")
            msg += (
                f"{emoji} <b>{r[5]}</b>\n"
                f"Nominal: Rp {r[4]:,.2f}\n"
                f"Status: <b>{r[6]}</b>\n\n"
            )
    query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(query.from_user.id))
