from pathlib import Path

from mutagen import File
from mutagen.mp3 import MP3


def _read_tag(audio, key):
    """从 mutagen 返回的标签里读取文本值。"""
    value = audio.tags.get(key) if audio is not None and audio.tags else None
    if not value:
        return ""
    return str(value[0]) if isinstance(value, list) else str(value)


def read_mp3_info(file_path):
    """读取 MP3 文件信息，返回可以保存到数据库的字典。"""
    path = Path(file_path)
    if path.suffix.lower() != ".mp3":
        return None

    audio = File(path, easy=True)
    duration = read_mp3_duration(path)
    title = _read_tag(audio, "title") or path.stem
    artist = _read_tag(audio, "artist") or "未知歌手"
    album = _read_tag(audio, "album") or "未知专辑"

    return {
        "title": title,
        "artist": artist,
        "album": album,
        "duration": duration,
        "file_path": str(path.resolve()),
    }


def read_mp3_duration(file_path):
    """只读取 MP3 实际时长，单位是秒。"""
    try:
        audio = File(file_path, easy=True)
        if audio is not None and audio.info and audio.info.length:
            return int(audio.info.length)
    except Exception:
        pass

    audio = MP3(file_path)
    if audio is not None and audio.info and audio.info.length:
        return int(audio.info.length)
    return 0


def read_many_mp3_infos(file_paths):
    """批量读取 MP3 信息，自动跳过非 MP3 或无法读取的文件。"""
    songs = []
    errors = []

    for file_path in file_paths:
        try:
            song_info = read_mp3_info(file_path)
            if song_info:
                songs.append(song_info)
        except Exception as exc:
            errors.append(f"{file_path}: {exc}")

    return songs, errors
