import discord
import os
import json
from dotenv import load_dotenv
from discord.ext import commands
import speech_recognition as sr
import asyncio
from gtts import gTTS
import tempfile

# Type hints for Gemini
try:
    import google.generativeai as genai  # type: ignore
except ImportError:
    raise RuntimeError("google-generativeai not installed. Run: pip install google-generativeai")

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_KEY')

genai.configure(api_key=GEMINI_KEY)  # type: ignore

if GEMINI_KEY is None or DISCORD_TOKEN is None:
    raise RuntimeError("Essential info is missing")

# Bot setup - ONLY ONE INITIALIZATION
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

SETTINGS_FILE = 'bot_settings.json'

default_settings = {  # Fixed typo: defaul -> default
    'personality': 'jarvis',
    'response_length': 'short',
    'emojis': True,
    'creativity_level': 0.8
}

personalities = {
    'spiderman': """You are Spider-Man (Peter Parker), the friendly neighborhood hero!
Personality:
- Friendly and humorous, always cracking jokes, even in serious situations
- Young, energetic, sometimes awkward or nerdy
- Loyal and caring, puts friends and civilians first
- Occasionally sarcastic, but well-meaning
- Uses pop culture references, puns, and playful nicknames like 'dude', 'buddy', or 'man'

Speaking style:
- Casual, conversational, and relatable
- Uses exclamations and humor to keep the mood light
- Optimistic and encouraging
- May include science references or web-slinging puns""",

    'jarvis': """You are Jarvis, Tony Stark's AI assistant.
Personality:
- Extremely intelligent, precise, and logical
- Polite, calm, and formal
- Efficient and helpful, rarely shows emotions
- Loyal to Tony Stark, providing support and advice
- Observant and quick to point out errors or risks

Speaking style:
- Formal, articulate, and precise
- Provides concise, clear explanations and suggestions
- Calm and professional tone, even under pressure
- Occasionally uses subtle dry humor"""
}

# Voice Bot Class
class VoiceBot:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.is_listening = False
        
    async def join_voice(self, ctx):
        """Join the voice channel"""
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            voice_client = await channel.connect()
            return voice_client
        return None
    
    async def text_to_speech(self, text, voice_client):
        """Convert text to speech and play in voice channel"""
        try:
            # Generate speech
            tts = gTTS(text=text, lang='en', slow=False)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                tts.save(fp.name)
                temp_file = fp.name
            
            # Play audio
            voice_client.play(
                discord.FFmpegPCMAudio(temp_file),
                after=lambda e: os.unlink(temp_file) if not e else print(f"Audio error: {e}")
            )
            
            # Wait for audio to finish
            while voice_client.is_playing():
                await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"TTS Error: {e}")
            raise
    
    def process_audio_chunk(self, audio_data):
        """Process audio and convert to text"""
        try:
            # Type ignore for dynamic method
            text = self.recognizer.recognize_google(audio_data)  # type: ignore
            return text
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            return None

voice_bot = VoiceBot()

# Settings Functions
def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'guilds': {}}
    
def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def get_guild_settings(guild_id):  # Fixed typo: settins -> settings
    settings = load_settings()
    guild_str_id = str(guild_id)
    if guild_str_id not in settings['guilds']:
        settings['guilds'][guild_str_id] = default_settings.copy()
        save_settings(settings)
    return settings['guilds'][guild_str_id]

def update_guild_settings(guild_id, key, value):
    settings = load_settings()
    guild_str_id = str(guild_id)  # Fixed typo: guilds_str_id -> guild_str_id
    if guild_str_id not in settings['guilds']:
        settings['guilds'][guild_str_id] = default_settings.copy()
    settings['guilds'][guild_str_id][key] = value 
    save_settings(settings)

def get_model_with_settings(guild_id):
    settings = get_guild_settings(guild_id)
    personality = personalities.get(settings['personality'], personalities['jarvis'])

    length_instructions = {  # Fixed typo: lenght -> length
        'short': '\n- Keep response brief (1-2 sentences when possible)',
        'medium': '\n- Keep response moderate (2-4 sentences)',
        'long': '\n- Provide detailed responses with examples'  # Fixed typo: responces -> responses
    }

    emoji_instruction = '' if settings['emojis'] else '\n- Do not use emojis'

    full_instruction = personality + length_instructions[settings['response_length']] + emoji_instruction
 
    return genai.GenerativeModel(  # type: ignore
        model_name='gemini-2.0-flash-exp',
        system_instruction=full_instruction
    )

# Settings View
class SettingsView(discord.ui.View):
    def __init__(self, guild_id: int, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.guild_id = guild_id
    
    @discord.ui.select(
        placeholder="Choose Personality", 
        options=[
            discord.SelectOption(label="Spider-Man", value="spiderman", emoji="🕷️"),
            discord.SelectOption(label="Jarvis", value="jarvis", emoji="🤖"),
        ]  
    )
    async def personality_select(self, interaction: discord.Interaction, select: discord.ui.Select):  # Fixed typo: personlity -> personality
        update_guild_settings(self.guild_id, 'personality', select.values[0])
        await interaction.response.send_message(
            f"Personality was changed to **{select.values[0].title()}**",
            ephemeral=True
        )
        
    @discord.ui.select(
        placeholder="Choose length of the response",
        options=[
            discord.SelectOption(label="Short", value="short", emoji="📝"),
            discord.SelectOption(label="Medium", value="medium", emoji="📄"),
            discord.SelectOption(label="Long", value="long", emoji="📚")
        ]
    )
    async def response_length_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        update_guild_settings(self.guild_id, 'response_length', select.values[0])
        await interaction.response.send_message(
            f"The response length was changed to **{select.values[0].title()}**",  # Fixed typo: responce -> response
            ephemeral=True
        )
    
    @discord.ui.button(label="Toggle Emoji", style=discord.ButtonStyle.primary)  # Fixed typo: Toogle -> Toggle
    async def emoji_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = get_guild_settings(self.guild_id)
        new_value = not settings['emojis']
        update_guild_settings(self.guild_id, 'emojis', new_value)
        status = 'Enabled' if new_value else 'Disabled'
        await interaction.response.send_message(f"Emojis are **{status}**", ephemeral=True)
    
    @discord.ui.button(label="Reset to Default", style=discord.ButtonStyle.danger)  # Fixed typo: Rest -> Reset
    async def reset_to_default(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = load_settings()
        guild_str_id = str(self.guild_id)
        settings['guilds'][guild_str_id] = default_settings.copy()
        save_settings(settings)
        await interaction.response.send_message('Settings reset to default', ephemeral=True)

# Bot Events
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print(f"📊 Connected to {len(bot.guilds)} guilds")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

# Voice Commands
@bot.command()
async def join(ctx):
    """Join voice channel"""
    try:
        voice_client = await voice_bot.join_voice(ctx)
        if voice_client:
            await ctx.send("✅ Joined voice channel!")
            # Get personality-based greeting
            settings = get_guild_settings(ctx.guild.id)
            if settings['personality'] == 'spiderman':
                greeting = "Hey there! Spider-Man ready to chat!"
            elif settings['personality'] == 'jarvis':
                greeting = "Good day. Jarvis is now online and ready to assist."
            else:
                greeting = "Hello! I'm ready to chat."
            
            await voice_bot.text_to_speech(greeting, voice_client)
        else:
            await ctx.send("❌ You need to be in a voice channel!")
    except Exception as e:
        await ctx.send(f"❌ Error joining voice: {e}")
        print(f"Join error: {e}")

@bot.command()
async def leave(ctx):
    """Leave voice channel"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Left voice channel!")
    else:
        await ctx.send("❌ I'm not in a voice channel!")

@bot.command()
async def say(ctx, *, message: str):
    """Make the bot speak in voice channel"""
    if ctx.voice_client:
        try:
            await voice_bot.text_to_speech(message, ctx.voice_client)
        except Exception as e:
            await ctx.send(f"❌ Error speaking: {e}")
    else:
        await ctx.send("❌ I'm not in a voice channel! Use `!join` first.")

@bot.command()
async def vchat(ctx, *, message: str):
    """Chat with AI and get voice response"""
    if not ctx.voice_client:
        await ctx.send("❌ I'm not in a voice channel! Use `!join` first.")
        return
    
    thinking_message = await ctx.send("🤔 Thinking...")
    try:
        model = get_model_with_settings(ctx.guild.id)
        response = model.generate_content(message)
        
        if not response.text:
            raise RuntimeError("Empty response from Gemini")
        
        # Send text response
        chunks = smart_split(response.text)
        for chunk in chunks:
            await ctx.send(chunk)
        
        # Speak the response
        await voice_bot.text_to_speech(response.text, ctx.voice_client)
        
        await thinking_message.delete()
    except Exception as e:
        await thinking_message.delete()
        await ctx.send(f"❌ Error: {e}")
        print(f"VChat error: {e}")

# Text Commands
@bot.command()
async def settings(ctx):
    """Display and modify bot settings"""
    current_settings = get_guild_settings(ctx.guild.id)
    embed = discord.Embed(
        title='🔧 Bot Settings',
        description='Customize how I respond to you',
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🎭 Current Personality",
        value=f"`{current_settings['personality'].title()}`",
        inline=True
    )
    embed.add_field(
        name="📏 Response Length",
        value=f"`{current_settings['response_length'].title()}`",
        inline=True
    )
    embed.add_field(
        name="😊 Emojis",
        value=f"`{'Enabled' if current_settings['emojis'] else 'Disabled'}`",
        inline=True
    )
    embed.set_footer(text="Use the dropdowns and buttons below to change settings")
    
    view = SettingsView(guild_id=ctx.guild.id)
    await ctx.send(embed=embed, view=view)

@bot.command()
async def chat(ctx, *, message: str):
    """Chat with the AI (text only)"""
    print(f"DEBUG: Message: '{message}' from {ctx.author}")

    thinking_message = await ctx.send("🤔 Thinking...")
    try:
        model = get_model_with_settings(ctx.guild.id)
        response = model.generate_content(message)
        
        if not response.text:
            raise RuntimeError("Empty response from Gemini")
            
        chunks = smart_split(response.text)
        for chunk in chunks:
            await ctx.send(chunk)
            
        await thinking_message.delete()
    except Exception as e:
        await thinking_message.delete()
        await ctx.send(f"❌ Error: {e}")
        print(f"Chat error: {e}")

def smart_split(text, limit=1500):
    """Split text into chunks that fit Discord's message limit"""
    if not text:
        return ["(Empty Response)"]
    
    chunks = []
    current_chunk = ""
    
    for line in text.splitlines(keepends=True):
        if len(current_chunk) + len(line) > limit:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = line
        else:
            current_chunk += line
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks if chunks else [text]

# Main
if __name__ == '__main__':
    print("🚀 Starting bot...")
    print("📝 Make sure FFmpeg is installed for voice features!")
    bot.run(DISCORD_TOKEN)