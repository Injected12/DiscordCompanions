"""
Status tracking implementation for D10 Discord Bot
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import datetime
import asyncio
from typing import Dict, Set

from utils.helpers import contains_d10_link
from utils.embeds import create_basic_embed, create_error_embed, create_success_embed
from utils.permissions import is_staff

logger = logging.getLogger("d10-bot")

class StatusTracker(commands.Cog):
    """
    Track user statuses containing '.gg/d10' and assign roles
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.tracked_users = {}  # Store user IDs with tracking data
        self.status_role_id = bot.status_role_id
        
    async def cog_load(self):
        """
        Called when the cog is loaded
        """
        # Start background task
        self.status_check_task = self.bot.loop.create_task(self.check_statuses())
        
    async def cog_unload(self):
        """
        Called when the cog is unloaded
        """
        # Cancel background task
        if hasattr(self, 'status_check_task'):
            self.status_check_task.cancel()
            
    async def check_statuses(self):
        """
        Background task to check user statuses
        """
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                # Process each guild
                for guild in self.bot.guilds:
                    # Get status role
                    if not self.status_role_id:
                        continue
                        
                    status_role = guild.get_role(self.status_role_id)
                    if not status_role:
                        continue
                        
                    # Check members with the role
                    members_with_role = set(status_role.members)
                    members_should_have = set()
                    
                    # Check all members
                    for member in guild.members:
                        # Skip bots
                        if member.bot:
                            continue
                            
                        # Check custom status and activities
                        has_d10_status = False
                        
                        # Check custom status
                        if member.activities:
                            for activity in member.activities:
                                if isinstance(activity, discord.CustomActivity) and activity.state:
                                    if contains_d10_link(activity.state):
                                        has_d10_status = True
                                        break
                        
                        # Update tracking
                        if has_d10_status:
                            members_should_have.add(member)
                            # Add to tracking if not already there
                            if member.id not in self.tracked_users:
                                self.tracked_users[member.id] = {
                                    "since": datetime.datetime.now(),
                                    "had_role": member in members_with_role
                                }
                        elif member.id in self.tracked_users:
                            # Remove from tracking
                            del self.tracked_users[member.id]
                    
                    # Add role to members who should have it
                    for member in members_should_have:
                        if member not in members_with_role:
                            try:
                                await member.add_roles(status_role, reason="D10 status detected")
                                logger.info(f"Added status role to {member} (ID: {member.id})")
                            except Exception as e:
                                logger.error(f"Error adding status role to {member}: {e}")
                    
                    # Remove role from members who shouldn't have it
                    for member in members_with_role:
                        if member not in members_should_have:
                            try:
                                await member.remove_roles(status_role, reason="D10 status no longer detected")
                                logger.info(f"Removed status role from {member} (ID: {member.id})")
                            except Exception as e:
                                logger.error(f"Error removing status role from {member}: {e}")
                
            except Exception as e:
                logger.error(f"Error in status tracker: {e}", exc_info=True)
            
            # Wait before next check
            await asyncio.sleep(60)  # Check every minute
            
    @app_commands.command(name="statusstats", description="Show statistics about users with D10 status")
    @app_commands.default_permissions(administrator=True)
    async def status_stats(self, interaction: discord.Interaction):
        """
        Show statistics about users with D10 status
        """
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to use this command."),
                ephemeral=True
            )
            return
        
        guild = interaction.guild
        status_role = guild.get_role(self.status_role_id)
        
        if not status_role:
            await interaction.response.send_message(
                embed=create_error_embed("Status role not found."),
                ephemeral=True
            )
            return
        
        # Get statistics
        users_with_role = len(status_role.members)
        tracked_users = sum(1 for user_id in self.tracked_users if guild.get_member(user_id))
        
        # Create embed
        embed = create_basic_embed(
            title="D10 Status Statistics",
            description=f"Statistics for users with discord.gg/d10 in their status",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Users with Status Role", value=str(users_with_role), inline=True)
        embed.add_field(name="Currently Tracked Users", value=str(tracked_users), inline=True)
        
        now = datetime.datetime.now()
        longest_duration = max(
            ((now - data["since"]).total_seconds() for data in self.tracked_users.values()),
            default=0
        )
        
        if longest_duration > 0:
            days = int(longest_duration // 86400)
            hours = int((longest_duration % 86400) // 3600)
            minutes = int((longest_duration % 3600) // 60)
            
            duration_str = f"{days}d {hours}h {minutes}m"
            embed.add_field(name="Longest Status Duration", value=duration_str, inline=True)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    """
    Add the cog to the bot
    """
    await bot.add_cog(StatusTracker(bot))
