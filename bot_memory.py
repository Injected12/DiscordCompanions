"""
D10 Discord Bot - Core bot class using in-memory database
"""

import os
import logging
import datetime
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Union, List

from memory_database import MemoryDatabase

# Configure logging
logger = logging.getLogger('d10-bot')

class D10Bot(commands.Bot):
    """
    Main bot class with all core functionality
    """
    def __init__(self):
        """
        Initialize the bot with required intents and command prefix
        """
        # Enable all necessary intents
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.presences = True
        
        # Initialize the bot with prefix commands (!)
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None  # Disable default help command
        )
        
        # Initialize database
        self.db = MemoryDatabase()
        
        # Settings
        self.staff_role_id = self._get_role_id("DISCORD_STAFF_ROLE_ID")
        self.status_role_id = self._get_role_id("DISCORD_STATUS_ROLE_ID")
        self.vouch_role_id = self._get_role_id("DISCORD_VOUCH_ROLE_ID")
        self.vouch_channel_id = self._get_channel_id("DISCORD_VOUCH_CHANNEL_ID")
        
        # Anti-raid settings
        self.anti_raid_mode = False
        self.join_timestamps = []
        
        # Active tasks
        self.tasks = []
        
    def _get_role_id(self, env_var: str) -> int:
        """Get a role ID from environment variables"""
        try:
            return int(os.getenv(env_var, "0"))
        except (ValueError, TypeError):
            logger.warning(f"{env_var} not set or invalid, using 0")
            return 0
            
    def _get_channel_id(self, env_var: str) -> int:
        """Get a channel ID from environment variables"""
        try:
            return int(os.getenv(env_var, "0"))
        except (ValueError, TypeError):
            logger.warning(f"{env_var} not set or invalid, using 0")
            return 0

    async def setup_hook(self) -> None:
        """
        Hook that is called when the bot is initially setting up
        """
        logger.info("Setting up bot...")
        
        # Load all cog modules
        await self.load_cogs()
        
        # Sync commands with Discord
        guild_id = os.getenv("DISCORD_SERVER_ID")
        if guild_id:
            try:
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(f"Synced {len(synced)} commands to guild: {guild_id}")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}", exc_info=True)
        else:
            logger.warning("DISCORD_SERVER_ID not set, skipping guild command sync")

    async def load_cogs(self) -> None:
        """
        Load all cog modules
        """
        # Define the cogs to load
        cog_names = [
            "tickets",
            "welcome",
            "status_tracker",
            "role_management",
            "admin",
            "voice_channels",
            "reports",
            "giveaway",
            "vouch",
            "slot_channels"
        ]
        
        # Load each cog
        for cog in cog_names:
            try:
                await self.load_extension(f"cogs.{cog}")
                logger.info(f"Loaded cog: cogs.{cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}", exc_info=True)

    async def on_ready(self) -> None:
        """
        Event handler for when the bot is ready
        """
        logger.info(f"Logged in as {self.user.name}#{self.user.discriminator} (ID: {self.user.id})")
        
        # Count connected guilds
        guild_count = len(self.guilds)
        logger.info(f"Connected to {guild_count} guilds")
        
        # Set the bot's status
        activity = discord.Activity(
            type=discord.ActivityType.watching, 
            name="the server | Use /help"
        )
        await self.change_presence(activity=activity, status=discord.Status.online)

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """
        Global error handler for command errors
        """
        if isinstance(error, commands.CommandNotFound):
            return
            
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
            return
            
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument: {str(error)}")
            return
            
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
            return
            
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"I don't have the required permissions: {', '.join(error.missing_permissions)}")
            return
            
        # Log unexpected errors
        logger.error(f"Command error in {ctx.command}: {str(error)}", exc_info=True)
        await ctx.send("An unexpected error occurred. Please try again later.")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        """
        Global error handler for application command errors
        """
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds.",
                ephemeral=True
            )
            return
            
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
            return
            
        if isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                f"I don't have the required permissions: {', '.join(error.missing_permissions)}",
                ephemeral=True
            )
            return
            
        # Log unexpected errors
        logger.error(f"App command error in {interaction.command.name}: {str(error)}", exc_info=True)
        
        # If interaction has not been responded to yet
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "An unexpected error occurred. Please try again later.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "An unexpected error occurred. Please try again later.",
                ephemeral=True
            )