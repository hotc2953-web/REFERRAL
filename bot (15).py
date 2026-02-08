import sqlite3
import datetime
import random
import time
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# --- CONFIGURATION ---
TOKEN = "8512330960:AAFx5Ofi9omIiTNSZ417P23tr8A-aDaQ59Y"
ADMIN_ID = 8136495141 # Apni numeric ID
CHANNEL_ID = "@referearing86" # Jise join karwana hai
WEB_APP_URL = "https://hotc2953-web.github.io/Spin/" # Apne Spin Wheel ka link daalein
MIN_WITHDRAW = 50

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('supreme_earning.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, 
                  referred_by INTEGER, total_ref INTEGER DEFAULT 0, 
                  last_bonus TEXT, last_spin INTEGER DEFAULT 0, 
                  is_banned INTEGER DEFAULT 0, used_promo TEXT DEFAULT '')''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (id INTEGER PRIMARY KEY, maintenance INTEGER DEFAULT 0, 
                  promo_name TEXT, promo_value INTEGER, min_withdraw INTEGER DEFAULT 50)''')
    c.execute("SELECT count(*) FROM settings")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO settings (id, maintenance, promo_name, promo_value, min_withdraw) VALUES (1, 0, 'LOOT100', 10, 50)")
    conn.commit()
    conn.close()

def db_query(query, params=(), fetchone=False, commit=False):
    conn = sqlite3.connect('supreme_earning.db')
    c = conn.cursor()
    c.execute(query, params)
    data = c.fetchone() if fetchone else c.fetchall()
    if commit: conn.commit()
    conn.close()
    return data

# --- KEYBOARDS ---
def main_menu():
    return ReplyKeyboardMarkup([
        ['👤 Profile', '🔗 Refer & Earn'],
        [KeyboardButton(text='🎡 Spin & Win', web_app=WebAppInfo(url=WEB_APP_URL))],
        ['🎁 Daily Bonus', '🎰 Promo Code'],
        ['💰 Withdraw UPI', '🏆 Leaderboard'],
        ['📊 Bot Stats']
    ], resize_keyboard=True)

# --- JOIN CHECK ---
async def is_joined(update, context):
    try:
        m = await context.bot.get_chat_member(CHANNEL_ID, update.effective_user.id)
        return m.status in ['member', 'administrator', 'creator']
    except: return True 

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    st = db_query("SELECT maintenance FROM settings WHERE id=1", fetchone=True)
    
    if st[0] == 1 and uid != ADMIN_ID:
        await update.message.reply_text("🚧 **Bot Under Maintenance!**")
        return

    if not await is_joined(update, context):
        btn = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_ID[1:]}")]]
        await update.message.reply_text("❌ Join karein tabhi access milega!", reply_markup=InlineKeyboardMarkup(btn))
        return

    user = db_query("SELECT is_banned FROM users WHERE user_id=?", (uid,), fetchone=True)
    if not user:
        # Captcha logic
        n1, n2 = random.randint(1, 10), random.randint(1, 10)
        context.user_data['captcha_ans'] = n1 + n2
        context.user_data['temp_ref'] = context.args[0] if context.args else None
        await update.message.reply_text(f"🤖 **Security:** {n1} + {n2} = ?")
        return

    if user[0] == 1:
        await update.message.reply_text("🚫 You are BANNED!")
        return

    await update.message.reply_text("💎 **Welcome to Supreme Bot!**", reply_markup=main_menu())

# --- ADMIN PANEL ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    kb = [
        [InlineKeyboardButton("📈 Stats", callback_data="adm_stats"), InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc")],
        [InlineKeyboardButton("🚫 Ban", callback_data="adm_ban"), InlineKeyboardButton("💰 Add Pts", callback_data="adm_add")],
        [InlineKeyboardButton("⚙️ Set Limit", callback_data="adm_limit"), InlineKeyboardButton("🔴 MT Toggle", callback_data="adm_mt")]
    ]
    await update.message.reply_text("💀 **SUPREME ADMIN CENTER**", reply_markup=InlineKeyboardMarkup(kb))

# --- HANDLER ---
async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text
    
    # Captcha Processing
    if 'captcha_ans' in context.user_data:
        if txt == str(context.user_data['captcha_ans']):
            del context.user_data['captcha_ans']
            ref_id = context.user_data.get('temp_ref')
            db_query("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (uid, ref_id), commit=True)
            if ref_id and ref_id.isdigit() and int(ref_id) != uid:
                db_query("UPDATE users SET balance = balance + 10, total_ref = total_ref + 1 WHERE user_id=?", (ref_id,), commit=True)
            await update.message.reply_text("✅ Verified!", reply_markup=main_menu())
        else: await update.message.reply_text("❌ Wrong Answer!")
        return

    u_data = db_query("SELECT balance, total_ref, used_promo, last_bonus FROM users WHERE user_id=?", (uid,), fetchone=True)
    if not u_data: return

    if txt == '👤 Profile':
        await update.message.reply_text(f"👤 **Account Stats**\n💰 Balance: {u_data[0]} pts\n👥 Refers: {u_data[1]}")
    
    elif txt == '🔗 Refer & Earn':
        bot_info = await context.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={uid}"
        await update.message.reply_text(f"🔗 **Refer Link:**\n`{link}`\n\nLevel 1: 10 Pts\nLevel 2: 5 Pts", parse_mode="Markdown")

    elif txt == '🎁 Daily Bonus':
        today = str(datetime.date.today())
        if u_data[3] == today: await update.message.reply_text("❌ Aaj ka bonus mil chuka hai.")
        else:
            db_query("UPDATE users SET balance = balance + 2, last_bonus = ? WHERE user_id=?", (today, uid), commit=True)
            await update.message.reply_text("🎁 +2 Pts added!")

    elif txt == '🎰 Promo Code':
        await update.message.reply_text("Code bhejein:")
        context.user_data['wait_promo'] = True

    elif context.user_data.get('wait_promo'):
        st = db_query("SELECT promo_name, promo_value FROM settings WHERE id=1", fetchone=True)
        if txt == st[0] and st[0] not in u_data[2]:
            db_query("UPDATE users SET balance = balance + ?, used_promo = used_promo || ? WHERE user_id=?", (st[1], f",{txt}", uid), commit=True)
            await update.message.reply_text("✅ Promo Applied!")
        else: await update.message.reply_text("❌ Invalid or Already Used!")
        context.user_data['wait_promo'] = False

    elif txt == '💰 Withdraw UPI':
        limit = db_query("SELECT min_withdraw FROM settings WHERE id=1", fetchone=True)[0]
        if u_data[0] < limit: await update.message.reply_text(f"❌ Min {limit} pts required.")
        else:
            await update.message.reply_text("UPI ID likh kar bhejein:")
            context.user_data['wait_upi'] = True

    elif context.user_data.get('wait_upi'):
        db_query("UPDATE users SET balance = 0 WHERE user_id=?", (uid,), commit=True)
        await context.bot.send_message(ADMIN_ID, f"🚨 **NEW PAYOUT**\nID: {uid}\nUPI: {txt}\nAmt: {u_data[0]}")
        await update.message.reply_text("✅ Request Sent!")
        context.user_data['wait_upi'] = False

    # Admin Text Actions
    if uid == ADMIN_ID and context.user_data.get('adm_action'):
        act = context.user_data['adm_action']
        if act == 'bc':
            for u in db_query("SELECT user_id FROM users"):
                try: await context.bot.send_message(u[0], f"📢 **BROADCAST:**\n{txt}")
                except: pass
        elif act == 'add':
            target, pts = txt.split()
            db_query("UPDATE users SET balance = balance + ? WHERE user_id = ?", (pts, target), commit=True)
            await update.message.reply_text("✅ Done!")
        context.user_data['adm_action'] = None

# --- WEB APP DATA ---
async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = json.loads(update.effective_message.web_app_data.data)
    pts = res.get("points", 0)
    db_query("UPDATE users SET balance = balance + ? WHERE user_id = ?", (pts, update.effective_user.id), commit=True)
    await update.message.reply_text(f"🎡 Spin se aapne {pts} pts jeete!")

# --- CALLBACKS ---
async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.data == "adm_stats":
        r = db_query("SELECT COUNT(*), SUM(balance) FROM users", fetchone=True)
        await q.message.reply_text(f"Users: {r[0]}\nTotal Bal: {r[1]}")
    elif q.data == "adm_mt":
        db_query("UPDATE settings SET maintenance = 1 - maintenance", commit=True)
        await q.answer("Maintenance Toggled!")
    elif q.data in ["adm_bc", "adm_ban", "adm_add", "adm_limit"]:
        context.user_data['adm_action'] = q.data.replace("adm_", "")
        await q.message.reply_text("Details bhejein:")

# --- MAIN ---
if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all))
    print("🚀 Bot Started!")
    app.run_polling()
