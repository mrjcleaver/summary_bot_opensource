import discord



def get_tagged_channels(guild: discord.Guild, tag: str):
    """Returns a list of text channels that have the given tag in their topic."""
    matching_channels = []
    
    for channel in guild.text_channels:
        if channel.topic and "Tags:" in channel.topic:
            # Extract tags from the topic
            topic_tags = channel.topic.split("Tags:")[-1].strip().lower()
            tag_list = [t.strip() for t in topic_tags.split(",")]

            if tag.lower() in tag_list:
                matching_channels.append(channel)

    return matching_channels  # Returns a list of matching discord.TextChannel objects



async def tagged_channels(ctx, tag: str):
    """Slash command to find tagged channels."""
    matching_channels = get_tagged_channels(ctx.guild, tag)

    if matching_channels:
        response = "**Channels matching `{}`:**\n".format(tag)
        response += "\n".join(f"🔹 {channel.mention}" for channel in matching_channels)
    else:
        response = f"No channels found with the tag `{tag}`."

    await ctx.respond(response, ephemeral=True)  # Sends privately

