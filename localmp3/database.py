import sqlite3
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "music.db"


def get_connection():
    """创建数据库连接。"""
    return sqlite3.connect(DB_PATH)


def init_db():
    """初始化数据库。"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                artist TEXT,
                album TEXT,
                duration INTEGER,
                file_path TEXT UNIQUE,
                created_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                created_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS playlist_songs (
                playlist_id INTEGER,
                song_id INTEGER,
                PRIMARY KEY (playlist_id, song_id),
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
            )
            """
        )


def add_song(song_info):
    """保存歌曲信息。如果文件已经导入过，就不重复插入。"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO songs
            (title, artist, album, duration, file_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                song_info["title"],
                song_info["artist"],
                song_info["album"],
                song_info["duration"],
                song_info["file_path"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        return cursor.lastrowid


def update_song_info(song_id, song_info):
    """更新已有歌曲的歌名、歌手、专辑和时长。"""
    return update_song_record(
        song_id,
        song_info["title"],
        song_info["artist"],
        song_info["album"],
        song_info["duration"],
        song_info.get("file_path"),
    )


def update_song_record(song_id, title, artist, album, duration, file_path=None):
    """更新歌曲记录。file_path 为空时不改文件路径。"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if file_path:
            cursor.execute(
                """
                UPDATE songs
                SET title = ?, artist = ?, album = ?, duration = ?, file_path = ?
                WHERE id = ?
                """,
                (title, artist, album, duration, file_path, song_id),
            )
        else:
            cursor.execute(
                """
                UPDATE songs
                SET title = ?, artist = ?, album = ?, duration = ?
                WHERE id = ?
                """,
                (title, artist, album, duration, song_id),
            )
        return cursor.rowcount > 0


def get_all_songs():
    """查询全部歌曲。"""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM songs ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_song(song_id):
    """根据歌曲 id 查询单首歌曲。"""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM songs WHERE id = ?", (song_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_playlist(name):
    """创建歌单。重名时不会重复创建。"""
    clean_name = name.strip()
    if not clean_name:
        return False

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO playlists (name, created_at)
            VALUES (?, ?)
            """,
            (clean_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        return cursor.rowcount > 0


def get_all_playlists():
    """查询所有歌单。"""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM playlists ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]


def add_song_to_playlist(playlist_id, song_id):
    """把歌曲加入歌单。已存在时忽略。"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO playlist_songs (playlist_id, song_id)
            VALUES (?, ?)
            """,
            (playlist_id, song_id),
        )
        return cursor.rowcount > 0


def remove_song_from_playlist(playlist_id, song_id):
    """从歌单中移除歌曲。"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM playlist_songs
            WHERE playlist_id = ? AND song_id = ?
            """,
            (playlist_id, song_id),
        )
        return cursor.rowcount > 0


def get_playlist_songs(playlist_id):
    """查询某个歌单里的歌曲。"""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT songs.*
            FROM songs
            INNER JOIN playlist_songs ON songs.id = playlist_songs.song_id
            WHERE playlist_songs.playlist_id = ?
            ORDER BY songs.title
            """,
            (playlist_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_song(song_id):
    """删除歌曲，同时清理它和歌单的关联。不会删除本地 MP3 文件。"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM playlist_songs WHERE song_id = ?", (song_id,))
        cursor.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        return cursor.rowcount > 0
