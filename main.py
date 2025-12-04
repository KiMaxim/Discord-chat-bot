import discord, os, requests, json
from dotenv import load_dotenv
from discord.ext import commands
from google import generativeai as genai

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_KEY')
genai.configure(api_key=GEMINI_KEY)
if DISCORD_TOKEN is None:
    raise RuntimeError("DISCORD_TOKEN is missing!")

intents = discord.Intents.default()
intents.message_content = True

# client = discord.Client(intents=intents) - this is low-level way of implementation, need to implement functions manually

bot = commands.Bot(command_prefix='!', intents=intents)

model = genai.GenerativeModel('gemini-2.5-flash')

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')


@bot.command()
async def chat(ctx, *, message:str):
    await ctx.send('Thinking...')
    response = model.generate_content(message)
    await ctx.send(response.text)

bot.run(DISCORD_TOKEN)

