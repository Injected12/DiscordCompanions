"""
Admin commands implementation for D10 Discord Bot
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
from typing import Optional, List

from utils.embeds import create_error_embed, create_success_embed, create_basic_embed
from utils.permissions import is_staff, can_kick_members, can_ban_members, check_hierarchy

logger = logging.getLogger("d10-bot")

class Admin(commands.Cog):
    """
    Administrative commands for server management
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.lockdown_channels = set()  # Track locked channels
        self.antiraid_mode = {}  # Track antiraid status per guild
        
    @app_commands.command(name="lockdown", description="Lock a channel or the entire server")
    @app_commands.describe(
        channel="The channel to lock (current channel if not specified)",
        reason="Reason for the lockdown"
    )
    @app_commands.default_permissions(manage_channels=True)
    async def lockdown(
        self, 
        interaction: discord.Interaction, 
        channel: Optional[discord.TextChannel] = None,
        reason: Optional[str] = "No reason provided"
    ):
        """
        Lock a channel or the entire server
        """
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to use this command."),
                ephemeral=True
            )
            return
            
        # Use current channel if none specified
        target_channel = channel or interaction.channel
        
        # Check if channel is already locked
        if target_channel.id in self.lockdown_channels:
            await interaction.response.send_message(
                embed=create_error_embed(f"{target_channel.mention} is already locked."),
                ephemeral=True
            )
            return
            
        # Lock the channel
        try:
            # Save current permissions for later restoration
            self.bot.db.insert("lockdown", {
                "guild_id": interaction.guild.id,
                "channel_id": target_channel.id,
                "send_messages": target_channel.overwrites_for(interaction.guild.default_role).send_messages,
                "add_reactions": target_channel.overwrites_for(interaction.guild.default_role).add_reactions,
                "locked_by": interaction.user.id,
                "locked_at": asyncio.get_event_loop().time(),
                "reason": reason
            })
            
            # Update permissions
            overwrites = target_channel.overwrites_for(interaction.guild.default_role)
            overwrites.send_messages = False
            overwrites.add_reactions = False
            
            await target_channel.set_permissions(
                interaction.guild.default_role,
                overwrite=overwrites,
                reason=f"Channel locked by {interaction.user} - {reason}"
            )
            
            # Add to locked channels
            self.lockdown_channels.add(target_channel.id)
            
            # Notify in channel
            await target_channel.send(
                embed=create_basic_embed(
                    title="Channel Locked",
                    description=f"This channel has been locked by {interaction.user.mention}.\nReason: {reason}",
                    color=discord.Color.red()
                )
            )
            
            # Notify command user
            await interaction.response.send_message(
                embed=create_success_embed(f"{target_channel.mention} has been locked."),
                ephemeral=True
            )
            
            logger.info(f"Channel {target_channel.name} locked by {interaction.user} - {reason}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("I don't have permission to manage this channel."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error locking channel: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
            
    @app_commands.command(name="unlock", description="Unlock a locked channel")
    @app_commands.describe(
        channel="The channel to unlock (current channel if not specified)"
    )
    @app_commands.default_permissions(manage_channels=True)
    async def unlock(
        self, 
        interaction: discord.Interaction, 
        channel: Optional[discord.TextChannel] = None
    ):
        """
        Unlock a locked channel
        """
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to use this command."),
                ephemeral=True
            )
            return
            
        # Use current channel if none specified
        target_channel = channel or interaction.channel
        
        # Check if channel is locked
        if target_channel.id not in self.lockdown_channels:
            await interaction.response.send_message(
                embed=create_error_embed(f"{target_channel.mention} is not locked."),
                ephemeral=True
            )
            return
            
        # Unlock the channel
        try:
            # Get original permissions
            lockdown_data = self.bot.db.get_one("lockdown", {
                "guild_id": interaction.guild.id,
                "channel_id": target_channel.id
            })
            
            # Update permissions
            overwrites = target_channel.overwrites_for(interaction.guild.default_role)
            
            if lockdown_data:
                # Restore original permissions
                overwrites.send_messages = lockdown_data.get("send_messages")
                overwrites.add_reactions = lockdown_data.get("add_reactions")
            else:
                # Default to None (inherit)
                overwrites.send_messages = None
                overwrites.add_reactions = None
                
            await target_channel.set_permissions(
                interaction.guild.default_role,
                overwrite=overwrites,
                reason=f"Channel unlocked by {interaction.user}"
            )
            
            # Remove from locked channels
            self.lockdown_channels.discard(target_channel.id)
            
            # Clean up database
            if lockdown_data:
                self.bot.db.delete("lockdown", lockdown_data["id"])
                
            # Notify in channel
            await target_channel.send(
                embed=create_basic_embed(
                    title="Channel Unlocked",
                    description=f"This channel has been unlocked by {interaction.user.mention}.",
                    color=discord.Color.green()
                )
            )
            
            # Notify command user
            await interaction.response.send_message(
                embed=create_success_embed(f"{target_channel.mention} has been unlocked."),
                ephemeral=True
            )
            
            logger.info(f"Channel {target_channel.name} unlocked by {interaction.user}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("I don't have permission to manage this channel."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error unlocking channel: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
            
    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(
        user="The user to ban",
        reason="Reason for the ban",
        delete_days="Number of days of messages to delete (0-7)"
    )
    @app_commands.default_permissions(ban_members=True)
    async def ban(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member,
        reason: Optional[str] = "No reason provided",
        delete_days: Optional[int] = 1
    ):
        """
        Ban a user from the server
        """
        # Check permissions
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to use this command."),
                ephemeral=True
            )
            return
            
        # Validate delete_days
        delete_days = max(0, min(7, delete_days))  # Clamp between 0 and 7
        
        # Check hierarchy
        if not can_ban_members(interaction.guild, interaction.user, user):
            await interaction.response.send_message(
                embed=create_error_embed("You cannot ban this user due to role hierarchy."),
                ephemeral=True
            )
            return
            
        # Check bot hierarchy
        if not can_ban_members(interaction.guild, interaction.guild.me, user):
            await interaction.response.send_message(
                embed=create_error_embed("I cannot ban this user due to role hierarchy."),
                ephemeral=True
            )
            return
            
        # Ban the user
        try:
            # DM the user
            try:
                embed = create_error_embed(
                    description=f"You have been banned from {interaction.guild.name}\nReason: {reason}",
                    title="Ban Notice"
                )
                await user.send(embed=embed)
            except:
                # Couldn't DM the user, continue anyway
                pass
                
            # Ban the user
            await interaction.guild.ban(
                user,
                reason=f"Banned by {interaction.user}: {reason}",
                delete_message_days=delete_days
            )
            
            # Log the ban
            self.bot.db.insert("moderation", {
                "guild_id": interaction.guild.id,
                "user_id": user.id,
                "moderator_id": interaction.user.id,
                "action": "ban",
                "reason": reason,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            # Notify command user
            await interaction.response.send_message(
                embed=create_success_embed(f"{user} has been banned.\nReason: {reason}"),
                ephemeral=True
            )
            
            logger.info(f"User {user} banned by {interaction.user} - {reason}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("I don't have permission to ban users."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error banning user: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
            
    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(
        user="The user to kick",
        reason="Reason for the kick"
    )
    @app_commands.default_permissions(kick_members=True)
    async def kick(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member,
        reason: Optional[str] = "No reason provided"
    ):
        """
        Kick a user from the server
        """
        # Check permissions
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to use this command."),
                ephemeral=True
            )
            return
            
        # Check hierarchy
        if not can_kick_members(interaction.guild, interaction.user, user):
            await interaction.response.send_message(
                embed=create_error_embed("You cannot kick this user due to role hierarchy."),
                ephemeral=True
            )
            return
            
        # Check bot hierarchy
        if not can_kick_members(interaction.guild, interaction.guild.me, user):
            await interaction.response.send_message(
                embed=create_error_embed("I cannot kick this user due to role hierarchy."),
                ephemeral=True
            )
            return
            
        # Kick the user
        try:
            # DM the user
            try:
                embed = create_error_embed(
                    description=f"You have been kicked from {interaction.guild.name}\nReason: {reason}",
                    title="Kick Notice"
                )
                await user.send(embed=embed)
            except:
                # Couldn't DM the user, continue anyway
                pass
                
            # Kick the user
            await interaction.guild.kick(
                user,
                reason=f"Kicked by {interaction.user}: {reason}"
            )
            
            # Log the kick
            self.bot.db.insert("moderation", {
                "guild_id": interaction.guild.id,
                "user_id": user.id,
                "moderator_id": interaction.user.id,
                "action": "kick",
                "reason": reason,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            # Notify command user
            await interaction.response.send_message(
                embed=create_success_embed(f"{user} has been kicked.\nReason: {reason}"),
                ephemeral=True
            )
            
            logger.info(f"User {user} kicked by {interaction.user} - {reason}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("I don't have permission to kick users."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error kicking user: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="mute", description="Mute a user in the server")
    @app_commands.describe(
        user="The user to mute",
        duration="Duration of the mute (e.g., 1h, 30m, 1d)",
        reason="Reason for the mute"
    )
    @app_commands.default_permissions(moderate_members=True)
    async def mute(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member,
        duration: str,
        reason: Optional[str] = "No reason provided"
    ):
        """
        Timeout (mute) a user
        """
        from utils.helpers import parse_time_string, format_duration
        
        # Check permissions
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to use this command."),
                ephemeral=True
            )
            return
            
        # Parse duration
        seconds = parse_time_string(duration)
        if seconds is None:
            await interaction.response.send_message(
                embed=create_error_embed("Invalid duration format. Use e.g., 1h, 30m, 1d."),
                ephemeral=True
            )
            return
            
        # Cap duration at 28 days (Discord limit)
        if seconds > 2419200:  # 28 days in seconds
            seconds = 2419200
            
        # Check hierarchy
        if not await check_hierarchy(interaction.guild, interaction.user, user):
            await interaction.response.send_message(
                embed=create_error_embed("You cannot mute this user due to role hierarchy."),
                ephemeral=True
            )
            return
            
        # Apply timeout
        try:
            # Calculate until time
            until = discord.utils.utcnow() + asyncio.timedelta(seconds=seconds)
            
            # Timeout the user
            await user.timeout(until, reason=f"Muted by {interaction.user}: {reason}")
            
            # Log the mute
            self.bot.db.insert("moderation", {
                "guild_id": interaction.guild.id,
                "user_id": user.id,
                "moderator_id": interaction.user.id,
                "action": "mute",
                "duration": seconds,
                "reason": reason,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            # Format duration for display
            duration_text = format_duration(seconds)
            
            # Notify command user
            await interaction.response.send_message(
                embed=create_success_embed(
                    f"{user} has been muted for {duration_text}.\nReason: {reason}"
                ),
                ephemeral=True
            )
            
            # Try to DM the user
            try:
                embed = create_error_embed(
                    description=f"You have been muted in {interaction.guild.name} for {duration_text}\nReason: {reason}",
                    title="Mute Notice"
                )
                await user.send(embed=embed)
            except:
                # Couldn't DM the user
                pass
                
            logger.info(f"User {user} muted by {interaction.user} for {duration_text} - {reason}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("I don't have permission to mute users."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error muting user: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
            
    @app_commands.command(name="unmute", description="Unmute a muted user")
    @app_commands.describe(
        user="The user to unmute",
        reason="Reason for the unmute"
    )
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = "No reason provided"
    ):
        """
        Remove timeout from a user
        """
        # Check permissions
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to use this command."),
                ephemeral=True
            )
            return
            
        # Check if user is timed out
        if not user.is_timed_out():
            await interaction.response.send_message(
                embed=create_error_embed(f"{user} is not muted."),
                ephemeral=True
            )
            return
            
        # Remove timeout
        try:
            await user.timeout(None, reason=f"Unmuted by {interaction.user}: {reason}")
            
            # Log the unmute
            self.bot.db.insert("moderation", {
                "guild_id": interaction.guild.id,
                "user_id": user.id,
                "moderator_id": interaction.user.id,
                "action": "unmute",
                "reason": reason,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            # Notify command user
            await interaction.response.send_message(
                embed=create_success_embed(f"{user} has been unmuted."),
                ephemeral=True
            )
            
            logger.info(f"User {user} unmuted by {interaction.user} - {reason}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("I don't have permission to unmute users."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error unmuting user: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="clearserver", description="Clear channels or roles in the server")
    @app_commands.describe(
        target="What to clear (channels or roles)",
        filter="Optional filter (e.g., 'category:name' or 'prefix:test')"
    )
    @app_commands.choices(target=[
        app_commands.Choice(name="Channels", value="channels"),
        app_commands.Choice(name="Roles", value="roles")
    ])
    @app_commands.default_permissions(administrator=True)
    async def clear_server(
        self,
        interaction: discord.Interaction,
        target: str,
        filter: Optional[str] = None
    ):
        """
        Clear channels or roles
        """
        # Check permissions (admin only)
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=create_error_embed("You must be an administrator to use this command."),
                ephemeral=True
            )
            return
            
        # Confirm action
        await interaction.response.send_message(
            f"Are you sure you want to clear {target}" + (f" with filter '{filter}'" if filter else "") + "?",
            view=ClearServerConfirmView(self.bot, target, filter),
            ephemeral=True
        )
        
    @app_commands.command(name="antiraid", description="Toggle anti-raid mode")
    @app_commands.describe(
        action="Enable or disable anti-raid mode"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Enable", value="enable"),
        app_commands.Choice(name="Disable", value="disable")
    ])
    @app_commands.default_permissions(administrator=True)
    async def antiraid(
        self,
        interaction: discord.Interaction,
        action: str
    ):
        """
        Toggle anti-raid mode
        """
        # Check permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=create_error_embed("You must be an administrator to use this command."),
                ephemeral=True
            )
            return
            
        guild_id = interaction.guild.id
        
        if action == "enable":
            # Enable anti-raid mode
            self.antiraid_mode[guild_id] = {
                "enabled": True,
                "enabled_by": interaction.user.id,
                "enabled_at": asyncio.get_event_loop().time()
            }
            
            # Notify
            await interaction.response.send_message(
                embed=create_success_embed(
                    "Anti-raid mode has been enabled. New accounts will be automatically kicked."
                ),
                ephemeral=True
            )
            
            # Announce in server
            try:
                channel = interaction.channel
                await channel.send(
                    embed=create_basic_embed(
                        title="Anti-Raid Mode Enabled",
                        description=f"Anti-raid mode has been enabled by {interaction.user.mention}. New accounts will be automatically kicked.",
                        color=discord.Color.red()
                    )
                )
            except:
                pass
                
            logger.info(f"Anti-raid mode enabled by {interaction.user}")
            
        else:
            # Disable anti-raid mode
            if guild_id in self.antiraid_mode:
                del self.antiraid_mode[guild_id]
                
            # Notify
            await interaction.response.send_message(
                embed=create_success_embed(
                    "Anti-raid mode has been disabled."
                ),
                ephemeral=True
            )
            
            # Announce in server
            try:
                channel = interaction.channel
                await channel.send(
                    embed=create_basic_embed(
                        title="Anti-Raid Mode Disabled",
                        description=f"Anti-raid mode has been disabled by {interaction.user.mention}.",
                        color=discord.Color.green()
                    )
                )
            except:
                pass
                
            logger.info(f"Anti-raid mode disabled by {interaction.user}")
            
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Check new members in anti-raid mode
        """
        guild_id = member.guild.id
        
        # Check if anti-raid mode is enabled
        if guild_id not in self.antiraid_mode or not self.antiraid_mode[guild_id]["enabled"]:
            return
            
        # Check account age
        account_age = (datetime.datetime.now() - member.created_at).days
        
        if account_age < 7:  # Less than 7 days old
            try:
                # DM the user
                try:
                    embed = create_error_embed(
                        description=f"You have been kicked from {member.guild.name} because your account is too new and the server is in anti-raid mode.",
                        title="Anti-Raid Protection"
                    )
                    await member.send(embed=embed)
                except:
                    # Couldn't DM the user
                    pass
                    
                # Kick the member
                await member.kick(reason="Anti-raid mode: New account")
                
                # Log action
                logger.info(f"Kicked new account {member} (age: {account_age} days) due to anti-raid mode")
                
                # Notify staff in log channel if configured
                log_channel_id = self.bot.db.get_one("config", {"key": "log_channel"})
                if log_channel_id:
                    channel = member.guild.get_channel(log_channel_id.get("value"))
                    if channel:
                        await channel.send(
                            embed=create_basic_embed(
                                title="Anti-Raid Protection",
                                description=f"Kicked new account: {member.mention} (age: {account_age} days)",
                                color=discord.Color.orange()
                            )
                        )
                        
            except Exception as e:
                logger.error(f"Error kicking new account in anti-raid mode: {e}", exc_info=True)


class ClearServerConfirmView(discord.ui.View):
    """
    View for confirming server clearing
    """
    def __init__(self, bot, target, filter=None):
        super().__init__(timeout=60)
        self.bot = bot
        self.target = target
        self.filter = filter
        
    @discord.ui.button(label="Yes, I'm sure", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Confirm server clearing
        """
        # Disable buttons
        self.clear_items()
        await interaction.response.edit_message(
            content=f"Clearing {self.target}...",
            view=self,
            embed=None
        )
        
        if self.target == "channels":
            await self.clear_channels(interaction)
        elif self.target == "roles":
            await self.clear_roles(interaction)
            
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Cancel server clearing
        """
        await interaction.response.edit_message(
            content="Operation cancelled.",
            view=None,
            embed=None
        )
        
    async def clear_channels(self, interaction: discord.Interaction):
        """
        Clear channels based on filter
        """
        guild = interaction.guild
        deleted_count = 0
        skipped_count = 0
        protected = ["ticket", "welcome", "log", "rules", "info", "announcement"]  # Protected names
        
        # Parse filter
        filter_type = None
        filter_value = None
        
        if self.filter:
            if ":" in self.filter:
                filter_parts = self.filter.split(":", 1)
                filter_type = filter_parts[0].lower()
                filter_value = filter_parts[1].lower()
                
        # Process channels
        for channel in list(guild.channels):  # Use list to avoid modification during iteration
            # Skip protected channels
            if any(p in channel.name.lower() for p in protected):
                skipped_count += 1
                continue
                
            # Apply filter
            if filter_type:
                if filter_type == "category" and isinstance(channel, discord.CategoryChannel):
                    if filter_value not in channel.name.lower():
                        continue
                elif filter_type == "prefix":
                    if not channel.name.lower().startswith(filter_value):
                        continue
                        
            # Delete the channel
            try:
                await channel.delete(reason=f"Server cleanup by {interaction.user}")
                deleted_count += 1
                # Add delay to avoid rate limits
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error deleting channel {channel.name}: {e}")
                skipped_count += 1
                
        # Send results
        await interaction.edit_original_response(
            content=f"Cleared {deleted_count} channels. Skipped {skipped_count} channels.",
            view=None
        )
        
        logger.info(f"Server channels cleared by {interaction.user}: {deleted_count} deleted, {skipped_count} skipped")
        
    async def clear_roles(self, interaction: discord.Interaction):
        """
        Clear roles based on filter
        """
        guild = interaction.guild
        deleted_count = 0
        skipped_count = 0
        protected = ["admin", "mod", "staff", "owner", "bot", "@everyone"]  # Protected roles
        
        # Parse filter
        filter_type = None
        filter_value = None
        
        if self.filter:
            if ":" in self.filter:
                filter_parts = self.filter.split(":", 1)
                filter_type = filter_parts[0].lower()
                filter_value = filter_parts[1].lower()
                
        # Process roles
        for role in list(guild.roles):  # Use list to avoid modification during iteration
            # Skip protected roles
            if role.name == "@everyone" or any(p in role.name.lower() for p in protected):
                skipped_count += 1
                continue
                
            # Skip roles higher than the bot
            if role >= guild.me.top_role:
                skipped_count += 1
                continue
                
            # Apply filter
            if filter_type:
                if filter_type == "prefix":
                    if not role.name.lower().startswith(filter_value):
                        continue
                        
            # Delete the role
            try:
                await role.delete(reason=f"Server cleanup by {interaction.user}")
                deleted_count += 1
                # Add delay to avoid rate limits
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error deleting role {role.name}: {e}")
                skipped_count += 1
                
        # Send results
        await interaction.edit_original_response(
            content=f"Cleared {deleted_count} roles. Skipped {skipped_count} roles.",
            view=None
        )
        
        logger.info(f"Server roles cleared by {interaction.user}: {deleted_count} deleted, {skipped_count} skipped")
        
    async def on_timeout(self):
        """
        Handle timeout
        """
        self.clear_items()

async def setup(bot):
    """
    Add the cog to the bot
    """
    await bot.add_cog(Admin(bot))
