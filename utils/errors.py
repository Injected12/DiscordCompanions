"""
Custom error classes for D10 Discord Bot
"""

from discord.ext import commands

class D10Error(commands.CommandError):
    """Base exception class for D10 bot errors"""
    pass

class TicketError(D10Error):
    """Exception raised for errors in the ticket system"""
    pass

class TicketAlreadyExists(TicketError):
    """Exception raised when a user already has an open ticket"""
    pass

class TicketNotFound(TicketError):
    """Exception raised when a ticket is not found"""
    pass

class SlotChannelError(D10Error):
    """Exception raised for errors in the slot channel system"""
    pass

class SlotLimitReached(SlotChannelError):
    """Exception raised when a user has reached their slot limit"""
    pass

class SlotChannelNotFound(SlotChannelError):
    """Exception raised when a slot channel is not found"""
    pass

class PingLimitReached(SlotChannelError):
    """Exception raised when a user has reached their ping limit for a slot"""
    pass

class VoiceChannelError(D10Error):
    """Exception raised for errors in the voice channel system"""
    pass

class SetupError(D10Error):
    """Exception raised for errors during feature setup"""
    pass

class MissingPermissions(D10Error):
    """Exception raised when a user is missing permissions"""
    pass

class ConfigError(D10Error):
    """Exception raised for errors in the configuration"""
    pass

class DatabaseError(D10Error):
    """Exception raised for errors in the database operations"""
    pass

class UserError(D10Error):
    """Exception raised for user-related errors"""
    pass

class InvalidTimeFormat(D10Error):
    """Exception raised when an invalid time format is provided"""
    pass

class InvalidArgument(D10Error):
    """Exception raised when an invalid argument is provided"""
    pass
