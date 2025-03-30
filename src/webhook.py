# Handles incoming webhook requests,  Send response to a provided target webhook.

from datetime import datetime
import asyncio
import logging
import json

# Flask inbound
from flask import Flask, request

# Outbound
import requests
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

from constants import MESSAGE_CHUNK_SIZE, LOG_DIAGNOSTICS_TO_CHANNEL

# Flask setup
app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler()])

# Flask route to handle incoming webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Handle incoming webhook requests.
    This function processes incoming JSON payloads from a webhook, extracts relevant information,
    and performs various actions such as summarizing channels, logging diagnostic messages, and
    sending messages to a target webhook.
    The function expects the following keys in the incoming JSON payload:
    - "guild_ids": List of guild IDs to process (default: empty list).
    - "channels_to_summarize": List of channel IDs to summarize (default: empty list).
    - "channels_to_exclude": List of channel IDs to exclude from summarization (default: empty list).
    - "diagnostic_channel_id": ID of the diagnostic channel (default: 0).
    - "time_period": Time period for summarization (default: "1d").
    - "target_webhook": URL of the target webhook to send the summarized message (default: 0).
    Returns:
        tuple: A tuple containing a response message and an HTTP status code.
    """

    if app.bot:
        logging.info("Bot variable exists")

    # Parse the incoming JSON payload
    request_payload = request.json
    request_payload.pop('bot_webhook_server', None)





    if not request_payload:
        logging.info("No payload received.")
    else:
        # Extract useful information from the webhook payload
        diagnostic_channel_id = request_payload.get("diagnostic_channel_id", 0)
        if diagnostic_channel_id == 0:
            diagnostic_channel_id = int(diagnostic_channel_id)
        target_webhook = request_payload.get("target_webhook", 0)

        # Using the bot's loop to run the coroutine
        future = asyncio.run_coroutine_threadsafe(
            app.summary_func(diagnostic_channel_id),
            app.bot.loop
            )

        result = future.result()

        document_id = request_payload.get("document_id", 0)
        if document_id == 0:
            document_id = request_payload.get("starttime_to_summarize", "") + "-" + request_payload.get("endtime_to_summarize", "")
            
        if document_id:
            result = f"Summary for document {document_id}:\n{result}"
            request_payload["document_id"] = document_id
        else:
            logging.info("No document ID provided or constructable.")

        #log_diagnostic_message(result)

        if request_payload.get("google_folder_id", False):
            write_file_to_google_drive(result, request_payload),
        else:
            logging.info("No Google Folder ID provided.")

            
        if target_webhook:
            result = asyncio.run_coroutine_threadsafe(
                send_message_to_webhook(result, target_webhook, request_payload),
                app.bot.loop
            )
            logging.info(f"Sent message to target webhook {result}")
        else:  
            logging.info("No target webhook provided.")

        result = {
            "message": result,
            "status": 200
        }

        logging.debug(f"Result: {result}")
        return result


async def send_message_to_webhook(message, target_webhook, incoming_payload):
    """
    Send a message to a specified webhook URL.
    Args:
        message (str): The message content to send to the webhook.
        target_webhook (str): The URL of the target webhook.
        payload (dict): Additional payload to send with the message.
    Returns:
        None
    Logs diagnostic messages before and after sending the request. If no target webhook is provided, logs an info message and returns without sending the request.
    """

    if not target_webhook:
        logging.info(f"No target webhook provided for {incoming_payload}.")
        return

    await log_diagnostic_message(f"Sending {json.dumps(incoming_payload, indent=2)} to {target_webhook}")


    headers = {"Content-Type": "application/json"}
    payload = {
        "content": message,
        "timestamp": datetime.now().replace(microsecond=0).isoformat() + "Z",  # Remove microseconds
        "incoming_payload": incoming_payload
    }

    response = requests.post(target_webhook, headers=headers, json=payload)
    
    await log_diagnostic_message(f"Webhook response: {response.status_code}")

# Send a diagnostic message to Discord from the bot
async def log_diagnostic_message(message):
    """
    Send a diagnostic message to a specified Discord channel.
    Args:
        message (str): The diagnostic message content.
    Returns:
        None
    Logs the diagnostic message and sends it to the specified Discord channel in chunks if necessary.
    """
    channel_id = app.diagnostic_channel_id
    logging.info(f"Sending {message} to {channel_id}")

    if not LOG_DIAGNOSTICS_TO_CHANNEL:
        # If the diagnostics channel is not enabled, log the message and return
        logging.info(f"Diagnostic {message}")
        return

    channel = app.bot.get_channel(channel_id)

    message_chunks = [
        message[i:i + MESSAGE_CHUNK_SIZE] 
        for i in range(0, len(message), MESSAGE_CHUNK_SIZE)
    ]
    

    if channel:
        if message is None:
            await channel.send("No message provided.")
        else:
            try:
                for chunk in message_chunks:
                    await channel.send(chunk)
            except Exception as e:
                logging.error(f"Error sending message to channel {channel_id}: {e}")
                await channel.send(f"message about {channel_id} could not be sent: {e}")
    else:
        logging.info(f"Channel with ID {channel_id} not found.")

def write_file_to_google_drive(message, payload):
    """
    Write a file to Google Drive.
    Args:
        document_id (str): The ID of the document to write to.
        message (str): The message content to write to the document.
        payload (dict): Additional payload to write to the document.
    Returns:
        None
    Logs diagnostic messages before and after writing the file.
    """
    folder_id = payload.get("google_folder_id", "0")
    document_id = payload.get("document_id", "0")

    logging.info(f"Writing file to Google Drive for {document_id}")
    logging.info(f"Google Folder ID: {folder_id}")
    logging.debug(f"Payload: {json.dumps(payload, indent=2)}")

    if not folder_id:
        logging.error("No Google Folder ID provided.")
        return
    
    if not document_id:
        logging.error("No document ID provided")
        return


    # Write the message to a file
    file_path = f"{document_id}.txt"

    # Authenticate and create the PyDrive client
    gauth = GoogleAuth()
    gauth.LoadClientConfigFile("src/static/client_secrets.json")
    gauth.LocalWebserverAuth()  # Creates local webserver and automatically handles authentication.
    if gauth.credentials is None:
        logging.error("Google Authentication failed")
        return
    elif gauth.credentials.access_token_expired:
        logging.info("Google Access token expired, refreshing...")
        gauth.Refresh()
        logging.info("Google Token refreshed.")
    else:
        logging.info("Google Authentication successful.")
        
    
    drive = GoogleDrive(gauth)

    # Create a file and upload it to Google Drive
    gfile = drive.CreateFile({'title': file_path,
                              'parents': [{'id': folder_id}]
                              })
    gfile.SetContentString(message)
    gfile.Upload()

    logging.info(f"File {document_id}.txt uploaded to Google Drive")
