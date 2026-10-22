
import logging

import discord
from discord.ext import commands

from config import DISCORD_TOKEN, TEST_GUILD_ID


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("Zavior")


class ZaviorBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()

        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        # Load all command modules before synchronization
        await self.load_extension("commands.ping")
        await self.load_extension("commands.suggest")

        logger.info("All command modules loaded.")

        if TEST_GUILD_ID:
            guild = discord.Object(id=TEST_GUILD_ID)

            # Copy global command definitions to test server
            self.tree.copy_global_to(guild=guild)

            # Synchronize current test server commands
            synced = await self.tree.sync(guild=guild)

            logger.info(
                "Synchronized %s commands to guild %s",
                len(synced),
                TEST_GUILD_ID
            )

        else:
            synced = await self.tree.sync()

            logger.info(
                "Synchronized %s global commands",
                len(synced)
            )

    async def on_ready(self):
        logger.info("Logged in as %s", self.user)
        logger.info("Zavior is online!")


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError(
            "Missing DISCORD_TOKEN in .env file."
        )

    bot = ZaviorBot()
    bot.run(DISCORD_TOKEN)
