import json
import sys
import requests

if len(sys.argv) != 2:
    print("Usage: python call-webhook1.py <config_file>")
    sys.exit(1)

config_file = sys.argv[1] # e.g. "src/static/martin.json"

# Read configuration values from martin.json
with open(config_file, 'r') as config_file:
    config = json.load(config_file)

url = config['bot_webhook_server']
headers = {"Content-Type": "application/json"}

print(f"For {url}, got: {config}") 

# Create payload by copying config and removing 'bot_webhook_server'
payload = {key: value for key, value in config.items() if key != 'bot_webhook_server'}


if 'target_webhook' not in payload or payload['target_webhook'] is None:
    print("No target webhook provided.")

if 'guild_ids' not in payload:
    print("No guild IDs provided.")

print(f"Sending {payload} to {url}")
 
# Define the URL and payload

headers = {"Content-Type": "application/json"}


# Make the POST request
response = requests.post(url, headers=headers, json=payload)

# Print the response
print(f"Status Code: {response.status_code}")
print(f"Response Body: {response.text}")
