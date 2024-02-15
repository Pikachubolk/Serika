import discord
import os
import random
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

    def load_initial_prompt(self):
        try:
            with open('prompt.txt', 'r', encoding='utf-8') as file:
                return file.read().strip()
        except FileNotFoundError:
            print("prompt.txt file not found.")
            return ""

    def generate_session_id(self, channel_id):
        random_id = random.randint(10000, 99999)
        return f"{channel_id}-{random_id}"

    async def ensure_chat_session(self, session_id):
        if session_id not in self.sessions:
            initial_prompt = self.load_initial_prompt()
            chat = self.model.start_chat()
            if initial_prompt:
                chat.send_message(initial_prompt)
            self.sessions[session_id] = chat
        return self.sessions[session_id]

    async def on_message(self, message):
        if message.author == self.user:
            return

        session_id = self.generate_session_id(message.channel.id)
        chat = await self.ensure_chat_session(session_id)

        async with message.channel.typing():
            try:
                response = chat.send_message(message.content)
                await message.channel.send(response.text)
            except Exception as e:
                print(f"Error in on_message: {e}")

bot = MyBot()
bot.run(DISCORD_BOT_TOKEN)
