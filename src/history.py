# Description: This file contains functions for retrieving and summarizing message history from Discord channels.
#  The `summarize_contents_of_channel_between_dates` function processes messages from a Discord channel within a specified time frame, retrieves prior messages for context, and generates a summarized response.
#  The `get_channel_messages` function retrieves messages from a specified Discord channel within a given time range.

import logging
from openai_summarizer import *

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

    logging.info(f"Messages received on {channel} from {starttime_to_summarize.date()} and prior during {prior_timeframe_for_context.date()}:")
   # logging.debug(recent_channel_messages)

    response = f"<h2>Contents of #{channel.name} between {starttime_to_summarize.date()} and {endtime_to_summarize.date()}\n</h2>\n\n" #TODO: find a better way to format this    

    prior_messages = []
    if recent_channel_messages:
        prior_messages = await get_channel_messages(channel, start=prior_timeframe_for_context, end=starttime_to_summarize)
        logging.debug(f"For context, retrieved prior messages during {prior_timeframe_for_context} in {channel}: {prior_messages}")
        if len(prior_messages) == 0:
            logging.debug("No prior messages found for context")
    
    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()]) #TODO: remove this line

    # TODO prior_messages is an array of strings, not a string, so the length is not representative of the number of tokens
    max_tokens = 30000  # Maximum tokens for OpenAI API
    assumed_token_length = 50  # Assumed average token length
    logging.info("Chunking for summarization")
    logging.debug(f"Length for prior messages: {len(prior_messages)}")
    budget_for_chunk = max_tokens - len(prior_messages)* assumed_token_length 
    logging.debug(f"Budget for chunk: {budget_for_chunk}")

    if budget_for_chunk < 0:
        logging.error("Prior messages exceed token limit. Truncating.")
        prior_messages = prior_messages[:int(max_tokens/assumed_token_length)]
        budget_for_chunk = 0

    # Divide recent_channel_messages into a chunked array if  exceeds max_tokens
    chunk_size = 1000  # Adjust chunk size as needed
    chunks = []
    for i in range(0, len(recent_channel_messages), chunk_size):
        chunks.append(recent_channel_messages[i:i + chunk_size])

    logging.debug(f"Number of chunks: {len(chunks)}")
    chunked_responses = []
    for chunk in chunks:
        chunked_response = await summarizer.get_summary_from_ai("\n".join(prior_messages),
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

    channel_messages = []
    async for msg in channel.history(after=start, before=end):
        first_message = True
        async for msg in channel.history(after=start, before=end):
            if msg.author != bot.user and not msg.content.startswith("/"):
                if first_message:
                    message_url = f"https://discord.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id}"
                    channel_messages.append(f"Discord: <a href='{message_url}'>Link to messages in {msg.guild.name}</a>")
                    channel_messages.append(f"{msg.author.display_name}: {msg.content}")
                    first_message = False
                else:
                    channel_messages.append(f"{msg.author.display_name}: {msg.content}")
    return channel_messages