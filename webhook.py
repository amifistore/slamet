from flask import Flask, request, jsonify
import re
import logging

app = Flask(__name__)

# Regex KHFY
RX = re.compile(
    r'RC=(?P<reffid>[a-f0-9-]+)\s+TrxID=(?P<trxid>\d+)\s+'
    r'(?P<produk>[A-Z0-9]+)\.(?P<tujuan>\d+)\s+'
    r'(?P<status_text>[A-Za-z]+)\s*'
    r'(?P<keterangan>.+?)'
    r'(?:\s+Saldo[\s\S]*?)?'
    r'(?:\bresult=(?P<status_code>\d+))?\s*>?$',
    re.I | re.DOTALL
)

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
        # TODO: update DB, notif user, dsb.
        return jsonify({'ok': True, 'parsed': groups}), 200
    except Exception as e:
        logging.exception("[WEBHOOK][ERROR]")
        return jsonify({'ok': False, 'error': 'internal_error'}), 500
