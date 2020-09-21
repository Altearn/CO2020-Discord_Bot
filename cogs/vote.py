import discord
import typing
from discord.ext import commands


class Creative(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="vote")
    @commands.cooldown(4, 30, type=commands.BucketType.guild)
    async def vote(self, ctx, number: typing.Optional[int] = 0, *, text):
        """Send a message on which anyone can vote through reactions. 

        If no number of choices is given, the emojis will be 👍 and 👎. Otherwise, it will be a series of numbers.
        The text sent by the bot is EXACTLY the one you give, without any more formatting."""
        if ctx.guild != None:
            if not (ctx.channel.permissions_for(ctx.guild.me).send_messages and ctx.channel.permissions_for(ctx.guild.me).add_reactions):
                return await ctx.send("I can't react here")
        if number == 0:
            msg = await ctx.send(text)
            try:
                await msg.add_reaction('👍')
                await msg.add_reaction('👎')
            except Exception as e:
                await ctx.send(f"error occured: {e}")
                return
        else:
            liste = ['\U00000030\U000020e3', '\U00000031\U000020e3', '\U00000032\U000020e3', '\U00000033\U000020e3', '\U00000034\U000020e3',
                     '\U00000035\U000020e3', '\U00000036\U000020e3', '\U00000037\U000020e3', '\U00000038\U000020e3', '\U00000039\U000020e3', '\U0001f51f']
            if number > 10 or number < 1:
                await ctx.send("invalid number")
                return
            msg = await ctx.send(text)
            for x in range(0, number+1):
                try:
                    await msg.add_reaction(liste[x])
                except discord.errors.NotFound:
                    return
                except Exception as e:
                    await ctx.send(f"error occured: {e}")

    @commands.command(name="donation", aliases=['mylink', 'donator'])
    async def donation(self, ctx: commands.Context, user: typing.Optional[discord.Member]):
        if user == None:
            user = ctx.author
        await ctx.send("https://gift.creative-olympics.net/donate/"+str(user.id))


def setup(bot):
    bot.add_cog(Creative(bot))
