import logging
logging.basicConfig(level=logging.INFO)

logging.info("Starting main.py")
import os

is_fly = os.getenv("FLY_ALLOC_ID") is not None
if is_fly:
    logging.info("Running on Fly.io")
    import sentry_sdk
    from flask import Flask #SMELL

    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:        
        sentry_sdk.init(
            dsn=sentry_dsn,
            # Add data like request headers and IP for users,
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
        )
        logging.info(f"Sentry enabled on {sentry_dsn}")
    else:
        logging.warning("No Sentry DSN found. Not enabling Sentry.")

if os.getenv("DEBUGPY_ENABLE") == "true":
    logging.info("Enabling debug via IDE")
    import debug
    

import json
import threading

import discord 
from discord import Option

from openai_summarizer import OpenAISummarizer

from dotenv import load_dotenv
load_dotenv()

from summary import summary, fromtosummary, unreadsummary, discord_command_summarize_all
from deployment import server
from constants import *
from events import *
from commands import *
from task_list import TaskList
from tasks_beaverworx import perform_catchup_and_queue_future_jobs,print_jobs
from time import sleep

from webhook import *
from summary_for_webhook import summary_for_webhook 
from tagged_channels import *

intents = discord.Intents.default()
bot = discord.Bot(intents=intents)
summarizer = OpenAISummarizer()



"""
The main entry point for the bot. This script starts the bot and sets up the necessary event listeners and commands.
"""

# Set up the Flask app for the Webhook
def run_webhook(bot, summary_func):
    app.bot = bot  # Attach the bot instance to the Flask app
    app.summary_func = summary_func  # Attach the summary function to the Flask app
    app.run(host="0.0.0.0", port=8080)  # Ensure the app listens on 0.0.0.0:8080


# Run the Webhook Flask app in a thread to avoid blocking the bot
webhook_server_thread = threading.Thread(target=run_webhook, 
                                         args=(bot,
                                               summary_for_webhook)
                                        )
webhook_server_thread.start()


tasklist_thread = threading.Thread(target=perform_catchup_and_queue_future_jobs)
#    logger.info("Starting the scheduler")
#    task_list.scheduler.start()
#logger.info("Scheduling future task list")
tasklist_thread.start()


async def on_ready():
    logging.info(f"{bot.user.name} is ready")
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.permissions_for(guild.me).view_channel:
                logging.debug("Bot has access to: %s", channel.name)


@bot.event
async def on_error(error, *args, **kwargs):
    if isinstance(args[0], discord.HTTPException) and args[0].status == 429:
        # Rate limit encountered
        retry_after = args[0].headers.get("Retry-After")
        if not retry_after:
            retry_after = 5
            
        logging.warning("Rate limit encountered. Retrying after %s seconds.", retry_after)
        await asyncio.sleep(retry_after)  # Fallback to a reasonable delay if Retry-After is not provided
    else:
        ctx = args[0]
#        if isinstance(error,  commands.CommandInvokeError): #TODO: Check if this is the correct error
#            await ctx.send(error.original)
#        elif isinstance(error, commands.CommandError): #TODO: Check if this is the correct error
#            await ctx.send(str(error))

bot.event(on_ready)
bot.event(on_guild_join)
bot.event(on_guild_remove)

bot.slash_command(name="summary", description="Get a summary of the last messages in this channel")(summary)
bot.slash_command(name="fromtosummary", description="Get a summary from a certain time to a certain time")(fromtosummary)
bot.slash_command(name="unreadsummary", description="Get a summary of all the messages after your last sent message")(unreadsummary)

bot.slash_command(name="setregion", description="Set your region (required for from/to time)")(set_region)
bot.slash_command(name="setlanguage", description="Set your language for future summaries")(set_language)
bot.slash_command(name="setthread", description="Choose whether or not you want to use a thread for summaries")(set_thread)

bot.slash_command(name="checkserverkey", description="Check whether or not the server has a set API key")(check_server_key)
bot.slash_command(name="setapikey", description="Set your OpenAI API key to use with the bot")(set_api_key)
bot.slash_command(name="removeapikey", description="Remove your OpenAI API key")(remove_api_key)
bot.slash_command(name="setmodel", description="Set the OpenAI model to use for future summaries")(set_model)

bot.slash_command(name="addmode", description="Add a mode to use for future summaries")(add_mode)
bot.slash_command(name="removemode", description="Remove an existing mode")(remove_mode)
bot.slash_command(name="listmodes", description="List your existing modes")(list_modes)

bot.slash_command(name="mycost", description="Checkout how much you have cost Summary Bot!")(my_cost)
bot.slash_command(name="servercost", description="Checkout how much this server has cost Summary Bot!")(server_cost)

bot.slash_command(name="developermode", description="Enter developer mode!")(developer_mode)
bot.slash_command(name="costlyusers", description="Developer only!")(costly_users)
bot.slash_command(name="costlyservers", description="Developer only!")(costly_servers)

bot.slash_command(name="ping", description="Check the bot's latency")(ping)
bot.slash_command(name="update", description="What's new in the latest update")(update)
bot.slash_command(name="help", description="Get help with the bot")(help)
bot.slash_command(name="guide", description="Guide to summary bot")(guide)
bot.slash_command(name="vote", description="Vote for the bot!")(vote)
bot.slash_command(name="invite", description="Invite the bot to your server")(invite)
bot.slash_command(name="info", description="Info about the bot")(info)

bot.slash_command(name="summarize_all", description="Summarize all messages from all channels")(discord_command_summarize_all)
bot.slash_command(name="tagged", description="Find channels based on tags in their topics")(tagged_channels)

bot.slash_command(name="print_jobs", description="Print the current jobs in the queue")(print_jobs)
#bot.slash_command(name="cancel_jobs", description="Cancel all jobs in the queue")(cancel_jobs)                                                                                  
#bot.slash_command(name="cancel_job", description="Cancel a specific job in the queue")(cancel_job)
#bot.slash_command(name="queue_jobs", description="Queue jobs for the TaskList class")(queue_jobs)
#bot.slash_command(name="run_jobs", description="Run the jobs in the queue")(run_jobs)
#bot.slash_command(name="clear_jobs", description="Clear the jobs in the queue")(clear_jobs)
#bot.slash_command(name="print_future_jobs", description="Print the future jobs in the queue")(print_future_jobs)
#bot.slash_command(name="print_past_jobs", description="Print the past jobs in the queue")(print_past_jobs)

@bot.slash_command(name="sync", description="Manually sync commands")
async def sync(ctx: discord.ApplicationContext):
    await bot.sync_commands()
    await ctx.respond("✅ Slash commands synced!", ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=server.serve_forever).start()
    logging.info(f"Server started on port {server.server_address} {server.socket}")
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logging.error("No token found in environment variables. Exiting.")
        exit(1)
    
    bot.run(token)
else:
    logging.error("Main called outside of direct call.")

