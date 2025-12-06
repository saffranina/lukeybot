import os
import random
import requests
import tempfile

import discord
from discord.ext import commands
from dotenv import load_dotenv
from typing import Optional

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
MAX_GIF_MB = int(os.getenv("MAX_GIF_MB", "50"))  # configurable via .env
MAX_GIF_SIZE_BYTES = MAX_GIF_MB * 1024 * 1024

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

def get_remote_file_size(url: str) -> Optional[int]:
    """Try to get remote Content-Length via HEAD. Return bytes or None if unknown."""
    try:
        h = requests.head(url, allow_redirects=True, timeout=5)
        if h.status_code == 200:
            cl = h.headers.get("Content-Length")
            if cl:
                return int(cl)
    except Exception:
        if DEBUG:
            print(f"[DEBUG] Error obteniendo Content-Length para {url}")
    return None

def select_random_file_with_limit(files, max_bytes: int, attempts: int = 10):
    """Selecciona un archivo aleatorio que cumpla con el límite de bytes para GIFs.
    Si no se encuentra ninguno en `attempts`, devuelve None.
    """
    for _ in range(attempts):
        f = random.choice(files)
        # Si no es GIF, lo aceptamos de inmediato
        if f.get('mimeType') != 'image/gif':
            return f

        url_check = f"https://drive.google.com/uc?export=download&id={f['id']}"
        size = get_remote_file_size(url_check)
        if size is None or size <= max_bytes:
            return f

    return None

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

    # Seleccionamos un archivo que cumpla el límite de tamaño para GIFs
    file = select_random_file_with_limit(files, MAX_GIF_SIZE_BYTES)
    if not file:
        await ctx.send(f"No se encontró ninguna imagen/GIF dentro del límite de {MAX_GIF_MB} MB.")
        return

    url = f"https://drive.google.com/uc?export=download&id={file['id']}"
    quote = random.choice(RANDOM_QUOTES)

    if file['mimeType'] == 'image/gif':
        # Descargamos y validamos el tamaño final antes de enviar
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as tmp:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        tmp.write(chunk)
                tmp.flush()
                tmp_size = os.path.getsize(tmp.name)
                if tmp_size > MAX_GIF_SIZE_BYTES:
                    await ctx.send(f"GIF omitido — demasiado grande ({tmp_size/1024/1024:.1f} MB). Límite: {MAX_GIF_MB} MB.")
                    return
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

    # Seleccionamos un archivo que cumpla el límite de tamaño para GIFs
    file = select_random_file_with_limit(files, MAX_GIF_SIZE_BYTES)
    if not file:
        await ctx.send(f"No se encontró ninguna imagen/GIF spicy dentro del límite de {MAX_GIF_MB} MB.")
        return

    url = f"https://drive.google.com/uc?export=download&id={file['id']}"
    quote = random.choice(SPICY_QUOTES)

    if file['mimeType'] == 'image/gif':
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as tmp:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        tmp.write(chunk)
                tmp.flush()
                tmp_size = os.path.getsize(tmp.name)
                if tmp_size > MAX_GIF_SIZE_BYTES:
                    await ctx.send(f"GIF spicy omitido — demasiado grande ({tmp_size/1024/1024:.1f} MB). Límite: {MAX_GIF_MB} MB.")
                    return
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
