# import requests
# import json
import datetime
import os
import textwrap
from io import BytesIO
from multiprocessing.pool import ThreadPool

import discord
import pytz
from discord.commands import Option
from discord.utils import basic_autocomplete
from gtts import gTTS
from openai import OpenAI
from parsedatetime import Calendar
from ai_chunking import chunk_messages_by_model_token_limit, get_tokens

from history import time_for_dating_back, summarize_contents_of_channel_between_dates
from tagged_channels import get_tagged_channels

from constants import CONTEXT_LOOKBACK_DAYS, MESSAGE_CHUNK_SIZE, INTRO_MESSAGE, ERROR, MESSAGE_LINK, LESS_MESSAGES
from constants import setup_user, set_user, set_server, TIMEZONES, MODELS
import logging

calendar = Calendar()



class Summary:
    def __init__(self, message):
        self.messages = lambda prompt: [
            {"role": "system", "content": message},
            {"role": "user", "content": prompt},
        ]
        self.full_summary = ""

    def summarize(self, prompt, key, model):
        if key == "pok its confusing because i dont have diZ context":
            key = os.getenv("CHATGPT_TOKEN")

        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model=model,
            messages=self.messages(prompt)
        )

        assert isinstance(
            response.choices[0].message.content, str
        ), "API response is not a string"

        summary = response.choices[0].message.content
        self.full_summary += summary + "\n"
        
        return summary

    def tts(self, username):
        tts = gTTS(text=self.full_summary, lang="en", slow=False)
        sound = BytesIO()
        tts.write_to_fp(sound)
        sound.seek(0)
        return discord.File(sound, filename=f"{username}'s Summary.mp3")


async def summary(
    ctx,
    messages: int = Option(
        int, "Number of messages to summarize", required=False, default=100, min_value=1, max_value=1000
    ),
    mode: str = Option(
        str,
        "Method of constructing summary, check your modes with /listmodes",
        required=False,
        default="standard",
    ),
    channel: discord.TextChannel = Option(
        discord.TextChannel, "The channel which will be summarized", required=False
    ),
    secret_mode: bool = Option(
        bool,
        "Whether or not to use secret mode",
        required=False,
        default=False,
    ),
):
    await ctx.response.defer()

    if channel is None:
        channel = ctx.channel

    history = []
    first = True

    async for message in channel.history(limit=None):
        if first:
            first = False
            continue

        history.append(message)

        if len(history) == messages:
            break

    if not history:
        await ctx.followup.send(LESS_MESSAGES)
        return

    await send_summary(ctx, history[::-1], mode, channel, secret_mode)


async def fromtosummary(
    ctx,
    from_time: str = Option(
        str, "Start time of messages to summarize, in natural language", required=True
    ),
    to_time: str = Option(
        str, "End time of messages to summarize, in natural language", required=True
    ),
    mode: str = Option(
        str,
        "Method of constructing summary, check your modes with /listmodes",
        required=False,
        default="standard",
    ),
    channel: discord.TextChannel = Option(
        discord.TextChannel, "The channel which will be summarized", required=False
    ),
    secret_mode: bool = Option(
        bool,
        "Whether or not to use secret mode",
        required=False,
        default=False,
    ),
):
    await ctx.response.defer()

    user, _ = setup_user(str(ctx.author), ctx.guild.name, ctx.guild.id)

    if channel is None:
        channel = ctx.channel

    offset = TIMEZONES[user["region"]]
    if offset == 0:
        await ctx.followup.send(
            f"**NOTE: Currently your timezone is UTC, this may cause some unwanted times, use /setregion if you want to change your timezone.**\n"
        )

    from_time = calendar.parse(from_time)[0]
    to_time = calendar.parse(to_time)[0]
    from_time = datetime.datetime(
        from_time.tm_year,
        from_time.tm_mon,
        from_time.tm_mday,
        from_time.tm_hour,
        from_time.tm_min,
        from_time.tm_sec,
        tzinfo=pytz.FixedOffset(offset * 60),
    )
    to_time = datetime.datetime(
        to_time.tm_year,
        to_time.tm_mon,
        to_time.tm_mday,
        to_time.tm_hour,
        to_time.tm_min,
        to_time.tm_sec,
        tzinfo=pytz.FixedOffset(offset * 60),
    )
    await ctx.send(
        f"Parsed times: {from_time.strftime('%x %X')} to {to_time.strftime('%x %X')}"
    )
    utc_from_time = from_time.astimezone(pytz.UTC)
    utc_to_time = to_time.astimezone(pytz.UTC)

    history = []
    first = True
    async for message in channel.history(limit=None):
        if first:
            first = False
            continue
        if message.created_at < utc_to_time and message.created_at > utc_from_time:
            history.append(message)
        if message.created_at < utc_from_time:
            break

    if not history:
        await ctx.followup.send(
            f"There were no messages in the time range, {from_time.strftime('%x %X')} to {to_time.strftime('%x %X')}. Please double check your timezone with /setregion"
        )
        return

    await send_summary(ctx, history[::-1], mode, channel, secret_mode)


async def unreadsummary(
    ctx,
    mode: str = Option(
        str,
        "Method of constructing summary, check your modes with /listmodes",
        required=False,
        default="standard",
    ),
    secret_mode: bool = Option(
        bool,
        "Whether or not to use secret mode",
        required=False,
        default=False,
    ),
):
    await ctx.response.defer()

    history = []
    first = True

    async for message in ctx.channel.history(limit=None):
        if first:
            first = False
            continue

        history.append(message)

        if message.author.id == ctx.author.id:
            break

    if not history:
        await ctx.followup.send(LESS_MESSAGES)
        return

    await send_summary(ctx, history[::-1], mode, ctx.channel, secret_mode)


async def send_summary(ctx, messages, mode, channel=None, secret_mode=False):
    """
    Asynchronously sends a summary of messages in a specified mode and channel.
    Args:
        ctx (Context): The context of the command invocation, containing information about the user and guild.
        messages (list): A list of messages to be summarized.
        mode (str): The mode of summarization to be used.
        channel (Optional[Channel]): The channel where the summary will be sent. Defaults to the current channel.
        secret_mode (bool): Whether to enable secret mode for the summary. Defaults to False.
    Returns:
        None: This function does not return a value but performs asynchronous operations.
    Raises:
        None: This function does not explicitly raise exceptions but may propagate exceptions from called functions.
    Notes:
        - Validates the message count and summarization mode before proceeding.
        - Handles secret mode by creating a private thread if enabled.
        - Retrieves the API key for the user and server to process the summary.
        - Chunks messages based on the selected model and updates token counts.
        - Generates headings for the summary and sends an embed with summary details.
        - Processes grouped messages to generate and send the final summary.
    """

    if not validate_message_count(ctx, messages):
        logging.info(f"Message count exceeds limit: {len(messages)}")
        return

    user, server = setup_user(str(ctx.author), ctx.guild.name, ctx.guild.id)
    if not validate_mode(ctx, mode, user):
        logging.info(f"Invalid mode: {mode}")
        return

    use_a_thread = use_a_thread(ctx, user, secret_mode)
    api_key = get_api_key(ctx, user, server)
    if not api_key:
        return

    model = MODELS[user["model"]]
    chunks, chunk_counts, starts, in_token_count = chunk_messages_by_model_token_limit(messages, model)
    update_token_counts(user, server, ctx, in_token_count)

    headings = generate_headings(ctx, channel, starts, chunk_counts)
    await send_summary_embed(ctx, len(messages), mode, user, use_a_thread, in_token_count, model, chunks, secret_mode)

    summary = Summary(INTRO_MESSAGE.format(ctx.guild.name, user["modes"][mode], user["language"]))
    await process_summary_groups(ctx, chunks, headings, summary, api_key, model, user, server, use_a_thread)


async def validate_message_count(ctx, messages):
    if len(messages) > 5000:
        await ctx.followup.send("The maximum number of messages that can be summarized is 5000.")
        return False
    return True


async def validate_mode(ctx, mode, user):
    if mode not in user["modes"]:
        await ctx.followup.send(
            f"Mode `{mode}` not found. Please try again with a valid mode. Use /listmodes to see all your modes."
        )
        return False
    return True


async def use_a_thread(ctx, user, secret_mode):
    """
    Handles the secret mode functionality for the summary bot.
    This function checks if the secret mode is enabled and adjusts the thread
    setting accordingly. If secret mode is active and threads are enabled, it
    sends a follow-up message to notify the user that threads are being turned
    off for the summary.
    Args:
        ctx: The context object, typically representing the interaction context.
        user (dict): A dictionary containing user-related data, including the
            "thread" key which indicates whether threads are enabled.
        secret_mode (bool): A flag indicating whether secret mode is enabled.
    Returns:
        bool: The updated thread status after considering the secret mode setting.
    """
    use_a_thread = user["thread"]
    logging.info(f"Thread status: {use_a_thread}")
    logging.info(f"Secret mode status: {secret_mode}")

    if secret_mode:
        if use_a_thread is True:
            await ctx.followup.send(
                "Summary Bot is turning off threads for this summary because you are using secret mode.",
                ephemeral=secret_mode
            )
            use_a_thread = False

    logging.info(f"Thread status after secret mode check: {use_a_thread}")
    return use_a_thread


async def get_api_key(ctx, user, server):
    """
    Asynchronously retrieves the API key for a user or server.
    This function checks the user's API key first. If the user's API key is set to "NONE",
    it falls back to the server's API key. If the server's API key is also "NONE", a message
    is sent to the user explaining that the common API key has been disabled and that they
    need to use their own OpenAI API key.
    Args:
        ctx: The context object used to send follow-up messages.
        user (dict): A dictionary containing user-specific data, including the "api-key".
        server (dict): A dictionary containing server-specific data, including the "api-key".
    Returns:
        str or None: The API key as a string if available, or None if no valid API key is found.
    """

    api_key = user["api-key"]
    if api_key == "NONE":
        api_key = server["api-key"]
        if api_key == "NONE":
            await ctx.followup.send(
                "Due to inappropriate usage of the common API key provided by Summary Bot, we have decided to shut it down. "
                "Summary Bot is still fully functional, but just with your own OpenAI API key."
            )
            return None
    return api_key


async def update_token_counts(user, server, ctx, in_token_count):
    """
    Asynchronously updates the token counts for a user and a server.
    This function increments the input token count for both the user and the server,
    and then updates their respective records in the storage.
    Args:
        user (dict): A dictionary containing user data, including the current token count.
        server (dict): A dictionary containing server data, including the current token count.
        ctx (Context): The context of the command invocation, used to identify the user and server.
        in_token_count (int): The number of input tokens to add to the user's and server's token counts.
    Returns:
        None
    """

    user["in_token_count"] += in_token_count
    set_user(str(ctx.author), user)
    server["in_token_count"] += in_token_count
    set_server(ctx.guild.name, ctx.guild.id, server)


def generate_headings(ctx, channel, starts, chunk_counts):
    """
    Generates a list of summary headings based on message links and group counts.
    Args:
        ctx: The context object, typically containing information about the guild.
        channel: The channel object where the messages are located.
        starts: A list of message objects representing the starting points of groups.
        group_counts: A list of integers representing the number of messages in each group.
    Returns:
        list: A list of formatted strings, each representing a summary heading with 
              message links and the number of messages in the group.
    """

    headings = []
    for i in range(len(starts) - 1):
        message1_link = MESSAGE_LINK.format(ctx.guild.id, channel.id, starts[i].id)
        message2_link = MESSAGE_LINK.format(ctx.guild.id, channel.id, starts[i + 1].id)
        num_messages = chunk_counts[i]
        headings.append(
            f"Summary from **{message1_link}** to **{message2_link}**. This summary contains __{num_messages}__ messages.\n\n"
        )
    return headings


async def send_summary_embed(ctx, message_count, mode, user, thread, in_token_count, model, chunks, ephemeral):
    """
    Sends an embed message summarizing the details of a summary generation request.
    Args:
        ctx (discord.ext.commands.Context): The context of the command invocation.
        message_count (int): The number of messages being summarized.
        mode (str): The mode of the summary generation (e.g., concise, detailed).
        user (dict): A dictionary containing user-specific information, such as language preference.
        thread (str): The thread or channel where the summary is being generated.
        in_token_count (int): The total number of input tokens used for the summary.
        model (dict): A dictionary containing model-specific information, such as the model name.
        groups (list): A list of message groups being summarized.
        ephemeral (bool): Whether the embed message should be ephemeral (visible only to the user).
    Returns:
        None
    """

    info_str = (
        f"Messages: ``{message_count}``\n"
        f"Mode: ``{mode}``\n"
        f"Language: ``{user['language']}``\n"
        f"Thread: ``{thread}``\n"
        f"Total Input Tokens: ``{in_token_count}``\n"
        f"Model: ``{model['name']}``\n"
        f"By {ctx.author.mention}"
    )
    embed = discord.Embed(title="Generated summary")
    embed.description = f"A `{len(chunks)}-message` summary is being prepared..."
    embed.add_field(name="Command Arguments:", value=info_str)
    await ctx.followup.send(embed=embed, ephemeral=ephemeral)


async def process_summary_groups(ctx, chunks, headings, summary, api_key, model, user, server, thread):
    """
    Asynchronously processes and sends summaries for a given set of groups.
    This function generates summaries for the provided groups using the specified
    API key and model, sends the summaries to the appropriate context, and updates
    token usage statistics. It also handles text-to-speech (TTS) summaries and
    error handling.
    Args:
        ctx (Context): The context object representing the current execution environment.
        groups (list): A list of groups to generate summaries for.
        headings (list): A list of headings corresponding to each group.
        summary (str): The overall summary text to be used for TTS.
        api_key (str): The API key for accessing the summary generation service.
        model (str): The model identifier to be used for generating summaries.
        user (User): The user object representing the current user.
        server (Server): The server object representing the current server.
        thread (Thread): The thread object where summaries will be sent.
    Raises:
        Exception: If an error occurs during summary processing, it is caught and
                   passed to the error handler.
    Returns:
        None
    """

    try:
        send_message_function, send_tts_function = functions_for_sending_message_and_tts(ctx, thread)
        responses = generate_a_summary_for_all_chunks(chunks, api_key, model, summary)

        for i, response in enumerate(responses):
            await send_group_summary(ctx, headings[i], response, send_message_function)
            update_output_token_counts(response, user, server, ctx)

        await send_tts_summary(ctx, summary, send_tts_function, send_message_function)
    except Exception as e:
        await handle_summary_error(ctx, e)


async def functions_for_sending_message_and_tts(ctx, thread, embed, messages, secret_mode):
    """
    Asynchronously sets up message sending functions for a Discord bot, allowing messages
    and files to be sent either in a thread or as follow-up messages.
    Args:
        ctx (discord.ext.commands.Context): The context of the command invocation.
        thread (bool): Whether to create and use a thread for sending messages.
        embed (discord.Embed): The embed to send as the initial message.
        messages (list): A list of messages to summarize, used for naming the thread in the channel.
        secret_mode (bool): If True, messages will be sent ephemerally (visible only to the user).
    Returns:
        tuple: A pair of functions:
            - send_message (function): A function to send text messages.
            - send_tts (function): A function to send files (e.g., text-to-speech audio).
    """

    if thread:
        message = await ctx.followup.send(embed=embed)
        thread = await ctx.channel.create_thread(
            name=f"Summary by {ctx.author.display_name}, {len(messages)} messages",
            message=message,
        )
        send_message = lambda msg: thread.send(msg, suppress=True)
        send_tts = lambda f: thread.send(file=f, suppress=True)
    else:
        send_message = lambda msg: ctx.followup.send(msg, ephemeral=secret_mode)
        send_tts = lambda f: ctx.followup.send(file=f, ephemeral=secret_mode)
    return send_message, send_tts


def generate_a_summary_for_all_chunks(chunk, api_key, model, summary):
    """
    Generates summaries for a list of chunks using a specified model and API key.
    Args:
        chunks (list): A list of chunks to generate summaries for.
        api_key (str): The API key required for authentication with the summarization service.
        model (dict): A dictionary containing model details, including the model name.
        summary (object): An object with a `summarize` method that performs the summarization.
    Returns:
        list: A list of summaries generated for each chunk.
    """

    to_generate = [(chunk[i], api_key, model["name"]) for i in range(len(chunk))]
    with ThreadPool(len(chunk)) as pool:
        return pool.starmap(summary.summarize, to_generate)


async def send_group_summary(ctx, heading, response, send_message_function):
    """
    Asynchronously sends a summarized message to a Discord channel.
    This function takes a heading and a response, combines them into a single
    block of text, and sends the text in chunks of a specified size to avoid
    exceeding message size limits.
    Args:
        ctx: The context in which the function is called. Typically includes
             metadata about the command invocation.
        heading (str): The heading or title of the summary.
        response (str): The body of the summary to be sent.
        send_message (Callable[[str], Awaitable[None]]): An asynchronous function
            used to send a message. It is called with each chunk of the summary.
    Returns:
        None
    """
    
    block = heading + response
    for chunk in textwrap.wrap(block, MESSAGE_CHUNK_SIZE, replace_whitespace=False):
        await send_message_function(chunk)


def update_output_token_counts(response, user, server, ctx):
    tokens = get_tokens(response)
    user["out_token_count"] += tokens
    set_user(str(ctx.author), user)
    server["out_token_count"] += tokens
    set_server(ctx.guild.name, ctx.guild.id, server)


async def send_tts_summary(ctx, summary, send_tts_function, send_message_function):
    """
    Asynchronously sends a text-to-speech (TTS) summary to the user.
    
    """

    try:
        result = summary.tts(ctx.author.display_name)
        await send_tts_function(result)
    except Exception as e:
        await send_message_function(ERROR.format(f"There was an error in generating the TTS summary: {e}"))


async def handle_summary_error(ctx, error):
    print(error)
    await ctx.followup.send(ERROR.format(error))


async def discord_command_summarize_all(ctx, 
                                        time_period: str = Option(str, "Time period",            required=False, default="1d"), 
                                        tag:         str = Option(str, "Tag to filter channels", required=False, default=None),
                                        category:    str = Option(str, "Category to filter channels", required=False, default=None)
                                        ):
    now = datetime.now()
    time_to_look_back = time_for_dating_back(now, time_period)
    time_to_look_back_for_context = now - timedelta(days=CONTEXT_LOOKBACK_DAYS)

    # "standard": INTRO_MESSAGE.format(ctx.guild.name, "standard", "english"),
    ai_prompts = {
        "formatting_instructions": "Format my answer as markdown",
        "context_prompt": "I’d like to ask you for a summary of a chat conversation. First, I will provide you with the context of the conversation so that you can better understand what it’s about, and then I will write the continuation, for which I will ask you to summarize and highlight the most important points. Here is the context:",
        "recent_messages_prompt": "Now, please summarize the following conversation, highlighting the most important elements in bold. Using one level of headers and one level of nested bullet points whenever that makes sense. Pay attention to technical and design details. Highlight the most important elements or terms in bold. Include any links to Discord channels. Don't repeat the details of the conversation. Ignore people thanking each other. If I gave you no conversation points just say 'no messages in the time period'.",
    }

    target_channel = ctx.channel
    
    #categories = [category for category in ctx.guild.channels if isinstance(category, discord.CategoryChannel)]
    #await target_channel.send(f"Categories in {ctx.guild.name}: {[cat.name for cat in categories]}")


    if tag:
        channels = get_tagged_channels(ctx.guild, tag)
        criteria = f"tag ({tag})"
    elif category:
        channels = [channel for channel in ctx.guild.channels if channel.category.name == category]
        criteria = f"category ({category})"
    else:
        channels = ctx.guild.channels
        criteria = "all"

    await target_channel.send(f"\n\nSummarizing all channels (criteria={criteria}) in {ctx.guild.name}...\n")


    for channel in channels:
        if isinstance(channel, discord.VoiceChannel):
            logging.info(f"Skipping voice channel {channel.name}")
            ctx.respond(f"Skipping voice channel {channel.name}")
            continue
        if isinstance(channel, discord.CategoryChannel):
            logging.info(f"Skipping category channel {channel.name}")
            ctx.respond(f"Skipping category channel {channel.name}")
            continue
        if isinstance(channel, discord.ForumChannel):
            logging.info(f"Skipping forum channel {channel.name}")
            ctx.respond(f"Skipping forum channel {channel.name}")
            continue
        if channel.permissions_for(ctx.guild.me).read_messages and channel.name != "summary":
            await target_channel.send(content=f"Summarizing {channel.name}... {time_to_look_back}")
            await summarize_to_named_channel(target_channel, channel, ctx, ai_prompts, time_period)


async def summarize_to_named_channel(target_channel, source_channel, ctx, ai_prompts, time_period="1d", context_lookback_days=2):
    """
    (Originally `process_channel`)
    Process the messages from a Discord channel and generate a summary response.
    Args:
        channel (discord.TextChannel): The Discord channel to process messages from.
        ctx (discord.ext.commands.Context): The context of the command.
        ai_prompts (str): The AI prompts to use for summarization.
        time_period (str): The time period to summarize (default is "1d").
        context_lookback_days (int): The number of days to look back for context (default is 5 days).
    Returns:
        str: A formatted HTML string containing the summarized content of the channel messages.
    """
    endtime_to_summarize = datetime.now()
    starttime_to_summarize = time_for_dating_back(endtime_to_summarize, time_period)
    prior_timeframe_for_context = time_for_dating_back(starttime_to_summarize, f"{context_lookback_days}d")

    logging.info(f"Summarizing messages from {source_channel} between {starttime_to_summarize.date()} and {endtime_to_summarize.date()}")
    await target_channel.send(f"Summarizing messages from {source_channel} between {starttime_to_summarize.date()} and {endtime_to_summarize.date()}")
    summary = await summarize_contents_of_channel_between_dates(source_channel, starttime_to_summarize, endtime_to_summarize, prior_timeframe_for_context, ai_prompts)

    response = f"**<#{source_channel.id}>**\n"  + summary

    response_chunks = [response[i:i + MESSAGE_CHUNK_SIZE] for i in range(0, len(response), MESSAGE_CHUNK_SIZE)]
    for chunk in response_chunks:
        await target_channel.send(chunk)