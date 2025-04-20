"""
Giveaway system implementation for D10 Discord Bot
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
import random
import datetime
from typing import Optional, List

from utils.embeds import create_error_embed, create_success_embed, create_giveaway_embed, create_giveaway_ended_embed
from utils.helpers import parse_time_string, format_timestamp
from utils.permissions import is_staff, has_staff_role

logger = logging.getLogger("d10-bot")

class Giveaway(commands.Cog):
    """
    Giveaway system for running contests
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}  # message_id -> giveaway data
        self.giveaway_tasks = {}  # message_id -> asyncio task
        
    async def cog_load(self):
        """
        Called when the cog is loaded
        """
        # Load active giveaways from database
        await self.load_active_giveaways()
        
        # Start background task
        self.cleanup_task = self.bot.loop.create_task(self.check_ended_giveaways())
        
    async def load_active_giveaways(self):
        """
        Load active giveaways from database and restart tasks
        """
        giveaways = self.bot.db.get("giveaways", {"ended": False})
        
        for giveaway in giveaways:
            # Check if giveaway is still valid
            end_time = giveaway.get("end_time", 0)
            
            if end_time and end_time > datetime.datetime.now().timestamp():
                # Still active, add to tracking
                message_id = giveaway.get("message_id")
                
                if message_id:
                    self.active_giveaways[message_id] = giveaway
                    
                    # Schedule end task
                    self.schedule_giveaway_end(message_id, end_time)
                    
        logger.info(f"Loaded {len(self.active_giveaways)} active giveaways")
        
    def schedule_giveaway_end(self, message_id, end_time):
        """
        Schedule a task to end a giveaway
        """
        now = datetime.datetime.now().timestamp()
        delay = max(0, end_time - now)
        
        task = self.bot.loop.create_task(self.end_giveaway_after_delay(message_id, delay))
        self.giveaway_tasks[message_id] = task
        
    async def end_giveaway_after_delay(self, message_id, delay):
        """
        End a giveaway after a delay
        """
        await asyncio.sleep(delay)
        await self.end_giveaway(message_id)
        
    async def check_ended_giveaways(self):
        """
        Background task to check for ended giveaways
        """
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                now = datetime.datetime.now().timestamp()
                ended_giveaways = []
                
                # Check each active giveaway
                for message_id, giveaway in self.active_giveaways.items():
                    end_time = giveaway.get("end_time", 0)
                    
                    # If end time has passed and no task is running
                    if end_time < now and message_id not in self.giveaway_tasks:
                        ended_giveaways.append(message_id)
                        
                # End any missed giveaways
                for message_id in ended_giveaways:
                    await self.end_giveaway(message_id)
                    
            except Exception as e:
                logger.error(f"Error checking ended giveaways: {e}", exc_info=True)
                
            # Check every minute
            await asyncio.sleep(60)
            
    async def cog_unload(self):
        """
        Called when the cog is unloaded
        """
        # Cancel all running tasks
        if hasattr(self, 'cleanup_task'):
            self.cleanup_task.cancel()
            
        for task in self.giveaway_tasks.values():
            task.cancel()
            
    @app_commands.command(name="giveaway", description="Start or manage giveaways")
    @app_commands.describe(
        action="The action to perform",
        prize="The prize for the giveaway",
        duration="Duration of the giveaway (e.g., 1h, 30m, 1d)",
        winners="Number of winners"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Start", value="start"),
        app_commands.Choice(name="End", value="end"),
        app_commands.Choice(name="Reroll", value="reroll")
    ])
    @app_commands.default_permissions(manage_messages=True)
    async def giveaway(
        self,
        interaction: discord.Interaction,
        action: str,
        prize: Optional[str] = None,
        duration: Optional[str] = None,
        winners: Optional[int] = 1
    ):
        """
        Giveaway management command
        """
        # Check permissions
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to manage giveaways."),
                ephemeral=True
            )
            return
            
        if action == "start":
            if not prize or not duration:
                await interaction.response.send_message(
                    embed=create_error_embed("Prize and duration are required for starting a giveaway."),
                    ephemeral=True
                )
                return
                
            await self.start_giveaway(interaction, prize, duration, winners)
            
        elif action == "end":
            # Show a select menu of active giveaways
            await self.show_giveaway_selector(interaction, "end")
            
        elif action == "reroll":
            # Show a select menu of ended giveaways
            await self.show_giveaway_selector(interaction, "reroll")
            
    async def start_giveaway(self, interaction, prize, duration, winners):
        """
        Start a new giveaway
        """
        # Parse duration
        seconds = parse_time_string(duration)
        if seconds is None:
            await interaction.response.send_message(
                embed=create_error_embed("Invalid duration format. Use e.g., 1h, 30m, 1d."),
                ephemeral=True
            )
            return
            
        # Calculate end time
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        
        # Create giveaway embed
        embed = create_giveaway_embed(prize, end_time, interaction.user, winners)
        
        # Create view with reaction button
        view = GiveawayView()
        
        # Send giveaway message
        await interaction.response.send_message(
            embed=create_success_embed("Creating giveaway..."),
            ephemeral=True
        )
        
        giveaway_message = await interaction.channel.send(embed=embed, view=view)
        
        # Add reaction
        await giveaway_message.add_reaction("🎉")
        
        # Store giveaway data
        giveaway_id = self.bot.db.insert("giveaways", {
            "guild_id": interaction.guild.id,
            "channel_id": interaction.channel.id,
            "message_id": giveaway_message.id,
            "host_id": interaction.user.id,
            "prize": prize,
            "winners_count": winners,
            "end_time": end_time.timestamp(),
            "created_at": datetime.datetime.now().timestamp(),
            "ended": False
        })
        
        # Add to active giveaways
        giveaway_data = self.bot.db.get_one("giveaways", {"id": giveaway_id})
        self.active_giveaways[giveaway_message.id] = giveaway_data
        
        # Schedule end task
        self.schedule_giveaway_end(giveaway_message.id, end_time.timestamp())
        
        # Notify success
        await interaction.edit_original_response(
            embed=create_success_embed(f"Giveaway created! It will end {format_timestamp(end_time, 'R')}")
        )
        
        logger.info(f"Giveaway created by {interaction.user} for {prize}, ending in {seconds} seconds")
        
    async def show_giveaway_selector(self, interaction, action_type):
        """
        Show a select menu of giveaways for ending or rerolling
        """
        # Get giveaways based on action type
        if action_type == "end":
            giveaways = self.bot.db.get("giveaways", {
                "guild_id": interaction.guild.id,
                "ended": False
            })
        else:  # reroll
            giveaways = self.bot.db.get("giveaways", {
                "guild_id": interaction.guild.id,
                "ended": True
            })
            
        if not giveaways:
            status = "active" if action_type == "end" else "ended"
            await interaction.response.send_message(
                embed=create_error_embed(f"No {status} giveaways found."),
                ephemeral=True
            )
            return
            
        # Create select menu options
        options = []
        
        for giveaway in giveaways[:25]:  # Discord limit of 25 options
            prize = giveaway.get("prize", "Unknown prize")
            message_id = giveaway.get("message_id")
            
            if len(prize) > 90:
                prize = prize[:87] + "..."
                
            options.append(
                discord.SelectOption(
                    label=f"{prize}",
                    value=str(message_id),
                    description=f"Message ID: {message_id}"
                )
            )
            
        # Create and send select menu
        await interaction.response.send_message(
            f"Select a giveaway to {action_type}:",
            view=GiveawaySelectView(self, options, action_type),
            ephemeral=True
        )
        
    async def end_giveaway(self, message_id):
        """
        End a giveaway
        """
        # Get giveaway data
        giveaway = self.active_giveaways.get(int(message_id))
        
        if not giveaway:
            logger.error(f"Tried to end non-existent giveaway: {message_id}")
            return
            
        try:
            # Remove from active giveaways
            if int(message_id) in self.active_giveaways:
                del self.active_giveaways[int(message_id)]
                
            # Cancel task if exists
            if int(message_id) in self.giveaway_tasks:
                self.giveaway_tasks[int(message_id)].cancel()
                del self.giveaway_tasks[int(message_id)]
                
            # Get message
            channel_id = giveaway.get("channel_id")
            guild_id = giveaway.get("guild_id")
            
            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.error(f"Guild not found for giveaway: {message_id}")
                return
                
            channel = guild.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel not found for giveaway: {message_id}")
                return
                
            try:
                message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                logger.error(f"Message not found for giveaway: {message_id}")
                return
                
            # Get reactions
            reaction = None
            for r in message.reactions:
                if str(r.emoji) == "🎉":
                    reaction = r
                    break
                    
            if not reaction:
                logger.error(f"No reaction found for giveaway: {message_id}")
                winners = []
            else:
                # Get users who reacted
                users = []
                async for user in reaction.users():
                    if not user.bot:
                        users.append(user)
                        
                # Pick winners
                winners_count = giveaway.get("winners_count", 1)
                winners = []
                
                if users:
                    # Pick random winners up to winners_count or user count
                    for _ in range(min(winners_count, len(users))):
                        if not users:
                            break
                            
                        winner = random.choice(users)
                        winners.append(winner)
                        users.remove(winner)
                        
            # Update embed
            prize = giveaway.get("prize", "Unknown prize")
            host_id = giveaway.get("host_id")
            host = guild.get_member(host_id) or await self.bot.fetch_user(host_id)
            
            # Create ended embed
            embed = create_giveaway_ended_embed(prize, host, winners)
            
            # Update message
            await message.edit(embed=embed, view=None)
            
            # Send winner announcement
            if winners:
                winners_mention = " ".join([winner.mention for winner in winners])
                await channel.send(
                    f"🎉 Congratulations {winners_mention}! You won the giveaway for **{prize}**!"
                )
            else:
                await channel.send(
                    f"No one entered the giveaway for **{prize}**!"
                )
                
            # Update database
            winner_ids = [winner.id for winner in winners]
            self.bot.db.update("giveaways", giveaway["id"], {
                **giveaway,
                "ended": True,
                "ended_at": datetime.datetime.now().timestamp(),
                "winner_ids": winner_ids
            })
            
            logger.info(f"Giveaway {message_id} ended with {len(winners)} winners")
            
        except Exception as e:
            logger.error(f"Error ending giveaway {message_id}: {e}", exc_info=True)
            
    async def reroll_giveaway(self, message_id):
        """
        Reroll a giveaway to pick new winners
        """
        # Get giveaway data
        giveaway = self.bot.db.get_one("giveaways", {
            "message_id": int(message_id),
            "ended": True
        })
        
        if not giveaway:
            logger.error(f"Tried to reroll non-existent giveaway: {message_id}")
            return None
            
        try:
            # Get message
            channel_id = giveaway.get("channel_id")
            guild_id = giveaway.get("guild_id")
            
            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.error(f"Guild not found for giveaway: {message_id}")
                return None
                
            channel = guild.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel not found for giveaway: {message_id}")
                return None
                
            try:
                message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                logger.error(f"Message not found for giveaway: {message_id}")
                return None
                
            # Get reactions
            reaction = None
            for r in message.reactions:
                if str(r.emoji) == "🎉":
                    reaction = r
                    break
                    
            if not reaction:
                logger.error(f"No reaction found for giveaway: {message_id}")
                return None
                
            # Get users who reacted
            users = []
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)
                    
            # Pick a new winner
            if not users:
                return None
                
            new_winner = random.choice(users)
            
            # Update database with new winner
            winner_ids = giveaway.get("winner_ids", [])
            winner_ids.append(new_winner.id)
            
            self.bot.db.update("giveaways", giveaway["id"], {
                **giveaway,
                "winner_ids": winner_ids,
                "rerolled_at": datetime.datetime.now().timestamp()
            })
            
            logger.info(f"Giveaway {message_id} rerolled with new winner: {new_winner}")
            
            return new_winner
            
        except Exception as e:
            logger.error(f"Error rerolling giveaway {message_id}: {e}", exc_info=True)
            return None

class GiveawayView(discord.ui.View):
    """
    View for giveaway message
    """
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Enter Giveaway", style=discord.ButtonStyle.green, emoji="🎉", custom_id="giveaway_enter")
    async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Enter the giveaway
        """
        # Add reaction to the message
        await interaction.message.add_reaction("🎉")
        
        # Notify user
        await interaction.response.send_message(
            "You've entered the giveaway!",
            ephemeral=True
        )

class GiveawaySelectView(discord.ui.View):
    """
    View for giveaway selection
    """
    def __init__(self, cog, options, action_type):
        super().__init__(timeout=60)
        self.cog = cog
        self.action_type = action_type
        
        # Add select menu
        self.add_item(GiveawaySelect(options, action_type))
        
    async def on_timeout(self):
        """
        Handle timeout
        """
        self.clear_items()

class GiveawaySelect(discord.ui.Select):
    """
    Select menu for choosing a giveaway
    """
    def __init__(self, options, action_type):
        super().__init__(
            placeholder=f"Select a giveaway to {action_type}...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.action_type = action_type
        
    async def callback(self, interaction: discord.Interaction):
        """
        Handle selection
        """
        message_id = self.values[0]
        
        if self.action_type == "end":
            # Confirm ending
            await interaction.response.send_message(
                "Are you sure you want to end this giveaway now?",
                view=GiveawayConfirmView(self.view.cog, message_id, "end"),
                ephemeral=True
            )
        else:  # reroll
            # Confirm rerolling
            await interaction.response.send_message(
                "Are you sure you want to reroll this giveaway?",
                view=GiveawayConfirmView(self.view.cog, message_id, "reroll"),
                ephemeral=True
            )

class GiveawayConfirmView(discord.ui.View):
    """
    View for confirming giveaway actions
    """
    def __init__(self, cog, message_id, action_type):
        super().__init__(timeout=60)
        self.cog = cog
        self.message_id = message_id
        self.action_type = action_type
        
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Confirm the action
        """
        self.clear_items()
        await interaction.response.edit_message(
            content=f"{self.action_type.capitalize()}ing giveaway...",
            view=self,
            embed=None
        )
        
        if self.action_type == "end":
            # End the giveaway
            await self.cog.end_giveaway(self.message_id)
            
            # Notify
            await interaction.edit_original_response(
                content=f"Giveaway ended successfully."
            )
            
        else:  # reroll
            # Reroll the giveaway
            new_winner = await self.cog.reroll_giveaway(self.message_id)
            
            if new_winner:
                # Notify
                await interaction.edit_original_response(
                    content=f"Giveaway rerolled successfully. New winner: {new_winner.mention}"
                )
                
                # Also announce in the channel
                giveaway = self.cog.bot.db.get_one("giveaways", {"message_id": int(self.message_id)})
                if giveaway:
                    channel_id = giveaway.get("channel_id")
                    channel = interaction.guild.get_channel(channel_id)
                    
                    if channel:
                        prize = giveaway.get("prize", "the giveaway")
                        await channel.send(
                            f"🎉 Giveaway rerolled! New winner: {new_winner.mention} won **{prize}**!"
                        )
            else:
                # Notify error
                await interaction.edit_original_response(
                    content=f"Failed to reroll giveaway. No valid entries found."
                )
                
    @discord.ui.button(label="No", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Cancel the action
        """
        await interaction.response.edit_message(
            content=f"Action cancelled.",
            view=None,
            embed=None
        )
        
    async def on_timeout(self):
        """
        Handle timeout
        """
        self.clear_items()

async def setup(bot):
    """
    Add the cog to the bot
    """
    await bot.add_cog(Giveaway(bot))
