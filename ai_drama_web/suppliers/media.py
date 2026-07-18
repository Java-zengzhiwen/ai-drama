def image_bytes_match_media_type(data, media_type):
    normalized = str(media_type or "").split(";", 1)[0].strip().lower()
    if normalized == "image/png":
        return bytes(data).startswith(b"\x89PNG\r\n\x1a\n")
    if normalized == "image/jpeg":
        return bytes(data).startswith(b"\xff\xd8\xff")
    if normalized == "image/webp":
        value = bytes(data)
        return len(value) >= 12 and value[:4] == b"RIFF" and value[8:12] == b"WEBP"
    return False
