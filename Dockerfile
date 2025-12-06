FROM python:3.13-slim

# Evitar buffering para ver logs en tiempo real
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar archivos de requirements primero para aprovechar cache de Docker
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

# Copiar el resto del código
COPY . /app

# Evitar incluir secretos en la imagen; se espera que se pasen por variables/env
ENV GOOGLE_APPLICATION_CREDENTIALS=service_account.json

CMD ["python", "lukeybot.py"]
