from constants import MAX_TOKENS
from tiktoken import encoding_for_model
import logging 

TOKENIZER = encoding_for_model("gpt-3.5-turbo")
def get_tokens(text):
     return len(TOKENIZER.encode(text))

def chunk_messages(prior_messages, recent_channel_messages, max_tokens=30000, assumed_token_length=50, chunk_size=1000):
        """
        Chunk messages for summarization.

        Args:
            prior_messages (list): List of prior messages for context.
            recent_channel_messages (list): List of recent messages to summarize.
            max_tokens (int): Maximum tokens for OpenAI API.
            assumed_token_length (int): Assumed average token length.
            chunk_size (int): Size of each chunk.

        Returns:
            list: List of message chunks.
        """
        logging.info("Chunking for summarization")
        logging.debug(f"Length for prior messages: {len(prior_messages)}")
        budget_for_chunk = max_tokens - len(prior_messages) * assumed_token_length
        logging.debug(f"Budget for chunk: {budget_for_chunk}")

        if budget_for_chunk < 0:
            logging.error("Prior messages exceed token limit. Truncating.")
            prior_messages = prior_messages[:int(max_tokens / assumed_token_length)]
            budget_for_chunk = 0

        chunks = []
        for i in range(0, len(recent_channel_messages), chunk_size):
            chunks.append(recent_channel_messages[i:i + chunk_size])

        logging.debug(f"Number of chunks: {len(chunks)}")
        return chunks

# This is an Arun's implementation of chunking messages for OpenAI API.
def chunk_messages_by_model_token_limit(messages, model):
    """
    Groups messages into chunks based on the token limit of the model.

    Args:
        messages (list): List of messages to be grouped.
        model (dict): Model information containing the context length.

    Returns:
        tuple: A tuple containing:
            - groups (list): List of grouped messages as strings.
            - group_counts (list): List of counts of messages in each group.
            - starts (list): List of starting messages for each group.
            - in_token_count (int): Total number of input tokens.
    """
    next_group = True
    groups = []
    group_counts = []
    starts = []
    curr_group = ""
    curr_count = 0
    in_token_count = 0

    for message in messages:
        if next_group:
            starts.append(message)
            next_group = False

        author_name = getattr(getattr(message, 'author', None), 'display_name', None)
        content = getattr(message, 'content', None)

        if not author_name or not content:
            logging.debug(f"Skipping incomplete message: {message}")
            continue  

        m = f"{author_name}: {content}\n"

        if get_tokens(curr_group + m) > (MAX_TOKENS * model["context_length"]):
            in_token_count += get_tokens(curr_group)
            groups.append(curr_group)
            group_counts.append(curr_count)
            curr_group = ""
            curr_count = 0
            next_group = True

        curr_group += m
        curr_count += 1

    starts.append(message)
    groups.append(curr_group)
    group_counts.append(curr_count)
    in_token_count += get_tokens(curr_group)

    logging.debug(f"Number of groups: {len(groups)}")
    logging.debug(f"Number of messages: {len(messages)}")
    logging.debug(f"Total tokens: {in_token_count}")
    

    return groups, group_counts, starts, in_token_count