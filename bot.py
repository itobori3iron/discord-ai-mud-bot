import discord
import os
import aiohttp
import json
import re
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not DISCORD_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("Missing DISCORD_TOKEN or OPENROUTER_API_KEY. Please set these in your environment.")

# Model config
MODEL = "deepseek/deepseek-chat-v3-0324:free"
PLAYER_NAMES_PATH = "/data/player_names.json"

# Load player names
def load_player_names():
    try:
        with open(PLAYER_NAMES_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_player_names(data):
    with open(PLAYER_NAMES_PATH, "w") as f:
        json.dump(data, f, indent=2)

player_names = load_player_names()

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

GAME_STATE = {
    "setting": "an ancient moss-covered temple",
    "events": []
}

# Helpers
def get_display_name(user):
    return player_names.get(str(user.id), user.name)

def split_message(message, limit=2000):
    if len(message) <= limit:
        return [message]
    chunks = []
    while len(message) > limit:
        idx = message.rfind("\n", 0, limit)
        if idx == -1:
            idx = limit
        chunks.append(message[:idx])
        message = message[idx:].lstrip()
    if message:
        chunks.append(message)
    return chunks

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
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                if "choices" in result:
                    return result["choices"][0]["message"]["content"]
                else:
                    error = result.get("error", {}).get("message", str(result))
                    return f"❌ Could not generate response:\n```{error}```"
    except Exception as e:
        return f"❌ Something went wrong:\n```{str(e)}```"

@bot.command(name="helpme")
async def help_command(ctx):
    await ctx.send("Say something like `explore the cave` or `call me Ranger` to influence the story.\nAlso try `what happened` to get a recap.")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content = message.content.strip()
    user_id = str(message.author.id)
    name = get_display_name(message.author)

    # Natural language name change
    match = re.match(r"(?i)call me (.+)", content)
    if match:
        new_name = match.group(1).strip()
        if new_name:
            player_names[user_id] = new_name
            save_player_names(player_names)
            await message.channel.send(f"✅ Got it! I'll call you **{new_name}**.")
        else:
            await message.channel.send("❌ You need to give me a name, like `call me Scout`.")
        return

    if re.search(r"(?i)\bwhat happened\b", content):
        recent = GAME_STATE["events"][-3:]
        summary = "\n".join([f"**{e['player']}**: {e['outcome']}" for e in recent]) or "No events yet!"
        await message.channel.send(f"📜 Here's what happened:\n{summary}")
        return

    # If not a command, treat as story input
    prompt = f"In {GAME_STATE['setting']}, {name} does: \"{content}\". Continue the story."
    response = await generate_story(prompt)

    GAME_STATE["events"].append({"player": name, "action": content, "outcome": response})
    for chunk in split_message(f"**{name}**: {content}\n{response}"):
        await message.channel.send(chunk)

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
