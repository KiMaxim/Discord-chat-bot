import discord, os, requests, json
from dotenv import load_dotenv
from discord.ext import commands
import google.generativeai as genai

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_KEY')
genai.configure(api_key=GEMINI_KEY) #type:ignore
if DISCORD_TOKEN is None:
    raise RuntimeError("DISCORD_TOKEN is missing!")

intents = discord.Intents.default()
intents.message_content = True

# client = discord.Client(intents=intents) - this is low-level way of implementation, need to implement functions manually

bot = commands.Bot(command_prefix='!', intents=intents)

model = genai.GenerativeModel(  #type: ignore
        model_name='gemini-2.5-flash',
        system_instruction="""You are a wise old wizard named Merlin who speaks in a mystical way.
    
        - Use archaic language occasionally ("thou", "thee", "mayhaps")
        - Reference magic and spells in your explanations
        - Wise but has a good sense of humor
        - Sometimes cryptic but ultimately helpful"""

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
async def chat(ctx, *, message:str):
    await ctx.send('Thinking...')
    try:
        response = model.generate_content(message)
    except Exception as er:
        await ctx.send("Gemini is not responding, blame Google")
        print(f"Error is {er}")
        return
    chunks = smart_split(response.text)
    for chunk in chunks:
        print(f"{ctx.author} and {ctx.channel}")
        await ctx.send(chunk)

def smart_split(text, limit=1500):  
    chunks = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = ""
        current = current + line

    if current:
        chunks.append(current)

    return chunks

bot.run(DISCORD_TOKEN)

