import discord
import os
from discord.ext import commands
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN chưa được thiết lập")

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True          # Cần thiết để nhắn tin riêng (DM)
        intents.message_content = True  # Cần để đọc lệnh
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Nạp file event.py từ thư mục cogs
        await self.load_extension("cogs.event")
        # Sync slash commands với Discord
        await self.tree.sync()
        print("Đã đồng bộ hóa Slash Commands!")

    async def on_ready(self):
        print(f"Bot đã sẵn sàng: {self.user}")

bot = MyBot()

if __name__ == "__main__":
    bot.run(TOKEN)
