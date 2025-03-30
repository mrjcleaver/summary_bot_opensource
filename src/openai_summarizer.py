from openai import OpenAI
import os
from async_lru_cache import AsyncLRUCache
import logging

logging.basicConfig(level=logging.DEBUG)

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

    async def get_cached_summary_from_ai(self, owner_to_messages, channel_messages, ai_prompts):     
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
        if ai_prompts is None:
           ai_prompts = {}
        key = (tuple(owner_to_messages), tuple(channel_messages))
        cached_result = await cache.get(key)
        if cached_result is not None:
            return cached_result
        else:
            result = await self.call_openai_summarize(owner_to_messages, channel_messages, ai_prompts)
            #await self.debug_summary_to_file(result, owner_of_messages, channel_messages)
            await cache.set(key, result)
            return result

    async def call_openai_summarize(self, owner_to_messages, messages_in_channel, ai_prompts):
        """
        :param owner_to_messages: The context of the conversation to provide background information.
        :type owner_to_messages: str
        :param messages_in_channel: The actual conversation messages that need to be summarized.
        :type messages_in_channel: str
        :param ai_prompts: Dictionary containing various AI prompts for formatting and context.
        :type ai_prompts: dict
        :return: The summarized conversation, formatted in HTML if specified.
        :rtype: str
        :raises Exception: If there is an issue with the OpenAI API call.
        .. note::
        Asynchronously calls the OpenAI API to summarize a chat conversation.
        Note:
            - The function logs the call number, context, and the conversation to be summarized.
            - The prompt can be formatted for Atlassian Confluence Cloud if needed.
            - The response is stripped of any markdown enclosures before being returned.
        """
        self.calls += 1

        logging.info("Call number: %s", self.calls)
        logging.debug("Owners:messages: %s", owner_to_messages)
        #logging.debug("Messages in channel: %s", messages_in_channel)

        prompt0 = ai_prompts.get("formatting_instructions", "FFormat my answer in Markdown.")
        prompt1 = ai_prompts.get("context_prompt", "I’d like to ask you for a summary of a chat conversation. First, I will provide you with the context of the conversation so that you can better understand what it’s about, and then I will write the continuation, for which I will ask you to summarize and highlight the most important points. Here is the context:")
        prompt2 = ai_prompts.get("recent_messages_prompt","Now, please summarize the following conversation, highlighting the most important elements in bold. Include the instructions I gave you.")
        
        ai_prompt = f"{prompt0}: \n\n"+ \
                    f"{prompt1}: \n\n"+ \
                    f"{'-' * 10}\n"+ \
                    f"{owner_to_messages}\n"+ \
                    f"{'-' * 10}\n\n"+ \
                     ">>>"+ \
                    f"{prompt0}: \n\n"+ \
                    f"{prompt2}:\n\n\n"+ \
                    f"{messages_in_channel}"
        
        # TODO: implement MODES and INTRO_MESSAGE
        #mode = "standard"
        #language = "English"
        #mode_prompt = MODES.get(mode)
        #ai_prompt = INTRO_MESSAGE.format("Guild", mode_prompt, language)


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
            
        # TODO: decide whether to use httpx instead of the OpenAI Python client library to capture the headers
        #    await self.debug_openai_response_headers(headers)

            return response
        except OpenAI.error.RateLimitError as e:
            logging.error(f"Rate limit exceeded. Retry after {e.headers.get('retry-after', 'unknown')} seconds.")

            raise


    async def debug_openai_response_headers(self, headers):
        """
        To get the response headers from the chat_completion call in the call_openai_summarize method, you would need to access the headers from the response object. 
        However, the OpenAI Python client library does not directly expose response headers. You would need to modify the library or use a lower-level HTTP client like requests or httpx to capture the headers.
        """
        print("Rate Limit Info:")
        print(f"Requests Allowed: {headers.get('x-ratelimit-limit-requests')}")
        print(f"Requests Remaining: {headers.get('x-ratelimit-remaining-requests')}")
        print(f"Requests Reset Time: {headers.get('x-ratelimit-reset-requests')}")
        print(f"Tokens Allowed: {headers.get('x-ratelimit-limit-tokens')}")
        print(f"Tokens Remaining: {headers.get('x-ratelimit-remaining-tokens')}")
        print(f"Tokens Reset Time: {headers.get('x-ratelimit-reset-tokens')}")

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
