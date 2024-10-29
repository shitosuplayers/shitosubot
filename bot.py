import discord
from discord.ext import commands
import time
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# Set up the intents
intents = discord.Intents.default()
intents.message_content = True  # Enable the intent to read message content (required for command handling)
intents.messages = True
intents.guilds = True
intents.members = True

# Channel ID where commands should be restricted
CHANNEL_ID = 1252657982572073050

# Create an instance of a bot with the specified intents and case insensitivity
bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)


# Debugging event to check if the bot is receiving commands
@bot.event
async def on_command(ctx):
    print(f'Command received: {ctx.message.content}')

# Ping command as a Slash Command
@bot.tree.command(name="ping", description="Check the bot's latency.")
async def ping(interaction: discord.Interaction):
    print('Ping command received')
    start_time = time.monotonic()
    await interaction.response.send_message('Pong!')
    end_time = time.monotonic()
    latency_ms = round((end_time - start_time) * 1000)
    await interaction.edit_original_response(content=f'Pong! ({latency_ms} ms)')

# Store bot startup time
bot.startup_time = datetime.now()

# Uptime command as a Slash Command
@bot.tree.command(name="uptime", description="Check how long the bot has been running.")
async def uptime(interaction: discord.Interaction):
    delta = datetime.now() - bot.startup_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Construct the uptime message
    uptime_msg = "Uptime: "
    if days > 0:
        uptime_msg += f"{days}d "
    if hours > 0:
        uptime_msg += f"{hours}h "
    if minutes > 0:
        uptime_msg += f"{minutes}m "
    uptime_msg += f"{seconds}s"

    await interaction.response.send_message(uptime_msg)



# Run the bot with the provided token
bot.run(os.getenv('BOT_TOKEN'))