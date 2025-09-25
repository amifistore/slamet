import sqlite3
import threading

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
            kode TEXT PRIMARY KEY, harga REAL, deskripsi TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS kode_unik_topup (
            kode TEXT PRIMARY KEY, user_id INTEGER, nominal REAL, digunakan INTEGER DEFAULT 0, dibuat_pada TEXT, digunakan_pada TEXT)""")
        conn.commit()
        conn.close()

# (tambahkan semua fungsi DB kamu di sini, gunakan db_lock untuk semua operasi tulis)
