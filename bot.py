import discord
import os
import aiohttp
import json
import re
from discord.ext import commands
from dotenv import load_dotenv

# Load .env file
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Debug: Check tokens loaded correctly
print("🔧 Starting bot.py...")
print(f"DISCORD_TOKEN present: {bool(DISCORD_TOKEN)}")
print(f"OPENROUTER_API_KEY present: {bool(OPENROUTER_API_KEY)}")

if not DISCORD_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("❌ Missing DISCORD_TOKEN or OPENROUTER_API_KEY.")

PLAYER_NAMES_PATH = '/data/player_names.json'
MODEL = "google/gemini-2-flash"
MAX_TOKENS = 1024

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

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

GAME_STATE = {
    'setting': 'a mysterious ancient city',
    'events': []
}

def get_display_name(user):
    return player_names.get(str(user.id), user.name)

def extract_intent(text):
    lowered = text.lower()

    try:
        name_match = re.search(r"(call me|my name is|i go by)\s+(.*)", lowered)
        if name_match:
            name = name_match.group(2).strip()
            if name:
                return 'setname', name
    except Exception as e:
        print(f"Intent detection failed: {str(e)}")

    if "should we" in lowered or "let's vote" in lowered:
        return 'vote', text

    return 'action', text

async def generate_story(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.9
    }

    print(f"📤 Sending to OpenRouter ({MODEL}): {prompt}")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as resp:
            try:
                response_json = await resp.json()
                print("📥 OpenRouter raw:", response_json)
            except Exception as e:
                return None, f"❌ Failed to parse response: {str(e)}"

            if "choices" in response_json:
                try:
                    return response_json['choices'][0]['message']['content'].strip(), None
                except Exception as e:
                    return None, f"❌ Format error: {str(e)}"

            return None, response_json.get("error", {}).get("message", "Unknown error.")

@bot.event
async def on_ready():
    print(f"✅ Bot is ready. Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    print(f"🗨️ From {message.author.name}: {message.content}")
    intent, value = extract_intent(message.content)

    if intent == "setname":
        player_names[str(message.author.id)] = value
        save_player_names(player_names)
        await message.channel.send(f"✅ Got it! You’ll be known as `{value}` from now on.")
        return

    elif intent == "vote":
        await message.channel.send("🗳️ Voting system coming soon. You suggested:\n" + value)
        return

    elif intent == "action":
        name = get_display_name(message.author)
        prompt = f"In {GAME_STATE['setting']}, {name} does: \"{value}\". Continue the story."

        story, error = await generate_story(prompt)
        if story:
            GAME_STATE['events'].append({'player': name, 'action': value, 'outcome': story})
            await message.channel.send(f"**{name}**: {value}\n{story}")
        else:
            await message.channel.send(f"❌ Could not generate response:\n```{error}```")

    await bot.process_commands(message)

@bot.command(name='summary')
async def show_summary(ctx):
    recent = GAME_STATE['events'][-3:]
    summary = "\n".join([f"- **{e['player']}**: {e['outcome']}" for e in recent]) or "No events yet."
    await ctx.send(f"📜 Recent story events:\n{summary}")

# ⬇️ NEW DEBUG LINE
print("🚀 Launching bot with bot.run()...")
bot.run(DISCORD_TOKEN)
