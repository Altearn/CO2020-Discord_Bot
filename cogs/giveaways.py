from discord.ext import commands, tasks
import os
import asyncio
import random
import discord
import traceback
import datetime
import re
import time


async def admin_or_permissions(ctx: commands.Context):
    return ctx.author.guild_permissions.administrator


class Giveaways(commands.Cog):
    """Giveaways."""

    def __init__(self, bot):
        self.bot = bot
        self.started = False
        self.settings = bot.get_cog("ConfigCog").confManager
        self.internal_task.start()

    async def cog_command_error(self, ctx, err):
        await ctx.send(f"`Error:` {err}")
        traceback.print_exception(type(err), err, err.__traceback__)

    @commands.group(pass_context=True, aliases=["gaw", "giveaways"])
    async def giveaway(self, ctx):
        """Start or stop giveaways."""
        if not ctx.invoked_subcommand:
            await ctx.send("`Error:` Subcommand not found")

    @giveaway.command(pass_context=True)
    @commands.check(admin_or_permissions)
    async def start(self, ctx, *, settings):
        """Start a giveaway.
        Usage"
        [p]giveaway start name: <Giveaway  name>; length: <Time length>; entries: [winners count]; channel: [channel mention]
        Giveaway name is mandatory.
        Length is mandatory.
        Winners count is optional (default 1).
        Channel is optional (default current channel).

        Example:
        [p]giveaway start name: Minecraft account; length: 3 days;
        [p]giveaway start name: Minecraft account; length: 2 hours; channel: #announcements
        [p]giveaway start name: Minecraft account; length: 5 days; entries: 5"""
        i_settings = settings.split("; ")
        server = ctx.message.guild
        channel = ctx.channel
        durations = (86400, 3600, 60)

        # Setting all of the settings.
        settings = {"name": "", "length": -1, "users": [], "started": True,
                    "channel": ctx.channel.id, "message": None, "entries": 1}
        for setting in i_settings:
            if setting.startswith("name: "):
                if setting[6:] in self.settings[ctx.message.guild.id]:
                    await ctx.send("There's already a giveaway running with this name.")
                    return
                else:
                    settings['name'] = setting[6:].strip()
            elif setting.startswith("entries: "):
                entries = setting.replace("entries: ", "").strip()
                if (not entries.isnumeric()) or (entries == "0"):
                    await ctx.send("Entries number must be a digit")
                    return
                settings['entries'] = int(entries)
            elif setting.startswith("length: "):
                length = setting[7:]
                total = 0
                for s in re.findall(r'(?:(\d{1,2}) days?)|(?:(\d{1,2}) hours?)|(?:(\d{1,2}) min)', length):
                    for e, d in enumerate(s):
                        if len(d) > 0:
                            total += durations[e] * int(d)
                if total > 0:
                    settings['length'] = total
            elif setting.startswith("channel: "):
                try:
                    channel = await commands.TextChannelConverter().convert(ctx, setting.replace('channel: ', ''))
                except:
                    await ctx.send("The 'channel' parameter is not a valid text channel.")
                    return
                perms = channel.permissions_for(ctx.guild.me)
                if not (perms.send_messages or perms.embed_links):
                    await ctx.send("I cannot send embeds in the specified channel")
                    return
                settings['channel'] = channel.id
        # Checking if mandatory settings are there.
        if settings['name'] == "":
            await ctx.send("The 'name' parameter cannot be empty.")
            return
        if settings['length'] == -1:
            await ctx.send("The 'length' parameter cannot be empty.")
            return
        settings['end'] = round(time.time()) + settings['length']
        # Send embed now
        try:
            emb = discord.Embed(title="New giveaway!", description=settings["name"], timestamp=datetime.datetime.utcnow(
            )+datetime.timedelta(seconds=settings['length']), color=random.randint(0, 16777215)).set_footer(text="Ends at")
            msg = await channel.send(embed=emb)
            settings['message'] = msg.id
        except:
            await ctx.send("Unable to send a message in "+channel.mention)
            return
        # Save settings in config
        if server.id not in self.settings.keys():
            self.settings[server.id] = {}
        self.settings[server.id][settings['name']] = settings
        await ctx.send("Successfully added giveaway **{}**.".format(settings['name']))

    @giveaway.command(pass_context=True)
    @commands.check(admin_or_permissions)
    async def stop(self, ctx, *, giveaway):
        """Stops a giveaway early so you can pick a winner.
        Example:
        [p]giveaway stop Minecraft account"""
        server = ctx.message.guild
        if server.id not in self.settings.keys():
            await ctx.send("There are no giveaways in this server.")
        elif giveaway not in self.settings[server.id]:
            await ctx.send("That's not a valid giveaway, to see all giveaways you can do {}giveaway list.".format(ctx.prefix))
        elif not self.settings[server.id][giveaway]['started']:
            await ctx.send("That giveaway's already stopped.")
        else:
            d = self.settings[server.id]
            d[giveaway]['started'] = False
            self.settings[server.id] = d
            await self.send_results(d, await self.pick_winners(ctx.guild, d))

    @giveaway.command(pass_context=True, enabled=False)
    @commands.check(admin_or_permissions)
    async def pick(self, ctx, *, giveaway):
        """Picks winners for the giveaway, which usually should be 1.
        Example:
        [p]giveaway pick Minecraft account (This will pick winners from all the people who entered the Minecraft account giveaway)"""
        server = ctx.message.guild
        if server.id not in self.settings.keys():
            await ctx.send("This server does not have any giveaways yet.")
            return
        if giveaway not in self.settings[server.id]:
            await ctx.send("That's not a valid giveaway.")
            return
        elif self.settings[server.id][giveaway]['started']:
            await ctx.send("That giveaway is still running, you can stop it with {}giveaway stop {}.".format(ctx.prefix, giveaway))
            return
        ga = self.settings[server.id][giveaway]
        users = set(ga['users']) | await self.get_users(ga['channel'], ga['message'])
        if len(users) == 0:
            await ctx.send("No one entered that giveaway! I will destroy it")
            del self.settings[server.id][giveaway]
        else:
            amount = min(ga['entries'], len(users))
            status = await ctx.send("Picking winners.")
            winners = []
            trials = 0
            users = list(users)
            while len(winners) < amount and trials < 20:
                w = discord.utils.get(server.members, id=random.choice(users))
                if w != None:
                    winners.append(w.mention)
                else:
                    trials += 1
            del self.settings[server.id][giveaway]
            if amount == 1:
                await status.edit(content="The winner is: {}! Congratulations, you won {}!".format(" ".join(winners), giveaway))
            else:
                await status.edit(content="The winners are: {}! Congratulations, you won {}!".format(" ".join(winners), giveaway))

    @giveaway.command(pass_context=True)
    async def enter(self, ctx, *, giveaway):
        """Enter a giveaway.
        Example:
        [p]giveaway enter Minecraft account."""
        if ctx.author.bot:
            await ctx.send("Bots can't participate to giveaways!")
            return
        server = ctx.message.guild
        author = ctx.message.author

        if server.id not in self.settings.keys():
            await ctx.send("This server has no giveaways.")
            return
        elif giveaway not in self.settings[server.id]:
            await ctx.send("That is not a valid giveaway.")
            return
        ga = self.settings[server.id][giveaway]
        if author.id in ga['users']:
            await ctx.send("You already entered this giveaway.")
        elif not ga['started']:
            await ctx.send("This giveaway has been stopped.")
        else:
            ga['users'].append(author.id)
            await ctx.send("You have successfully entered the {} giveaway, good luck!".format(giveaway))
        self.settings[server.id][giveaway] = ga

    @giveaway.command(pass_context=True)
    async def list(self, ctx):
        """Lists all giveaways running in this server."""
        server = ctx.message.guild
        if server.id not in self.settings.keys() or self.settings[server.id] == {}:
            await ctx.send("This server has no giveaways running.")
        else:
            every = list(self.settings[server.id].values())
            running = [x['name'] for x in every if x['started']]
            stopped = [x['name'] for x in every if not x['started']]
            text = "This server has the following giveaways running:\n\t{}".format(
                "\n\t".join(running)) if len(running) > 0 else ""
            if len(stopped) > 0:
                text += ("\n\n" if len(text) > 0 else "") + \
                    "This server has the following giveaways stopped:\n\t{}".format(
                        "\n\t".join(stopped))
            if len(text) == 0:
                text = "This server has no giveaway"
            await ctx.send(text)

    @giveaway.command(pass_context=True)
    async def info(self, ctx, *, giveaway):
        """Get information for a giveaway.
        Example:
        [p]giveaway info Minecraft account"""
        server = ctx.message.guild
        if server.id not in self.settings.keys():
            await ctx.send("This server has no giveaways running.")
        elif giveaway not in self.settings[server.id]:
            await ctx.send("That's not a valid giveaway running in this server.")
        else:
            settings = self.settings[server.id][giveaway]
            entries = len(set(settings['users']) | await self.get_users(settings['channel'], settings['message']))
            time_left = settings['end'] - round(time.time())
            time_left = self.secondsToText(
                time_left) if time_left > 0 else "already stopped"
            await ctx.send("Name: **{}**\nTime left: **{}**\nEntries: **{}**\nChannel: <#{}>".format(giveaway, time_left, entries, settings['channel']))

    def cog_unload(self):
        self.internal_task.cancel()

    @tasks.loop(seconds=1.0)
    async def internal_task(self):
        for server in self.settings.keys():
            for giveaway in self.settings[server]:
                if self.settings[server][giveaway]['started']:
                    if self.settings[server][giveaway]['end'] <= time.time():
                        d = self.settings[server][giveaway]
                        d['started'] = False
                        await self.send_results(d, await self.pick_winners(self.bot.get_guild(server), d))

    # http://bit.ly/2ofiay3

    def secondsToText(self, secs):
        days = secs//86400
        hours = (secs - days*86400)//3600
        minutes = (secs - days*86400 - hours*3600)//60
        seconds = secs - days*86400 - hours*3600 - minutes*60
        result = ("{0} day{1} ".format(days, "s" if days != 1 else "") if days else "") + \
            ("{0} hour{1} ".format(hours, "s" if hours != 1 else "") if hours else "") + \
            ("{0} minute{1} ".format(minutes, "s" if minutes != 1 else "") if minutes else "") + \
            ("{0} second{1}".format(
                seconds, "s" if seconds != 1 else "") if seconds else "")
        return result

    async def get_users(self, channel: int, message: int):
        """Get users who reacted to a message"""
        channel: discord.TextChannel = self.bot.get_channel(channel)
        if channel is None:
            return []
        message: discord.Message = await channel.fetch_message(message)
        if message is None or message.author != self.bot.user:
            return []
        users = set()
        for react in message.reactions:
            async for user in react.users():
                if not user.bot:
                    users.add(user.id)
        return users

    async def edit_embed(self, channel: discord.TextChannel, message: int, winners: [discord.Member]):
        """Edit the embed to display results"""
        message: discord.Message = await channel.fetch_message(message)
        if message is None or message.author != self.bot.user:
            return None
        if len(message.embeds) == 0 or message.embeds[0].title != "New giveaway!":
            return None
        emb: discord.Embed = message.embeds[0]
        emb.set_footer(text="Ended at")
        emb.description = "Price: {}\nWon by: {}".format(
            emb.description, " ".join([x.mention for x in winners]))
        await message.edit(embed=emb)
        return emb.color

    async def pick_winners(self, guild: discord.Guild, giveaway: dict):
        users = set(giveaway['users']) | await self.get_users(giveaway['channel'], giveaway['message'])
        if len(users) == 0:
            return list()
        else:
            amount = min(giveaway['entries'], len(users))
            winners = []
            trials = 0
            users = list(users)
            while len(winners) < amount and trials < 20:
                w = discord.utils.get(guild.members, id=random.choice(users))
                if w != None:
                    winners.append(w)
                else:
                    trials += 1
        return winners

    async def send_results(self, giveaway: dict, winners: [discord.Member]):
        """Send the giveaway results in a new embed"""
        print(f"Giveaway '{giveaway['name']}' has stopped")
        channel: discord.TextChannel = self.bot.get_channel(giveaway['channel'])
        if channel is None:
            return None
        emb_color = await self.edit_embed(channel, giveaway['message'], winners)
        if emb_color is None:
            emb_color = random.randint(0, 16777215)
        win = "There was no participant :confused:" if len(winners) == 0 else (
            "The winner is" if len(winners) == 1 else "The winners are")
        emb = discord.Embed(title="Giveaway is over!", description="Price: {}\n\n{} {}".format(
            giveaway['name'], win, " ".join([x.mention for x in winners])), color=emb_color)
        await channel.send(embed=emb)
        del self.settings[channel.guild.id][giveaway['name']]


def setup(bot):
    bot.add_cog(Giveaways(bot))
