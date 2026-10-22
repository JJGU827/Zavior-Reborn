import logging

import discord
from discord import app_commands
from discord.ext import commands

from functions.url_parser import parse_fanfiction_url
from functions.ao3_scraper import (
    scrape_ao3,
    AO3ScraperError
)


logger = logging.getLogger("Zavior")


def format_list(items, limit=900):
    if not items:
        return "None listed"

    result = ""

    for item in items:
        addition = item + "\n"

        if len(result) + len(addition) > limit:
            result += "..."
            break

        result += addition

    return result.strip()


def truncate(text, limit=1000):
    if len(text) <= limit:
        return text

    return text[:limit - 3].rstrip() + "..."


class Suggest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="suggest",
        description="Suggest a fanfiction from AO3 or FFN."
    )
    @app_commands.describe(
        url="The AO3 or FanFiction.net story URL."
    )
    async def suggest(
        self,
        interaction: discord.Interaction,
        url: str
    ):
        # Parsing and network requests can take time.
        await interaction.response.defer(thinking=True)

        story = parse_fanfiction_url(url)

        if story is None:
            await interaction.followup.send(
                "Invalid URL. Please provide a valid "
                "AO3 or FanFiction.net story link.",
                ephemeral=True
            )
            return

        # AO3 metadata extraction
        if story["site"] == "Archive of Our Own (AO3)":
            try:
                work = await scrape_ao3(story["url"])

            except AO3ScraperError as error:
                await interaction.followup.send(
                    "Unable to retrieve AO3 metadata:\n"
                    + str(error),
                    ephemeral=True
                )
                return

            except Exception:
                logger.exception(
                    "Unexpected AO3 scraping error"
                )

                await interaction.followup.send(
                    "An unexpected error occurred "
                    "while retrieving AO3 metadata.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title=truncate(work.title, 250),
                url=work.url,
                description=truncate(work.summary, 3500),
                color=discord.Color.purple()
            )

            embed.add_field(
                name="Author",
                value=format_list(work.authors),
                inline=True
            )

            embed.add_field(
                name="Rating",
                value=truncate(work.rating),
                inline=True
            )

            embed.add_field(
                name="Status",
                value=work.status,
                inline=True
            )

            embed.add_field(
                name="Fandoms",
                value=format_list(work.fandoms),
                inline=False
            )

            embed.add_field(
                name="Relationships",
                value=format_list(work.relationships),
                inline=False
            )

            embed.add_field(
                name="Characters",
                value=format_list(work.characters),
                inline=False
            )

            embed.add_field(
                name="Additional Tags",
                value=format_list(work.additional_tags),
                inline=False
            )

            embed.add_field(
                name="Warnings",
                value=format_list(work.warnings),
                inline=False
            )

            embed.add_field(
                name="Categories",
                value=format_list(work.categories),
                inline=False
            )

            embed.add_field(
                name="Words",
                value=work.words,
                inline=True
            )

            embed.add_field(
                name="Chapters",
                value=work.chapters,
                inline=True
            )

            embed.add_field(
                name="Language",
                value=work.language,
                inline=True
            )

            embed.add_field(
                name="Kudos",
                value=work.kudos,
                inline=True
            )

            embed.add_field(
                name="Bookmarks",
                value=work.bookmarks,
                inline=True
            )

            embed.add_field(
                name="Hits",
                value=work.hits,
                inline=True
            )

            embed.add_field(
                name="Published",
                value=work.published,
                inline=True
            )

            embed.add_field(
                name="Updated",
                value=work.updated,
                inline=True
            )

            embed.set_footer(
                text="AO3 Metadata | Suggested by "
                + str(interaction.user)
            )

            await interaction.followup.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions.none()
            )

            logger.info(
                "AO3 suggestion: %s by user %s",
                story["url"],
                interaction.user.id
            )

        else:
            # FFN metadata support will be implemented later.
            embed = discord.Embed(
                title="Fanfiction Suggestion Received",
                description="Valid FanFiction.net link.",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="Story ID",
                value=story["story_id"]
            )

            embed.add_field(
                name="URL",
                value=story["url"],
                inline=False
            )

            embed.set_footer(
                text="FFN metadata extraction coming soon."
            )

            await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Suggest(bot))
