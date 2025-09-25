from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from db import tambah_user, get_saldo, get_riwayat_user, get_produk_override
from provider import get_products

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
    produk_list = get_products()
    msg = "📦 <b>Info Stok Produk</b>\n\n"
    if not produk_list:
        msg += "Tidak ada produk ditemukan."
    else:
        for produk in produk_list:
            kode = produk.get('kode') or produk.get('kode_produk') or produk.get('sku') or "-"
            nama = produk.get('nama') or produk.get('product_name') or produk.get('name') or "-"
            harga = produk.get('harga') or produk.get('price') or 0
            local = get_produk_override(kode)
            if local.get("harga") is not None:
                harga = local["harga"]
            msg += f"🟢 <b>{nama}</b>\nKode: <code>{kode}</code>\nHarga: <b>Rp {float(harga):,.0f}</b>\n\n"
    query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(query.from_user.id))
