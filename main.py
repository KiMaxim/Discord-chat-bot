import discord, os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("MY_TOKEN")
if token is None:
    raise RuntimeError("Token is missing!")

class MyClient(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content.startswith('$hello'):
            await message.channel.send('Hello World!')
        

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True    

client = MyClient(intents=intents)
client.run(token)

