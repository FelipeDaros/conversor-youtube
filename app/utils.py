import re

YT_REGEX = re.compile(r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})')

def is_youtube_url(url: str) -> bool:
    return bool(YT_REGEX.search(url))
