import discord
import time
import os
import aiomysql
from discord.ext import commands
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional

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


@bot.tree.command(name="register", description="Register to sop! with your osu! ID.")
async def register(interaction: discord.Interaction, osu_id: str, discord_user: Optional[str] = None):
    # Determine the target user ID based on input
    if discord_user:
        if discord_user.startswith("<@") and discord_user.endswith(">"):
            target_user_id = int(discord_user[2:-1])  # Extract the Discord user ID from the mention
        else:
            target_user_id = int(discord_user)  # Assume the input is a plain numeric ID
    else:
        target_user_id = interaction.user.id  # Default to interaction user's Discord ID if no ID is provided
    
    # Check if the user is an admin or if they are registering their own ID
    is_admin = interaction.user.guild_permissions.administrator
    if not is_admin and target_user_id != interaction.user.id:
        await interaction.response.send_message("You don't have permission to register someone else's user.", ephemeral=True)
        return

    async with bot.db_pool.acquire() as connection:
        async with connection.cursor() as cursor:
            # Check if the user is already registered by Discord ID or osu! ID
            await cursor.execute(
                "SELECT discord_user_id, osu_user_id FROM members WHERE discord_user_id = %s OR osu_user_id = %s",
                (target_user_id, osu_id)
            )
            existing_user = await cursor.fetchone()

            if existing_user:
                registered_discord_id, registered_osu_id = existing_user
                message_parts = []
                if registered_discord_id == target_user_id:
                    message_parts.append("You are already registered.")
                else:
                    message_parts.append("Someone else is registered with that osu! ID. Please contact staff if you think this is incorrect.")

                await interaction.response.send_message(" ".join(message_parts))
                return

            # Determine the role based on the target user's roles
            target_user = interaction.guild.get_member(target_user_id)
            role_name = "Member"  # Default role
            if target_user:
                if any(role.id == 994947833931235421 for role in target_user.roles):
                    role_name = "Owner"
                elif any(role.id in (1234568141431111751, 1163949337777275020) for role in target_user.roles):
                    role_name = "Moderator"
                elif any(role.id == 1200081565787639848 for role in target_user.roles):
                    role_name = "Content Manager"

            try:
                # Insert new user registration with role
                await cursor.execute(
                    "INSERT INTO members (discord_user_id, discord_username, osu_user_id, role) VALUES (%s, %s, %s, %s)",
                    (target_user_id, target_user.name if target_user else "Unknown", int(osu_id), role_name)
                )
                await connection.commit()  # Commit the transaction

            except Exception:
                await interaction.response.send_message("An error occurred while processing your request. Please check your input.", ephemeral=True)
                return

    await interaction.response.send_message(f"Registered osu! user ID: {osu_id} as {role_name}.")



@bot.tree.command(name="unregister", description="Remove your sop! registration.")
async def unregister(interaction: discord.Interaction, user: str = None):
    # Determine target user ID based on input
    if user:
        # Check if input is in mention format, e.g., "<@123456789>"
        if user.startswith("<@") and user.endswith(">"):
            target_user_id = int(user[2:-1])  # Extract the Discord user ID from the mention
        else:
            target_user_id = int(user)  # Assume the input is a plain numeric ID
    else:
        target_user_id = interaction.user.id  # Default to interaction user's Discord ID if no ID is provided

    async with bot.db_pool.acquire() as connection:
        async with connection.cursor() as cursor:
            # Check if the user is registered with either osu_user_id or discord_user_id
            await cursor.execute(
                "SELECT osu_user_id, discord_user_id FROM members WHERE osu_user_id = %s OR discord_user_id = %s",
                (target_user_id, target_user_id)
            )
            existing_user = await cursor.fetchone()
            
            if not existing_user:
                response_message = (
                    "It looks like you're not registered yet."
                    if target_user_id == interaction.user.id
                    else "It looks like this user is not registered yet."
                )
                await interaction.response.send_message(response_message, ephemeral=True)
                return

            # Check if the user is an admin or if they are unregistering their own ID
            is_admin = interaction.user.guild_permissions.administrator
            if not is_admin and existing_user[1] != interaction.user.id:
                await interaction.response.send_message("You don't have permission to unregister another user.", ephemeral=True)
                return

            # Set response message based on whether the current user is unregistering themselves
            response_message = (
                "Your registration has been removed."
                if existing_user[1] == interaction.user.id
                else f"Removed registration for user ID: {target_user_id}."
            )
            
            # Delete the user registration based on the matched ID
            await cursor.execute(
                "DELETE FROM members WHERE osu_user_id = %s OR discord_user_id = %s",
                (target_user_id, target_user_id)
            )
            await connection.commit()  # Commit the transaction

    await interaction.response.send_message(response_message)



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
