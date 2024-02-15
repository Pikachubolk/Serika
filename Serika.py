import discord
import os
from dotenv import load_dotenv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import asyncio
from vertexai.preview.generative_models import GenerativeModel
from google.cloud import aiplatform


load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.messages = True

class MyBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, intents=intents)
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.model = GenerativeModel("gemini-pro")
        self.chat_history = []

    async def on_ready(self):
        print(f'Logged in as {self.user}')

    def load_prompt(self):
        with open('prompt.txt', 'r', encoding='utf-8') as file:
            return file.read().strip()

    def append_to_history(self, author, content):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.chat_history.append(f'({timestamp}) {author}: {content}')

    def format_chat_history(self):
        return "\n".join(self.chat_history)

    async def on_message(self, message):
        if message.author == self.user:
            return

        self.append_to_history(message.author.display_name, message.content)

        base_prompt = self.load_prompt()
        conversation_history = self.format_chat_history()
        full_prompt = f"{base_prompt}\n\nConversation History:\n{conversation_history}\n\n{message.author.display_name} (USER):\n{message.content}\n\nBot (YOU):"

        async def get_gemini_response(prompt):
            chat = self.model.start_chat()
            responses = chat.send_message(prompt, stream=True)
            return next(responses).text

        try:
            response_message = await asyncio.get_event_loop().run_in_executor(self.executor, get_gemini_response, full_prompt)
            self.append_to_history("Bot (YOU)", response_message)
            await message.channel.send(response_message)
        except Exception as e:
            print(f"Error: {e}")
            await message.channel.send("Sorry, I can't respond at the moment.")

bot = MyBot()
bot.run(DISCORD_BOT_TOKEN)
