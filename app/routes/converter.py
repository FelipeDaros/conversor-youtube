import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.converter import ConvertRequest, ConvertResponse
from app.services.converter_service import convert_and_prepare

router = APIRouter(prefix="/api", tags=["converter"])

FILES_DIR = os.getenv("FILES_DIR", "app/files")


@router.post('/convert', response_model=ConvertResponse)
async def convert(req: ConvertRequest):
    """Convert YouTube video to MP3 or MP4."""
    if req.format not in ('mp3', 'mp4'):
        raise HTTPException(status_code=400, detail='Formato inválido. Use mp3 ou mp4')

    try:
        download_path = await convert_and_prepare(str(req.url), req.format, FILES_DIR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    filename = os.path.basename(download_path)
    return ConvertResponse(
        download_url=f"/api/files/{filename}",
        filename=filename
    )


@router.get('/files/{filename}')
async def get_file(filename: str):
    """Download converted file."""
    safe_path = os.path.join(FILES_DIR, os.path.basename(filename))
    if not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail='Arquivo não encontrado')
    return FileResponse(safe_path, media_type='application/octet-stream', filename=filename)
