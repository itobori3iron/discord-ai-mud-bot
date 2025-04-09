import discord
import os
import json
import aiohttp
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# Set up Discord intents for message reading
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Initialize bot with '!' prefix
bot = commands.Bot(command_prefix='!', intents=intents)

# Path for storing player names
PLAYER_NAMES_PATH = '/data/player_names.json'

# Load player names from JSON file
def load_player_names():
    try:
        with open(PLAYER_NAMES_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save player names to JSON file
def save_player_names(data):
    with open(PLAYER_NAMES_PATH, 'w') as f:
        json.dump(data, f, indent=4)

player_names = load_player_names()

# Command to set a custom display name
@bot.command(name='setname')
async def set_display_name(ctx, *, custom_name: str):
    player_names[str(ctx.author.id)] = custom_name
    save_player_names(player_names)
    await ctx.send(f"✅ Your display name has been set to {custom_name}")

# Get a user's display name (custom or default)
def get_display_name(user):
    return player_names.get(str(user.id), user.name)

# Generate a story via OpenRouter API
async def generate_story(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
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

# Command to show a summary of all player names
@bot.command(name='summary')
async def show_summary(ctx):
    if not player_names:
        await ctx.send("No players have set custom names yet!")
        return
    
    summary = "\n".join(f"- <@{user_id}>: {name}" for user_id, name in player_names.items())
    await ctx.send(f"Player Name Summary:\n{summary}")

# Help command with cleaner instructions
@bot.command(name='help')
async def show_help(ctx):
    help_text = (
        "Welcome to the Story Bot! Here's how to use it:\n\n"
        "1. Set Your Name: Use !setname followed by your desired name.\n"
        "   Example: !setname BraveKnight\n\n"
        "2. Perform an Action: Type > followed by an action to get a dramatic narration.\n"
        "   Example: > swings sword at dragon\n\n"
        "3. View Summary: Use !summary to see all players and their custom names.\n\n"
        "4. Get Help: Use !help to see these instructions again.\n\n"
        "Enjoy your adventure!"
    )
    await ctx.send(help_text)

# Handle messages for actions and commands
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check for action trigger (>)
    if message.content.startswith('>'):
        player_action = message.content[1:].strip()
        player_display_name = get_display_name(message.author)

        prompt = f"Player {player_display_name} performs action: {player_action}. Narrate dramatically (2-3 sentences)."
        response = await generate_story(prompt)

        await message.channel.send(f"{player_display_name}'s action: {player_action}\n\n{response}")

    # Process commands like !setname, !help, !summary
    await bot.process_commands(message)

# Start the bot
bot.run(os.getenv('DISCORD_TOKEN'))