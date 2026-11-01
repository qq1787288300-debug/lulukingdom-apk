# -*- coding: utf-8 -*-
# Kivy 版本：撸撸王国-逃杀工具（深色主题美化版）
import json
import ssl
import threading
import time

import websocket
from kivy.clock import Clock
from kivy.app import App
from kivy.metrics import dp, sp
from kivy.utils import platform
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle

if platform == "android":
    Window.softinput_mode = "below_target"
else:
    Window.softinput_mode = "below_target"

# ---- 主题色 ----
BG = (0.09, 0.09, 0.12, 1)          # 页面背景
CARD = (0.14, 0.15, 0.20, 1)        # 卡片背景
INPUT_BG = (0.20, 0.21, 0.28, 1)    # 输入框
PRIMARY = (0.30, 0.55, 1.00, 1)     # 主按钮蓝
DANGER = (0.95, 0.35, 0.38, 1)      # 停止按钮红
DISABLED = (0.25, 0.26, 0.32, 1)
TEXT = (0.92, 0.93, 0.96, 1)
SUBTEXT = (0.55, 0.58, 0.66, 1)
LOG_BG = (0.07, 0.08, 0.10, 1)


class Card(BoxLayout):
    """圆角卡片容器"""
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(14),
                         spacing=dp(10), **kwargs)
        with self.canvas.before:
            Color(*CARD)
            self._bg = RoundedRectangle(radius=[dp(12)])
        self.bind(pos=self._update, size=self._update)

    def _update(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size


class ThemeLabel(Label):
    font_name = "CJK"

    def __init__(self, text="", size=None, color=TEXT, bold=False, **kw):
        super().__init__(text=text, color=color, bold=bold,
                         font_size=sp(14) if not bold else sp(15),
                         size_hint_y=None, height=size or dp(24), **kw)


class ThemeInput(TextInput):
    font_name = "CJK"

    def __init__(self, **kw):
        super().__init__(background_color=INPUT_BG,
                         foreground_color=TEXT,
                         cursor_color=PRIMARY,
                         selection_color=(0.3, 0.55, 1.0, 0.35),
                         font_size=sp(14), padding=[dp(10), dp(10)],
                         **kw)


class ThemeButton(Button):
    font_name = "CJK"

    def __init__(self, text, color, disabled_color=DISABLED, **kw):
        super().__init__(text=text, font_size=sp(15), bold=True,
                         background_normal="", background_down="",
                         background_color=color, color=(1, 1, 1, 1), **kw)
        with self.canvas.before:
            Color(*(color if not self.disabled else disabled_color))
            self._bg = RoundedRectangle(radius=[dp(10)])
        self.bind(pos=self._update, size=self._update, state=self._update)
        self.bind(disabled=lambda *_: self._recolor())

    def _recolor(self):
        self.canvas.before.clear()
        c = DISABLED if self.disabled else self.background_color
        with self.canvas.before:
            Color(*c)
            self._bg = RoundedRectangle(radius=[dp(10)])
        self._update()

    def _update(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size


class MainLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(14),
                         spacing=dp(12), **kwargs)
        self.running = False
        self.threads = []
        self.sockets = []

        # 页面背景
        with self.canvas.before:
            Color(*BG)
            self._page_bg = RoundedRectangle(radius=[0])
        self.bind(pos=self._page_update, size=self._page_update)

        # ---- 参数卡片 ----
        card = Card()
        card.add_widget(ThemeLabel("参数设置", bold=True))

        form = GridLayout(cols=2, size_hint_y=None, spacing=dp(8))
        form.bind(minimum_height=form.setter("height"))

        def add_row(label, entry):
            lb = ThemeLabel(label, color=SUBTEXT)
            lb.size_hint_x = 0.42
            form.add_widget(lb)
            form.add_widget(entry)

        self.gopher_entry = ThemeInput(text="57", multiline=False)
        self.silver_entry = ThemeInput(text="1.0", multiline=False)
        self.thread_entry = ThemeInput(text="5", multiline=False)
        add_row("gopher_id", self.gopher_entry)
        add_row("silver_amount", self.silver_entry)
        add_row("每账号并发", self.thread_entry)

        card.add_widget(form)
        self.add_widget(card)

        # ---- WS_URLS 卡片 ----
        card2 = Card()
        card2.add_widget(ThemeLabel("WS_URLS（每行一个账号）", bold=True))
        self.urls_text = TextInput(
            text="\n".join([
                "wss://boom-ljj.lululu.com.cn/ws?token=6b2167df9d73a9af842703ea335e271f&userid=62238431",
                "wss://boom-ljj.lululu.com.cn/ws?token=b4e53efe7d8bceb7d862316324648e13&userid=15384828",
            ]),
            background_color=INPUT_BG, foreground_color=TEXT,
            cursor_color=PRIMARY, font_size=sp(12), font_name="CJK",
            padding=[dp(10), dp(10)],
        )
        card2.add_widget(self.urls_text)
        self.add_widget(card2)

        # ---- 按钮 ----
        btn_frame = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        self.start_btn = ThemeButton("开 始", PRIMARY)
        self.start_btn.bind(on_press=lambda *_: self.start())
        self.stop_btn = ThemeButton("停 止", DANGER)
        self.stop_btn.disabled = True
        self.stop_btn.bind(on_press=lambda *_: self.stop())
        btn_frame.add_widget(self.start_btn)
        btn_frame.add_widget(self.stop_btn)
        self.add_widget(btn_frame)

        # ---- 日志卡片 ----
        card3 = Card(padding=dp(0), spacing=dp(0))
        header = ThemeLabel("  运行日志", bold=True, size=dp(40),
                            color=SUBTEXT)
        card3.add_widget(header)
        self.text = TextInput(readonly=True, font_size=sp(12),
                              background_color=LOG_BG, foreground_color=TEXT,
                              cursor_color=PRIMARY, font_name="CJK",
                              padding=[dp(10), dp(8)],
                              background_normal="")
        card3.add_widget(self.text)
        self.add_widget(card3)

    def _page_update(self, *_):
        self._page_bg.pos = self.pos
        self._page_bg.size = self.size

    def log(self, msg):
        Clock.schedule_once(lambda *_: self._append_log(f"{msg}\n"), 0)

    def _append_log(self, line):
        self.text.text += line
        self.text.scroll_y = 0

    def worker(self, thread_id, ws_url, t_text):
        headers = [
            "User-Agent: BestHTTP",
            "Cache-Control: no-cache",
            "Pragma: no-cache",
            "Accept-Encoding: gzip, identity",
        ]
        sslopt = {"cert_reqs": ssl.CERT_NONE}
        self.log(f"线程{thread_id} 连接中...")
        try:
            ws = websocket.create_connection(ws_url, header=headers, timeout=5, sslopt=sslopt)
        except Exception as e:
            if self.running:
                self.log(f"线程{thread_id} 连接失败: {e}")
            return
        self.sockets.append(ws)
        self.log(f"线程{thread_id} 已连接")
        while self.running:
            try:
                ws.send(t_text)
                time.sleep(0.1)
            except Exception as e:
                if not self.running:
                    break
                self.log(f"线程{thread_id} 发送失败，重连中: {e}")
                try:
                    ws.close()
                except Exception:
                    pass
                try:
                    ws = websocket.create_connection(ws_url, header=headers, timeout=5, sslopt=sslopt)
                    self.sockets.append(ws)
                    self.log(f"线程{thread_id} 重连成功")
                except Exception as e2:
                    self.log(f"线程{thread_id} 重连失败: {e2}")
                    return
        try:
            ws.close()
        except Exception:
            pass
        self.log(f"线程{thread_id} 已退出")

    def start(self):
        gopher = self.gopher_entry.text.strip()
        silver = self.silver_entry.text.strip()
        urls = [u.strip() for u in self.urls_text.text.splitlines() if u.strip()]
        try:
            thread_num = max(1, int(self.thread_entry.text.strip() or "1"))
        except ValueError:
            thread_num = 1
        if not gopher or not silver or not urls:
            self.log("请填写 gopher_id、silver_amount 和至少一个 WS_URL")
            return
        try:
            t_text = json.dumps({"e": "2002", "d": {
                "gopher_id": int(gopher),
                "silver_amount": float(silver),
                "item_id": 102201,
            }})
        except ValueError:
            self.log("gopher_id 需为整数，silver_amount 需为数字")
            return

        self.running = True
        self.start_btn.disabled = True
        self.stop_btn.disabled = False
        self.threads = []
        for idx, ws_url in enumerate(urls):
            for i in range(thread_num):
                th = threading.Thread(
                    target=self.worker,
                    args=(f"{idx}-{i}", ws_url, t_text),
                    daemon=True,
                )
                th.start()
                self.threads.append(th)
        self.log(f"已启动 {len(self.threads)} 个线程（{len(urls)} 个账号 x {thread_num} 并发）")

    def stop(self):
        self.running = False
        for ws in list(self.sockets):
            try:
                ws.close()
            except Exception:
                pass
        self.sockets = []
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        self.log("已停止")


class MyApp(App):
    def build(self):
        LabelBase.register(
            name="CJK",
            fn_regular="assets/NotoSansSC.ttf",
        )
        self.title = "撸撸王国-逃杀工具"
        return MainLayout()


if __name__ == "__main__":
    MyApp().run()
