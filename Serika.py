import discord
import os
from vertexai.preview.generative_models import GenerativeModel

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.messages = True

class MyBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, intents=intents)
        self.model = GenerativeModel("gemini-pro")
        self.sessions = {}

    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def ensure_chat_session(self, session_id):
        if session_id not in self.sessions:
            self.sessions[session_id] = self.model.start_chat()
        return self.sessions[session_id]

    async def on_message(self, message):
        if message.author == self.user:
            return

        session_id = message.channel.id  # Use channel ID for session management
        chat = await self.ensure_chat_session(session_id)

        async with message.channel.typing():
            response = chat.send_message(message.content)
            await message.channel.send(response.text)

bot = MyBot()
bot.run(DISCORD_BOT_TOKEN)
