"""
Role management implementation for D10 Discord Bot
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging

from utils.permissions import is_staff, can_manage_roles
from utils.embeds import create_error_embed, create_success_embed

logger = logging.getLogger("d10-bot")

class RoleManagement(commands.Cog):
    """
    Role management commands
    """
    
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="giverole", description="Give a role to a user")
    @app_commands.describe(
        user="The user to give the role to",
        role="The role to give to the user"
    )
    @app_commands.default_permissions(manage_roles=True)
    async def give_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        """
        Give a role to a user
        """
        # Check if command user has permission
        if not is_staff(interaction) and not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to manage roles."),
                ephemeral=True
            )
            return
            
        # Check bot hierarchy
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                embed=create_error_embed("I can't assign a role that is higher than or equal to my highest role."),
                ephemeral=True
            )
            return
            
        # Check user hierarchy
        if not can_manage_roles(interaction.guild, interaction.user, role):
            await interaction.response.send_message(
                embed=create_error_embed("You can't assign a role that is higher than or equal to your highest role."),
                ephemeral=True
            )
            return
            
        # Check if user already has the role
        if role in user.roles:
            await interaction.response.send_message(
                embed=create_error_embed(f"{user.mention} already has the {role.name} role."),
                ephemeral=True
            )
            return
            
        # Give the role
        try:
            await user.add_roles(role, reason=f"Role given by {interaction.user}")
            
            # Send success message
            await interaction.response.send_message(
                embed=create_success_embed(f"Gave {role.mention} to {user.mention}."),
                ephemeral=True
            )
            
            logger.info(f"{interaction.user} gave {role.name} to {user}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("I don't have permission to manage roles."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
            
    @app_commands.command(name="removerole", description="Remove a role from a user")
    @app_commands.describe(
        user="The user to remove the role from",
        role="The role to remove from the user"
    )
    @app_commands.default_permissions(manage_roles=True)
    async def remove_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        """
        Remove a role from a user
        """
        # Check if command user has permission
        if not is_staff(interaction) and not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                embed=create_error_embed("You don't have permission to manage roles."),
                ephemeral=True
            )
            return
            
        # Check bot hierarchy
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                embed=create_error_embed("I can't remove a role that is higher than or equal to my highest role."),
                ephemeral=True
            )
            return
            
        # Check user hierarchy
        if not can_manage_roles(interaction.guild, interaction.user, role):
            await interaction.response.send_message(
                embed=create_error_embed("You can't remove a role that is higher than or equal to your highest role."),
                ephemeral=True
            )
            return
            
        # Check if user has the role
        if role not in user.roles:
            await interaction.response.send_message(
                embed=create_error_embed(f"{user.mention} doesn't have the {role.name} role."),
                ephemeral=True
            )
            return
            
        # Remove the role
        try:
            await user.remove_roles(role, reason=f"Role removed by {interaction.user}")
            
            # Send success message
            await interaction.response.send_message(
                embed=create_success_embed(f"Removed {role.mention} from {user.mention}."),
                ephemeral=True
            )
            
            logger.info(f"{interaction.user} removed {role.name} from {user}")
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("I don't have permission to manage roles."),
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"An error occurred: {str(e)}"),
                ephemeral=True
            )
            
    @app_commands.command(name="roles", description="List all roles in the server")
    async def list_roles(self, interaction: discord.Interaction):
        """
        List all roles in the server
        """
        # Get all roles and sort them by position (highest first)
        roles = sorted(interaction.guild.roles, key=lambda r: r.position, reverse=True)
        
        # Create a formatted list of roles
        role_chunks = []
        current_chunk = []
        current_length = 0
        
        for role in roles:
            if role.name == "@everyone":
                continue
                
            role_line = f"{role.mention} - {len(role.members)} members"
            line_length = len(role_line)
            
            # Check if adding this line would exceed the maximum embed description length
            if current_length + line_length > 2000:
                role_chunks.append("\n".join(current_chunk))
                current_chunk = [role_line]
                current_length = line_length
            else:
                current_chunk.append(role_line)
                current_length += line_length
                
        if current_chunk:
            role_chunks.append("\n".join(current_chunk))
            
        # Send the role list
        if not role_chunks:
            await interaction.response.send_message(
                embed=create_error_embed("No roles to display."),
                ephemeral=True
            )
            return
            
        # Create and send embeds
        embeds = []
        for i, chunk in enumerate(role_chunks):
            embed = discord.Embed(
                title=f"Server Roles ({i+1}/{len(role_chunks)})",
                description=chunk,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Total roles: {len(roles) - 1}")
            embeds.append(embed)
            
        await interaction.response.send_message(embeds=embeds[:10], ephemeral=True)  # Discord allows max 10 embeds

async def setup(bot):
    """
    Add the cog to the bot
    """
    await bot.add_cog(RoleManagement(bot))
