"""
Permission utilities for D10 Discord Bot
"""

import discord
from discord.ext import commands
from typing import Optional, Union, List, Callable, Awaitable
import logging

logger = logging.getLogger("d10-bot")

def is_admin() -> Callable[[commands.Context], bool]:
    """
    Check if the user is an administrator
    """
    async def predicate(ctx: commands.Context) -> bool:
        if not ctx.guild:
            return False
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

def is_staff(ctx_or_interaction: Union[commands.Context, discord.Interaction]) -> bool:
    """
    Check if the user has the staff role
    """
    user = ctx_or_interaction.author if isinstance(ctx_or_interaction, commands.Context) else ctx_or_interaction.user
    guild = ctx_or_interaction.guild
    
    if not guild:
        return False
        
    # Get the staff role ID from the bot instance
    bot = ctx_or_interaction.bot
    staff_role_id = getattr(bot, 'staff_role_id', None)
    
    if not staff_role_id:
        # Fall back to checking admin permissions
        return user.guild_permissions.administrator
        
    # Check if the user has the staff role
    user_roles = [role.id for role in user.roles]
    return staff_role_id in user_roles or user.guild_permissions.administrator

def has_staff_role() -> Callable[[commands.Context], bool]:
    """
    Check decorator for staff role
    """
    async def predicate(ctx: commands.Context) -> bool:
        return is_staff(ctx)
    return commands.check(predicate)

async def check_hierarchy(
    guild: discord.Guild, 
    user: discord.Member, 
    target: discord.Member
) -> bool:
    """
    Check if the user is higher in the role hierarchy than the target
    """
    return (
        user.top_role > target.top_role and 
        guild.owner_id != target.id and
        user.id != target.id
    )

def can_manage_channel(
    channel: discord.abc.GuildChannel, 
    user: discord.Member
) -> bool:
    """
    Check if the user can manage the given channel
    """
    return (
        user.guild_permissions.administrator or
        channel.permissions_for(user).manage_channels
    )

def can_manage_roles(
    guild: discord.Guild, 
    user: discord.Member, 
    role: discord.Role
) -> bool:
    """
    Check if the user can manage the given role
    """
    return (
        user.guild_permissions.administrator or
        (user.guild_permissions.manage_roles and user.top_role > role)
    )

def can_kick_members(
    guild: discord.Guild,
    user: discord.Member,
    target: discord.Member
) -> bool:
    """
    Check if the user can kick the target member
    """
    return (
        user.guild_permissions.kick_members and
        user.top_role > target.top_role and
        guild.owner_id != target.id
    )

def can_ban_members(
    guild: discord.Guild,
    user: discord.Member,
    target: discord.Member
) -> bool:
    """
    Check if the user can ban the target member
    """
    return (
        user.guild_permissions.ban_members and
        user.top_role > target.top_role and
        guild.owner_id != target.id
    )

def can_manage_messages(
    channel: discord.abc.GuildChannel,
    user: discord.Member
) -> bool:
    """
    Check if the user can manage messages in the given channel
    """
    return (
        user.guild_permissions.administrator or
        channel.permissions_for(user).manage_messages
    )

def get_required_permissions(command_name: str) -> List[str]:
    """
    Get the required permissions for a command
    """
    command_permissions = {
        "ban": ["ban_members"],
        "kick": ["kick_members"],
        "mute": ["manage_roles"],
        "unmute": ["manage_roles"],
        "clear": ["manage_messages"],
        "lockdown": ["manage_channels"],
        "unlock": ["manage_channels"],
        "setupticket": ["administrator"],
        "setupwelcome": ["administrator"],
        "giverole": ["manage_roles"],
        "setupvc": ["administrator"],
        "createslot": ["manage_channels"],
        "clearserver": ["administrator"],
        "antiraid": ["administrator"]
    }
    
    return command_permissions.get(command_name, [])
