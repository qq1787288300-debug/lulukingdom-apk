[app]
title = LuLuKingdom
package.name = lulukingdom
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 1.0

requirements = python3,kivy==2.3.1,websocket-client

orientation = portrait
fullscreen = 0

android.archs = arm64-v8a
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 34
android.ndk_api = 24
android.minapi = 24
android.accept_sdk_license = True

# 使用官方 develop 分支的 python-for-android（新版通过 pip --platform 安装安卓 wheel，兼容新 pip）
p4a.url = https://github.com/kivy/python-for-android.git
p4a.branch = develop


[buildozer]
log_level = 2
warn_on_root = 1
