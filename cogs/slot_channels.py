"""
Slot channel system implementation for D10 Discord Bot
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
import datetime
import json
import io
from typing import Dict, List, Optional, Any, Union

from utils.embeds import create_slot_embed, create_error_embed, create_success_embed, create_slot_ping_embed
from utils.permissions import is_staff, has_staff_role
from utils.helpers import format_timestamp, format_duration, parse_time_string
from utils.transcript import generate_text_transcript, generate_slot_data, send_transcript_dm

logger = logging.getLogger("d10-bot")

class SlotChannels(commands.Cog):
    """
    Slot channel system for temporary user channels
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.active_slots = {}  # Stores active slot data
        
    async def cog_load(self):
        """
        Called when the cog is loaded
        """
        # Load existing slots from database
        self.load_slots()
        
        # Start background task to check slot expirations
        self.expiration_task = self.bot.loop.create_task(self.check_slot_expirations())
        
    def load_slots(self):
        """
        Load active slots from database
        """
        try:
            slots = self.bot.db.get("slot_channels", {"active": True})
            
            for slot in slots:
                channel_id = slot.get("channel_id")
                if channel_id:
                    self.active_slots[channel_id] = slot
                    
            logger.info(f"Loaded {len(self.active_slots)} active slot channels")
        except Exception as e:
            logger.error(f"Error loading slots: {e}", exc_info=True)
            
    async def cog_unload(self):
        """
        Called when the cog is unloaded
        """
        # Cancel background task
        if hasattr(self, 'expiration_task'):
            self.expiration_task.cancel()
            
    async def check_slot_expirations(self):
        """
        Background task to check slot expirations
        """
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                now = datetime.datetime.now().timestamp()
                channels_to_remove = []
                
                # Check each active slot
                for channel_id, slot_data in self.active_slots.items():
                    # Check if expired
                    expires_at = slot_data.get("expires_at", 0)
                    
                    # Convert expires_at to timestamp if it's a datetime object
                    if isinstance(expires_at, datetime.datetime):
                        expires_at = expires_at.timestamp()
                    
                    # Skip if expires_at is not valid
                    if not expires_at:
                        continue
                        
                    if now > expires_at:
                        # Get channel
                        channel = self.bot.get_channel(channel_id)
                        
                        if channel:
                            # Get user
                            user_id = slot_data.get("user_id")
                            user = None
                            
                            if user_id:
                                guild = channel.guild
                                user = guild.get_member(user_id) or await self.bot.fetch_user(user_id)
                                
                            # Send expiration message
                            try:
                                await channel.send(
                                    embed=create_error_embed(
                                        "This slot channel has expired and will be deleted in 5 minutes."
                                    )
                                )
                                
                                # Send transcript to user if available
                                if user:
                                    await send_transcript_dm(
                                        user, 
                                        channel, 
                                        slot_data
                                    )
                                    
                                # Wait 5 minutes
                                await asyncio.sleep(300)
                                
                                # Delete channel
                                await channel.delete(reason="Slot channel expired")
                                logger.info(f"Deleted expired slot channel {channel.name} (ID: {channel.id})")
                                
                            except Exception as e:
                                logger.error(f"Error deleting expired slot: {e}", exc_info=True)
                                
                        # Mark for removal
                        channels_to_remove.append(channel_id)
                        
                        # Update in database
                        self.bot.db.update("slot_channels", slot_data["id"], {
                            **slot_data,
                            "active": False,
                            "closed_at": now,
                            "closed_reason": "expired"
                        })
                
                # Remove expired channels from active_slots
                for channel_id in channels_to_remove:
                    self.active_slots.pop(channel_id, None)
                    
            except Exception as e:
                logger.error(f"Error checking slot expirations: {e}", exc_info=True)
                
            # Check every minute
            await asyncio.sleep(60)
            
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Monitor pings in slot channels
        """
        # Ignore DMs and bot messages
        if not message.guild or message.author.bot:
            return
            
        # Check if this is a slot channel
        if message.channel.id not in self.active_slots:
            return
            
        slot_data = self.active_slots[message.channel.id]
        user_id = slot_data.get("user_id")
        
        # Skip if not the slot owner
        if message.author.id != user_id:
            return
            
        # Check for @everyone and @here pings
        everyone_ping = False
        here_ping = False
        
        if message.mention_everyone:
            # Determine which type of ping
            if "@everyone" in message.content:
                everyone_ping = True
            if "@here" in message.content:
                here_ping = True
                
        # Process @everyone ping
        if everyone_ping:
            everyone_pings = slot_data.get("everyone_pings", 0)
            everyone_pings_used = slot_data.get("everyone_pings_used", 0)
            
            if everyone_pings_used >= everyone_pings:
                # Over limit, delete message
                try:
                    await message.delete()
                    await message.channel.send(
                        embed=create_error_embed(f"{message.author.mention}, you have used all your @everyone pings."),
                        delete_after=10
                    )
                    return
                except discord.Forbidden:
                    pass
                    
            # Increment used pings
            slot_data["everyone_pings_used"] = everyone_pings_used + 1
            remaining = everyone_pings - (everyone_pings_used + 1)
            
            # Update database
            self.bot.db.update("slot_channels", slot_data["id"], slot_data)
            
            # Notify
            embed = create_slot_ping_embed(message.author, "@everyone", remaining)
            await message.channel.send(embed=embed)
            
            # Check if limit reached
            if remaining <= 0:
                await message.channel.send(
                    embed=create_error_embed(
                        f"{message.author.mention}, you have now used all your @everyone pings."
                    )
                )
                
        # Process @here ping
        if here_ping:
            here_pings = slot_data.get("here_pings", 0)
            here_pings_used = slot_data.get("here_pings_used", 0)
            
            if here_pings_used >= here_pings:
                # Over limit, delete message
                try:
                    await message.delete()
                    await message.channel.send(
                        embed=create_error_embed(f"{message.author.mention}, you have used all your @here pings."),
                        delete_after=10
                    )
                    return
                except discord.Forbidden:
                    pass
                    
            # Increment used pings
            slot_data["here_pings_used"] = here_pings_used + 1
            remaining = here_pings - (here_pings_used + 1)
            
            # Update database
            self.bot.db.update("slot_channels", slot_data["id"], slot_data)
            
            # Notify
            embed = create_slot_ping_embed(message.author, "@here", remaining)
            await message.channel.send(embed=embed)
            
            # Check if limit reached
            if remaining <= 0:
                await message.channel.send(
                    embed=create_error_embed(
                        f"{message.author.mention}, you have now used all your @here pings."
                    )
                )
                
        # Check if both limits reached
        everyone_pings = slot_data.get("everyone_pings", 0)
        everyone_pings_used = slot_data.get("everyone_pings_used", 0)
        here_pings = slot_data.get("here_pings", 0)
        here_pings_used = slot_data.get("here_pings_used", 0)
        
        if (everyone_pings_used >= everyone_pings and here_pings_used >= here_pings):
            # Both limits reached, schedule removal
            await message.channel.send(
                embed=create_error_embed(
                    "You have reached all ping limits. This slot channel will be removed in 5 minutes."
                )
            )
            
            # Mark as inactive and remove from active slots
            slot_data["active"] = False
            self.bot.db.update("slot_channels", slot_data["id"], slot_data)
            self.active_slots.pop(message.channel.id, None)
            
            # Send transcript to user
            user = message.author
            await send_transcript_dm(user, message.channel, slot_data)
            
            # Wait 5 minutes
            await asyncio.sleep(300)
            
            # Delete channel
            try:
                await message.channel.delete(reason="Slot ping limits reached")
                logger.info(f"Deleted slot channel {message.channel.name} due to ping limits")
                
                # Remove from active slots
                self.active_slots.pop(message.channel.id, None)
                
            except Exception as e:
                logger.error(f"Error deleting slot channel: {e}", exc_info=True)
                
    @app_commands.command(name="createslot", description="Create a slot channel for a user")
    @app_commands.describe(
        user="The user to create a slot for",
        duration="Duration in days",
        everyone_pings="Number of @everyone pings allowed",
        here_pings="Number of @here pings allowed",
        category="Category for the slot channel"
    )
    @app_commands.default_permissions(manage_channels=True)
    async def create_slot(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member,
        duration: int,
        everyone_pings: int,
        here_pings: int,
        category: str
    ):
        """
        Create a slot channel for a user
        """
        # Check if command user has permission
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to create slot channels."),
                ephemeral=True
            )
            return
            
        # Validate parameters
        if duration <= 0:
            await interaction.response.send_message(
                embed=create_error_embed("Duration must be at least 1 day."),
                ephemeral=True
            )
            return
            
        if everyone_pings < 0 or here_pings < 0:
            await interaction.response.send_message(
                embed=create_error_embed("Ping limits cannot be negative."),
                ephemeral=True
            )
            return
            
        # Defer response as channel creation might take time
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get or create slot category
            slot_category = None
            for cat in interaction.guild.categories:
                if cat.name.lower() == category.lower():
                    slot_category = cat
                    break
                    
            if not slot_category:
                slot_category = await interaction.guild.create_category(
                    name=category,
                    reason=f"Slot category created by {interaction.user}"
                )
                
            # Create the channel
            channel_name = f"slot-{user.name.lower()}"
            channel_name = channel_name[:100]  # Discord channel name length limit
            
            # Create permissions for the slot channel
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False,
                    read_message_history=True
                ),
                user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True,
                    embed_links=True,
                    attach_files=True,
                    mention_everyone=True
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_messages=True,
                    manage_channels=True
                )
            }
            
            # Add staff role permissions
            if hasattr(self.bot, 'staff_role_id'):
                staff_role = interaction.guild.get_role(self.bot.staff_role_id)
                if staff_role:
                    overwrites[staff_role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_messages=True
                    )
            
            # Create the channel
            channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=slot_category,
                overwrites=overwrites,
                reason=f"Slot channel created by {interaction.user} for {user}"
            )
            
            # Calculate expiry date
            now = datetime.datetime.now()
            expires_at = now + datetime.timedelta(days=duration)
            
            # Store slot info in database
            slot_id = self.bot.db.insert("slot_channels", {
                "guild_id": interaction.guild.id,
                "channel_id": channel.id,
                "user_id": user.id,
                "duration_days": duration,
                "everyone_pings": everyone_pings,
                "everyone_pings_used": 0,
                "here_pings": here_pings,
                "here_pings_used": 0,
                "category_id": slot_category.id,
                "created_at": now.timestamp(),
                "expires_at": expires_at.timestamp(),
                "created_by": interaction.user.id,
                "active": True
            })
            
            # Add to active slots
            slot_data = self.bot.db.get_one("slot_channels", {"id": slot_id})
            self.active_slots[channel.id] = slot_data
            
            # Create and send slot info embed
            embed = create_slot_embed(
                user,
                duration,
                everyone_pings,
                here_pings,
                category
            )
            
            await channel.send(
                embed=embed
            )
            
            # Notify success
            await interaction.followup.send(
                embed=create_success_embed(f"Slot channel created: {channel.mention}")
            )
            
            logger.info(f"Slot channel created: {channel.name} (ID: {channel.id}) for {user} by {interaction.user}")
            
        except discord.Forbidden:
            await interaction.followup.send(
                embed=create_error_embed("I don't have permission to create channels.")
            )
        except Exception as e:
            logger.error(f"Error creating slot channel: {e}", exc_info=True)
            await interaction.followup.send(
                embed=create_error_embed(f"An error occurred: {str(e)}")
            )
            
    @app_commands.command(name="closeslot", description="Close and delete a slot channel")
    async def close_slot(self, interaction: discord.Interaction):
        """
        Close a slot channel
        """
        # Check if the channel is a slot
        if interaction.channel.id not in self.active_slots:
            await interaction.response.send_message(
                embed=create_error_embed("This is not a slot channel."),
                ephemeral=True
            )
            return
            
        slot_data = self.active_slots[interaction.channel.id]
        user_id = slot_data.get("user_id")
        
        # Check if user is staff or slot owner
        if not (is_staff(interaction) or interaction.user.id == user_id):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to close this slot."),
                ephemeral=True
            )
            return
            
        # Confirm closure
        await interaction.response.send_message(
            "Are you sure you want to close this slot channel?",
            view=SlotCloseConfirmView(self),
            ephemeral=True
        )
            
    @app_commands.command(name="restore", description="Restore a slot channel from data")
    @app_commands.describe(
        username="The username of the slot to restore"
    )
    @app_commands.default_permissions(manage_channels=True)
    async def restore_slot(self, interaction: discord.Interaction, username: str):
        """
        Restore a slot channel from data
        """
        # Check if command user has permission
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to restore slot channels."),
                ephemeral=True
            )
            return
            
        # Ask for the data file
        await interaction.response.send_message(
            "Please upload the data.json file from the transcript DM.",
            ephemeral=True
        )
        
        def check(m):
            return (
                m.author.id == interaction.user.id and 
                m.channel.id == interaction.channel.id and
                m.attachments
            )
            
        try:
            # Wait for file upload
            message = await self.bot.wait_for('message', check=check, timeout=60)
            
            # Get the first attachment
            if not message.attachments:
                await interaction.followup.send(
                    embed=create_error_embed("No attachments found."),
                    ephemeral=True
                )
                return
                
            attachment = message.attachments[0]
            
            # Check if it's a JSON file
            if not attachment.filename.endswith('.json'):
                await interaction.followup.send(
                    embed=create_error_embed("Please upload a .json file."),
                    ephemeral=True
                )
                return
                
            # Download and parse the file
            try:
                content = await attachment.read()
                data = json.loads(content)
                
                # Validate data
                required_fields = [
                    "user_id", "duration_days", "everyone_pings", "here_pings",
                    "category_id", "everyone_pings_used", "here_pings_used"
                ]
                
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    await interaction.followup.send(
                        embed=create_error_embed(f"Invalid data file. Missing fields: {', '.join(missing_fields)}"),
                        ephemeral=True
                    )
                    return
                    
                # Get user
                user_id = int(data["user_id"])
                user = interaction.guild.get_member(user_id)
                
                if not user:
                    await interaction.followup.send(
                        embed=create_error_embed(f"User with ID {user_id} not found in this server."),
                        ephemeral=True
                    )
                    return
                    
                # Restore the slot channel
                await self.restore_slot_channel(interaction, data, user, username)
                
            except json.JSONDecodeError:
                await interaction.followup.send(
                    embed=create_error_embed("Invalid JSON file."),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error restoring slot: {e}", exc_info=True)
                await interaction.followup.send(
                    embed=create_error_embed(f"An error occurred: {str(e)}"),
                    ephemeral=True
                )
                
        except asyncio.TimeoutError:
            await interaction.followup.send(
                embed=create_error_embed("Timed out waiting for file upload."),
                ephemeral=True
            )
            
    async def restore_slot_channel(self, interaction, data, user, username):
        """
        Restore a slot channel from data
        """
        # Get category
        category_id = data.get("category_id")
        category = interaction.guild.get_channel(category_id)
        
        # If category doesn't exist, create a new one
        if not category:
            category = await interaction.guild.create_category(
                name="Restored Slots",
                reason=f"Slot restoration by {interaction.user}"
            )
            
        # Create channel name
        channel_name = f"slot-{username.lower()}"
        channel_name = channel_name[:100]  # Discord channel name length limit
        
        # Create permissions
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=False,
                read_message_history=True
            ),
            user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                read_message_history=True,
                embed_links=True,
                attach_files=True,
                mention_everyone=True
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                manage_channels=True
            )
        }
        
        # Add staff role permissions
        if hasattr(self.bot, 'staff_role_id'):
            staff_role = interaction.guild.get_role(self.bot.staff_role_id)
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_messages=True
                )
                
        # Create the channel
        try:
            channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Slot channel restored by {interaction.user} for {user}"
            )
            
            # Get data values
            duration_days = data.get("duration_days", 7)
            everyone_pings = data.get("everyone_pings", 0)
            everyone_pings_used = data.get("everyone_pings_used", 0)
            here_pings = data.get("here_pings", 0)
            here_pings_used = data.get("here_pings_used", 0)
            
            # Calculate expiry date
            now = datetime.datetime.now()
            expires_at = now + datetime.timedelta(days=duration_days)
            
            # Store slot info in database
            slot_id = self.bot.db.insert("slot_channels", {
                "guild_id": interaction.guild.id,
                "channel_id": channel.id,
                "user_id": user.id,
                "duration_days": duration_days,
                "everyone_pings": everyone_pings,
                "everyone_pings_used": everyone_pings_used,
                "here_pings": here_pings,
                "here_pings_used": here_pings_used,
                "category_id": category.id,
                "created_at": now.timestamp(),
                "expires_at": expires_at.timestamp(),
                "created_by": interaction.user.id,
                "active": True,
                "restored": True,
                "restored_at": now.timestamp(),
                "restored_by": interaction.user.id
            })
            
            # Add to active slots
            slot_data = self.bot.db.get_one("slot_channels", {"id": slot_id})
            self.active_slots[channel.id] = slot_data
            
            # Create and send slot info embed
            remaining_everyone = everyone_pings - everyone_pings_used
            remaining_here = here_pings - here_pings_used
            
            embed = discord.Embed(
                title="Slot Channel Restored",
                description=f"Slot channel for {user.mention} has been restored.",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Duration", value=f"{duration_days} days", inline=True)
            embed.add_field(name="Expires", value=format_timestamp(expires_at), inline=True)
            embed.add_field(name="Category", value=category.name, inline=True)
            embed.add_field(name="@everyone Pings", value=f"{remaining_everyone} remaining", inline=True)
            embed.add_field(name="@here Pings", value=f"{remaining_here} remaining", inline=True)
            
            await channel.send(embed=embed)
            
            # Notify success
            await interaction.followup.send(
                embed=create_success_embed(f"Slot channel restored: {channel.mention}"),
                ephemeral=True
            )
            
            logger.info(f"Slot channel restored: {channel.name} (ID: {channel.id}) for {user} by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error restoring slot channel: {e}", exc_info=True)
            await interaction.followup.send(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )

class SlotCloseConfirmView(discord.ui.View):
    """
    View for confirming slot closure
    """
    def __init__(self, cog):
        super().__init__(timeout=60)
        self.cog = cog
        
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Confirm slot closure
        """
        self.clear_items()
        await interaction.response.edit_message(
            content="Closing slot channel...",
            view=self,
            embed=None
        )
        
        # Get slot data
        channel = interaction.channel
        slot_data = self.cog.active_slots.get(channel.id)
        
        if not slot_data:
            await interaction.followup.send(
                embed=create_error_embed("This is not a slot channel or it has already been closed."),
                ephemeral=True
            )
            return
            
        # Get user
        user_id = slot_data.get("user_id")
        user = interaction.guild.get_member(user_id) or await self.cog.bot.fetch_user(user_id)
        
        # Send transcript to user
        if user:
            await send_transcript_dm(user, channel, slot_data)
            
        # Update status in database
        self.cog.bot.db.update("slot_channels", slot_data["id"], {
            **slot_data,
            "active": False,
            "closed_at": datetime.datetime.now().timestamp(),
            "closed_by": interaction.user.id,
            "closed_reason": "manual"
        })
        
        # Remove from active slots
        self.cog.active_slots.pop(channel.id, None)
        
        # Notify closure
        await channel.send(
            embed=create_error_embed(f"This slot channel has been closed by {interaction.user.mention}. Channel will be deleted in 10 seconds.")
        )
        
        # Wait and delete channel
        await asyncio.sleep(10)
        try:
            await channel.delete(reason=f"Slot closed by {interaction.user}")
        except Exception as e:
            logger.error(f"Error deleting slot channel: {e}", exc_info=True)
            
    @discord.ui.button(label="No", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Cancel slot closure
        """
        await interaction.response.edit_message(
            content="Slot closure cancelled.",
            view=None,
            embed=None
        )
        
    async def on_timeout(self):
        """
        Handle view timeout
        """
        self.clear_items()

async def setup(bot):
    """
    Add the cog to the bot
    """
    await bot.add_cog(SlotChannels(bot))
