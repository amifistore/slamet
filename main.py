import os
import logging
import threading
import sqlite3
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, InputMediaPhoto
)
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
)
import requests
from dotenv import load_dotenv

# ========== CONFIG ==========
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]
PROVIDER_BASE_URL = os.getenv("PROVIDER_BASE_URL")
PROVIDER_API_KEY = os.getenv("PROVIDER_API_KEY")
QRIS_STATIS = os.getenv("QRIS_STATIS")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", 8080))
LOG_FILE = os.getenv("LOG_FILE", "bot_error.log")

# ========== LOGGING ==========
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== DB ==========
DBNAME = "botdata.db"
db_lock = threading.Lock()

def get_conn():
    return sqlite3.connect(DBNAME, check_same_thread=False)

def init_db():
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT, nama TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS saldo (
            user_id INTEGER PRIMARY KEY, saldo REAL DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS riwayat_transaksi (
            id TEXT PRIMARY KEY, user_id INTEGER, produk TEXT, tujuan TEXT, harga REAL, waktu TEXT, status_text TEXT, keterangan TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS topup_pending (
            id TEXT PRIMARY KEY, user_id INTEGER, username TEXT, nama TEXT, nominal REAL, waktu TEXT, status TEXT, bukti_file_id TEXT, bukti_caption TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS kode_unik_topup (
            kode TEXT PRIMARY KEY, user_id INTEGER, nominal REAL, digunakan INTEGER DEFAULT 0, dibuat_pada TEXT, digunakan_pada TEXT)""")
        conn.commit()
        conn.close()

def tambah_user(user_id, username, nama):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (id, username, nama) VALUES (?, ?, ?)", (user_id, username, nama))
        c.execute("INSERT OR IGNORE INTO saldo (user_id, saldo) VALUES (?, 0)", (user_id,))
        conn.commit()
        conn.close()

def get_user(user_id):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, username, nama FROM users WHERE id=?", (user_id,))
        user = c.fetchone()
        conn.close()
        return user

def get_all_users():
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT id, username, nama FROM users")
        users = c.fetchall()
        conn.close()
        return users

def get_saldo(user_id):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT saldo FROM saldo WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else 0

def tambah_saldo(user_id, amount):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO saldo(user_id, saldo) VALUES (?,0)", (user_id,))
        c.execute("UPDATE saldo SET saldo=saldo+? WHERE user_id=?", (amount, user_id))
        conn.commit()
        conn.close()

def kurang_saldo(user_id, amount):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE saldo SET saldo=saldo-? WHERE user_id=?", (amount, user_id))
        conn.commit()
        conn.close()

def log_riwayat(id, user_id, produk, tujuan, harga, waktu, status_text, keterangan):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""INSERT INTO riwayat_transaksi
            (id, user_id, produk, tujuan, harga, waktu, status_text, keterangan)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (id, user_id, produk, tujuan, harga, waktu, status_text, keterangan))
        conn.commit()
        conn.close()

def get_riwayat_user(user_id, limit=10):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""SELECT * FROM riwayat_transaksi WHERE user_id=? ORDER BY waktu DESC LIMIT ?""", (user_id, limit))
        rows = c.fetchall()
        conn.close()
        return rows

def get_all_riwayat(limit=10):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""SELECT * FROM riwayat_transaksi ORDER BY waktu DESC LIMIT ?""", (limit,))
        rows = c.fetchall()
        conn.close()
        return rows

def get_riwayat_by_refid(reffid):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM riwayat_transaksi WHERE id=?", (reffid,))
        row = c.fetchone()
        conn.close()
        return row

def update_riwayat_status(reffid, status_text, keterangan):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE riwayat_transaksi SET status_text=?, keterangan=? WHERE id=?",
                  (status_text, keterangan, reffid))
        conn.commit()
        conn.close()

def insert_topup_pending(id, user_id, username, nama, nominal, waktu, status):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""INSERT INTO topup_pending
            (id, user_id, username, nama, nominal, waktu, status, bukti_file_id, bukti_caption)
            VALUES (?, ?, ?, ?, ?, ?, ?, '', '')""",
            (id, user_id, username, nama, nominal, waktu, status))
        conn.commit()
        conn.close()

def update_topup_bukti(id, bukti_file_id, bukti_caption):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE topup_pending SET bukti_file_id=?, bukti_caption=? WHERE id=?",
                  (bukti_file_id, bukti_caption, id))
        conn.commit()
        conn.close()

def update_topup_status(id, status):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE topup_pending SET status=? WHERE id=?", (status, id))
        conn.commit()
        conn.close()

def get_topup_pending_by_user(user_id, limit=10):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""SELECT * FROM topup_pending WHERE user_id=? ORDER BY waktu DESC LIMIT ?""", (user_id, limit))
        rows = c.fetchall()
        conn.close()
        return rows

def get_topup_pending_all(limit=10):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""SELECT * FROM topup_pending WHERE status='pending' ORDER BY waktu DESC LIMIT ?""", (limit,))
        rows = c.fetchall()
        conn.close()
        return rows

def get_topup_by_id(id):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM topup_pending WHERE id=?", (id,))
        row = c.fetchone()
        conn.close()
        return row

def simpan_kode_unik(kode, user_id, nominal):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""INSERT INTO kode_unik_topup 
            (kode, user_id, nominal, digunakan, dibuat_pada) 
            VALUES (?, ?, ?, 0, ?)""",
            (kode, user_id, nominal, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

def get_kode_unik(kode):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM kode_unik_topup WHERE kode=?", (kode,))
        row = c.fetchone()
        conn.close()
        if row:
            return {
                "kode": row[0], "user_id": row[1], "nominal": row[2],
                "digunakan": row[3], "dibuat_pada": row[4], "digunakan_pada": row[5]
            }
        return None

def gunakan_kode_unik(kode):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("UPDATE kode_unik_topup SET digunakan=1, digunakan_pada=? WHERE kode=?",
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), kode))
        conn.commit()
        conn.close()

def get_kode_unik_user(user_id, limit=5):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM kode_unik_topup WHERE user_id=? ORDER BY dibuat_pada DESC LIMIT ?", (user_id, limit))
        rows = c.fetchall()
        conn.close()
        return [{
            "kode": r[0], "user_id": r[1], "nominal": r[2], "digunakan": r[3],
            "dibuat_pada": r[4], "digunakan_pada": r[5]
        } for r in rows]

# ========== PROVIDER ==========
def get_products():
    url = f"{PROVIDER_BASE_URL}list_product?api_key={PROVIDER_API_KEY}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get('data', [])

def create_transaction(produk, tujuan, reff_id):
    url = f"{PROVIDER_BASE_URL}trx"
    params = {
        "produk": produk,
        "tujuan": tujuan,
        "reff_id": reff_id,
        "api_key": PROVIDER_API_KEY
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def get_history(refid):
    url = f"{PROVIDER_BASE_URL}history?api_key={PROVIDER_API_KEY}&refid={refid}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

# ========== UTILS ==========
import time

class RateLimiter:
    def __init__(self, limit_per_minute=10):
        self.limit = limit_per_minute
        self.users = {}
        self.lock = threading.Lock()

    def check(self, user_id):
        now = int(time.time())
        with self.lock:
            data = self.users.get(user_id, [])
            data = [t for t in data if now - t < 60]
            if len(data) >= self.limit:
                return False
            data.append(now)
            self.users[user_id] = data
            return True

rate_limiter = RateLimiter()

# ========== WEBHOOK ==========
app = Flask(__name__)
from re import compile as re_compile

RX = re_compile(
    r'RC=(?P<reffid>[a-f0-9-]+)\s+TrxID=(?P<trxid>\d+)\s+'
    r'(?P<produk>[A-Z0-9]+)\.(?P<tujuan>\d+)\s+'
    r'(?P<status_text>[A-Za-z]+)\s*'
    r'(?P<keterangan>.+?)'
    r'(?:\s+Saldo[\s\S]*?)?'
    r'(?:\bresult=(?P<status_code>\d+))?\s*>?$',
    re_compile.I | re_compile.DOTALL
)

updater = None

@app.route('/webhook', methods=['GET', 'POST'])
def webhook_handler():
    try:
        message = request.args.get('message') or request.form.get('message')
        if not message:
            return jsonify({'ok': False, 'error': 'message kosong'}), 400
        match = RX.match(message)
        if not match:
            return jsonify({'ok': False, 'error': 'format tidak dikenali'}), 200

        groups = match.groupdict()
        reffid = groups.get('reffid')
        status_text = groups.get('status_text', '').lower()
        keterangan = groups.get('keterangan', '').strip()

        riwayat = get_riwayat_by_refid(reffid)
        if not riwayat:
            return jsonify({'ok': False, 'error': 'transaksi tidak ditemukan'}), 200

        (db_reffid, user_id, produk_kode, tujuan, harga, waktu, current_status, db_keterangan) = riwayat

        # Hindari update ganda
        if any(s in current_status.lower() for s in ("sukses", "gagal", "batal")):
            return jsonify({'ok': True, 'message': 'Status sudah final'}), 200

        update_riwayat_status(reffid, status_text.upper(), keterangan)

        if updater:
            try:
                bot = updater.bot
                if "sukses" in status_text:
                    bot.send_message(
                        user_id,
                        f"✅ <b>TRANSAKSI SUKSES</b>\n\n"
                        f"Produk [{produk_kode}] ke {tujuan} BERHASIL.\n"
                        f"Keterangan: {keterangan}\n"
                        f"Saldo akhir: Rp {get_saldo(user_id):,.0f}",
                        parse_mode=ParseMode.HTML
                    )
                elif "gagal" in status_text or "batal" in status_text:
                    tambah_saldo(user_id, harga)
                    bot.send_message(
                        user_id,
                        f"❌ <b>TRANSAKSI GAGAL</b>\n\n"
                        f"Produk [{produk_kode}] ke {tujuan} GAGAL.\n"
                        f"Keterangan: {keterangan}\n"
                        f"Saldo kembali: Rp {harga:,.0f}\nSaldo sekarang: Rp {get_saldo(user_id):,.0f}",
                        parse_mode=ParseMode.HTML
                    )
            except Exception as e:
                logger.error(f"Gagal kirim notif ke user {user_id}: {e}")
        return jsonify({'ok': True, 'message': 'Webhook diterima'}), 200

    except Exception as e:
        logger.exception("[WEBHOOK][ERROR]")
        return jsonify({'ok': False, 'error': 'internal_error'}), 500

# ========== HANDLER MENU ==========
def get_menu(uid):
    admin = uid in ADMIN_IDS
    menu = [
        [InlineKeyboardButton("🛒 Beli Produk", callback_data='order_start')],
        [InlineKeyboardButton("💳 Top Up Saldo", callback_data='topup_start')],
        [InlineKeyboardButton("📋 Riwayat", callback_data='riwayat')],
        [InlineKeyboardButton("🧾 Riwayat Top Up", callback_data='topup_riwayat')],
        [InlineKeyboardButton("📦 Info Stok", callback_data='cek_stok')],
        [InlineKeyboardButton("🔑 Kode Unik Saya", callback_data='my_kode_unik')],
        [InlineKeyboardButton("ℹ️ Bantuan", callback_data='bantuan')],
    ]
    if admin:
        menu.append([InlineKeyboardButton("👑 Panel Admin", callback_data='admin_panel')])
    return InlineKeyboardMarkup(menu)

def menu_router(update, context):
    query = update.callback_query
    data = query.data
    user = query.from_user
    is_admin = user.id in ADMIN_IDS

    if data == "main_menu":
        saldo = get_saldo(user.id)
        query.edit_message_text(
            f"🏠 <b>MENU UTAMA</b>\nSaldo kamu: <b>Rp {saldo:,.0f}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_menu(user.id)
        )
    elif data == "order_start":
        return order_start(update, context)
    elif data == "topup_start":
        return topup_start(update, context)
    elif data == "riwayat":
        items = get_riwayat_user(user.id, 10)
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
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    elif data == "topup_riwayat":
        items = get_topup_pending_by_user(user.id, 10)
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
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    elif data == "cek_stok":
        produk_list = get_products()
        msg = "📦 <b>Info Stok Produk</b>\n\n"
        for produk in produk_list:
            status = produk.get('status', 'Tersedia')
            emoji = "✅" if status == 'Tersedia' else "❌"
            msg += f"{emoji} [{produk['kode']}] {produk['nama']} ({status})\n"
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    elif data == "my_kode_unik":
        items = get_kode_unik_user(user.id, 5)
        msg = "🔑 <b>Kode Unik Top Up</b>\n\n"
        if not items:
            msg += "Belum ada kode unik."
        else:
            for kode in items:
                used = "✅" if kode["digunakan"] else "⏳"
                msg += (
                    f"{used} Kode: <code>{kode['kode']}</code>\n"
                    f"Nominal: Rp {kode['nominal']:,.0f}\n"
                    f"Dibuat: {kode['dibuat_pada']}\n"
                    f"Status: {'Digunakan' if kode['digunakan'] else 'Belum'}\n\n"
                )
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    elif data == "bantuan":
        msg = (
            "❓ <b>Bantuan</b>\n"
            "• Untuk order, klik 'Beli Produk'\n"
            "• Top up saldo, klik 'Top Up Saldo'\n"
            "• Riwayat transaksi/top up, klik menu terkait\n"
            "Jika ada kendala, hubungi admin."
        )
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    elif data == "admin_panel" and is_admin:
        return admin_panel(update, context)
    elif data == "admin_cekuser" and is_admin:
        users = get_all_users()
        msg = f"👤 <b>Data User</b>\nTotal: {len(users)} user\n\n"
        for u in users:
            msg += f"- {u[2]} (@{u[1]}) - ID: <code>{u[0]}</code>\n"
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    elif data == "lihat_saldo" and is_admin:
        users = get_all_users()
        msg = f"💰 <b>Saldo Semua User</b>\n\n"
        for u in users:
            saldo = get_saldo(u[0])
            msg += f"{u[2]}: Rp {saldo:,.0f}\n"
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    elif data == "semua_riwayat" and is_admin:
        items = get_all_riwayat(10)
        msg = "📊 <b>Semua Riwayat Transaksi</b>\n\n"
        if not items:
            msg += "Belum ada transaksi."
        else:
            for r in items:
                status = r[6].upper()
                emoji = "✅" if "SUKSES" in status else ("❌" if "GAGAL" in status else "⏳")
                msg += (
                    f"{emoji} {r[5]} | {r[1]} | {r[2]} ke {r[3]}\n"
                    f"Harga: Rp {r[4]:,.2f} | Status: {status}\n\n"
                )
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    else:
        query.answer("Menu tidak tersedia.", show_alert=True)

def admin_panel(update, context):
    query = update.callback_query
    query.edit_message_text(
        "👑 <b>PANEL ADMIN</b>\nPilih menu:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 Data User", callback_data='admin_cekuser')],
            [InlineKeyboardButton("💰 Lihat Saldo", callback_data='lihat_saldo')],
            [InlineKeyboardButton("📊 Semua Riwayat", callback_data='semua_riwayat')],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data='main_menu')]
        ])
    )
    return ConversationHandler.END

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    if not rate_limiter.check(user.id):
        update.message.reply_text("❗️Terlalu banyak permintaan. Coba lagi beberapa saat lagi.")
        return
    tambah_user(user.id, user.username or "", user.full_name)
    saldo = get_saldo(user.id)
    update.message.reply_text(
        f"Selamat datang, <b>{user.full_name}</b>!\nSaldo: <b>Rp {saldo:,.0f}</b>\nSilakan pilih menu:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_menu(user.id)
    )

def handle_text(update: Update, context: CallbackContext):
    update.message.reply_text("Gunakan tombol menu.", reply_markup=get_menu(update.effective_user.id))

def order_start(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text("🔄 Memuat daftar produk, mohon tunggu...")

    produk_list = get_products()
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
    return ConversationHandler.END

def topup_start(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "💳 <b>TOP UP SALDO</b>\n\nSilakan transfer ke QRIS berikut, lalu upload bukti transfer di sini.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data="main_menu")]])
    )
    # Simulasi, tinggal integrasi QRIS API jika ada

def main():
    init_db()
    global updater
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CallbackQueryHandler(menu_router))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    # Jalankan webhook Flask di thread terpisah
    flask_thread = threading.Thread(target=app.run, kwargs={
        "host": "0.0.0.0",
        "port": WEBHOOK_PORT
    })
    flask_thread.daemon = True
    flask_thread.start()

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
