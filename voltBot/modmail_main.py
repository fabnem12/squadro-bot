import nextcord
import pandas as pd
import datetime
from nextcord.ext import commands
from os.path import join, abspath, dirname

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constantes import TOKENVOLT as token, prefixVolt as prefix, redFlags
from utils import stockePID, cheminOutputs as outputsPath

stockePID()

# ticket_log is the file that logs all the tickets, so the bot can restart w/o problems
# it has the ChannelID of the ticket_thread, the AuthorTag and AuthorID of the person who the ticket is with
# the Ticketnumber, simply a number that counts up when and functions as unique ID
# the Status, whether the ticket is Active or Closed
# and optionally the Moderator, if the ticket was created by a mod and the Reason for which the mod made the ticket

try:
    ticket_log = pd.read_csv(join(dirname(__file__), 'log.csv'), na_filter=False)
except FileNotFoundError:
    ticket_log = pd.DataFrame(columns=['ChannelID', 'AuthorTag', 'AuthorID', 'Ticketnumber', 'Status', 'Moderator', 'Reason'])

ticket_log.info()
# bot_settings.txt is a simple 5-line txt file with the ticket_hub_id in the 1st line, prefix in the 2nd, etc.
with open(join(dirname(__file__), 'bot_settings.txt'), 'r+') as settings:
    ticket_hub_id = int(settings.readline())
    prefix = str(settings.readline())[:-1]
    mod_anonymity = int(settings.readline())
    join_message = str(settings.readline())[:-1]
    
# initializing the bot
owners = (180333726306140160, 619574125622722560)
bot = commands.Bot(command_prefix=prefix, owner_ids=owners)
settings.close()
print(f"Ticket hub: {ticket_hub_id}\nPrefix: {prefix}\nMod anonymity: {mod_anonymity}\nCmd prefix: {bot.command_prefix}"
      f"\nToken: {token}")


@bot.command(name='test', help="Quite pointless to be honest.")
async def test(ctx):
    await ctx.channel.send("Test received!")


"""
    Hello there, I am a modmail bot. You can DM me and I will tell you how to create a ticket from the user perspective. There are also some moderator commands:
    \n{prefix}help: Gets you to this screen.
    \n{prefix}test: Quite pointless to be honest.
    \n{prefix}debug_info: Information about the bot's current settings.
    \n{prefix}set_tickethub [channel_id]: This command is used for changing the channel where the threads for all the tickets are created, pass the channel as the channel ID. (Requires admin permissions)
    \n{prefix}set_prefix: This command allows you to change the bot's prefix. (Requires admin permissions)
    \n{prefix}set_mod_anonymity: This command allows you to change whether or not moderators reply anonymously to tickets, valid values are 0 (for no anonymity) and 1 (for anonymity). (Requires admin permissions)
    \n{prefix}open_ticket [user] [reason]: This command allows moderators to open a ticket with a specific user that is passed as a user ID. You can also optionally pass a reason argument. (Requires ban members permissions)
    \n{prefix}close: This command can only be used in active tickets (so in ticket threads, or in DMs with modmail while there is an active ticket. This closes the current ticket.
    \n{prefix}reopen: This command can only be used in previously active tickets
"""


@bot.command(name='shutdown')
@commands.is_owner()
async def shutdown(ctx):
    await ctx.channel.send('bye')
    exit()


@bot.command(name='get_logs', help="Get the log file where the threads are stored. Requires Manage Channels")
@commands.has_guild_permissions(manage_channels=True)
async def get_logs(ctx):
    await ctx.channel.send(file=nextcord.File(join(dirname(__file__), 'log.csv')))


@bot.command(name='set_logs', help="Replace the log file where the threads are stored. Requires Manage Channels")
@commands.is_owner()
async def set_logs(ctx):
    global ticket_log
    await ctx.message.attachments[0].save(join(dirname(__file__), 'log.csv'))
    ticket_log = pd.read_csv('log.csv', na_filter=False)
    ctx.channel.send("Successfully overridden old log")


@bot.command(name='get_settings', help="Get the settings file, where the bot's settings are stored. Requires Manage Channels")
@commands.has_guild_permissions(manage_channels=True)
async def get_logs(ctx):
    await ctx.channel.send(file=nextcord.File(join(dirname(__file__), 'bot_settings.txt')))


@bot.command(name='debug_info', help="Information about the bot's current settings.")
async def debug_info(ctx):
    await ctx.channel.send(f"Ticket hub: {ticket_hub_id}\nPrefix: {prefix}\nMod anonymity: {mod_anonymity}")


@bot.command(name='set_tickethub',
             help="This command is used for changing the channel where the threads for all the tickets are created, pass the channel as the channel ID. (Requires Manage Channels)")
@commands.has_guild_permissions(manage_channels=True)
async def set_tickethub(ctx, channel_id):
    global ticket_hub_id
    try:
        # check whether the channel exists
        await bot.fetch_channel(int(channel_id))
        ticket_hub_id = int(channel_id)
        # update settings
        with open('bot_settings.txt', 'w') as settings_writable:
            settings_writable.write(f"{ticket_hub_id}\n{prefix}\n{mod_anonymity}\n{join_message}\n{token}")
        # print(f"im at: {settings.tell()}, my name: {settings.name}")
        await ctx.channel.send(f"Ticket hub updated to <#{int(channel_id)}>.")
    except (nextcord.errors.NotFound, ValueError):
        await ctx.channel.send("Please enter a valid Channel ID")
        # print(e)


@bot.command(name='set_prefix', help="This command allows you to change the bot's prefix. (Requires admin permissions)")
@commands.has_guild_permissions(administrator=True)
async def set_prefix(ctx, new_prefix):
    global prefix
    prefix = new_prefix
    bot.command_prefix = prefix
    with open(join(dirname(__file__), 'bot_settings.txt'), 'w') as settings_writable:
        settings_writable.write(f"{ticket_hub_id}\n{prefix}\n{mod_anonymity}\n{join_message}\n{token}")
    await ctx.channel.send(f"Prefix updated to {prefix}.")


@bot.command(name="set_mod_anonymity",
             help="This command allows you to change whether or not moderators reply anonymously to tickets, valid values are 0 (for no anonymity) and 1 (for anonymity). (Requires admin permissions)")
@commands.has_guild_permissions(administrator=True)
async def set_mod_anonymity(ctx, new_value):
    global mod_anonymity
    if int(new_value) == 1:
        mod_anonymity = 1
        await ctx.channel.send(f"Moderator anonymity set to {bool(int(new_value))}")
    elif int(new_value) == 0:
        mod_anonymity = 0
        await ctx.channel.send(f"Moderator anonymity set to {bool(int(new_value))}")
    else:
        await ctx.channel.send("Please enter a valid argument (0 or 1)")
    with open('bot_settings.txt', 'w') as settings_writable:
        settings_writable.write(f"{ticket_hub_id}\n{prefix}\n{mod_anonymity}\n{join_message}\n{token}")


@bot.command(name="open_ticket",
             help="This command allows moderators to open a ticket with a specific user that is passed as a user ID. You can also optionally pass a reason argument. (Requires ban members permissions)")
# this command is to open a ticket with a specific user as moderator
@commands.has_guild_permissions(ban_members=True)
async def open_ticket(ctx, user, *reason):
    reason = ' '.join(reason)  # all arguments after the first one are part of the reason
    try:
        user = await bot.fetch_user(user)  # attempts to fetch the user, the command fails if this doesn't work
        ticket_info = ticket_log[ticket_log['AuthorID'] == user.id].tail(1)

        # this if statement ensures this user doesn't have any other open tickets to make sure a user only has 1 open ticket
        if (len(ticket_info['Status']) == 0) or (len(ticket_info['Status']) == 1 and ticket_info['Status'].iloc[0] != 'Active'):
            ticket_number = len(ticket_log) + 1
            ticket_hub = bot.get_channel(ticket_hub_id)
            ticket_thread = await ticket_hub.create_thread(
                name=f'{user} num{ticket_number} id{user.id}',
                type=nextcord.ChannelType.public_thread,
                reason=f'Ticket for {user}, ID: {user.id}, Ticketnumber: {ticket_number}, Created by: {ctx.author}, ID: {ctx.author.id}')
            new_ticket = [ticket_thread.id, user, user.id, ticket_number, 'Active', int(ctx.author.id), reason]
            print(f"New ticket created by mod: {new_ticket}")
            msg_to_send = nextcord.Embed(
                colour=nextcord.Colour.from_rgb(80, 35, 121),
                timestamp=datetime.datetime.now(),
                title="New ticket opened by moderator.",
                description=f"{ctx.author.mention} | {ctx.author.id} | {ctx.author} started this ticket with {user.mention}."
            )
            if reason:
                msg_to_send.description += f" Reason: {reason}"
            msg_to_send.set_author(name=f"{user} | {user.id}",
                                   icon_url=user.avatar.url)
            await ticket_thread.send(embed=msg_to_send)
            # ticket_log.info()
            ticket_log.loc[len(ticket_log)] = new_ticket
            ticket_log.to_csv(join(dirname(__file__), 'log.csv'), index=False)
            desc = "New ticket opened by "
            if mod_anonymity:
                desc += "a moderator "
            else:
                desc += f"{ctx.author.mention} "
            desc += f"for you. Send a message back in this channel to respond."
            if reason:
                desc += f" Reason: {reason}"
            msg_to_dm = nextcord.Embed(
                colour=nextcord.Colour.from_rgb(80, 35, 121),
                timestamp=datetime.datetime.now(),
                title="New ticket opened by moderator.",
                description=desc
            )
            await ctx.channel.send(f"Successfully opened a new ticket: {ticket_thread.mention}")
            try:
                await user.send(embed=msg_to_dm)
            except nextcord.errors.HTTPException:
                await ctx.channel.send(
                    "Failed at DMing user. This could be due to closed DMs or due to no servers in common.")
                await ticket_thread.send(
                    "Failed at DMing user. This could be due to closed DMs or due to no servers in common.")

        else:
            await ctx.channel.send("This user already has an open ticket.")

    except (commands.CommandInvokeError, nextcord.errors.NotFound, nextcord.errors.HTTPException):
        # this is the error thrown when it tries to find the user but can't
        await ctx.channel.send("That is not a valid user. Please use a User ID.")


@bot.listen('on_ready')
async def handle_ready():
    print(f'We have logged in as {bot.user}')
    await bot.change_presence(activity=nextcord.Game(name="DM me to contact staff", start=datetime.datetime.utcnow()))


# @bot.listen('on_member_join')
# async def handle_member_join(member):
#     await member.send(f"{join_message}")
#     print('a new member has just joined')


@bot.listen('on_message')
async def handle_message(message):

    if message.author == bot.user:
        return

    if isinstance(message.channel, nextcord.DMChannel):

        # this if statement gets the user's active ticket or the latest inactive ticket if there are no active ones
        if len(ticket_log[(ticket_log['AuthorID'] == message.author.id) & (ticket_log['Status'] == 'Active')]) > 0:
            ticket_info = ticket_log[(ticket_log['AuthorID'] == message.author.id) & (ticket_log['Status'] == 'Active')].tail(1)
        else:
            ticket_info = ticket_log[ticket_log['AuthorID'] == message.author.id].tail(1)

        # check if the ticket is active
        if len(ticket_info['Status']) == 1 and ticket_info['Status'].iloc[0] == 'Active':
            ticket_info = ticket_info.iloc[0]
            # ticket_thread is the thread used in the server used to communicate with the user
            ticket_thread = await bot.fetch_channel(ticket_info['ChannelID'])
            if message.content == f"{prefix}close":
                ticket_info['Status'] = 'Closed'
                # sets the ticket to closed in the DataFrame
                ticket_log.loc[(ticket_log['AuthorID'] == message.author.id) & (ticket_log['Status'] == 'Active'), 'Status'] = 'Closed'

                await message.channel.send("Ticket closed. Send `ticket` to open another ticket.")
                await ticket_thread.send("Ticket closed by creator.")
                await ticket_thread.edit(archived=True)
            else:
                # this else handles sending the message from the user to the ticket thread
                msg_to_send = nextcord.Embed(
                    description=f"{message.content}",
                    colour=nextcord.Colour.from_rgb(80, 35, 121),
                    timestamp=datetime.datetime.now()
                )
                msg_to_send.set_author(name=f"{message.author} | {message.author.id}",
                                       icon_url=message.author.avatar.url)
                for doc in message.attachments:
                    msg_to_send.description += f"\n{doc.proxy_url}"
                msg_to_send.description += f"\n\n{message.author.mention}"
                await ticket_thread.send(embed=msg_to_send)
                await message.add_reaction('✅')

        elif message.content.lower() == 'ticket':
            # the unique ID for tickets
            ticket_number = len(ticket_log) + 1
            await message.channel.send("Ticket opened. I will react with :white_check_mark: to confirm I sent your message.")
            tickets = bot.get_channel(ticket_hub_id)
            # create a ticket thread
            ticket_thread = await tickets.create_thread(
                name=f'{message.author} num{ticket_number} id{message.author.id}',
                type=nextcord.ChannelType.public_thread,
                reason=f'Ticket for {message.author}, ID: {message.author.id}, Ticketnumber: {ticket_number}')
            new_ticket = [ticket_thread.id, message.author, message.author.id, ticket_number, 'Active', '', '']
            msg_to_send = nextcord.Embed(
                colour=nextcord.Colour.from_rgb(80, 35, 121),
                timestamp=datetime.datetime.now(),
                title="New ticket opened.",
                description=f"by {message.author.mention}"
            )
            msg_to_send.set_author(name=f"{message.author} | {message.author.id}",
                                   icon_url=message.author.avatar.url)
            await ticket_thread.send(embed=msg_to_send)
            ticket_log.loc[len(ticket_log)] = new_ticket

        # reopen the ticket if the user sends the command
        elif message.content.lower() == f"{prefix}reopen" and len(ticket_info['Status']) == 1 and ticket_info['Status'].iloc[0] == 'Closed':
            ticket_info = ticket_info.iloc[0]
            ticket_thread = await bot.fetch_channel(ticket_info['ChannelID'])
            print(ticket_log.loc[(ticket_log['AuthorID'] == message.author.id) & (ticket_log['Status'] == 'Closed'), 'Status'].iloc[-1])
            ticket_to_open = ticket_log.loc[(ticket_log['AuthorID'] == message.author.id) & (ticket_log['Status'] == 'Closed'), 'Ticketnumber'].iloc[-1]
            ticket_log.loc[ticket_log['Ticketnumber'] == ticket_to_open, 'Status'] = 'Active'
            await message.channel.send("Ticket reopened")
            await ticket_thread.send("This ticket has been reopened by the user.")

        else:
            await message.channel.send('Hello. Do you want to open a ticket? Type `ticket` to start a ticket.' +
                                       f'\nWhen you want to close the ticket, type `{prefix}close` to close it.')

    # this deals with sending messages from the thread to the user
    elif isinstance(message.channel, nextcord.Thread) and len(ticket_log.loc[ticket_log['ChannelID'] == message.channel.id]) > 0:

        ticket_info = ticket_log[ticket_log['ChannelID'] == message.channel.id].tail(1).iloc[0]
        ticket_maker = await bot.fetch_user(ticket_info['AuthorID'])
        # ticket_maker = await bot.fetch_user(log.loc[log['ChannelID'] == message.channel.id]['AuthorID'].iloc[0])
        if ticket_info['Status'] == 'Closed' and len(ticket_log[(ticket_log['AuthorID'] == ticket_maker.id) & (ticket_log['Status'] == 'Active')]) == 0:
            ticket_to_open = ticket_log.loc[(ticket_log['ChannelID'] == message.channel.id) & (ticket_log['Status'] == 'Closed'), 'Ticketnumber'].iloc[-1]
            ticket_log.loc[ticket_log['Ticketnumber'] == ticket_to_open, 'Status'] = 'Active'
            # print(log.loc[(log['AuthorID'] == ticket_maker.id) & (log['Status'] == 'Closed'), :])
            await message.channel.send("Ticket reopened by moderator")
            msg_to_send = "This ticket has been reopened by "
            if mod_anonymity:
                msg_to_send += "a moderator."
            else:
                msg_to_send += f"{message.author.mention}."

            try:
                await ticket_maker.send(msg_to_send)
            except nextcord.errors.HTTPException:
                pass
        elif ticket_info['Status'] == 'Closed':
            await message.channel.send("This user already has another active ticket. Users can only have one active ticket at a time.")
        if message.content == f"{prefix}close":
            ticket_log.loc[(ticket_log['AuthorID'] == ticket_maker.id) & (ticket_log['Status'] == 'Active'), 'Status'] = 'Closed'
            await message.channel.send("Ticket closed successfully.")
            msg_to_send = "This ticket has been closed by "
            if mod_anonymity:
                msg_to_send += "a moderator. "
            else:
                msg_to_send += f"{message.author.mention}. "
            msg_to_send += f"Send `ticket` to open a new ticket or send `{prefix}reopen` to reopen the current ticket."
            try:
                await ticket_maker.send(msg_to_send)
            except nextcord.errors.HTTPException:
                await message.channel.send("Failed at DMing user. This could be due to closed DMs or due to no servers in common.")
            await message.channel.edit(archived=True)
        else:
            msg_to_send = nextcord.Embed(
                description=f"{message.content}",
                colour=nextcord.Colour.from_rgb(80, 35, 121),
                timestamp=datetime.datetime.now()
            )
            for doc in message.attachments:
                msg_to_send.description += f"\n{doc.proxy_url}"
            if not mod_anonymity:
                msg_to_send.set_author(name=f"{message.author} | {message.author.id}",
                                       icon_url=message.author.avatar.url)
                msg_to_send.description += f"\n\n{message.author.mention}"
            else:
                msg_to_send.set_author(name=f"Message received from staff")

            try:
                await ticket_maker.send(embed=msg_to_send)
                await message.add_reaction('✅')
            except nextcord.errors.HTTPException:
                await message.channel.send("Failed at DMing user. This could be due to closed DMs or due to no servers in common.")

    ticket_log.to_csv(join(dirname(__file__), 'log.csv'), index=False)

bot.run(token)
