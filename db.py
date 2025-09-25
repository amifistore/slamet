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
        c.execute("""
            CREATE TABLE IF NOT EXISTS produk (
                kode TEXT PRIMARY KEY,
                nama TEXT,
                harga REAL,
                deskripsi TEXT,
                aktif INTEGER DEFAULT 1
            )
        """)
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT, nama TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS saldo (
            user_id INTEGER PRIMARY KEY, saldo REAL DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS riwayat_transaksi (
            id TEXT PRIMARY KEY, user_id INTEGER, produk TEXT, tujuan TEXT, harga REAL, waktu TEXT, status_text TEXT, keterangan TEXT)""")
        conn.commit()
        conn.close()

# PRODUK
def get_all_produk(show_nonaktif=False):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        if show_nonaktif:
            c.execute("SELECT kode, nama, harga, deskripsi, aktif FROM produk ORDER BY nama ASC")
        else:
            c.execute("SELECT kode, nama, harga, deskripsi, aktif FROM produk WHERE aktif=1 ORDER BY nama ASC")
        rows = c.fetchall()
        conn.close()
        return rows

def get_produk_by_kode(kode):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT kode, nama, harga, deskripsi, aktif FROM produk WHERE kode=?", (kode,))
        row = c.fetchone()
        conn.close()
        return row

def add_produk(kode, nama, harga, deskripsi, aktif=1):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO produk (kode, nama, harga, deskripsi, aktif) VALUES (?, ?, ?, ?, ?)",
                  (kode, nama, harga, deskripsi, aktif))
        conn.commit()
        conn.close()

def update_produk(kode, nama=None, harga=None, deskripsi=None, aktif=None):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        if nama is not None:
            c.execute("UPDATE produk SET nama=? WHERE kode=?", (nama, kode))
        if harga is not None:
            c.execute("UPDATE produk SET harga=? WHERE kode=?", (harga, kode))
        if deskripsi is not None:
            c.execute("UPDATE produk SET deskripsi=? WHERE kode=?", (deskripsi, kode))
        if aktif is not None:
            c.execute("UPDATE produk SET aktif=? WHERE kode=?", (aktif, kode))
        conn.commit()
        conn.close()

def delete_produk(kode):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM produk WHERE kode=?", (kode,))
        conn.commit()
        conn.close()

# USER & SALDO
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
