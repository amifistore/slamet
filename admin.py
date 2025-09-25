from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from db import get_all_users, get_saldo, set_produk_local, get_all_riwayat
from provider import get_products

def admin_panel(update, context):
    query = update.callback_query
    query.edit_message_text(
        "👑 <b>PANEL ADMIN</b>\nPilih menu:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 Data User", callback_data='admin_cekuser')],
            [InlineKeyboardButton("💰 Lihat Saldo", callback_data='lihat_saldo')],
            [InlineKeyboardButton("📊 Semua Riwayat", callback_data='semua_riwayat')],
            [InlineKeyboardButton("🛠️ Edit Produk", callback_data="admin_edit_produk")],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data='main_menu')]
        ])
    )

def admin_edit_produk(update, context):
    query = update.callback_query
    produk_list = get_products()
    keyboard = []
    for produk in produk_list:
        kode = produk.get('kode') or produk.get('kode_produk') or produk.get('sku') or "-"
        nama = produk.get('nama') or produk.get('product_name') or produk.get('name') or "-"
        keyboard.append([InlineKeyboardButton(f"{nama} [{kode}]", callback_data=f"admin_edit_produk_{kode}")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="admin_panel")])
    query.edit_message_text(
        "🛠️ <b>EDIT PRODUK</b>\nPilih produk yang ingin diedit:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def admin_edit_produk_detail(update, context):
    query = update.callback_query
    kode_produk = query.data.replace("admin_edit_produk_", "")
    context.user_data["edit_kode_produk"] = kode_produk
    query.edit_message_text(
        f"📝 <b>Edit Produk {kode_produk}</b>\nKetik:\n\n"
        "<b>/editharga HARGA_BARU</b> untuk ubah harga (di bot)\n"
        "<b>/editdesk DESKRIPSI_BARU</b> untuk ubah deskripsi (di bot)",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_edit_produk")]
        ])
    )

def edit_harga(update, context):
    user = update.effective_user
    from main import ADMIN_IDS
    if user.id not in ADMIN_IDS:
        update.message.reply_text("❌ Menu khusus admin.")
        return
    if "edit_kode_produk" not in context.user_data:
        update.message.reply_text("Pilih produk dulu dari panel admin.")
        return
    if not context.args:
        update.message.reply_text("Format: /editharga 12345")
        return
    try:
        harga_baru = float(context.args[0])
    except Exception:
        update.message.reply_text("Format harga salah.")
        return
    kode_produk = context.user_data["edit_kode_produk"]
    set_produk_local(kode_produk, harga=harga_baru)
    update.message.reply_text("✅ Harga produk berhasil diupdate di database lokal.")

def edit_deskripsi(update, context):
    user = update.effective_user
    from main import ADMIN_IDS
    if user.id not in ADMIN_IDS:
        update.message.reply_text("❌ Menu khusus admin.")
        return
    if "edit_kode_produk" not in context.user_data:
        update.message.reply_text("Pilih produk dulu dari panel admin.")
        return
    if not context.args:
        update.message.reply_text("Format: /editdesk Deskripsi Baru Produk")
        return
    deskripsi_baru = " ".join(context.args)
    kode_produk = context.user_data["edit_kode_produk"]
    set_produk_local(kode_produk, deskripsi=deskripsi_baru)
    update.message.reply_text("✅ Deskripsi produk berhasil diupdate di database lokal.")
