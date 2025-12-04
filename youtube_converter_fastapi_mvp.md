# YouTube Converter MVP — FastAPI

Projeto pronto (boilerplate) para um **MVP de conversor de vídeos do YouTube** usando **FastAPI + yt-dlp + ffmpeg**. Conteúdo incluído: estrutura de projeto, código do backend, Dockerfile, docker-compose e instruções de uso.

---

## Estrutura do repositório

```
youtube-converter-fastapi-mvp/
├── app/
│   ├── main.py              # FastAPI app
│   ├── converter.py         # Lógica de download / conversão
│   ├── utils.py             # Helpers e validações
│   └── files/               # saída temporária (gitignore)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## README (conteúdo principal)

```markdown
# YouTube Converter MVP (FastAPI)

## Visão geral
Pequeno serviço que converte vídeos do YouTube para MP3 ou MP4 usando `yt-dlp` e `ffmpeg`.

Este repo fornece um backend em FastAPI com endpoints para:
- iniciar conversão (POST /convert)
- baixar arquivo convertido (via /files/)

Arquitetura: request -> FastAPI -> yt-dlp (baixa) -> ffmpeg (quando necessário) -> arquivo temporário -> link de download

---

## Pré-requisitos
- Docker (recomendado) ou Python 3.10+
- ffmpeg instalado no host (se não usar Docker)
- yt-dlp instalado no host (se não usar Docker)

---

## Variáveis de ambiente
Copie `.env.example` para `.env` e ajuste se necessário.

---

## Como rodar (local, sem Docker)
1. Crie e ative um venv
```bash
python -m venv .venv
source .venv/bin/activate    # macOS / Linux
.venv\Scripts\activate      # Windows
```
2. Instale dependências
```bash
pip install -r requirements.txt
```
3. Crie a pasta de arquivos
```bash
mkdir -p app/files
```
4. Instale ffmpeg e yt-dlp no sistema
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg -y
python -m pip install -U yt-dlp
```
5. Rode a aplicação
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
6. Use o endpoint POST /convert
```bash
curl -X POST "http://localhost:8000/convert" -H "Content-Type: application/json" -d '{"url":"https://www.youtube.com/watch?v=XXXXX","format":"mp3"}'
```

---

## Como rodar com Docker (recomendado)
1. Build & up
```bash
docker compose up --build
```
2. Acesse `http://localhost:8000/docs` para a documentação interativa do FastAPI

---

## Observações de produção
- Arquivos ficam em `app/files` e expiram depois de X minutos (implementar TTL/limpeza). Há um endpoint simples, mas recomendo usar um worker/queue para conversões longas.
- Use S3/Backblaze/Cloudflare R2 para armazenar arquivos e gerar URLs presigned para downloads.
- Proteja endpoints com rate limiting e proteção contra uso indevido.

---

## Licença
MIT
```
```

---

## Arquivos do projeto

### `requirements.txt`

```
fastapi
uvicorn[standard]
pydantic
python-multipart
yt-dlp
ffmpeg-python
python-dotenv
```

---

### `.env.example`

```
# Porta para o uvicorn
PORT=8000
# Diretório onde os arquivos convertidos serão salvos
FILES_DIR=app/files
# Tempo de expiração (segundos) - para referência
FILE_TTL=900
```

---

### `Dockerfile`

```dockerfile
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
```

---

### `docker-compose.yml`

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./app/files:/app/app/files
    environment:
      - PORT=8000
      - FILES_DIR=/app/app/files
      - FILE_TTL=900
```

---

### `app/main.py`

```python
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from .converter import convert_and_prepare
from dotenv import load_dotenv

load_dotenv()

FILES_DIR = os.getenv("FILES_DIR", "app/files")
if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR, exist_ok=True)

app = FastAPI(title="YouTube Converter MVP")

class ConvertRequest(BaseModel):
    url: HttpUrl
    format: str  # 'mp3' or 'mp4'

@app.post('/convert')
async def convert(req: ConvertRequest):
    if req.format not in ('mp3', 'mp4'):
        raise HTTPException(status_code=400, detail='Formato inválido')

    try:
        download_path = await convert_and_prepare(str(req.url), req.format, FILES_DIR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    filename = os.path.basename(download_path)
    return {"download_url": f"/files/{filename}", "filename": filename}

@app.get('/files/{filename}')
async def get_file(filename: str):
    safe_path = os.path.join(FILES_DIR, os.path.basename(filename))
    if not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail='Arquivo não encontrado')
    return FileResponse(safe_path, media_type='application/octet-stream', filename=filename)
```

---

### `app/converter.py`

```python
import asyncio
import os
import uuid
import shlex
from yt_dlp import YoutubeDL
import subprocess

async def run_subprocess(cmd: list):
    """Run subprocess asynchronously (Python 3.7+)."""
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nstdout: {stdout.decode()}\nstderr: {stderr.decode()}")
    return stdout.decode(), stderr.decode()

async def download_video(url: str, out_template: str):
    ydl_opts = {
        'outtmpl': out_template,
        'quiet': True,
        'noplaylist': True,
    }
    loop = asyncio.get_event_loop()
    # yt-dlp is synchronous, run it in thread pool
    def _download():
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info
    info = await loop.run_in_executor(None, _download)
    return info

async def convert_and_prepare(url: str, fmt: str, files_dir: str):
    # unique prefix
    uid = str(uuid.uuid4())
    base_out = os.path.join(files_dir, uid)

    # first download the best video (or audio) with yt-dlp
    # save temporary file path (let yt-dlp pick extension)
    out_template = base_out + '.%(ext)s'
    info = await download_video(url, out_template)

    # find downloaded filename from info
    # yt-dlp returns 'requested_formats' or 'ext'
    # try common keys
    downloaded_filepath = None
    if 'requested_downloads' in info:
        # older structures (defensive)
        downloaded_filepath = info['requested_downloads'][0].get('filename')
    elif 'url' in info and 'ext' in info:
        # fallback (not always accurate)
        # search for a file that starts with uid in files_dir
        for f in os.listdir(files_dir):
            if f.startswith(uid):
                downloaded_filepath = os.path.join(files_dir, f)
                break
    else:
        # search
        for f in os.listdir(files_dir):
            if f.startswith(uid):
                downloaded_filepath = os.path.join(files_dir, f)
                break

    if not downloaded_filepath or not os.path.exists(downloaded_filepath):
        # try best-effort detection
        candidates = [os.path.join(files_dir, f) for f in os.listdir(files_dir) if f.startswith(uid)]
        if candidates:
            downloaded_filepath = candidates[0]

    if not downloaded_filepath:
        raise RuntimeError('Não foi possível localizar o arquivo baixado')

    # desired output path
    if fmt == 'mp3':
        final_path = base_out + '.mp3'
        # use ffmpeg to extract audio
        cmd = ['ffmpeg', '-y', '-i', downloaded_filepath, '-vn', '-ab', '192k', '-ar', '44100', final_path]
        await run_subprocess(cmd)
    else:
        # mp4 - we can remux/convert to mp4 720p to standardize size
        final_path = base_out + '.mp4'
        # scale to 1280x720 while preserving aspect with ffmpeg
        cmd = [
            'ffmpeg', '-y', '-i', downloaded_filepath,
            '-vf', "scale='min(1280,iw)':-2",
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k', final_path
        ]
        await run_subprocess(cmd)

    # optionally remove the original downloaded file to save space
    try:
        if downloaded_filepath != final_path and os.path.exists(downloaded_filepath):
            os.remove(downloaded_filepath)
    except Exception:
        pass

    return final_path
```

---

### `app/utils.py` (opcional)

```python
import re

YT_REGEX = re.compile(r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})')

def is_youtube_url(url: str) -> bool:
    return bool(YT_REGEX.search(url))
```

---

## Observações finais
- Este projeto é um ponto de partida: você pode adicionar fila (Redis + RQ/Celery), TTL de arquivos, cache, proteção por token, logs, métricas e armazenamento em S3.
- Teste com vídeos curtos primeiro para confirmar que a pipeline está ok.

---

Se quiser, eu posso:
- Gerar o mesmo projeto em **Laravel** ou **Node.js** para comparação.
- Converter isto em um repositório GitHub pronto para clonar com `git init` + commits.
- Adicionar um pequeno frontend Next.js que consome o endpoint.

Diga qual próximo passo você prefere.

