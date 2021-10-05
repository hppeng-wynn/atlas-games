from __future__ import annotations

from functools import wraps
import json

import requests

from emojis import ATLAS

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread, Lock
import time
import asyncio
import json
from io import BytesIO
from PIL import Image, ImageDraw
from queue import Queue

import os
SERVER_PORT = int(os.environ['PORT'])

import discord
from discord.ext import tasks, commands

from typing import Union

from game.game_state import GameState
from draw import NORMAL_FONT, break_text, render_text

PLAYER_DAT_FILE = "atlas-games_store/players.json"

class DiscordBot():
    """
    Class handling interactions with the discord bot.
    @see https://discordpy.readthedocs.io/en/stable/quickstart.html
    """

    def __init__(self):
        self._bot = commands.Bot(command_prefix='$', help_command=None)

        self._bot_running = False
        # self._client = discord.Client()
        # Message queue for things to send (text for now)
        self._messages = Queue()
        self._message_send_pause = False
        self._bind_channel = None
        self._running = True

        self._game_lock = Lock()
        self._game = None
        self._github_guild_id = None
        self._github_init = False

        item_dat = json.loads(requests.get("https://wynnbuilder.github.io/compress.json").text)
        self.id_map = {}
        for item in item_dat["items"]:
            self.id_map[item["id"]] = item
        self.current_entry = None
        b64_digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-"
        self.b64_reverse = {c: i for i, c in enumerate(b64_digits)}
        self.research_mode = False

        def toInt(digits):
            result = 0;
            for digit in digits:
                result = (result << 6) + self.b64_reverse[digit]
            return result
        def toIntSigned(digits):
            result = 0;
            if self.b64_reverse[digits[0]] & 0x20:
                result = -1
            for digit in digits:
                result = (result << 6) + self.b64_reverse[digit]
            return result

        def binding(f):
            @wraps(f)
            async def wrapper(ctx, *args, **kwargs):
                if self.research_mode:
                    return
                if self._bind_channel is None:
                    self._bind_channel = ctx.channel
                    await ctx.send('Bound to '+ctx.channel.name)
                return await f(ctx, *args, **kwargs)
            return wrapper

        def github_init(f):
            @wraps(f)
            async def wrapper(ctx, *args, **kwargs):
                if not self._github_init:
                    #TODO error check
                    guild = ctx.guild
                    guild_id: int = guild.id
                    os.system(f"sh github_init.sh {guild_id}")
                    self._github_init = True
                return await f(ctx, *args, **kwargs)
            return wrapper

        def github_init_research(f):
            @wraps(f)
            async def wrapper(ctx, *args, **kwargs):
                if not self._github_init:
                    #TODO error check
                    guild = ctx.guild
                    os.system("sh github_init.sh research")
                    self._github_init = True
                    self.research_mode = True
                return await f(ctx, *args, **kwargs)
            return wrapper

        @self._bot.event
        async def on_ready():
            """
            Callback triggered when discord bot is connected.
            """
            print('We have logged in as {0.user}'.format(self._bot))
            loop.self = self
            loop.start()

        def simplify_item(item):
            keys = ["id", "tier", "type", "str", "dex", "int", "def", "agi",  "strReq", "dexReq", "intReq", "defReq", "agiReq"]
            simplified_item = {key: item.get(key, 0) for key in keys}
            simplified_item["name"] = get_name(item)
            return simplified_item

        def get_name(item):
            if "displayName" in item:
                return item["displayName"]
            return item["name"]

        @self._bot.command(name='build')
        @github_init_research
        async def build(ctx, url: str):
            wb_hash = url.split('_')[1]
            equips = [None]*9
            slots = ["Helmet", "Chestplate", "Leggings", "Boots", "Ring 1", "Ring 2", "Bracelet", "Necklace"]
            skillpoints = [0]*5
            # Hard coded to v5 protocol
            start_idx = 0
            for i in range(len(equips)):
                equipment_str = wb_hash[start_idx:start_idx+3]
                item_id = toInt(equipment_str)
                if item_id not in self.id_map:
                    equips[i] = {"id": -1, "name": "No "+slots[i]}
                    continue
                item = self.id_map[item_id]
                equips[i] = simplify_item(item)
                start_idx += 3;
            wb_hash = wb_hash[start_idx:]
            skillpoint_info = wb_hash[:10]
            for i in range(5):
                skillpoints[i] = toIntSigned(skillpoint_info[i+i:i+i+2])

            build = {"equips": equips, "sp": skillpoints}
            self.current_entry = {"build": build, "add": None, "pops": []}
            await ctx.send("Set build: " + str([e['name'] for e in equips]))

        @build.error
        async def build_error(ctx, error):
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("`$build <wynnbuilder_url>`")
            else:
                await ctx.send(str(error))

        @self._bot.command(name='add')
        async def add(ctx, item_name: str):
            if self.current_entry is None:
                await ctx.send("Set a build first with `$build`")
                return
            for item in self.id_map.values():
                if get_name(item).lower() == item_name.lower():
                    self.current_entry["add"] = simplify_item(item)
                    self.current_entry["pops"] = []
                    await ctx.send("Set add item, reset pops")
                    return
            await ctx.send("Item not found")

        @add.error
        async def add_error(ctx, error):
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("`$add <item_name_ignorecase>`")

        @self._bot.command(name='pop')
        async def pop(ctx, slot: str, skillpoint: str):
            if self.current_entry is None:
                await ctx.send("Set a build first with `$build`")
                return
            if self.current_entry["add"] is None:
                await ctx.send("Set the added item first with `$add`")
                return
            slot = slot.lower()
            alias_list = (("boots", "boot"),
                        ("leggings", "legs", "leg"),
                        ("chestplate", "chest", "cp"),
                        ("helmet", "helm"),
                        ("ring1", "r1"),
                        ("ring2", "r2"),
                        ("bracelet", "brace"),
                        ("necklace", "neck"))
            alias_map = {}
            for dat in alias_list:
                if dat[0] == slot:
                    break
                done = False
                for alias in dat[1:]:
                    if alias == slot:
                        slot = dat[0]
                        done = True
                        break
                if done:
                    break
            slots = ["boots", "leggings", "chestplate", "helmet", "ring1", "ring2", "bracelet", "necklace"]
            if slot not in slots:
                await ctx.send("Invalid slot, pick from " + str(slots))
                return
            skillpoint = skillpoint.lower()
            skillpoints = ["str", "dex", "int", "def", "agi"]
            if skillpoint not in skillpoints:
                await ctx.send("Invalid skillpoint, pick from " + str(skillpoints))
                return
            self.current_entry["pops"].append((slot, skillpoint))
            await ctx.send(f"Added pop ({slot}, {skillpoint})")

        @pop.error
        async def pop_error(ctx, error):
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("`$pop <slot_ignorecase> <skillpoint_ignorecase>`")
            else:
                await ctx.send(str(error))

        @self._bot.command(name='save')
        async def save(ctx):
            with open(PLAYER_DAT_FILE, 'r') as build_file:
                build_data = json.load(build_file)
            if not isinstance(build_data, list):
                build_data = []
            build_data.append(self.current_entry)
            with open(PLAYER_DAT_FILE, 'w') as write_file:
                json.dump(build_data, write_file)
            os.system(f"sh github_update.sh research")
            self.current_entry["add"] = None
            self.current_entry["pops"] = []
            await ctx.send("Saved data (cleared add and pops)")

        @self._bot.command(name='hello')
        @binding
        async def hello(ctx):
            await ctx.send(f"Hello! I'm on port {SERVER_PORT}")

        @self._bot.command(name='github_nuke')
        @binding
        async def github_nuke(ctx):
            os.system("sh github_nuke.sh")
            await ctx.send(f"Nuked git repo")

        @self._bot.command(name='register')
        @binding
        @github_init
        async def register(ctx):
            player = ctx.author
            player_id = str(player.id)
            player_name = player.name
            player_img = str(player.avatar_url)
            player_obj = {
                    "name": player_name,
                    "img": player_img,
                    "active": True
                }
            with open(PLAYER_DAT_FILE, 'r') as player_file:
                player_data = json.load(player_file)

            player_data[player_id] = player_obj

            with open(PLAYER_DAT_FILE, 'w') as write_file:
                json.dump(player_data, write_file)
            os.system(f"sh github_update.sh {ctx.guild.id}")
            await ctx.send(f"{player_name}, Registered succesfully!")

        @self._bot.command(name='listplayers')
        @binding
        @github_init
        async def listplayers(ctx):
            with open(PLAYER_DAT_FILE, 'r') as player_file:
                player_data = json.load(player_file)
            for player in player_data.values():
                self.queue_message(player["name"])

        @self._bot.command(name='dc')
        @binding
        async def dc(ctx, port: int):
            if port == SERVER_PORT:
                print(f"Disconnecting bot running on port {port}")
                await ctx.send(f"Disconnecting bot running on port {port}")
                self.pause()
            else:
                await ctx.send(f"Wrong port. The bot is currently running on port {SERVER_PORT}")

        @dc.error
        async def dc_error(ctx, error):
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("`$dc <PORT>`")
            elif isinstance(error, commands.BadArgument):
                await ctx.send('Please verify that `<PORT>` is an integer.')

        @self._bot.command(name='newgame', aliases=['ng'])
        @binding
        @github_init
        async def newgame(ctx):
            if self._bind_channel is None:
                await ctx.send('atlas-games needs to be bound to a channel first! Use $host')
            else:
                await ctx.send('Starting a new round of atlas-games! Use $next to advance and $player to view player stats.')
                with self._game_lock:
                    self._world_data = json.load(open("game/world_data.json", 'r'))
                    self._event_data = json.load(open("game/event_data.json", 'r'))
                    self._player_data = json.load(open(PLAYER_DAT_FILE, 'r'))
                    self._game = GameState(self._world_data, self._player_data, self._event_data, self.queue_message)

                    def player_highlighter(this: GameState, event_data):
                        ascent, descent = NORMAL_FONT.normal.getmetrics()
                        line_height = ascent + descent
                        image_size = 64

                        batch_width = 500
                        batch_height = 0
                        # Tuple(y, images, text)
                        render_batch = []
                        dummy_image = Image.new(mode='RGBA', size=(1000, 50), color=(54, 57, 63))
                        dummy_draw = ImageDraw.Draw(dummy_image)
                        for idx, (event, event_type, players) in enumerate(event_data):
                            imagelist = [p.get_active_image() for p in players]

                            images_width = image_size*len(players)* 1.25 + image_size/4
                            result_height = round(image_size*1.25) + 5

                            event_raw_text, n_lines = break_text(event['text'].format(*(f"\\*{p.name}\\*" for p in players)), dummy_draw, NORMAL_FONT, batch_width)
                            print(event_raw_text)

                            result_height += line_height*n_lines
                            render_batch.append((batch_height, imagelist, event_raw_text))
                            batch_height += result_height

                            if len(render_batch) == 5 or idx == len(event_data) - 1:
                                result = Image.new(mode='RGBA', size=(batch_width, batch_height), color=(54, 57, 63))
                                d = ImageDraw.Draw(result)
                                for y, images, text in render_batch:
                                    text_start_y = y + round(image_size * 1.25) + 5
                                    render_text(text, result, d, NORMAL_FONT, (0, text_start_y), (255,255,255))
                                    for i, image  in enumerate(images):
                                        result.paste(im=image, box=(int(i*image_size*1.25) + image_size//4, y+image_size // 4), mask=image.convert('RGBA'))
                                self.queue_message(result)
                                batch_height = 0
                                render_batch = []

                    self._game.set_event_printer(player_highlighter)

        @self._bot.command(name='next', aliases=['n'])
        async def next_turn(ctx):
            if self._game_lock.acquire(blocking=False):
                print('Got game lock')
                if self._game is None:
                    print('No game is running! Start a new game with $newgame.')
                    await ctx.send('No game is running! Start a new game with $newgame.')
                else:
                    if self._game.get_num_alive_players() <= 1:
                        if self._game._players:
                            for player_name in self._game._players:
                                await ctx.send(f"The winner is **{player_name}**!")
                                self._game = None
                                self._message_send_pause = False
                                self._game_lock.release()
                                return
                        else:
                            await ctx.send("What a tragedy! no winners this time around.")
                            self._game = None
                            self._message_send_pause = False
                            self._game_lock.release()
                            return
                    print('Starting turn')
                    self._game.turn()
                    self.queue_message(
                        f"Alive: {self._game.get_num_alive_players()}, Dead: {self._game.get_num_dead_players()}")
                    self.queue_message(self._game.print_map())
                    self.queue_message(
                        "Day concluded --- type `$next` or react ⏭️ to continue")
                self._game_lock.release()
            else:
                print('Game is busy! Try again soon...')
                await ctx.send('Game is busy! Try again soon...')

        @self._bot.command(name='resume', aliases=['r'])
        async def resume(ctx):
            print("Resuming printout")
            self._message_send_pause = False
        
        @self._bot.event
        async def on_message(message):
            """
            Callback triggered when a message is sent in a channel viewable by this bot.
            adds reactions to messages containing "`$next`" and "`$resume`"
            """
            if not self._running:
                return

            if "`$next`" in message.content:
                await message.add_reaction("⏭️")
            if "`$resume`" in message.content:
                await message.add_reaction("▶️")

            if message.author == self._bot.user:
                return

            await self._bot.process_commands(message)

        @self._bot.event
        async def on_reaction_add(reaction: discord.Reaction,
                                  user: Union[discord.Member, discord.User]):
            """
            Activates "$next" and "$resume" via reactions
            """                          
            context = await self._bot.get_context(reaction.message)
            if user.bot:
                return
            if self._message_send_pause:
                if reaction.emoji == "▶️" and ("`$resume`" in reaction.message.content):
                    await resume(context)
            if reaction.emoji == "⏭️" and ("`$next`" in reaction.message.content):
                await next_turn(context)
                    
        @self._bot.command(name='player', aliases=['p'])
        async def player_info(ctx, player_name):
            if self._game is None:
                await ctx.send('No game is running! Start a new game with $newgame.')
            else:
                try:
                    await ctx.send(self._game.player_info(player_name))
                except:
                    await ctx.send("`$player <playername>`")

        @self._bot.command(name='help')
        @binding
        async def help_menu(ctx):
            await ctx.send(
f'''{ATLAS} **Welcome to atlas games!** {ATLAS}
here are a few helpful commands: ```ARM
$hello -- pings the bot, returns the current hosting port (debug use)
$dc <port> -- disconnect the bot running on the specified port (debug use)
$newgame -- only after the bot is bound, starts a new round of atlas games
$next -- starts the next day given that a game is already running
$resume -- resume printing
$player <playername> -- returns the statistics of a player
```''')

        @tasks.loop(seconds=1.0)
        async def loop():
            """
            Loop function for the bot. Since I can't send messages from other threads
            (something about asyncio) using this as an in-between.
            For now: Reads messages out of the message queue (can be filled by other threads)
            and spits them out into the bound channel.
            """
            self = loop.self
            print(f"Heartbeat: {time.time()}")
            if not self._running:
                return
            elif self._message_send_pause:
                return

            if self._bind_channel is not None:
                buffered_message = []
                buffered_msg_len = 0
                sent_msgs = 0
                while not self._messages.empty():
                    content = self._messages.get()
                    if isinstance(content, str):
                        buffered_msg_len += len(content) + 1
                        if len(buffered_message) == 0:
                            sent_msgs += 1
                        buffered_message.append(content)
                        if buffered_msg_len > 1000:
                            await self._bind_channel.send('\n'.join(buffered_message))
                            buffered_message = []
                    else:
                        if len(buffered_message) > 0:
                            await self._bind_channel.send('\n'.join(buffered_message))
                            buffered_message = []

                        if isinstance(content, Image.Image):
                            with BytesIO() as image_binary:
                                content.save(image_binary, 'PNG')
                                image_binary.seek(0)
                                await self._bind_channel.send(file=discord.File(fp=image_binary, filename='content.png'))
                            sent_msgs += 1
                    if sent_msgs >= 5 and not self._messages.empty():
                        self._message_send_pause = True
                        break
                if len(buffered_message) > 0:
                    await self._bind_channel.send('\n'.join(buffered_message))
                if self._message_send_pause:
                    await self._bind_channel.send('Paused sending messages -- type `$resume` or react ▶️ to resume')

    def queue_message(self, content) -> bool:
        """
        Queue a new message to be sent by the bot.
        Return: True on success, false if bot is not running.
        """
        if not self._running:
            return False

        self._messages.put(content)
        return True

    def start(self):
        self._running = True

    def pause(self):
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def run(self):
        """
        Run the bot. Starts an HTTP server in another thread to listen for input
        from the dashboard.
        """
        try:
            start_server(SERVER_PORT)
            self._bot.run(os.environ['TOKEN'])
        except Exception as e:
            print(e)
            print("exiting")

BOT_OBJ = DiscordBot()

class RequestHandler(SimpleHTTPRequestHandler):
    """
    Simple HTTP request handler. TODO: probably extend SimpleHTTPRequestHandler instead
    to allow easier html/js/css blargh
    For now the only endpoint of interest is /ping
        (sends a "Pong!" message to the bot's bound channel)
    """

    def do_GET(self):
        """
        Handle an HTTP GET request.
        @see https://docs.python.org/3/library/http.server.html
        (or google since this docs page is kinda bad)
        """
        path = self.path
        if path.startswith("/api/"):
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            path = path[5:]
            if path == "ping":
                message = "pong"
                BOT_OBJ.queue_message("Pong!")
            elif path == "start":
                message = "Listening on discord"
                BOT_OBJ.start()
            elif path == "pause":
                message = "Pausing bot"
                BOT_OBJ.pause()
            elif path == "status":
                message = "Running status: " + str(BOT_OBJ.is_running())
            elif path == "summary" and BOT_OBJ.research_mode:
                with open(PLAYER_DAT_FILE, 'r') as build_file:
                    build_data = json.load(build_file)
                entries = []
                for entry in build_data:
                    build = entry["build"]
                    val = '["'+'", "'.join(build['equips'])+'"]' + str(build['skillpoints']) + ' + ' + entry['add']['name'] + '->'
                    val += ', '.join(build['pops'])
                    entries.append(val)
                message = '\n'.join(sorted(entries))
            else:
                message = "/api/help"
            self.wfile.write(bytes(message, "utf8"))

        else:
            # IS THIS SECURE? TODO
            for suffix in [".html", ".js", ".css", ".txt"]:
                if path.endswith(suffix):
                    return super().do_GET()
            self.send_error(403)

def start_server(port: int):
    """
    Start an http server on a separate thread.
    TODO: separate process much?
    """
    print(f"Starting on port {port}")
    server = ThreadingHTTPServer(('', port), RequestHandler)
    serve_thread = Thread(group=None, target=server.serve_forever)
    serve_thread.start()

if __name__ == "__main__":
    BOT_OBJ.run()
