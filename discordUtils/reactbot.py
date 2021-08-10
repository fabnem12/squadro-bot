import asyncio
import discord
from discord.ext import commands
from typing import Union

from constantes import tokenReact

def main() -> None:
    bot = commands.Bot(command_prefix=",", help_command=None)

    @bot.command(name="react")
    async def react(ctx, *emojis: Union[discord.Emoji, str]):
        reference = ctx.message.reference

        if reference:
            msg = await ctx.channel.fetch_message(reference.message_id)
            for emoji in emojis:
                await msg.add_reaction(emoji)

        await ctx.message.delete()

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(tokenReact))
    loop.run_forever()

main()
