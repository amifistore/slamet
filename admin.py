from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from db import (
    get_all_produk, add_produk, update_produk, delete_produk, 
    get_produk_by_kode, get_all_users, get_saldo
)

def admin_panel(update, context):
    query = update.callback_query
    query.edit_message_text(
        "👑 <b>PANEL ADMIN</b>\nPilih menu admin:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Tambah Produk", callback_data='admin_add_produk')],
            [InlineKeyboardButton("📝 Kelola Produk", callback_data='admin_list_produk')],
            [InlineKeyboardButton("👤 Data User", callback_data='admin_cekuser')],
            [InlineKeyboardButton("💰 Lihat Saldo", callback_data='lihat_saldo')],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data='main_menu')],
        ])
    )

def admin_add_produk(update, context):
    query = update.callback_query
    context.user_data.clear()
    query.edit_message_text(
        "🆕 <b>Tambah Produk</b>\nKetik:\n<code>/produkbaru KODE NAMA HARGA DESKRIPSI</code>\nContoh:\n"
        "<code>/produkbaru PUL10 Pulsa10rb 11000 Pulsa elektrik 10rb</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_panel")]
        ])
    )

def cmd_produkbaru(update, context):
    if len(context.args) < 4:
        update.message.reply_text("Format salah.\nContoh:\n<code>/produkbaru PUL10 Pulsa10rb 11000 Pulsa elektrik 10rb</code>", parse_mode=ParseMode.HTML)
        return
    kode, nama, harga, *desk = context.args
    try:
        harga = float(harga)
    except Exception:
        update.message.reply_text("Harga harus angka!\nContoh: <code>/produkbaru PUL10 Pulsa10rb 11000 Deskripsi</code>", parse_mode=ParseMode.HTML)
        return
    deskripsi = " ".join(desk)
    add_produk(kode, nama, harga, deskripsi, 1)
    update.message.reply_text(f"✅ Produk <b>{nama}</b> berhasil ditambah & diaktifkan!", parse_mode=ParseMode.HTML)

def admin_list_produk(update, context):
    query = update.callback_query
    rows = get_all_produk(show_nonaktif=True)
    if not rows:
        msg = "❌ Tidak ada produk di database."
    else:
        msg = "📝 <b>Kelola Produk</b>\nKlik produk untuk edit/hapus/ubah status:\n\n"
        for kode, nama, harga, deskripsi, aktif in rows:
            status = "✅" if aktif else "❌"
            msg += f"{status} <b>{nama}</b> | Kode: <code>{kode}</code> | Rp {harga:,.0f}\n"
    keyboard = [
        [InlineKeyboardButton(f"{nama} [{kode}]", callback_data=f"admin_edit_produk_{kode}")]
        for kode, nama, harga, deskripsi, aktif in rows
    ]
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data="admin_panel")])
    query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

def admin_edit_produk(update, context):
    query = update.callback_query
    kode = query.data.replace("admin_edit_produk_", "")
    row = get_produk_by_kode(kode)
    if not row:
        query.edit_message_text("Produk tidak ditemukan.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_list_produk")]
        ]))
        return
    kode, nama, harga, deskripsi, aktif = row
    status = "Aktif ✅" if aktif else "Nonaktif ❌"
    query.edit_message_text(
        f"📝 <b>Edit Produk</b>\n"
        f"Kode: <code>{kode}</code>\nNama: <b>{nama}</b>\nHarga: <b>Rp {harga:,.0f}</b>\nDeskripsi: {deskripsi}\nStatus: {status}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Edit Nama", callback_data=f"admin_edit_nama_{kode}"),
             InlineKeyboardButton("💵 Edit Harga", callback_data=f"admin_edit_harga_{kode}")],
            [InlineKeyboardButton("📝 Edit Deskripsi", callback_data=f"admin_edit_desk_{kode}")],
            [InlineKeyboardButton("✅ Aktifkan" if not aktif else "❌ Nonaktifkan", callback_data=f"admin_toggle_{kode}")],
            [InlineKeyboardButton("🗑️ Hapus Produk", callback_data=f"admin_del_{kode}")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_list_produk")]
        ])
    )

def admin_edit_nama(update, context):
    query = update.callback_query
    kode = query.data.replace("admin_edit_nama_", "")
    context.user_data["edit_kode"] = kode
    query.edit_message_text(
        f"✏️ <b>Edit Nama Produk</b>\nKetik:\n<code>/editnama NAMABARU</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"admin_edit_produk_{kode}")]])
    )

def admin_edit_harga(update, context):
    query = update.callback_query
    kode = query.data.replace("admin_edit_harga_", "")
    context.user_data["edit_kode"] = kode
    query.edit_message_text(
        f"💵 <b>Edit Harga Produk</b>\nKetik:\n<code>/editharga HARGABARU</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"admin_edit_produk_{kode}")]])
    )

def admin_edit_desk(update, context):
    query = update.callback_query
    kode = query.data.replace("admin_edit_desk_", "")
    context.user_data["edit_kode"] = kode
    query.edit_message_text(
        f"📝 <b>Edit Deskripsi Produk</b>\nKetik:\n<code>/editdesk DESKRIPSI_BARU</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data=f"admin_edit_produk_{kode}")]])
    )

def admin_toggle(update, context):
    query = update.callback_query
    kode = query.data.replace("admin_toggle_", "")
    row = get_produk_by_kode(kode)
    if not row:
        query.edit_message_text("Produk tidak ditemukan.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_list_produk")]
        ]))
        return
    aktif = 0 if row[4] else 1
    update_produk(kode, aktif=aktif)
    query.answer("Status produk diubah.")
    admin_edit_produk(update, context)

def admin_del(update, context):
    query = update.callback_query
    kode = query.data.replace("admin_del_", "")
    delete_produk(kode)
    query.answer("Produk dihapus!")
    admin_list_produk(update, context)

def cmd_editnama(update, context):
    kode = context.user_data.get("edit_kode")
    if not kode or not context.args:
        update.message.reply_text("Format: /editnama NAMABARU")
        return
    nama = " ".join(context.args)
    update_produk(kode, nama=nama)
    update.message.reply_text("✅ Nama produk diubah.")

def cmd_editharga(update, context):
    kode = context.user_data.get("edit_kode")
    if not kode or not context.args:
        update.message.reply_text("Format: /editharga HARGABARU")
        return
    try:
        harga = float(context.args[0])
    except Exception:
        update.message.reply_text("Harga salah.")
        return
    update_produk(kode, harga=harga)
    update.message.reply_text("✅ Harga produk diubah.")

def cmd_editdesk(update, context):
    kode = context.user_data.get("edit_kode")
    if not kode or not context.args:
        update.message.reply_text("Format: /editdesk DESKRIPSI_BARU")
        return
    deskripsi = " ".join(context.args)
    update_produk(kode, deskripsi=deskripsi)
    update.message.reply_text("✅ Deskripsi produk diubah.")

def admin_cekuser(update, context):
    query = update.callback_query
    users = get_all_users()
    msg = f"👤 <b>Data User</b>\nTotal: {len(users)} user\n\n"
    for u in users:
        msg += f"- {u[2]} (@{u[1]}) - ID: <code>{u[0]}</code>\n"
    query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Kembali", callback_data='admin_panel')]
    ]))

def lihat_saldo(update, context):
    query = update.callback_query
    users = get_all_users()
    msg = f"💰 <b>Saldo Semua User</b>\n\n"
    for u in users:
        saldo = get_saldo(u[0])
        msg += f"{u[2]}: Rp {saldo:,.0f}\n"
    query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Kembali", callback_data='admin_panel')]
    ]))
