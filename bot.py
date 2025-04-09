import discord
import os
import aiohttp
import json
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Load or initialize player names
PLAYER_NAMES_PATH = '/data/player_names.json'

def load_player_names():
    try:
        with open(PLAYER_NAMES_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_player_names(data):
    with open(PLAYER_NAMES_PATH, 'w') as f:
        json.dump(data, f, indent=4)

player_names = load_player_names()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command("help")

# Game state
GAME_STATE = {
    'setting': 'a mysterious ancient city',
    'events': []
}

# Function to get display name
def get_display_name(user):
    return player_names.get(str(user.id), user.name)

# OpenRouter AI call
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

# Command to set custom display name
@bot.command(name='setname')
async def set_display_name(ctx, *, custom_name: str):
    player_names[str(ctx.author.id)] = custom_name
    save_player_names(player_names)
    await ctx.send(f"✅ Your display name has been set to: `{custom_name}`")

# Optional help command
@bot.command(name='helpme')
async def help_command(ctx):
    await ctx.send("Here are some commands you can use:\n- !setname YourName\n- !summary\n- > [your action]")

# Event handling for player actions
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('>'):
        player_action = message.content[1:].strip()
        display_name = get_display_name(message.author)
        prompt = f"""
        You are the host of a multiplayer story game set in {GAME_STATE['setting']}.
        The player {display_name} performs the action: \"{player_action}\".

        Continue the story in 2-3 sentences, using rich narration and natural consequences.
        """
        response = await generate_story(prompt)

        GAME_STATE['events'].append({
            'player': display_name,
            'action': player_action,
            'outcome': response
        })

        await message.channel.send(f"**{display_name}'s action:** {player_action}\n\n{response}")

    elif message.content.startswith('!summary'):
        display_name = get_display_name(message.author)
        recent = GAME_STATE['events'][-3:] if GAME_STATE['events'] else []
        summary = "\n".join(
            [f"- **{e['player']}** {e['action']}: {e['outcome']}" for e in recent]
        ) or "No events yet."
        await message.channel.send(f"**Recent Events for {display_name}:**\n{summary}")

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
