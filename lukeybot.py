import os
import random
import requests
import tempfile
import subprocess
import shutil

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
DISCORD_MAX_MB = int(os.getenv("DISCORD_MAX_MB", "8"))
DISCORD_MAX_BYTES = DISCORD_MAX_MB * 1024 * 1024

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

def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None

def compress_gif_with_ffmpeg(input_path: str, target_bytes: int, attempts: int = 6) -> Optional[str]:
    """Attempt to compress the GIF using ffmpeg and palette optimization.
    Returns path to compressed file if successful and <= target_bytes, else None.
    """
    if not ffmpeg_available():
        if DEBUG:
            print("[DEBUG] ffmpeg no está disponible en el sistema")
        return None

    base = os.path.splitext(input_path)[0]
    palette = f"{base}_palette.png"
    out_path = f"{base}_compressed.gif"

    scale_factor = 1.0
    fps = 20

    for i in range(attempts):
        # reduce scale and fps progressively
        scale = f"iw*{scale_factor}:-1"
        try:
            cmd_palette = [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", f"fps={fps},scale={scale}:flags=lanczos,palettegen", palette
            ]
            subprocess.run(cmd_palette, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)

            cmd_use = [
                "ffmpeg", "-y", "-i", input_path, "-i", palette,
                "-lavfi", f"fps={fps},scale={scale}:flags=lanczos [x]; [x][1:v] paletteuse",
                out_path
            ]
            subprocess.run(cmd_use, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)

            out_size = os.path.getsize(out_path)
            if DEBUG:
                print(f"[DEBUG] Intento {i+1}: size={out_size} bytes, target={target_bytes}")
            if out_size <= target_bytes:
                # cleanup palette
                try:
                    os.remove(palette)
                except Exception:
                    pass
                return out_path

        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] compress error: {e}")

        # make compression stronger
        scale_factor *= 0.75
        fps = max(8, int(fps * 0.85))

    # final cleanup
    try:
        if os.path.exists(palette):
            os.remove(palette)
    except Exception:
        pass

    # if out_path exists but not small enough, remove it
    if os.path.exists(out_path):
        try:
            if os.path.getsize(out_path) <= target_bytes:
                return out_path
        except Exception:
            pass
        try:
            os.remove(out_path)
        except Exception:
            pass

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
                # If exceeds Discord per-file limit, attempt to compress to DISCORD_MAX_BYTES
                if tmp_size > DISCORD_MAX_BYTES:
                    if ffmpeg_available():
                        if DEBUG:
                            print(f"[DEBUG] GIF {file['name']} es {tmp_size} bytes, intentando comprimir a {DISCORD_MAX_BYTES} bytes")
                        compressed = compress_gif_with_ffmpeg(tmp.name, DISCORD_MAX_BYTES)
                        if compressed and os.path.exists(compressed):
                            comp_size = os.path.getsize(compressed)
                            if comp_size <= DISCORD_MAX_BYTES:
                                await ctx.send(content=quote, file=discord.File(compressed, filename=file['name']))
                                try:
                                    os.remove(compressed)
                                except Exception:
                                    pass
                                return
                            else:
                                await ctx.send(f"GIF omitido — no fue posible reducirlo por debajo de {DISCORD_MAX_MB} MB.")
                                try:
                                    os.remove(compressed)
                                except Exception:
                                    pass
                                return
                        else:
                            await ctx.send(f"GIF omitido — compresión fallida o ffmpeg no disponible.")
                            return
                    else:
                        await ctx.send(f"GIF omitido — demasiado grande ({tmp_size/1024/1024:.1f} MB) y `ffmpeg` no está disponible para comprimir.")
                        return

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
                # If exceeds Discord per-file limit, attempt to compress to DISCORD_MAX_BYTES
                if tmp_size > DISCORD_MAX_BYTES:
                    if ffmpeg_available():
                        if DEBUG:
                            print(f"[DEBUG] GIF spicy {file['name']} es {tmp_size} bytes, intentando comprimir a {DISCORD_MAX_BYTES} bytes")
                        compressed = compress_gif_with_ffmpeg(tmp.name, DISCORD_MAX_BYTES)
                        if compressed and os.path.exists(compressed):
                            comp_size = os.path.getsize(compressed)
                            if comp_size <= DISCORD_MAX_BYTES:
                                await ctx.send(content=f"🔥 {quote}", file=discord.File(compressed, filename=file['name']))
                                try:
                                    os.remove(compressed)
                                except Exception:
                                    pass
                                return
                            else:
                                await ctx.send(f"GIF spicy omitido — no fue posible reducirlo por debajo de {DISCORD_MAX_MB} MB.")
                                try:
                                    os.remove(compressed)
                                except Exception:
                                    pass
                                return
                        else:
                            await ctx.send(f"GIF spicy omitido — compresión fallida o ffmpeg no disponible.")
                            return
                    else:
                        await ctx.send(f"GIF spicy omitido — demasiado grande ({tmp_size/1024/1024:.1f} MB) y `ffmpeg` no está disponible para comprimir.")
                        return

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
