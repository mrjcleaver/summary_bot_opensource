import json
import sys
import requests
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta

import signal
import os

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

class TaskList:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.default_payload = {
            "bot_webhook_server": "http://localhost:5000/webhook",
            "guild_ids": ["FRC 2609 - Beaverworx"],
            "channels_to_include": [
                "general", "elec-general", "mech-general", "programming-general"
            ],
            "channels_to_exclude": [],
            "diagnostic_channel_id": 1332451557530402877,
            "target_webhook": "https://hooks.zapier.com/hooks/catch/30615/2f3lh4c/",
            "ai_prompts": {
                "formatting_instructions": "Format my answer in HTML suitable for Atlassian Confluence Cloud. This includes never using ** to mark bold. Always use HTML to replace it if you see that in the text. Always check to make sure your output is well formatted. Keep any links to Discord messages",
                "context_prompt": "I’d like to ask you for a summary of a chat conversation. First, I will provide you with the context of the conversation so that you can better understand what it’s about, and then I will write the continuation, for which I will ask you to summarize and highlight the most important points. Include any links to Discord channels. Here is the context:",
                "recent_messages_prompt": "Now, please summarize the following conversation, using a h2 headers and a list of one level of nested bullet points whenever that makes sense. Pay attention to technical and design details. Highlight the most important elements or terms in bold. Include any links to Discord channels. Don't repeat the details of the conversation. Ignore people thanking each other. If I gave you no conversation points just say 'no messages in the time period'."
            }
        }
        self.SUMMARY_DIR = "summaries"
        self.periods = []

    def signal_handler(self, signal_number, frame):
        logging.info("Caught signal")
        self.scheduler.shutdown(wait=False)

    def generate_job_periods(self, start_date, end_date):

        logging.debug(self.periods)

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
            if new_period and new_period not in self.periods:
                self.periods.append(new_period)
                logging.debug(f"Added {new_period} to list")
            else:
                logging.debug(f"Skipping {new_period} as already in list")
            current_date += timedelta(days=1)

        
        

    def post_period(self, url, payload):
        print(f"Sending {payload} to {url}")
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")

    def retrospective_job_to_call_webhook(self, expected_run_time, payload):
        actual_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"Scheduled Time: {expected_run_time}, Actual Execution Time: {actual_time}")
        print(payload)
        self.post_period(payload['bot_webhook_server'], payload)

    def current_job_to_call_webhook(self, payload):
        actual_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"Actual Execution Time: {actual_time}")
        print(payload)
        self.post_period(payload['bot_webhook_server'], payload)
        

    def schedule_webhook_calls(self):
    
        now = datetime.datetime.now()
        soon = now + datetime.timedelta(minutes=1)
        test_hr = soon.hour
        test_min = soon.minute
        cron_trigger = CronTrigger(hour=test_hr, minute=test_min)
        expected_run_time = cron_trigger.get_next_fire_time(None, now).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Queuing {expected_run_time}")
        payload = self.default_payload
        payload['endtime_to_summarize'] = expected_run_time
        payload['time_period'] = '3d'
        self.scheduler.add_job(
            self.retrospective_job_to_call_webhook,
            trigger=cron_trigger,
            args=[expected_run_time, payload],
            id=f"day_task"
        )

    def file_for_period(self, start, end):
        return self.SUMMARY_DIR+os.sep+f"{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.txt"

    def store_job_result(self, start, end, result):
        os.makedirs(self.SUMMARY_DIR, exist_ok=True)
        file_path = self.file_for_period(start, end)
        with open(file_path, "w") as file:
            file.write(result)

    def job_is_done(self, start, end):
        file_path = self.file_for_period(start, end)
        exists = os.path.exists(file_path)
        logging.debug(f"Checking if {file_path} exists: {exists}")
        return exists

    """
    Returns the next job from the past to be done. If no job is due, returns None.
    """
    def get_next_past_job(self):
        now = datetime.now()
        logging.info(f"Current time: {now}")
        for start, end in self.periods:
            if self.job_is_done(start, end):
                # TODO: remove the period from the list
                logging.info(f"Job {start}-{end} already done")                 
                next
            else:
                logging.info(f"Checking {start}-{end}")
                if now > end:
                    logging.info(f"Please do past job {start}-{end}")
                    return {"start": start, "end": end}
                else:
                    logging.info(f"nothing due as end job {end} later than now {now} ")
                    return None
                
        logging.debug("Shouldn't reach here")

    def get_future_jobs(self):
        
        pass

