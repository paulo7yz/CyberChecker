[app]
title = CyberChecker
package.name = cyberchecker
package.domain = org.cyberchecker
source.dir = .
source.include_exts = py,png,jpg,kv,json,txt
requirements = python3,kivy==2.3.1,requests,urllib3,retry-requests

# (str) Presplash of the application
presplash.filename = %(source.dir)s/assets/icon.png

# (str) Icon of the application
icon.filename = %(source.dir)s/assets/icon.png

# (str) Supported orientation (landscape, portrait or all)
orientation = portrait

# android.permissions
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (int) Target Android API, should be as high as possible.
android.api = 31

# (bool) If True, then skip trying to update the Android sdk
# This can be useful to avoid excess Internet downloads or save time
# when an update is due and you just want to test/build your package
android.skip_update = True

# (int) Android SDK version to use
android.sdk = 31

# (str) Android NDK version to use
android.ndk = 23b

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
android.ndk_path =

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
android.sdk_path =

# (str) python-for-android branch to use, defaults to master
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
