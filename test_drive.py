#!/usr/bin/env python3
"""Script de prueba para verificar conexión con Google Drive"""

import os
import sys
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

print(f"🔍 Verificando configuración...")
print(f"DRIVE_FOLDER_ID: {DRIVE_FOLDER_ID}")
print(f"SERVICE_ACCOUNT_FILE: {SERVICE_ACCOUNT_FILE}")
print(f"SERVICE_ACCOUNT_JSON exists: {bool(SERVICE_ACCOUNT_JSON)}")
print()

try:
    # Intentar conectar
    if SERVICE_ACCOUNT_JSON:
        import json
        service_account_info = json.loads(SERVICE_ACCOUNT_JSON)
        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
        print("✅ Usando SERVICE_ACCOUNT_JSON")
    elif SERVICE_ACCOUNT_FILE:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        print("✅ Usando SERVICE_ACCOUNT_FILE")
    else:
        raise ValueError("No service account configurado")

    service = build("drive", "v3", credentials=creds)
    print("✅ Conexión a Drive establecida")
    print()

    # Intentar obtener info de la carpeta
    print(f"📁 Verificando carpeta {DRIVE_FOLDER_ID}...")
    try:
        folder_info = service.files().get(fileId=DRIVE_FOLDER_ID, fields="id,name,mimeType").execute()
        print(f"✅ Carpeta encontrada: '{folder_info.get('name')}'")
        print(f"   Type: {folder_info.get('mimeType')}")
    except Exception as e:
        print(f"❌ ERROR accediendo a la carpeta: {e}")
        print("\n⚠️  POSIBLES CAUSAS:")
        print("   1. La service account NO tiene permisos en esta carpeta")
        print("   2. El DRIVE_FOLDER_ID es incorrecto")
        print(f"   3. Necesitas compartir la carpeta con: {creds.service_account_email}")
        sys.exit(1)

    print()

    # Intentar listar archivos
    print("📂 Listando archivos en la carpeta...")
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

        batch = response.get("files", [])
        files.extend(batch)
        
        if batch:
            print(f"   Encontrados {len(batch)} archivos en esta página")
        
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    print()
    print(f"✅ TOTAL: {len(files)} archivos encontrados")
    
    if files:
        print("\n📋 Primeros archivos:")
        for f in files[:10]:
            print(f"   - {f['name']} ({f['mimeType']})")
    else:
        print("\n⚠️  NO SE ENCONTRARON ARCHIVOS")
        print("   Verifica que:")
        print(f"   1. La carpeta contenga imágenes (JPG, PNG, GIF)")
        print(f"   2. La service account tenga permisos de LECTURA")
        print(f"   3. Comparte la carpeta con: {creds.service_account_email}")

except Exception as e:
    print(f"❌ ERROR FATAL: {e}")
    import traceback
    traceback.print_exc()
