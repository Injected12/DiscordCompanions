"""
D10 Discord Bot - Core bot class
"""

import os
import asyncio
import logging
from typing import List, Optional
import discord
from discord.ext import commands
from discord import app_commands
import config
from database import Database

logger = logging.getLogger("d10-bot")

class D10Bot(commands.Bot):
    """
    Main bot class with all core functionality
    """
    
    def __init__(self):
        intents = discord.Intents.all()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        
        super().__init__(
            command_prefix=commands.when_mentioned_or('!'),
            intents=intents,
            application_id=int(os.getenv("DISCORD_APPLICATION_ID", "0")),
            help_command=None
        )
        
        self.db = Database()
        self.guild_id = int(os.getenv("DISCORD_SERVER_ID", "1358090413340102686"))
        self.staff_role_id = int(os.getenv("DISCORD_STAFF_ROLE_ID", "1363277490008621337"))
        self.status_role_id = int(os.getenv("DISCORD_STATUS_ROLE_ID", "1363311828142264492"))
        self.vouch_role_id = int(os.getenv("DISCORD_VOUCH_ROLE_ID", "1363277493443756256"))
        self.vouch_channel_id = int(os.getenv("DISCORD_VOUCH_CHANNEL_ID", "1363277606874779809"))
        
        # Load cogs on startup
        self.setup_hook_called = asyncio.Event()
        
    async def setup_hook(self) -> None:
        """
        Hook that is called when the bot is initially setting up
        """
        logger.info("Setting up bot...")
        
        # Load all cogs
        await self.load_cogs()
        
        # Sync commands with Discord
        if self.guild_id:
            guild = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands to guild: {self.guild_id}")
        else:
            await self.tree.sync()
            logger.info("Synced global commands")
            
        self.setup_hook_called.set()
        
    async def load_cogs(self) -> None:
        """
        Load all cog modules
        """
        cogs_to_load = [
            'cogs.tickets',
            'cogs.welcome',
            'cogs.status_tracker',
            'cogs.role_management',
            'cogs.slot_channels',
            'cogs.admin',
            'cogs.voice_channels',
            'cogs.reports',
            'cogs.giveaway',
            'cogs.vouch'
        ]
        
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}", exc_info=True)
                
    async def on_ready(self) -> None:
        """
        Event handler for when the bot is ready
        """
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="discord.gg/d10"
            )
        )
        
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
            await ctx.send(f"Bad argument: {error}")
            return
            
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
            return
            
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"I need the following permissions to run this command: {', '.join(error.missing_permissions)}")
            return
            
        # Log the error
        logger.error(f"Command error: {error}", exc_info=error)
        await ctx.send("An error occurred while processing the command.")
        
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        """
        Global error handler for application command errors
        """
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
                ephemeral=True
            )
            return
            
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
            return
            
        # Log the error
        logger.error(f"App command error: {error}", exc_info=error)
        
        try:
            if interaction.response.is_done():
                await interaction.followup.send("An error occurred while processing the command.", ephemeral=True)
            else:
                await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)
        except:
            pass
