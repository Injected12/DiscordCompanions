"""
D10 Discord Bot - Main entry point
"""

import os
import logging
import asyncio
from bot import D10Bot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("d10-bot")

# Main entry point
if __name__ == "__main__":
    # Get the token from environment variables
    token = os.getenv("DISCORD_TOKEN")
    
    if not token:
        logger.error("DISCORD_TOKEN environment variable not set")
        exit(1)
    
    # Create and run bot
    bot = D10Bot()
    
    try:
        asyncio.run(bot.start(token))
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)