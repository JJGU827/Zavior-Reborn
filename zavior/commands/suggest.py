
import logging

import discord
from discord import app_commands
from discord.ext import commands

from functions.ao3_retriever import retrieve_ao3_work
from functions.ao3_scraper import AO3ScraperError

logger = logging.getLogger("Zavior")


def format_list(items, max_length=950):
    """
    Format a list of tags for a Discord embed field.

    Discord limits each embed field to 1024 characters.
    """

    if not items:
        return "None"

    result = []
    length = 0

    for item in items:
        item = str(item).strip()

        if not item:
            continue

        separator = "\n• " if result else "• "
        addition = separator + item

        if length + len(addition) > max_length:
            break

        result.append(item)
        length += len(addition)

    remaining = len(items) - len(result)

    formatted = "\n".join(
        "• " + item for item in result
    )

    if remaining > 0:
        formatted += (
            "\n...and " + str(remaining) + " more"
        )

    return formatted or "None"


def add_field(embed, name, value, inline=False):
    """
    Add an embed field only when meaningful data exists.
    """

    if value is None:
        return

    if isinstance(value, list):
        if not value:
            return
        value = format_list(value)

    value = str(value).strip()

    if not value or value == "None":
        return

    embed.add_field(
        name=name,
        value=value[:1024],
        inline=inline
    )


def build_suggestion_embed(work, normalized, source):
    title = str(work.title or "Untitled Work")

    embed = discord.Embed(
        title=title[:256],
        url=work.url,
        color=discord.Color.purple()
    )

    authors = work.authors or []

    if authors:
        embed.description = (
            "**Author:** "
            + ", ".join(authors)
        )

    # Normalized fandom information
    add_field(
        embed,
        "Franchise",
        normalized.franchises
    )

    add_field(
        embed,
        "Series",
        normalized.series
    )

    add_field(
        embed,
        "Other Fandoms",
        normalized.other_fandoms
    )

    # Normalized relationships and themes
    add_field(
        embed,
        "Relationships",
        normalized.relationships
    )

    add_field(
        embed,
        "Key Themes",
        normalized.themes
    )

    add_field(
        embed,
        "Content Warnings",
        normalized.warnings
    )

    # General metadata
    add_field(
        embed,
        "Rating",
        work.rating,
        inline=True
    )

    add_field(
        embed,
        "Status",
        work.status,
        inline=True
    )

    add_field(
        embed,
        "Words",
        work.words,
        inline=True
    )

    add_field(
        embed,
        "Chapters",
        work.chapters,
        inline=True
    )

    add_field(
        embed,
        "Kudos",
        work.kudos,
        inline=True
    )

    add_field(
        embed,
        "Bookmarks",
        work.bookmarks,
        inline=True
    )

    # Summary
    if work.summary:
        summary = str(work.summary).strip()

        add_field(
            embed,
            "Summary",
            (
                summary[:900] + "..."
                if len(summary) > 900
                else summary
            )
        )

    embed.set_footer(
        text="Metadata source: " + source
    )

    return embed


class Suggest(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="suggest",
        description="Suggest an AO3 fanfiction."
    )
    @app_commands.describe(
        url="Link to an Archive of Our Own work."
    )
    async def suggest(
        self,
        interaction: discord.Interaction,
        url: str
    ):
        await interaction.response.defer(
            thinking=True
        )

        try:
            result = await retrieve_ao3_work(url)

            work = result.work
            normalized = result.normalized

            if normalized is None:
                raise AO3ScraperError(
                    "Normalized metadata is unavailable."
                )

            embed = build_suggestion_embed(
                work,
                normalized,
                result.source
            )

            await interaction.followup.send(
                embed=embed
            )

            logger.info(
                "Suggestion displayed: %s | Source: %s",
                work.title,
                result.source
            )

        except AO3ScraperError as error:
            logger.warning(
                "AO3 retrieval failed for %s: %s",
                url,
                error
            )

            await interaction.followup.send(
                "Unable to retrieve that AO3 work: "
                + str(error),
                ephemeral=True
            )

        except Exception:
            logger.exception(
                "Unexpected error in /suggest"
            )

            await interaction.followup.send(
                "An unexpected error occurred while "
                "processing this suggestion.",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Suggest(bot))