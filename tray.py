"""Cross-platform status tray/menu-bar indicator.

  create_tray(get_display, on_copy_last, on_switch_engine, current_engine) -> .run()

  get_display() -> (icon_key, status_text, last_text)   icon_key: idle|rec|proc|done|err
  on_copy_last()            copy last transcription
  on_switch_engine(name)    switch engine in place (whisper|sensevoice|paraformer)
  current_engine() -> name  currently active engine

macOS uses rumps (menu-bar emoji); Windows/Linux use pystray with the same emoji
rendered into the tray icon (Segoe UI Emoji), falling back to a colored dot.
Imports are lazy so this module never fails on the wrong platform.
"""
import os
import threading
import time

from vplatform import IS_MAC

ICON_EMOJI = {"idle": "🎤", "rec": "🔴", "proc": "⏳", "done": "✅", "err": "⚠️"}
ICON_COLORS = {
    "idle": (110, 168, 254, 255), "rec": (248, 80, 80, 255),
    "proc": (240, 200, 60, 255), "done": (80, 200, 120, 255),
    "err": (240, 120, 60, 255),
}
ENGINE_LABELS = {"whisper": "Whisper", "sensevoice": "SenseVoice", "paraformer": "Paraformer"}
REFRESH_SECONDS = 0.15


def _make_rumps_tray(get_display, on_copy_last, on_switch_engine, current_engine):
    import rumps

    class _RumpsTray(rumps.App):
        def __init__(self):
            super().__init__(ICON_EMOJI["idle"], quit_button="退出语音输入")
            self.status_item = rumps.MenuItem("状态: 准备中…")
            self.last_item = rumps.MenuItem("最近识别: (无)", callback=self._copy)
            self.eng_items = {}
            sub = []
            for key, label in ENGINE_LABELS.items():
                mi = rumps.MenuItem(label, callback=lambda s, k=key: on_switch_engine(k))
                self.eng_items[key] = mi
                sub.append(mi)
            self.menu = [self.status_item, self.last_item, None, ("切换引擎", sub), None]
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
            cur = current_engine()
            for k, mi in self.eng_items.items():
                mi.state = 1 if k == cur else 0

    return _RumpsTray()


def _make_pystray_tray(get_display, on_copy_last, on_switch_engine, current_engine):
    import pystray
    from PIL import Image, ImageDraw

    def _circle(color):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse([10, 10, 54, 54], fill=color)
        return img

    def _emoji(ch, key):
        # render the actual color emoji glyph so Windows looks like macOS
        try:
            from PIL import ImageFont
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            font = ImageFont.truetype("seguiemj.ttf", 48)  # Segoe UI Emoji (Windows)
            d.text((32, 34), ch, font=font, anchor="mm", embedded_color=True)
            if img.getbbox():  # non-empty -> rendered ok
                return img
        except Exception:
            pass
        return _circle(ICON_COLORS[key])

    images = {}
    for k in ICON_EMOJI:
        try:
            images[k] = _emoji(ICON_EMOJI[k], k)
        except Exception:
            images[k] = _circle(ICON_COLORS[k])

    class _PystrayTray:
        def __init__(self):
            self.icon = pystray.Icon("voice", images["idle"], "语音输入", self._menu())

        def _menu(self):
            # Flat menu (no submenu / no checked= — both upset older pystray on
            # Windows). Active engine shown via ●/○ in dynamic item text.
            try:
                items = [pystray.MenuItem(lambda item: get_display()[1], None, enabled=False)]
                for key, label in ENGINE_LABELS.items():
                    items.append(pystray.MenuItem(
                        (lambda item, kk=key, lb=label:
                            ("● " if current_engine() == kk else "○ ") + lb),
                        (lambda icon, item, kk=key: on_switch_engine(kk))))
                items.append(pystray.MenuItem("复制最近识别", lambda icon, item: on_copy_last()))
                items.append(pystray.MenuItem("退出语音输入", self._quit))
                return pystray.Menu(*items)
            except Exception:
                return pystray.Menu(pystray.MenuItem("退出语音输入", self._quit))

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


def create_tray(get_display, on_copy_last, on_switch_engine, current_engine):
    args = (get_display, on_copy_last, on_switch_engine, current_engine)
    return _make_rumps_tray(*args) if IS_MAC else _make_pystray_tray(*args)
