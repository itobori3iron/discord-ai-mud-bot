import discord
import os
import aiohttp
import json
from discord.ext import commands
from dotenv import load_dotenv

# Load secrets
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

if not DISCORD_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("❌ Missing DISCORD_TOKEN or OPENROUTER_API_KEY.")

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

# Enable required Discord intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command("help")

GAME_STATE = {
    'setting': 'a mysterious ancient city',
    'events': []
}

MODEL = "deepseek/deepseek-chat-v3-0324:free"  # Set your preferred model here

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
        "max_tokens": 250
    }

    print(f"📤 Sending prompt to OpenRouter ({MODEL}): {prompt}")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as resp:
            try:
                response_json = await resp.json()
            except Exception as e:
                return None, f"❌ Failed to parse response: {str(e)}"

            print("📥 OpenRouter response:", response_json)

            if "choices" in response_json:
                try:
                    content = response_json['choices'][0]['message']['content']
                    return content.strip(), None
                except Exception as e:
                    return None, f"❌ Unexpected format: {str(e)}"

            error_msg = response_json.get("error", {}).get("message", "Unknown error.")
            return None, f"❌ OpenRouter error: {error_msg}"

@bot.command(name='setname')
async def set_display_name(ctx, *, custom_name: str):
    print(f"📛 {ctx.author.name} set their display name to: {custom_name}")
    player_names[str(ctx.author.id)] = custom_name
    save_player_names(player_names)
    await ctx.send(f"✅ Display name set to: `{custom_name}`")

@bot.command(name='helpme')
async def help_command(ctx):
    await ctx.send("🛠️ Commands:\n> your action\n!setname YourName\n!summary")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    print(f"🗨️ Message from {message.author.name}: {message.content}")

    if message.content.startswith('>'):
        action = message.content[1:].strip()
        name = get_display_name(message.author)
        prompt = f"In {GAME_STATE['setting']}, {name} does: \"{action}\". Continue the story."

        story, error = await generate_story(prompt)

        if story:
            GAME_STATE['events'].append({'player': name, 'action': action, 'outcome': story})
            await message.channel.send(f"**{name}**: {action}\n{story}")
        else:
            await message.channel.send(f"❌ Could not generate response:\n```{error}```")

    elif message.content.startswith('!summary'):
        recent = GAME_STATE['events'][-3:]
        summary = "\n".join([f"- **{e['player']}**: {e['outcome']}" for e in recent]) or "No events yet."
        await message.channel.send(f"📜 Recent story events:\n{summary}")

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user} (ID: {bot.user.id})")

bot.run(DISCORD_TOKEN)
