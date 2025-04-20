"""
Report and praise system implementation for D10 Discord Bot
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
from typing import Dict, List, Optional, Literal

from utils.embeds import create_error_embed, create_success_embed, create_report_embed
from utils.permissions import is_staff

logger = logging.getLogger("d10-bot")

class Reports(commands.Cog):
    """
    Report and praise system for user feedback
    """
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="report", description="Report a user for breaking rules")
    @app_commands.describe(
        user="The user to report",
        reason="The reason for the report"
    )
    async def report(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        """
        Report a user for rule violations
        """
        # Prevent self-reports
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                embed=create_error_embed("You cannot report yourself."),
                ephemeral=True
            )
            return
            
        # Prevent reporting bots
        if user.bot:
            await interaction.response.send_message(
                embed=create_error_embed("You cannot report bots."),
                ephemeral=True
            )
            return
            
        # Prevent reporting staff members
        if is_staff(interaction._cog_state_to_dict(user)):
            await interaction.response.send_message(
                embed=create_error_embed("You cannot report staff members."),
                ephemeral=True
            )
            return
            
        # Submit the report
        report_id = self.bot.db.insert("reports", {
            "guild_id": interaction.guild.id,
            "user_id": user.id,
            "reporter_id": interaction.user.id,
            "reason": reason,
            "type": "report",
            "timestamp": asyncio.get_event_loop().time(),
            "status": "pending"
        })
        
        # Notify user
        await interaction.response.send_message(
            embed=create_success_embed(f"Your report has been submitted. Thank you for helping keep the server safe."),
            ephemeral=True
        )
        
        # Notify staff
        await self.notify_staff(interaction.guild, interaction.user, user, reason, True)
        
        logger.info(f"User {user} reported by {interaction.user}: {reason}")
        
    @app_commands.command(name="praise", description="Praise a user for positive behavior")
    @app_commands.describe(
        user="The user to praise",
        reason="The reason for the praise"
    )
    async def praise(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        """
        Praise a user for positive behavior
        """
        # Prevent self-praise
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                embed=create_error_embed("You cannot praise yourself."),
                ephemeral=True
            )
            return
            
        # Prevent praising bots
        if user.bot:
            await interaction.response.send_message(
                embed=create_error_embed("You cannot praise bots."),
                ephemeral=True
            )
            return
            
        # Submit the praise
        praise_id = self.bot.db.insert("reports", {
            "guild_id": interaction.guild.id,
            "user_id": user.id,
            "reporter_id": interaction.user.id,
            "reason": reason,
            "type": "praise",
            "timestamp": asyncio.get_event_loop().time(),
            "status": "approved"  # Auto-approve praises
        })
        
        # Notify user
        await interaction.response.send_message(
            embed=create_success_embed(f"Your praise for {user.mention} has been submitted."),
            ephemeral=True
        )
        
        # Notify staff
        await self.notify_staff(interaction.guild, interaction.user, user, reason, False)
        
        logger.info(f"User {user} praised by {interaction.user}: {reason}")
        
    @app_commands.command(name="status", description="Check a user's report history")
    @app_commands.describe(
        user="The user to check"
    )
    async def status(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """
        Check a user's report history
        """
        # Default to self if no user specified
        target_user = user or interaction.user
        
        # Staff can check anyone, regular users can only check themselves
        if target_user.id != interaction.user.id and not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You can only check your own report history."),
                ephemeral=True
            )
            return
            
        # Get reports and praises
        reports = self.bot.db.get("reports", {
            "guild_id": interaction.guild.id,
            "user_id": target_user.id,
            "type": "report",
            "status": "approved"
        })
        
        praises = self.bot.db.get("reports", {
            "guild_id": interaction.guild.id,
            "user_id": target_user.id,
            "type": "praise"
        })
        
        # Create status embed
        embed = discord.Embed(
            title=f"Status for {target_user}",
            description=f"Report/praise history for {target_user.mention}",
            color=discord.Color.blue()
        )
        
        # Add report count
        embed.add_field(
            name="Reports",
            value=f"{len(reports)} approved report(s)",
            inline=True
        )
        
        # Add praise count
        embed.add_field(
            name="Praises",
            value=f"{len(praises)} praise(s)",
            inline=True
        )
        
        # Show ratio
        total = len(reports) + len(praises)
        if total > 0:
            praise_percent = (len(praises) / total) * 100
            embed.add_field(
                name="Praise Ratio",
                value=f"{praise_percent:.1f}% positive",
                inline=True
            )
            
        # Add recent activity (staff only)
        if is_staff(interaction):
            recent_activity = []
            
            # Combine and sort by timestamp
            all_items = reports + praises
            all_items.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            
            # Add most recent 5
            for i, item in enumerate(all_items[:5]):
                item_type = "Report" if item.get("type") == "report" else "Praise"
                timestamp = item.get("timestamp", 0)
                time_str = f"<t:{int(timestamp)}:R>" if timestamp else "Unknown time"
                
                reporter_id = item.get("reporter_id")
                reporter_name = "Unknown"
                if reporter_id:
                    reporter = interaction.guild.get_member(reporter_id)
                    if reporter:
                        reporter_name = reporter.display_name
                        
                reason = item.get("reason", "No reason provided")
                reason = reason[:50] + "..." if len(reason) > 50 else reason
                
                recent_activity.append(f"{i+1}. {item_type} {time_str} by {reporter_name}: {reason}")
                
            if recent_activity:
                embed.add_field(
                    name="Recent Activity",
                    value="\n".join(recent_activity),
                    inline=False
                )
            
        # Send the status
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        
    @app_commands.command(name="reviewreport", description="Review a pending report")
    @app_commands.describe(
        report_id="The ID of the report to review",
        action="Approve or reject the report"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Approve", value="approve"),
        app_commands.Choice(name="Reject", value="reject")
    ])
    @app_commands.default_permissions(kick_members=True)
    async def review_report(
        self,
        interaction: discord.Interaction,
        report_id: str,
        action: str
    ):
        """
        Review a pending report (staff only)
        """
        # Check permissions
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to review reports."),
                ephemeral=True
            )
            return
            
        # Get the report
        report = self.bot.db.get_one("reports", {"id": report_id})
        
        if not report:
            await interaction.response.send_message(
                embed=create_error_embed("Report not found."),
                ephemeral=True
            )
            return
            
        # Check if already reviewed
        if report.get("status") != "pending":
            await interaction.response.send_message(
                embed=create_error_embed(f"This report has already been {report.get('status')}."),
                ephemeral=True
            )
            return
            
        # Update report status
        new_status = "approved" if action == "approve" else "rejected"
        self.bot.db.update("reports", report_id, {
            **report,
            "status": new_status,
            "reviewed_by": interaction.user.id,
            "reviewed_at": asyncio.get_event_loop().time()
        })
        
        # Notify staff
        await interaction.response.send_message(
            embed=create_success_embed(f"Report {report_id} has been {new_status}."),
            ephemeral=True
        )
        
        logger.info(f"Report {report_id} {new_status} by {interaction.user}")
        
    async def notify_staff(
        self,
        guild: discord.Guild,
        reporter: discord.Member,
        target: discord.Member,
        reason: str,
        is_report: bool
    ):
        """
        Notify staff about a report or praise
        """
        # Find staff channel
        log_channel_id = self.bot.db.get_one("config", {"key": "log_channel"})
        
        if log_channel_id:
            channel_id = log_channel_id.get("value")
            channel = guild.get_channel(channel_id)
            
            if channel:
                # Create embed
                embed = create_report_embed(reporter, target, reason, is_report)
                
                # Add action buttons for reports
                view = None
                if is_report:
                    view = ReportActionView(self.bot)
                    
                # Send notification
                await channel.send(embed=embed, view=view)
                return
                
        # If no channel found, try to DM staff members
        if hasattr(self.bot, 'staff_role_id'):
            staff_role = guild.get_role(self.bot.staff_role_id)
            if staff_role:
                # Get online staff members
                online_staff = [
                    member for member in staff_role.members 
                    if member.status != discord.Status.offline and not member.bot
                ]
                
                if online_staff:
                    # Pick the first online staff member to notify
                    staff_member = online_staff[0]
                    
                    # Create embed
                    embed = create_report_embed(reporter, target, reason, is_report)
                    
                    # Send DM
                    try:
                        await staff_member.send(
                            f"New {'report' if is_report else 'praise'} in {guild.name}:",
                            embed=embed
                        )
                    except:
                        # Couldn't DM, but that's okay
                        pass

class ReportActionView(discord.ui.View):
    """
    View with action buttons for reports
    """
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        
    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, custom_id="report_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Approve the report
        """
        # Check permissions
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to approve reports."),
                ephemeral=True
            )
            return
            
        # Extract report ID from message
        try:
            embed = interaction.message.embeds[0]
            footer_text = embed.footer.text
            report_id = footer_text.split("ID: ")[1].split("-")[0]
            
            # Get report
            report = self.bot.db.get_one("reports", {"id": report_id})
            
            if not report:
                await interaction.response.send_message(
                    embed=create_error_embed("Report not found."),
                    ephemeral=True
                )
                return
                
            # Update report
            self.bot.db.update("reports", report_id, {
                **report,
                "status": "approved",
                "reviewed_by": interaction.user.id,
                "reviewed_at": asyncio.get_event_loop().time()
            })
            
            # Notify
            await interaction.response.send_message(
                embed=create_success_embed("Report approved."),
                ephemeral=True
            )
            
            # Update original message
            new_embed = embed.copy()
            new_embed.color = discord.Color.green()
            new_embed.add_field(
                name="Status",
                value=f"Approved by {interaction.user.mention}",
                inline=False
            )
            
            await interaction.message.edit(embed=new_embed, view=None)
            
            logger.info(f"Report {report_id} approved by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error approving report: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
            
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red, custom_id="report_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Reject the report
        """
        # Check permissions
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to reject reports."),
                ephemeral=True
            )
            return
            
        # Extract report ID from message
        try:
            embed = interaction.message.embeds[0]
            footer_text = embed.footer.text
            report_id = footer_text.split("ID: ")[1].split("-")[0]
            
            # Get report
            report = self.bot.db.get_one("reports", {"id": report_id})
            
            if not report:
                await interaction.response.send_message(
                    embed=create_error_embed("Report not found."),
                    ephemeral=True
                )
                return
                
            # Update report
            self.bot.db.update("reports", report_id, {
                **report,
                "status": "rejected",
                "reviewed_by": interaction.user.id,
                "reviewed_at": asyncio.get_event_loop().time()
            })
            
            # Notify
            await interaction.response.send_message(
                embed=create_success_embed("Report rejected."),
                ephemeral=True
            )
            
            # Update original message
            new_embed = embed.copy()
            new_embed.color = discord.Color.dark_red()
            new_embed.add_field(
                name="Status",
                value=f"Rejected by {interaction.user.mention}",
                inline=False
            )
            
            await interaction.message.edit(embed=new_embed, view=None)
            
            logger.info(f"Report {report_id} rejected by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error rejecting report: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
            
    @discord.ui.button(label="Warn User", style=discord.ButtonStyle.blurple, custom_id="report_warn")
    async def warn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Warn the reported user
        """
        # Check permissions
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to warn users."),
                ephemeral=True
            )
            return
            
        # Extract report information
        try:
            embed = interaction.message.embeds[0]
            footer_text = embed.footer.text
            report_id = footer_text.split("ID: ")[1].split("-")[0]
            
            # Get report data
            report = self.bot.db.get_one("reports", {"id": report_id})
            
            if not report:
                await interaction.response.send_message(
                    embed=create_error_embed("Report not found."),
                    ephemeral=True
                )
                return
                
            # Get user
            user_id = report.get("user_id")
            user = interaction.guild.get_member(user_id)
            
            if not user:
                await interaction.response.send_message(
                    embed=create_error_embed("User not found."),
                    ephemeral=True
                )
                return
                
            # Prepare warning modal
            await interaction.response.send_modal(WarnUserModal(self.bot, user, report))
            
        except Exception as e:
            logger.error(f"Error preparing warn modal: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )

class WarnUserModal(discord.ui.Modal):
    """
    Modal for sending a warning to a user
    """
    def __init__(self, bot, user, report):
        super().__init__(title=f"Warn {user.display_name}")
        self.bot = bot
        self.user = user
        self.report = report
        
        reason = report.get("reason", "")
        
        self.warning = discord.ui.TextInput(
            label="Warning Message",
            style=discord.TextStyle.paragraph,
            placeholder="Enter the warning message to send to the user...",
            default=f"You have been warned regarding: {reason}",
            required=True
        )
        
        self.add_item(self.warning)
        
    async def on_submit(self, interaction: discord.Interaction):
        """
        Handle modal submission
        """
        # Send warning to user
        try:
            warning_text = self.warning.value
            
            # Create warning embed
            embed = discord.Embed(
                title=f"Warning from {interaction.guild.name}",
                description=warning_text,
                color=discord.Color.orange()
            )
            
            embed.set_footer(text=f"Warned by {interaction.user}")
            
            # Send DM
            try:
                await self.user.send(embed=embed)
                dm_sent = True
            except:
                dm_sent = False
                
            # Update report
            self.bot.db.update("reports", self.report["id"], {
                **self.report,
                "status": "warned",
                "reviewed_by": interaction.user.id,
                "reviewed_at": asyncio.get_event_loop().time(),
                "warning_text": warning_text
            })
            
            # Log warning
            self.bot.db.insert("moderation", {
                "guild_id": interaction.guild.id,
                "user_id": self.user.id,
                "moderator_id": interaction.user.id,
                "action": "warn",
                "reason": warning_text,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            # Notify staff
            dm_status = "sent" if dm_sent else "could not be sent"
            await interaction.response.send_message(
                embed=create_success_embed(
                    f"Warning to {self.user.mention} {dm_status}."
                ),
                ephemeral=True
            )
            
            # Update original message
            message = interaction.message
            if message:
                embed = message.embeds[0].copy()
                embed.color = discord.Color.orange()
                embed.add_field(
                    name="Status",
                    value=f"User warned by {interaction.user.mention}",
                    inline=False
                )
                
                await message.edit(embed=embed, view=None)
                
            logger.info(f"User {self.user} warned by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error sending warning: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
            
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """
        Handle modal errors
        """
        logger.error(f"Error in warning modal: {error}", exc_info=True)
        await interaction.response.send_message(
            embed=create_error_embed(f"An error occurred: {str(error)}"),
            ephemeral=True
        )

async def setup(bot):
    """
    Add the cog to the bot
    """
    await bot.add_cog(Reports(bot))
