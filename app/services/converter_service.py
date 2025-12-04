import asyncio
import os
import uuid
from yt_dlp import YoutubeDL


async def run_subprocess(cmd: list):
    """Run subprocess asynchronously (Python 3.7+)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed: {cmd}\nstdout: {stdout.decode()}\nstderr: {stderr.decode()}"
        )
    return stdout.decode(), stderr.decode()


async def download_video(url: str, out_template: str):
    """Download video from YouTube using yt-dlp."""
    ydl_opts = {
        'outtmpl': out_template,
        'quiet': True,
        'noplaylist': True,
    }
    loop = asyncio.get_event_loop()
    
    def _download():
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info
    
    info = await loop.run_in_executor(None, _download)
    return info


def _find_downloaded_file(files_dir: str, uid: str) -> str:
    """Find the downloaded file by uid prefix."""
    candidates = [
        os.path.join(files_dir, f)
        for f in os.listdir(files_dir)
        if f.startswith(uid)
    ]
    if candidates:
        return candidates[0]
    return None


async def convert_and_prepare(url: str, fmt: str, files_dir: str) -> str:
    """Convert YouTube video to MP3 or MP4."""
    uid = str(uuid.uuid4())
    base_out = os.path.join(files_dir, uid)
    out_template = base_out + '.%(ext)s'
    
    # Download video
    info = await download_video(url, out_template)
    
    # Find downloaded file
    downloaded_filepath = _find_downloaded_file(files_dir, uid)
    
    if not downloaded_filepath:
        raise RuntimeError('Não foi possível localizar o arquivo baixado')
    
    # Convert to desired format
    if fmt == 'mp3':
        final_path = base_out + '.mp3'
        cmd = [
            'ffmpeg', '-y', '-i', downloaded_filepath,
            '-vn', '-ab', '192k', '-ar', '44100', final_path
        ]
        await run_subprocess(cmd)
    elif fmt == 'mp4':
        final_path = base_out + '.mp4'
        cmd = [
            'ffmpeg', '-y', '-i', downloaded_filepath,
            '-vf', "scale='min(1280,iw)':-2",
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k', final_path
        ]
        await run_subprocess(cmd)
    else:
        raise ValueError(f'Formato inválido: {fmt}')
    
    # Remove original file to save space
    try:
        if downloaded_filepath != final_path and os.path.exists(downloaded_filepath):
            os.remove(downloaded_filepath)
    except Exception:
        pass
    
    return final_path
