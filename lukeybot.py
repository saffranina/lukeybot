import os
import random
import requests
import tempfile
import subprocess
import shutil
import logging
import atexit
import signal
import sys

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ==========================
# Configuración de Logging
# ==========================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('lukeybot')

# Lista global para rastrear archivos temporales
temp_files_to_cleanup = []

# ==========================
# Limpieza de archivos temporales
# ==========================

def cleanup_temp_files():
    """Limpia todos los archivos temporales al finalizar."""
    logger.info(f"Limpiando {len(temp_files_to_cleanup)} archivos temporales...")
    for filepath in temp_files_to_cleanup:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.debug(f"Eliminado: {filepath}")
        except Exception as e:
            logger.warning(f"No se pudo eliminar {filepath}: {e}")
    temp_files_to_cleanup.clear()

def register_temp_file(filepath: str):
    """Registra un archivo temporal para limpieza posterior."""
    temp_files_to_cleanup.append(filepath)

def cleanup_temp_file(filepath: str):
    """Limpia un archivo temporal inmediatamente."""
    try:
        if filepath in temp_files_to_cleanup:
            temp_files_to_cleanup.remove(filepath)
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.debug(f"Limpiado inmediato: {filepath}")
    except Exception as e:
        logger.warning(f"Error limpiando {filepath}: {e}")

def signal_handler(sig, frame):
    """Maneja señales de terminación para limpiar antes de salir."""
    logger.info(f"Señal {sig} recibida, limpiando...")
    cleanup_temp_files()
    sys.exit(0)

# Registrar handlers de limpieza
atexit.register(cleanup_temp_files)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ==========================
# Cargar variables de entorno
# ==========================


load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")  # JSON como string
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
MAX_GIF_MB = int(os.getenv("MAX_GIF_MB", "50"))  # configurable via .env
MAX_GIF_SIZE_BYTES = MAX_GIF_MB * 1024 * 1024
DISCORD_MAX_MB = int(os.getenv("DISCORD_MAX_MB", "8"))
DISCORD_MAX_BYTES = DISCORD_MAX_MB * 1024 * 1024
AUTO_POST_CHANNEL_ID = os.getenv("AUTO_POST_CHANNEL_ID")  # ID del canal para auto-post cada 6h
KCD_POST_CHANNEL_ID = os.getenv("KCD_POST_CHANNEL_ID")  # ID del canal para auto-post cada 8h

if not DISCORD_TOKEN:
    logger.error("Falta DISCORD_TOKEN en el archivo .env")
    raise RuntimeError("Falta DISCORD_TOKEN en el archivo .env")
if not DRIVE_FOLDER_ID:
    logger.error("Falta DRIVE_FOLDER_ID en el archivo .env")
    raise RuntimeError("Falta DRIVE_FOLDER_ID en el archivo .env")
if not SERVICE_ACCOUNT_FILE and not SERVICE_ACCOUNT_JSON:
    logger.error("Falta GOOGLE_SERVICE_ACCOUNT_FILE o GOOGLE_SERVICE_ACCOUNT_JSON en el archivo .env")
    raise RuntimeError("Falta GOOGLE_SERVICE_ACCOUNT_FILE o GOOGLE_SERVICE_ACCOUNT_JSON en el archivo .env")

logger.info(f"Configuración cargada: MAX_GIF_MB={MAX_GIF_MB}, DISCORD_MAX_MB={DISCORD_MAX_MB}, DEBUG={DEBUG}")

# ==========================
# Configuración Discord
# ==========================

intents = discord.Intents.default()
intents.message_content = True  # MUY IMPORTANTE

bot_name = "LukeyBot"
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
# Asegurar que el comando por defecto 'help' esté eliminado
try:
    bot.remove_command('help')
except Exception:
    # en caso de que ya esté eliminado o no exista, ignorar
    pass


bot_name = "LukeyBot"

# ==========================
# Frases ALMONDS (auto-post cada 6h)
# ==========================

ALMONDS_QUOTES = [
    "ALMENDRASSSSSS 🌰🌰🌰",
    "NUECESSSSSS 🥜🥜🥜",
    "ANACARDOSSSSSS 💰🌰",
    "MANÍÍÍÍÍÍÍÍÍÍÍÍÍ 🥜🥜",
    "NUECESSSS DE NOGALLLLL 🌰🌰",
    "PISTACHOSSSSSS 🟢🌰🟢",
    "AVELLANASSSSSS 🤎🌰🤎",
    "MACADAMIASSSSSS 🏝️🌰",
    "NUECECCESSS PECANASSSSS 🍂🌰🍂",
    "CASTAÑASSSSSS 🔥🌰🔥",
    "NUECESSS DE BRASILEEEEE 🇧🇷🌰🇧🇷",
    "PIÑONESSSSSS 🌲🌰🌲",
    "SEMILLAS DE GIRASOLLLLL 🌻🌻🌻",
    "SEMILLAS DE CALABAZAAAA 🎃🎃🎃",
    "COCOOOOOOOO 🥥🥥🥥",
    "NUECESSS DE BETELLLLL 🔴🌰🔴",
    "BELLOTASSSSSS 🍂🌰🍂",
    "NUECESSS DE TIGREEEEE 🐯🌰🐯",
    "NUECESSS DE KOLAAAAAA ☕🌰☕",
    "NUECESSS DE GINKGOOOOO 🍃🌰🍃",
    "AYYY NO LA ROPAAAAA---",
    "AY DIOS MIOOO",
]

# ==========================
# Frases KCD (auto-post cada 8h)
# ==========================

KCD_QUOTES = [
    "TO THE TASK! ⚔️",
    "Audentes fortuna iuvat 🛡️",
    "ALMENDRAS 🌰",
    "Jesus Christ be praised! 🙏",
]

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
    
    # Español spicy 🔥
    "Advertencia: Luke detectado. Hidrátate.",
    "Demasiado guapo para manejarlo, demasiado icónico para ignorarlo.",
    "Tu corazón acaba de acelerarse un 27%. De nada.",
    "Este Luke está clínicamente probado para causar sonrojos.",
    "Precaución: el contacto visual puede inducir sed.",
    "Si estás leyendo esto, ya es tarde. Estás nervios@.",
    "Mmm… alguien se ve delicioso hoy.",
    "Luke picante entregado. Maneja con cuidado.",
    "Niveles de atracción subiendo repentinamente…",
    "Temperatura en aumento: procede con precaución.",
    "No estabas list@ para este nivel de Luke.",
    "Sí, estás sonrojad@. No mientas.",
    "Niveles de sed: CRÍTICOS.",
    "Ay papi… qué guapo.",
    "Luke ha llegado y tú no estás preparad@.",
    "¿Hace calor aquí o soy yo?… No, es Luke.",
    "Esto debería ser ilegal. Demasiado bien.",
    "Tu pulso: 📈 Tu dignidad: 📉",
    "Permiso, vengo a robarte el aliento.",
    "Código rojo: Luke peligrosamente atractivo detectado.",
]

# ==========================
# Google Drive
# ==========================

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def get_drive_service():
    try:
        # Priorizar JSON desde variable de entorno (para Railway)
        if SERVICE_ACCOUNT_JSON:
            import json
            service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
            creds = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES
            )
        elif SERVICE_ACCOUNT_FILE:
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
        else:
            raise ValueError("No se encontró configuración de Service Account")
        
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        logger.error(f"Error conectando con Google Drive: {e}")
        raise

def get_all_media_files_from_folder():
    try:
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

        logger.info(f"Cargados {len(files)} archivos desde Drive")
        return files
    except Exception as e:
        logger.error(f"Error obteniendo archivos de Drive: {e}")
        return []

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
        logger.debug("ffmpeg no está disponible en el sistema")
        return None

    base = os.path.splitext(input_path)[0]
    palette = f"{base}_palette.png"
    out_path = f"{base}_compressed.gif"
    register_temp_file(palette)
    register_temp_file(out_path)

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
            logger.debug(f"Intento compresión {i+1}: size={out_size} bytes, target={target_bytes}")
            if out_size <= target_bytes:
                # cleanup palette
                cleanup_temp_file(palette)
                return out_path

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout en compresión ffmpeg (intento {i+1})")
        except Exception as e:
            logger.debug(f"Error en compresión: {e}")

        # make compression stronger
        scale_factor *= 0.75
        fps = max(8, int(fps * 0.85))

    # final cleanup
    cleanup_temp_file(palette)

    # if out_path exists but not small enough, remove it
    if os.path.exists(out_path):
        try:
            if os.path.getsize(out_path) <= target_bytes:
                return out_path
        except Exception:
            pass
        cleanup_temp_file(out_path)

    return None

# ==========================
# Eventos y comandos
# ==========================

@bot.event
async def on_ready():
    logger.info(f"{bot_name} ONLINE como {bot.user} (id: {bot.user.id})")
    try:
        await bot.change_presence(activity=discord.Game(name="summoning Luke"))
    except Exception as e:
        logger.error(f"Error cambiando presencia: {e}")
    
    # Iniciar tarea de auto-post si está configurado el canal
    if AUTO_POST_CHANNEL_ID:
        auto_post_almonds.start()
        logger.info(f"Auto-post ALMONDS iniciado para canal ID: {AUTO_POST_CHANNEL_ID}")
    else:
        logger.info("AUTO_POST_CHANNEL_ID no configurado, auto-post ALMONDS deshabilitado")
    
    # Iniciar tarea de auto-post KCD cada 8h
    if KCD_POST_CHANNEL_ID:
        auto_post_kcd.start()
        logger.info(f"Auto-post KCD iniciado para canal ID: {KCD_POST_CHANNEL_ID}")
    else:
        logger.info("KCD_POST_CHANNEL_ID no configurado, auto-post KCD deshabilitado")

@bot.event
async def on_disconnect():
    logger.warning("Bot desconectado de Discord")

@bot.event
async def on_resumed():
    logger.info("Bot reconectado a Discord")

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Error en evento {event}", exc_info=True)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignorar comandos no encontrados
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Falta un argumento requerido: {error.param.name}")
    else:
        logger.error(f"Error en comando {ctx.command}: {error}", exc_info=True)
        await ctx.send("Ocurrió un error al ejecutar el comando. Intenta de nuevo.")

# ==========================
# Tarea automática: Auto-post cada 6 horas
# ==========================

@tasks.loop(hours=6)
async def auto_post_almonds():
    """Post automático cada 6 horas con imagen random y frase ALMONDS."""
    if not AUTO_POST_CHANNEL_ID:
        return
    
    tmp_file = None
    compressed_file = None
    try:
        channel = bot.get_channel(int(AUTO_POST_CHANNEL_ID))
        if not channel:
            logger.error(f"Canal {AUTO_POST_CHANNEL_ID} no encontrado")
            return

        files = get_all_media_files_from_folder()
        if not files:
            logger.warning("No hay archivos en Drive para auto-post")
            return

        # Seleccionar archivo dentro del límite
        file = select_random_file_with_limit(files, MAX_GIF_SIZE_BYTES)
        if not file:
            logger.warning(f"No se encontró archivo dentro del límite de {MAX_GIF_MB} MB")
            return

        url = f"https://drive.google.com/uc?export=download&id={file['id']}"
        quote = random.choice(ALMONDS_QUOTES)

        if file['mimeType'] == 'image/gif':
            r = requests.get(url, stream=True, timeout=30)
            if r.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as tmp:
                    tmp_file = tmp.name
                    register_temp_file(tmp_file)
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            tmp.write(chunk)
                    tmp.flush()
                    tmp_size = os.path.getsize(tmp.name)
                    
                    if tmp_size > DISCORD_MAX_BYTES:
                        if ffmpeg_available():
                            logger.debug(f"Auto-post GIF {file['name']} es {tmp_size} bytes, comprimiendo")
                            compressed_file = compress_gif_with_ffmpeg(tmp.name, DISCORD_MAX_BYTES)
                            if compressed_file and os.path.exists(compressed_file):
                                comp_size = os.path.getsize(compressed_file)
                                if comp_size <= DISCORD_MAX_BYTES:
                                    await channel.send(content=quote, file=discord.File(compressed_file, filename=file['name']))
                                    cleanup_temp_file(compressed_file)
                                    cleanup_temp_file(tmp_file)
                                    logger.info(f"Auto-post enviado: {quote}")
                                    return
                            logger.warning("Auto-post: compresión fallida")
                            cleanup_temp_file(tmp_file)
                            return
                        else:
                            logger.warning(f"Auto-post: GIF muy grande y ffmpeg no disponible")
                            cleanup_temp_file(tmp_file)
                            return
                    
                    if tmp_size > MAX_GIF_SIZE_BYTES:
                        logger.warning(f"Auto-post: GIF muy grande ({tmp_size/1024/1024:.1f} MB)")
                        cleanup_temp_file(tmp_file)
                        return

                    await channel.send(content=quote, file=discord.File(tmp.name, filename=file['name']))
                    cleanup_temp_file(tmp_file)
                    logger.info(f"Auto-post enviado: {quote}")
            else:
                logger.error("Auto-post: no se pudo descargar GIF")
        else:
            almonds_color = discord.Color.from_rgb(
                random.randint(150, 255),
                random.randint(100, 200),
                random.randint(50, 150)
            )
            embed = discord.Embed(
                title=quote,
                color=almonds_color
            )
            embed.set_image(url=url)
            await channel.send(embed=embed)
            logger.info(f"Auto-post enviado: {quote}")
            
    except Exception as e:
        logger.error(f"Error en auto-post: {e}", exc_info=True)
    finally:
        if tmp_file:
            cleanup_temp_file(tmp_file)
        if compressed_file:
            cleanup_temp_file(compressed_file)

@auto_post_almonds.before_loop
async def before_auto_post():
    """Esperar a que el bot esté listo antes de iniciar el loop."""
    await bot.wait_until_ready()
    logger.info("Auto-post ALMONDS loop listo para iniciar")

# ==========================
# Tarea automática: Auto-post KCD cada 8 horas
# ==========================

@tasks.loop(hours=8)
async def auto_post_kcd():
    """Post automático cada 8 horas con imagen random y frase KCD."""
    if not KCD_POST_CHANNEL_ID:
        return
    
    tmp_file = None
    compressed_file = None
    try:
        channel = bot.get_channel(int(KCD_POST_CHANNEL_ID))
        if not channel:
            logger.error(f"Canal KCD {KCD_POST_CHANNEL_ID} no encontrado")
            return

        files = get_all_media_files_from_folder()
        if not files:
            logger.warning("No hay archivos en Drive para auto-post KCD")
            return

        # Seleccionar archivo dentro del límite
        file = select_random_file_with_limit(files, MAX_GIF_SIZE_BYTES)
        if not file:
            logger.warning(f"No se encontró archivo KCD dentro del límite de {MAX_GIF_MB} MB")
            return

        url = f"https://drive.google.com/uc?export=download&id={file['id']}"
        quote = random.choice(KCD_QUOTES)

        if file['mimeType'] == 'image/gif':
            r = requests.get(url, stream=True, timeout=30)
            if r.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as tmp:
                    tmp_file = tmp.name
                    register_temp_file(tmp_file)
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            tmp.write(chunk)
                    tmp.flush()
                    tmp_size = os.path.getsize(tmp.name)
                    
                    if tmp_size > DISCORD_MAX_BYTES:
                        if ffmpeg_available():
                            logger.debug(f"Auto-post KCD GIF {file['name']} es {tmp_size} bytes, comprimiendo")
                            compressed_file = compress_gif_with_ffmpeg(tmp.name, DISCORD_MAX_BYTES)
                            if compressed_file and os.path.exists(compressed_file):
                                comp_size = os.path.getsize(compressed_file)
                                if comp_size <= DISCORD_MAX_BYTES:
                                    await channel.send(content=quote, file=discord.File(compressed_file, filename=file['name']))
                                    cleanup_temp_file(compressed_file)
                                    cleanup_temp_file(tmp_file)
                                    logger.info(f"Auto-post KCD enviado: {quote}")
                                    return
                            logger.warning("Auto-post KCD: compresión fallida")
                            cleanup_temp_file(tmp_file)
                            return
                        else:
                            logger.warning(f"Auto-post KCD: GIF muy grande y ffmpeg no disponible")
                            cleanup_temp_file(tmp_file)
                            return
                    
                    if tmp_size > MAX_GIF_SIZE_BYTES:
                        logger.warning(f"Auto-post KCD: GIF muy grande ({tmp_size/1024/1024:.1f} MB)")
                        cleanup_temp_file(tmp_file)
                        return

                    await channel.send(content=quote, file=discord.File(tmp.name, filename=file['name']))
                    cleanup_temp_file(tmp_file)
                    logger.info(f"Auto-post KCD enviado: {quote}")
            else:
                logger.error("Auto-post KCD: no se pudo descargar GIF")
        else:
            kcd_color = discord.Color.from_rgb(
                random.randint(100, 200),
                random.randint(100, 180),
                random.randint(50, 120)
            )
            embed = discord.Embed(
                title=quote,
                color=kcd_color
            )
            embed.set_image(url=url)
            await channel.send(embed=embed)
            logger.info(f"Auto-post KCD enviado: {quote}")
            
    except Exception as e:
        logger.error(f"Error en auto-post KCD: {e}", exc_info=True)
    finally:
        if tmp_file:
            cleanup_temp_file(tmp_file)
        if compressed_file:
            cleanup_temp_file(compressed_file)

@auto_post_kcd.before_loop
async def before_auto_post_kcd():
    """Esperar a que el bot esté listo antes de iniciar el loop KCD."""
    await bot.wait_until_ready()
    logger.info("Auto-post KCD loop listo para iniciar")

# ==========================
# Comandos
# ==========================

# -----------------------------------
# !luke — modo normal
# -----------------------------------
@bot.command(name="luke", help="Random Luke image + normal quote")
async def luke_command(ctx):
    tmp_file = None
    compressed_file = None
    try:
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
            r = requests.get(url, stream=True, timeout=30)
            if r.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as tmp:
                    tmp_file = tmp.name
                    register_temp_file(tmp_file)
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            tmp.write(chunk)
                    tmp.flush()
                    tmp_size = os.path.getsize(tmp.name)
                    # If exceeds Discord per-file limit, attempt to compress to DISCORD_MAX_BYTES
                    if tmp_size > DISCORD_MAX_BYTES:
                        if ffmpeg_available():
                            logger.debug(f"GIF {file['name']} es {tmp_size} bytes, intentando comprimir a {DISCORD_MAX_BYTES} bytes")
                            compressed_file = compress_gif_with_ffmpeg(tmp.name, DISCORD_MAX_BYTES)
                            if compressed_file and os.path.exists(compressed_file):
                                comp_size = os.path.getsize(compressed_file)
                                if comp_size <= DISCORD_MAX_BYTES:
                                    await ctx.send(content=quote, file=discord.File(compressed_file, filename=file['name']))
                                    cleanup_temp_file(compressed_file)
                                    cleanup_temp_file(tmp_file)
                                    return
                                else:
                                    await ctx.send(f"GIF omitido — no fue posible reducirlo por debajo de {DISCORD_MAX_MB} MB.")
                                    cleanup_temp_file(compressed_file)
                                    cleanup_temp_file(tmp_file)
                                    return
                            else:
                                await ctx.send(f"GIF omitido — compresión fallida o ffmpeg no disponible.")
                                cleanup_temp_file(tmp_file)
                                return
                        else:
                            await ctx.send(f"GIF omitido — demasiado grande ({tmp_size/1024/1024:.1f} MB) y `ffmpeg` no está disponible para comprimir.")
                            cleanup_temp_file(tmp_file)
                            return

                    if tmp_size > MAX_GIF_SIZE_BYTES:
                        await ctx.send(f"GIF omitido — demasiado grande ({tmp_size/1024/1024:.1f} MB). Límite: {MAX_GIF_MB} MB.")
                        cleanup_temp_file(tmp_file)
                        return

                    sent = await ctx.send(content=quote, file=discord.File(tmp.name, filename=file['name']))
                    cleanup_temp_file(tmp_file)
                    try:
                        await sent.add_reaction("✨")
                    except Exception:
                        pass
            else:
                sent = await ctx.send("No se pudo descargar el GIF.")
                try:
                    await sent.add_reaction("✨")
                except Exception:
                    pass
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
            sent = await ctx.send(embed=embed)
            try:
                await sent.add_reaction("✨")
            except Exception:
                pass
    except requests.Timeout:
        logger.error("Timeout descargando imagen")
        await ctx.send("Timeout al descargar la imagen. Intenta de nuevo.")
    except Exception as e:
        logger.error(f"Error en comando !luke: {e}", exc_info=True)
        await ctx.send("Ocurrió un error. Intenta de nuevo.")
    finally:
        if tmp_file:
            cleanup_temp_file(tmp_file)
        if compressed_file:
            cleanup_temp_file(compressed_file)

# -----------------------------------
# !spicyluke — modo SPICY 🔥
# -----------------------------------
@bot.command(name="spicyluke", help="SPICY Luke image + spicy quote 🔥")
async def spicyluke_command(ctx):
    tmp_file = None
    compressed_file = None
    try:
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
            r = requests.get(url, stream=True, timeout=30)
            if r.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as tmp:
                    tmp_file = tmp.name
                    register_temp_file(tmp_file)
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            tmp.write(chunk)
                    tmp.flush()
                    tmp_size = os.path.getsize(tmp.name)
                    # If exceeds Discord per-file limit, attempt to compress to DISCORD_MAX_BYTES
                    if tmp_size > DISCORD_MAX_BYTES:
                        if ffmpeg_available():
                            logger.debug(f"GIF spicy {file['name']} es {tmp_size} bytes, intentando comprimir a {DISCORD_MAX_BYTES} bytes")
                            compressed_file = compress_gif_with_ffmpeg(tmp.name, DISCORD_MAX_BYTES)
                            if compressed_file and os.path.exists(compressed_file):
                                comp_size = os.path.getsize(compressed_file)
                                if comp_size <= DISCORD_MAX_BYTES:
                                    await ctx.send(content=f"🔥 {quote}", file=discord.File(compressed_file, filename=file['name']))
                                    cleanup_temp_file(compressed_file)
                                    cleanup_temp_file(tmp_file)
                                    return
                                else:
                                    await ctx.send(f"GIF spicy omitido — no fue posible reducirlo por debajo de {DISCORD_MAX_MB} MB.")
                                    cleanup_temp_file(compressed_file)
                                    cleanup_temp_file(tmp_file)
                                    return
                            else:
                                await ctx.send(f"GIF spicy omitido — compresión fallida o ffmpeg no disponible.")
                                cleanup_temp_file(tmp_file)
                                return
                        else:
                            await ctx.send(f"GIF spicy omitido — demasiado grande ({tmp_size/1024/1024:.1f} MB) y `ffmpeg` no está disponible para comprimir.")
                            cleanup_temp_file(tmp_file)
                            return

                    if tmp_size > MAX_GIF_SIZE_BYTES:
                        await ctx.send(f"GIF spicy omitido — demasiado grande ({tmp_size/1024/1024:.1f} MB). Límite: {MAX_GIF_MB} MB.")
                        cleanup_temp_file(tmp_file)
                        return

                    sent = await ctx.send(content=f"🔥 {quote}", file=discord.File(tmp.name, filename=file['name']))
                    cleanup_temp_file(tmp_file)
                    try:
                        await sent.add_reaction("✨")
                    except Exception:
                        pass
            else:
                sent = await ctx.send("No se pudo descargar el GIF spicy.")
                try:
                    await sent.add_reaction("✨")
                except Exception:
                    pass
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
            sent = await ctx.send(embed=embed)
            try:
                await sent.add_reaction("✨")
            except Exception:
                pass
    except requests.Timeout:
        logger.error("Timeout descargando imagen spicy")
        await ctx.send("Timeout al descargar la imagen. Intenta de nuevo.")
    except Exception as e:
        logger.error(f"Error en comando !spicyluke: {e}", exc_info=True)
        await ctx.send("Ocurrió un error. Intenta de nuevo.")
    finally:
        if tmp_file:
            cleanup_temp_file(tmp_file)
        if compressed_file:
            cleanup_temp_file(compressed_file)

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
            "**!almendras** — random Luke image + random nut type 🌰\n"
            "**Auto-Post (6h)** — Random Luke + ALMONDS quote 🌰\n"
            "**Auto-Post (8h)** — Random Luke + KCD quote ⚔️\n"
            "**Source:** Google Drive folder (JPG, PNG, GIF)\n\n"
            "Add new images to the Drive folder and LukeyBot will use them automatically.\n"
            "Hydration recommended."
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed)


@bot.command(name="ping", help="Check bot latency")
async def ping(ctx):
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"Pong! Latencia: {latency_ms} ms")

# -----------------------------------
# !almendras — imagen + tipo de nuez
# -----------------------------------
@bot.command(name="almendras", help="Random Luke image + random nut type 🌰")
async def almendras_command(ctx):
    tmp_file = None
    compressed_file = None
    try:
        files = get_all_media_files_from_folder()
        if DEBUG:
            await ctx.send(f"[DEBUG] Archivos en Drive: {len(files)}")
        if not files:
            await ctx.send("No hay almendras en el Drive 🌰")
            return

        # Seleccionar archivo dentro del límite
        file = select_random_file_with_limit(files, MAX_GIF_SIZE_BYTES)
        if not file:
            await ctx.send(f"No se encontró ninguna imagen/GIF dentro del límite de {MAX_GIF_MB} MB.")
            return

        url = f"https://drive.google.com/uc?export=download&id={file['id']}"
        quote = random.choice(ALMONDS_QUOTES)

        if file['mimeType'] == 'image/gif':
            r = requests.get(url, stream=True, timeout=30)
            if r.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as tmp:
                    tmp_file = tmp.name
                    register_temp_file(tmp_file)
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            tmp.write(chunk)
                    tmp.flush()
                    tmp_size = os.path.getsize(tmp.name)
                    
                    if tmp_size > DISCORD_MAX_BYTES:
                        if ffmpeg_available():
                            logger.debug(f"GIF almendras {file['name']} es {tmp_size} bytes, intentando comprimir a {DISCORD_MAX_BYTES} bytes")
                            compressed_file = compress_gif_with_ffmpeg(tmp.name, DISCORD_MAX_BYTES)
                            if compressed_file and os.path.exists(compressed_file):
                                comp_size = os.path.getsize(compressed_file)
                                if comp_size <= DISCORD_MAX_BYTES:
                                    await ctx.send(content=quote, file=discord.File(compressed_file, filename=file['name']))
                                    cleanup_temp_file(compressed_file)
                                    cleanup_temp_file(tmp_file)
                                    return
                                else:
                                    await ctx.send(f"GIF omitido — no fue posible reducirlo por debajo de {DISCORD_MAX_MB} MB.")
                                    cleanup_temp_file(compressed_file)
                                    cleanup_temp_file(tmp_file)
                                    return
                            else:
                                await ctx.send(f"GIF omitido — compresión fallida o ffmpeg no disponible.")
                                cleanup_temp_file(tmp_file)
                                return
                        else:
                            await ctx.send(f"GIF omitido — demasiado grande ({tmp_size/1024/1024:.1f} MB) y `ffmpeg` no está disponible para comprimir.")
                            cleanup_temp_file(tmp_file)
                            return

                    if tmp_size > MAX_GIF_SIZE_BYTES:
                        await ctx.send(f"GIF omitido — demasiado grande ({tmp_size/1024/1024:.1f} MB). Límite: {MAX_GIF_MB} MB.")
                        cleanup_temp_file(tmp_file)
                        return

                    sent = await ctx.send(content=quote, file=discord.File(tmp.name, filename=file['name']))
                    cleanup_temp_file(tmp_file)
                    try:
                        await sent.add_reaction("🌰")
                    except Exception:
                        pass
            else:
                sent = await ctx.send("No se pudo descargar el GIF de almendras.")
                try:
                    await sent.add_reaction("🌰")
                except Exception:
                    pass
        else:
            almendras_color = discord.Color.from_rgb(
                random.randint(150, 220),
                random.randint(120, 180),
                random.randint(80, 140)
            )
            embed = discord.Embed(
                title=quote,
                color=almendras_color
            )
            embed.set_image(url=url)
            sent = await ctx.send(embed=embed)
            try:
                await sent.add_reaction("🌰")
            except Exception:
                pass
    except requests.Timeout:
        logger.error("Timeout descargando imagen almendras")
        await ctx.send("Timeout al descargar la imagen. Intenta de nuevo.")
    except Exception as e:
        logger.error(f"Error en comando !almendras: {e}", exc_info=True)
        await ctx.send("Ocurrió un error. Intenta de nuevo.")
    finally:
        if tmp_file:
            cleanup_temp_file(tmp_file)
        if compressed_file:
            cleanup_temp_file(compressed_file)

# ==========================
# Run bot
# ==========================

if __name__ == "__main__":
    try:
        logger.info("Iniciando LukeyBot...")
        bot.run(DISCORD_TOKEN, reconnect=True)
    except KeyboardInterrupt:
        logger.info("Bot detenido por usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
    finally:
        cleanup_temp_files()
        logger.info("LukeyBot finalizado")
