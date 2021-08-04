from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread, Lock
import time
import asyncio

import os
SERVER_PORT = int(os.environ['PORT'])

import discord
from discord.ext import tasks

class DiscordBot():
    """
    Class handling interactions with the discord bot.
    @see https://discordpy.readthedocs.io/en/stable/quickstart.html
    """

    def __init__(self):
        self._bot_running = False
        self._client = discord.Client()
        # Message queue for things to send (text for now)
        self._message_lock = Lock()
        self._messages = []
        self._bind_channel = None

        @self._client.event
        async def on_ready():
            """
            Callback triggered when discord bot is connected.
            """
            print('We have logged in as {0.user}'.format(self._client))
            loop.start()

        @self._client.event
        async def on_message(message):
            """
            Callback triggered when a message is sent in a channel viewable by this bot.

            Behavior for now:
            - $hello: ping (sends "Hello!" message)
            - $bind:  bind bot to current channel
            """
            if message.author == self._client.user:
                return

            if message.content.startswith('$hello'):
                await message.channel.send('Hello!')
            elif message.content.startswith('$deez'):
                await message.channel.send('nuts')
                await message.channel.send(type(message.content))
            elif message.content.startswith('$bind'):
                self._bind_channel = message.channel
                await message.channel.send('Bound to '+message.channel.name)

        @tasks.loop(seconds=1.0)
        async def loop():
            """
            Loop function for the bot. Since I can't send messages from other threads
            (something about asyncio) using this as an in-between.

            For now: Reads messages out of the message queue (can be filled by other threads)
            and spits them out into the bound channel.
            """
            if self._bind_channel is not None:
                with self._message_lock:
                    for text in self._messages:
                        await self._bind_channel.send(text)
                    self._messages = []

    def queue_message(self, text):
        """
        Queue a new message to be sent by the bot.
        """
        with self._message_lock:
            self._messages.append(text)

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
                BOT_OBJ.queue_message("Pong!")

            message = "Hello, World! " + path
            self.wfile.write(bytes(message, "utf8"))

        else:
            # IS THIS SECURE? TODO
            for suffix in [".html", ".js", ".css"]:
                if path.endswith(suffix):
                    return super().do_GET()
            self.send_error(403)

def start_server(port):
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
