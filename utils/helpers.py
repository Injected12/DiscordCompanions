"""
Helper functions for D10 Discord Bot
"""

import datetime
import asyncio
import discord
from typing import Optional, Union, List, Dict, Any, Tuple
import os
import re

def format_timestamp(timestamp: Optional[datetime.datetime] = None, style: str = 'f') -> str:
    """
    Format a timestamp for display in Discord
    
    Styles:
    - t: Short Time (e.g., 9:41 PM)
    - T: Long Time (e.g., 9:41:30 PM)
    - d: Short Date (e.g., 06/09/2021)
    - D: Long Date (e.g., June 9, 2021)
    - f: Short Date/Time (e.g., June 9, 2021 9:41 PM)
    - F: Long Date/Time (e.g., Wednesday, June 9, 2021 9:41 PM)
    - R: Relative Time (e.g., 2 months ago)
    """
    if timestamp is None:
        timestamp = datetime.datetime.now()
        
    # Convert to UTC timestamp
    unix_timestamp = int(timestamp.timestamp())
    return f"<t:{unix_timestamp}:{style}>"
    
def get_clean_mention(user_id: Union[int, str]) -> str:
    """
    Get a clean user mention string from user ID
    """
    return f"<@{user_id}>"
    
async def create_timeout_task(timeout: int, callback, *args, **kwargs) -> asyncio.Task:
    """
    Create a timeout task that will execute after specified seconds
    """
    await asyncio.sleep(timeout)
    return await callback(*args, **kwargs)
    
def parse_time_string(time_string: str) -> Optional[int]:
    """
    Parse a time string like "1d", "2h", "30m", "45s" into seconds
    """
    time_regex = re.compile(r"^(\d+)([dhms])$")
    match = time_regex.match(time_string.lower())
    
    if not match:
        return None
        
    amount, unit = match.groups()
    amount = int(amount)
    
    if unit == 'd':
        return amount * 86400  # Days to seconds
    elif unit == 'h':
        return amount * 3600   # Hours to seconds
    elif unit == 'm':
        return amount * 60     # Minutes to seconds
    elif unit == 's':
        return amount          # Seconds
    return None
    
def format_duration(seconds: int) -> str:
    """
    Format seconds into a human-readable duration string
    """
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        
    if not parts:
        return "0 seconds"
        
    return ", ".join(parts)
    
async def safe_send(destination, content=None, **kwargs) -> Optional[discord.Message]:
    """
    Safely send a message, handling common exceptions
    """
    try:
        return await destination.send(content, **kwargs)
    except discord.Forbidden:
        # Don't have permission to send
        return None
    except discord.HTTPException as e:
        # HTTP error occurred
        print(f"Error sending message: {e}")
        return None
        
def contains_d10_link(text: str) -> bool:
    """
    Check if a text contains the d10 invite link
    """
    if not text:
        return False
        
    patterns = [
        r'\.gg/d10',
        r'discord\.gg/d10',
        r'discord\.com/invite/d10'
    ]
    
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
            
    return False
