import sqlite3
import threading
from datetime import datetime

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
        c.execute("""CREATE TABLE IF NOT EXISTS produk_admin (
            kode TEXT PRIMARY KEY, harga REAL, deskripsi TEXT, nama TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS kode_unik_topup (
            kode TEXT PRIMARY KEY, user_id INTEGER, nominal REAL, digunakan INTEGER DEFAULT 0, dibuat_pada TEXT, digunakan_pada TEXT)""")
        conn.commit()
        conn.close()

# USER
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

# SALDO
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

# TRANSAKSI
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

def get_riwayat_jml(user_id):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM riwayat_transaksi WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else 0

# TOPUP PENDING
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

# PRODUK ADMIN (Full Custom Support: nama, harga, deskripsi)
def set_produk_admin_nama(kode, nama):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        # Urutan: kode, harga, deskripsi, nama
        c.execute("INSERT OR IGNORE INTO produk_admin (kode, harga, deskripsi, nama) VALUES (?, 0, '', ?)", (kode, nama))
        c.execute("UPDATE produk_admin SET nama=? WHERE kode=?", (nama, kode))
        conn.commit()
        conn.close()

def set_produk_admin_harga(kode, harga):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        # Urutan: kode, harga, deskripsi, nama
        c.execute("INSERT OR IGNORE INTO produk_admin (kode, harga, deskripsi, nama) VALUES (?, ?, '', '')", (kode, harga))
        c.execute("UPDATE produk_admin SET harga=? WHERE kode=?", (harga, kode))
        conn.commit()
        conn.close()

def set_produk_admin_deskripsi(kode, deskripsi):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        # Urutan: kode, harga, deskripsi, nama
        c.execute("INSERT OR IGNORE INTO produk_admin (kode, harga, deskripsi, nama) VALUES (?, 0, ?, '')", (kode, deskripsi))
        c.execute("UPDATE produk_admin SET deskripsi=? WHERE kode=?", (deskripsi, kode))
        conn.commit()
        conn.close()

def get_all_produk_admin():
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT kode, harga, deskripsi, nama FROM produk_admin")
        rows = c.fetchall()
        conn.close()
        produk_dict = {}
        for row in rows:
            produk_dict[row[0].lower()] = {
                "harga": row[1], "deskripsi": row[2], "nama": row[3]
            }
        return produk_dict

def get_produk_admin(kode):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT harga, deskripsi, nama FROM produk_admin WHERE kode=?", (kode,))
        row = c.fetchone()
        conn.close()
        if row:
            return {"harga": row[0], "deskripsi": row[1], "nama": row[2]}
        return None

# KODE UNIK TOPUP
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
