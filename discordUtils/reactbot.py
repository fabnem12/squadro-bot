import asyncio
import nextcord
from nextcord.ext import commands
from typing import Union

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constantes import tokenReact

def main() -> None:
    intentsBot = nextcord.Intents.default()
    intentsBot.members = True
    intentsBot.messages = True
    intentsBot.message_content = True
    bot = commands.Bot(command_prefix=",", help_command=None, intents = intentsBot)

    @bot.command(name="react")
    async def react(ctx, *emojis: Union[nextcord.Emoji, str]):
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
