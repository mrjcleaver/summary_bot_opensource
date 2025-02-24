import os
import json
import threading

import discord 
from discord import Option

from openai_summarizer import OpenAISummarizer

from dotenv import load_dotenv
load_dotenv()

from summary import summary, fromtosummary, unreadsummary
from deployment import server
from constants import *
from events import *
from commands import *
from task_list import TaskList
from time import sleep


intents = discord.Intents.default()
bot = discord.Bot(intents=intents)
summarizer = OpenAISummarizer()


from webhook import *
from summary_for_webhook import summary_for_webhook 


# Run Flask in a separate thread
def run_flask(bot, summary_func):
    app.bot = bot  # Attach the bot instance to the Flask app
    app.summary_func = summary_func  # Attach the summary function to the Flask app
    app.run(host="0.0.0.0", port=5000)  # Set host and port for the Flask server


# Run the Flask app in a thread to avoid blocking the bot
flask_thread = threading.Thread(target=run_flask, 
                                args=(bot,summary_for_webhook))
flask_thread.start()


async def on_ready():
    print(f"{bot.user.name} is ready")
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.permissions_for(guild.me).view_channel:
                logging.info("Bot has access to: %s", channel.name)


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



if __name__ == "__main__":
    #threading.Thread(target=server.serve_forever).start()
    print("Server started on port 8000")

    #bot.run(os.getenv("DISCORD_TOKEN"))



    # Example usage
    task_worker = TaskList()
    start_date = datetime(2025, 1, 4)
    end_date = datetime(2025, 4, 5)
    task_worker.generate_job_periods(start_date, end_date)

    next_past_job = task_worker.get_next_past_job()

    while next_past_job:
        start, end = next_past_job["start"], next_past_job["end"]
        print(f"Next job period: {start.strftime('%Y-%m-%d %H:%M:%S')} to {end.strftime('%Y-%m-%d %H:%M:%S')}")

        payload = task_worker.default_payload.copy()
        payload['starttime_to_summarize'] = start.strftime('%Y-%m-%d %H:%M:%S')
        payload['endtime_to_summarize'] = end.strftime('%Y-%m-%d %H:%M:%S')
        
        
        task_worker.current_job_to_call_webhook(payload)
        result = f"Processed job from {start} to {end}"
        task_worker.store_job_result(start, end, result)
        next_past_job = task_worker.get_next_past_job()
        print(f"Next job: {next_past_job}")
        if next_past_job:
            print(f"Sleeping for 5 seconds")
            sleep(5)
        else:
            print("No more past jobs")

    # Schedule future jobs

    task_worker.scheduler.start()