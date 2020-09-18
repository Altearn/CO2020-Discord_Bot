#!/usr/bin/env python
# coding=utf-8

import discord
import time
import asyncio
from signal import SIGTERM
from discord.ext import commands

ALLOWED_USERS = [279568324260528128,  # Z_runner
                 125722240896598016]  # Leirof / Vincent#4203


class zbot(commands.bot.BotBase, discord.Client):

    def __init__(self, command_prefix=None, case_insensitive=None, status=None, database_online=True, beta=False, dbl_token=""):
        super().__init__(command_prefix=command_prefix,
                         case_insensitive=case_insensitive, status=status)

    async def get_prefix(self, msg):
        return get_prefix(self, msg)


def get_prefix(bot, msg):
    return commands.when_mentioned_or("/")(bot, msg)


def main():
    client = zbot(command_prefix=get_prefix, case_insensitive=True)

    client.load_extension("admin")
    client.load_extension("vote")
    client.load_extension("configManager")
    client.load_extension("giveaways")

    async def on_ready():
        print('\nBot connecté')
        print("Nom : "+client.user.name)
        print("ID : "+str(client.user.id))
        if len(client.guilds) < 200:
            serveurs = [x.name for x in client.guilds]
            print(
                "Connecté sur ["+str(len(client.guilds))+"] "+", ".join(serveurs))
        else:
            print("Connecté sur "+str(len(client.guilds))+" serveurs")
        print(time.strftime("%d/%m  %H:%M:%S"))
        print('------')
        await asyncio.sleep(2)

    async def check_once(ctx):
        try:
            return ctx.guild != None and ctx.guild.id in [719527687000948797]
        except Exception as e:
            ctx.bot.log.error("ERROR on global_check:", e, ctx.guild)
            return True

    client.add_listener(on_ready)
    # client.add_check(check_once, call_once=True)

    # client.run("NzIzMjUyNzY4MDg0NTkwNjMz.XuvcfQ.siAjI04qNzXGEkHIU6MZ7G-6c-0")
    client.run("NDM2ODM1Njc1MzA0NzU1MjAw.WtnA7Q.z57aMatjIeJwPvee8OtnrSQWT4A")


if __name__ == "__main__":
    main()
