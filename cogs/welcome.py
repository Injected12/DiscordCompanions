"""
Welcome system implementation for D10 Discord Bot
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import datetime

from utils.embeds import create_welcome_embed, create_error_embed, create_success_embed
from utils.permissions import is_staff

logger = logging.getLogger("d10-bot")

class Welcome(commands.Cog):
    """
    Welcome system for new members
    """
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Event triggered when a member joins the server
        """
        # Get welcome settings for this guild
        welcome_settings = self.bot.db.get_one("welcome", {"guild_id": member.guild.id})
        
        if not welcome_settings or not welcome_settings.get("enabled", True):
            return
            
        # Get welcome channel
        channel_id = welcome_settings.get("channel_id")
        if not channel_id:
            return
            
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return
            
        # Create welcome embed
        embed = create_welcome_embed(member)
        
        # Send welcome message
        try:
            await channel.send(
                content=f"Welcome {member.mention}!",
                embed=embed
            )
            
            logger.info(f"Sent welcome message for {member} in {channel.name}")
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}", exc_info=True)
            
    @app_commands.command(name="setupwelcome", description="Set up the welcome system in a channel")
    @app_commands.describe(channel="The channel to send welcome messages in")
    @app_commands.default_permissions(administrator=True)
    async def setup_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """
        Set up the welcome system
        """
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to use this command."),
                ephemeral=True
            )
            return
            
        # Get existing settings
        welcome_settings = self.bot.db.get_one("welcome", {"guild_id": interaction.guild.id})
        
        # Update or create settings
        if welcome_settings:
            self.bot.db.update("welcome", welcome_settings["id"], {
                "guild_id": interaction.guild.id,
                "channel_id": channel.id,
                "enabled": True,
                "updated_at": datetime.datetime.now().timestamp(),
                "updated_by": interaction.user.id
            })
        else:
            self.bot.db.insert("welcome", {
                "guild_id": interaction.guild.id,
                "channel_id": channel.id,
                "enabled": True,
                "created_at": datetime.datetime.now().timestamp(),
                "created_by": interaction.user.id
            })
            
        # Send success message
        await interaction.response.send_message(
            embed=create_success_embed(f"Welcome system has been set up in {channel.mention}"),
            ephemeral=True
        )
        
        # Show example welcome message
        example_embed = create_welcome_embed(interaction.user)
        await interaction.followup.send(
            content="Here's an example of the welcome message:",
            embed=example_embed,
            ephemeral=True
        )
        
        logger.info(f"Welcome system set up in {channel.name} (ID: {channel.id}) by {interaction.user}")
        
    @app_commands.command(name="togglewelcome", description="Enable or disable the welcome system")
    @app_commands.default_permissions(administrator=True)
    async def toggle_welcome(self, interaction: discord.Interaction):
        """
        Toggle the welcome system on or off
        """
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to use this command."),
                ephemeral=True
            )
            return
            
        # Get existing settings
        welcome_settings = self.bot.db.get_one("welcome", {"guild_id": interaction.guild.id})
        
        if not welcome_settings:
            await interaction.response.send_message(
                embed=create_error_embed("Welcome system has not been set up yet. Use /setupwelcome first."),
                ephemeral=True
            )
            return
            
        # Toggle enabled status
        new_status = not welcome_settings.get("enabled", True)
        
        # Update settings
        self.bot.db.update("welcome", welcome_settings["id"], {
            **welcome_settings,
            "enabled": new_status,
            "updated_at": datetime.datetime.now().timestamp(),
            "updated_by": interaction.user.id
        })
        
        # Send success message
        status_text = "enabled" if new_status else "disabled"
        await interaction.response.send_message(
            embed=create_success_embed(f"Welcome system has been {status_text}."),
            ephemeral=True
        )
        
        logger.info(f"Welcome system {status_text} by {interaction.user}")

async def setup(bot):
    """
    Add the cog to the bot
    """
    await bot.add_cog(Welcome(bot))
