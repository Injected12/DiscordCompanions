"""
Ticket system implementation for D10 Discord Bot
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
import datetime

from utils.embeds import create_ticket_embed, create_ticket_info_embed, create_error_embed, create_success_embed
from utils.permissions import is_staff, has_staff_role
from utils.transcript import generate_text_transcript, send_transcript_dm
from utils.errors import TicketError, TicketAlreadyExists, TicketNotFound

logger = logging.getLogger("d10-bot")

# Ticket types and their questions
TICKET_TYPES = {
    "Partnership Ticket": ["Invite Link (250+ members)"],
    "Support": ["Subject", "Description"],
    "Purchase": ["Product", "Payment Method"],
    "Staff Application": [
        "Have you ever been staff on a similar server?", 
        "Why do you want to be staff?", 
        "Do you agree to status/or bio with .gg/d10?"
    ],
    "Leaker Application": [
        "Preview of what you will leak", 
        "How do you leak?"
    ]
}

class TicketView(discord.ui.View):
    """
    View for ticket creation
    """
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        
    @discord.ui.button(label="Create ticket", style=discord.ButtonStyle.green, custom_id="ticket_create_button")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Handle ticket creation button press
        """
        # Check if user already has an open ticket
        user_tickets = self.bot.db.get("tickets", {"user_id": interaction.user.id, "status": "open"})
        if user_tickets:
            await interaction.response.send_message(
                embed=create_error_embed("You already have an open ticket."),
                ephemeral=True
            )
            return
            
        # Show ticket type selection
        await interaction.response.send_message(
            "Please select a ticket type:",
            view=TicketTypeSelect(self.bot),
            ephemeral=True
        )

class TicketTypeSelect(discord.ui.View):
    """
    View for selecting ticket type
    """
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        
        # Add ticket type dropdown
        self.add_item(TicketTypeDropdown())
        
    async def on_timeout(self):
        """
        Handle view timeout
        """
        # View timed out, nothing to do
        pass

class TicketTypeDropdown(discord.ui.Select):
    """
    Dropdown for selecting ticket type
    """
    def __init__(self):
        options = [
            discord.SelectOption(label=ticket_type, value=ticket_type)
            for ticket_type in TICKET_TYPES.keys()
        ]
        
        super().__init__(
            placeholder="Select ticket type...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_type_dropdown"
        )
        
    async def callback(self, interaction: discord.Interaction):
        """
        Handle ticket type selection
        """
        ticket_type = self.values[0]
        questions = TICKET_TYPES[ticket_type]
        
        # Start the modal with questions
        modal = TicketModal(ticket_type, questions)
        await interaction.response.send_modal(modal)

class TicketModal(discord.ui.Modal):
    """
    Modal for ticket information
    """
    def __init__(self, ticket_type: str, questions: List[str]):
        super().__init__(title=f"{ticket_type} Ticket", timeout=600)
        self.ticket_type = ticket_type
        self.questions = questions
        
        # Add text inputs for each question
        self.inputs = []
        for i, question in enumerate(questions):
            style = discord.TextStyle.paragraph if i == len(questions) - 1 else discord.TextStyle.short
            text_input = discord.ui.TextInput(
                label=question,
                style=style,
                required=True,
                max_length=1000
            )
            self.add_item(text_input)
            self.inputs.append(text_input)
        
    async def on_submit(self, interaction: discord.Interaction):
        """
        Handle ticket modal submission
        """
        # Get answers
        answers = {
            self.questions[i]: input_field.value
            for i, input_field in enumerate(self.inputs)
        }
        
        try:
            # Create the ticket
            await self.create_ticket(interaction, answers)
        except Exception as e:
            logger.error(f"Error creating ticket: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred while creating the ticket: {str(e)}"),
                ephemeral=True
            )
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """
        Handle modal errors
        """
        logger.error(f"Error in ticket modal: {error}", exc_info=True)
        await interaction.response.send_message(
            embed=create_error_embed(f"An error occurred: {str(error)}"),
            ephemeral=True
        )
    
    async def create_ticket(self, interaction: discord.Interaction, answers: Dict[str, str]):
        """
        Create a ticket channel and handle setup
        """
        guild = interaction.guild
        user = interaction.user
        
        # Get ticket category
        ticket_settings = interaction.client.db.get_one("ticket_settings", {"guild_id": guild.id})
        category_id = ticket_settings.get("category_id") if ticket_settings else None
        
        category = None
        if category_id:
            category = guild.get_channel(category_id)
        
        # Generate channel name
        channel_name = f"ticket-{user.name.lower()}-{self.ticket_type.lower().replace(' ', '-')}"
        channel_name = channel_name[:100]  # Discord channel name length limit
        
        # Create permissions for the ticket channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
                read_message_history=True
            )
        }
        
        # Add staff role permissions
        if hasattr(interaction.client, 'staff_role_id'):
            staff_role = guild.get_role(interaction.client.staff_role_id)
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True,
                    read_message_history=True,
                    manage_messages=True
                )
        
        # Create the channel
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Ticket created by {user}"
        )
        
        # Store ticket info in database
        ticket_id = interaction.client.db.insert("tickets", {
            "guild_id": guild.id,
            "channel_id": channel.id,
            "user_id": user.id,
            "ticket_type": self.ticket_type,
            "answers": answers,
            "status": "open",
            "created_at": datetime.datetime.now().timestamp(),
            "staff_id": None
        })
        
        # Send initial message in ticket channel
        embed = create_ticket_info_embed(self.ticket_type, user, answers)
        
        # Add buttons for ticket management
        view = TicketManagementView(interaction.client)
        await channel.send(
            f"{user.mention} Your ticket has been created.",
            embed=embed,
            view=view
        )
        
        # Notify user
        await interaction.response.send_message(
            embed=create_success_embed(f"Your ticket has been created: {channel.mention}"),
            ephemeral=True
        )
        
        logger.info(f"Ticket created: {channel.name} (ID: {channel.id}) by {user} for {self.ticket_type}")

class TicketManagementView(discord.ui.View):
    """
    View for ticket management buttons
    """
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        
    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, custom_id="ticket_close_button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Close the ticket
        """
        # Check if user is staff or ticket creator
        ticket = self.bot.db.get_one("tickets", {"channel_id": interaction.channel.id, "status": "open"})
        if not ticket:
            await interaction.response.send_message(
                embed=create_error_embed("This channel is not an active ticket."),
                ephemeral=True
            )
            return
            
        is_ticket_creator = ticket["user_id"] == interaction.user.id
        if not (is_staff(interaction) or is_ticket_creator):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to close this ticket."),
                ephemeral=True
            )
            return
            
        # Confirm closure
        await interaction.response.send_message(
            "Are you sure you want to close this ticket?",
            view=TicketCloseConfirmView(self.bot, ticket),
            ephemeral=True
        )

class TicketCloseConfirmView(discord.ui.View):
    """
    View for confirming ticket closure
    """
    def __init__(self, bot, ticket):
        super().__init__(timeout=60)
        self.bot = bot
        self.ticket = ticket
        
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Confirm ticket closure
        """
        self.clear_items()
        await interaction.response.edit_message(
            content="Closing ticket...",
            view=self,
            embed=None
        )
        
        # Get channel and user
        channel = interaction.channel
        guild = interaction.guild
        user_id = self.ticket["user_id"]
        user = guild.get_member(user_id) or await self.bot.fetch_user(user_id)
        
        # Generate transcript
        try:
            if user:
                await send_transcript_dm(user, channel)
        except Exception as e:
            logger.error(f"Error sending transcript: {e}", exc_info=True)
            
        # Update ticket status
        self.bot.db.update("tickets", self.ticket["id"], {
            **self.ticket,
            "status": "closed",
            "closed_at": datetime.datetime.now().timestamp(),
            "closed_by": interaction.user.id
        })
        
        # Send closure message and schedule deletion
        await channel.send(
            embed=create_success_embed(f"This ticket has been closed by {interaction.user.mention}. Channel will be deleted in 10 seconds.")
        )
        
        # Wait and delete channel
        await asyncio.sleep(10)
        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user}")
        except Exception as e:
            logger.error(f"Error deleting ticket channel: {e}", exc_info=True)
        
    @discord.ui.button(label="No", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Cancel ticket closure
        """
        await interaction.response.edit_message(
            content="Ticket closure cancelled.",
            view=None,
            embed=None
        )
        
    async def on_timeout(self):
        """
        Handle view timeout
        """
        # View timed out, just disable buttons
        self.clear_items()

class Tickets(commands.Cog):
    """
    Ticket system cog
    """
    
    def __init__(self, bot):
        self.bot = bot
        
    async def cog_load(self):
        """
        Called when the cog is loaded
        """
        # Register persistent view
        self.bot.add_view(TicketView(self.bot))
        self.bot.add_view(TicketManagementView(self.bot))
        
    @app_commands.command(name="setupticket", description="Set up the ticket system in a channel")
    @app_commands.describe(channel="The channel to set up the ticket system in")
    @app_commands.default_permissions(administrator=True)
    async def setup_ticket(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        """
        Set up the ticket system in a channel
        """
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to use this command."),
                ephemeral=True
            )
            return
            
        # Use current channel if none specified
        channel = channel or interaction.channel
        
        # Check if setup already exists
        existing_setup = self.bot.db.get_one("ticket_settings", {"guild_id": interaction.guild.id})
        
        # Get ticket category or create one if it doesn't exist
        category = None
        category_id = None
        
        if existing_setup and existing_setup.get("category_id"):
            category_id = existing_setup["category_id"]
            category = interaction.guild.get_channel(category_id)
            
        if not category:
            try:
                # Create new category
                category = await interaction.guild.create_category(
                    name="Tickets",
                    reason="Ticket system setup"
                )
                category_id = category.id
            except discord.Forbidden:
                await interaction.response.send_message(
                    embed=create_error_embed("I don't have permission to create categories."),
                    ephemeral=True
                )
                return
                
        # Save settings to database
        if existing_setup:
            self.bot.db.update("ticket_settings", existing_setup["id"], {
                "guild_id": interaction.guild.id,
                "channel_id": channel.id,
                "category_id": category_id,
                "updated_at": datetime.datetime.now().timestamp(),
                "updated_by": interaction.user.id
            })
        else:
            self.bot.db.insert("ticket_settings", {
                "guild_id": interaction.guild.id,
                "channel_id": channel.id,
                "category_id": category_id,
                "created_at": datetime.datetime.now().timestamp(),
                "created_by": interaction.user.id
            })
            
        # Create embed and view
        image_url = "https://imgur.com/HuSzeAX"
        embed = create_ticket_embed(image_url)
        view = TicketView(self.bot)
        
        # Send the embed
        await channel.send(
            embed=embed,
            content="Press \"Create ticket\"",
            view=view
        )
        
        # Notify setup complete
        await interaction.response.send_message(
            embed=create_success_embed(f"Ticket system has been set up in {channel.mention}"),
            ephemeral=True
        )
        
        logger.info(f"Ticket system set up in {channel.name} (ID: {channel.id}) by {interaction.user}")
        
    @app_commands.command(name="closeticket", description="Close the current ticket")
    async def close_ticket(self, interaction: discord.Interaction):
        """
        Close the current ticket
        """
        # Check if channel is a ticket
        ticket = self.bot.db.get_one("tickets", {"channel_id": interaction.channel.id, "status": "open"})
        if not ticket:
            await interaction.response.send_message(
                embed=create_error_embed("This channel is not an active ticket."),
                ephemeral=True
            )
            return
            
        # Check if user is staff or ticket creator
        is_ticket_creator = ticket["user_id"] == interaction.user.id
        if not (is_staff(interaction) or is_ticket_creator):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to close this ticket."),
                ephemeral=True
            )
            return
            
        # Confirm closure
        await interaction.response.send_message(
            "Are you sure you want to close this ticket?",
            view=TicketCloseConfirmView(self.bot, ticket),
            ephemeral=True
        )
        
    @app_commands.command(name="closealltickets", description="Close all open tickets")
    @app_commands.default_permissions(administrator=True)
    async def close_all_tickets(self, interaction: discord.Interaction):
        """
        Close all open tickets
        """
        if not is_staff(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to use this command."),
                ephemeral=True
            )
            return
            
        # Get all open tickets for this guild
        open_tickets = self.bot.db.get("tickets", {"guild_id": interaction.guild.id, "status": "open"})
        
        if not open_tickets:
            await interaction.response.send_message(
                embed=create_error_embed("There are no open tickets."),
                ephemeral=True
            )
            return
            
        # Confirm closure of all tickets
        await interaction.response.send_message(
            f"Are you sure you want to close all {len(open_tickets)} open tickets?",
            view=CloseAllTicketsConfirmView(self.bot, open_tickets),
            ephemeral=True
        )
        
class CloseAllTicketsConfirmView(discord.ui.View):
    """
    View for confirming closing all tickets
    """
    def __init__(self, bot, tickets):
        super().__init__(timeout=60)
        self.bot = bot
        self.tickets = tickets
        
    @discord.ui.button(label="Yes", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Confirm closing all tickets
        """
        self.clear_items()
        await interaction.response.edit_message(
            content=f"Closing {len(self.tickets)} tickets...",
            view=self,
            embed=None
        )
        
        # Track results
        closed_count = 0
        failed_count = 0
        
        # Close each ticket
        for ticket in self.tickets:
            try:
                # Get channel
                channel_id = ticket["channel_id"]
                channel = interaction.guild.get_channel(channel_id)
                
                if not channel:
                    continue
                    
                # Generate transcript
                user_id = ticket["user_id"]
                user = interaction.guild.get_member(user_id) or await self.bot.fetch_user(user_id)
                
                if user:
                    try:
                        await send_transcript_dm(user, channel)
                    except Exception as e:
                        logger.error(f"Error sending transcript: {e}", exc_info=True)
                        
                # Update ticket status
                self.bot.db.update("tickets", ticket["id"], {
                    **ticket,
                    "status": "closed",
                    "closed_at": datetime.datetime.now().timestamp(),
                    "closed_by": interaction.user.id
                })
                
                # Send closure message
                await channel.send(
                    embed=create_success_embed(f"This ticket has been closed by {interaction.user.mention} as part of a mass ticket closure. Channel will be deleted in 5 seconds.")
                )
                
                # Wait a bit and delete
                await asyncio.sleep(5)
                await channel.delete(reason=f"Mass ticket closure by {interaction.user}")
                
                closed_count += 1
                
            except Exception as e:
                logger.error(f"Error closing ticket {ticket.get('id')}: {e}", exc_info=True)
                failed_count += 1
                
        # Send results
        await interaction.edit_original_response(
            content=f"Closed {closed_count} tickets. {failed_count} failed.",
            view=None
        )
        
        logger.info(f"Mass ticket closure by {interaction.user}: {closed_count} closed, {failed_count} failed")
        
    @discord.ui.button(label="No", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Cancel closing all tickets
        """
        await interaction.response.edit_message(
            content="Mass ticket closure cancelled.",
            view=None,
            embed=None
        )
        
    async def on_timeout(self):
        """
        Handle view timeout
        """
        # View timed out, just disable buttons
        self.clear_items()

async def setup(bot):
    """
    Add the cog to the bot
    """
    await bot.add_cog(Tickets(bot))
