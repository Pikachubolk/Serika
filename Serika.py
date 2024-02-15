import discord
import os
from datetime import datetime
import asyncio
from vertexai.preview.generative_models import GenerativeModel, HarmBlockThreshold, HarmCategory
import vertexai.preview.generative_models as generative_models

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.messages = True

class MyBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, intents=intents)
        self.chat_history = []
        self.model = GenerativeModel("gemini-pro-vision")  # Initialize the model once to reuse

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

    async def generate_response(self, prompt):
        conversation_history = self.format_chat_history()
        full_prompt = f"{prompt}\n\nConversation History:\n{conversation_history}\n\nSerika (YOU):"
        
        responses = self.model.generate_content(
            full_prompt,
            generation_config={
                "max_output_tokens": 2048,
                "temperature": 0.7,
                "top_p": 1,
                "top_k": 32
            },
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            },
            stream=True,
        )
        response_text = next(responses).text  # Assuming synchronous call
        return response_text

    async def on_message(self, message):
        if message.author == self.user:
            return

        self.append_to_history(message.author.display_name, message.content)

        base_prompt = self.load_prompt()
        
        try:
            response_message = await self.generate_response(base_prompt)
            self.append_to_history("Serika (YOU)", response_message)
            await message.channel.send(response_message)
        except Exception as e:
            print(f"Error: {e}")
            await message.channel.send("Sorry, I can't respond at the moment.")

bot = MyBot()
bot.run(DISCORD_BOT_TOKEN)
