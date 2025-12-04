import os
from fastapi import FastAPI
from dotenv import load_dotenv

from app.routes.converter import router as converter_router
from app.routes.users import router as users_router

load_dotenv()

FILES_DIR = os.getenv("FILES_DIR", "app/files")
if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR, exist_ok=True)

app = FastAPI(
    title="YouTube Converter MVP",
    description="Serviço para converter vídeos do YouTube para MP3 ou MP4",
    version="1.0.0"
)

# Register routes
app.include_router(converter_router)
app.include_router(users_router)
