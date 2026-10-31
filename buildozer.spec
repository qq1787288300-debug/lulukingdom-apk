[app]
title = LuLuKingdom
package.name = lulukingdom
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0

requirements = python3,kivy==2.3.0,websocket-client

orientation = portrait
fullscreen = 0

android.archs = arm64-v8a,armeabi-v7a
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 34
android.ndk_api = 24
android.minapi = 24
android.accept_sdk_license = True


[buildozer]
log_level = 2
warn_on_root = 1
