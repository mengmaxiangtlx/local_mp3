import ctypes
import random
import re
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QSettings, QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import database
from importer import read_many_mp3_infos, read_mp3_duration, read_mp3_info
from player import MusicPlayer
from taskbar_toolbar import WindowsTaskbarToolbar


ALL_SONGS_ID = 0
BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = BASE_DIR / "settings.ini"
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'

WM_NCHITTEST = 0x0084
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17


class NativeMessage(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_ssize_t),
        ("time", ctypes.c_uint),
        ("pt", ctypes.c_long * 2),
    ]


class TitleBar(QFrame):
    """自绘标题栏，负责显示图标、歌曲标题、关闭按钮和窗口拖动。"""

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.drag_position = QPoint()
        self.setObjectName("titleBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 10, 8)
        layout.setSpacing(10)

        self.icon_label = QLabel("♪")
        self.icon_label.setObjectName("appIcon")
        self.title_label = QLabel("LocalMusic")
        self.title_label.setObjectName("titleSong")
        self.close_button = QPushButton("×")
        self.close_button.setObjectName("closeButton")
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.clicked.connect(self.window.close)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label, stretch=1)
        layout.addWidget(self.close_button)

    def set_song_title(self, text):
        self.title_label.setText(text or "LocalMusic")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.window.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()


class SongTableWidget(QTableWidget):
    """支持整行拖拽排序的歌曲表格。"""

    def __init__(self, parent_window):
        super().__init__(0, 4)
        self.parent_window = parent_window

    def dropEvent(self, event):
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            super().dropEvent(event)
            return

        source_row = selected_rows[0].row()
        target_index = self.indexAt(event.position().toPoint())
        target_row = target_index.row()
        if target_row < 0:
            target_row = self.rowCount() - 1

        self.parent_window.move_song_row(source_row, target_row)
        event.accept()


class SettingsDialog(QDialog):
    """设置窗口：调整字体大小、颜色和背景图片。"""

    def __init__(self, parent, settings):
        super().__init__(parent)
        self.setWindowTitle("界面设置")
        self.setMinimumWidth(430)
        self.settings = settings

        self.font_color = self.settings.value("appearance/font_color", "#f8fafc")
        self.title_color = self.settings.value("appearance/title_color", "#ffffff")
        self.background_image = self.settings.value("appearance/background_image", "")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.font_size_input = QSpinBox()
        self.font_size_input.setRange(10, 24)
        self.font_size_input.setValue(int(self.settings.value("appearance/font_size", 14)))
        form.addRow("字体大小", self.font_size_input)

        self.font_color_button = QPushButton(self.font_color)
        self.font_color_button.clicked.connect(self.choose_font_color)
        form.addRow("普通字体颜色", self.font_color_button)

        self.title_color_button = QPushButton(self.title_color)
        self.title_color_button.clicked.connect(self.choose_title_color)
        form.addRow("标题字体颜色", self.title_color_button)

        background_row = QHBoxLayout()
        self.background_label = QLabel(self._background_label_text())
        self.background_label.setWordWrap(True)
        choose_background_button = QPushButton("选择图片")
        choose_background_button.clicked.connect(self.choose_background_image)
        clear_background_button = QPushButton("清除")
        clear_background_button.clicked.connect(self.clear_background_image)
        background_row.addWidget(self.background_label, stretch=1)
        background_row.addWidget(choose_background_button)
        background_row.addWidget(clear_background_button)
        form.addRow("背景图片", background_row)

        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_color_button(self.font_color_button, self.font_color)
        self._update_color_button(self.title_color_button, self.title_color)

    def choose_font_color(self):
        color = QColorDialog.getColor(QColor(self.font_color), self, "选择普通字体颜色")
        if color.isValid():
            self.font_color = color.name()
            self._update_color_button(self.font_color_button, self.font_color)

    def choose_title_color(self):
        color = QColorDialog.getColor(QColor(self.title_color), self, "选择标题字体颜色")
        if color.isValid():
            self.title_color = color.name()
            self._update_color_button(self.title_color_button, self.title_color)

    def choose_background_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择背景图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp)",
        )
        if file_path:
            self.background_image = file_path
            self.background_label.setText(self._background_label_text())

    def clear_background_image(self):
        self.background_image = ""
        self.background_label.setText(self._background_label_text())

    def save_settings(self):
        self.settings.setValue("appearance/font_size", self.font_size_input.value())
        self.settings.setValue("appearance/font_color", self.font_color)
        self.settings.setValue("appearance/title_color", self.title_color)
        self.settings.setValue("appearance/background_image", self.background_image)
        self.settings.sync()

    def _background_label_text(self):
        return self.background_image if self.background_image else "未设置"

    def _update_color_button(self, button, color):
        button.setText(color)
        button.setStyleSheet(
            f"background: {color}; color: {self._readable_text_color(color)}; padding: 6px;"
        )

    def _readable_text_color(self, color):
        qcolor = QColor(color)
        brightness = (
            qcolor.red() * 299 + qcolor.green() * 587 + qcolor.blue() * 114
        ) / 1000
        return "#111827" if brightness > 150 else "#ffffff"


class MainWindow(QMainWindow):
    """LocalMusic 的无边框迷你播放器主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LocalMusic 本地音乐播放器")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(1040, 720)
        self.setMinimumSize(900, 620)

        self.settings = QSettings(str(SETTINGS_PATH), QSettings.Format.IniFormat)
        self.resize_border_width = 8
        self.restore_window_settings()
        self.player = MusicPlayer()
        self.player.set_navigation_handlers(self.play_previous_song, self.play_next_song)
        self.current_songs = []
        self.current_playlist_id = ALL_SONGS_ID
        self.current_song_index = -1
        self.is_dragging_progress = False
        self.is_loading_table = False
        self.is_playlist_collapsed = False
        self.taskbar_toolbar = WindowsTaskbarToolbar(self)

        self._build_ui()
        self._connect_player_signals()
        self._apply_style()
        self.refresh_playlists()
        self.refresh_song_metadata(silent=True)
        self.load_all_songs()

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(10, 10, 10, 10)

        self.window_frame = QFrame()
        self.window_frame.setObjectName("windowFrame")
        frame_layout = QVBoxLayout(self.window_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        self.title_bar = TitleBar(self)
        frame_layout.addWidget(self.title_bar)

        body = QWidget()
        body.setObjectName("body")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(18, 14, 18, 16)
        body_layout.setSpacing(14)
        frame_layout.addWidget(body, stretch=1)

        top_tools = QHBoxLayout()
        self.toggle_playlist_button = self._create_button("收纳歌单")
        self.toggle_playlist_button.clicked.connect(self.toggle_playlist_panel)
        self.settings_button = self._create_button("设置")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        top_tools.addWidget(self.toggle_playlist_button)
        top_tools.addWidget(self.settings_button)
        top_tools.addStretch()
        body_layout.addLayout(top_tools)

        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setObjectName("contentSplitter")
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.splitterMoved.connect(self.save_layout_settings)
        body_layout.addWidget(self.content_splitter, stretch=1)

        self.playlist_panel = QFrame()
        self.playlist_panel.setObjectName("sidePanel")
        playlist_layout = QVBoxLayout(self.playlist_panel)
        playlist_layout.setContentsMargins(12, 12, 12, 12)
        playlist_title = QLabel("歌单")
        playlist_title.setObjectName("sectionTitle")
        self.playlist_list = QListWidget()
        self.playlist_list.setObjectName("playlistList")
        self.playlist_list.itemClicked.connect(self.on_playlist_clicked)
        playlist_layout.addWidget(playlist_title)
        playlist_layout.addWidget(self.playlist_list)
        self.content_splitter.addWidget(self.playlist_panel)

        song_panel = QFrame()
        song_panel.setObjectName("mainPanel")
        song_layout = QVBoxLayout(song_panel)
        song_layout.setContentsMargins(12, 12, 12, 12)
        song_layout.setSpacing(10)

        song_header = QHBoxLayout()
        song_title = QLabel("歌曲列表")
        song_title.setObjectName("sectionTitle")
        self.song_count_label = QLabel("0 首歌曲")
        self.song_count_label.setObjectName("mutedLabel")
        song_header.addWidget(song_title)
        song_header.addStretch()
        song_header.addWidget(QLabel("排序"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("自定义顺序", "manual")
        self.sort_combo.addItem("导入时间", "created_at")
        self.sort_combo.addItem("歌名", "title")
        self.sort_combo.addItem("歌手", "artist")
        self.sort_combo.setCurrentIndex(1)
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        song_header.addWidget(self.sort_combo)
        song_header.addWidget(self.song_count_label)
        song_layout.addLayout(song_header)

        self.song_table = SongTableWidget(self)
        self.song_table.setObjectName("songTable")
        self.song_table.setHorizontalHeaderLabels(["歌名", "歌手", "专辑", "时长"])
        self.song_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.song_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.song_table.setDragEnabled(True)
        self.song_table.setAcceptDrops(True)
        self.song_table.setDragDropOverwriteMode(False)
        self.song_table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.song_table.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.song_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.song_table.setAlternatingRowColors(True)
        self.song_table.setShowGrid(False)
        self.song_table.verticalHeader().setVisible(False)
        self.song_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.song_table.horizontalHeader().sectionResized.connect(self.save_layout_settings)
        self.song_table.cellDoubleClicked.connect(self.on_song_cell_double_clicked)
        self.song_table.itemChanged.connect(self.on_song_item_changed)
        self.song_table.customContextMenuRequested.connect(self.show_song_context_menu)
        song_layout.addWidget(self.song_table)
        self.content_splitter.addWidget(song_panel)

        self.mini_panel = QFrame()
        self.mini_panel.setObjectName("miniPlayer")
        mini_layout = QVBoxLayout(self.mini_panel)
        mini_layout.setContentsMargins(18, 18, 18, 18)
        mini_layout.setSpacing(12)

        self.album_cover = QLabel("♪")
        self.album_cover.setObjectName("albumCover")
        self.album_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.album_cover.setFixedSize(220, 220)
        mini_layout.addWidget(self.album_cover, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.now_playing_label = QLabel("当前播放：无")
        self.now_playing_label.setObjectName("nowPlaying")
        self.now_playing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.now_playing_label.setWordWrap(True)
        mini_layout.addWidget(self.now_playing_label)

        progress_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setObjectName("timeLabel")
        self.duration_label = QLabel("00:00")
        self.duration_label.setObjectName("timeLabel")
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setObjectName("progressSlider")
        self.progress_slider.setRange(0, 0)
        self.progress_slider.sliderPressed.connect(self.on_progress_pressed)
        self.progress_slider.sliderMoved.connect(self.on_progress_moved)
        self.progress_slider.sliderReleased.connect(self.on_progress_released)
        progress_layout.addWidget(self.current_time_label)
        progress_layout.addWidget(self.progress_slider, stretch=1)
        progress_layout.addWidget(self.duration_label)
        mini_layout.addLayout(progress_layout)

        mini_controls = QHBoxLayout()
        mini_controls.setSpacing(14)
        self.prev_button = self._create_player_button("上一首")
        self.play_pause_button = self._create_player_button("播放")
        self.next_button = self._create_player_button("下一首")
        self.prev_button.clicked.connect(self.play_previous_song)
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.next_button.clicked.connect(self.play_next_song)
        mini_controls.addStretch()
        mini_controls.addWidget(self.prev_button)
        mini_controls.addWidget(self.play_pause_button)
        mini_controls.addWidget(self.next_button)
        mini_controls.addStretch()
        mini_layout.addLayout(mini_controls)

        extra_tools = QHBoxLayout()
        self.import_button = self._create_button("导入")
        self.refresh_info_button = self._create_button("刷新")
        self.new_playlist_button = self._create_button("新建歌单")
        self.add_to_playlist_button = self._create_button("加入歌单")
        self.remove_from_playlist_button = self._create_button("移除")
        self.delete_song_button = self._create_button("删除", "danger")
        self.import_button.clicked.connect(self.import_songs)
        self.refresh_info_button.clicked.connect(self.refresh_song_metadata)
        self.new_playlist_button.clicked.connect(self.create_playlist)
        self.add_to_playlist_button.clicked.connect(self.add_selected_song_to_playlist)
        self.remove_from_playlist_button.clicked.connect(self.remove_selected_song_from_playlist)
        self.delete_song_button.clicked.connect(self.delete_selected_song)
        for button in [
            self.import_button,
            self.refresh_info_button,
            self.new_playlist_button,
            self.add_to_playlist_button,
            self.remove_from_playlist_button,
            self.delete_song_button,
        ]:
            extra_tools.addWidget(button)
        mini_layout.addLayout(extra_tools)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("播放顺序"))
        self.play_mode_combo = QComboBox()
        self.play_mode_combo.addItem("顺序播放", "sequence")
        self.play_mode_combo.addItem("随机播放", "random")
        self.play_mode_combo.addItem("单曲循环", "repeat_one")
        mode_layout.addWidget(self.play_mode_combo)
        mode_layout.addWidget(QLabel("音量"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("volumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(self.player.set_volume)
        mode_layout.addWidget(self.volume_slider)
        mini_layout.addLayout(mode_layout)
        mini_layout.addStretch()

        self.content_splitter.addWidget(self.mini_panel)
        self.restore_layout_settings()

        root_layout.addWidget(self.window_frame)
        self.setCentralWidget(root)

    def _connect_player_signals(self):
        self.player.player.positionChanged.connect(self.on_player_position_changed)
        self.player.player.durationChanged.connect(self.on_player_duration_changed)
        self.player.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.player.playbackStateChanged.connect(self.on_playback_state_changed)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.taskbar_toolbar.initialize)

    def nativeEvent(self, event_type, message):
        resize_hit = self._resize_hit_test(message)
        if resize_hit:
            return True, resize_hit
        if self.taskbar_toolbar.handle_native_event(message):
            return True, 0
        return super().nativeEvent(event_type, message)

    def _resize_hit_test(self, message):
        if sys.platform != "win32":
            return None

        msg = NativeMessage.from_address(int(message))
        if msg.message != WM_NCHITTEST:
            return None

        x = ctypes.c_short(msg.lParam & 0xFFFF).value
        y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
        frame = self.frameGeometry()
        border = self.resize_border_width

        on_left = frame.left() <= x < frame.left() + border
        on_right = frame.right() - border < x <= frame.right()
        on_top = frame.top() <= y < frame.top() + border
        on_bottom = frame.bottom() - border < y <= frame.bottom()

        if on_top and on_left:
            return HTTOPLEFT
        if on_top and on_right:
            return HTTOPRIGHT
        if on_bottom and on_left:
            return HTBOTTOMLEFT
        if on_bottom and on_right:
            return HTBOTTOMRIGHT
        if on_left:
            return HTLEFT
        if on_right:
            return HTRIGHT
        if on_top:
            return HTTOP
        if on_bottom:
            return HTBOTTOM
        return None

    def _create_button(self, text, role="normal"):
        button = QPushButton(text)
        button.setProperty("role", role)
        button.setProperty("flash", False)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(34)
        button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        button.clicked.connect(lambda checked=False, target=button: self._flash_button(target))
        return button

    def _create_player_button(self, text):
        button = self._create_button(text, "player")
        button.setObjectName("playerButton")
        button.setFixedSize(76, 46)
        return button

    def _flash_button(self, button):
        button.setProperty("flash", True)
        self._refresh_widget_style(button)
        QTimer.singleShot(150, lambda: self._clear_button_flash(button))

    def _clear_button_flash(self, button):
        button.setProperty("flash", False)
        self._refresh_widget_style(button)

    def _refresh_widget_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _apply_style(self):
        font_size = int(self.settings.value("appearance/font_size", 14))
        font_color = self.settings.value("appearance/font_color", "#f8fafc")
        title_color = self.settings.value("appearance/title_color", "#ffffff")
        background_image = self.settings.value("appearance/background_image", "")
        frame_background = (
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 #0f172a, stop:0.58 #111827, stop:1 #1e293b);"
        )
        if background_image and Path(background_image).exists():
            image_path = background_image.replace("\\", "/")
            frame_background = f'border-image: url("{image_path}") 0 0 0 0 stretch stretch;'

        self.setStyleSheet(
            f"""
            QWidget#root {{
                background: transparent;
                color: {font_color};
                font-family: "Microsoft YaHei", "Segoe UI";
                font-size: {font_size}px;
            }}
            QFrame#windowFrame {{
                {frame_background}
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-radius: 18px;
            }}
            QFrame#titleBar {{
                background: rgba(2, 6, 23, 0.48);
                border-top-left-radius: 18px;
                border-top-right-radius: 18px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.12);
            }}
            QLabel#appIcon {{
                background: rgba(96, 165, 250, 0.25);
                color: #ffffff;
                border: 1px solid rgba(147, 197, 253, 0.52);
                border-radius: 13px;
                min-width: 26px;
                min-height: 26px;
                font-weight: 900;
            }}
            QLabel#titleSong {{
                color: {title_color};
                font-size: {font_size + 1}px;
                font-weight: 800;
                background: transparent;
            }}
            QPushButton#closeButton {{
                background: rgba(255, 255, 255, 0.10);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 12px;
                min-width: 28px;
                min-height: 28px;
                font-size: 18px;
                font-weight: 800;
                padding: 0;
            }}
            QPushButton#closeButton:hover {{
                background: #ef4444;
                border-color: #fca5a5;
            }}
            QWidget#body {{
                background: transparent;
            }}
            QLabel {{
                color: {font_color};
                background: transparent;
            }}
            QLabel#sectionTitle {{
                color: {title_color};
                font-size: {font_size + 2}px;
                font-weight: 800;
            }}
            QLabel#mutedLabel, QLabel#timeLabel {{
                color: rgba(248, 250, 252, 0.78);
                font-weight: 600;
            }}
            QFrame#sidePanel, QFrame#mainPanel, QFrame#miniPlayer {{
                background: rgba(15, 23, 42, 0.44);
                border: 1px solid rgba(255, 255, 255, 0.20);
                border-radius: 14px;
            }}
            QSplitter#contentSplitter {{
                background: transparent;
            }}
            QSplitter#contentSplitter::handle {{
                background: rgba(255, 255, 255, 0.16);
                border-radius: 3px;
                margin: 6px 2px;
            }}
            QSplitter#contentSplitter::handle:hover {{
                background: rgba(96, 165, 250, 0.70);
            }}
            QLabel#albumCover {{
                background: rgba(255, 255, 255, 0.10);
                color: rgba(255, 255, 255, 0.92);
                border: 1px solid rgba(255, 255, 255, 0.20);
                border-radius: 18px;
                font-size: 74px;
                font-weight: 900;
            }}
            QLabel#nowPlaying {{
                color: {title_color};
                font-size: {font_size + 1}px;
                font-weight: 800;
                padding: 6px;
            }}
            QListWidget#playlistList, QTableWidget#songTable, QComboBox {{
                background: rgba(15, 23, 42, 0.34);
                border: 1px solid rgba(255, 255, 255, 0.20);
                border-radius: 8px;
                color: {font_color};
                outline: none;
                padding: 5px 8px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 22px;
            }}
            QComboBox QAbstractItemView {{
                background: #111827;
                color: #f8fafc;
                selection-background-color: #2563eb;
            }}
            QListWidget#playlistList::item {{
                min-height: 34px;
                padding: 7px 10px;
                border-radius: 6px;
                margin: 2px;
                color: {font_color};
            }}
            QListWidget#playlistList::item:hover {{
                background: rgba(96, 165, 250, 0.32);
                color: #ffffff;
            }}
            QListWidget#playlistList::item:selected {{
                background: rgba(37, 99, 235, 0.82);
                color: #ffffff;
            }}
            QTableWidget#songTable {{
                alternate-background-color: rgba(255, 255, 255, 0.06);
                selection-background-color: rgba(59, 130, 246, 0.62);
                selection-color: #ffffff;
            }}
            QHeaderView::section {{
                background: rgba(15, 23, 42, 0.70);
                color: {title_color};
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.18);
                padding: 8px;
                font-weight: 800;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                color: {font_color};
                font-weight: 600;
            }}
            QTableWidget::item:hover {{
                background: rgba(96, 165, 250, 0.24);
            }}
            QPushButton {{
                background: rgba(255, 255, 255, 0.13);
                border: 1px solid rgba(255, 255, 255, 0.24);
                border-radius: 9px;
                padding: 7px 12px;
                color: {font_color};
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: rgba(96, 165, 250, 0.34);
                border-color: rgba(147, 197, 253, 0.65);
            }}
            QPushButton:pressed {{
                background: rgba(37, 99, 235, 0.66);
                padding-top: 9px;
                padding-bottom: 5px;
            }}
            QPushButton[role="danger"] {{
                color: #ffffff;
                border-color: rgba(252, 165, 165, 0.74);
                background: rgba(185, 28, 28, 0.72);
            }}
            QPushButton[role="player"], QPushButton#playerButton {{
                background: rgba(37, 99, 235, 0.86);
                border-color: rgba(147, 197, 253, 0.82);
                color: #ffffff;
                border-radius: 23px;
                font-weight: 900;
            }}
            QPushButton[role="player"]:hover, QPushButton#playerButton:hover {{
                background: rgba(59, 130, 246, 0.96);
            }}
            QPushButton[flash="true"] {{
                background: rgba(34, 197, 94, 0.92);
                border-color: rgba(187, 247, 208, 0.92);
                color: #ffffff;
            }}
            QSlider#volumeSlider::groove:horizontal, QSlider#progressSlider::groove:horizontal {{
                height: 6px;
                background: rgba(255, 255, 255, 0.22);
                border-radius: 3px;
            }}
            QSlider#volumeSlider::handle:horizontal, QSlider#progressSlider::handle:horizontal {{
                background: #f8fafc;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider#volumeSlider::sub-page:horizontal, QSlider#progressSlider::sub-page:horizontal {{
                background: #60a5fa;
                border-radius: 3px;
            }}
            QMenu {{
                background: #111827;
                color: #f8fafc;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 7px 24px;
                border-radius: 5px;
            }}
            QMenu::item:selected {{
                background: #2563eb;
            }}
            """
        )

    def open_settings_dialog(self):
        dialog = SettingsDialog(self, self.settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.save_settings()
            self._apply_style()

    def restore_window_settings(self):
        width = self._setting_int("window/width", self.width())
        height = self._setting_int("window/height", self.height())
        self.resize(
            max(width, self.minimumWidth()),
            max(height, self.minimumHeight()),
        )

        x = self.settings.value("window/x")
        y = self.settings.value("window/y")
        if x is not None and y is not None:
            try:
                self.move(int(x), int(y))
            except (TypeError, ValueError):
                pass

    def save_window_settings(self):
        if self.isMinimized():
            return
        geometry = self.normalGeometry() if self.isMaximized() else self.geometry()
        self.settings.setValue("window/x", geometry.x())
        self.settings.setValue("window/y", geometry.y())
        self.settings.setValue("window/width", geometry.width())
        self.settings.setValue("window/height", geometry.height())
        self.settings.sync()

    def _setting_int(self, key, default):
        try:
            return int(self.settings.value(key, default))
        except (TypeError, ValueError):
            return default

    def restore_layout_settings(self):
        splitter_sizes = self.settings.value("layout/content_splitter_sizes")
        if splitter_sizes:
            sizes = [int(size) for size in str(splitter_sizes).split(",") if str(size).isdigit()]
            if len(sizes) == 3:
                self.content_splitter.setSizes(sizes)
            else:
                self.content_splitter.setSizes([190, 560, 270])
        else:
            self.content_splitter.setSizes([190, 560, 270])

        table_widths = self.settings.value("layout/song_table_column_widths")
        if table_widths:
            widths = [int(width) for width in str(table_widths).split(",") if str(width).isdigit()]
            for column, width in enumerate(widths[: self.song_table.columnCount()]):
                self.song_table.setColumnWidth(column, width)
        else:
            self.song_table.setColumnWidth(0, 240)
            self.song_table.setColumnWidth(1, 120)
            self.song_table.setColumnWidth(2, 150)
            self.song_table.setColumnWidth(3, 80)

    def save_layout_settings(self):
        if not hasattr(self, "content_splitter") or not hasattr(self, "song_table"):
            return
        splitter_sizes = ",".join(str(size) for size in self.content_splitter.sizes())
        table_widths = ",".join(
            str(self.song_table.columnWidth(column))
            for column in range(self.song_table.columnCount())
        )
        self.settings.setValue("layout/content_splitter_sizes", splitter_sizes)
        self.settings.setValue("layout/song_table_column_widths", table_widths)
        self.settings.sync()

    def closeEvent(self, event):
        self.save_layout_settings()
        self.save_window_settings()
        super().closeEvent(event)

    def toggle_playlist_panel(self):
        self.is_playlist_collapsed = not self.is_playlist_collapsed
        self.playlist_panel.setVisible(not self.is_playlist_collapsed)
        self.toggle_playlist_button.setText("展开歌单" if self.is_playlist_collapsed else "收纳歌单")

    def on_sort_changed(self):
        self.current_songs = self.sorted_songs(self.current_songs)
        self.show_songs(self.current_songs)

    def sorted_songs(self, songs):
        sort_key = self.sort_combo.currentData() if hasattr(self, "sort_combo") else "created_at"
        if sort_key == "manual":
            return list(songs)
        if sort_key == "title":
            return sorted(songs, key=lambda song: (song.get("title") or "").casefold())
        if sort_key == "artist":
            return sorted(songs, key=lambda song: ((song.get("artist") or ""), (song.get("title") or "")))
        return sorted(songs, key=lambda song: int(song.get("id") or 0), reverse=True)

    def refresh_song_metadata(self, silent=False):
        updated_count = 0
        skipped_count = 0
        for song in database.get_all_songs():
            file_path = Path(song["file_path"])
            if not file_path.exists():
                skipped_count += 1
                continue
            try:
                song_info = read_mp3_info(file_path)
            except Exception:
                skipped_count += 1
                continue
            if not song_info:
                skipped_count += 1
                continue
            title = song["title"]
            artist = self.keep_user_text(song["artist"], song_info["artist"], "未知歌手")
            album = self.keep_user_text(song["album"], song_info["album"], "未知专辑")
            duration = song_info["duration"] or int(song.get("duration") or 0)
            if self._song_record_changed(song, title, artist, album, duration):
                database.update_song_record(song["id"], title, artist, album, duration)
                updated_count += 1
        self.reload_current_song_view()
        if not silent:
            QMessageBox.information(self, "刷新完成", f"已更新 {updated_count} 首歌曲信息，跳过 {skipped_count} 个无法读取的文件。")

    def keep_user_text(self, current_value, tag_value, unknown_text):
        current = (current_value or "").strip()
        tag = (tag_value or "").strip()
        if current and current != unknown_text:
            return current
        return tag if tag and tag != unknown_text else current or unknown_text

    def _song_record_changed(self, song, title, artist, album, duration):
        return (
            song.get("title") != title
            or song.get("artist") != artist
            or song.get("album") != album
            or int(song.get("duration") or 0) != int(duration or 0)
        )

    def refresh_playlists(self):
        self.playlist_list.clear()
        all_item = QListWidgetItem("全部歌曲")
        all_item.setData(Qt.ItemDataRole.UserRole, ALL_SONGS_ID)
        self.playlist_list.addItem(all_item)
        for playlist in database.get_all_playlists():
            item = QListWidgetItem(playlist["name"])
            item.setData(Qt.ItemDataRole.UserRole, playlist["id"])
            self.playlist_list.addItem(item)
        self.playlist_list.setCurrentRow(0)

    def load_all_songs(self):
        self.current_playlist_id = ALL_SONGS_ID
        self.current_songs = self.sorted_songs(database.get_all_songs())
        self.show_songs(self.current_songs)

    def load_playlist_songs(self, playlist_id):
        self.current_playlist_id = playlist_id
        self.current_songs = self.sorted_songs(database.get_playlist_songs(playlist_id))
        self.show_songs(self.current_songs)

    def reload_current_song_view(self):
        if self.current_playlist_id == ALL_SONGS_ID:
            self.load_all_songs()
        else:
            self.load_playlist_songs(self.current_playlist_id)

    def show_songs(self, songs):
        self.is_loading_table = True
        self.song_table.setRowCount(len(songs))
        self.song_count_label.setText(f"{len(songs)} 首歌曲")
        for row, song in enumerate(songs):
            self.song_table.setItem(row, 0, self._table_item(song["title"], song["id"], True))
            self.song_table.setItem(row, 1, self._table_item(song["artist"], song["id"], True))
            self.song_table.setItem(row, 2, self._table_item(song["album"], song["id"], True))
            self.song_table.setItem(row, 3, self._table_item(self.format_duration(song["duration"]), song["id"], False))
        self.is_loading_table = False

    def _table_item(self, text, song_id, editable):
        item = QTableWidgetItem(str(text))
        item.setData(Qt.ItemDataRole.UserRole, song_id)
        flags = item.flags()
        item.setFlags(flags | Qt.ItemFlag.ItemIsEditable if editable else flags & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def on_song_item_changed(self, item):
        if self.is_loading_table or item.column() not in (0, 1, 2):
            return
        row = item.row()
        if row < 0 or row >= len(self.current_songs):
            return
        song = self.current_songs[row]
        new_value = item.text().strip()
        if not new_value:
            QMessageBox.warning(self, "提示", "内容不能为空。")
            self.reload_current_song_view()
            return
        if item.column() == 0:
            self.update_song_title_and_file(song, new_value)
        else:
            self.update_song_text_field(song, item.column(), new_value)

    def update_song_text_field(self, song, column, new_value):
        title = song["title"]
        artist = new_value if column == 1 else song["artist"]
        album = new_value if column == 2 else song["album"]
        duration = self.get_actual_duration(song["file_path"], song["duration"])
        database.update_song_record(song["id"], title, artist, album, duration)
        self.reload_current_song_view()

    def update_song_title_and_file(self, song, new_title):
        old_path = Path(song["file_path"])
        if not old_path.exists():
            QMessageBox.warning(self, "文件不存在", "找不到原 MP3 文件，无法重命名。")
            self.reload_current_song_view()
            return
        new_path = self.build_unique_song_path(old_path, new_title)
        if not new_path:
            QMessageBox.warning(self, "提示", "歌名不能作为有效文件名。")
            self.reload_current_song_view()
            return
        try:
            if self.player.current_song and self.player.current_song.get("id") == song["id"]:
                self.player.stop()
            if old_path.resolve() != new_path.resolve():
                old_path.rename(new_path)
        except OSError as exc:
            QMessageBox.warning(self, "重命名失败", f"无法修改 MP3 文件名：{exc}")
            self.reload_current_song_view()
            return
        duration = self.get_actual_duration(new_path, song["duration"])
        database.update_song_record(song["id"], new_title, song["artist"], song["album"], duration, str(new_path.resolve()))
        self.reload_current_song_view()

    def build_unique_song_path(self, old_path, title):
        safe_name = self.sanitize_filename(title)
        if not safe_name:
            return None
        target = old_path.with_name(f"{safe_name}{old_path.suffix}")
        if target.resolve() == old_path.resolve() or not target.exists():
            return target
        index = 2
        while True:
            candidate = old_path.with_name(f"{safe_name} ({index}){old_path.suffix}")
            if not candidate.exists():
                return candidate
            index += 1

    def sanitize_filename(self, text):
        safe = re.sub(INVALID_FILENAME_CHARS, "_", text).strip().rstrip(".")
        return safe[:120]

    def get_actual_duration(self, file_path, fallback_duration):
        try:
            return read_mp3_duration(file_path)
        except Exception:
            return int(fallback_duration or 0)

    def import_songs(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "选择 MP3 文件", "", "MP3 文件 (*.mp3)")
        if not file_paths:
            return
        songs, errors = read_many_mp3_infos(file_paths)
        added_count = 0
        for song_info in songs:
            song_id = database.add_song(song_info)
            if song_id:
                added_count += 1
        self.refresh_song_metadata(silent=True)
        self.load_all_songs()
        message = f"导入完成：新增 {added_count} 首歌曲。"
        if errors:
            message += f"\n有 {len(errors)} 个文件读取失败。"
        QMessageBox.information(self, "导入结果", message)

    def create_playlist(self):
        name, ok = QInputDialog.getText(self, "新建歌单", "请输入歌单名称：")
        if not ok:
            return
        if database.create_playlist(name):
            self.refresh_playlists()
        else:
            QMessageBox.warning(self, "提示", "歌单名称为空，或已经存在。")

    def on_playlist_clicked(self, item):
        playlist_id = item.data(Qt.ItemDataRole.UserRole)
        self.load_all_songs() if playlist_id == ALL_SONGS_ID else self.load_playlist_songs(playlist_id)

    def on_song_cell_double_clicked(self, row, column):
        self.play_song_at_row(row)

    def move_song_row(self, source_row, target_row):
        if source_row == target_row or source_row < 0 or source_row >= len(self.current_songs):
            return
        if target_row < 0 or target_row >= len(self.current_songs):
            return
        song = self.current_songs.pop(source_row)
        self.current_songs.insert(target_row, song)
        if self.current_song_index == source_row:
            self.current_song_index = target_row
        elif source_row < self.current_song_index <= target_row:
            self.current_song_index -= 1
        elif target_row <= self.current_song_index < source_row:
            self.current_song_index += 1
        self.sort_combo.blockSignals(True)
        self.sort_combo.setCurrentIndex(0)
        self.sort_combo.blockSignals(False)
        self.show_songs(self.current_songs)
        self.song_table.selectRow(target_row)

    def show_song_context_menu(self, position):
        row = self.song_table.rowAt(position.y())
        if row < 0 or row >= len(self.current_songs):
            return
        self.song_table.selectRow(row)
        song = self.current_songs[row]
        menu = QMenu(self)
        play_action = menu.addAction("播放")
        menu.addSeparator()
        rename_title_action = menu.addAction("修改歌名")
        edit_artist_action = menu.addAction("修改歌手")
        edit_album_action = menu.addAction("修改专辑")
        menu.addSeparator()
        delete_action = menu.addAction("删除记录")
        action = menu.exec(self.song_table.viewport().mapToGlobal(position))
        if action == play_action:
            self.play_song_at_row(row)
        elif action == rename_title_action:
            self.edit_song_title(song)
        elif action == edit_artist_action:
            self.edit_song_artist(song)
        elif action == edit_album_action:
            self.edit_song_album(song)
        elif action == delete_action:
            self.delete_song(song)

    def edit_song_title(self, song):
        new_title, ok = QInputDialog.getText(self, "修改歌名", "请输入新的歌名：", text=song["title"])
        if ok and new_title.strip():
            self.update_song_title_and_file(song, new_title.strip())

    def edit_song_artist(self, song):
        new_artist, ok = QInputDialog.getText(self, "修改歌手", "请输入新的歌手：", text=song["artist"])
        if ok and new_artist.strip():
            self.update_song_text_field(song, 1, new_artist.strip())

    def edit_song_album(self, song):
        new_album, ok = QInputDialog.getText(self, "修改专辑", "请输入新的专辑：", text=song["album"])
        if ok and new_album.strip():
            self.update_song_text_field(song, 2, new_album.strip())

    def play_song_at_row(self, row):
        if row < 0 or row >= len(self.current_songs):
            return
        song = self.current_songs[row]
        try:
            self.player.play_song(song)
        except FileNotFoundError as exc:
            QMessageBox.warning(self, "文件不存在", str(exc))
            return
        self.current_song_index = row
        display_title = f"{song['title']} - {song['artist']}"
        self.now_playing_label.setText(display_title)
        self.title_bar.set_song_title(display_title)
        self.play_pause_button.setText("暂停")
        self.taskbar_toolbar.update_play_pause(True)

    def toggle_play_pause(self):
        self.player.toggle_play_pause()
        state = self.player.player.playbackState()
        is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_pause_button.setText("暂停" if is_playing else "播放")
        self.taskbar_toolbar.update_play_pause(is_playing)

    def on_playback_state_changed(self, state):
        is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_pause_button.setText("暂停" if is_playing else "播放")
        self.taskbar_toolbar.update_play_pause(is_playing)

    def previous_song(self):
        self.play_previous_song()

    def next_song(self):
        self.play_next_song()

    def play_previous_song(self):
        if not self.current_songs:
            return
        if self.current_song_index <= 0:
            self.play_song_at_row(len(self.current_songs) - 1)
        else:
            self.play_song_at_row(self.current_song_index - 1)

    def play_next_song(self):
        next_index = self.get_next_song_index()
        if next_index is not None:
            self.play_song_at_row(next_index)

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_next_song()

    def get_next_song_index(self):
        if not self.current_songs:
            return None
        mode = self.play_mode_combo.currentData()
        if mode == "repeat_one" and self.current_song_index >= 0:
            return self.current_song_index
        if mode == "random":
            if len(self.current_songs) == 1:
                return 0
            choices = list(range(len(self.current_songs)))
            if 0 <= self.current_song_index < len(choices):
                choices.remove(self.current_song_index)
            return random.choice(choices)
        if self.current_song_index < 0:
            return 0
        next_index = self.current_song_index + 1
        return 0 if next_index >= len(self.current_songs) else next_index

    def on_player_position_changed(self, position):
        if self.is_dragging_progress:
            return
        self.progress_slider.setValue(position)
        self.current_time_label.setText(self.format_milliseconds(position))

    def on_player_duration_changed(self, duration):
        self.progress_slider.setRange(0, duration)
        self.duration_label.setText(self.format_milliseconds(duration))
        if duration == 0:
            self.current_time_label.setText("00:00")

    def on_progress_pressed(self):
        self.is_dragging_progress = True

    def on_progress_moved(self, position):
        self.current_time_label.setText(self.format_milliseconds(position))

    def on_progress_released(self):
        self.is_dragging_progress = False
        self.player.set_position(self.progress_slider.value())

    def add_selected_song_to_playlist(self):
        song = self.get_selected_song()
        if not song:
            QMessageBox.warning(self, "提示", "请先选择一首歌曲。")
            return
        playlists = database.get_all_playlists()
        if not playlists:
            QMessageBox.warning(self, "提示", "请先创建歌单。")
            return
        names = [playlist["name"] for playlist in playlists]
        name, ok = QInputDialog.getItem(self, "加入歌单", "选择歌单：", names, 0, False)
        if not ok:
            return
        playlist = next(item for item in playlists if item["name"] == name)
        database.add_song_to_playlist(playlist["id"], song["id"])
        QMessageBox.information(self, "完成", "歌曲已加入歌单。")

    def remove_selected_song_from_playlist(self):
        if self.current_playlist_id == ALL_SONGS_ID:
            QMessageBox.warning(self, "提示", "请先在左侧选择一个具体歌单。")
            return
        song = self.get_selected_song()
        if not song:
            QMessageBox.warning(self, "提示", "请先选择一首歌曲。")
            return
        database.remove_song_from_playlist(self.current_playlist_id, song["id"])
        self.load_playlist_songs(self.current_playlist_id)

    def delete_selected_song(self):
        song = self.get_selected_song()
        if not song:
            QMessageBox.warning(self, "提示", "请先选择一首歌曲。")
            return
        self.delete_song(song)

    def delete_song(self, song):
        reply = QMessageBox.question(self, "确认删除", "只删除软件里的歌曲记录，不会删除本地 MP3 文件。确定继续吗？")
        if reply != QMessageBox.StandardButton.Yes:
            return
        database.delete_song(song["id"])
        self.reload_current_song_view()

    def get_selected_song(self):
        selected_rows = self.song_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        if row < 0 or row >= len(self.current_songs):
            return None
        return self.current_songs[row]

    def format_duration(self, seconds):
        minutes = int(seconds or 0) // 60
        remain_seconds = int(seconds or 0) % 60
        return f"{minutes:02d}:{remain_seconds:02d}"

    def format_milliseconds(self, milliseconds):
        total_seconds = int(milliseconds) // 1000
        return self.format_duration(total_seconds)
