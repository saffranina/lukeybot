# LukeyBot

# Bot de Discord con integración a Google Drive

Este proyecto es un bot de Discord desarrollado en Python que permite a los usuarios obtener imágenes y GIFs almacenados en una carpeta de Google Drive, respondiendo a comandos personalizados en el servidor. El bot está diseñado para ser fácil de desplegar y seguro, manteniendo las credenciales fuera del repositorio.

## Características principales

- Responde a comandos en Discord enviando imágenes o GIFs aleatorios desde una carpeta de Google Drive.
- Permite configurar diferentes carpetas para distintos comandos.
- Envía los GIFs como archivos adjuntos para asegurar que se animen correctamente en Discord.
- Incluye un sistema de mensajes de ayuda y un modo debug opcional.
- Maneja errores de forma robusta y muestra mensajes claros al usuario.

## Seguridad

- Las credenciales y tokens se almacenan en archivos `.env` y `service_account.json`, que están excluidos del repositorio mediante `.gitignore`.
- No subas tus credenciales a GitHub ni las compartas públicamente.

## Despliegue 24/7

Puedes desplegar este bot gratis en plataformas como Railway, Replit o Render. Solo necesitas subir tu código a GitHub y seguir las instrucciones de despliegue de cada plataforma. Recuerda configurar las variables de entorno y subir tu archivo de credenciales de Google Drive de forma segura.

## Instalación local

1. Clona este repositorio.
2. Instala las dependencias con `pip install -r requirements.txt`.
3. Crea un archivo `.env` con tu token de Discord y el ID de la carpeta de Google Drive.
4. Descarga tu `service_account.json` de Google Cloud y colócalo en la raíz del proyecto.
5. Ejecuta el bot con `python lukeybot.py`.

## Comandos disponibles

- Comando principal: envía una imagen o GIF aleatorio desde la carpeta configurada.
- Comando alternativo: permite obtener contenido de otra carpeta (por ejemplo, contenido "spicy").
- Comando de ayuda: muestra información sobre el uso del bot.

## Dependencias principales

- discord.py
- python-dotenv
- google-api-python-client
- google-auth

## Notas

- El bot está pensado para ser fácilmente personalizable y seguro.
- Puedes modificar los comandos y carpetas según tus necesidades.

---
Para dudas o mejoras, abre un issue o un pull request en este repositorio.
¡Un bot de Discord que envía imágenes y GIFs aleatorios desde una carpeta de Google Drive!

## Características
- Comando `!luke`: envía una imagen o GIF aleatorio con una frase divertida.
- Comando `!spicyluke`: envía una imagen o GIF aleatorio con una frase spicy.
- Comando `!lukeyhelp`: muestra instrucciones de uso.
- Soporta imágenes JPG, PNG y GIF animados.
- Las imágenes se obtienen automáticamente de una carpeta de Google Drive.

## Requisitos
- Python 3.8+
- Un bot de Discord y su token
- Una carpeta en Google Drive con imágenes
- Un archivo de credenciales de Google Service Account

## Instalación
1. Clona este repositorio:
	```bash
	git clone https://github.com/TU_USUARIO/lukeybot.git
	cd lukeybot
	```
2. Instala las dependencias:
	```bash
	pip install -r requirements.txt
	```
3. Crea un archivo `.env` con el siguiente contenido:
	```env
	DISCORD_TOKEN=tu_token_de_discord
	DRIVE_FOLDER_ID=tu_id_de_carpeta_drive
	GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
	DEBUG=False
	```
4. Coloca tu archivo `service_account.json` en la raíz del proyecto.

## Uso
Ejecuta el bot con:
```bash
python lukeybot.py
```

## Comandos
- `!luke` — Imagen/GIF + frase random
- `!spicyluke` — Imagen/GIF + frase spicy
- `!lukeyhelp` — Instrucciones

## Notas de seguridad
- **No subas tu archivo `.env` ni `service_account.json` a GitHub.**
- El archivo `.gitignore` ya está configurado para proteger tus secretos.

## Despliegue 24/7
Puedes desplegar este bot gratis en Railway, Render, Replit, etc. Solo asegúrate de configurar las variables de entorno y subir tus credenciales de forma segura.

---

¡Disfruta a LukeyBot!