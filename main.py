import discord
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_KEY')

genai.configure(api_key=GEMINI_KEY) # type: ignore 

if GEMINI_KEY is None or DISCORD_TOKEN is None:
    raise RuntimeError("Essential info is missing")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

SETTINGS_FILE = 'bot_settings.json' #keep per-server (guild) settings

defaul_settings = {
    'personality': 'luna',
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


def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'guilds': {}}
    
def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def get_guild_settins(guild_id):
    settings = load_settings()
    guild_str_id = str(guild_id)
    if guild_str_id not in settings['guilds']:
        settings['guilds'][guild_str_id] = defaul_settings.copy()
        save_settings(settings)
    return settings['guilds'][guild_str_id]

def update_guild_settings(guild_id, key, value):
    settings = load_settings()
    guilds_str_id = str(guild_id)
    if guilds_str_id not in settings['guilds']:
        settings['guilds'][guilds_str_id] = defaul_settings.copy()
        save_settings(settings)
    settings['guilds'][guilds_str_id][key] = value 
    save_settings(settings)

def get_model_with_settings(guild_id):
    settings = get_guild_settins(guild_id)
    personality = personalities.get(settings['personality'], personalities['jarvis'])

    lenght_intructions = {
        'short': '\n- Keep response brief (1-2 sentences when possible)',
        'medium': '\n- Keep response moderate (2-4 sentences)',
        'long': '\n- Provide detailed responces with examples'
    }

    emoji_instruction = '' if settings['emojis'] else '\n- Do not use emojis'

    full_instruction = personality + lenght_intructions[settings['response_length']] + emoji_instruction
 
    return genai.GenerativeModel( #type: ignore
        model_name = 'gemini-2.5-flash',
        system_instruction = full_instruction
    )

class SettingsView(discord.ui.View):
    def __init__(self, *, timeout: float = 180, guild_id): # type: ignore
        super().__init__(timeout=timeout)
        self.guild_id = guild_id
    
    @discord.ui.select(placeholder="Choose Personality", 
                       options=[
                            discord.SelectOption(label="Spider-Man", value="spiderman", emoji="🕷️"),
                            discord.SelectOption(label="Iron Man", value="ironman", emoji="🤖"),
                            discord.SelectOption(label="Captain America", value="captainamerica", emoji="🛡️"),
                            discord.SelectOption(label="Luna (Cheerful)", value="luna", emoji="🌙"),
                            discord.SelectOption(label="Wizard (Mystical)", value="wizard", emoji="🧙"),
                            discord.SelectOption(label="Pirate (Adventurous)", value="pirate", emoji="🏴‍☠️"),
                            discord.SelectOption(label="Professional", value="professional", emoji="💼")
                        ]  
                       ) # type: ignore
    async def personlity_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        update_guild_settings(self.guild_id, 'personality', select.values[0])
        await interaction.response.send_message(f"Personality was changed to **{select.values[0].title()}**",
                                                ephemeral= True)
        
    @discord.ui.select(placeholder="Choose length of the response",
                       options=[
                            discord.SelectOption(label="Short", value="short", emoji="📝"),
                            discord.SelectOption(label="Medium", value="medium", emoji="📄"),
                            discord.SelectOption(label="Long", value="long", emoji="📚")
                        ])
    async def response_length_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        update_guild_settings(self.guild_id, 'response_length', select.values[0])
        await interaction.response.send_message(f"The responce length was changed to **{select.values[0].title()}**",
                                                ephemeral=True)
    
    @discord.ui.button(label="Toogle", style=discord.ButtonStyle.primary, emoji=None)
    async def emoji_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = get_guild_settins(self.guild_id)
        new_value = not settings['emojis']
        update_guild_settings(self.guild_id, 'emojis', new_value)
        status = 'Emoji enabled' if new_value else 'Emoji disabled'
        await interaction.response.send_message(f"The emoji is **{status}**", ephemeral=True)
    
    @discord.ui.button(label="Rest to default", style=discord.ButtonStyle.danger, emoji=None)
    async def reset_to_default(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = load_settings()
        guild_str_id = str(self.guild_id)
        settings['guilds'][guild_str_id] = defaul_settings.copy()
        save_settings(settings)
        await interaction.response.send_message('Settings reset to default', ephemeral=True)
    
@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)
        
@bot.command()
async def settings(ctx):
    current_settings = get_guild_settins(ctx.guild.id)
    embed = discord.Embed(
        title='Bot settings',
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
    print(f"DEBUG: Message content: '{ctx.message.content}'")
    print(f"DEBUG: Message content: '{ctx.message.author}'")

    thinking_message = await ctx.send("Thinking to asnwer your dumb ass question...")
    try:
        model = get_model_with_settings(ctx.guild.id)
        response = model.generate_content(message)
        chunks = smart_split(response.text)
        if chunks is None:
            raise RuntimeError("Gemini is not responding")
        for chunk in chunks:
            await ctx.send(chunk)
    except Exception as er:
        await thinking_message.delete()
        print(f"Error is {er}")
        raise RuntimeError("Gemini is not responding, blame google")

def smart_split(text, limit = 1500):
    if not text:
        return ["(Empty Response)"]
    chunks = []
    current_line = ""
    
    for line in text.splitlines(keepends=True):
        if len(line) + len(current_line) > limit:
            chunks.append(current_line)
            current_line = line
        else:
            current_line += line

        if current_line:
            chunks.append(current_line)
        
        return chunks if chunks else [text]

bot.run(DISCORD_TOKEN)
    
