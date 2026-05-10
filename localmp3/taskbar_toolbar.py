import ctypes
import os
import sys
import tempfile
import uuid
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap


BUTTON_PREVIOUS = 101
BUTTON_PLAY_PAUSE = 102
BUTTON_NEXT = 103

WM_COMMAND = 0x0111
THBN_CLICKED = 0x1800

THB_BITMAP = 0x1
THB_ICON = 0x2
THB_TOOLTIP = 0x4
THB_FLAGS = 0x8
THBF_ENABLED = 0x0

CLSCTX_INPROC_SERVER = 0x1
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x10


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def make_guid(value):
    guid = uuid.UUID(value)
    raw = guid.bytes_le
    data4 = (ctypes.c_ubyte * 8).from_buffer_copy(raw[8:])
    return GUID(
        int.from_bytes(raw[0:4], "little"),
        int.from_bytes(raw[4:6], "little"),
        int.from_bytes(raw[6:8], "little"),
        data4,
    )


class THUMBBUTTON(ctypes.Structure):
    _fields_ = [
        ("dwMask", wintypes.DWORD),
        ("iId", wintypes.UINT),
        ("iBitmap", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 260),
        ("dwFlags", wintypes.DWORD),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class WindowsTaskbarToolbar:
    """Windows 7+ taskbar thumbnail toolbar wrapper for ITaskbarList3."""

    def __init__(self, window):
        self.window = window
        self.hwnd = None
        self.taskbar = None
        self.icons = {}
        self.initialized = False

    def initialize(self):
        if sys.platform != "win32" or self.initialized:
            return

        self.hwnd = int(self.window.winId())
        if not self.hwnd:
            return

        ctypes.windll.ole32.CoInitialize(None)
        self.taskbar = self._create_taskbar_list3()
        if not self.taskbar:
            return

        self._call(3)  # HrInit
        self.icons = {
            "previous": self._create_icon("previous"),
            "play": self._create_icon("play"),
            "pause": self._create_icon("pause"),
            "next": self._create_icon("next"),
        }
        self._add_buttons(is_playing=False)
        self.initialized = True

    def handle_native_event(self, message):
        if sys.platform != "win32":
            return False

        msg = MSG.from_address(int(message))
        if msg.message != WM_COMMAND:
            return False

        command_id = msg.wParam & 0xFFFF
        notify_code = (msg.wParam >> 16) & 0xFFFF
        if notify_code != THBN_CLICKED:
            return False

        if command_id == BUTTON_PREVIOUS:
            self.window.player.previous_song()
            return True
        if command_id == BUTTON_PLAY_PAUSE:
            self.window.player.toggle_play_pause()
            return True
        if command_id == BUTTON_NEXT:
            self.window.player.next_song()
            return True
        return False

    def update_play_pause(self, is_playing):
        if not self.initialized:
            return
        self._update_buttons(is_playing)

    def _create_taskbar_list3(self):
        clsid = make_guid("{56FDF344-FD6D-11D0-958A-006097C9A090}")
        iid = make_guid("{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}")
        obj = ctypes.c_void_p()
        ole32 = ctypes.windll.ole32
        result = ole32.CoCreateInstance(
            ctypes.byref(clsid),
            None,
            CLSCTX_INPROC_SERVER,
            ctypes.byref(iid),
            ctypes.byref(obj),
        )
        if result != 0:
            return None
        return obj

    def _call(self, index, *args):
        vtable = ctypes.cast(self.taskbar, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        method = vtable[index]
        prototype = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *[type(arg) for arg in args])
        return prototype(method)(self.taskbar, *args)

    def _add_buttons(self, is_playing):
        buttons = self._make_buttons(is_playing)
        self._thumbbar_call(15, buttons)

    def _update_buttons(self, is_playing):
        buttons = self._make_buttons(is_playing)
        self._thumbbar_call(16, buttons)

    def _thumbbar_call(self, method_index, buttons):
        vtable = ctypes.cast(self.taskbar, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        method = vtable[method_index]
        prototype = ctypes.WINFUNCTYPE(
            ctypes.c_long,
            ctypes.c_void_p,
            wintypes.HWND,
            wintypes.UINT,
            ctypes.POINTER(THUMBBUTTON),
        )
        return prototype(method)(self.taskbar, self.hwnd, len(buttons), buttons)

    def _make_buttons(self, is_playing):
        buttons = (THUMBBUTTON * 3)()
        self._fill_button(buttons[0], BUTTON_PREVIOUS, self.icons["previous"], "上一首")
        self._fill_button(
            buttons[1],
            BUTTON_PLAY_PAUSE,
            self.icons["pause" if is_playing else "play"],
            "暂停" if is_playing else "播放",
        )
        self._fill_button(buttons[2], BUTTON_NEXT, self.icons["next"], "下一首")
        return buttons

    def _fill_button(self, button, button_id, icon, tip):
        button.dwMask = THB_ICON | THB_TOOLTIP | THB_FLAGS
        button.iId = button_id
        button.iBitmap = 0
        button.hIcon = icon
        button.szTip = tip
        button.dwFlags = THBF_ENABLED

    def _create_icon(self, kind):
        icon_dir = Path(tempfile.gettempdir()) / "localmusic_taskbar_icons"
        icon_dir.mkdir(exist_ok=True)
        icon_path = icon_dir / f"{kind}.ico"

        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#2563eb"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 30, 30)
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#ffffff"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))

        if kind == "play":
            painter.drawLine(13, 10, 13, 22)
            painter.drawLine(13, 22, 23, 16)
            painter.drawLine(23, 16, 13, 10)
            painter.setBrush(QColor("#ffffff"))
        elif kind == "pause":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(11, 9, 4, 14, 2, 2)
            painter.drawRoundedRect(18, 9, 4, 14, 2, 2)
        elif kind == "previous":
            painter.drawLine(20, 10, 12, 16)
            painter.drawLine(12, 16, 20, 22)
            painter.drawLine(10, 10, 10, 22)
        elif kind == "next":
            painter.drawLine(12, 10, 20, 16)
            painter.drawLine(20, 16, 12, 22)
            painter.drawLine(22, 10, 22, 22)

        painter.end()
        pixmap.save(str(icon_path), "ICO")

        hicon = ctypes.windll.user32.LoadImageW(
            None,
            os.fspath(icon_path),
            IMAGE_ICON,
            16,
            16,
            LR_LOADFROMFILE,
        )
        return hicon
