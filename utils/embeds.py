"""
Embed utilities for D10 Discord Bot
"""

import discord
import datetime
from typing import Optional, List, Dict, Any, Union
from .helpers import format_timestamp

def create_basic_embed(
    title: str, 
    description: Optional[str] = None,
    color: Optional[discord.Color] = None
) -> discord.Embed:
    """
    Create a basic embed with title and description
    """
    if color is None:
        color = discord.Color.blurple()
        
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now()
    )
    
    return embed

def create_error_embed(
    description: str,
    title: str = "Error"
) -> discord.Embed:
    """
    Create an error embed
    """
    return create_basic_embed(
        title=title,
        description=description,
        color=discord.Color.red()
    )

def create_success_embed(
    description: str,
    title: str = "Success"
) -> discord.Embed:
    """
    Create a success embed
    """
    return create_basic_embed(
        title=title,
        description=description,
        color=discord.Color.green()
    )

def create_info_embed(
    description: str,
    title: str = "Information"
) -> discord.Embed:
    """
    Create an information embed
    """
    return create_basic_embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )

def create_ticket_embed(
    image_url: str = "https://imgur.com/HuSzeAX"
) -> discord.Embed:
    """
    Create the ticket system embed
    """
    embed = create_basic_embed(
        title="This is D10 ticket system",
        description="Press \"Create ticket\" to open a new ticket.",
        color=discord.Color.blurple()
    )
    
    embed.set_image(url=image_url)
    embed.set_footer(text="D10 Ticket System")
    
    return embed

def create_welcome_embed(
    member: discord.Member
) -> discord.Embed:
    """
    Create a welcome embed for a new member
    """
    embed = create_basic_embed(
        title=f"Welcome to the server, {member.name}!",
        description="Thanks for joining! Make sure to check out discord.gg/d10",
        color=discord.Color.green()
    )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Member #{member.guild.member_count}")
    
    return embed

def create_slot_embed(
    user: discord.Member,
    duration_days: int,
    everyone_pings: int,
    here_pings: int,
    category: str
) -> discord.Embed:
    """
    Create an embed for a new slot channel
    """
    embed = create_basic_embed(
        title=f"Slot Channel Created",
        description=f"A new slot channel has been created for {user.mention}.",
        color=discord.Color.blue()
    )
    
    expiry_date = datetime.datetime.now() + datetime.timedelta(days=duration_days)
    
    embed.add_field(name="Duration", value=f"{duration_days} days", inline=True)
    embed.add_field(name="Expires", value=format_timestamp(expiry_date), inline=True)
    embed.add_field(name="Category", value=category, inline=True)
    embed.add_field(name="@everyone Pings", value=f"{everyone_pings} remaining", inline=True)
    embed.add_field(name="@here Pings", value=f"{here_pings} remaining", inline=True)
    
    embed.set_footer(text=f"User ID: {user.id}")
    
    return embed

def create_slot_ping_embed(
    user: discord.Member,
    ping_type: str,
    remaining: int
) -> discord.Embed:
    """
    Create an embed for a slot ping notification
    """
    embed = create_basic_embed(
        title="Ping Used",
        description=f"{user.mention} has used a {ping_type} ping.",
        color=discord.Color.orange()
    )
    
    embed.add_field(name="Remaining", value=f"{remaining} {ping_type} pings", inline=True)
    
    return embed

def create_vouch_embed(
    voucher: discord.Member,
    target: discord.Member,
    reason: str
) -> discord.Embed:
    """
    Create a vouch embed
    """
    embed = create_basic_embed(
        title="New Vouch",
        description=f"{voucher.mention} has vouched for {target.mention}",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"Vouch ID: {voucher.id}-{target.id}")
    embed.timestamp = datetime.datetime.now()
    
    return embed

def create_giveaway_embed(
    prize: str,
    end_time: datetime.datetime,
    host: discord.Member,
    winners: int = 1
) -> discord.Embed:
    """
    Create a giveaway embed
    """
    embed = create_basic_embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}",
        color=discord.Color.brand_green()
    )
    
    embed.add_field(name="Host", value=host.mention, inline=True)
    embed.add_field(name="Winners", value=str(winners), inline=True)
    embed.add_field(name="Ends", value=format_timestamp(end_time), inline=True)
    embed.set_footer(text="React with 🎉 to enter!")
    
    return embed

def create_giveaway_ended_embed(
    prize: str,
    host: discord.Member,
    winners: List[discord.Member]
) -> discord.Embed:
    """
    Create a giveaway ended embed
    """
    if not winners:
        description = f"**Prize:** {prize}\n\n**Winners:** No valid participants"
    else:
        winners_text = ", ".join([winner.mention for winner in winners])
        description = f"**Prize:** {prize}\n\n**Winners:** {winners_text}"
    
    embed = create_basic_embed(
        title="🎉 GIVEAWAY ENDED 🎉",
        description=description,
        color=discord.Color.brand_green()
    )
    
    embed.add_field(name="Host", value=host.mention, inline=True)
    embed.set_footer(text="Giveaway has ended")
    
    return embed

def create_ticket_info_embed(
    ticket_type: str,
    creator: discord.Member,
    answers: Dict[str, str]
) -> discord.Embed:
    """
    Create an embed with ticket information
    """
    embed = create_basic_embed(
        title=f"Ticket Information - {ticket_type}",
        description=f"Ticket created by {creator.mention}",
        color=discord.Color.blue()
    )
    
    # Add each question and answer as a field
    for question, answer in answers.items():
        embed.add_field(name=question, value=answer, inline=False)
        
    embed.set_footer(text=f"Ticket ID: {creator.id}")
    embed.timestamp = datetime.datetime.now()
    
    return embed

def create_report_embed(
    reporter: discord.Member,
    target: discord.Member,
    reason: str,
    is_report: bool = True
) -> discord.Embed:
    """
    Create a report or praise embed
    """
    title = "User Report" if is_report else "User Praise"
    color = discord.Color.red() if is_report else discord.Color.green()
    
    embed = create_basic_embed(
        title=title,
        description=f"**{'Reporter' if is_report else 'From'}:** {reporter.mention}\n**{'Reported User' if is_report else 'To'}:** {target.mention}",
        color=color
    )
    
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"ID: {reporter.id}-{target.id}")
    embed.timestamp = datetime.datetime.now()
    
    return embed
