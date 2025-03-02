from openai import OpenAI
import os

from async_lru_cache import AsyncLRUCache
import logging

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

client = OpenAI(
    api_key=api_key,  # This is the default and can be omitted
)

cache = AsyncLRUCache()
class OpenAISummarizer:
    def __init__(self):
        """
        Initializes the OpenAISummarizer instance.

        Sets the initial number of API calls to 0 and configures the logging
        to the DEBUG level.
        """
        self.calls = 0
        logging.basicConfig(level=logging.INFO)

    async def get_summary_from_ai(self, owner_of_messages, channel_messages, ai_prompts={}):
        """
        Asynchronously retrieves a summary for the given messages. If a cached summary exists, it returns the cached result.
        Otherwise, it calls the OpenAI summarization API, caches the result, and returns it.

        Args:
            owner_of_messages (list): A list of message owners.
            channel_messages (list): A list of messages from the channel.
            ai_prompts (dict): A dictionary of AI prompts to use for summarization.

        Returns:
            str: The summary of the provided messages.
        """
        key = (tuple(owner_of_messages), tuple(channel_messages))
        cached_result = await cache.get(key)
        if cached_result is not None:
            return cached_result
        else:
            result = await self.call_openai_summarize(owner_of_messages, channel_messages, ai_prompts)
            #await self.debug_summary_to_file(result, owner_of_messages, channel_messages)
            await cache.set(key, result)
            return result

    async def call_openai_summarize(self, owner_of_messages, messages_in_channel, ai_prompts):
        """
        Asynchronously calls the OpenAI API to summarize a chat conversation.
        Args:
            messages_context (str): The context of the conversation to provide background information.
            messages_in_channel (str): The actual conversation messages that need to be summarized.
        Returns:
            str: The summarized conversation, formatted in HTML if specified.
        Raises:
            Exception: If there is an issue with the OpenAI API call.
        Note:
            - The function logs the call number, context, and the conversation to be summarized.
            - The prompt can be formatted for Atlassian Confluence Cloud if needed.
            - The response is stripped of any markdown enclosures before being returned.
        """
        self.calls += 1
        logging.basicConfig(level=logging.INFO)
        logging.info("Call number: %s", self.calls)
        logging.info("Owners of messages: %s", owner_of_messages)
        #logging.debug("Messages in channel: %s", messages_in_channel)

        prompt0 = ai_prompts.get("formatting_instructions", "Format my answer in HTML suitable for Atlassian Confluence Cloud. This includes never using ** to mark bold. Always use HTML to replace it if you see that in the text.")
        prompt1 = ai_prompts.get("context_prompt", "I’d like to ask you for a summary of a chat conversation. First, I will provide you with the context of the conversation so that you can better understand what it’s about, and then I will write the continuation, for which I will ask you to summarize and highlight the most important points. Here is the context:")
        prompt2 = ai_prompts.get("recent_messages_prompt","Now, please summarize the following conversation, highlighting the most important elements in bold. Include the instructions I gave you.")
        
        ai_prompt = f"{prompt0}: \n\n"+ \
                    f"{prompt1}: \n\n"+ \
                    f"{'-' * 10}\n"+ \
                    f"{owner_of_messages}\n"+ \
                    f"{'-' * 10}\n\n"+ \
                     ">>>"+ \
                    f"{prompt0}: \n\n"+ \
                    f"{prompt2}:\n\n\n"+ \
                    f"{messages_in_channel}"
        
        #logging.debug(ai_prompt)

        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "assistant",
                        "content": ai_prompt
                    }
                ],
                model="gpt-4o",
            )

            response = chat_completion.choices[0].message.content

            # Remove markdown enclosure
            if response.startswith("```html") and response.endswith("```"):
                response = response[7:-3]
                logging.debug("Stripped ```html at start and ```")

            if response.startswith("```") and response.endswith("```"):
                response = response[3:-3]
                logging.debug("Stripped ``` at start and end")

            #logging.debug(response)
            return response
        except OpenAI.error.RateLimitError as e:
            logging.error(f"Rate limit exceeded: {e}")
            raise

    async def debug_summary_to_file(self, summary, owner_of_messages, messages_in_channel, folder_path="summaries", file_path=None):
        """
        Asynchronously writes a summary and its context to a file for debugging purposes.
        
        Args:
            summary (str): The summary text to be written to the file.
            messages_context (str): The context of the conversation.
            messages_in_channel (str): The actual conversation messages.
            folder_path (str, optional): The path to the folder where the summary file will be stored. Defaults to "summaries".
            file_path (str, optional): The path to the file where the summary will be written. If not provided, a default path will be used.

        Returns:
            None
        """
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        if file_path is None:
            file_path = os.path.join(folder_path, f"summary_{self.calls}.txt")
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write("Context:\n")
            file.write(owner_of_messages + "\n\n")
            file.write("Messages:\n")
            file.write(messages_in_channel + "\n\n")
            file.write("Summary:\n")
            file.write(summary)
        
        logging.info("Summary written to %s", file_path)

    

summarizer = OpenAISummarizer()
