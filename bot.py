import discord
import os
import aiohttp
import json
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

if not DISCORD_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("Both DISCORD_TOKEN and OPENROUTER_API_KEY must be set.")

PLAYER_NAMES_PATH = '/data/player_names.json'
MODEL = "gryphe/mythomax-l2-13b:free"

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
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as resp:
            try:
                response_json = await resp.json()
                print("Prompt sent:", prompt)
                print("Raw response:", response_json)
                return response_json['choices'][0]['message']['content']
            except Exception as e:
                return f"❌ Could not generate response:\n```\n{e}\n```"

@bot.command(name='helpme')
async def help_command(ctx):
    await ctx.send("Try typing something like:\n- `explores the ruins`\n- `call me Starhawk`\n- `summary`\nThe AI will continue your story from there!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    name = get_display_name(message.author)
    content = message.content.strip()

    if content.lower().startswith("call me "):
        new_name = content[8:].strip()
        if not new_name:
            await message.channel.send("❌ Please specify a valid name after `call me`.")
            return
        player_names[str(message.author.id)] = new_name
        save_player_names(player_names)
        await message.channel.send(f"✅ Got it. I’ll call you **{new_name}** from now on.")
        return

    if content.lower() == "summary":
        recent = GAME_STATE['events'][-3:]
        summary = "\n".join([f"- **{e['player']}**: {e['outcome']}" for e in recent]) or "No events yet."
        await message.channel.send(f"🧾 Story summary:\n{summary}")
        return

    # Natural language story action
    prompt = f"In {GAME_STATE['setting']}, {name} does: \"{content}\". What happens next?"
    response = await generate_story(prompt)

    if "Could not generate response" not in response:
        GAME_STATE['events'].append({'player': name, 'action': content, 'outcome': response})

    await message.channel.send(f"**{name}**: {content}\n{response}")

    await bot.process_commands(message)

print("Starting bot.py...")
bot.run(DISCORD_TOKEN)
