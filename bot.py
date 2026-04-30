import os
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, datetime
import asyncio

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

ADMIN_IDS = 8611339445
ADMIN_USERNAME = adamus83

class Database:
    def __init__(self):
        self.conn = sqlite3.connect("umkm_db.sqlite", check_same_thread=False)
        self.c = self.conn.cursor()
        self.setup()
    
    def setup(self):
        self.c.execute("CREATE TABLE IF NOT EXISTS players (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, omzet INTEGER DEFAULT 0, tap_power INTEGER DEFAULT 1, level INTEGER DEFAULT 1, total_taps INTEGER DEFAULT 0, last_daily TEXT)")
        self.c.execute("CREATE TABLE IF NOT EXISTS upgrades (user_id INTEGER, upgrade_key TEXT, level INTEGER DEFAULT 0, PRIMARY KEY (user_id, upgrade_key))")
        self.c.execute("CREATE TABLE IF NOT EXISTS employees (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, emp_type TEXT, efficiency REAL DEFAULT 1.0)")
        self.conn.commit()
    
    def get_player(self, uid):
        self.c.execute("SELECT * FROM players WHERE user_id=?", (uid,))
        return self.c.fetchone()
    
    def create_player(self, uid, username, first_name):
        self.c.execute("INSERT OR IGNORE INTO players VALUES (?,?,?,0,1,1,0,NULL)", (uid, username, first_name))
        self.conn.commit()
    
    def tap(self, uid, amount):
        self.c.execute("UPDATE players SET omzet=omzet+?, total_taps=total_taps+1 WHERE user_id=?", (amount, uid))
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
        self.c.execute("UPDATE players SET omzet=omzet-?, tap_power=tap_power+? WHERE user_id=?", (cost, power, uid))
        self.c.execute("INSERT INTO upgrades VALUES (?,?,1) ON CONFLICT(user_id,upgrade_key) DO UPDATE SET level=level+1", (uid, upgrade_key))
        self.conn.commit()
        return True
    
    def hire_employee(self, uid, emp_type, cost, efficiency):
        self.c.execute("SELECT omzet FROM players WHERE user_id=?", (uid,))
        if self.c.fetchone()[0] < cost:
            return False
        self.c.execute("UPDATE players SET omzet=omzet-? WHERE user_id=?", (cost, uid))
        self.c.execute("INSERT INTO employees (user_id, emp_type, efficiency) VALUES (?,?,?)", (uid, emp_type, efficiency))
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
        self.c.execute("UPDATE players SET omzet=omzet+?, last_daily=? WHERE user_id=?", (amount, today, uid))
        self.conn.commit()
        return True
    
    def get_top(self, limit=10):
        self.c.execute("SELECT username, first_name, omzet, level FROM players ORDER BY omzet DESC LIMIT ?", (limit,))
        return self.c.fetchall()
    
    def add_ticket(self, uid):
        self.c.execute("CREATE TABLE IF NOT EXISTS lucky_draw (user_id INTEGER, week_number INTEGER, tickets INTEGER DEFAULT 0, PRIMARY KEY (user_id, week_number))")
        week = datetime.now().isocalendar()[1]
        self.c.execute("INSERT INTO lucky_draw VALUES (?,?,1) ON CONFLICT(user_id,week_number) DO UPDATE SET tickets=tickets+1", (uid, week))
        self.conn.commit()
    
    def get_tickets(self, uid):
        self.c.execute("CREATE TABLE IF NOT EXISTS lucky_draw (user_id INTEGER, week_number INTEGER, tickets INTEGER DEFAULT 0, PRIMARY KEY (user_id, week_number))")
        week = datetime.now().isocalendar()[1]
        self.c.execute("SELECT tickets FROM lucky_draw WHERE user_id=? AND week_number=?", (uid, week))
        r = self.c.fetchone()
        return r[0] if r else 0

db = Database()

LEVELS = {1: {"name": "Pentol Keliling", "icon": "🥟", "omzet": 0}, 5: {"name": "Warkop Sederhana", "icon": "☕", "omzet": 2000}, 10: {"name": "Es Teh Franchise", "icon": "🥤", "omzet": 10000}, 15: {"name": "Pabrik Pentol", "icon": "🏭", "omzet": 50000}, 20: {"name": "Juragan Pentol", "icon": "👑", "omzet": 200000}}
UPGRADES = {"bumbu": {"name": "Bumbu Rahasia", "cost": 50, "power": 2}, "saus": {"name": "Saus Dewa", "cost": 200, "power": 5}, "iklan": {"name": "Iklan Medsos", "cost": 1000, "power": 15}, "mesin": {"name": "Mesin Otomatis", "cost": 5000, "power": 50}}
EMPLOYEES = {"masak": {"name": "Tukang Masak", "cost": 500, "eff": 1.0}, "kasir": {"name": "Kasir", "cost": 1000, "eff": 1.5}, "marketing": {"name": "Marketing", "cost": 2500, "eff": 2.5}}

def get_level(omzet):
    current = 1
    for lvl, data in sorted(LEVELS.items()):
        if omzet >= data["omzet"]:
            current = lvl
    return current

cooldowns = {}

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("JUAL PENTOL! (+Rp)", callback_data="tap")],
        [InlineKeyboardButton("BISNISKU", callback_data="stats"), InlineKeyboardButton("UPGRADE", callback_data="upgrade")],
        [InlineKeyboardButton("KARYAWAN", callback_data="employee"), InlineKeyboardButton("DAILY", callback_data="daily")],
        [InlineKeyboardButton("EVENT", callback_data="event"), InlineKeyboardButton("TOP 10", callback_data="top")]
    ])

def upgrade_menu(uid):
    upgrades = db.get_upgrades(uid)
    btns = []
    for key, data in UPGRADES.items():
        lv = upgrades.get(key, 0)
        cost = int(data["cost"] * (1.5 ** lv))
        btns.append([InlineKeyboardButton(f"{data['name']} Lv.{lv} - Rp {cost:,}", callback_data=f"buy_{key}")])
    btns.append([InlineKeyboardButton("KEMBALI", callback_data="back")])
    return InlineKeyboardMarkup(btns)

def employee_menu(uid):
    emps = db.get_employees(uid)
    count = len(emps)
    btns = []
    for key, data in EMPLOYEES.items():
        cost = int(data["cost"] * (1.3 ** count))
        btns.append([InlineKeyboardButton(f"{data['name']} - Rp {cost:,} [{count}/10]", callback_data=f"hire_{key}")])
    btns.append([InlineKeyboardButton("KEMBALI", callback_data="back")])
    return InlineKeyboardMarkup(btns)

app = Client("rap_tap_bot", bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def cmd_start(client, message):
    user = message.from_user
    db.create_player(user.id, user.username or "anon", user.first_name or "Cak")
    text = f"Halo {user.first_name or 'Cak'}!\n\nSelamat datang di RAP TAP UMKM - Game Simulasi Bisnis Pentol!\n\nTap JUAL PENTOL untuk mulai!"
    await message.reply_text(text, reply_markup=main_menu())

@app.on_callback_query()
async def handle_buttons(client, callback):
    uid = callback.from_user.id
    data = callback.data
    
    now = datetime.now().timestamp()
    if data == "tap":
        if uid in cooldowns and now - cooldowns[uid] < 0.3:
            await callback.answer("Sabar!")
            return
        cooldowns[uid] = now
    
    if data == "tap":
        player = db.get_player(uid)
        if not player:
            await callback.answer("Ketik /start dulu")
            return
        omzet = player[3]
        tap_power = player[4]
        level = player[5]
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
            ld = LEVELS.get(new_level, {"name": "Bisnis", "icon": ""})
            level_msg = f"\n\nLEVEL UP! {ld['name']} {ld['icon']}"
        tickets = db.get_tickets(uid)
        text = f"+Rp {earned:,}\nOmzet: Rp {new_omzet:,}\nTap: {tap_power}\nLevel: {new_level}\nTiket: {tickets}{level_msg}"
        await callback.message.edit_text(text, reply_markup=main_menu())
        await callback.answer(f"+Rp {earned:,}")
    
    elif data == "stats":
        player = db.get_player(uid)
        if not player:
            await callback.answer("Ketik /start dulu")
            return
        emps = db.get_employees(uid)
        ld = LEVELS.get(player[5], LEVELS[1])
        tickets = db.get_tickets(uid)
        text = f"BISNISKU\nLevel {player[5]}: {ld['name']} {ld['icon']}\nOmzet: Rp {player[3]:,}\nTap: {player[4]}\nTotal Tap: {player[6]:,}\nKaryawan: {len(emps)}/10\nTiket: {tickets}"
        await callback.message.edit_text(text, reply_markup=main_menu())
    
    elif data == "upgrade":
        await callback.message.edit_text("UPGRADE\nPilih:", reply_markup=upgrade_menu(uid))
    
    elif data.startswith("buy_"):
        key = data.replace("buy_", "")
        ud = UPGRADES[key]
        upgrades = db.get_upgrades(uid)
        lv = upgrades.get(key, 0)
        cost = int(ud["cost"] * (1.5 ** lv))
        if db.buy_upgrade(uid, key, cost, ud["power"]):
            await callback.answer("Berhasil!", show_alert=True)
        else:
            await callback.answer(f"Butuh Rp {cost:,}", show_alert=True)
        await callback.message.edit_text("UPGRADE\nPilih:", reply_markup=upgrade_menu(uid))
    
    elif data == "employee":
        await callback.message.edit_text("KARYAWAN\nHire:", reply_markup=employee_menu(uid))
    
    elif data.startswith("hire_"):
        key = data.replace("hire_", "")
        ed = EMPLOYEES[key]
        count = len(db.get_employees(uid))
        cost = int(ed["cost"] * (1.3 ** count))
        if db.hire_employee(uid, key, cost, ed["eff"]):
            await callback.answer("Berhasil!", show_alert=True)
        else:
            await callback.answer(f"Butuh Rp {cost:,}", show_alert=True)
        await callback.message.edit_text("KARYAWAN\nHire:", reply_markup=employee_menu(uid))
    
    elif data == "daily":
        player = db.get_player(uid)
        if not player:
            await callback.answer("Ketik /start dulu")
            return
        reward = min(player[5] * 100, 2000)
        if db.claim_daily(uid, reward):
            await callback.answer(f"Dapat Rp {reward:,}!", show_alert=True)
        else:
            await callback.answer("Sudah klaim!", show_alert=True)
        await callback.message.edit_text(f"Daily: +Rp {reward:,}", reply_markup=main_menu())
    
    elif data == "event":
        tickets = db.get_tickets(uid)
        text = f"EVENT\n\nLucky Draw Mingguan\nTiket: {tickets}\n\n100 tap = 1 tiket\nUndian tiap Senin"
        await callback.message.edit_text(text, reply_markup=main_menu())
    
    elif data == "top":
        top = db.get_top(10)
        text = "TOP 10 JURAGAN PENTOL\n\n"
        for i, p in enumerate(top):
            name = p[1] or p[0] or "Anonim"
            text += f"{i+1}. {name} - Rp {p[2]:,} (Lv.{p[3]})\n"
        await callback.message.edit_text(text, reply_markup=main_menu())
    
    elif data == "back":
        await callback.message.edit_text("RAP TAP UMKM\nPilih menu:", reply_markup=main_menu())

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

print("Bot Running...")
app.run()