from discord.ext import commands
from json import load, dump
import os
import re

CONFIG_FOLDER = "configs"


class serverConfig(dict):
    def __init__(self, manager, serverID, value):
        super().__init__(value)
        self.manager = manager
        self.serverID = serverID

    def __getitem__(self, key):
        return super().__getitem__(key)

    def __setitem__(self, key, item):
        super().__setitem__(key, item)
        self.manager[self.serverID] = self

    def __delitem__(self, key):
        super().__delitem__(key)
        self.manager[self.serverID] = self


class ConfigCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.file = "configManager"
        self.confManager = self.configManager()

    class configManager(dict):

        def __init__(self):
            self.servers_list = None
            self.servers_list = self.keys()

        def __setitem__(self, key, item):
            if not (isinstance(key, int) or key.isnumeric()):
                raise ValueError("Key need to be a valid guild ID")
            with open(f"{CONFIG_FOLDER}/{key}.json", "w", encoding="utf8") as f:
                dump(item, f)
            if key not in self.servers_list:
                self.servers_list.append(key)

        def __getitem__(self, key):
            if not (isinstance(key, int) or key.isnumeric()):
                raise ValueError("Key need to be a valid guild ID")
            result = dict()
            try:
                with open(f"{CONFIG_FOLDER}/{key}.json", "r", encoding="utf8") as f:
                    result.update(load(f))
            except FileNotFoundError:
                pass
            return serverConfig(self, key, result)

        def __repr__(self):
            return "<configManager>"

        def __len__(self):
            return len([name for name in self._files() if os.path.isfile(name)])

        def __delitem__(self, key):
            pass

        def has_key(self, k):
            return os.path.isfile(f"{CONFIG_FOLDER}/{k}.json")

        def update(self, *args, **kwargs):
            for arg in args:
                if isinstance(arg, dict):
                    for k, v in arg.items():
                        self.__setitem__(k, v)
            for kwarg in kwargs:
                for k, v in kwarg.items():
                    self.__setitem__(k, v)

        def _files(self):
            p = re.compile('^\d{16,18}.json')
            return [x for x in os.listdir(CONFIG_FOLDER) if p.match(x)]

        def keys(self):
            if self.servers_list == None:
                return [int(name.replace('.json', '')) for name in self._files()]
            else:
                return self.servers_list

        # def values(self):
        #     return self.__dict__.values()

        # def items(self):
        #     return self.__dict__.items()

        # def pop(self, *args):
        #     return self.__dict__.pop(*args)

        def __contains__(self, item):
            return self.has_key(item)


def setup(bot):
    bot.add_cog(ConfigCog(bot))
