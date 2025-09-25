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
        c.execute("""CREATE TABLE IF NOT EXISTS kode_unik_topup (
            kode TEXT PRIMARY KEY, user_id INTEGER, nominal REAL, digunakan INTEGER DEFAULT 0, dibuat_pada TEXT, digunakan_pada TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS produk_local (
            kode TEXT PRIMARY KEY, harga REAL, deskripsi TEXT)""")
        conn.commit()
        conn.close()

# User & saldo
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

# Riwayat transaksi
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

# Produk lokal (override harga/deskripsi)
def set_produk_local(kode, harga=None, deskripsi=None):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO produk_local (kode, harga, deskripsi) VALUES (?, NULL, NULL)", (kode,))
        if harga is not None:
            c.execute("UPDATE produk_local SET harga=? WHERE kode=?", (harga, kode))
        if deskripsi is not None:
            c.execute("UPDATE produk_local SET deskripsi=? WHERE kode=?", (deskripsi, kode))
        conn.commit()
        conn.close()

def get_produk_override(kode):
    with db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT harga, deskripsi FROM produk_local WHERE kode=?", (kode,))
        row = c.fetchone()
        conn.close()
        return {"harga": row[0], "deskripsi": row[1]} if row else {}
