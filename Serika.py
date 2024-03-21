import discord
import os
from datetime import datetime
from vertexai.preview.generative_models import GenerativeModel, ResponseBlockedError
from vertexai.preview.generative_models import HarmCategory, HarmBlockThreshold
from bs4 import BeautifulSoup
import requests
import base64


# Initialize Vertex AI Model
model = GenerativeModel("gemini-pro-vision") 

# Configuration values
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Default settings
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

intents = discord.Intents.default()
intents.messages = True


class MyBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, intents=intents)
        self.sessions = {}

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

    def get_youtube_video_info(self, video_id):
        youtube_api_url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={YOUTUBE_API_KEY}&part=snippet,statistics"
        response = requests.get(youtube_api_url)
        if response.status_code == 200:
            data = response.json()
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

    def get_spotify_access_token(self):
        auth_response = requests.post(
            'https://accounts.spotify.com/api/token',
            data={
                'grant_type': 'client_credentials'
            },
            headers={
                'Authorization': f'Basic {base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()}'
            }
        )
        if auth_response.status_code == 200:
            return auth_response.json().get('access_token')
        return None

    def get_spotify_track_info(self, track_id):
        access_token = self.get_spotify_access_token()
        if access_token:
            spotify_api_url = f"https://api.spotify.com/v1/tracks/{track_id}"
            response = requests.get(
                spotify_api_url,
                headers={
                    'Authorization': f'Bearer {access_token}'
                }
            )
            if response.status_code == 200:
                track_info = response.json()
                title = track_info['name']
                artists = ', '.join(artist['name'] for artist in track_info['artists'])
                return f"Title: {title}, Artists: {artists}"
        return None

    def get_webpage_content(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                paragraphs = [p.get_text().strip() for p in soup.find_all('p')]
                text = ' '.join(paragraphs)
                return text[:2000]  # Limit output for brevity
        except Exception as e:
            print(f"Error fetching webpage content: {e}")
            return None

bot = MyBot()
bot.run(DISCORD_BOT_TOKEN)
