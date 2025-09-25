from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from db import tambah_user, get_saldo, get_all_produk

def get_menu(uid):
    menu = [
        [InlineKeyboardButton("🛒 Beli Produk", callback_data='order_start')],
        [InlineKeyboardButton("💳 Top Up Saldo", callback_data='topup_start')],
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
