import discord
from discord import app_commands
from discord.ext import commands
import datetime

# 1. Giao diện bảng nhập tên (Modal)
class RegistrationModal(discord.ui.Modal):
    title = "Đăng ký tham gia sự kiện"

    name_input = discord.ui.TextInput(
        label="Họ và tên của bạn",
        placeholder="Nhập tên thật hoặc nickname...",
        min_length=2,
        max_length=50
    )

    def __init__(self, view, start_time):
        super().__init__()
        self.view = view
        self.start_time = start_time

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        
        # Kiểm tra nếu đã đủ người hoặc đã đăng ký
        if user.id in self.view.participants:
            return await interaction.response.send_message("Bạn đã đăng ký rồi!", ephemeral=True)
        
        if len(self.view.participants) >= 8:
            return await interaction.response.send_message("Sự kiện đã đủ 8 người!", ephemeral=True)

        # Lưu thông tin
        self.view.participants[user.id] = self.name_input.value
        count = len(self.view.participants)

        await interaction.response.send_message(f"✅ Đã ghi danh {self.name_input.value} ({count}/8)", ephemeral=True)

        # Gửi tin nhắn riêng (DM) kèm đếm ngược
        timestamp = int(self.start_time.timestamp())
        try:
            embed_dm = discord.Embed(title="Xác nhận đăng ký thành công", color=discord.Color.green())
            embed_dm.description = (
                f"Sự kiện: **{self.view.event_title}**\n"
                f"Thời gian bắt đầu: <t:{timestamp}:F>\n"
                f"Đếm ngược: <t:{timestamp}:R> ⏳"
            )
            await user.send(embed=embed_dm)
        except:
            await interaction.followup.send("Lưu ý: Bot không thể gửi DM cho bạn (hãy mở DM trong cài đặt server).", ephemeral=True)

        # Cập nhật tin nhắn gốc
        await self.view.update_message(interaction.message)

# 2. Giao diện nút bấm (View)
class EventView(discord.ui.View):
    def __init__(self, title, start_time):
        super().__init__(timeout=None)
        self.event_title = title
        self.start_time = start_time
        self.participants = {} # {id: name}

    @discord.ui.button(label="Tham gia (0/8)", style=discord.ButtonStyle.primary)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.participants) >= 8:
            button.disabled = True
            button.label = "Đã đủ người"
            await interaction.message.edit(view=self)
            return await interaction.response.send_message("Sự kiện đã đầy!", ephemeral=True)

        await interaction.response.send_modal(RegistrationModal(self, self.start_time))

    async def update_message(self, message):
        count = len(self.participants)
        list_names = "\n".join([f"- {name}" for name in self.participants.values()])
        
        embed = message.embeds[0]
        embed.set_field_at(0, name=f"Danh sách tham gia ({count}/8)", value=list_names or "Chưa có ai", inline=False)
        
        # Cập nhật nút bấm
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.label = f"Tham gia ({count}/8)"
                if count >= 8:
                    item.disabled = True
                    item.label = "Sự kiện đã đầy"
                    item.style = discord.ButtonStyle.danger

        await message.edit(embed=embed, view=self)

# 3. Class Cog chứa lệnh
class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="event", description="Tạo sự kiện mới giới hạn 8 người")
    @app_commands.describe(title="Tên sự kiện", minutes="Số phút nữa sẽ bắt đầu")
    async def event(self, interaction: discord.Interaction, title: str, minutes: int):
        start_time = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        view = EventView(title, start_time)
        
        embed = discord.Embed(title=f"🏆 {title}", color=discord.Color.gold())
        embed.add_field(name="Danh sách tham gia (0/8)", value="Chưa có ai", inline=False)
        embed.set_footer(text=f"Bắt đầu lúc: {start_time.strftime('%H:%M - %d/%m/%Y')}")

        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(EventCog(bot))