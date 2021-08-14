from __future__ import annotations
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

        self._world_data = json.load(open("game/world_data.json", 'r'))
        self._event_data = json.load(open("game/event_data.json", 'r'))
        self._player_data = json.load(open("game/players_full.json", 'r'))
        self._game_lock = Lock()
        self._game = None

        @self._bot.event
        async def on_ready():
            """
            Callback triggered when discord bot is connected.
            """
            print('We have logged in as {0.user}'.format(self._bot))
            loop.self = self
            loop.start()

        @self._bot.event
        async def on_message(message: discord.Message):
            """
            Callback triggered when a message is sent in a channel viewable by this bot.
            """
            if not self._running:
                return

            if message.author == self._bot.user:
                return
            print(f"Message recv: {message.content}")
            await self._bot.process_commands(message)

        @self._bot.command(name='hello')
        async def hello(ctx):
            await ctx.send(f"Hello! I'm on port {SERVER_PORT}")

        @self._bot.command(name='dc')
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

        @self._bot.command(name='host')
        async def host(ctx):
            print("$host: Wait for lock")
            self._bind_channel = ctx.channel
            await ctx.send('Bound to '+ctx.channel.name)

        @self._bot.command(name='newgame', aliases=['ng'])
        async def newgame(ctx):
            if self._bind_channel is None:
                await ctx.send('atlas-games needs to be bound to a channel first! Use $host')
            else:
                await ctx.send('Starting a new round of atlas-games! Use $next to advance and $player to view player stats.')
                with self._game_lock:
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
                    print('Starting turn')
                    self._game.turn()
                    self.queue_message(f"Alive: {self._game.get_num_alive_players()}, Dead: {self._game.get_num_dead_players()}")
                    self.queue_message(self._game.print_map())
                self._game_lock.release()
            else:
                print('Game is busy! Try again soon...')
                await ctx.send('Game is busy! Try again soon...')

        @self._bot.command(name='resume', aliases=['r'])
        async def resume(ctx):
            print("Resuming printout")
            self._message_send_pause = False

        @self._bot.event
        async def on_reaction_add(reaction: discord.Reaction,
                                  user: Union[discord.Member, discord.User]):
            context = await self._bot.get_context(reaction.message)
            if user.bot:
                return
            if self._message_send_pause:
                if reaction.emoji == "▶️" and reaction.message.content.find("`$resume`") != -1:
                    await resume(context)
#                 if reaction.emoji == "⏭️" and reaction.message.content.find("`$next`") != -1:
#                     await next_turn(context)
                    
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
        async def help_menu(ctx):
            await ctx.send(
f'''{ATLAS} **Welcome to atlas games!** {ATLAS}
here are a few helpful commands: ```ARM
$hello -- pings the bot, returns the current hosting port (debug use)
$dc <port> -- disconnect the bot running on the specified port (debug use)
$host -- binds the bot to the current channel
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
                    if sent_msgs >= 5:
                        self._message_send_pause = True
                        break
                if len(buffered_message) > 0:
                    await self._bind_channel.send('\n'.join(buffered_message))
                if self._message_send_pause:
                    resume_message = await self._bind_channel.send('Paused sending messages -- type `$resume` or react ▶️ to resume')
                    await resume_message.add_reaction("▶️")

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
