import os
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import date, datetime, timedelta
import asyncio

# ===== ⚠️ GANTI INI: TOKEN DARI BOTFATHER =====
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8611339445:AAHVuTsoLegBmAXwtYDYIcrKnrLDrGRehIE"

# ===== ⚠️ GANTI INI: ID TELEGRAM KAMU (angka dari @userinfobot) =====
ADMIN_IDS = @Raptapumkm83_bot

# ===== ⚠️ GANTI INI:  =====
ADMIN_USERNAME = "adamus83"

# ===== DATABASE =====
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("umkm_db.sqlite", check_same_thread=False)
        self.c = self.conn.cursor()
        self.setup()
    
    def setup(self):
        self.c.execute('''CREATE TABLE IF NOT EXISTS players
            (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
             omzet INTEGER DEFAULT 0, tap_power INTEGER DEFAULT 1,
             level INTEGER DEFAULT 1, total_taps INTEGER DEFAULT 0,
             last_daily TEXT)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS upgrades
            (user_id INTEGER, upgrade_key TEXT, level INTEGER DEFAULT 0,
             PRIMARY KEY (user_id, upgrade_key))''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS employees
            (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
             emp_type TEXT, efficiency REAL DEFAULT 1.0)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS purchases
            (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
             package_name TEXT, amount INTEGER, status TEXT DEFAULT 'pending',
             purchase_date TEXT)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS lucky_draw
            (user_id INTEGER, week_number INTEGER, tickets INTEGER DEFAULT 0,
             PRIMARY KEY (user_id, week_number))''')
        self.conn.commit()
    
    def get_player(self, uid):
        self.c.execute("SELECT * FROM players WHERE user_id=?", (uid,))
        return self.c.fetchone()
    
    def create_player(self, uid, username, first_name):
        self.c.execute(
            "INSERT OR IGNORE INTO players VALUES (?,?,?,0,1,1,0,NULL)",
            (uid, username, first_name))
        self.conn.commit()
    
    def tap(self, uid, amount):
        self.c.execute(
            "UPDATE players SET omzet=omzet+?, total_taps=total_taps+1 WHERE user_id=?",
            (amount, uid))
        self.conn.commit()
    
    def update_level(self, uid, level):
        self.c.execute("UPDATE players SET level=? WHERE user_id=?", (level, uid))
        self.conn.commit()
    
    def get_upgrades(self, uid):
        self.c.execute("SELECT upgrade_key, level FROM upgrades WHERE user_id=?", (uid,))
        return {row[0]: row[1] for row in self.c.fetchall()}
    
    def buy_upgrade(self, uid, upgrade_key, cost, power):
        self.c.execute("SELECT omzet FROM players WHERE user_id=?", (uid,))
        if self.c.fetchone()[0] < cost:
            return False
        self.c.execute("UPDATE players SET omzet=omzet-?, tap_power=tap_power+? WHERE user_id=?",
                      (cost, power, uid))
        self.c.execute('''INSERT INTO upgrades VALUES (?,?,1)
                         ON CONFLICT(user_id,upgrade_key) DO UPDATE SET level=level+1''',
                      (uid, upgrade_key))
        self.conn.commit()
        return True
    
    def hire_employee(self, uid, emp_type, cost, efficiency):
        self.c.execute("SELECT omzet FROM players WHERE user_id=?", (uid,))
        if self.c.fetchone()[0] < cost:
            return False
        self.c.execute("UPDATE players SET omzet=omzet-? WHERE user_id=?", (cost, uid))
        self.c.execute("INSERT INTO employees (user_id, emp_type, efficiency) VALUES (?,?,?)",
                      (uid, emp_type, efficiency))
        self.conn.commit()
        return True
    
    def get_employees(self, uid):
        self.c.execute("SELECT * FROM employees WHERE user_id=?", (uid,))
        return self.c.fetchall()
    
    def claim_daily(self, uid, amount):
        today = str(date.today())
        self.c.execute("SELECT last_daily FROM players WHERE user_id=?", (uid,))
        if self.c.fetchone()[0] == today:
            return False
        self.c.execute("UPDATE players SET omzet=omzet+?, last_daily=? WHERE user_id=?",
                      (amount, today, uid))
        self.conn.commit()
        return True
    
    def get_top(self, limit=10):
        self.c.execute(
            "SELECT username, first_name, omzet, level FROM players ORDER BY omzet DESC LIMIT ?",
            (limit,))
        return self.c.fetchall()
    
    def add_ticket(self, uid):
        week = datetime.now().isocalendar()[1]
        self.c.execute('''INSERT INTO lucky_draw VALUES (?,?,1)
                         ON CONFLICT(user_id,week_number) DO UPDATE SET tickets=tickets+1''',
                      (uid, week))
        self.conn.commit()
    
    def get_tickets(self, uid):
        week = datetime.now().isocalendar()[1]
        self.c.execute("SELECT tickets FROM lucky_draw WHERE user_id=? AND week_number=?",
                      (uid, week))
        r = self.c.fetchone()
        return r[0] if r else 0
    
    def add_purchase(self, uid, package_name, amount):
        self.c.execute(
            "INSERT INTO purchases (user_id, package_name, amount, purchase_date) VALUES (?,?,?,?)",
            (uid, package_name, amount, str(datetime.now())))
        self.conn.commit()
    
    def verify_purchase(self, uid, package_name):
        packages = {
            "modal_awal": {"tap_power": 5, "bonus_omzet": 1000, "free_employee": True},
            "go_digital": {"tap_power": 15, "auto_tap_boost": 2, "bonus_omzet": 5000},
            "warung_modern": {"all_upgrades": 5, "premium_employees": 3}
        }
        pkg = packages.get(package_name)
        if not pkg:
            return False
        for benefit, value in pkg.items():
            if benefit == "tap_power":
                self.c.execute("UPDATE players SET tap_power=tap_power+? WHERE user_id=?",
                             (value, uid))
            elif benefit == "bonus_omzet":
                self.c.execute("UPDATE players SET omzet=omzet+? WHERE user_id=?",
                             (value, uid))
            elif benefit == "free_employee" and value:
                self.c.execute(
                    "INSERT INTO employees (user_id, emp_type, efficiency) VALUES (?,?,?)",
                    (uid, "marketing", 2.0))
        self.conn.commit()
        return True

db = Database()

# ===== GAME DATA =====
LEVELS = {
    1: {"name": "Pentol Keliling", "icon": "🥟", "omzet": 0},
    5: {"name": "Warkop Sederhana", "icon": "☕", "omzet": 2000},
    10: {"name": "Es Teh Franchise", "icon": "🥤", "omzet": 10000},
    15: {"name": "Pabrik Pentol", "icon": "🏭", "omzet": 50000},
    20: {"name": "Juragan Pentol", "icon": "👑", "omzet": 200000}
}

UPGRADES = {
    "bumbu": {"name": "🧂 Bumbu Rahasia", "cost": 50, "power": 2},
    "saus": {"name": "🌶️ Saus Dewa", "cost": 200, "power": 5},
    "iklan": {"name": "📱 Iklan Medsos", "cost": 1000, "power": 15},
    "mesin": {"name": "⚙️ Mesin Otomatis", "cost": 5000, "power": 50}
}

EMPLOYEES = {
    "masak": {"name": "👨‍🍳 Tukang Masak", "cost": 500, "eff": 1.0},
    "kasir": {"name": "💁 Kasir", "cost": 1000, "eff": 1.5},
    "marketing": {"name": "📣 Marketing", "cost": 2500, "eff": 2.5}
}

# ===== ⚠️ GANTI INI: LINK QRIS KAMU =====
PREMIUM_PACKAGES = {
    "modal_awal": {
        "name": "💰 Modal Awal Usaha",
        "price": 5000,
        "qris": "‎https://ibb.co.com/tPYtXLrx"
    },
    "go_digital": {
        "name": "📱 Paket Go Digital",
        "price": 15000,
        "qris": "‎https://ibb.co.com/tPYtXLrx"
    },
    "warung_modern": {
        "name": "🏪 Paket Warung Modern",
        "price": 35000,
        "qris": "‎https://ibb.co.com/tPYtXLrx"
    }
}

def get_level(omzet):
    current = 1
    for lvl, data in sorted(LEVELS.items()):
        if omzet >= data["omzet"]:
            current = lvl
    return current

cooldowns = {}

# ===== KEYBOARDS =====
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥟 JUAL PENTOL! (+Rp)", callback_data="tap")],
        [InlineKeyboardButton("📊 BISNISKU", callback_data="stats"),
         InlineKeyboardButton("⬆️ UPGRADE", callback_data="upgrade")],
        [InlineKeyboardButton("👥 KARYAWAN", callback_data="employee"),
         InlineKeyboardButton("🎁 DAILY", callback_data="daily")],
        [InlineKeyboardButton("💎 PREMIUM", callback_data="premium"),
         InlineKeyboardButton("🎪 EVENT", callback_data="event")],
        [InlineKeyboardButton("🏆 TOP 10", callback_data="top")]
    ])

def upgrade_menu(uid):
    upgrades = db.get_upgrades(uid)
    btns = []
    for key, data in UPGRADES.items():
        lv = upgrades.get(key, 0)
        cost = int(data["cost"] * (1.5 ** lv))
        btns.append([InlineKeyboardButton(f"{data['name']} Lv.{lv} - Rp {cost:,}", callback_data=f"buy_{key}")])
    btns.append([InlineKeyboardButton("🔙 KEMBALI", callback_data="back")])
    return InlineKeyboardMarkup(btns)

def employee_menu(uid):
    emps = db.get_employees(uid)
    count = len(emps)
    btns = []
    for key, data in EMPLOYEES.items():
        cost = int(data["cost"] * (1.3 ** count))
        btns.append([InlineKeyboardButton(f"{data['name']} - Rp {cost:,} [{count}/10]", callback_data=f"hire_{key}")])
    btns.append([InlineKeyboardButton("🔙 KEMBALI", callback_data="back")])
    return InlineKeyboardMarkup(btns)

def premium_menu():
    btns = []
    for key, data in PREMIUM_PACKAGES.items():
        btns.append([InlineKeyboardButton(f"{data['name']} - Rp {data['price']:,}", callback_data=f"beli_{key}")])
    btns.append([InlineKeyboardButton("💳 Info Pembayaran", callback_data="info_bayar")])
    btns.append([InlineKeyboardButton("🔙 KEMBALI", callback_data="back")])
    return InlineKeyboardMarkup(btns)

# ===== BOT CLIENT =====
app = Client("rap_tap_bot", bot_token=BOT_TOKEN)

# ===== COMMAND HANDLERS =====
@app.on_message(filters.command("start"))
async def cmd_start(client, message):
    user = message.from_user
    db.create_player(user.id, user.username or "anon", user.first_name or "Cak")
    
    text = f"""**🥟 RAP TAP UMKM - SURABAYA EDITION**

Halo *{user.first_name or 'Cak'}*! 

Bangun bisnis pentol dari nol sampai jadi Juragan!

**Cara Main:**
🥟 Tap **JUAL PENTOL** untuk hasilkan omzet
⬆️ Upgrade bumbu biar makin cuan
👥 Hire karyawan untuk bantu jualan
💎 Beli paket premium untuk akselerasi bisnis
🎪 Ikuti event menangkan voucher data!

*Seng penting tap terus, Cak!*"""

    await message.reply_text(text, reply_markup=main_menu())

# ===== CALLBACK HANDLER =====
@app.on_callback_query()
async def handle_buttons(client, callback: CallbackQuery):
    uid = callback.from_user.id
    data = callback.data
    
    now = datetime.now().timestamp()
    if data == "tap":
        if uid in cooldowns and now - cooldowns[uid] < 0.3:
            await callback.answer("Sabar Cak!", show_alert=False)
            return
        cooldowns[uid] = now
    
    # ===== TAP =====
    if data == "tap":
        player = db.get_player(uid)
        if not player:
            await callback.answer("Ketik /start dulu")
            return
        
        omzet, tap_power, level = player[3], player[4], player[5]
        emps = db.get_employees(uid)
        emp_bonus = sum([tap_power * 0.5 * emp[3] for emp in emps])
        earned = int(tap_power + emp_bonus)
        
        db.tap(uid, earned)
        db.add_ticket(uid)
        
        new_omzet = omzet + earned
        new_level = get_level(new_omzet)
        
        level_msg = ""
        if new_level > level:
            db.update_level(uid, new_level)
            ld = LEVELS.get(new_level, {})
            level_msg = f"\n\n🎉 LEVEL UP! **{ld.get('name', '')}** {ld.get('icon', '')}"
        
        tickets = db.get_tickets(uid)
        text = f"🥟 +Rp {earned:,}\n💰 Omzet: Rp {new_omzet:,}\n💪 Tap: {tap_power}\n📊 Level: {new_level}\n🎟️ Tiket: {tickets}{level_msg}"
        
        await callback.message.edit_text(text, reply_markup=main_menu())
        await callback.answer(f"+Rp {earned:,}")
    
    # ===== STATS =====
    elif data == "stats":
        player = db.get_player(uid)
        if not player:
            await callback.answer("Ketik /start dulu")
            return
        emps = db.get_employees(uid)
        ld = LEVELS.get(player[5], LEVELS[1])
        tickets = db.get_tickets(uid)
        
        text = f"""📊 **BISNISKU**
🏪 Level {player[5]}: {ld['name']} {ld['icon']}
💰 Omzet: Rp {player[3]:,}
💪 Tap Power: {player[4]}
👆 Total Tap: {player[6]:,}
👥 Karyawan: {len(emps)}/10
🎟️ Tiket Lucky Draw: {tickets}"""
        
        await callback.message.edit_text(text, reply_markup=main_menu())
    
    # ===== UPGRADE =====
    elif data == "upgrade":
        await callback.message.edit_text("⬆️ **UPGRADE BISNIS**\n\nPilih upgrade:", reply_markup=upgrade_menu(uid))
    
    elif data.startswith("buy_"):
        key = data.replace("buy_", "")
        ud = UPGRADES[key]
        upgrades = db.get_upgrades(uid)
        lv = upgrades.get(key, 0)
        cost = int(ud["cost"] * (1.5 ** lv))
        
        if db.buy_upgrade(uid, key, cost, ud["power"]):
            await callback.answer(f"✅ {ud['name']} berhasil!", show_alert=True)
        else:
            await callback.answer(f"❌ Omzet kurang! Butuh Rp {cost:,}", show_alert=True)
        await callback.message.edit_text("⬆️ **UPGRADE**\n\nPilih upgrade:", reply_markup=upgrade_menu(uid))
    
    # ===== EMPLOYEE =====
    elif data == "employee":
        await callback.message.edit_text("👥 **KARYAWAN**\n\nHire karyawan (maks 10):", reply_markup=employee_menu(uid))
    
    elif data.startswith("hire_"):
        key = data.replace("hire_", "")
        ed = EMPLOYEES[key]
        count = len(db.get_employees(uid))
        cost = int(ed["cost"] * (1.3 ** count))
        
        if db.hire_employee(uid, key, cost, ed["eff"]):
            await callback.answer(f"✅ {ed['name']} dihire!", show_alert=True)
        else:
            await callback.answer(f"❌ Omzet kurang! Butuh Rp {cost:,}", show_alert=True)
        await callback.message.edit_text("👥 **KARYAWAN**\n\nHire karyawan:", reply_markup=employee_menu(uid))
    
    # ===== DAILY =====
    elif data == "daily":
        player = db.get_player(uid)
        if not player:
            await callback.answer("Ketik /start dulu")
            return
        reward = min(player[5] * 100, 2000)
        
        if db.claim_daily(uid, reward):
            await callback.answer(f"✅ Dapat Rp {reward:,}!", show_alert=True)
        else:
            await callback.answer("❌ Sudah klaim hari ini!", show_alert=True)
        await callback.message.edit_text(f"🎁 Daily Reward: +Rp {reward:,}", reply_markup=main_menu())
    
    # ===== PREMIUM =====
    elif data == "premium":
        text = "💎 **PAKET PREMIUM UMKM**\n\nDukung pengembangan bisnis virtual kamu!\nSemua pembayaran via QRIS resmi.\n\nPilih paket:"
        await callback.message.edit_text(text, reply_markup=premium_menu())
    
    elif data.startswith("beli_"):
        key = data.replace("beli_", "")
        pkg = PREMIUM_PACKAGES.get(key)
        if not pkg:
            await callback.answer("Paket tidak ditemukan")
            return
        
        text = f"💎 **{pkg['name']}**\n\n💰 Harga: Rp {pkg['price']:,}\n\n**Cara Beli:**\n1. Scan QRIS di bawah\n2. Transfer sesuai nominal\n3. Kirim bukti ke @{ADMIN_USERNAME}"
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Saya Sudah Transfer", callback_data=f"confirm_{key}")],
            [InlineKeyboardButton("📞 Hubungi Admin", url=f"https://t.me/{ADMIN_USERNAME}")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="premium")]
        ]))
        
        if pkg.get("qris") and "LINK_QRIS" not in pkg["qris"]:
            await client.send_photo(uid, pkg["qris"], caption=f"📱 Bayar **{pkg['name']}**\nNominal: Rp {pkg['price']:,}")
    
    elif data.startswith("confirm_"):
        key = data.replace("confirm_", "")
        pkg = PREMIUM_PACKAGES.get(key)
        if pkg:
            db.add_purchase(uid, pkg['name'], pkg['price'])
            for admin_id in ADMIN_IDS:
                try:
                    await client.send_message(admin_id,
                        f"🔔 **PEMBELIAN BARU**\n\nUser: {callback.from_user.first_name}\nID: {uid}\nPaket: {pkg['name']}\nHarga: Rp {pkg['price']:,}\n\n⏳ Verifikasi: /verify {uid} {key}")
                except:
                    pass
        await callback.answer("✅ Pesanan dicatat! Admin akan verifikasi dalam 1x24 jam.", show_alert=True)
    
    elif data == "info_bayar":
        text = f"💳 **CARA PEMBAYARAN**\n\n1. Pilih paket premium\n2. Scan QRIS yang muncul\n3. Transfer sesuai nominal\n4. Screenshot bukti transfer\n5. Kirim ke admin: @{ADMIN_USERNAME}\n6. Paket aktif dalam 1x24 jam\n\n📞 Bantuan: @{ADMIN_USERNAME}"
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali", callback_data="premium")]
        ]))
    
    # ===== EVENT =====
    elif data == "event":
        tickets = db.get_tickets(uid)
        text = f"""🎪 **EVENT & HADIAH**

🌙 **Pasar Malam Digital**
   Target: 50.000 omzet | Hadiah: Voucher Data 1-5GB

📱 **UMKM Go Online Challenge**
   Selesaikan misi digital! Hadiah: Voucher Pulsa

🎰 **Lucky Draw Mingguan**
   Tiket kamu: {tickets} 🎟️
   Hadiah Utama: Voucher Data 10GB + GoPay 50K!
   
⏰ Pengundian tiap Senin malam"""
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎰 Info Lucky Draw", callback_data="info_lucky")],
            [InlineKeyboardButton("🏆 Cek Hadiah", url=f"https://t.me/{ADMIN_USERNAME}")],
            [InlineKeyboardButton("🔙 KEMBALI", callback_data="back")]
        ]))
    
    elif data == "info_lucky":
        tickets = db.get_tickets(uid)
        text = f"🎰 **LUCKY DRAW**\n\n🎟️ Tiket: {tickets}\n📊 100 tap = 1 tiket\n\n🎁 Hadiah:\n🥇 Voucher Data 10GB + GoPay 50K\n🥈 5x Voucher Data 2GB\n🥉 10x Bonus Omzet 10.000\n\n⏰ Undian: Senin 20:00 WIB"
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Kembali", callback_data="event")]
        ]))
    
    # ===== TOP =====
    elif data == "top":
        top = db.get_top(10)
        medals = ["🥇", "🥈", "🥉"]
        text = "🏆 **TOP 10 JURAGAN PENTOL**\n\n"
        for i, p in enumerate(top):
            name = p[1] or p[0] or "Anonim"
            medal = medals[i] if i < 3 else f"{i+1}."
            text += f"{medal} **{name}** - Rp {p[2]:,} (Lv.{p[3]})\n"
        await callback.message.edit_text(text, reply_markup=main_menu())
    
    # ===== BACK =====
    elif data == "back":
        await callback.message.edit_text("🥟 **RAP TAP UMKM**\n\nPilih menu:", reply_markup=main_menu())

# ===== ADMIN COMMANDS =====
@app.on_message(filters.command("verify") & filters.user(ADMIN_IDS))
async def cmd_verify(client, message):
    args = message.command[1:]
    if len(args) < 2:
        await message.reply("Format: /verify [user_id] [modal_awal/go_digital/warung_modern]")
        return
    try:
        uid = int(args[0])
        pkg = args[1]
        if db.verify_purchase(uid, pkg):
            await message.reply(f"✅ Paket {pkg} diaktifkan untuk user {uid}")
            try:
                await client.send_message(uid, f"✅ **PEMBELIAN BERHASIL!**\n\nPaket kamu sudah diaktifkan!\nSelamat mengembangkan bisnis UMKM! 🎉")
            except:
                pass
        else:
            await message.reply("❌ Gagal verifikasi")
    except Exception as e:
        await message.reply(f"Error: {e}")

@app.on_message(filters.command("giveprize") & filters.user(ADMIN_IDS))
async def cmd_giveprize(client, message):
    args = message.command[1:]
    if len(args) < 2:
        await message.reply("Format: /giveprize [user_id] [nama_hadiah]")
        return
    try:
        uid = int(args[0])
        prize = " ".join(args[1:])
        try:
            await client.send_message(uid, f"🎉 **SELAMAT!**\n\nKamu memenangkan: **{prize}**\n\nHadiah akan diproses admin.\nInfo: @{ADMIN_USERNAME}")
        except:
            pass
        await message.reply(f"✅ Hadiah '{prize}' dikirim ke user {uid}")
    except Exception as e:
        await message.reply(f"Error: {e}")

# ===== AUTO-TAP KARYAWAN =====
async def auto_tap():
    while True:
        await asyncio.sleep(5)
        try:
            emps = db.c.execute("SELECT * FROM employees").fetchall()
            for emp in emps:
                player = db.get_player(emp[1])
                if player:
                    bonus = int(player[4] * 0.5 * emp[3])
                    db.c.execute("UPDATE players SET omzet=omzet+? WHERE user_id=?", (bonus, emp[1]))
            db.conn.commit()
        except:
            pass

@app.on_startup()
async def startup():
    asyncio.create_task(auto_tap())

# ===== RUN =====
print("🥟 Rap Tap UMKM Bot Running...")
app.run()