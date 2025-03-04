# Description: This file contains the implementation of the summary_for_webhook function, which generates a summary for a Discord webhook based on the provided payload.
# Calls process_channel for each channel in the payload, which
# correspondingly calls get_channel_messages and OpenAISummarizer.get_summary




import re
from datetime import datetime, timedelta
import json
import logging
import discord
from discord.ext import commands
from flask import request
from openai_summarizer import OpenAISummarizer
from history import summarize_contents_of_channel_between_dates
from webhook import app
from webhook import log_diagnostic_message
from history import time_for_dating_back
from constants import CONTEXT_LOOKBACK_DAYS
import asyncio

#When called from the internal function, the timeout is handled by the asyncio.timeout context manager.
#This ensures that the function returns a response within the specified time limit.
async def summary_for_internal_call(diagnostic_channel_id, payload):
    try:
        async with asyncio.timeout(10):
            response = await summary_from_payload(diagnostic_channel_id, payload)
    except asyncio.TimeoutError:
            response = "Timeout error occurred while processing the summary."
    return response

#Inside Flask App:
#The framework handled timeouts (e.g., request timeouts in Flask).
#It manages the event loop and automatically scheduled coroutines.
#The async functions are running inside an existing event loop.
async def summary_for_webhook(diagnostic_channel_id):
    payload = request.json
    response = await summary_from_payload(diagnostic_channel_id, payload)
    return response



# Shared logic for generating a summary from a payload
async def summary_from_payload(diagnostic_channel_id, payload):
    """
    Generates a summary for a Discord webhook based on the provided payload.
    Args:
        diagnostic_channel_id (int): The ID of the diagnostic channel.
    Returns:
        str: The generated summary response.

    The function processes the payload received from a webhook request, which includes:
    - `endtime_to_summarize`: The end time for the summary period (default is now).
    - `time_period`: The duration of the time period to summarize (default is 1 day).
    - `ai_prompts`: AI prompts for generating the summary.
    - `context_lookback_days`: Number of days to look back for context (default is 5 days).
    - `diagnostic_channel_id`: The ID or name of the diagnostic channel.
    - `guild_ids`: List of guild IDs or names to include in the summary.
    - `channels_to_include`: List of channel IDs or names to include in the summary.
    - `channels_to_exclude`: List of channel IDs or names to exclude from the summary.

    The function performs the following steps:
    1. Parses the payload and determines the time period for the summary.
    2. Logs diagnostic information.
    3. Identifies the diagnostic channel and validates its existence.
    4. Prepares the response string with summary details.
    5. Iterates through the specified guilds and channels to generate the summary.
    6. Logs and skips channels based on permissions and exclusions.
    7. Calls `process_channel` to generate the summary for each channel.
    8. Returns the final summary response.
    Raises:
        ValueError: If the diagnostic channel ID is invalid.
    """
    now = datetime.now().replace(microsecond=0)

    endtime_to_summarize = payload.get("endtime_to_summarize", now)
    if endtime_to_summarize == 'now':
        endtime_to_summarize = now
    else:
        endtime_to_summarize = datetime.fromisoformat(endtime_to_summarize)

    time_period = payload.get("time_period", "1d")
    logging.debug(f"Time period: {time_period}")

    starttime_to_summarize = time_for_dating_back(endtime_to_summarize, time_period)

    logging.debug(f"From {starttime_to_summarize} to {endtime_to_summarize}")

    ai_prompts = payload.get("ai_prompts", {})
    context_lookback_days = payload.get("context_lookback_days", CONTEXT_LOOKBACK_DAYS)

    logging.info("Received webhook payload: %s", json.dumps(payload, indent=4))
    logging.debug(f"ai_prompts: {ai_prompts}")

    app.diagnostic_channel_id = 0
    if payload['diagnostic_channel_id']:
        channel_name_or_id = payload['diagnostic_channel_id']
        if not isinstance(channel_name_or_id,int):
            logging.info("channel_name_or_id is not an int, looking up the channel by name from the bot's guild.")
            app.diagnostic_channel_id = discord.utils.get(app.bot.guilds. channels, name=channel_name_or_id)
        else:
            app.diagnostic_channel_id = channel_name_or_id
        
    # TODO: Validate the diagnostic channel ID    
    #    if app.bot.get_channel(app.diagnostic_channel_id) is None:
    #        raise ValueError(f"Invalid diagnostic channel ID: {app.diagnostic_channel_id}")

    response = ""



    prior_starttime_for_context =starttime_to_summarize - timedelta(days=context_lookback_days)
    logging.info(f"Webhook summary started {starttime_to_summarize} to {endtime_to_summarize}, preceded by context of {prior_starttime_for_context}")

    response += f"Summary of channels\n\n"
    response += f"Showing from {starttime_to_summarize} to {endtime_to_summarize}\n\n"
    response += f"Prior context from {prior_starttime_for_context} for {context_lookback_days} days\n\n"

    #await log_diagnostic_message(response)
    
    guilds = []
    if 'guild_ids' in payload and payload['guild_ids']:
        guild_ids = payload['guild_ids']
        for guild in app.bot.guilds:
            if guild.id in guild_ids or guild.name in guild_ids:
                guilds.append(guild)        
            else:
                logging.debug(f"Skipping guild {guild}")
    else:
        guilds = app.bot.guilds

    for guild in guilds:
        text_channels = []

        channels_to_exclude = payload.get("channels_to_exclude", [])

        if 'channels_to_include' in payload:
            channels = payload.get("channels_to_include", [])
            for channel in guild.text_channels:
                if channel.id in channels or channel.name in channels:
                    if channel.id not in channels_to_exclude and channel.name not in channels_to_exclude:
                        text_channels.append(channel)
                    else:
                        logging.debug(f"Channel {channel} is in exclude list")
                else:
                    logging.debug(f"Skipping channel {channel}")
        else:
            logging.debug("No channels_to_include in payload, processing all text channels")

        if text_channels == []:
            logging.info(f"No channels to summarize in {guild}")

        response += (f"# GUILD {guild}") 
        for channel in text_channels:
            await log_diagnostic_message(f"CHANNEL {channel}")
            if channel.id == diagnostic_channel_id:
                await log_diagnostic_message("skipping of processing the diagnostic channel")
                continue
            if channel.name == "summary": # legacy compatibility
                await log_diagnostic_message("skipping of processing the summary channel")
                continue
            if channel.permissions_for(channel.guild.me).read_messages:
                response += await summarize_contents_of_channel_between_dates(channel, 
                                                    starttime_to_summarize,
                                                    endtime_to_summarize,
                                                    prior_starttime_for_context,
                                                    ai_prompts)
            else:
                response += f"Skipping channel {channel.name} due to lack of permissions\n"

    logging.info("Summaries done")
    return response

