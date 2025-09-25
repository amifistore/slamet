from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMIN_IDS
from produk import get_produk_list

def is_admin(user_id):
    return user_id in ADMIN_IDS

def menu_user():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Lihat Produk", callback_data='lihat_produk')],
        [InlineKeyboardButton("🛒 Beli Produk", callback_data='beli_produk')],
        [InlineKeyboardButton("💸 Top Up", callback_data='topup')],
        [InlineKeyboardButton("🔍 Cek Status", callback_data='cek_status')],
        [InlineKeyboardButton("📄 Riwayat", callback_data='riwayat')],
        [InlineKeyboardButton("📊 Cek Stock XL/Axis", callback_data='stock_akrab')],
    ])

def menu_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Lihat Produk", callback_data='lihat_produk')],
        [InlineKeyboardButton("🛒 Beli Produk", callback_data='beli_produk')],
        [InlineKeyboardButton("💸 Top Up", callback_data='topup')],
        [InlineKeyboardButton("🔍 Cek Status", callback_data='cek_status')],
        [InlineKeyboardButton("📄 Riwayat", callback_data='riwayat')],
        [InlineKeyboardButton("📊 Cek Stock XL/Axis", callback_data='stock_akrab')],
        [InlineKeyboardButton("🗃️ Semua Riwayat", callback_data='semua_riwayat')],
        [InlineKeyboardButton("💰 Lihat Saldo", callback_data='lihat_saldo')],
        [InlineKeyboardButton("➕ Tambah Saldo", callback_data='tambah_saldo')],
        [InlineKeyboardButton("📝 Manajemen Produk", callback_data='manajemen_produk')]
    ])

def get_menu(user_id):
    return menu_admin() if is_admin(user_id) else menu_user()

def produk_inline_keyboard():
    keyboard = []
    for i, p in enumerate(get_produk_list()):
        keyboard.append([
            InlineKeyboardButton(f"{p['kode']} | {p['nama']}", callback_data=f"produk_static|{i}")
        ])
    return InlineKeyboardMarkup(keyboard)

def admin_edit_produk_keyboard(kode):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Edit Nama", callback_data=f"editnama|{kode}"),
         InlineKeyboardButton("Edit Harga", callback_data=f"editharga|{kode}")],
        [InlineKeyboardButton("Edit Kuota", callback_data=f"editkuota|{kode}"),
         InlineKeyboardButton("Edit Deskripsi", callback_data=f"editdeskripsi|{kode}")],
        [InlineKeyboardButton("⬅️ Kembali", callback_data="manajemen_produk")]
    ])
