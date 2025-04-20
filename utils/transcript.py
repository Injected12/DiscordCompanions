"""
Transcript generation utilities for D10 Discord Bot
"""

import discord
import datetime
import io
import logging
from typing import List, Optional, Dict, Any, Union

logger = logging.getLogger("d10-bot")

async def generate_text_transcript(
    channel: discord.TextChannel,
    limit: int = 1000
) -> io.BytesIO:
    """
    Generate a text transcript of a channel
    
    Args:
        channel: The channel to generate a transcript from
        limit: Maximum number of messages to include
        
    Returns:
        A BytesIO object containing the transcript
    """
    logger.info(f"Generating transcript for channel {channel.name} ({channel.id})")
    
    transcript = io.BytesIO()
    
    # Write header
    header = f"# Transcript for {channel.name} (ID: {channel.id})\n"
    header += f"Generated at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
    header += f"Guild: {channel.guild.name} (ID: {channel.guild.id})\n\n"
    transcript.write(header.encode('utf-8'))
    
    try:
        # Get messages
        messages = []
        async for message in channel.history(limit=limit, oldest_first=True):
            messages.append(message)
            
        if not messages:
            transcript.write(b"No messages found in this channel.\n")
        else:
            # Write messages
            for message in messages:
                created_at = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                author = f"{message.author} (ID: {message.author.id})"
                content = message.content or "[No content]"
                
                # Handle attachments
                attachments = ""
                if message.attachments:
                    attachments = "\nAttachments:\n"
                    for attachment in message.attachments:
                        attachments += f"- {attachment.url}\n"
                        
                # Handle embeds
                embeds = ""
                if message.embeds:
                    embeds = "\nEmbeds:\n"
                    for embed in message.embeds:
                        embeds += f"- Title: {embed.title}\n"
                        if embed.description:
                            embeds += f"  Description: {embed.description}\n"
                            
                msg_text = f"[{created_at}] {author}: {content}{attachments}{embeds}\n\n"
                transcript.write(msg_text.encode('utf-8'))
                
    except discord.Forbidden:
        transcript.write(b"Error: Bot doesn't have permission to read message history.\n")
    except discord.HTTPException as e:
        transcript.write(f"Error: Failed to fetch messages: {str(e)}\n".encode('utf-8'))
    except Exception as e:
        logger.error(f"Error generating transcript: {e}", exc_info=True)
        transcript.write(f"Error generating transcript: {str(e)}\n".encode('utf-8'))
        
    # Reset position to beginning of file
    transcript.seek(0)
    return transcript

async def generate_ticket_data(
    channel: discord.TextChannel,
    user_id: int,
    ticket_type: str,
    answers: Dict[str, str]
) -> Dict[str, Any]:
    """
    Generate ticket data for restoration
    
    Args:
        channel: The ticket channel
        user_id: The user ID who created the ticket
        ticket_type: The type of ticket
        answers: The answers to the ticket questions
        
    Returns:
        A dictionary containing the ticket data
    """
    return {
        "user_id": user_id,
        "ticket_type": ticket_type,
        "answers": answers,
        "channel_id": channel.id,
        "channel_name": channel.name,
        "created_at": datetime.datetime.now().timestamp(),
        "category_id": channel.category.id if channel.category else None
    }

async def generate_slot_data(
    channel: discord.TextChannel,
    user_id: int,
    duration_days: int,
    everyone_pings: int,
    everyone_pings_used: int,
    here_pings: int,
    here_pings_used: int,
    category_id: int
) -> Dict[str, Any]:
    """
    Generate slot data for restoration
    
    Args:
        channel: The slot channel
        user_id: The user ID who owns the slot
        duration_days: The duration in days
        everyone_pings: The total everyone pings
        everyone_pings_used: The used everyone pings
        here_pings: The total here pings
        here_pings_used: The used here pings
        category_id: The category ID
        
    Returns:
        A dictionary containing the slot data
    """
    return {
        "user_id": user_id,
        "channel_id": channel.id,
        "channel_name": channel.name,
        "duration_days": duration_days,
        "everyone_pings": everyone_pings,
        "everyone_pings_used": everyone_pings_used,
        "here_pings": here_pings,
        "here_pings_used": here_pings_used,
        "category_id": category_id,
        "created_at": datetime.datetime.now().timestamp(),
        "expires_at": (datetime.datetime.now() + datetime.timedelta(days=duration_days)).timestamp()
    }

async def send_transcript_dm(
    user: discord.User,
    channel: discord.TextChannel,
    data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Send a transcript to a user via DM
    
    Args:
        user: The user to send the transcript to
        channel: The channel to generate a transcript from
        data: Optional additional data to include
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate transcript
        transcript_file = await generate_text_transcript(channel)
        
        # Create data file if provided
        data_file = None
        if data:
            import json
            data_json = json.dumps(data, indent=2)
            data_file = io.BytesIO(data_json.encode('utf-8'))
            data_file.seek(0)
        
        # Create message content
        content = f"Here's the transcript for {channel.name} from {channel.guild.name}."
        if data:
            content += "\nThis transcript includes restoration data that can be used with the appropriate commands."
            
        # Send files
        files = [discord.File(transcript_file, filename=f"transcript-{channel.name}.txt")]
        if data_file:
            files.append(discord.File(data_file, filename=f"data-{channel.name}.json"))
            
        await user.send(content=content, files=files)
        return True
        
    except discord.Forbidden:
        logger.warning(f"Cannot send DM to user {user.id}")
        return False
    except Exception as e:
        logger.error(f"Error sending transcript DM: {e}", exc_info=True)
        return False
