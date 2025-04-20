"""
D10 Discord Bot - Core bot class for Linux environments
"""

import os
import sys
import logging
import traceback
import datetime
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, Union

# Import the PostgreSQL database implementation
from database_pg import Database

# Initialize logger
logger = logging.getLogger('d10-bot')

class D10Bot(commands.Bot):
    """
    Main bot class with all core functionality
    """
    def __init__(self):
        """
        Initialize the bot with required intents and command prefix
        """
        # Set up intents with all the permissions we need
        intents = discord.Intents.default()
        intents.message_content = True  # For reading message content
        intents.members = True  # For member events like join/leave
        intents.presences = True  # For status tracking
        intents.guilds = True  # For guild events
        intents.voice_states = True  # For voice channel management
        
        # Initialize the bot with our prefix and intents
        super().__init__(
            command_prefix='!', 
            intents=intents,
            help_command=None,  # Disable default help command
            case_insensitive=True,  # Make commands case-insensitive
        )
        
        # Store IDs from environment variables
        self.server_id = int(os.getenv('DISCORD_SERVER_ID', 0))
        self.staff_role_id = int(os.getenv('DISCORD_STAFF_ROLE_ID', 0))
        self.status_role_id = int(os.getenv('DISCORD_STATUS_ROLE_ID', 0))
        self.vouch_role_id = int(os.getenv('DISCORD_VOUCH_ROLE_ID', 0))
        self.vouch_channel_id = int(os.getenv('DISCORD_VOUCH_CHANNEL_ID', 0))
        
        # Initialize database
        self.db = Database()
        
        # Start time of the bot
        self.start_time = datetime.datetime.utcnow()
        
    async def setup_hook(self) -> None:
        """
        Hook that is called when the bot is initially setting up
        """
        logger.info("Setting up bot...")
        
        # Load all cogs
        await self.load_cogs()
        
        # Sync slash commands to the guild
        if self.server_id:
            guild = discord.Object(id=self.server_id)
            try:
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(f"Synced {len(synced)} commands to guild: {self.server_id}")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}", exc_info=True)
        
    async def load_cogs(self) -> None:
        """
        Load all cog modules
        """
        # Get the directory where the bot.py file is located
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cogs_dir = os.path.join(base_dir, 'cogs')
        
        # Check if the cogs directory exists
        if not os.path.exists(cogs_dir):
            logger.error(f"Cogs directory not found: {cogs_dir}")
            return
        
        # Load each cog in the cogs directory
        for filename in os.listdir(cogs_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                cog_name = filename[:-3]  # Remove .py extension
                try:
                    await self.load_extension(f'cogs.{cog_name}')
                    logger.info(f"Loaded cog: cogs.{cog_name}")
                except Exception as e:
                    logger.error(f"Failed to load cog {cog_name}: {e}", exc_info=True)
    
    async def on_ready(self) -> None:
        """
        Event handler for when the bot is ready
        """
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set custom status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=".gg/d10"
            )
        )
        
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """
        Global error handler for command errors
        """
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
            
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
            
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument provided: {error}")
            
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(f"You don't have permission to use this command.")
            
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"I don't have the necessary permissions to execute this command.")
            
        else:
            # Log the error
            logger.error(f"Command error in {ctx.command}: {error}", exc_info=True)
            await ctx.send(f"An error occurred while executing the command: {error}")
            
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        """
        Global error handler for application command errors
        """
        if isinstance(error, app_commands.CommandNotFound):
            return  # Ignore command not found errors
            
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command.", 
                ephemeral=True
            )
            
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                "I don't have the necessary permissions to execute this command.",
                ephemeral=True
            )
            
        elif isinstance(error, app_commands.CommandInvokeError):
            # Log the error
            logger.error(f"Command error: {error.original}", exc_info=True)
            
            # Try to respond if not already responded
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(
                        f"An error occurred: {error.original}",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"An error occurred: {error.original}",
                        ephemeral=True
                    )
            except Exception as e:
                logger.error(f"Failed to send error message: {e}", exc_info=True)
                
        else:
            # Log the error
            logger.error(f"App command error: {error}", exc_info=True)
            
            # Try to respond if not already responded
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(
                        f"An error occurred: {error}",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"An error occurred: {error}",
                        ephemeral=True
                    )
            except Exception as e:
                logger.error(f"Failed to send error message: {e}", exc_info=True)