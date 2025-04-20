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
