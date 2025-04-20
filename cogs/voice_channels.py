"""
Voice channel system implementation for D10 Discord Bot
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
from typing import Dict, Optional, Union

from utils.embeds import create_error_embed, create_success_embed
from utils.permissions import is_staff

logger = logging.getLogger("d10-bot")

class VoiceChannels(commands.Cog):
    """
    Voice channel system with dynamic channel creation
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = {}  # Map of user_id -> channel_id
        self.join_to_create_channels = {}  # Map of guild_id -> channel_id
        
    async def cog_load(self):
        """
        Called when the cog is loaded
        """
        # Load JTC channels from database
        jtc_data = self.bot.db.get("voice_channels", {"type": "jtc"})
        
        for data in jtc_data:
            guild_id = data.get("guild_id")
            channel_id = data.get("channel_id")
            
            if guild_id and channel_id:
                self.join_to_create_channels[guild_id] = channel_id
                
        # Load active temp channels
        temp_data = self.bot.db.get("voice_channels", {"type": "temp", "active": True})
        
        for data in temp_data:
            user_id = data.get("user_id")
            channel_id = data.get("channel_id")
            
            if user_id and channel_id:
                self.temp_channels[user_id] = channel_id
                
        logger.info(f"Loaded {len(self.join_to_create_channels)} JTC channels and {len(self.temp_channels)} temp channels")
                
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """
        Handle voice channel joins/leaves
        """
        # Skip bots
        if member.bot:
            return
            
        # Get guild ID
        guild_id = member.guild.id
        
        # Check if user joined a JTC channel
        if after.channel and guild_id in self.join_to_create_channels:
            jtc_channel_id = self.join_to_create_channels[guild_id]
            
            if after.channel.id == jtc_channel_id:
                await self.create_temp_voice_channel(member, after.channel)
                
        # Check if user left a temp channel
        if before.channel and member.id in self.temp_channels:
            temp_channel_id = self.temp_channels[member.id]
            
            if before.channel.id == temp_channel_id:
                # Check if channel is empty
                if not before.channel.members:
                    await self.delete_temp_voice_channel(member, before.channel)
                    
    async def create_temp_voice_channel(self, member: discord.Member, jtc_channel: discord.VoiceChannel):
        """
        Create a temporary voice channel for a user
        """
        try:
            # Get category from JTC channel
            category = jtc_channel.category
            
            # Create channel name from user's name
            channel_name = f"{member.display_name}'s Channel"
            
            # Create the channel with permission for the creator to manage it
            overwrites = {
                member.guild.default_role: discord.PermissionOverwrite(
                    connect=True,
                    speak=True
                ),
                member: discord.PermissionOverwrite(
                    connect=True,
                    speak=True,
                    move_members=True,
                    mute_members=True,
                    manage_channels=True
                ),
                member.guild.me: discord.PermissionOverwrite(
                    connect=True,
                    speak=True,
                    move_members=True,
                    manage_channels=True
                )
            }
            
            # Create the channel
            temp_channel = await member.guild.create_voice_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Temp voice channel for {member}"
            )
            
            # Move the user to the new channel
            await member.move_to(temp_channel, reason="JTC system")
            
            # Store temp channel
            self.temp_channels[member.id] = temp_channel.id
            
            # Store in database
            self.bot.db.insert("voice_channels", {
                "guild_id": member.guild.id,
                "channel_id": temp_channel.id,
                "user_id": member.id,
                "type": "temp",
                "active": True,
                "created_at": asyncio.get_event_loop().time()
            })
            
            logger.info(f"Created temp voice channel {temp_channel.name} for {member}")
            
        except discord.Forbidden:
            logger.error(f"Missing permissions to create voice channel for {member}")
        except Exception as e:
            logger.error(f"Error creating temp voice channel: {e}", exc_info=True)
            
    async def delete_temp_voice_channel(self, member: discord.Member, channel: discord.VoiceChannel):
        """
        Delete a temporary voice channel
        """
        try:
            # Delete the channel
            await channel.delete(reason=f"Temp voice channel emptied")
            
            # Update records
            if member.id in self.temp_channels:
                del self.temp_channels[member.id]
                
            # Update database
            temp_channel = self.bot.db.get_one("voice_channels", {
                "channel_id": channel.id,
                "user_id": member.id,
                "type": "temp",
                "active": True
            })
            
            if temp_channel:
                self.bot.db.update("voice_channels", temp_channel["id"], {
                    **temp_channel,
                    "active": False,
                    "deleted_at": asyncio.get_event_loop().time()
                })
                
            logger.info(f"Deleted temp voice channel {channel.name}")
            
        except discord.Forbidden:
            logger.error(f"Missing permissions to delete voice channel {channel.name}")
        except Exception as e:
            logger.error(f"Error deleting temp voice channel: {e}", exc_info=True)
            
    @app_commands.command(name="setupvc", description="Set up the join-to-create voice system in a category")
    @app_commands.describe(
        category="The category to create the join-to-create channel in"
    )
    @app_commands.default_permissions(administrator=True)
    async def setup_vc(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        """
        Set up the join-to-create voice system
        """
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to use this command."),
                ephemeral=True
            )
            return
            
        try:
            # Create the JTC channel
            jtc_channel = await interaction.guild.create_voice_channel(
                name="Join to Create",
                category=category,
                reason=f"JTC system created by {interaction.user}"
            )
            
            # Store in database
            guild_id = interaction.guild.id
            
            # Check if setup already exists
            existing = self.bot.db.get_one("voice_channels", {
                "guild_id": guild_id,
                "type": "jtc"
            })
            
            if existing:
                # Update existing
                self.bot.db.update("voice_channels", existing["id"], {
                    "guild_id": guild_id,
                    "channel_id": jtc_channel.id,
                    "category_id": category.id,
                    "updated_at": asyncio.get_event_loop().time(),
                    "updated_by": interaction.user.id
                })
            else:
                # Create new
                self.bot.db.insert("voice_channels", {
                    "guild_id": guild_id,
                    "channel_id": jtc_channel.id,
                    "category_id": category.id,
                    "type": "jtc",
                    "created_at": asyncio.get_event_loop().time(),
                    "created_by": interaction.user.id
                })
                
            # Update cache
            self.join_to_create_channels[guild_id] = jtc_channel.id
            
            # Notify success
            await interaction.response.send_message(
                embed=create_success_embed(f"Join-to-create voice system has been set up in {category.name}.\nJoin {jtc_channel.mention} to create your own voice channel!"),
                ephemeral=True
            )
            
            logger.info(f"JTC system set up in {category.name} by {interaction.user}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("I don't have permission to create voice channels."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error setting up JTC system: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="vclimit", description="Set user limit for your voice channel")
    @app_commands.describe(
        limit="The user limit (0 for unlimited)"
    )
    async def vc_limit(self, interaction: discord.Interaction, limit: int):
        """
        Set user limit for a voice channel
        """
        # Check if user has a temp channel
        if interaction.user.id not in self.temp_channels:
            await interaction.response.send_message(
                embed=create_error_embed("You don't have a voice channel."),
                ephemeral=True
            )
            return
            
        # Get the channel
        channel_id = self.temp_channels[interaction.user.id]
        channel = interaction.guild.get_channel(channel_id)
        
        if not channel:
            await interaction.response.send_message(
                embed=create_error_embed("I couldn't find your voice channel."),
                ephemeral=True
            )
            # Clean up stale entry
            del self.temp_channels[interaction.user.id]
            return
            
        # Validate limit
        if limit < 0:
            limit = 0
        elif limit > 99:
            limit = 99
            
        # Update channel
        try:
            await channel.edit(user_limit=limit, reason=f"Limit set by {interaction.user}")
            
            # Notify success
            limit_text = "unlimited" if limit == 0 else str(limit)
            await interaction.response.send_message(
                embed=create_success_embed(f"User limit for your voice channel has been set to {limit_text}."),
                ephemeral=True
            )
            
            logger.info(f"Voice channel limit for {channel.name} set to {limit} by {interaction.user}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("I don't have permission to edit your voice channel."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error setting voice channel limit: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
            
    @app_commands.command(name="vcname", description="Rename your voice channel")
    @app_commands.describe(
        name="The new name for your voice channel"
    )
    async def vc_name(self, interaction: discord.Interaction, name: str):
        """
        Rename a voice channel
        """
        # Check if user has a temp channel
        if interaction.user.id not in self.temp_channels:
            await interaction.response.send_message(
                embed=create_error_embed("You don't have a voice channel."),
                ephemeral=True
            )
            return
            
        # Get the channel
        channel_id = self.temp_channels[interaction.user.id]
        channel = interaction.guild.get_channel(channel_id)
        
        if not channel:
            await interaction.response.send_message(
                embed=create_error_embed("I couldn't find your voice channel."),
                ephemeral=True
            )
            # Clean up stale entry
            del self.temp_channels[interaction.user.id]
            return
            
        # Validate name
        if len(name) > 100:
            name = name[:100]
            
        # Update channel
        try:
            await channel.edit(name=name, reason=f"Name changed by {interaction.user}")
            
            # Notify success
            await interaction.response.send_message(
                embed=create_success_embed(f"Your voice channel has been renamed to \"{name}\"."),
                ephemeral=True
            )
            
            logger.info(f"Voice channel {channel.id} renamed to {name} by {interaction.user}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("I don't have permission to edit your voice channel."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error renaming voice channel: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
            
    @app_commands.command(name="vclock", description="Lock or unlock your voice channel")
    @app_commands.describe(
        locked="Whether to lock or unlock the channel"
    )
    @app_commands.choices(locked=[
        app_commands.Choice(name="Lock", value="lock"),
        app_commands.Choice(name="Unlock", value="unlock")
    ])
    async def vc_lock(self, interaction: discord.Interaction, locked: str):
        """
        Lock or unlock a voice channel
        """
        # Check if user has a temp channel
        if interaction.user.id not in self.temp_channels:
            await interaction.response.send_message(
                embed=create_error_embed("You don't have a voice channel."),
                ephemeral=True
            )
            return
            
        # Get the channel
        channel_id = self.temp_channels[interaction.user.id]
        channel = interaction.guild.get_channel(channel_id)
        
        if not channel:
            await interaction.response.send_message(
                embed=create_error_embed("I couldn't find your voice channel."),
                ephemeral=True
            )
            # Clean up stale entry
            del self.temp_channels[interaction.user.id]
            return
            
        # Update permissions
        try:
            is_locking = locked == "lock"
            
            # Edit permissions for default role
            await channel.set_permissions(
                interaction.guild.default_role,
                connect=not is_locking,
                reason=f"Channel {'locked' if is_locking else 'unlocked'} by {interaction.user}"
            )
            
            # Notify success
            status = "locked" if is_locking else "unlocked"
            await interaction.response.send_message(
                embed=create_success_embed(f"Your voice channel has been {status}."),
                ephemeral=True
            )
            
            logger.info(f"Voice channel {channel.name} {status} by {interaction.user}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("I don't have permission to edit your voice channel permissions."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error updating voice channel permissions: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )

async def setup(bot):
    """
    Add the cog to the bot
    """
    await bot.add_cog(VoiceChannels(bot))
