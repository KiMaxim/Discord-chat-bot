import discord
import os
import json
from dotenv import load_dotenv
from discord.ext import commands
import google.generativeai as genai

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_KEY')

genai.configure(api_key=GEMINI_KEY)

if DISCORD_TOKEN is None:
    raise RuntimeError("DISCORD_TOKEN is missing!")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Settings storage
SETTINGS_FILE = 'bot_settings.json'

# Default settings
default_settings = {
    'personality': 'luna',  # luna, wizard, pirate, professional
    'response_length': 'medium',  # short, medium, long
    'use_emojis': True,
    'temperature': 0.7  # 0.0 to 1.0 (creativity level)
}

# Load settings from file
def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'guilds': {}}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def get_guild_settings(guild_id):
    settings = load_settings()
    guild_id_str = str(guild_id)
    if guild_id_str not in settings['guilds']:
        settings['guilds'][guild_id_str] = default_settings.copy()
        save_settings(settings)
    return settings['guilds'][guild_id_str]

def update_guild_setting(guild_id, key, value):
    settings = load_settings()
    guild_id_str = str(guild_id)
    if guild_id_str not in settings['guilds']:
        settings['guilds'][guild_id_str] = default_settings.copy()
    settings['guilds'][guild_id_str][key] = value
    save_settings(settings)

# Personality presets
personalities = {
    'spiderman': """You are Spider-Man (Peter Parker), the friendly neighborhood hero!
    Personality:
    - Witty and makes jokes even in serious situations
    - Uses pop culture references and puns constantly
    - Calls people "dude", "man", or "buddy"
    - Youthful energy and enthusiasm
    - Sometimes nerdy with science references
    Speaking style:
    - Casual and conversational
    - Self-deprecating humor
    - Optimistic even when things are tough
    - "With great power comes great responsibility" mindset
    - Web-slinging and spider-themed puns""",
    
    'ironman': """You are Tony Stark / Iron Man, genius billionaire playboy philanthropist.
    Personality:
    - Sarcastic and witty with a sharp tongue
    - Extremely confident, sometimes arrogant
    - Uses tech references and engineering terminology
    - Calls people "kid", uses nicknames for everyone
    - Quick thinker, always has a clever comeback
    Speaking style:
    - Fast-paced and energetic
    - Snarky humor and one-liners
    - References to his tech, suits, and inventions
    - "I am Iron Man" confidence
    - Sometimes mentions Jarvis, suits, or arc reactor""",
    
    'captainamerica': """You are Steve Rogers / Captain America, the First Avenger.
    Personality:
    - Noble, honorable, and principled
    - Inspirational and encouraging
    - Strong moral compass and leadership qualities
    - Occasionally confused by modern references (was frozen since 1940s)
    - Respectful and polite, calls people "soldier" or by their name
    Speaking style:
    - Clear and direct communication
    - Motivational and uplifting
    - Sometimes uses old-fashioned phrases ("back in my day")
    - "I can do this all day" determination
    - References to duty, honor, and doing the right thing""",
    
    'luna': """You are Luna, a cheerful and helpful AI assistant!
    Personality:
    - Always enthusiastic and uses exclamation marks
    - Makes puns occasionally
    - Refers to users as 'friend' or 'buddy'
    Speaking style:
    - Casual and friendly tone
    - Keeps responses concise but warm""",
    
    'wizard': """You are Merlin, a wise old wizard.
    Personality:
    - Use archaic language occasionally ("thou", "thee", "mayhaps")
    - Reference magic and spells in explanations
    - Wise but has a good sense of humor
    Speaking style:
    - Mystical and educational
    - Sometimes cryptic but ultimately helpful""",
    
    'pirate': """You are Captain Blackbeard, a friendly pirate.
    Personality:
    - Talk like a pirate (arr, matey, ye)
    - Reference sailing and treasure
    - Adventurous and bold
    Speaking style:
    - Nautical terms and pirate slang
    - Enthusiastic and colorful language""",
    
    'professional': """You are a professional AI assistant.
    Personality:
    - Polite and formal
    - Focus on accuracy and clarity
    - Respectful and courteous
    Speaking style:
    - Clear and concise
    - Professional tone
    - Well-structured responses"""
}

def get_model_with_settings(guild_id):
    settings = get_guild_settings(guild_id)
    personality = personalities.get(settings['personality'], personalities['luna'])
    
    # Add response length instruction
    length_instructions = {
        'short': '\n- Keep responses brief (1-2 sentences when possible)',
        'medium': '\n- Keep responses moderate length (2-4 sentences)',
        'long': '\n- Provide detailed responses with examples'
    }
    
    # Add emoji instruction
    emoji_instruction = '' if settings['use_emojis'] else '\n- Do not use emojis'
    
    full_instruction = personality + length_instructions[settings['response_length']] + emoji_instruction
    
    return genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        system_instruction=full_instruction
    )

# Settings View using Discord UI
class SettingsView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=180)  # 3 minute timeout
        self.guild_id = guild_id
    
    @discord.ui.select(
        placeholder="Choose Personality",
        options=[
            discord.SelectOption(label="Spider-Man", value="spiderman", emoji="🕷️"),
            discord.SelectOption(label="Iron Man", value="ironman", emoji="🤖"),
            discord.SelectOption(label="Captain America", value="captainamerica", emoji="🛡️"),
            discord.SelectOption(label="Luna (Cheerful)", value="luna", emoji="🌙"),
            discord.SelectOption(label="Wizard (Mystical)", value="wizard", emoji="🧙"),
            discord.SelectOption(label="Pirate (Adventurous)", value="pirate", emoji="🏴‍☠️"),
            discord.SelectOption(label="Professional", value="professional", emoji="💼")
        ]
    )
    async def personality_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        update_guild_setting(self.guild_id, 'personality', select.values[0])
        await interaction.response.send_message(
            f"✅ Personality changed to **{select.values[0].title()}**!",
            ephemeral=True
        )
    
    @discord.ui.select(
        placeholder="Response Length",
        options=[
            discord.SelectOption(label="Short", value="short", emoji="📝"),
            discord.SelectOption(label="Medium", value="medium", emoji="📄"),
            discord.SelectOption(label="Long", value="long", emoji="📚")
        ]
    )
    async def length_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        update_guild_setting(self.guild_id, 'response_length', select.values[0])
        await interaction.response.send_message(
            f"✅ Response length set to **{select.values[0]}**!",
            ephemeral=True
        )
    
    @discord.ui.button(label="Toggle Emojis", style=discord.ButtonStyle.primary, emoji="😊")
    async def emoji_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = get_guild_settings(self.guild_id)
        new_value = not settings['use_emojis']
        update_guild_setting(self.guild_id, 'use_emojis', new_value)
        status = "enabled" if new_value else "disabled"
        await interaction.response.send_message(
            f"✅ Emojis **{status}**!",
            ephemeral=True
        )
    
    @discord.ui.button(label="Reset to Default", style=discord.ButtonStyle.danger, emoji="🔄")
    async def reset_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = load_settings()
        settings['guilds'][str(self.guild_id)] = default_settings.copy()
        save_settings(settings)
        await interaction.response.send_message(
            "✅ Settings reset to default!",
            ephemeral=True
        )

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.command()
async def settings(ctx):
    """Open the settings menu"""
    current_settings = get_guild_settings(ctx.guild.id)
    
    embed = discord.Embed(
        title="⚙️ Bot Settings",
        description="Customize how I respond to you!",
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
        value=f"`{'Enabled' if current_settings['use_emojis'] else 'Disabled'}`",
        inline=True
    )
    
    embed.set_footer(text="Use the dropdowns and buttons below to change settings")
    
    view = SettingsView(ctx.guild.id)
    await ctx.send(embed=embed, view=view)

@bot.command()
async def viewsettings(ctx):
    """View current settings in detail"""
    settings = get_guild_settings(ctx.guild.id)
    
    embed = discord.Embed(
        title="📋 Current Settings",
        color=discord.Color.green()
    )
    
    for key, value in settings.items():
        embed.add_field(name=key.replace('_', ' ').title(), value=f"`{value}`", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def chat(ctx, *, message: str):
    thinking_msg = await ctx.send('Thinking...')
    
    try:
        # Get model with current settings
        model = get_model_with_settings(ctx.guild.id)
        response = model.generate_content(message)
        
        await thinking_msg.delete()
        
        chunks = smart_split(response.text)
        for chunk in chunks:
            await ctx.send(chunk)
            
    except Exception as er:
        await thinking_msg.delete()
        await ctx.send("Gemini is not responding, blame Google 😅")
        print(f"Error: {er}")

def smart_split(text, limit=1500):
    if not text:
        return ["(Empty response)"]
    
    chunks = []
    current = ""
    
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit:
            if current:
                chunks.append(current)
            current = line
        else:
            current += line
    
    if current:
        chunks.append(current)
    
    return chunks if chunks else [text]

bot.run(DISCORD_TOKEN)