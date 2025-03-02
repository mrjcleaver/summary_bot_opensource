# Description: This file contains the main function to queue jobs for the TaskList class.
#   """ 
#   Queue jobs for the TaskList class.
#   """
#

import os
import json
import threading
from time import sleep
from task_list import TaskList
from datetime import datetime, timedelta

import logging


# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("Starting job queue process")

default_payload = {
            "bot_webhook_server": "http://localhost:5000/webhook",
            "guild_ids": ["FRC 2609 - Beaverworx"],
            "channels_to_include": [
                "general", "elec-general", "mech-general", "programming-general"
            ],
            "channels_to_exclude": [],
            "diagnostic_channel_id": 1332451557530402877,
            "target_webhook": "",
            "google_folder_id": "",
            "ai_prompts": {
                "formatting_instructions": "Format my answer in HTML suitable for Atlassian Confluence Cloud. This includes never using ** to mark bold. Always use HTML to replace it if you see that in the text. Always check to make sure your output is well formatted. Keep any links to Discord messages",
                "context_prompt": "I’d like to ask you for a summary of a chat conversation. First, I will provide you with the context of the conversation so that you can better understand what it’s about, and then I will write the continuation, for which I will ask you to summarize and highlight the most important points. Include any links to Discord channels. Here is the context:",
                "recent_messages_prompt": "Now, please summarize the following conversation, using a h2 headers and a list of one level of nested bullet points whenever that makes sense. Pay attention to technical and design details. Highlight the most important elements or terms in bold. Include any links to Discord channels. Don't repeat the details of the conversation. Ignore people thanking each other. If I gave you no conversation points just say 'no messages in the time period'."
            }
        }

task_list = TaskList(default_payload)

def generate_job_periods(start_date, end_date):

    periods = []
    logging.debug(periods)

    current_date = start_date
    while current_date <= end_date:
        weekday = current_date.weekday()
        new_period = None
        if weekday == 3:  # Thursday
            new_period = (datetime.combine(current_date, datetime.min.time()), 
                            datetime.combine(current_date + timedelta(days=2), datetime.max.time().replace(microsecond=0)))
        elif weekday == 6:  # Sunday
            new_period = (datetime.combine(current_date, datetime.min.time()), 
                            datetime.combine(current_date + timedelta(days=3), datetime.max.time().replace(microsecond=0)))
        elif weekday == 2:  # Wednesday
            new_period = (datetime.combine(current_date, datetime.min.time()), 
                            datetime.combine(current_date + timedelta(days=1), datetime.max.time().replace(microsecond=0)))
        if new_period and new_period not in periods:
            periods.append(new_period)
            logging.debug(f"Added {new_period} to list")
        else:
            logging.debug(f"Skipping {new_period} as already in list")
        current_date += timedelta(days=1)

    return periods

def perform_catchup_and_queue_future_jobs():
    """
    Queue jobs for the TaskList class.
    """

    # Example usage
    start_date = datetime(2025, 1, 4)
    end_date = datetime(2025, 4, 5)
    task_list.set_periods(
        generate_job_periods(start_date, end_date)
    )

    next_catchup_job = task_list.get_next_catchup_job()

    while next_catchup_job:
        start, end = next_catchup_job["start"], next_catchup_job["end"]
        logging.info(f"Next job period: {start.strftime('%Y-%m-%d %H:%M:%S')} to {end.strftime('%Y-%m-%d %H:%M:%S')}")

        payload = task_list.default_payload.copy()
        payload['starttime_to_summarize'] = start.strftime('%Y-%m-%d %H:%M:%S')
        payload['endtime_to_summarize'] = end.strftime('%Y-%m-%d %H:%M:%S')
        payload['document_id'] = f"{start.strftime('%Y-%m-%d')}_to_{end.strftime('%Y-%m-%d')}"
        
        result = task_list.perform_job(payload)
        logging.debug(f"Result: {result}")

        next_catchup_job = task_list.get_next_catchup_job()
        logging.info(f"Next job: {next_catchup_job}")
        if next_catchup_job:
            print(f"Sleeping for 5 seconds")
            sleep(5)
        else:
            print("No more past jobs")

    # Schedule future jobs

    logger.info("Scheduling future jobs")
    future_jobs = task_list.get_future_jobs()

    for job in future_jobs:
        start, end = job["start"], job["end"]
        payload = task_list.default_payload.copy()
        payload['starttime_to_summarize'] = start.strftime('%Y-%m-%d %H:%M:%S')
        payload['endtime_to_summarize'] = end.strftime('%Y-%m-%d %H:%M:%S')
        payload['document_id'] = f"{start.strftime('%Y-%m-%d')}_to_{end.strftime('%Y-%m-%d')}"
        
        logging.info(f"Scheduling for {end} the future job running from {start} to {end}")
        task_list.scheduler.add_job(
            task_list.perform_job,
            'date',
            run_date=end,
            args=[payload]
        )

    # Print the jobs queued in the scheduler
    jobs = task_list.scheduler.get_jobs()
    for job in jobs:
        logger.debug(f"Job id: {job.id}, name: {job.name}, trigger: {job.trigger}")

async def print_jobs(
    ctx,
):
    
    jobs = task_list.scheduler.get_jobs()
    result = "\n".join(f"trigger: {job.trigger}" for job in jobs)
        
    await ctx.respond(f"**__Jobs__**:\n{result}", ephemeral=True)