import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

guild_id = os.getenv("TEST_GUILD_ID")

TEST_GUILD_ID = int(guild_id) if guild_id else None
