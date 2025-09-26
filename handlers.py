import json
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from provider import create_trx, history, cek_stock_akrab
from provider_qris import generate_qris
from markup import get_menu, produk_inline_keyboard, admin_edit_produk_keyboard, is_admin
from produk import get_produk_list, edit_produk, get_produk_by_kode
from utils import (
    get_saldo, set_saldo, load_riwayat, save_riwayat, load_topup, save_topup, format_stock_akrab
)

CHOOSING_PRODUK, INPUT_TUJUAN, KONFIRMASI, TOPUP_NOMINAL, ADMIN_EDIT = range(5)

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    update.message.reply_text(
        f"Halo <b>{user.first_name}</b>!\nGunakan menu di bawah.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_menu(user.id)
    )

def main_menu_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    data = query.data
    query.answer()
    if data == 'lihat_produk':
        produk_list = get_produk_list()
        msg = "<b>Daftar Produk:</b>\n"
        for p in produk_list:
            msg += f"<code>{p['kode']}</code> | {p['nama']} | <b>Rp {p['harga']:,}</b> | Kuota: {p['kuota']}\n"
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    elif data == 'beli_produk':
        query.edit_message_text("Pilih produk yang ingin dibeli:", reply_markup=produk_inline_keyboard())
        context.user_data.clear()
        return CHOOSING_PRODUK
    elif data == 'topup':
        query.edit_message_text(
            "Masukkan nominal Top Up saldo yang diinginkan (minimal 10.000):",
            parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
        return TOPUP_NOMINAL
    elif data == 'cek_status':
        query.edit_message_text("Kirim format: <code>CEK|refid</code>", parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    elif data == 'riwayat':
        riwayat_user(query, context)
    elif data == 'stock_akrab':
        raw = cek_stock_akrab()
        msg = format_stock_akrab(raw)
        if isinstance(msg, str) and msg.strip().lower().startswith("<html"):
            msg = "❌ Provider membalas data tidak valid."
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    elif data == 'semua_riwayat' and is_admin(user.id):
        semua_riwayat(query, context)
    elif data == 'lihat_saldo' and is_admin(user.id):
        saldo = get_saldo()
        query.edit_message_text(f"Saldo bot: <b>Rp {saldo:,}</b>", parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    elif data == 'tambah_saldo' and is_admin(user.id):
        query.edit_message_text("Kirim format: <code>TAMBAH|jumlah</code>", parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    elif data == 'manajemen_produk' and is_admin(user.id):
        produk_list = get_produk_list()
        msg = "<b>Manajemen Produk:</b>\n"
        keyboard = []
        for p in produk_list:
            keyboard.append([InlineKeyboardButton(f"{p['kode']} | {p['nama']}", callback_data=f"admin_edit_produk|{p['kode']}")])
        keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="back_admin")])
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("admin_edit_produk|") and is_admin(user.id):
        kode = data.split("|")[1]
        p = get_produk_by_kode(kode)
        if not p:
            query.edit_message_text("Produk tidak ditemukan.", reply_markup=get_menu(user.id))
            return ConversationHandler.END
        msg = (f"<b>Edit Produk {p['kode']}:</b>\n"
               f"Nama: {p['nama']}\nHarga: Rp {p['harga']:,}\nKuota: {p['kuota']}\nDeskripsi: {p['deskripsi']}\n\n"
               "Pilih field yang ingin diedit:")
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=admin_edit_produk_keyboard(kode))
        context.user_data["edit_kode"] = kode
        return ADMIN_EDIT
    elif data == "back_admin":
        query.edit_message_text("Kembali ke menu admin.", reply_markup=get_menu(user.id))
    elif data.startswith("editharga|"):
        context.user_data["edit_field"] = "harga"
        kode = context.user_data.get("edit_kode")
        query.edit_message_text(f"Masukkan harga baru untuk produk <b>{kode}</b> (angka):", parse_mode="HTML")
        return ADMIN_EDIT
    elif data.startswith("editkuota|"):
        query.edit_message_text("Stok produk mengikuti provider dan tidak bisa diedit manual.", reply_markup=get_menu(user.id))
        return ConversationHandler.END
    elif data.startswith("editdeskripsi|"):
        context.user_data["edit_field"] = "deskripsi"
        kode = context.user_data.get("edit_kode")
        query.edit_message_text(f"Masukkan deskripsi baru untuk produk <b>{kode}</b>:", parse_mode="HTML")
        return ADMIN_EDIT
    else:
        query.edit_message_text("Menu tidak dikenal.", reply_markup=get_menu(user.id))
    return ConversationHandler.END

def admin_edit_produk_step(update, context):
    kode = context.user_data.get("edit_kode")
    field = context.user_data.get("edit_field")
    value = update.message.text.strip()
    p = get_produk_by_kode(kode)
    if not kode or not field or not p:
        update.message.reply_text(
            "❌ Kueri tidak valid. Silakan ulangi.",
            reply_markup=get_menu(update.effective_user.id)
        )
        return ConversationHandler.END

    # Edit harga
    if field == "harga":
        try:
            harga = int(value.replace(".", "").replace(",", ""))
            if harga <= 0:
                raise ValueError("Harga harus lebih dari 0.")
            old_harga = p["harga"]
            edit_produk(kode, harga=harga)
            p_new = get_produk_by_kode(kode)
            update.message.reply_text(
                f"✅ <b>Harga produk berhasil diupdate!</b>\n\n"
                f"Produk: <b>{kode}</b> - {p_new['nama']}\n"
                f"Harga lama: <s>Rp {old_harga:,}</s>\n"
                f"Harga baru: <b>Rp {p_new['harga']:,}</b>\n"
                f"Deskripsi: {p_new['deskripsi']}",
                parse_mode="HTML",
                reply_markup=get_menu(update.effective_user.id)
            )
        except Exception as e:
            update.message.reply_text(
                f"❌ <b>Gagal update harga produk!</b>\n"
                f"Produk: <b>{kode}</b> - {p['nama']}\n"
                f"Error: {e}",
                parse_mode="HTML",
                reply_markup=get_menu(update.effective_user.id)
            )
        return ConversationHandler.END

    # Edit deskripsi
    elif field == "deskripsi":
        try:
            old_deskripsi = p["deskripsi"]
            edit_produk(kode, deskripsi=value)
            p_new = get_produk_by_kode(kode)
            update.message.reply_text(
                f"✅ <b>Deskripsi produk berhasil diupdate!</b>\n\n"
                f"Produk: <b>{kode}</b> - {p_new['nama']}\n"
                f"Deskripsi lama: <code>{old_deskripsi}</code>\n"
                f"Deskripsi baru: <b>{p_new['deskripsi']}</b>",
                parse_mode="HTML",
                reply_markup=get_menu(update.effective_user.id)
            )
        except Exception as e:
            update.message.reply_text(
                f"❌ <b>Gagal update deskripsi produk!</b>\n"
                f"Produk: <b>{kode}</b> - {p['nama']}\n"
                f"Error: {e}",
                parse_mode="HTML",
                reply_markup=get_menu(update.effective_user.id)
            )
        return ConversationHandler.END

    else:
        update.message.reply_text(
            "❌ Field tidak dikenal.",
            reply_markup=get_menu(update.effective_user.id)
        )
        return ConversationHandler.END

def produk_pilih_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    data = query.data
    query.answer()
    if data.startswith("produk_static|"):
        idx = int(data.split("|")[1])
        produk_list = get_produk_list()
        if idx >= len(produk_list):
            query.edit_message_text("Produk tidak valid.", reply_markup=get_menu(user.id))
            return ConversationHandler.END
        p = produk_list[idx]
        context.user_data["produk"] = p
        query.edit_message_text(
            f"Produk yang dipilih:\n<b>{p['kode']}</b> - {p['nama']}\nHarga: Rp {p['harga']:,}\nKuota: {p['kuota']}\n\nSilakan input nomor tujuan:",
            parse_mode=ParseMode.HTML
        )
        return INPUT_TUJUAN
    return ConversationHandler.END

def input_tujuan_step(update: Update, context: CallbackContext):
    tujuan = update.message.text.strip()
    if not tujuan.isdigit() or len(tujuan) < 9:
        update.message.reply_text("Format nomor tidak valid. Masukkan ulang.")
        return INPUT_TUJUAN
    context.user_data["tujuan"] = tujuan
    p = context.user_data.get("produk")
    update.message.reply_text(
        f"Konfirmasi pesanan:\nProduk: <b>{p['kode']}</b> - {p['nama']}\nHarga: Rp {p['harga']:,}\nNomor: <b>{tujuan}</b>\n\nKetik 'YA' untuk konfirmasi atau 'BATAL' untuk membatalkan.",
        parse_mode=ParseMode.HTML
    )
    return KONFIRMASI

def konfirmasi_step(update: Update, context: CallbackContext):
    text = update.message.text.strip().upper()
    if text == "BATAL":
        update.message.reply_text("Transaksi dibatalkan.", reply_markup=get_menu(update.effective_user.id))
        return ConversationHandler.END
    if text != "YA":
        update.message.reply_text("Ketik 'YA' untuk konfirmasi atau 'BATAL' untuk batal.")
        return KONFIRMASI
    p = context.user_data.get("produk")
    harga = p["harga"]
    tujuan = context.user_data.get("tujuan")
    saldo = get_saldo()
    if saldo < harga:
        update.message.reply_text("Saldo bot tidak cukup.", reply_markup=get_menu(update.effective_user.id))
        return ConversationHandler.END
    data = create_trx(p["kode"], tujuan)
    update.message.reply_text(
        f"<b>Respon API:</b>\n<pre>{json.dumps(data, indent=2, ensure_ascii=False)}</pre>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_menu(update.effective_user.id)
    )
    if not data or not data.get("refid"):
        err_msg = data.get("message", "Gagal membuat transaksi.") if data else "Tidak ada respon API."
        update.message.reply_text(f"Gagal membuat transaksi:\n<b>{err_msg}</b>", parse_mode=ParseMode.HTML, reply_markup=get_menu(update.effective_user.id))
        return ConversationHandler.END
    riwayat = load_riwayat()
    refid = data["refid"]
    user = update.effective_user
    riwayat[refid] = {
        "trxid": data.get("trxid", ""),
        "reffid": refid,
        "produk": p["kode"],
        "tujuan": tujuan,
        "status_text": data.get("status", "pending"),
        "status_code": None,
        "keterangan": data.get("message", ""),
        "waktu": data.get("waktu", ""),
        "harga": harga,
        "user_id": user.id,
        "username": user.username or "",
        "nama": user.full_name,
    }
    save_riwayat(riwayat)
    set_saldo(saldo-harga)
    update.message.reply_text(
        f"Transaksi dibuat!\nProduk: {p['kode']}\nTujuan: {tujuan}\nRefID: <code>{refid}</code>\nStatus: {data.get('status','pending')}\nSaldo bot: Rp {saldo-harga:,}",
        parse_mode=ParseMode.HTML,
        reply_markup=get_menu(user.id)
    )
    return ConversationHandler.END

def topup_nominal_step(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    try:
        nominal = int(text.replace(".", "").replace(",", ""))
        if nominal < 10000:
            raise Exception
    except Exception:
        update.message.reply_text("Nominal minimal 10.000. Masukkan kembali nominal:")
        return TOPUP_NOMINAL
    context.user_data["topup_nominal"] = nominal

    resp = generate_qris(nominal)
    if resp.get("status") != "success":
        update.message.reply_text(f"Gagal generate QRIS: {resp.get('message')}")
        return ConversationHandler.END
    qris_base64 = resp.get("qris_base64")
    msg = f"Silakan lakukan pembayaran Top Up sebesar <b>Rp {nominal:,}</b>\n\nScan QRIS berikut:"
    if qris_base64:
        update.message.reply_photo(photo=f"data:image/png;base64,{qris_base64}", caption=msg, parse_mode=ParseMode.HTML)
    else:
        update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    return ConversationHandler.END

def riwayat_user(query, context):
    user = query.from_user
    riwayat = load_riwayat()
    items = [r for r in riwayat.values() if r.get("user_id") == user.id]
    items = sorted(items, key=lambda x: x.get("waktu", ""), reverse=True)
    msg = "<b>Riwayat Transaksi Anda:</b>\n"
    for r in items[:10]:
        msg += (
            f"{r.get('waktu','')} | <code>{r['reffid']}</code>\n"
            f"{r['produk']} ke {r['tujuan']} | Rp {r['harga']:,}\n"
            f"Status: <b>{r['status_text']}</b>\n\n"
        )
    if not items:
        msg += "Belum ada transaksi."
    query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))

def semua_riwayat(query, context):
    riwayat = list(load_riwayat().values())
    riwayat = sorted(riwayat, key=lambda x: x.get("waktu", ""), reverse=True)
    msg = "<b>Semua Riwayat Transaksi (max 30):</b>\n"
    for r in riwayat[:30]:
        msg += (
            f"{r.get('waktu','')} | <code>{r['reffid']}</code>\n"
            f"{r['produk']} ke {r['tujuan']} | Rp {r['harga']:,}\n"
            f"Status: <b>{r['status_text']}</b> | User: {r.get('username','-')}\n\n"
        )
    if not riwayat:
        msg += "Belum ada transaksi."
    query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(query.from_user.id))

def handle_text(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    user = update.effective_user
    isadmin = is_admin(user.id)
    if text.startswith("CEK|"):
        refid = text.split("|", 1)[1]
        data = history(refid)
        update.message.reply_text(
            f"<b>Respon API:</b>\n<pre>{json.dumps(data, indent=2, ensure_ascii=False)}</pre>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_menu(user.id)
        )
        if not data:
            update.message.reply_text("Gagal cek status transaksi.", reply_markup=get_menu(user.id))
            return
        msg = f"Status transaksi <code>{refid}</code>:\n"
        for k, v in data.items():
            msg += f"<b>{k}</b>: {v}\n"
        update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    elif text.startswith("TAMBAH|") and isadmin:
        try:
            tambah = int(text.split("|", 1)[1])
            saldo = get_saldo() + tambah
            set_saldo(saldo)
            update.message.reply_text(f"Saldo ditambah. Saldo sekarang: <b>Rp {saldo:,}</b>", parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
        except Exception:
            update.message.reply_text("Nilai tidak valid.", reply_markup=get_menu(user.id))
    else:
        update.message.reply_text("Gunakan menu.", reply_markup=get_menu(user.id))
