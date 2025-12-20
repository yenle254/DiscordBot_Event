import discord
from discord import app_commands
from discord.ext import commands
import datetime
import asyncio

# --- 1. MODAL ĐIỀN USERNAME (NGƯỜI CHƠI) ---
class RegistrationModal(discord.ui.Modal):
    title = "Event Registration"
    username_input = discord.ui.TextInput(
        label="Your username",
        placeholder="Enter your display username...",
        min_length=2, max_length=30
    )

    def __init__(self, view, start_time):
        super().__init__()
        self.view = view
        self.start_time = start_time

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        user = interaction.user
        if user.id in self.view.participants:
            return await interaction.followup.send("You have already joined!", ephemeral=True)

        self.view.participants[user.id] = self.username_input.value
        await self.view.update_message(interaction.message)
        
        await interaction.followup.send(f"✅ {self.username_input.value} has been added!", ephemeral=True)

        timestamp = int(self.start_time.timestamp())
        try:
            await user.send(
                f"📅 **Registration confirmed!**\n\n"
                f"Event: **{self.view.event_title}**\n"
                f"Start time: <t:{timestamp}:F>\n"
                f"⏳ **Countdown: <t:{timestamp}:R>**"
            )
        except:
            pass

# --- 2. EVENT VIEW (GIAO DIỆN CHÍNH) ---
class EventView(discord.ui.View):
    def __init__(self, title, event_type, start_time, host_id):
        super().__init__(timeout=None)
        self.event_title = title
        self.event_type = event_type
        self.start_time = start_time
        self.host_id = host_id
        self.participants = {}
        self.is_closed = False

    def create_embed(self):
        status = "CLOSED" if self.is_closed else "OPEN"
        color = 0xe74c3c if self.is_closed else 0x2ecc71
        embed = discord.Embed(title=f"--❤[ {self.event_title} ]❤--", color=color)
        
        desc = (
            f"✨ **Status**: {status}\n"
            f"☁ **Type**: {self.event_type}\n"
            f"👥 **Players**: {len(self.participants)}/8\n\n"
            f"📜 **Player List**:\n"
        )
        if not self.participants:
            desc += "Join or leave anytime"
        else:
            for i, (uid, name) in enumerate(self.participants.items(), 1):
                desc += f"{i}. <@{uid}> ({name})\n"

        embed.description = desc
        embed.set_footer(text=f"Starts at: {self.start_time.strftime('%d/%m/%Y %H:%M')}")
        return embed

    @discord.ui.button(label="Join Run", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.is_closed or len(self.participants) >= 8:
            return await interaction.response.send_message("You cannot join this event.", ephemeral=True)
        await interaction.response.send_modal(RegistrationModal(self, self.start_time))

    @discord.ui.button(label="Leave Run", style=discord.ButtonStyle.danger)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.participants:
            return await interaction.response.send_message("You are not participating.", ephemeral=True)
        
        del self.participants[interaction.user.id]
        await interaction.response.send_message("You have left the event.", ephemeral=True)
        await self.update_message(interaction.message)

    @discord.ui.button(label="Close Run", style=discord.ButtonStyle.secondary)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host_id:
            return await interaction.response.send_message("Only the host can close this event.", ephemeral=True)
        
        self.is_closed = True
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def update_message(self, message):
        await message.edit(embed=self.create_embed(), view=self)

# --- 3. MODAL NHẬP THỜI GIAN (DÀNH CHO HOST) ---
class TimeInputModal(discord.ui.Modal, title="Set event start time"):
    date_str = discord.ui.TextInput(
        label="Start date (DD/MM/YYYY)",
        min_length=8, max_length=10
    )
    time_str = discord.ui.TextInput(
        label="Start time (HH:mm)",
        placeholder="Example: 23:00",
        min_length=4, max_length=5
    )

    def __init__(self, title, event_type, host_id, cog):
        super().__init__()
        self.event_title = title
        self.event_type = event_type
        self.host_id = host_id
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            full_date_str = f"{self.date_str.value} {self.time_str.value.replace('.', ':')}"
            start_time = datetime.datetime.strptime(full_date_str, "%d/%m/%Y %H:%M")
            
            if start_time < datetime.datetime.now():
                return await interaction.followup.send(
                    "❌ The selected time cannot be in the past.",
                    ephemeral=True
                )

            view = EventView(self.event_title, self.event_type, start_time, self.host_id)
            
            await interaction.edit_original_response(
                content="✅ Event created successfully!",
                view=None
            )

            if isinstance(interaction.channel, discord.TextChannel):
                await interaction.channel.send(embed=view.create_embed(), view=view)
            else:
                await interaction.followup.send(embed=view.create_embed(), view=view)

            asyncio.create_task(self.cog.wait_for_start(self.event_title, start_time, view))

        except ValueError:
            await interaction.followup.send(
                "❌ Invalid format! (Date: 20/12/2025 | Time: 23:00)",
                ephemeral=True
            )

class SetupView(discord.ui.View):
    def __init__(self, title, event_type, host_id, cog):
        super().__init__(timeout=60)
        self.title = title
        self.event_type = event_type
        self.host_id = host_id
        self.cog = cog

    @discord.ui.button(label="Click to set time", style=discord.ButtonStyle.primary)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            TimeInputModal(self.title, self.event_type, self.host_id, self.cog)
        )

# --- 4. COG ---
class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def wait_for_start(self, title, start_time, view):
        while True:
            now = datetime.datetime.now()
            delay = (start_time - now).total_seconds()
            if delay <= 0:
                break
            await asyncio.sleep(min(delay, 60))

        for uid, name in view.participants.items():
            try:
                user = await self.bot.fetch_user(uid)
                await user.send(
                    f"🚀 **{title}** ({view.event_type}) has started! "
                    f"Let’s go **{name}**!"
                )
            except:
                pass

    @app_commands.command(name="event", description="Create a new event")
    @app_commands.choices(event_type=[
        app_commands.Choice(name="Long-run", value="Long-run"),
        app_commands.Choice(name="Casual-run", value="Casual-run")
    ])
    async def event(
        self,
        interaction: discord.Interaction,
        title: str,
        event_type: app_commands.Choice[str]
    ):
        view = SetupView(title, event_type.value, interaction.user.id, self)
        await interaction.response.send_message(
            f"⚙ **Event setup:** {title}\n*Type: {event_type.name}*",
            view=view,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(EventCog(bot))
