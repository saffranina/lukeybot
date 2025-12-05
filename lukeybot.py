import os
import random
import requests
import tempfile

import discord
from discord.ext import commands
from dotenv import load_dotenv

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ==========================
# Cargar variables de entorno
# ==========================


load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

if not DISCORD_TOKEN:
    raise RuntimeError("Falta DISCORD_TOKEN en el archivo .env")
if not DRIVE_FOLDER_ID:
    raise RuntimeError("Falta DRIVE_FOLDER_ID en el archivo .env")
if not SERVICE_ACCOUNT_FILE:
    raise RuntimeError("Falta GOOGLE_SERVICE_ACCOUNT_FILE en el archivo .env")

# ==========================
# Configuración Discord
# ==========================

intents = discord.Intents.default()
intents.message_content = True  # MUY IMPORTANTE

bot = commands.Bot(command_prefix="!", intents=intents)


bot_name = "LukeyBot"

# ==========================
# Frases random (modo normal)
# ==========================

RANDOM_QUOTES = [
    "Here's your daily dose of Luke.",
    "You can't spell 'chaos' without Luke.",
    "May this Luke bless your timeline.",
    "A wild Luke appears!",
    "Luke energy detected.",
    "You were chosen for this Luke.",
    "May your day be as iconic as this picture.",
    "A random Luke for your mental health.",
    "Analyzing… Yes. You needed this Luke.",
    "Certified Luke moment.",

    # requested
    "Jesus Christ be praised",
    "I'm smart",
    "Luke has come to see us",
]

# ==========================
# Frases SPICY
# ==========================

SPICY_QUOTES = [
    "Warning: Luke detected. Hydrate yourself.",
    "Too hot to handle, too iconic to ignore.",
    "Your heartbeat just increased by 27%. You're welcome.",
    "This Luke is clinically proven to cause blushing.",
    "Caution: visual contact may induce thirst.",
    "If you're reading this, it's already too late. You're flustered.",
    "Mmm… somebody looks delicious today.",
    "Spicy Luke delivered. Handle with care.",
    "Sudden attraction levels rising…",
    "Temperature rising: proceed with caution.",
    "You weren't ready for this level of Luke.",
    "Yes, you're blushing. Don't lie.",
    "Thirst levels: CRITICAL.",
]

# ==========================
# Google Drive
# ==========================

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)

def get_all_media_files_from_folder():
    service = get_drive_service()

    query = (
        f"'{DRIVE_FOLDER_ID}' in parents and ("
        "mimeType = 'image/jpeg' or "
        "mimeType = 'image/png' or "
        "mimeType = 'image/gif'"
        ") and trashed = false"
    )

    files = []
    page_token = None

    while True:
        response = service.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
        ).execute()

        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return files

def get_random_image_url():
    files = get_all_media_files_from_folder()
    if not files:
        return None

    file_id = random.choice(files)["id"]
    return f"https://drive.google.com/uc?export=view&id={file_id}"

# ==========================
# Eventos y comandos
# ==========================

@bot.event
async def on_ready():
    print(f"{bot_name} ONLINE como {bot.user} (id: {bot.user.id})")
    await bot.change_presence(activity=discord.Game(name="summoning Luke"))

# -----------------------------------
# !luke — modo normal
# -----------------------------------
@bot.command(name="luke", help="Random Luke image + normal quote")
async def luke_command(ctx):
    files = get_all_media_files_from_folder()
    if DEBUG:
        await ctx.send(f"[DEBUG] Archivos en Drive: {len(files)}")
    if not files:
        await ctx.send("No images found in Drive folder.")
        return

    file = random.choice(files)
    url = f"https://drive.google.com/uc?export=download&id={file['id']}"
    quote = random.choice(RANDOM_QUOTES)

    if file['mimeType'] == 'image/gif':
        r = requests.get(url)
        if r.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as tmp:
                tmp.write(r.content)
                tmp.flush()
                await ctx.send(content=quote, file=discord.File(tmp.name, filename=file['name']))
        else:
            await ctx.send("No se pudo descargar el GIF.")
    else:
        random_color = discord.Color.from_rgb(
            random.randint(0,255),
            random.randint(0,255),
            random.randint(0,255),
        )
        embed = discord.Embed(
            title=quote,
            color=random_color
        )
        embed.set_image(url=url)
        await ctx.send(embed=embed)

# -----------------------------------
# !spicyluke — modo SPICY 🔥
# -----------------------------------
@bot.command(name="spicyluke", help="SPICY Luke image + spicy quote 🔥")
async def spicyluke_command(ctx):
    files = get_all_media_files_from_folder()
    if DEBUG:
        await ctx.send(f"[DEBUG] Archivos en Drive: {len(files)}")
    if not files:
        await ctx.send("No spicy material found in Drive 😳")
        return

    file = random.choice(files)
    url = f"https://drive.google.com/uc?export=download&id={file['id']}"
    quote = random.choice(SPICY_QUOTES)

    if file['mimeType'] == 'image/gif':
        r = requests.get(url)
        if r.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as tmp:
                tmp.write(r.content)
                tmp.flush()
                await ctx.send(content=f"🔥 {quote}", file=discord.File(tmp.name, filename=file['name']))
        else:
            await ctx.send("No se pudo descargar el GIF spicy.")
    else:
        spicy_color = discord.Color.from_rgb(
            random.randint(180,255),
            random.randint(0,80),
            random.randint(50,200),
        )
        embed = discord.Embed(
            title=quote,
            description="🔥 Spicy Mode Activated 🔥",
            color=spicy_color
        )
        embed.set_image(url=url)
        await ctx.send(embed=embed)

# -----------------------------------
# !lukeyhelp — instrucciones
# -----------------------------------
@bot.command(name="lukeyhelp", help="Shows instructions for LukeyBot")
async def lukeyhelp(ctx):
    embed = discord.Embed(
        title="📸 LukeyBot — Instructions",
        description=(
            "**!luke** — random Luke image + random quote\n"
            "**!spicyluke** — spicy Luke image + spicy quote 🔥\n"
            "**Source:** Google Drive folder (JPG, PNG, GIF)\n\n"
            "Add new images to the Drive folder and LukeyBot will use them automatically.\n"
            "Hydration recommended."
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed)

# ==========================
# Run bot
# ==========================

bot.run(DISCORD_TOKEN)
