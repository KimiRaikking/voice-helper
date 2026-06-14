"""Cross-platform status tray/menu-bar indicator.

Exposes create_tray(get_display, on_copy_last) -> object with a blocking .run().

  get_display() -> (icon_key, status_text, last_text)
      icon_key in: idle | rec | proc | done | err

macOS uses rumps (menu-bar emoji); Windows/Linux use pystray (colored tray icon).
Both are imported lazily so importing this module never fails on the wrong platform.
"""
import os
import threading
import time

from vplatform import IS_MAC

# Emoji used as the macOS menu-bar title per state.
ICON_EMOJI = {"idle": "🎤", "rec": "🔴", "proc": "⏳", "done": "✅", "err": "⚠️"}
# RGBA fill colors for the pystray tray circle per state.
ICON_COLORS = {
    "idle": (110, 168, 254, 255), "rec": (248, 80, 80, 255),
    "proc": (240, 200, 60, 255), "done": (80, 200, 120, 255),
    "err": (240, 120, 60, 255),
}
REFRESH_SECONDS = 0.15


def _make_rumps_tray(get_display, on_copy_last):
    import rumps

    class _RumpsTray(rumps.App):
        def __init__(self):
            super().__init__(ICON_EMOJI["idle"], quit_button="退出语音输入")
            self.status_item = rumps.MenuItem("状态: 准备中…")
            self.last_item = rumps.MenuItem("最近识别: (无)", callback=self._copy)
            self.menu = [self.status_item, self.last_item, None]
            rumps.Timer(self._refresh, REFRESH_SECONDS).start()

        def _copy(self, _):
            on_copy_last()

        def _refresh(self, _):
            key, status, last = get_display()
            self.title = ICON_EMOJI.get(key, ICON_EMOJI["idle"])
            self.status_item.title = status
            if last:
                short = last if len(last) <= 40 else last[:40] + "…"
                self.last_item.title = f"最近识别: {short}（点击复制）"

    return _RumpsTray()


def _make_pystray_tray(get_display, on_copy_last):
    import pystray
    from PIL import Image, ImageDraw

    def circle(color):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse([10, 10, 54, 54], fill=color)
        return img

    images = {k: circle(c) for k, c in ICON_COLORS.items()}

    class _PystrayTray:
        def __init__(self):
            menu = pystray.Menu(
                pystray.MenuItem(lambda item: get_display()[1], None, enabled=False),
                pystray.MenuItem("复制最近识别", lambda icon, item: on_copy_last()),
                pystray.MenuItem("退出语音输入", self._quit),
            )
            self.icon = pystray.Icon("voice", images["idle"], "语音输入", menu)

        def _quit(self, icon, item):
            icon.stop()
            os._exit(0)

        def _poller(self):
            last_key = None
            while True:
                key, status, last = get_display()
                try:
                    if key != last_key:
                        self.icon.icon = images.get(key, images["idle"])
                        last_key = key
                    self.icon.title = status + (f" | {last[:30]}" if last else "")
                    self.icon.update_menu()
                except Exception:
                    pass
                time.sleep(REFRESH_SECONDS)

        def run(self):
            threading.Thread(target=self._poller, daemon=True).start()
            self.icon.run()

    return _PystrayTray()


def create_tray(get_display, on_copy_last):
    if IS_MAC:
        return _make_rumps_tray(get_display, on_copy_last)
    return _make_pystray_tray(get_display, on_copy_last)
