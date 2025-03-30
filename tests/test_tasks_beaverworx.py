import os
import sys
import warnings

os.environ['OPENAI_API_KEY'] = "NOT GOING TO BE USED ANYWAY AS WE STUB THE CALL"
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Add the src directory to the Python path
folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))

print(folder)
sys.path.append(folder)

import pytest
from datetime import datetime, timedelta
from apscheduler.triggers.cron import CronTrigger


@pytest.fixture
def mock_summary_for_internal_call():
    with patch('main.summary_for_internal_call', MagicMock()) as mock:
        yield mock



from task_list import TaskList
from unittest.mock import patch, MagicMock




@pytest.fixture
def task_list():
    # Set up a default payload and initialize the TaskList instance
    default_payload = {
        "diagnostic_channel_id": 12345,
        "bot_webhook_server": "http://example.com/webhook"
    }
    return TaskList(default_payload)

def test_get_future_jobs(task_list):
    # Set up test periods
    now = datetime.now()
    future_time_1 = now + timedelta(days=1)
    future_time_2 = now + timedelta(days=2)
    task_list.set_periods([(now, future_time_1), (now, future_time_2)])

    # Get future jobs
    future_jobs = task_list.get_future_jobs()

    # Verify the number of future jobs
    assert len(future_jobs) == 2

    # Verify the details of the first future job
    job_1 = future_jobs[0]
    assert job_1["start"] == now
    assert job_1["end"] == future_time_1
    assert isinstance(job_1["trigger"], CronTrigger)

    # Verify the details of the second future job
    job_2 = future_jobs[1]
    assert job_2["start"] == now
    assert job_2["end"] == future_time_2
    assert isinstance(job_2["trigger"], CronTrigger)

def test_save_and_load_task_list(task_list):
    # Set up test periods
    now = datetime.now()
    future_time_1 = now + timedelta(days=1)
    future_time_2 = now + timedelta(days=2)
    task_list.set_periods([(now, future_time_1), (now, future_time_2)])

    # Save the task list
    task_list.save_task_list()

    # Create a new TaskList instance and load the task list
    new_task_list = TaskList(task_list.default_payload)
    new_task_list.load_task_list()

    # Verify the loaded periods
    assert new_task_list.periods == [(now, future_time_1), (now, future_time_2)]