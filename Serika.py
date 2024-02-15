import discord
import os
from datetime import datetime
from vertexai.preview.generative_models import GenerativeModel, HarmBlockThreshold, HarmCategory

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.messages = True

class MyBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, intents=intents)
        self.model = GenerativeModel("gemini-pro-vision")
        self.sessions = {}

    async def on_ready(self):
        print(f'Logged in as {self.user}')

    def load_prompt(self):
        with open('prompt.txt', 'r', encoding='utf-8') as file:
            return file.read().strip()

    async def generate_response(self, session_id, prompt):
        if session_id not in self.sessions:
            self.sessions[session_id] = self.model.start_chat()

        session = self.sessions[session_id]

        response = session.generate_response(prompt)
        response_text = response.text
        

        return response_text

    async def on_message(self, message):
        if message.author == self.user:
            return

        async with message.channel.typing():
            base_prompt = self.load_prompt()
            session_id = message.channel.id
            
            try:
                response_message = await self.generate_response(session_id, base_prompt)
                await message.channel.send(response_message)
            except Exception as e:
                print(f"Error: {e}")
                await message.channel.send("Sorry, I can't respond at the moment.")

bot = MyBot()
bot.run(DISCORD_BOT_TOKEN)
