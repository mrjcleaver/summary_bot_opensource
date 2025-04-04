import json
import requests
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from summary_for_webhook import summary_for_internal_call
from constants import FILE_FORMAT

import os

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

class TaskList:
    def __init__(self, default_payload):
        self.default_payload = default_payload
        self.scheduler = AsyncIOScheduler()
        self.SUMMARY_DIR = "summaries"
        self.periods = []

    def set_periods(self, periods):
        self.periods = periods

    def signal_handler(self, signal_number, frame): #TODO: implement this
        logging.info("Caught signal")
        self.scheduler.shutdown(wait=False)
        
    
    async def perform_job_using_internal_call(self, payload):
        actual_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"Actual Execution Time: {actual_time}")
        print(payload)

        diagnostic_channel_id = payload.get("diagnostic_channel_id", 0)
        if diagnostic_channel_id != 0:
            diagnostic_channel_id = int(diagnostic_channel_id)

        if payload.get("bot_webhook_server", None):
            logging.warning("bot_webhook_server is not None, but performing job using internal call")
            
        result = await(summary_for_internal_call(diagnostic_channel_id, payload))
        self.store_job_result(payload, result)

    """
        This function is called by the scheduler to perform the job. 
        The method returns the result of the job.

        It calls the perform_job_using_webhook method, calling the external API even for internally originated calls. 
        This is done as the Flask call to the webhook server is not blocking, and we can use the same code for both internal and external calls.
        
    """
    def perform_job(self, payload):
        #if payload.get("bot_webhook_server", None):
        return self.perform_job_using_webhook(payload)
        #else:
        #loop = asyncio.new_event_loop()  # TODO: consider if loops should be reused between calls
        #asyncio.set_event_loop(loop)  
        #return asyncio.run(self.perform_job_using_internal_call(payload))
        #loop.close()  
    
        


### WEBHOOK RELATED FUNCTIONS
    # This effectively calls ```summary_for_webhook.py:summary_for_webhook```

    def call_webhook_with_payload(self, url, payload):
        logging.debug(f"Sending {payload} to {url}")
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload)
        logging.debug(f"Status Code: {response.status_code}")
        logging.debug(f"Response Body: {response.text}")
        return response


    def perform_job_using_webhook(self, payload):
        actual_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logging.debug(f"Actual Time of Execution: {actual_time}")
        
        response = self.call_webhook_with_payload(payload['bot_webhook_server'], payload)

        if response.status_code != 200:
            result = f"Error: {response.status_code} {response.text}"
        else:
            result = response.text

        data = {}
        
        try:
            data = json.loads(result) 

            if data["message"]:
                message = data["message"]

        except json.JSONDecodeError:
            message = "Error decoding JSON response - Chances are, we passed too many tokens."
            logging.error(message)
            message = result
        

        self.store_job_result(payload, message) #TODO: think about name
        return message

    def default_filename_for_period(self, start, end):
        formatted_start = start.strftime('%Y-%m-%d')
        formatted_end = end.strftime('%Y-%m-%d')
        file_path = self.SUMMARY_DIR+os.sep + \
                                            f"{formatted_start}_{formatted_end}"+"."+FILE_FORMAT
        return file_path


    def default_filename_for_payload(self, payload):
        #if "document_id" in payload:
        #    return payload["document_id"]+"."+FILE_FORMAT #TODO change this to .md and

        if "starttime_to_summarize" in payload:
            starttime = payload["starttime_to_summarize"]
            formatted_start = starttime.split()[0] # date only.
        else:
            formatted_start = payload["start"].strftime('%Y-%m-%d')

        if "endtime_to_summarize" in payload:
            endtime = payload["endtime_to_summarize"]
            formatted_end = endtime.split()[0]  
        else:
            formatted_end = payload["end"].strftime('%Y-%m-%d')

        file_path = self.SUMMARY_DIR+os.sep + \
                                            f"{formatted_start}_{formatted_end}"+"."+FILE_FORMAT
        return file_path

    def store_job_result(self, payload, result):
        os.makedirs(self.SUMMARY_DIR, exist_ok=True)

        file_path = self.default_filename_for_payload(payload)
        # TODO: Think about document_id, can it be used in the filename if the format gets changed between runs?
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(result)

    def job_is_done(self, start, end):
        file_path = self.default_filename_for_period(start, end)
        exists = os.path.exists(file_path)
        logging.debug(f"Checking if {file_path} exists: {exists}")
        return exists

    """
    Returns the next job from the past to be done. If no job is due, returns None.
    """
    def get_next_catchup_job(self):
        now = datetime.now()
        logging.info(f"Current time: {now}")
        for start, end in self.periods:
            if self.job_is_done(start, end):
                # TODO: remove historical period from the list
                logging.info(f"Job {start}-{end} already done")                 
                # next
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
        now = datetime.now()
        future_jobs = []
        for start, end in self.periods:
            if end > now:
                future_jobs.append({
                    "start": start,
                    "end": end,
                    "trigger": CronTrigger(year=end.year, month=end.month, day=end.day, hour=end.hour, minute=end.minute, second=end.second)
                })
        return future_jobs
        
    

