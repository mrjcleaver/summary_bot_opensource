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
from tiktoken import encoding_for_model
from history import time_for_dating_back, summarize_contents_of_channel_between_dates
from datetime import datetime, timedelta
from tagged_channels import get_tagged_channels

from constants import *
import logging

calendar = Calendar()

TOKENIZER = encoding_for_model("gpt-3.5-turbo")
get_tokens = lambda text: len(TOKENIZER.encode(text))


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
    if len(messages) > 5000:
        await ctx.followup.send(
            "The maximum number of messages that can be summarized is 5000."
        )
        return

    # Grab variables from database
    user, server = setup_user(str(ctx.author), ctx.guild.name, ctx.guild.id)
    language = user["language"]
    if mode in user["modes"]:
        mode_prompt = user["modes"][mode]
    else:
        await ctx.followup.send(
            f"Mode `{mode}` not found. Please try again with a valid mode. Use /listmodes to see all your modes."
        )
        return

    thread = user["thread"]

    if secret_mode:
        if thread is True:
            await ctx.followup.send(
                "Summary Bot is turning off threads for this summary because you are using secret mode.",
                ephemeral=secret_mode
            )
            thread = False

    api_key = user["api-key"]
    if api_key == "NONE":
        api_key = server["api-key"]
        if api_key == "NONE":
            await ctx.followup.send(
                f"Due to inappropriate usage of the common API key provided by Summary Bot, we have decided to shut it down. Summary Bot is still fully functional, but just with your own OpenAI API key."
            )
            return

    if mode not in user["modes"]:
        await ctx.followup.send(
            f"Mode `{mode}` not found. Please try again with a valid mode. Use /listmodes to see all your modes."
        )
        return

    model = MODELS[user["model"]]

    # Group messages into groups of MAX_TOKENS
    # Create a list starts for the first message in each group
    next_group = True
    groups = []
    group_counts = []
    starts = []
    curr_group = ""
    curr_count = 0
    in_token_count = 0

    for message in messages:
        if next_group:
            starts.append(message)
            next_group = False

        m = f"{message.author.display_name}: {message.content}\n"

        if get_tokens(curr_group + m) > (MAX_TOKENS * model["context_length"]):
            in_token_count += get_tokens(curr_group)
            groups.append(curr_group)
            group_counts.append(curr_count)
            curr_group = ""
            curr_count = 0
            next_group = True

        curr_group += m
        curr_count += 1

    starts.append(message)
    groups.append(curr_group)
    group_counts.append(curr_count)
    in_token_count += get_tokens(curr_group)

    user["in_token_count"] += in_token_count
    set_user(str(ctx.author), user)

    server["in_token_count"] += in_token_count
    set_server(ctx.guild.name, ctx.guild.id, server)

    headings = []
    for i in range(len(starts) - 1):
        message1_link = MESSAGE_LINK.format(ctx.guild.id, channel.id, starts[i].id)
        message2_link = MESSAGE_LINK.format(ctx.guild.id, channel.id, starts[i + 1].id)
        num_messages = group_counts[i]
        headings.append(
            f"Summary from **{message1_link}** to **{message2_link}**. This summary contains __{num_messages}__ messages.\n\n"
        )

    print(f"{ctx.author}'s summary: Grouped into {len(groups)} groups")
    print(f"{ctx.author}'s summary of {len(messages)} messages")

    # Start sending the summary
    info_str = "\n"
    info_str += f"Messages: ``{len(messages)}``\n"
    info_str += f"Mode: ``{mode}``\n"
    info_str += f"Language: ``{language}``\n"
    info_str += f"Thread: ``{thread}``\n"
    info_str += f"Total Input Tokens: ``{in_token_count}``\n"
    info_str += f"Model: ``{model['name']}``\n"
    info_str += f"By {ctx.author.mention}"
    embed = discord.Embed(title="Generated summary")
    embed.description = f"A `{len(groups)}-message` summary is being prepared..."
    embed.add_field(name="Command Arguments:", value=info_str)
    summary = Summary(INTRO_MESSAGE.format(ctx.guild.name, mode_prompt, language))

    try:
        send_message = None
        send_tts = None
        if thread:
            message = await ctx.followup.send(embed=embed)
            thread = await ctx.channel.create_thread(
                name=f"Summary by {ctx.author.display_name}, {len(messages)} messages",
                message=message,
            )
            send_message = lambda msg: thread.send(msg, suppress=True)
            send_tts = lambda f: thread.send(file=f, suppress=True)
        else:
            message = await ctx.followup.send(embed=embed, ephemeral=secret_mode)
            thread = channel
            send_message = lambda msg: ctx.followup.send(msg, ephemeral=secret_mode)
            send_tts = lambda f: ctx.followup.send(file=f, ephemeral=secret_mode)

        to_generate = [(groups[i], api_key, model["name"]) for i in range(len(groups))]
        with ThreadPool(len(groups)) as pool:
            responses = pool.starmap(summary.summarize, to_generate)

        for i in range(len(groups)):
            response = responses[i]

            # Send message in 2000 character chunks to prevent error
            block = headings[i] + response
            for chunk in textwrap.wrap(block, MESSAGE_CHUNK_SIZE, replace_whitespace=False):
                await send_message(chunk)

            tokens = get_tokens(response)
            user["out_token_count"] += tokens
            set_user(str(ctx.author), user)

            server["out_token_count"] += tokens
            set_server(ctx.guild.name, ctx.guild.id, server)

            print(f"{ctx.author}'s summary: Sent group {i+1}/{len(groups)}")

        # Send TTS summary
        try:
            result = summary.tts(ctx.author.display_name)
            await send_tts(result)
        except Exception as e:
            print(e)
            await send_message(ERROR.format(f"There was an error in generating the TTS summary: {e}"))

    except Exception as e:
        print(e)
        await message.edit(content=ERROR.format(e))





async def discord_command_summarize_all(ctx, time_period: str = "1d"):
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
    tag = "build-general"
    category = "Mentors Lounge"


    #categories = [category for category in ctx.guild.channels if isinstance(category, discord.CategoryChannel)]
    #await target_channel.send(f"Categories in {ctx.guild.name}: {[cat.name for cat in categories]}")

    status_message = target_channel.send(f"Summarizing...")

    if tag:
        channels = get_tagged_channels(ctx.guild, tag)
        criteria = "tag"
    elif category:
        channels = [channel for channel in ctx.guild.channels if channel.category.name == category]
        criteria = "category"
    else:
        channels = ctx.guild.channels
        criteria = "all"

    await target_channel.send(f"Summarizing all channels (criteria={criteria}) in {ctx.guild.name}...")


    for channel in channels:
        if channel.permissions_for(ctx.guild.me).read_messages and channel.name != "summary":
            await target_channel.send(content=f"Summarizing {channel.name}... {time_for_dating_back}")
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