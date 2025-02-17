Last update: 1/13/2025

# Summary Bot - Opensource
Summary Bot's code, opensourced. This is a distinct repository from the one in active development as we have loads of private information saved in git history.

Since Feb 2025, it contains elements of  `discord-summarizer-bot`, another bot designed to provide concise summaries of channel conversations using OpenAI's GPT-4. 

## Features

- Summarizes Discord channel messages over a specified time period.
- Uses OpenAI's GPT-4 for accurate and coherent summaries.
- Easy to deploy and use within any Discord server.

Interactive Use
- TODO: outline summary_bot's features as listed on https://top.gg/bot/1058568749076185119



Webhook Use:
- The server will respond to incoming requests to send a response to a target webhook.
- We use this to create summaries of discord content onto a remote Confluence server as a new page or blog post.

## Installation

To install and run `discord-summarizer-bot` on your server, follow these steps:

1. Clone the repository:
   ```bash

   git clone https://github.com/ArjunSahlot/summary_bot_opensource.git
   ```
2. Install the required dependencies:
   ```bash

   cd summary_bot_opensource
   pip install poetry
   poetry install
   ```
3. To get your `summary_bot_opensource` up and running, you'll need to configure your API keys as follows:
   1. OpenAI API Key 
      - Go to [OpenAI's API platform](https://beta.openai.com/signup/) and sign up for an account if you haven't already. 
      - Once you have an account, navigate to the API section and generate a new API key. 
      - Set the API key as an environment variable:
        ```bash
        export OPENAI_API_KEY='your_openai_api_key'
   2. Discord Bot Token
      - Head over to the [Discord Developer Portal](https://discord.com/developers/applications).
      - Create a new application and add a bot to it.
      - Under the "Bot" section, find and copy your bot token.
      - Set the token as an environment variable:
         ```bash
         export DISCORD_TOKEN='your_discord_bot_token'
4. Confirm that the environment variables are set up:
    - `OPENAI_API_KEY`: Your OpenAI API key.
    - `DISCORD_TOKEN`: Your Discord bot token.

5. Run the bot:
   ```bash
   python bot.py

## Usage

See https://top.gg/bot/1058568749076185119


## Webhook Usage

The webhook is useful where you want the summary to somewhere elsewhere than Discord. Our use case was to summarize to Atlassian Confluence.

In Zapier
* Create a Zap
* Component 1:
 * Webhook
 * Get the Catch URL, e.g. "https://hooks.zapier.com/hooks/catch/1111/2f3l111/"
* Component 2:
 * Whatever you like, e.g. post to another target. e.g. a Discord channel webhook, or whatever 

In test
* Copy src/static/webhook-server-example.json your-example.json
* Edit  

{
    "bot_webhook_server": "http://localhost:5000/webhook",

    "guild_ids": ["your guild"],
    "channels_to_include": [
        "general", "elec-general", "mech-general", "programming-general"
    ],
    "channels_to_exclude": [],
    "time_period": "5d",
    "starttime_to_summarize": "2025-02-10",
    "endtime_to_summarize": "2025-02-15",

    "diagnostic_channel_id": 1332451557530402877,
    "target_webhook": "https://hooks.zapier.com/hooks/catch/11111/11111/",
    "ai_prompts" : {
        "formatting_instructions": "Format my answer in HTML suitable for Atlassian Confluence Cloud. This includes never using ** to mark bold. Always use HTML to replace it if you see that in the text. Always check to make sure your output is well formatted. Keep any links to Discord messages",
        "context_prompt": "I’d like to ask you for a summary of a chat conversation. First, I will provide you with the context of the conversation so that you can better understand what it’s about, and then I will write the continuation, for which I will ask you to summarize and highlight the most important points. Include any links to Discord channels. Here is the context:",
        "recent_messages_prompt": "Now, please summarize the following conversation, using a h2 headers and a list of one level of nested bullet points whenever that makes sense. Pay attention to technical and design details. Highlight the most important elements or terms in bold. Include any links to Discord channels. Don't repeat the details of the conversation. Ignore people thanking each other. If I gave you no conversation points just say 'no messages in the time period'."
    }
        
}

Notes:
* endtime_to_summarize defaults to now
* either starttime_to_summarize or time_period is needed. The default time_period is 1d



## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".



## License

Distributed under the MIT License. See `LICENSE` for more information.


## Acknowledgments

- [OpenAI](https://openai.com/)
- [Discord.py](https://github.com/Rapptz/discord.py)
- [discord-summarizer-bot](https://github.com/nybble16/discord-summarizer-bot)


## Testing

You can test for free manually, rather than using Zapier. 

In a command window
* cd test
* python.exe call-webhook1.py src/static/your-example.json

Expected results
* the channel number in your-example.json should be notified with the summary message
* any target_webhook should be called with the summary message



## Developing and Debugging

In vscode:
* create a launch.json file
 * "env": {
                "OPENAI_API_KEY": "",
                "DISCORD_TOKEN" : ""
            } 
* select main.py
* start debugger



Diagnosis
* Increase the logging levels.
* summary_for_webhook is capable of writing a file per channel being summarized if you want to check it working. These files will be written to `summaries/`