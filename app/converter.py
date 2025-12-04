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
