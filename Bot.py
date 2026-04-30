import os
from pyrogram import Client, filters

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

app = Client("rap_tap_bot", bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Halo! Bot berhasil jalan!")

@app.on_message(filters.text)
async def echo(client, message):
    await message.reply_text(f"Kamu mengetik: {message.text}")

print("Bot started!")
app.run()
