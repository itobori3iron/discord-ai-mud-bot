import discord
import os
import aiohttp
import json
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

if not DISCORD_TOKEN:
    raise ValueError("Missing DISCORD_TOKEN. Set it in .env or Render environment variables.")

PLAYER_NAMES_PATH = '/data/player_names.json'

def load_player_names():
    try:
        with open(PLAYER_NAMES_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_player_names(data):
    os.makedirs(os.path.dirname(PLAYER_NAMES_PATH), exist_ok=True)
    with open(PLAYER_NAMES_PATH, 'w') as f:
        json.dump(data, f, indent=4)

player_names = load_player_names()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command("help")

GAME_STATE = {
    'setting': 'a mysterious ancient city',
    'events': []
}

def get_display_name(user):
    return player_names.get(str(user.id), user.name)

async def generate_story(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-4-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 250
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as resp:
            response_json = await resp.json()
            return response_json['choices'][0]['message']['content']

@bot.command(name='setname')
async def set_display_name(ctx, *, custom_name: str):
    player_names[str(ctx.author.id)] = custom_name
    save_player_names(player_names)
    await ctx.send(f"✅ Display name set to: `{custom_name}`")

@bot.command(name='helpme')
async def help_command(ctx):
    await ctx.send("Commands:\n> your action\n!setname YourName\n!summary")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('>'):
        action = message.content[1:].strip()
        name = get_display_name(message.author)
        prompt = f"In {GAME_STATE['setting']}, {name} does: \"{action}\". Continue the story."
        response = await generate_story(prompt)
        GAME_STATE['events'].append({'player': name, 'action': action, 'outcome': response})
        await message.channel.send(f"**{name}**: {action}\n{response}")

    elif message.content.startswith('!summary'):
        recent = GAME_STATE['events'][-3:]
        summary = "\n".join([f"- **{e['player']}**: {e['outcome']}" for e in recent]) or "No events yet."
        await message.channel.send(f"Recent story events:\n{summary}")

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
