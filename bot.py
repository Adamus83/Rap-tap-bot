import os
import asyncio
from pyrogram import Client, filters

BOT_TOKEN = "8611339445:AAEaohbwsnAJljAjCjeg3xJhUU0JZNAz1_A"

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN tidak ditemukan!")
    exit(1)

app = Client("rap_tap_bot", bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Halo! Bot Rap Tap UMKM berhasil jalan! 🥟")

@app.on_message()
async def handle_all(client, message):
    await message.reply_text(f"Pesan diterima: {message.text}")

async def main():
    await app.start()
    print("Bot berjalan...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    app.run()
