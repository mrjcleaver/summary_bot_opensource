"""
This module contains functions to manage job scheduling and execution for the Beaverworx bot. 
It includes functionality to generate job periods based on specific weekday rules, queue jobs 
for execution, and schedule future jobs.
## Key Features:
1. **Job Period Generation**:
    - Generates job periods based on the weekday of the current date:
      - **Thursday**: Creates a period from Thursday to Saturday.
      - **Sunday**: Creates a period from Sunday to Wednesday.
      - **Wednesday**: Creates a period from Wednesday to Thursday.
2. **Catchup and Future Job Management**:
    - Queues and executes past jobs.
    - Schedules future jobs for execution at specified times.
3. **Job Printing**:
    - Provides functionality to print catchup jobs, future jobs, and scheduled jobs.
4. **Programming-General Summary Scheduling**:
    - Schedules a recurring job to summarize the "programming-general" channel every Monday at 5 PM.
## Usage:
This module is designed to be called from `main.py`. Ensure that `main.py` initializes and invokes 
the appropriate functions from this module to manage job scheduling and execution.
## Dependencies:
- `apscheduler` for job scheduling.
- `task_list.TaskList` for managing tasks.
- `datetime` and `timedelta` for date and time manipulation.
- `json` for handling payload configurations.
- `logging` for logging events and debugging information.
## Functions:
- `generate_job_periods(start_date, end_date)`: Generates job periods based on weekday rules.
- `perform_catchup_and_queue_future_jobs()`: Manages catchup jobs and schedules future jobs.
- `print_jobs(ctx)`: Prints details of catchup, future, and scheduled jobs.
- `schedule_programming_general_summary()`: Schedules a recurring job for the "programming-general" channel.
## Notes:
- Ensure that the `static/beaverworkx_payload.json` file exists and contains the default payload configuration.
- This module relies on the `TaskList` class for task management and scheduling.
# tasks_beaverworx.py
# This module contains functions to manage job scheduling and execution for the Beaverworx bot.
# It includes functionality to generate job periods based on specific weekday rules,

# The periods are determined based on the weekday of the current date:
- Thursday: Creates a period from Thursday to Saturday.
- Sunday: Creates a period from Sunday to Wednesday.
- Wednesday: Creates a period from Wednesday to Thursday.
Args:
    start_date (datetime): The starting date of the range.
    end_date (datetime): The ending date of the range.
Returns:
    list: A list of tuples, where each tuple contains two datetime objects representing
          the start and end of a job period.
""" 

import logging
from time import sleep
from task_list import TaskList
from datetime import datetime, timedelta
from calendar import THURSDAY, SUNDAY, WEDNESDAY
import json

from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging = logging.getLogger(__name__)

logging.info("Starting job queue process")

# TODO: implement collection_name in saved file name.
default_payload = json.load(open("/app/src/static/beaverworx_payload.json", "r"))
task_list = TaskList(default_payload)

# Set up the scheduler

def generate_job_periods(start_date, end_date):

    periods = []
    logging.debug(periods)

    current_date = start_date
    while current_date <= end_date:
        weekday = current_date.weekday()
        new_period = None
        if weekday == THURSDAY:  
            new_period = (datetime.combine(current_date, datetime.min.time()), 
                            datetime.combine(current_date + timedelta(days=2), datetime.max.time().replace(microsecond=0)))
        elif weekday == SUNDAY:
            new_period = (datetime.combine(current_date, datetime.min.time()), 
                            datetime.combine(current_date + timedelta(days=3), datetime.max.time().replace(microsecond=0)))
        elif weekday == WEDNESDAY:
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
    Do them if they are in the past
    Queue future jobs to be done in the future.
    """

    # Example usage
    start_date = datetime(2025, 1, 4)
    end_date = datetime(2025, 4, 5)
    sleep_seconds = 60
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
            logging.debug(f"Sleeping for {sleep_seconds} seconds")
            sleep(sleep_seconds)
        else:
            logging.info("No more past jobs")

    # Schedule future jobs

    logging.info("Scheduling future jobs")
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
        logging.debug(f"Job id: {job.id}, name: {job.name}, trigger: {job.trigger}")

# TODO consider if this bot method should be in the task_list class or elsewhere.
async def print_jobs(ctx):
    try:
        await ctx.respond("Printing jobs", ephemeral=True)

        await ctx.respond("# Jobs\n", ephemeral=True)

        catchup_jobs = task_list.get_catchup_jobs()
        await ctx.respond(f"**__Catchup Jobs__**:\n{catchup_jobs}", ephemeral=True)

        future_jobs = task_list.get_future_jobs()
        await ctx.respond(f"**__Future Jobs__**:\n{future_jobs}", ephemeral=True)

        scheduled_jobs = task_list.scheduler.get_jobs()
        await ctx.respond(f"**__Scheduled Jobs__**:\n{scheduled_jobs}", ephemeral=True)

        jobs = catchup_jobs + future_jobs + scheduled_jobs

        result = "\n".join(f"trigger: {job.trigger}" for job in jobs)
            
        await ctx.respond(f"**__Jobs__**:\n{result}", ephemeral=True)
    except Exception as e:
        logging.error(f"Error in print_jobs: {e}")
        await ctx.respond(f"An error occurred: {e}", ephemeral=True)
    


def schedule_programming_general_summary():
    """
    Schedule a job to summarize the programming-general channel every Monday at 5pm.
    """

    payload = task_list.default_payload.copy()
    payload['channels_to_include'] = ["programming-general"]
    payload['document_id'] = "programming_general_summary"

    trigger = CronTrigger(day_of_week='mon', hour=17, minute=0)
    task_list.scheduler.add_job(
        task_list.perform_job,
        trigger,
        args=[payload],
        id='programming_general_summary'
    )


if __file__ == "__main__":
    # Example usage of the functions
    start_date = datetime.now()
    end_date = start_date + timedelta(days=7)

    # Generate job periods
    periods = generate_job_periods(start_date, end_date)
    logging.info(f"Generated job periods: {periods}")

    # Perform catchup and queue future jobs
    perform_catchup_and_queue_future_jobs()

    # Print jobs (example context object)
    class MockContext:
        async def respond(self, message, ephemeral=False):
            print(message)

    ctx = MockContext()
    print_jobs(ctx)



