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
