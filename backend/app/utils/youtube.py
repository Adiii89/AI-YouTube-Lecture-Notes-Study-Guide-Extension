import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

YOUTUBE_ID_EXACT = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def extract_video_id(url_or_id: str) -> Optional[str]:
    """
    Extract an 11-character YouTube video ID from various URL formats or raw video ID.

    Supported formats:
    - https://www.youtube.com/watch?v=dQw4w9WgXcQ
    - https://youtu.be/dQw4w9WgXcQ
    - https://www.youtube.com/shorts/dQw4w9WgXcQ
    - https://www.youtube.com/embed/dQw4w9WgXcQ
    - https://www.youtube.com/live/dQw4w9WgXcQ
    - https://www.youtube.com/v/dQw4w9WgXcQ
    - dQw4w9WgXcQ (raw 11-char ID)

    Returns:
        11-character video ID if found and valid, otherwise None.
    """
    if not url_or_id:
        return None

    cleaned = url_or_id.strip()

    # Exact 11-character video ID match
    if YOUTUBE_ID_EXACT.match(cleaned):
        return cleaned

    # Add protocol if missing to allow standard urlparse
    url_to_parse = cleaned
    if not cleaned.startswith(("http://", "https://")):
        url_to_parse = f"https://{cleaned}"

    try:
        parsed = urlparse(url_to_parse)
        hostname = (parsed.hostname or "").lower()

        # Handle youtu.be/VIDEO_ID
        if hostname in ("youtu.be", "www.youtu.be"):
            path_parts = [p for p in parsed.path.split("/") if p]
            if path_parts and YOUTUBE_ID_EXACT.match(path_parts[0]):
                return path_parts[0]

        # Handle youtube.com (and subdomains like m.youtube.com, music.youtube.com)
        if "youtube.com" in hostname:
            # Query param ?v=VIDEO_ID
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                candidate = qs["v"][0]
                if YOUTUBE_ID_EXACT.match(candidate):
                    return candidate

            # Paths like /embed/VIDEO_ID, /shorts/VIDEO_ID, /live/VIDEO_ID, /v/VIDEO_ID
            path_parts = [p for p in parsed.path.split("/") if p]
            if len(path_parts) >= 2 and path_parts[0] in ("embed", "shorts", "live", "v"):
                if YOUTUBE_ID_EXACT.match(path_parts[1]):
                    return path_parts[1]
    except Exception:
        pass

    return None


def format_timestamp(seconds: float) -> str:
    """
    Convert a duration/timestamp in seconds to HH:MM:SS or MM:SS format.

    Examples:
        45.2 -> '00:45'
        165.0 -> '02:45'
        3665.0 -> '01:01:05'
    """
    total_seconds = int(max(0, seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
