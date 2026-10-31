# -*- coding: utf-8 -*-
# Kivy 版本：撸撸王国-逃杀工具（可用 Buildozer 打包成 APK）
# 依赖: pip install kivy websocket-client
import json
import ssl
import threading
import time

import websocket
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window

Window.softinput_mode = "below_target"


class MainLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=10, spacing=8, **kwargs)
        self.running = False
        self.threads = []
        self.sockets = []

        # ---- 参数区 ----
        grid = GridLayout(cols=2, size_hint_y=None, spacing=5)
        grid.bind(minimum_height=grid.setter("height"))

        grid.add_widget(Label(text="gopher_id:", size_hint_y=None, height=40))
        self.gopher_entry = TextInput(text="57", multiline=False,
                                      size_hint_y=None, height=40)
        grid.add_widget(self.gopher_entry)

        grid.add_widget(Label(text="silver_amount:", size_hint_y=None, height=40))
        self.silver_entry = TextInput(text="1.0", multiline=False,
                                      size_hint_y=None, height=40)
        grid.add_widget(self.silver_entry)

        grid.add_widget(Label(text="每账号并发线程数:", size_hint_y=None, height=40))
        self.thread_entry = TextInput(text="5", multiline=False,
                                      size_hint_y=None, height=40)
        grid.add_widget(self.thread_entry)

        sv = ScrollView(size_hint=(1, 0.35))
        sv.add_widget(grid)
        self.add_widget(sv)

        # ---- WS_URLS 列表区 ----
        self.add_widget(Label(text="WS_URLS（每行一个账号）", size_hint_y=None, height=30))
        self.urls_text = TextInput(
            text="\n".join([
                "wss://boom-ljj.lululu.com.cn/ws?token=6b2167df9d73a9af842703ea335e271f&userid=62238431",
                "wss://boom-ljj.lululu.com.cn/ws?token=b4e53efe7d8bceb7d862316324648e13&userid=15384828",
            ]),
            size_hint_y=None, height=150,
        )
        self.add_widget(self.urls_text)

        # ---- 按钮 ----
        btn_frame = BoxLayout(size_hint_y=None, height=50, spacing=10)
        self.start_btn = Button(text="开始")
        self.start_btn.bind(on_press=lambda *_: self.start())
        self.stop_btn = Button(text="停止", disabled=True)
        self.stop_btn.bind(on_press=lambda *_: self.stop())
        btn_frame.add_widget(self.start_btn)
        btn_frame.add_widget(self.stop_btn)
        self.add_widget(btn_frame)

        # ---- 日志区 ----
        self.text = TextInput(readonly=True, font_size=13)
        self.add_widget(self.text)

    def log(self, msg):
        # 线程安全：调度到主线程更新 UI
        Clock.schedule_once(lambda *_: self._append_log(f"{msg}\n"), 0)

    def _append_log(self, line):
        self.text.text += line
        self.text.cursor = (0, len(self.text.text) or 0)

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
        Window.title = "撸撸王国-逃杀工具"
        return MainLayout()


if __name__ == "__main__":
    MyApp().run()
