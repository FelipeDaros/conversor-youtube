from pydantic import BaseModel, HttpUrl


class ConvertRequest(BaseModel):
    url: HttpUrl
    format: str  # 'mp3' or 'mp4'


class ConvertResponse(BaseModel):
    download_url: str
    filename: str

class Users (BaseModel):
    username: str
    email: str
    password: str
    is_active: bool = True
    last_login: str = None
    updated_at: str = None