import discord
import os
from datetime import datetime
from vertexai.preview.generative_models import GenerativeModel, ResponseBlockedError
from vertexai.preview.generative_models import HarmCategory, HarmBlockThreshold

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.messages = True

generation_config = {
    "max_output_tokens": 300,
    "temperature": 0.7,
    "top_p": 1,
}

safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

class MyBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, intents=intents)
        self.model = GenerativeModel("gemini-pro-vision")
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
        return str(channel_id)

    async def ensure_chat_session(self, session_id):
        if session_id not in self.sessions:
            initial_prompt = self.load_initial_prompt()
            chat = self.model.start_chat()
            self.sessions[session_id] = {'chat': chat, 'first_message': True, 'initial_prompt': initial_prompt}
        return self.sessions[session_id]

    def format_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"TIME:({timestamp}) USER ID:{message.author.id} USER NAME:{message.author.display_name} MESSAGE: {message.content}"

    async def on_message(self, message):
        if message.author == self.user:
            return

        bot_mentioned = self.user.mentioned_in(message) and not message.mention_everyone
        contains_keyword = "Serika" in message.content

        if bot_mentioned or contains_keyword:
            session_id = self.generate_session_id(message.channel.id)
            session = await self.ensure_chat_session(session_id)
            formatted_message = self.format_message(message)

            if session['first_message']:
                formatted_message = f"{session['initial_prompt']}\n\n{formatted_message}\n\n\nYOUR RESPONSE:"
                session['first_message'] = False

            async with message.channel.typing():
                try:
                    response = session['chat'].send_message(
                        formatted_message,
                        generation_config=generation_config,
                        safety_settings=safety_settings
                    )
                    if response.text.strip():
                        await message.channel.send(response.text)
                    else:
                        await message.channel.send("I'm not sure how to respond to that.")
                except ResponseBlockedError as e:
                    print(f"Response was blocked: {e}")
                except Exception as e:
                    print(f"Error in on_message: {e}")

bot = MyBot()
bot.run(DISCORD_BOT_TOKEN)
