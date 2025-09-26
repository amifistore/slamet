import json
import logging
from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler, CommandHandler

from provider import create_trx, history, cek_stock_akrab
from provider_qris import generate_qris
from markup import get_menu, produk_inline_keyboard, admin_edit_produk_keyboard, is_admin
from produk import get_produk_list, edit_produk, get_produk_by_kode
from utils import (
    get_saldo, set_saldo, load_riwayat, save_riwayat, load_topup, save_topup, format_stock_akrab
)

# Setup logging
logger = logging.getLogger(__name__)

# Conversation states
CHOOSING_PRODUK, INPUT_TUJUAN, KONFIRMASI, TOPUP_NOMINAL, ADMIN_EDIT = range(5)

def start(update: Update, context: CallbackContext):
    """Handler untuk command /start"""
    user = update.effective_user
    update.message.reply_text(
        f"Halo <b>{user.first_name}</b>!\nGunakan menu di bawah.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_menu(user.id)
    )

def help_command(update: Update, context: CallbackContext):
    """Handler untuk command /help"""
    help_text = """
🤖 <b>BOT DIGITAL PRODUCT</b>

<b>Fitur Utama:</b>
• 📦 Beli produk digital
• 💰 Top Up saldo via QRIS
• 📜 Cek riwayat transaksi
• 🔍 Cek status transaksi
• 📊 Cek stok provider

<b>Perintah Admin:</b>
• 👥 Lihat semua riwayat
• 💳 Kelola saldo bot
• 🛠️ Manajemen produk

Gunakan menu di bawah untuk mulai menggunakan bot.
    """
    update.message.reply_text(help_text, parse_mode=ParseMode.HTML, reply_markup=get_menu(update.effective_user.id))

def cancel(update: Update, context: CallbackContext):
    """Handler untuk membatalkan conversation"""
    user = update.effective_user
    context.user_data.clear()
    
    if update.message:
        update.message.reply_text(
            "❌ Operasi dibatalkan.",
            reply_markup=get_menu(user.id)
        )
    elif update.callback_query:
        update.callback_query.message.reply_text(
            "❌ Operasi dibatalkan.",
            reply_markup=get_menu(user.id)
        )
    
    return ConversationHandler.END

def main_menu_callback(update: Update, context: CallbackContext):
    """Handler untuk callback query dari menu utama"""
    query = update.callback_query
    user = query.from_user
    data = query.data
    query.answer()
    
    logger.info(f"User {user.id} memilih menu: {data}")
    
    # Clear user data ketika memulai operasi baru
    context.user_data.clear()
    
    if data == 'lihat_produk':
        return handle_lihat_produk(query, context)
    
    elif data == 'beli_produk':
        return handle_beli_produk(query, context)
    
    elif data == 'topup':
        return handle_topup(query, context)
    
    elif data == 'cek_status':
        return handle_cek_status(query, context)
    
    elif data == 'riwayat':
        return handle_riwayat_user(query, context)
    
    elif data == 'stock_akrab':
        return handle_stock_akrab(query, context)
    
    elif data == 'semua_riwayat' and is_admin(user.id):
        return handle_semua_riwayat(query, context)
    
    elif data == 'lihat_saldo' and is_admin(user.id):
        return handle_lihat_saldo(query, context)
    
    elif data == 'tambah_saldo' and is_admin(user.id):
        return handle_tambah_saldo(query, context)
    
    elif data == 'manajemen_produk' and is_admin(user.id):
        return handle_manajemen_produk(query, context)
    
    elif data.startswith("admin_edit_produk|") and is_admin(user.id):
        return handle_admin_edit_produk(query, context, data)
    
    elif data.startswith("editharga|") and is_admin(user.id):
        return handle_edit_harga(query, context, data)
    
    elif data.startswith("editdeskripsi|") and is_admin(user.id):
        return handle_edit_deskripsi(query, context, data)
    
    elif data.startswith("resetcustom|") and is_admin(user.id):
        return handle_reset_custom(query, context, data)
    
    elif data == "back_admin":
        return handle_back_admin(query, context)
    
    elif data == "back_main":
        return handle_back_main(query, context)
    
    else:
        query.edit_message_text(
            "❌ Menu tidak dikenal.", 
            reply_markup=get_menu(user.id)
        )
        return ConversationHandler.END

# === HANDLER FUNCTIONS ===

def handle_lihat_produk(query, context):
    """Menampilkan daftar produk"""
    try:
        produk_list = get_produk_list()
        if not produk_list:
            query.edit_message_text(
                "❌ Tidak ada produk tersedia.", 
                reply_markup=get_menu(query.from_user.id)
            )
            return ConversationHandler.END
        
        msg = "<b>🛍️ Daftar Produk:</b>\n\n"
        for p in produk_list:
            status = "✅" if p.get('kuota', 0) > 0 else "❌"
            msg += f"{status} <code>{p['kode']}</code> | {p['nama']} | <b>Rp {p['harga']:,}</b> | Stok: {p['kuota']}\n"
        
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(query.from_user.id))
    except Exception as e:
        logger.error(f"Error melihat produk: {e}")
        query.edit_message_text(
            "❌ Gagal memuat daftar produk.", 
            reply_markup=get_menu(query.from_user.id)
        )
    
    return ConversationHandler.END

def handle_beli_produk(query, context):
    """Memulai proses pembelian produk"""
    query.edit_message_text(
        "🛒 Pilih produk yang ingin dibeli:", 
        reply_markup=produk_inline_keyboard()
    )
    return CHOOSING_PRODUK

def handle_topup(query, context):
    """Memulai proses topup saldo"""
    query.edit_message_text(
        "💰 <b>Top Up Saldo</b>\n\nMasukkan nominal Top Up (minimal Rp 10.000):\n\nKetik /batal untuk membatalkan.",
        parse_mode=ParseMode.HTML
    )
    return TOPUP_NOMINAL

def handle_cek_status(query, context):
    """Menampilkan instruksi cek status"""
    query.edit_message_text(
        "🔍 <b>Cek Status Transaksi</b>\n\nKirim format: <code>CEK|refid</code>\nContoh: <code>CEK|TRX123456</code>", 
        parse_mode=ParseMode.HTML, 
        reply_markup=get_menu(query.from_user.id)
    )
    return ConversationHandler.END

def handle_riwayat_user(query, context):
    """Menampilkan riwayat transaksi user"""
    user = query.from_user
    try:
        riwayat = load_riwayat()
        items = [r for r in riwayat.values() if r.get("user_id") == user.id]
        items = sorted(items, key=lambda x: x.get("waktu", ""), reverse=True)
        
        if not items:
            query.edit_message_text(
                "📭 Anda belum memiliki riwayat transaksi.",
                reply_markup=get_menu(user.id)
            )
            return ConversationHandler.END
        
        msg = "<b>📜 Riwayat Transaksi Anda:</b>\n\n"
        for i, r in enumerate(items[:10], 1):
            status_icon = "✅" if r['status_text'].lower() == 'success' else "⏳" if r['status_text'].lower() == 'pending' else "❌"
            msg += (
                f"{i}. {status_icon} <b>{r['produk']}</b>\n"
                f"   📱 {r['tujuan']} | 💰 Rp {r['harga']:,}\n"
                f"   🆔 <code>{r['reffid']}</code>\n"
                f"   ⏰ {r.get('waktu','')}\n"
                f"   📊 {r['status_text']}\n\n"
            )
            
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(user.id))
    except Exception as e:
        logger.error(f"Error memuat riwayat user: {e}")
        query.edit_message_text(
            "❌ Gagal memuat riwayat transaksi.", 
            parse_mode=ParseMode.HTML, 
            reply_markup=get_menu(user.id)
        )
    
    return ConversationHandler.END

def handle_stock_akrab(query, context):
    """Cek stok provider"""
    try:
        raw = cek_stock_akrab()
        msg = format_stock_akrab(raw)
        
        if isinstance(msg, str) and msg.strip().lower().startswith("<html"):
            msg = "❌ Provider membalas data tidak valid."
        
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(query.from_user.id))
    except Exception as e:
        logger.error(f"Error cek stock: {e}")
        query.edit_message_text(
            f"❌ Error cek stock: {str(e)}", 
            parse_mode=ParseMode.HTML, 
            reply_markup=get_menu(query.from_user.id)
        )
    
    return ConversationHandler.END

def handle_semua_riwayat(query, context):
    """Menampilkan semua riwayat transaksi (admin only)"""
    try:
        riwayat = list(load_riwayat().values())
        riwayat = sorted(riwayat, key=lambda x: x.get("waktu", ""), reverse=True)
        
        if not riwayat:
            query.edit_message_text(
                "📭 Belum ada transaksi.",
                reply_markup=get_menu(query.from_user.id)
            )
            return ConversationHandler.END
        
        msg = "<b>📜 Semua Riwayat Transaksi:</b>\n\n"
        for i, r in enumerate(riwayat[:30], 1):
            status_icon = "✅" if r['status_text'].lower() == 'success' else "⏳" if r['status_text'].lower() == 'pending' else "❌"
            msg += (
                f"{i}. {status_icon} <b>{r['produk']}</b>\n"
                f"   👤 {r.get('username', r.get('nama', 'Unknown'))}\n"
                f"   📱 {r['tujuan']} | 💰 Rp {r['harga']:,}\n"
                f"   🆔 <code>{r['reffid']}</code>\n"
                f"   ⏰ {r.get('waktu','')}\n"
                f"   📊 {r['status_text']}\n\n"
            )
            
        query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(query.from_user.id))
    except Exception as e:
        logger.error(f"Error memuat semua riwayat: {e}")
        query.edit_message_text(
            "❌ Gagal memuat riwayat transaksi.", 
            parse_mode=ParseMode.HTML, 
            reply_markup=get_menu(query.from_user.id)
        )
    
    return ConversationHandler.END

def handle_lihat_saldo(query, context):
    """Menampilkan saldo bot (admin only)"""
    saldo = get_saldo()
    query.edit_message_text(
        f"💰 <b>Saldo Bot:</b> Rp {saldo:,}", 
        parse_mode=ParseMode.HTML, 
        reply_markup=get_menu(query.from_user.id)
    )
    return ConversationHandler.END

def handle_tambah_saldo(query, context):
    """Instruksi tambah saldo (admin only)"""
    query.edit_message_text(
        "💳 <b>Tambah Saldo Bot</b>\n\nKirim format: <code>TAMBAH|jumlah</code>\nContoh: <code>TAMBAH|50000</code>", 
        parse_mode=ParseMode.HTML, 
        reply_markup=get_menu(query.from_user.id)
    )
    return ConversationHandler.END

def handle_manajemen_produk(query, context):
    """Menu manajemen produk (admin only)"""
    produk_list = get_produk_list()
    if not produk_list:
        query.edit_message_text(
            "❌ Tidak ada produk tersedia.", 
            reply_markup=get_menu(query.from_user.id)
        )
        return ConversationHandler.END
    
    msg = "<b>🛠️ Manajemen Produk:</b>\nPilih produk untuk diedit:\n"
    keyboard = []
    
    for p in produk_list:
        keyboard.append([
            InlineKeyboardButton(
                f"{p['kode']} | {p['nama']} | Rp {p['harga']:,}", 
                callback_data=f"admin_edit_produk|{p['kode']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="back_admin")])
    
    query.edit_message_text(
        msg, 
        parse_mode=ParseMode.HTML, 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END

def handle_admin_edit_produk(query, context, data):
    """Edit produk tertentu (admin only)"""
    kode = data.split("|")[1]
    p = get_produk_by_kode(kode)
    
    if not p:
        query.edit_message_text(
            "❌ Produk tidak ditemukan.", 
            reply_markup=get_menu(query.from_user.id)
        )
        return ConversationHandler.END
    
    msg = (
        f"<b>✏️ Edit Produk {p['kode']}:</b>\n\n"
        f"📦 Nama: {p['nama']}\n"
        f"💰 Harga: Rp {p['harga']:,}\n"
        f"📊 Kuota: {p['kuota']}\n"
        f"📝 Deskripsi: {p['deskripsi']}\n\n"
        "Pilih aksi edit di bawah:"
    )
    
    query.edit_message_text(
        msg, 
        parse_mode=ParseMode.HTML, 
        reply_markup=admin_edit_produk_keyboard(kode)
    )
    
    context.user_data["edit_kode"] = kode
    return ADMIN_EDIT

def handle_edit_harga(query, context, data):
    """Edit harga produk (admin only)"""
    kode = data.split("|")[1]
    context.user_data["edit_kode"] = kode
    context.user_data["edit_field"] = "harga"
    
    query.edit_message_text(
        f"💰 <b>Edit Harga Produk</b>\n\nProduk: <b>{kode}</b>\nMasukkan harga baru (angka):\n\nKetik /batal untuk membatalkan.", 
        parse_mode=ParseMode.HTML
    )
    return ADMIN_EDIT

def handle_edit_deskripsi(query, context, data):
    """Edit deskripsi produk (admin only)"""
    kode = data.split("|")[1]
    context.user_data["edit_kode"] = kode
    context.user_data["edit_field"] = "deskripsi"
    
    query.edit_message_text(
        f"📝 <b>Edit Deskripsi Produk</b>\n\nProduk: <b>{kode}</b>\nMasukkan deskripsi baru:\n\nKetik /batal untuk membatalkan.", 
        parse_mode=ParseMode.HTML
    )
    return ADMIN_EDIT

def handle_reset_custom(query, context, data):
    """Reset custom produk (admin only)"""
    from produk import reset_produk_custom
    kode = data.split("|")[1]
    
    try:
        ok = reset_produk_custom(kode)
        if ok:
            query.edit_message_text(
                f"✅ Sukses reset custom produk <b>{kode}</b> ke default.", 
                parse_mode=ParseMode.HTML, 
                reply_markup=get_menu(query.from_user.id)
            )
        else:
            query.edit_message_text(
                f"❌ Gagal reset custom produk <b>{kode}</b>.", 
                parse_mode=ParseMode.HTML, 
                reply_markup=get_menu(query.from_user.id)
            )
    except Exception as e:
        logger.error(f"Error reset custom: {e}")
        query.edit_message_text(
            f"❌ Error reset produk: {str(e)}", 
            parse_mode=ParseMode.HTML, 
            reply_markup=get_menu(query.from_user.id)
        )
    
    return ConversationHandler.END

def handle_back_admin(query, context):
    """Kembali ke menu admin"""
    query.edit_message_text(
        "Kembali ke menu admin.", 
        reply_markup=get_menu(query.from_user.id)
    )
    return ConversationHandler.END

def handle_back_main(query, context):
    """Kembali ke menu utama"""
    query.edit_message_text(
        "Kembali ke menu utama.", 
        reply_markup=get_menu(query.from_user.id)
    )
    return ConversationHandler.END

# === CONVERSATION HANDLERS ===

def produk_pilih_callback(update: Update, context: CallbackContext):
    """Handler untuk memilih produk dari inline keyboard"""
    query = update.callback_query
    user = query.from_user
    data = query.data
    query.answer()
    
    if data.startswith("produk_static|"):
        try:
            idx = int(data.split("|")[1])
            produk_list = get_produk_list()
            
            if idx < 0 or idx >= len(produk_list):
                query.edit_message_text(
                    "❌ Produk tidak valid.", 
                    reply_markup=get_menu(user.id)
                )
                return ConversationHandler.END
            
            p = produk_list[idx]
            
            # Cek stok
            if p.get('kuota', 0) <= 0:
                query.edit_message_text(
                    f"❌ Produk {p['kode']} sedang habis stok.", 
                    reply_markup=get_menu(user.id)
                )
                return ConversationHandler.END
            
            context.user_data["produk"] = p
            query.edit_message_text(
                f"✅ <b>Produk Dipilih:</b>\n\n"
                f"📦 {p['kode']} - {p['nama']}\n"
                f"💰 Harga: Rp {p['harga']:,}\n"
                f"📊 Stok: {p['kuota']}\n\n"
                f"Silakan masukkan nomor tujuan:\n\nKetik /batal untuk membatalkan.",
                parse_mode=ParseMode.HTML
            )
            return INPUT_TUJUAN
        
        except (ValueError, IndexError) as e:
            logger.error(f"Error memilih produk: {e}")
            query.edit_message_text(
                "❌ Error memilih produk.", 
                reply_markup=get_menu(user.id)
            )
            return ConversationHandler.END
    
    elif data == "back_main":
        query.edit_message_text(
            "Kembali ke menu utama.", 
            reply_markup=get_menu(user.id)
        )
        return ConversationHandler.END
    
    else:
        query.edit_message_text(
            "❌ Menu tidak dikenal.", 
            reply_markup=get_menu(user.id)
        )
        return ConversationHandler.END

def input_tujuan_step(update: Update, context: CallbackContext):
    """Handler untuk input nomor tujuan"""
    tujuan = update.message.text.strip()
    
    # Validasi nomor telepon
    if not tujuan.isdigit() or len(tujuan) < 9 or len(tujuan) > 15:
        update.message.reply_text(
            "❌ Format nomor tidak valid. Masukkan nomor handphone (9-15 digit):"
        )
        return INPUT_TUJUAN
    
    context.user_data["tujuan"] = tujuan
    p = context.user_data.get("produk")
    
    update.message.reply_text(
        f"📋 <b>Konfirmasi Pesanan:</b>\n\n"
        f"📦 Produk: {p['kode']} - {p['nama']}\n"
        f"💰 Harga: Rp {p['harga']:,}\n"
        f"📱 Tujuan: {tujuan}\n\n"
        f"Ketik <b>YA</b> untuk konfirmasi atau <b>BATAL</b> untuk membatalkan.",
        parse_mode=ParseMode.HTML
    )
    return KONFIRMASI

def konfirmasi_step(update: Update, context: CallbackContext):
    """Handler untuk konfirmasi transaksi"""
    text = update.message.text.strip().upper()
    
    if text == "BATAL":
        update.message.reply_text(
            "❌ Transaksi dibatalkan.", 
            reply_markup=get_menu(update.effective_user.id)
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    if text != "YA":
        update.message.reply_text(
            "❌ Ketik 'YA' untuk konfirmasi atau 'BATAL' untuk batal."
        )
        return KONFIRMASI
    
    # Proses transaksi
    return process_transaction(update, context)

def process_transaction(update: Update, context: CallbackContext):
    """Memproses transaksi"""
    p = context.user_data.get("produk")
    tujuan = context.user_data.get("tujuan")
    
    if not p or not tujuan:
        update.message.reply_text(
            "❌ Data transaksi tidak lengkap.", 
            reply_markup=get_menu(update.effective_user.id)
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    harga = p["harga"]
    saldo = get_saldo()
    user = update.effective_user
    
    # Cek saldo
    if saldo < harga:
        update.message.reply_text(
            f"❌ Saldo bot tidak cukup.\nSaldo tersedia: Rp {saldo:,}\nDibutuhkan: Rp {harga:,}",
            reply_markup=get_menu(user.id)
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Buat transaksi
    try:
        data = create_trx(p["kode"], tujuan)
        
        if not data or not data.get("refid"):
            err_msg = data.get("message", "Gagal membuat transaksi.") if data else "Tidak ada respon API."
            update.message.reply_text(
                f"❌ Gagal membuat transaksi:\n<b>{err_msg}</b>", 
                parse_mode=ParseMode.HTML, 
                reply_markup=get_menu(user.id)
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        # Simpan riwayat transaksi
        riwayat = load_riwayat()
        refid = data["refid"]
        
        riwayat[refid] = {
            "trxid": data.get("trxid", ""),
            "reffid": refid,
            "produk": p["kode"],
            "tujuan": tujuan,
            "status_text": data.get("status", "pending"),
            "status_code": data.get("status_code"),
            "keterangan": data.get("message", ""),
            "waktu": data.get("waktu", ""),
            "harga": harga,
            "user_id": user.id,
            "username": user.username or "",
            "nama": user.full_name,
        }
        save_riwayat(riwayat)
        
        # Update saldo
        set_saldo(saldo - harga)
        
        # Kirim konfirmasi sukses
        update.message.reply_text(
            f"✅ <b>Transaksi Berhasil!</b>\n\n"
            f"📦 Produk: {p['kode']}\n"
            f"📱 Tujuan: {tujuan}\n"
            f"🔢 RefID: <code>{refid}</code>\n"
            f"📊 Status: {data.get('status','pending')}\n"
            f"💰 Saldo bot: Rp {saldo-harga:,}\n\n"
            f"Gunakan menu 'Cek Status' untuk memantau transaksi.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_menu(user.id)
        )
        
    except Exception as e:
        logger.error(f"Error membuat transaksi: {e}")
        update.message.reply_text(
            f"❌ Error membuat transaksi: {str(e)}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_menu(user.id)
        )
    
    finally:
        context.user_data.clear()
    
    return ConversationHandler.END

def topup_nominal_step(update: Update, context: CallbackContext):
    """Handler untuk input nominal topup"""
    text = update.message.text.strip()
    
    try:
        nominal = int(text.replace(".", "").replace(",", ""))
        if nominal < 10000:
            update.message.reply_text(
                "❌ Nominal minimal Rp 10.000. Masukkan kembali nominal:"
            )
            return TOPUP_NOMINAL
        
        # Generate QRIS
        resp = generate_qris(nominal)
        if resp.get("status") != "success":
            update.message.reply_text(
                f"❌ Gagal generate QRIS: {resp.get('message', 'Unknown error')}"
            )
            return ConversationHandler.END
        
        qris_base64 = resp.get("qris_base64")
        msg = f"💰 <b>Top Up Saldo</b>\n\nSilakan lakukan pembayaran sebesar <b>Rp {nominal:,}</b>\n\nScan QRIS berikut:"
        
        if qris_base64:
            # Remove data URL prefix jika ada
            if qris_base64.startswith("data:image/png;base64,"):
                qris_base64 = qris_base64.replace("data:image/png;base64,", "")
            
            update.message.reply_photo(
                photo=qris_base64,
                caption=msg, 
                parse_mode=ParseMode.HTML
            )
        else:
            update.message.reply_text(
                msg + "\n\n❌ QRIS tidak tersedia", 
                parse_mode=ParseMode.HTML
            )
            
    except ValueError:
        update.message.reply_text(
            "❌ Format nominal tidak valid. Masukkan angka:"
        )
        return TOPUP_NOMINAL
    except Exception as e:
        logger.error(f"Error generating QRIS: {e}")
        update.message.reply_text(
            f"❌ Error: {str(e)}"
        )
    
    return ConversationHandler.END

def admin_edit_produk_step(update: Update, context: CallbackContext):
    """Handler untuk edit produk oleh admin"""
    kode = context.user_data.get("edit_kode")
    field = context.user_data.get("edit_field")
    value = update.message.text.strip()
    
    if not kode or not field:
        update.message.reply_text(
            "❌ Kueri tidak valid. Silakan ulangi.",
            reply_markup=get_menu(update.effective_user.id)
        )
        context.user_data.clear()
        return ConversationHandler.END

    p = get_produk_by_kode(kode)
    if not p:
        update.message.reply_text(
            "❌ Produk tidak ditemukan.",
            reply_markup=get_menu(update.effective_user.id)
        )
        context.user_data.clear()
        return ConversationHandler.END

    try:
        if field == "harga":
            try:
                harga = int(value.replace(".", "").replace(",", ""))
                if harga <= 0:
                    update.message.reply_text("❌ Harga harus lebih dari 0. Silakan masukkan lagi:")
                    return ADMIN_EDIT
                
                old_harga = p["harga"]
                edit_produk(kode, harga=harga)
                p_new = get_produk_by_kode(kode)
                
                update.message.reply_text(
                    f"✅ <b>Harga produk berhasil diupdate!</b>\n\n"
                    f"📦 Produk: {p_new['kode']} - {p_new['nama']}\n"
                    f"💰 Harga lama: <s>Rp {old_harga:,}</s>\n"
                    f"💰 Harga baru: <b>Rp {p_new['harga']:,}</b>",
                    parse_mode="HTML",
                    reply_markup=get_menu(update.effective_user.id)
                )
                
            except ValueError:
                update.message.reply_text("❌ Format harga tidak valid. Silakan masukkan angka:")
                return ADMIN_EDIT
        
        elif field == "deskripsi":
            old_deskripsi = p["deskripsi"]
            edit_produk(kode, deskripsi=value)
            p_new = get_produk_by_kode(kode)
            
            update.message.reply_text(
                f"✅ <b>Deskripsi produk berhasil diupdate!</b>\n\n"
                f"📦 Produk: {p_new['kode']} - {p_new['nama']}\n"
                f"📝 Deskripsi lama: <i>{old_deskripsi}</i>\n"
                f"📝 Deskripsi baru: <b>{p_new['deskripsi']}</b>",
                parse_mode="HTML",
                reply_markup=get_menu(update.effective_user.id)
            )
        
        else:
            update.message.reply_text(
                "❌ Field tidak dikenal.",
                reply_markup=get_menu(update.effective_user.id)
            )
    
    except Exception as e:
        logger.error(f"Error editing product: {e}")
        update.message.reply_text(
            f"❌ <b>Gagal update produk!</b>\nError: {str(e)}",
            parse_mode="HTML",
            reply_markup=get_menu(update.effective_user.id)
        )
    
    finally:
        context.user_data.clear()
    
    return ConversationHandler.END

def handle_text_message(update: Update, context: CallbackContext):
    """Handler untuk pesan teks biasa"""
    # Skip jika sedang dalam conversation
    if context.user_data:
        return
    
    text = update.message.text.strip()
    user = update.effective_user
    
    if text.startswith("CEK|"):
        handle_cek_status_message(update, context)
    
    elif text.startswith("TAMBAH|") and is_admin(user.id):
        handle_tambah_saldo_message(update, context)
    
    else:
        update.message.reply_text(
            "❌ Perintah tidak dikenali. Gunakan menu di bawah atau ketik /help untuk bantuan.", 
            reply_markup=get_menu(user.id)
        )

def handle_cek_status_message(update: Update, context: CallbackContext):
    """Handler untuk cek status via pesan teks"""
    try:
        refid = text.split("|", 1)[1].strip()
        if not refid:
            update.message.reply_text(
                "❌ RefID tidak boleh kosong.", 
                reply_markup=get_menu(update.effective_user.id)
            )
            return
            
        data = history(refid)
        
        if not data:
            update.message.reply_text(
                "❌ Transaksi tidak ditemukan.", 
                reply_markup=get_menu(update.effective_user.id)
            )
            return
            
        msg = f"🔍 <b>Status Transaksi</b>\n\nRefID: <code>{refid}</code>\n\n"
        for k, v in data.items():
            msg += f"• <b>{k}</b>: {v}\n"
        
        update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=get_menu(update.effective_user.id))
        
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        update.message.reply_text(
            f"❌ Error cek status: {str(e)}", 
            reply_markup=get_menu(update.effective_user.id)
        )

def handle_tambah_saldo_message(update: Update, context: CallbackContext):
    """Handler untuk tambah saldo via pesan teks (admin only)"""
    try:
        tambah_text = text.split("|", 1)[1].strip()
        if not tambah_text:
            update.message.reply_text(
                "❌ Nilai tidak boleh kosong.", 
                reply_markup=get_menu(update.effective_user.id)
            )
            return
            
        tambah = int(tambah_text)
        saldo_sebelum = get_saldo()
        saldo_sesudah = saldo_sebelum + tambah
        set_saldo(saldo_sesudah)
        
        update.message.reply_text(
            f"✅ <b>Saldo berhasil ditambahkan!</b>\n\n"
            f"💰 Sebelum: Rp {saldo_sebelum:,}\n"
            f"💰 Tambah: Rp {tambah:,}\n"
            f"💰 Sekarang: Rp {saldo_sesudah:,}",
            parse_mode=ParseMode.HTML, 
            reply_markup=get_menu(update.effective_user.id)
        )
        
    except ValueError:
        update.message.reply_text(
            "❌ Format nilai tidak valid.", 
            reply_markup=get_menu(update.effective_user.id)
        )
    except Exception as e:
        logger.error(f"Error adding balance: {e}")
        update.message.reply_text(
            f"❌ Error: {str(e)}", 
            reply_markup=get_menu(update.effective_user.id)
        )

def get_conversation_handler():
    """Mengembalikan conversation handler yang sudah dikonfigurasi"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(main_menu_callback)],
        states={
            CHOOSING_PRODUK: [CallbackQueryHandler(produk_pilih_callback)],
            INPUT_TUJUAN: [MessageHandler(Filters.text & ~Filters.command, input_tujuan_step)],
            KONFIRMASI: [MessageHandler(Filters.text & ~Filters.command, konfirmasi_step)],
            TOPUP_NOMINAL: [MessageHandler(Filters.text & ~Filters.command, topup_nominal_step)],
            ADMIN_EDIT: [MessageHandler(Filters.text & ~Filters.command, admin_edit_produk_step)],
        },
        fallbacks=[
            CommandHandler("batal", cancel),
            MessageHandler(Filters.regex(r'^(/batal|batal|BATAL|cancel)$'), cancel),
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True
    )

def error_handler(update: Update, context: CallbackContext):
    """Global error handler"""
    logger.error(f"Error: {context.error}", exc_info=context.error)
    
    if update and update.effective_user:
        try:
            update.effective_message.reply_text(
                "❌ Terjadi error. Silakan coba lagi.",
                reply_markup=get_menu(update.effective_user.id)
            )
        except:
            pass
