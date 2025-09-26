def format_stock_akrab(json_data):
    import json as _json
    # Jika response dari provider adalah HTML (error), jangan kirim ke Telegram!
    if isinstance(json_data, str) and "<html" in json_data.lower():
        return "<b>❌ Provider error (balikkan HTML). Cek server provider!</b>"
    if not json_data or (isinstance(json_data, str) and not json_data.strip()):
        return "<b>❌ Gagal mengambil data stok dari provider.</b>\nSilakan cek koneksi/API provider."
    if isinstance(json_data, dict):
        data = json_data
    else:
        try:
            data = _json.loads(json_data)
        except Exception as e:
            # Jika json_data HTML, juga akan jatuh ke sini
            if isinstance(json_data, str) and "<html" in json_data.lower():
                return "<b>❌ Provider error (balikkan HTML). Cek server provider!</b>"
            return f"<b>❌ Error parsing data stok:</b>\n<pre>{e}\n{json_data}</pre>"
    items = data.get("data", [])
    if not items:
        return "<b>Stok kosong atau tidak ditemukan.</b>"
    msg = "<b>📊 Cek Stok Produk Akrab:</b>\n\n"
    msg += "<b>Kode      | Nama                | Sisa Slot</b>\n"
    msg += "<pre>"
    for item in items:
        kode = item['type'].ljust(8)
        nama = item['nama'].ljust(20)
        slot = str(item['sisa_slot']).rjust(4)
        msg += f"{kode} | {nama} | {slot}\n"
    msg += "</pre>"
    return msg
