FROM python:3.11-slim

# evitar prompts
ENV DEBIAN_FRONTEND=noninteractive

# instalar dependências do sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
       git \
       curl \
    && rm -rf /var/lib/apt/lists/*

# instalar yt-dlp via pip (mais simples que apt)
RUN pip install --no-cache-dir yt-dlp

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ./app /app/app

# criar pasta de arquivos
RUN mkdir -p /app/app/files

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
