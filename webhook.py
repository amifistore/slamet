from flask import Flask, request, jsonify
import re
import logging
import db
from telegram import ParseMode
from config import get_config

app = Flask(__name__)
cfg = get_config()

# Regex sesuai dokumentasi provider
RX = re.compile(
    r'RC=(?P<reffid>[a-f0-9-]+)\s+TrxID=(?P<trxid>\d+)\s+'
    r'(?P<produk>[A-Z0-9]+)\.(?P<tujuan>\d+)\s+'
    r'(?P<status_text>[A-Za-z]+)\s*'
    r'(?P<keterangan>.+?)'
    r'(?:\s+Saldo[\s\S]*?)?'
    r'(?:\bresult=(?P<status_code>\d+))?\s*>?$',
    re.I | re.DOTALL
)

# updater harus di-set dari main.py (setelah Updater dibuat)
updater = None

@app.route('/webhook', methods=['GET', 'POST'])
def webhook_handler():
    try:
        message = request.args.get('message') or request.form.get('message')
        if not message:
            logging.warning("[WEBHOOK] Pesan kosong diterima.")
            return jsonify({'ok': False, 'error': 'message kosong'}), 400

        logging.info(f"[WEBHOOK] RAW: {message}")
        match = RX.match(message)
        if not match:
            logging.warning(f"[WEBHOOK] Format tidak dikenali -> {message}")
            return jsonify({'ok': False, 'error': 'format tidak dikenali'}), 200

        groups = match.groupdict()
        reffid = groups.get('reffid')
        status_text = groups.get('status_text', '').lower()
        keterangan = groups.get('keterangan', '').strip()

        logging.info(f"Webhook ter-parse -> RefID: {reffid}, Status: {status_text}")

        riwayat = db.get_riwayat_by_refid(reffid)
        if not riwayat:
            logging.warning(f"RefID {reffid} tidak ditemukan di database.")
            return jsonify({'ok': False, 'error': 'transaksi tidak ditemukan'}), 200

        (db_reffid, user_id, produk_kode, tujuan, harga, waktu, current_status, db_keterangan) = riwayat

        # Hindari update ganda (sudah sukses/gagal)
        if any(s in current_status.lower() for s in ("sukses", "gagal", "batal")):
            logging.info(f"RefID {reffid} sudah status final. Update diabaikan.")
            return jsonify({'ok': True, 'message': 'Status sudah final'}), 200

        # Update status transaksi di DB
        db.update_riwayat_status(reffid, status_text.upper(), keterangan)

        # Beri notifikasi user
        if updater:
            try:
                bot = updater.bot
                if "sukses" in status_text:
                    bot.send_message(
                        user_id,
                        f"✅ <b>TRANSAKSI SUKSES</b>\n\n"
                        f"Produk [{produk_kode}] ke {tujuan} BERHASIL.\n"
                        f"Keterangan: {keterangan}\n"
                        f"Saldo akhir: Rp {db.get_saldo(user_id):,.0f}",
                        parse_mode=ParseMode.HTML
                    )
                elif "gagal" in status_text or "batal" in status_text:
                    db.tambah_saldo(user_id, harga)
                    bot.send_message(
                        user_id,
                        f"❌ <b>TRANSAKSI GAGAL</b>\n\n"
                        f"Produk [{produk_kode}] ke {tujuan} GAGAL.\n"
                        f"Keterangan: {keterangan}\n"
                        f"Saldo kembali: Rp {harga:,.0f}\nSaldo sekarang: Rp {db.get_saldo(user_id):,.0f}",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    pass # Status non-final, abaikan
            except Exception as e:
                logging.error(f"Gagal kirim notif ke user {user_id}: {e}")
        return jsonify({'ok': True, 'message': 'Webhook diterima'}), 200

    except Exception as e:
        logging.exception("[WEBHOOK][ERROR]")
        return jsonify({'ok': False, 'error': 'internal_error'}), 500
