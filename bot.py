import discord
from discord.ext import commands
import time
from datetime import datetime
from dotenv import load_dotenv
import os
import aiomysql

load_dotenv()

async def create_db_pool():
    return await aiomysql.create_pool(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        db=os.getenv('DB_NAME')
    )

# Set up the intents
intents = discord.Intents.default()
intents.message_content = True  # Enable the intent to read message content (required for command handling)
intents.guilds = True
intents.members = True

# Create an instance of a bot with the specified intents and case insensitivity
bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)

@bot.event
async def on_ready():
    bot.db_pool = await create_db_pool()  # Store pool in bot instance
    await bot.change_presence(activity=discord.Game(name="osu!"))  # Set the bot's status to "Playing osu!"
    print(f"Bot is online as {bot.user}")
    await bot.tree.sync()  # Sync the slash commands
    print('Slash commands synced.')

# Register command to take osu! user ID
@bot.tree.command(name="register", description="Register your osu! user ID.")
async def register(interaction: discord.Interaction, osu_id: str):
    async with bot.db_pool.acquire() as connection:
        async with connection.cursor() as cursor:
            # Check if the user is already registered by Discord ID or osu! ID
            await cursor.execute(
                "SELECT discord_user_id, osu_user_id FROM members WHERE discord_user_id = %s OR osu_user_id = %s",
                (interaction.user.id, osu_id)
            )
            existing_user = await cursor.fetchone()

            if existing_user:
                registered_discord_id, registered_osu_id = existing_user
                message_parts = []
                if registered_discord_id == interaction.user.id:
                    message_parts.append("You are already a registered member of sop!")
                elif registered_osu_id:
                    message_parts.append(f"Someone else is registered with that osu! id. Please contant staff if you think this is incorrect.")

                await interaction.response.send_message(" ".join(message_parts))
                return

            # Determine the role based on user's roles
            role_name = "Member"  # Default role
            if any(role.id == 994947833931235421 for role in interaction.user.roles):
                role_name = "Owner"
            elif any(role.id in (1234568141431111751, 1163949337777275020) for role in interaction.user.roles):
                role_name = "Moderator"
            elif any(role.id == 1200081565787639848 for role in interaction.user.roles):
                role_name = "Content Manager"

            # Insert new user registration with role
            await cursor.execute(
                "INSERT INTO members (discord_user_id, discord_username, osu_user_id, role) VALUES (%s, %s, %s, %s)",
                (interaction.user.id, interaction.user.name, osu_id, role_name)
            )
            await connection.commit()  # Commit the transaction

    await interaction.response.send_message(f"Registered osu! user ID: {osu_id} as {role_name}.")


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
