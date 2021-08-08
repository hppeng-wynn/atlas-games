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
from discord.ext import tasks

from typing import Union

from game.game_state import GameState
from draw import NORMAL_FONT, BOLD_FONT

class DiscordBot():
    """
    Class handling interactions with the discord bot.
    @see https://discordpy.readthedocs.io/en/stable/quickstart.html
    """

    def __init__(self):
        self._bot_running = False
        self._client = discord.Client()
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

        @self._client.event
        async def on_ready():
            """
            Callback triggered when discord bot is connected.
            """
            print('We have logged in as {0.user}'.format(self._client))
            loop.self = self
            loop.start()

        @self._client.event
        async def on_message(message: discord.Message):
            """
            Callback triggered when a message is sent in a channel viewable by this bot.
            """
            if not self._running:
                return

            if message.author == self._client.user:
                return
            print(f"Message recv: {message.content}")

            if message.content.startswith('$hello'):
                await message.channel.send(f"Hello! I'm on port {SERVER_PORT}")
            if message.content.startswith('$dc'):
                try:
                    port = int(message.content.split(' ', 1)[1].strip())
                    if port == SERVER_PORT:
                        print(f"Disconnecting bot running on port {port}")
                        await message.channel.send(f"Disconnecting bot running on port {port}")
                        self.pause()
                except:
                    await message.channel.send("`$dc PORT`")
            elif message.content.startswith('$host'):
                print("$host: Wait for lock")
                self._bind_channel = message.channel
                await message.channel.send('Bound to '+message.channel.name)
            elif message.content.startswith('$newgame'):
                if self._bind_channel is None:
                    await message.channel.send('atlas-games needs to be bound to a channel first! Use $host')
                else:
                    await message.channel.send('Starting a new round of atlas-games! Use $next to advance and $player to view player stats.')
                    with self._game_lock:
                        self._game = GameState(self._world_data, self._player_data, self._event_data, self.queue_message)

                        def player_highlighter(this: GameState, event: Event, players: List[Player]):
                            imagelist = [p.get_active_image() for p in players]
                            image_size = 64

                            images_width = image_size*len(players)* 1.25 + image_size/4
                            result_height = round(image_size*1.25) + 5

                            text_start_y = result_height
                            event_raw_text = event['text'].format(*(p.name for p in players))
                            text_horiz_chars = max(len(event_raw_text), 40)
                            result_width = int(max(images_width, (text_horiz_chars + 2) *9.6))

                            #TODO compute n_lines, and text, and draw bold/underline...
                            n_lines = 1
                            result_height += 16*n_lines
                            text = event_raw_text

                            result = Image.new(mode='RGBA', size=(result_width, result_height), color=(54, 57, 63))

                            d = ImageDraw.Draw(result)
                            d.multiline_text((5,text_start_y), text, font=NORMAL_FONT, fill=(255, 255, 255))

                            for i in range(len(imagelist)):
                                result.paste(im=imagelist[i], box=(image_size * i + image_size // 4 * (i + 1), image_size // 4), mask=imagelist[i].convert('RGBA'))
                            self.queue_message(result)
                            #self.queue_message(event['text'].format(*(f"__**{p.name}**__" for p in players)))

                        self._game.set_event_printer(player_highlighter)
            elif message.content.startswith('$next'):
                if self._game_lock.acquire(blocking=False):
                    print('Got game lock')
                    if self._game is None:
                        print('No game is running! Start a new game with $newgame.')
                        await message.channel.send('No game is running! Start a new game with $newgame.')
                    else:
                        print('Starting turn')
                        self._game.turn()
                        self.queue_message(f"Alive: {self._game.get_num_alive_players()}, Dead: {self._game.get_num_dead_players()}")
                    self._game_lock.release()
                else:
                    print('Game is busy! Try again soon...')
                    await message.channel.send('Game is busy! Try again soon...')
            elif message.content.startswith('$resume'):
                print("Resuming printout")
                self._message_send_pause = False
            elif message.content.startswith('$player'):
                if self._game is None:
                    await message.channel.send('No game is running! Start a new game with $newgame.')
                else:
                    try:
                        player_name = message.content.split(' ', 1)[1]
                        await message.channel.send(self._game.player_info(player_name))
                    except:
                        await message.channel.send("`$player <playername>`")
            elif message.content.startswith('$help'):
                await message.channel.send(
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

        @self._client.event
        async def on_reaction_add(reaction: discord.Reaction,
                                  user: Union[discord.Member, discord.User]):
            await reaction.message.add_reaction(reaction.emoji)

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
                        if sent_msgs >= 10:
                            self._message_send_pause = True
                            break
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
                if len(buffered_message) > 0:
                    await self._bind_channel.send('\n'.join(buffered_message))
                if self._message_send_pause:
                    await self._bind_channel.send('Paused sending messages -- `$resume` to continue')

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
            self._client.run(os.environ['TOKEN'])
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
