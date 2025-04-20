"""
D10 Discord Bot - Main entry point for Linux environments
"""

import os
import sys
import logging
import asyncio
import signal
from dotenv import load_dotenv
from bot import D10Bot

# Setup signal handlers for graceful shutdown
def signal_handler(sig, frame):
    print("Received shutdown signal, exiting gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Load environment variables from .env file
load_dotenv()

# Configure logging with proper Linux paths
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "bot.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("d10-bot")

# Verify environment variables
required_env_vars = [
    "DISCORD_TOKEN",
    "DISCORD_SERVER_ID",
    "DISCORD_STAFF_ROLE_ID"
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    logger.error("Please set these variables in your .env file and try again")
    sys.exit(1)

# Main entry point
async def main():
    # Get the token from environment variables
    token = os.getenv("DISCORD_TOKEN")
    
    # Create the bot instance
    bot = D10Bot()
    
    try:
        logger.info("Starting Discord bot...")
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        # Ensure we close the bot properly
        if not bot.is_closed():
            await bot.close()
            logger.info("Bot connection closed")

if __name__ == "__main__":
    # On Windows asyncio creates a ProactorEventLoop by default
    # On Linux it's usually the SelectorEventLoop
    # This ensures consistent behavior across platforms
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)