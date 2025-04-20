@echo off
echo Starting D10 Discord bot...
echo.

REM Check if Python is installed
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.8 or higher.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b
)

REM Check Python version (need 3.8+)
python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" > nul 2>&1
if %errorlevel% neq 0 (
    echo Your Python version is too old. Please install Python 3.8 or higher.
    pause
    exit /b
)

echo Checking and installing required packages...
python -m pip install -U discord.py python-dotenv asyncio aiohttp

REM Create a .env file if it doesn't exist
if not exist .env (
    echo Creating .env file with required environment variables...
    echo DISCORD_TOKEN=MTM2MzMxNDY3MDU4MDE0MjI4MQ.GgkHat.w5RwFvuEf4afj7R-urz-porynWe8Nligs9VVmc> .env
    echo DISCORD_SERVER_ID=1358090413340102686>> .env
    echo DISCORD_STAFF_ROLE_ID=1363277490008621337>> .env
    echo DISCORD_STATUS_ROLE_ID=1363311828142264492>> .env
    echo DISCORD_VOUCH_ROLE_ID=1363277493443756256>> .env
    echo DISCORD_VOUCH_CHANNEL_ID=1363277606874779809>> .env
)

echo.
echo Starting the bot...
echo (Press Ctrl+C to stop the bot)
echo.

REM Create/update the bot_memory.py file if it doesn't exist
if not exist memory_database.py (
    echo Creating memory_database.py for in-memory storage...
    copy /y NUL memory_database.py > NUL
    echo import uuid > memory_database.py
    echo import logging >> memory_database.py
    echo import datetime >> memory_database.py
    echo import copy >> memory_database.py
    echo from typing import Dict, List, Any, Optional >> memory_database.py
    echo. >> memory_database.py
    echo # Set up logging >> memory_database.py
    echo logger = logging.getLogger('d10-bot'^) >> memory_database.py
    echo. >> memory_database.py
    echo class MemoryDatabase: >> memory_database.py
    echo     """In-memory database manager for D10 Discord Bot""" >> memory_database.py
    echo     def __init__(self^): >> memory_database.py
    echo         """Initialize the in-memory database""" >> memory_database.py
    echo         self.collections = { >> memory_database.py
    echo             'tickets': [], >> memory_database.py
    echo             'welcome': [], >> memory_database.py
    echo             'status': [], >> memory_database.py
    echo             'roles': [], >> memory_database.py
    echo             'voice_channels': [], >> memory_database.py
    echo             'temp_voice_channels': [], >> memory_database.py
    echo             'reports': [], >> memory_database.py
    echo             'giveaways': [], >> memory_database.py
    echo             'vouches': [], >> memory_database.py
    echo             'slot_channels': [] >> memory_database.py
    echo         } >> memory_database.py
    echo         logger.info("In-memory database initialized"^) >> memory_database.py
    echo. >> memory_database.py
    echo     def _setup_database(self^) -^> None: >> memory_database.py
    echo         """No setup needed for in-memory database""" >> memory_database.py
    echo         pass >> memory_database.py
    echo. >> memory_database.py
    echo     def get(self, collection: str, filter_dict: Optional[Dict[str, Any]] = None^) -^> List[Dict[str, Any]]: >> memory_database.py
    echo         """Get items from a collection with optional filtering""" >> memory_database.py
    echo         try: >> memory_database.py
    echo             if collection not in self.collections: >> memory_database.py
    echo                 self.collections[collection] = [] >> memory_database.py
    echo. >> memory_database.py
    echo             # Return all items if no filter >> memory_database.py
    echo             if not filter_dict: >> memory_database.py
    echo                 return copy.deepcopy(self.collections.get(collection, []^)^) >> memory_database.py
    echo. >> memory_database.py
    echo             # Filter the items >> memory_database.py
    echo             results = [] >> memory_database.py
    echo             for item in self.collections.get(collection, []^): >> memory_database.py
    echo                 match = True >> memory_database.py
    echo                 for key, value in filter_dict.items(^): >> memory_database.py
    echo                     if key not in item or item[key] != value: >> memory_database.py
    echo                         match = False >> memory_database.py
    echo                         break >> memory_database.py
    echo                 if match: >> memory_database.py
    echo                     results.append(copy.deepcopy(item^)^) >> memory_database.py
    echo. >> memory_database.py
    echo             return results >> memory_database.py
    echo. >> memory_database.py
    echo         except Exception as e: >> memory_database.py
    echo             logger.error(f"In-memory database get error ({collection}^): {e}", exc_info=True^) >> memory_database.py
    echo             return [] >> memory_database.py
)

if not exist bot_memory.py (
    echo Creating bot_memory.py for database-free operation...
    copy /y NUL bot_memory.py > NUL
    echo import os > bot_memory.py
    echo import logging >> bot_memory.py
    echo import datetime >> bot_memory.py
    echo import asyncio >> bot_memory.py
    echo import discord >> bot_memory.py
    echo from discord.ext import commands >> bot_memory.py
    echo from discord import app_commands >> bot_memory.py
    echo from typing import Optional, Union, List >> bot_memory.py
    echo. >> bot_memory.py
    echo from memory_database import MemoryDatabase >> bot_memory.py
    echo. >> bot_memory.py
    echo # Configure logging >> bot_memory.py
    echo logger = logging.getLogger('d10-bot'^) >> bot_memory.py
    echo. >> bot_memory.py
    echo class D10Bot(commands.Bot^): >> bot_memory.py
    echo     """Main bot class with all core functionality""" >> bot_memory.py
    echo     def __init__(self^): >> bot_memory.py
    echo         # Enable all necessary intents >> bot_memory.py
    echo         intents = discord.Intents.default(^) >> bot_memory.py
    echo         intents.members = True >> bot_memory.py
    echo         intents.message_content = True >> bot_memory.py
    echo         intents.presences = True >> bot_memory.py
    echo. >> bot_memory.py
    echo         # Initialize the bot with prefix commands (!^) >> bot_memory.py
    echo         super(^).__init__( >> bot_memory.py
    echo             command_prefix="!", >> bot_memory.py
    echo             intents=intents, >> bot_memory.py
    echo             help_command=None  # Disable default help command >> bot_memory.py
    echo         ^) >> bot_memory.py
    echo. >> bot_memory.py
    echo         # Initialize database >> bot_memory.py
    echo         self.db = MemoryDatabase(^) >> bot_memory.py
    echo. >> bot_memory.py
    echo         # Settings >> bot_memory.py
    echo         self.staff_role_id = self._get_role_id("DISCORD_STAFF_ROLE_ID"^) >> bot_memory.py
    echo         self.status_role_id = self._get_role_id("DISCORD_STATUS_ROLE_ID"^) >> bot_memory.py
    echo         self.vouch_role_id = self._get_role_id("DISCORD_VOUCH_ROLE_ID"^) >> bot_memory.py
    echo         self.vouch_channel_id = self._get_channel_id("DISCORD_VOUCH_CHANNEL_ID"^) >> bot_memory.py
    echo. >> bot_memory.py
    echo         # Anti-raid settings >> bot_memory.py
    echo         self.anti_raid_mode = False >> bot_memory.py
    echo         self.join_timestamps = [] >> bot_memory.py
    echo. >> bot_memory.py
    echo         # Active tasks >> bot_memory.py
    echo         self.tasks = [] >> bot_memory.py
)

REM Update main.py to use memory database
findstr /C:"from bot_memory import D10Bot" main.py >nul 2>&1
if errorlevel 1 (
    echo Updating main.py to use memory database...
    powershell -Command "(Get-Content main.py) -replace 'from bot import D10Bot', 'from bot_memory import D10Bot' | Set-Content main.py"
)

REM Run the bot
python main.py

REM If the bot exits, ask if the user wants to restart
echo.
echo The bot has stopped.
choice /C YN /M "Do you want to restart the bot?"
if %errorlevel% equ 1 (
    cls
    goto :eof
) else (
    echo Exiting...
    timeout /t 3
    exit /b
)
