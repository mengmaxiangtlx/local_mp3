from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class MusicPlayer:
    """封装 QtMultimedia 播放逻辑。"""

    def __init__(self):
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(0.7)

        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)

        self.current_song = None
        self.previous_callback = None
        self.next_callback = None

    def set_navigation_handlers(self, previous_callback, next_callback):
        """设置上一首、下一首的回调函数。"""
        self.previous_callback = previous_callback
        self.next_callback = next_callback

    def play_song(self, song):
        """播放一首歌曲。"""
        file_path = Path(song["file_path"])
        if not file_path.exists():
            raise FileNotFoundError(f"找不到文件：{file_path}")

        self.current_song = song
        self.player.setSource(QUrl.fromLocalFile(str(file_path)))
        self.player.play()

    def toggle_play_pause(self):
        """播放和暂停之间切换。"""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def stop(self):
        """停止播放。"""
        self.player.stop()

    def previous_song(self):
        """播放上一首。具体列表逻辑由主窗口提供。"""
        if self.previous_callback:
            self.previous_callback()

    def next_song(self):
        """播放下一首。具体列表逻辑由主窗口提供。"""
        if self.next_callback:
            self.next_callback()

    def set_position(self, position):
        """跳转到指定播放位置。position 的单位是毫秒。"""
        self.player.setPosition(position)

    def get_position(self):
        """获取当前播放位置，单位是毫秒。"""
        return self.player.position()

    def get_duration(self):
        """获取当前歌曲总时长，单位是毫秒。"""
        return self.player.duration()

    def set_volume(self, value):
        """设置音量。value 是 0 到 100 的整数。"""
        self.audio_output.setVolume(value / 100)
