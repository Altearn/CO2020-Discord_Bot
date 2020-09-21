import discord
from discord.ext import commands

import os
import sys
import copy
import traceback
import io
import textwrap
import typing
from contextlib import redirect_stdout
from glob import glob
from git import Repo, Remote


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    # remove `foo`
    return content.strip('` \n')


async def check_admin(ctx):
    return ctx.author.id in [279568324260528128, 125722240896598016, 621874860544622605]


class AdminCog(commands.Cog):
    """Here are listed all commands related to the internal administration of the bot. Most of them are not accessible to users, but only to COBot administrators."""

    def __init__(self, bot):
        self.bot = bot
        self.file = "admin"
        self._last_result = None

    @commands.command(name="ping", aliases=['rep'])
    async def rep(self, ctx, ip=None):
        """Get bot latency
        You can also use this command to ping any other server"""
        m = await ctx.send("Ping...")
        t = (m.created_at - ctx.message.created_at).total_seconds()
        await m.edit(content=":ping_pong:  Pong !\nBot ping: {}ms\nDiscord ping: {}ms".format(round(t*1000), round(self.bot.latency*1000)))

    @commands.group(name='admin', hidden=True)
    @commands.check(check_admin)
    async def main_msg(self, ctx):
        """Commandes réservées aux administrateurs de COBot"""
        if ctx.subcommand_passed == None:
            text = "Liste des commandes disponibles :"
            for cmd in sorted(self.main_msg.commands, key=lambda x: x.name):
                text += "\n- {} *({})*".format(cmd.name, '...' if cmd.help ==
                                               None else cmd.help.split('\n')[0])
                if type(cmd) == commands.core.Group:
                    for cmds in cmd.commands:
                        text += "\n        - {} *({})*".format(cmds.name, cmds.help.split('\n')[0])
            await ctx.send(text)

    @main_msg.command(name='shutdown')
    async def shutdown(self, ctx):
        """Eteint le bot"""
        m = await ctx.send("Nettoyage de l'espace de travail...")
        await self.cleanup_workspace()
        await m.edit(content="Bot en voie d'extinction")
        await self.bot.change_presence(status=discord.Status('offline'))
        print("Fermeture du bot")
        await self.bot.logout()
        await self.bot.close()

    @main_msg.command(name='pull')
    async def pull(self, ctx):
        """Tire des changements de GitLab"""
        m = await ctx.send("Mise à jour depuis gitlab...")
        repo = Repo('/home/Gunibot.py')
        assert not repo.bare
        origin = repo.remotes.origin
        origin.pull()
        await ctx.send(content="Redémarrage en cours...")
        await self.cleanup_workspace()
        print("Redémarrage du bot")
        os.execl(sys.executable, sys.executable, 'start.py')

    @main_msg.command(name='purge')
    async def clean(self, ctx, limit: int):
        await ctx.channel.purge(limit=limit)
        await ctx.send('Purged by {}'.format(ctx.author.mention))
        await ctx.message.delete()

    async def cleanup_workspace(self):
        for folderName, _, filenames in os.walk('.'):
            for filename in filenames:
                if filename.endswith('.pyc'):
                    os.unlink(folderName+'/'+filename)
            if folderName.endswith('__pycache__'):
                os.rmdir(folderName)

    @main_msg.command(name='reboot')
    async def restart_bot(self, ctx):
        """Relance le bot"""
        await ctx.send(content="Redémarrage en cours...")
        await self.cleanup_workspace()
        print("Redémarrage du bot")
        os.execl(sys.executable, sys.executable, 'start.py')

    @main_msg.command(name='reload')
    async def reload_cog(self, ctx, *, cog: str):
        """Recharge un module"""
        done = list()
        for cog in cog.split(" "):
            try:
                self.bot.reload_extension(cog)
            except Exception as e:
                await ctx.send(str(e))
            else:
                done.append(cog)
        if len(done) > 0:
            s = "s" if len(done) > 1 else ""
            await ctx.send("Module{0} {1} rechargé{0}".format(s, " - ".join(done)))
            print("Module{0} {1} rechargé{0}".format(s, " - ".join(done)))

    @main_msg.command(name="add_cog", hidden=True)
    @commands.check(check_admin)
    async def add_cog(self, ctx, name):
        """Ajouter un cog au bot"""
        try:
            self.bot.load_extension('fcts.'+name)
            await ctx.send("Module '{}' ajouté !".format(name))
            print("Module {} ajouté".format(name))
        except Exception as e:
            await ctx.send(str(e))

    @main_msg.command(name="del_cog", aliases=['remove_cog'], hidden=True)
    @commands.check(check_admin)
    async def rm_cog(self, ctx, name):
        """Enlever un cog au bot"""
        try:
            self.bot.unload_extension('fcts.'+name)
            await ctx.send("Module '{}' désactivé !".format(name))
            print("Module {} ajouté".format(name))
        except Exception as e:
            await ctx.send(str(e))

    @main_msg.command(name='eval')
    @commands.check(check_admin)
    async def _eval(self, ctx, *, body: str):
        """Evaluates a code
        Credits: Rapptz (https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py)"""
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }
        env.update(globals())

        body = cleanup_code(body)
        stdout = io.StringIO()
        try:
            to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e, ctx)
            return
        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            await ctx.bot.cogs['UtilitiesCog'].add_check_reaction(ctx.message)

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @main_msg.command(name='execute', hidden=True)
    @commands.check(check_admin)
    async def sudo(self, ctx, who: typing.Union[discord.Member, discord.User], *, command: str):
        """Run a command as another user
        Credits: Rapptz (https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py)"""
        msg = copy.copy(ctx.message)
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg)
        #new_ctx.db = ctx.db
        await self.bot.invoke(new_ctx)
        await ctx.bot.cogs['UtilitiesCog'].add_check_reaction(ctx.message)


def setup(bot):
    bot.add_cog(AdminCog(bot))
