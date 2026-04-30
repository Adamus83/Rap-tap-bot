import os
from pyrogram import Client, filters

# 
BOT_TOKEN = "8611339445:AAEaohbwsnAJ1jAjCjeg3x"

if not BOT_TOKEN or len(BOT_TOKEN) < 30:
    print("ERROR: Token tidak valid!")
    exit(1)

print(f"Token loaded: {BOT_TOKEN[:10]}...")  # Print 10 karakter pertama untuk debug

app = Client("rap_tap_bot", bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Halo! Bot Rap Tap UMKM berhasil jalan! 🥟")

print("Bot starting...")
app.run()
