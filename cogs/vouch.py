"""
Vouch system implementation for D10 Discord Bot
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
import datetime

from utils.embeds import create_error_embed, create_success_embed, create_vouch_embed
from utils.permissions import is_staff

logger = logging.getLogger("d10-bot")

class Vouch(commands.Cog):
    """
    Vouch system for positive user endorsements
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.vouch_cooldowns = {}  # User ID -> last vouch timestamp
        self.COOLDOWN_SECONDS = 3600  # 1 hour cooldown
        
    @app_commands.command(name="vouch", description="Vouch for another user")
    @app_commands.describe(
        user="The user to vouch for",
        reason="The reason for the vouch"
    )
    async def vouch(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        """
        Vouch for another user
        """
        # Check if user is trying to vouch for themselves
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                embed=create_error_embed("You cannot vouch for yourself."),
                ephemeral=True
            )
            return
            
        # Check if target has the vouch role
        has_vouch_role = False
        vouch_role = interaction.guild.get_role(self.bot.vouch_role_id)
        
        if not vouch_role:
            await interaction.response.send_message(
                embed=create_error_embed("The vouch role has not been configured properly."),
                ephemeral=True
            )
            return
            
        if vouch_role in user.roles:
            has_vouch_role = True
            
        if not has_vouch_role:
            await interaction.response.send_message(
                embed=create_error_embed(f"{user.mention} does not have the required role to receive vouches."),
                ephemeral=True
            )
            return
            
        # Check cooldown
        now = datetime.datetime.now().timestamp()
        
        if interaction.user.id in self.vouch_cooldowns:
            last_vouch = self.vouch_cooldowns[interaction.user.id]
            time_since = now - last_vouch
            
            if time_since < self.COOLDOWN_SECONDS:
                remaining = self.COOLDOWN_SECONDS - time_since
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                
                await interaction.response.send_message(
                    embed=create_error_embed(f"You can vouch again in {minutes}m {seconds}s."),
                    ephemeral=True
                )
                return
                
        # Check if user has already vouched for this person
        existing_vouch = self.bot.db.get_one("vouches", {
            "guild_id": interaction.guild.id,
            "user_id": user.id,
            "voucher_id": interaction.user.id
        })
        
        if existing_vouch:
            await interaction.response.send_message(
                embed=create_error_embed(f"You have already vouched for {user.mention}."),
                ephemeral=True
            )
            return
            
        # Create the vouch
        vouch_id = self.bot.db.insert("vouches", {
            "guild_id": interaction.guild.id,
            "user_id": user.id,
            "voucher_id": interaction.user.id,
            "reason": reason,
            "timestamp": now
        })
        
        # Update cooldown
        self.vouch_cooldowns[interaction.user.id] = now
        
        # Create and send vouch embed
        embed = create_vouch_embed(interaction.user, user, reason)
        
        # Get the vouch channel
        vouch_channel = interaction.guild.get_channel(self.bot.vouch_channel_id)
        
        if vouch_channel:
            await vouch_channel.send(embed=embed)
            
        # Notify user
        await interaction.response.send_message(
            embed=create_success_embed(f"You have successfully vouched for {user.mention}."),
            ephemeral=True
        )
        
        logger.info(f"User {interaction.user} vouched for {user}: {reason}")
        
    @app_commands.command(name="vouches", description="View vouches for a user")
    @app_commands.describe(
        user="The user to view vouches for (defaults to yourself)"
    )
    async def vouches(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """
        View vouches for a user
        """
        # Default to command user if no user specified
        target = user or interaction.user
        
        # Get vouches for the user
        vouches = self.bot.db.get("vouches", {
            "guild_id": interaction.guild.id,
            "user_id": target.id
        })
        
        if not vouches:
            await interaction.response.send_message(
                embed=create_error_embed(f"{target.mention} has no vouches."),
                ephemeral=True
            )
            return
            
        # Create embed
        embed = discord.Embed(
            title=f"Vouches for {target.display_name}",
            description=f"Total vouches: {len(vouches)}",
            color=discord.Color.gold()
        )
        
        # Sort vouches by timestamp (newest first)
        vouches.sort(key=lambda v: v.get("timestamp", 0), reverse=True)
        
        # Add recent vouches (up to 10)
        for i, vouch in enumerate(vouches[:10]):
            voucher_id = vouch.get("voucher_id")
            voucher = interaction.guild.get_member(voucher_id) or f"Unknown User ({voucher_id})"
            
            reason = vouch.get("reason", "No reason provided")
            timestamp = vouch.get("timestamp", 0)
            
            time_str = f"<t:{int(timestamp)}:R>" if timestamp else "Unknown time"
            
            if isinstance(voucher, discord.Member):
                name = f"From {voucher.display_name} {time_str}"
            else:
                name = f"From {voucher} {time_str}"
                
            embed.add_field(
                name=name,
                value=reason,
                inline=False
            )
            
        # Add footer
        if len(vouches) > 10:
            embed.set_footer(text=f"Showing 10 of {len(vouches)} vouches")
            
        # Send response
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="vouchstats", description="View vouch statistics")
    @app_commands.default_permissions(manage_messages=True)
    async def vouch_stats(self, interaction: discord.Interaction):
        """
        View vouch statistics (staff only)
        """
        # Check permissions
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to view vouch statistics."),
                ephemeral=True
            )
            return
            
        # Get all vouches
        all_vouches = self.bot.db.get("vouches", {"guild_id": interaction.guild.id})
        
        if not all_vouches:
            await interaction.response.send_message(
                embed=create_error_embed("There are no vouches in this server."),
                ephemeral=True
            )
            return
            
        # Collect stats
        total_vouches = len(all_vouches)
        
        # Count vouches per user
        user_vouches = {}
        for vouch in all_vouches:
            user_id = vouch.get("user_id")
            if user_id not in user_vouches:
                user_vouches[user_id] = 0
            user_vouches[user_id] += 1
            
        # Find most vouched user
        most_vouched_id = max(user_vouches.items(), key=lambda x: x[1])[0] if user_vouches else None
        most_vouched_count = user_vouches.get(most_vouched_id, 0)
        most_vouched_user = interaction.guild.get_member(most_vouched_id) if most_vouched_id else None
        
        # Count vouches given per user
        vouches_given = {}
        for vouch in all_vouches:
            voucher_id = vouch.get("voucher_id")
            if voucher_id not in vouches_given:
                vouches_given[voucher_id] = 0
            vouches_given[voucher_id] += 1
            
        # Find most active voucher
        most_active_id = max(vouches_given.items(), key=lambda x: x[1])[0] if vouches_given else None
        most_active_count = vouches_given.get(most_active_id, 0)
        most_active_user = interaction.guild.get_member(most_active_id) if most_active_id else None
        
        # Create stats embed
        embed = discord.Embed(
            title="Vouch Statistics",
            description=f"Total vouches: {total_vouches}",
            color=discord.Color.blue()
        )
        
        # Add most vouched user
        if most_vouched_user:
            embed.add_field(
                name="Most Vouched User",
                value=f"{most_vouched_user.mention} ({most_vouched_count} vouches)",
                inline=True
            )
        
        # Add most active voucher
        if most_active_user:
            embed.add_field(
                name="Most Active Voucher",
                value=f"{most_active_user.mention} ({most_active_count} vouches given)",
                inline=True
            )
            
        # Add recent activity
        recent_vouches = sorted(all_vouches, key=lambda v: v.get("timestamp", 0), reverse=True)[:5]
        
        if recent_vouches:
            recent_activity = []
            
            for vouch in recent_vouches:
                user_id = vouch.get("user_id")
                voucher_id = vouch.get("voucher_id")
                timestamp = vouch.get("timestamp", 0)
                
                user = interaction.guild.get_member(user_id) or f"Unknown ({user_id})"
                voucher = interaction.guild.get_member(voucher_id) or f"Unknown ({voucher_id})"
                time_str = f"<t:{int(timestamp)}:R>" if timestamp else "Unknown time"
                
                if isinstance(user, discord.Member) and isinstance(voucher, discord.Member):
                    recent_activity.append(f"{voucher.display_name} → {user.display_name} {time_str}")
                else:
                    recent_activity.append(f"{voucher} → {user} {time_str}")
                    
            embed.add_field(
                name="Recent Vouches",
                value="\n".join(recent_activity) if recent_activity else "No recent vouches",
                inline=False
            )
            
        # Send response
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="deletevouch", description="Delete a vouch")
    @app_commands.describe(
        user="The user who received the vouch",
        voucher="The user who gave the vouch"
    )
    @app_commands.default_permissions(manage_messages=True)
    async def delete_vouch(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        voucher: discord.Member
    ):
        """
        Delete a vouch (staff only)
        """
        # Check permissions
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to delete vouches."),
                ephemeral=True
            )
            return
            
        # Find the vouch
        vouch = self.bot.db.get_one("vouches", {
            "guild_id": interaction.guild.id,
            "user_id": user.id,
            "voucher_id": voucher.id
        })
        
        if not vouch:
            await interaction.response.send_message(
                embed=create_error_embed(f"No vouch found from {voucher.mention} to {user.mention}."),
                ephemeral=True
            )
            return
            
        # Delete the vouch
        self.bot.db.delete("vouches", vouch["id"])
        
        # Notify
        await interaction.response.send_message(
            embed=create_success_embed(f"Vouch from {voucher.mention} to {user.mention} has been deleted."),
            ephemeral=True
        )
        
        logger.info(f"Vouch from {voucher} to {user} deleted by {interaction.user}")

async def setup(bot):
    """
    Add the cog to the bot
    """
    await bot.add_cog(Vouch(bot))
