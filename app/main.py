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
