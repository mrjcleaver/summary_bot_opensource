# Description: This file contains functions for retrieving and summarizing message history from Discord channels.
#  The `summarize_contents_of_channel_between_dates` function processes messages from a Discord channel within a specified time frame, retrieves prior messages for context, and generates a summarized response.
#  The `get_channel_messages` function retrieves messages from a specified Discord channel within a given time range.

import logging
from openai_summarizer import *
from constants import MESSAGE_CHUNK_SIZE
from datetime import datetime, timedelta
import re
from ai_chunking import chunk_messages, chunk_messages_by_model_token_limit

async def summarize_contents_of_channel_between_dates(channel, starttime_to_summarize, endtime_to_summarize, prior_timeframe_for_context, ai_prompts):
    """
    Asynchronously processes messages from a Discord channel within a specified time frame, retrieves prior messages for context, and generates a summarized response.
    Args:
        channel (discord.TextChannel): The Discord channel to process messages from.
        starttime_to_summarize (datetime): The start time of the period to summarize messages.
        endtime_to_summarize (datetime): The end time of the period to summarize messages.
        prior_timeframe_for_context (datetime): The start time of the period to retrieve prior messages for context.
        ai_prompts (str): The AI prompts to use for summarization.
    Returns:
        str: A formatted HTML string containing the summarized content of the channel messages within the specified time frame.
    """

    recent_channel_messages = await get_channel_messages(channel, start=starttime_to_summarize, end=endtime_to_summarize) 

    logging.info(f"Messages received from Discord about {channel} from {starttime_to_summarize.date()} and prior during {prior_timeframe_for_context.date()}:")
   # logging.debug(recent_channel_messages)

    response = f"## Contents of #{channel.name} between {starttime_to_summarize.date()} and {endtime_to_summarize.date()}\n\n" 

    prior_messages = []
    if recent_channel_messages:
        prior_messages = await get_channel_messages(channel, start=prior_timeframe_for_context, end=starttime_to_summarize)
        logging.debug(f"For context, retrieved prior messages during {prior_timeframe_for_context} in {channel}: {prior_messages}")
        if len(prior_messages) == 0:
            logging.debug("No prior messages found for context")

    # TODO: merge these chunks and groups mechanisms
    chunks = chunk_messages(prior_messages, recent_channel_messages)
    groups,  group_counts, starts, in_token_count = chunk_messages_by_model_token_limit(recent_channel_messages, "gpt-4o")
    logging.debug(f"Number of groups: {len(groups)}")
    logging.debug(f"Number of chunks: {len(chunks)}")
    logging.debug(f"Number of starts: {len(starts)}")
    logging.debug(f"Total tokens: {in_token_count}")
    logging.debug(f"Group counts: {group_counts}")

    chunked_responses = []
    for chunk in chunks:
        chunked_response = await summarizer.get_cached_summary_from_ai("\n".join(prior_messages),
                                                                "\n".join(chunk),
                                                                 ai_prompts)
        chunked_responses.append(chunked_response)

    response += "\n".join(chunked_responses) + "\n"

    return response

async def get_channel_messages(channel, start, end):
    """
    Retrieve messages from a specified Discord channel within a given time range.

    Args:
        channel (discord.TextChannel): The Discord channel to retrieve messages from.
        start (datetime.datetime): The start time to retrieve messages from.
        end (datetime.datetime): The end time to retrieve messages until.

    Returns:
        list: A list of strings containing the messages retrieved from the channel.
              The first message includes a link to the messages in the channel.
    """
    logging.debug(f"Retrieving messages from {channel} between {start} and {end}")

    # Get the bot object from the channel
    bot = channel.guild.me._state._get_client() #TDO - code smell
    bot = channel.guild.me.guild.me

    channel_messages = []
    async for msg in channel.history(after=start, before=end):
        first_message = True

        if msg.author != bot.user and not msg.content.startswith("/"):
            if first_message:
                message_url = f"https://discord.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id}"
                channel_messages.append(f"Discord: <a href='{message_url}'>Link to messages in {msg.guild.name}</a>")
                channel_messages.append(f"{msg.author.display_name}: {msg.content}")
                first_message = False
            else:
                channel_messages.append(f"{msg.author.display_name}: {msg.content}")
    return channel_messages


# Legacy Helper function
def time_for_dating_back(enddate, time_period):

    match = re.match(r'(\d+)([dhm])$', time_period)
    if not match:
        raise ValueError("Invalid time period format. Use '<number><d/h/m>' (e.g., '1d', '6h', '30m').")

    quantity, unit = match.groups()
    quantity = int(quantity)


    return {
        'd': enddate - timedelta(days=quantity),
        'h': enddate - timedelta(hours=quantity),
        'm': enddate - timedelta(minutes=quantity)
    }.get(unit, ValueError("Invalid time unit. Use 'd' for days, 'h' for hours, or 'm' for minutes."))

