import os
import random
import requests
import tempfile

import discord
from discord.ext import commands
from dotenv import load_dotenv
import traceback
import datetime

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

# Resolver ruta del archivo de cuenta de servicio relativa al directorio del
# script si se pasó un nombre relativo (por ejemplo `service_account.json`).
if SERVICE_ACCOUNT_FILE and not os.path.isabs(SERVICE_ACCOUNT_FILE):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    SERVICE_ACCOUNT_FILE = os.path.join(base_dir, SERVICE_ACCOUNT_FILE)

print(f"Using service account file: {SERVICE_ACCOUNT_FILE} (exists={os.path.exists(SERVICE_ACCOUNT_FILE)})")

# ==========================
# Configuración Discord
# ==========================

intents = discord.Intents.default()
intents.message_content = True  # MUY IMPORTANTE

bot = commands.Bot(command_prefix="!", intents=intents)


bot_name = "LukeyBot"

# Modo silencioso para evitar enviar mensajes de error al canal
# Por seguridad y para respetar la petición del usuario, por defecto está activado.
QUIET_MODE = os.getenv("QUIET_MODE", "True").lower() == "true"


def _is_error_text(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    keywords = [
        "error",
        "no se pudo",
        "no images",
        "no spicy",
        "archivo de cuenta",
        "service_account",
        "service account",
        "no such file",
        "errno",
        "ocurrió un error",
        "file not found",
    ]
    return any(k in lower for k in keywords)


async def safe_send(ctx, *args, **kwargs):
    # Detectar contenido de texto y suprimir si parece un mensaje de error
    content = kwargs.get("content")
    if not content and args:
        first = args[0]
        if isinstance(first, str):
            content = first

    if QUIET_MODE and content and _is_error_text(content):
        print(f"[safe_send] Suppressed error message to channel: {content}")
        return

    await ctx.send(*args, **kwargs)

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
    try:
        service = get_drive_service()
    except Exception as e:
        print(f"Error al conectar con Google Drive: {e}")
        raise

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
            fields="nextPageToken, files(id, name, mimeType, size)",
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


def _log_traceback_to_file(exc: Exception):
    try:
        tb = traceback.format_exc()
        ts = datetime.datetime.utcnow().isoformat()
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error_traces.log')
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f"{ts} - {str(exc)}\n")
            f.write(tb)
            f.write('\n' + ('-'*80) + '\n')
    except Exception as e:
        print(f"Failed to write traceback to file: {e}")

# ==========================
# Eventos y comandos
# ==========================

@bot.event
async def on_ready():
    print(f"{bot_name} ONLINE como {bot.user} (id: {bot.user.id})")
    print(f"Comandos disponibles: {[cmd.name for cmd in bot.commands]}")
    await bot.change_presence(activity=discord.Game(name="summoning Luke"))


@bot.event
async def on_message(message):
    # Logear mensajes entrantes para depuración y asegurarnos de procesar comandos
    try:
        # Allow inspecting our own messages so we can remove sensitive outputs
        if message.author == bot.user:
            content_lower = (message.content or "").lower()
            # Patterns that should never be visible in channels
            sensitive_patterns = ["no such file", "errno", "service_account", "service account", "service_account.json"]
            if any(pat in content_lower for pat in sensitive_patterns):
                try:
                    await message.delete()
                    print(f"Deleted sensitive bot message: {message.content}")
                except Exception as e:
                    print(f"Failed to delete sensitive bot message: {e}")
            # Do not return here; allow processing if needed
        elif message.author.bot:
            return
        print(f"Mensaje recibido de {message.author}: {message.content}")
    except Exception:
        pass

    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # suppressed: no user-facing error messages per request
        print("Command not found (suppressed message to channel)")
    else:
        # No divulgar texto de excepciones en Discord. Registrar traceback en logs.
        print(f"Error en comando: {error}")
        import traceback
        traceback.print_exc()
        try:
            _log_traceback_to_file(error)
        except Exception as _e:
            print(f"Failed to write traceback to error_traces.log: {_e}")
        # suppressed: do not send error messages to channels
        print("Internal command error (suppressed message to channel)")

# -----------------------------------
# !luke — modo normal
# -----------------------------------
@bot.command(name="luke", help="Random Luke image + normal quote")
async def luke_command(ctx):
    try:
        print(f"Comando !luke ejecutado por {ctx.author}")
        files = get_all_media_files_from_folder()
        if DEBUG:
            await safe_send(ctx, f"[DEBUG] Archivos en Drive: {len(files)}")
        if not files:
            # suppressed: No images found message removed
            print("No images found in Drive folder (suppressed message to channel)")
            return

        file = random.choice(files)
        url = f"https://drive.google.com/uc?export=download&id={file['id']}"
        quote = random.choice(RANDOM_QUOTES)

        if file['mimeType'] == 'image/gif':
            # Try to upload GIF only if it's small enough for Discord (8 MB default).
            size = None
            try:
                size = int(file.get('size')) if file.get('size') else None
            except Exception:
                size = None

            MAX_SIZE = 8 * 1024 * 1024  # 8 MB

            if size and size <= MAX_SIZE:
                # Safe to download and upload (should be animated when uploaded)
                r = requests.get(url)
                if r.status_code == 200:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as tmp:
                        tmp.write(r.content)
                        tmp.flush()
                        tmp_path = tmp.name
                    try:
                        await ctx.send(content=quote, file=discord.File(tmp_path, filename=file['name']))
                    finally:
                        try:
                            os.remove(tmp_path)
                        except Exception as e:
                            print(f"Warning: could not remove tmp file {tmp_path}: {e}")
                else:
                    print(f"Failed to download GIF for upload, HTTP {r.status_code}")
                    gif_url = f"https://drive.google.com/uc?export=view&id={file['id']}"
                    random_color = discord.Color.from_rgb(
                        random.randint(0,255),
                        random.randint(0,255),
                        random.randint(0,255),
                    )
                    embed = discord.Embed(title=quote, color=random_color)
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)
            else:
                # Too large or unknown size: use Drive view URL in an embed (may or may not animate)
                gif_url = f"https://drive.google.com/uc?export=view&id={file['id']}"
                random_color = discord.Color.from_rgb(
                    random.randint(0,255),
                    random.randint(0,255),
                    random.randint(0,255),
                )
                embed = discord.Embed(title=quote, color=random_color)
                embed.set_image(url=gif_url)
                await ctx.send(embed=embed)
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
    except Exception as e:
        print(f"Error en !luke: {e}")
        traceback.print_exc()
        _log_traceback_to_file(e)
        # suppressed: do not send error messages to channel
        print("Internal error in !luke (suppressed message to channel)")

# -----------------------------------
# !spicyluke — modo SPICY 🔥
# -----------------------------------
@bot.command(name="spicyluke", help="SPICY Luke image + spicy quote 🔥")
async def spicyluke_command(ctx):
    try:
        print(f"Comando !spicyluke ejecutado por {ctx.author}")
        files = get_all_media_files_from_folder()
        if DEBUG:
            await safe_send(ctx, f"[DEBUG] Archivos en Drive: {len(files)}")
        if not files:
            await safe_send(ctx, "No spicy material found in Drive 😳")
            return

        file = random.choice(files)
        url = f"https://drive.google.com/uc?export=download&id={file['id']}"
        quote = random.choice(SPICY_QUOTES)

        if file['mimeType'] == 'image/gif':
            # For spicy GIFs, prefer to upload if small enough to preserve animation
            size = None
            try:
                size = int(file.get('size')) if file.get('size') else None
            except Exception:
                size = None

            MAX_SIZE = 8 * 1024 * 1024  # 8 MB

            if size and size <= MAX_SIZE:
                r = requests.get(url)
                if r.status_code == 200:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as tmp:
                        tmp.write(r.content)
                        tmp.flush()
                        tmp_path = tmp.name
                    try:
                        await ctx.send(content=f"🔥 {quote}", file=discord.File(tmp_path, filename=file['name']))
                    finally:
                        try:
                            os.remove(tmp_path)
                        except Exception as e:
                            print(f"Warning: could not remove tmp file {tmp_path}: {e}")
                else:
                    print(f"Failed to download spicy GIF for upload, HTTP {r.status_code}")
                    gif_url = f"https://drive.google.com/uc?export=view&id={file['id']}"
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
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)
            else:
                gif_url = f"https://drive.google.com/uc?export=view&id={file['id']}"
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
                embed.set_image(url=gif_url)
                await ctx.send(embed=embed)
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
    except Exception as e:
        print(f"Error en !spicyluke: {e}")
        traceback.print_exc()
        _log_traceback_to_file(e)
        # suppressed: do not send error messages to channel
        print("Internal error in !spicyluke (suppressed message to channel)")

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
            "**!lukeytest** — test Google Drive connection\n"
            "**Source:** Google Drive folder (JPG, PNG, GIF)\n\n"
            "Add new images to the Drive folder and LukeyBot will use them automatically.\n"
            "Hydration recommended."
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed)

# -----------------------------------
# !lukeytest — diagnostico
# -----------------------------------
@bot.command(name="lukeytest", help="Test Google Drive connection")
async def lukeytest(ctx):
    await ctx.send("🔍 Testing Google Drive connection...")
    
    try:
        # Test 1: Service account file
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            # suppressed: service account missing message
            print(f"Service account file not found at {SERVICE_ACCOUNT_FILE} (suppressed message to channel)")
            return
        await safe_send(ctx, "✅ Archivo de cuenta de servicio: OK")
        
        # Test 2: Connect to Drive
        service = get_drive_service()
        await safe_send(ctx, "✅ Successfully connected to Google Drive API")
        
        # Test 3: Access folder
        files = get_all_media_files_from_folder()
        await safe_send(ctx, f"✅ Found {len(files)} files in Drive folder")
        
        if files:
            await safe_send(ctx, f"📁 First file: `{files[0]['name']}` (type: {files[0]['mimeType']})")
        else:
            await safe_send(ctx, "⚠️ Folder is empty or bot doesn't have access")
            
    except Exception as e:
        print(f"Error detallado en !lukeytest: {e}")
        traceback.print_exc()
        _log_traceback_to_file(e)
        # suppressed: do not send error message to channel
        print("Internal error in !lukeytest (suppressed message to channel)")

# ==========================
# Run bot
# ==========================

bot.run(DISCORD_TOKEN)
