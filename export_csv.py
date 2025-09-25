import csv
import db

def export_transaksi_csv(filename="riwayat_transaksi.csv"):
    rows = db.get_all_riwayat(10000)  # export maximal 10.000, ganti sesuai kebutuhan
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "reffid", "user_id", "kode_produk", "tujuan", "harga", "waktu", "status", "keterangan"
        ])
        for r in rows:
            writer.writerow(r)
    print(f"Export transaksi selesai ke {filename}")

def export_topup_csv(filename="topup.csv"):
    # Mirip, silakan buat get_all_topup() di db.py jika ingin semua data, atau pakai SELECT * FROM topup_pending
    import sqlite3
    conn = sqlite3.connect("botdata.db")
    c = conn.cursor()
    c.execute("SELECT * FROM topup_pending")
    rows = c.fetchall()
    conn.close()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "user_id", "username", "nama", "nominal", "waktu", "status", "bukti_file_id", "bukti_caption"
        ])
        for r in rows:
            writer.writerow(r)
    print(f"Export top up selesai ke {filename}")

if __name__ == "__main__":
    export_transaksi_csv()
    export_topup_csv()
