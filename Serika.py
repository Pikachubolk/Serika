import discord
import os
import requests
import base64
from datetime import datetime
from vertexai.preview.generative_models import GenerativeModel, ResponseBlockedError
from vertexai.preview.generative_models import HarmCategory, HarmBlockThreshold
from bs4 import BeautifulSoup
import base64
from dotenv import load_dotenv
from pymongo import MongoClient
import re

# Load environment variables
load_dotenv()
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './gen-lang-client-0092326929-c36ba0ed62fd.json'

# API keys and client tokens
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
MONGO_URI = os.getenv('MONGO_URI')

# Model and bot configurations
model = GenerativeModel("gemini-pro")
generation_config = {
    "max_output_tokens": 1280,
    "temperature": 0.7,
    "top_p": 1,
}
safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
}
intents = discord.Intents.default()
intents.messages = True

class MyBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, intents=intents)
        self.sessions = {}
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client['Serika']
        self.chats_collection = self.db['chats']

    async def on_ready(self):
        print(f'Logged in as {self.user}')

    def load_initial_prompt(self):
        try:
            with open('prompt.txt', 'r', encoding='utf-8') as file:
                return file.read().strip()
        except FileNotFoundError:
            return ""

    def generate_session_id(self, channel_id):
        return str(channel_id)

    async def ensure_chat_session(self, session_id):
        if session_id not in self.sessions:
            initial_prompt = self.load_initial_prompt()
            chat = model.start_chat()
            self.sessions[session_id] = {'chat': chat, 'first_message': True, 'initial_prompt': initial_prompt}
        return self.sessions[session_id]

    def format_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"TIME:({timestamp}) USER ID:{message.author.id} USER NAME:{message.author.display_name} MESSAGE: {message.content}"


    async def on_message(self, message):
        if message.author == self.user:
            return

        youtube_info, spotify_info, webpage_info = "", "", ""
        youtube_url_match = re.search(r'(https?://(?:www\.)?youtube\.com/watch\?v=|https?://youtu\.be/)([\w-]+)', message.content)
        if youtube_url_match:
            video_id = youtube_url_match.group(2)
            youtube_info = self.get_youtube_video_info(video_id)

        spotify_url_match = re.search(r'https?://open.spotify.com/track/([a-zA-Z0-9]+)', message.content)
        if spotify_url_match:
            track_id = spotify_url_match.group(1)
            spotify_info = self.get_spotify_track_info(track_id)

        general_url_match = re.search(r'https?://[^\s]+', message.content)
        if general_url_match and not youtube_url_match and not spotify_url_match:
            url = general_url_match.group(0)
            webpage_info = self.get_webpage_content(url)

        additional_info = "\n".join(filter(None, [youtube_info, spotify_info, webpage_info]))
        if additional_info:
            message.content += f"\n\n{additional_info}"

        bot_mentioned = self.user.mentioned_in(message) and not message.mention_everyone
        contains_keyword = "Serika" in message.content

        if bot_mentioned or contains_keyword:
            session_id = self.generate_session_id(message.channel.id)
            session = await self.ensure_chat_session(session_id)
            formatted_message = self.format_message(message)

            if session['first_message']:
                formatted_message = f"{session['initial_prompt']}\n\n{formatted_message}"
                session['first_message'] = False

            async with message.channel.typing():
                try:
                    response = session['chat'].send_message(
                        formatted_message,
                        generation_config=generation_config,
                        safety_settings=safety_settings
                    )
                    if response.text.strip():
                        await message.reply(response.text)
                    else:
                        await message.reply("I'm not sure how to respond to that.")
                except ResponseBlockedError as e:
                    print(f"Response was blocked: {e}")
                except Exception as e:
                    print(f"Error in on_message: {e}")


    def get_active_chat_id(self):
        """Fetches the active chat ID from the MongoDB database."""
        chat_data = self.chats_collection.find_one({'isActive': True})
        if chat_data:
            return chat_data['channel_id']
        return None

    def add_chat_id(self, channel_id):
        """Adds a new chat ID to the MongoDB database with isActive flag set to True."""
        chat_data = {'channel_id': channel_id, 'isActive': True}
        return self.chats_collection.insert_one(chat_data).inserted_id     

    async def get_youtube_video_info(self, video_id):
        async with self.http_session.get(f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={YOUTUBE_API_KEY}&part=snippet,statistics") as response:
            if response.status == 200:
                data = await response.json()
                items = data.get('items', [])
                if items:
                    snippet = items[0]['snippet']
                    statistics = items[0]['statistics']
                    title = snippet['title']
                    description = snippet['description']
                    upload_date = snippet['publishedAt']
                    tags = snippet.get('tags', "Not available")
                    likes = statistics.get('likeCount', "Not available")
                    views = statistics.get('viewCount', "Not available")
                    return f"Title: {title}, Description: {description}, Upload Date: {upload_date}, Tags: {', '.join(tags)}, Likes: {likes}, Views: {views}"
            return None

    async def get_spotify_access_token(self):
        data = {
            'grant_type': 'client_credentials'
        }
        headers = {
            'Authorization': f'Basic {base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()}'
        }
        async with self.http_session.post('https://accounts.spotify.com/api/token', data=data, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('access_token')
        return None

    async def get_spotify_track_info(self, track_id):
        access_token = await self.get_spotify_access_token()
        if access_token:
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            async with self.http_session.get(f"https://api.spotify.com/v1/tracks/{track_id}", headers=headers) as response:
                if response.status == 200:
                    track_info = await response.json()
                    title = track_info['name']
                    artists = ', '.join(artist['name'] for artist in track_info['artists'])
                    return f"Title: {title}, Artists: {artists}"
        return None

    async def get_webpage_content(self, url):
        try:
            async with self.http_session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                    soup = BeautifulSoup(text, 'html.parser')
                    paragraphs = [p.get_text().strip() for p in soup.find_all('p')]
                    return ' '.join(paragraphs)[:4000]
        except Exception as e:
            print(f"Error fetching webpage content: {e}")
        return None

    async def close(self):
        await super().close()
        await self.http_session.close()



bot = MyBot()
bot.run(DISCORD_BOT_TOKEN)
