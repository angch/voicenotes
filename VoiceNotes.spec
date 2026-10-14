# -*- mode: python ; coding: utf-8 -*-

import glob
import os
import sys
import sysconfig
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

site_packages = sysconfig.get_path('purelib')

datas = [
    ('models', 'models'),
    ('samples', 'samples'),
    ('assets', 'assets'),
]
if os.path.isdir('voicenotes/lib'):
    datas.append(('voicenotes/lib', 'voicenotes/lib'))

# Collect metadata and data files for machine learning packages
datas += collect_data_files('faster_whisper')
datas += collect_data_files('onnxruntime')
datas += collect_data_files('_sounddevice_data')
datas += collect_data_files('_soundfile_data')

binaries = []
binaries += collect_dynamic_libs('ctranslate2')
binaries += collect_dynamic_libs('onnxruntime')
binaries += collect_dynamic_libs('av')

if sys.platform == 'win32':
    # Collect all vendor DLLs from *.libs directories (av/FFmpeg, numpy, scipy, portaudio)
    for lib_dir in ['av.libs', 'numpy.libs', 'scipy.libs', '_sounddevice_data/portaudio-binaries', '_soundfile_data', 'sklearn/.libs']:
        target_dir = os.path.join(site_packages, *lib_dir.split('/'))
        if os.path.isdir(target_dir):
            for dll_file in glob.glob(os.path.join(target_dir, '*.dll')):
                bname = os.path.basename(dll_file).lower()
                if '32bit' in bname or 'arm64' in bname:
                    continue
                binaries.append((dll_file, '.'))

    for pkg in ('nvidia.cublas', 'nvidia.cudnn', 'nvidia.cuda_nvrtc'):
        try:
            binaries += collect_dynamic_libs(pkg)
        except Exception:
            pass
elif sys.platform == 'darwin':
    # Collect macOS vendor dylibs
    for lib_dir in ['_sounddevice_data/portaudio-binaries', '_soundfile_data', 'av/.dylibs', 'PIL/.dylibs', 'sklearn/.dylibs', 'ctranslate2/.dylibs', 'scipy/.dylibs']:
        target_dir = os.path.join(site_packages, *lib_dir.split('/'))
        if os.path.isdir(target_dir):
            for dylib_file in glob.glob(os.path.join(target_dir, '*.dylib')):
                binaries.append((dylib_file, '.'))
elif sys.platform.startswith('linux'):
    # Collect Linux runtime libraries (bundled portaudio, xcb-cursor)
    if os.path.isdir('voicenotes/lib'):
        for so_file in glob.glob('voicenotes/lib/*.so*'):
            binaries.append((so_file, '.'))

    for pkg in ('nvidia.cublas', 'nvidia.cudnn', 'nvidia.cuda_nvrtc'):
        try:
            binaries += collect_dynamic_libs(pkg)
        except Exception:
            pass

hiddenimports = [
    'voicenotes.compat',
    'av',
    'av.audio',
    'av.container',
    'av.subtitles',
    'PIL',
    'PIL.Image',
    'PIL.ImageOps',
    'faster_whisper',
    'ctranslate2',
    'onnxruntime',
    'soundfile',
    'sounddevice',
    '_soundfile_data',
    '_sounddevice_data',
    'scipy.signal',
    'scipy.special',
    'sklearn',
    'sklearn.cluster',
    'sklearn.cluster._agglomerative',
    'sklearn.metrics.pairwise',
    'PyQt6.QtMultimedia',
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'voicenotes',
    'voicenotes.app',
    'voicenotes.config',
    'voicenotes.engine',
    'voicenotes.engine.audio_utils',
    'voicenotes.engine.diarizer',
    'voicenotes.engine.model_manager',
    'voicenotes.engine.transcriber',
    'voicenotes.export',
    'voicenotes.export.exporters',
    'voicenotes.gui',
    'voicenotes.gui.audio_player',
    'voicenotes.gui.dialogs',
    'voicenotes.gui.main_window',
    'voicenotes.gui.styles',
    'voicenotes.gui.find_bar',
    'voicenotes.gui.speakers_panel',
    'voicenotes.gui.transcription_worker',
    'voicenotes.gui.vocabulary_panel',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'torch', 'IPython', 'notebook'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

app_icon = 'assets/app_icon.icns' if (sys.platform == 'darwin' and os.path.exists('assets/app_icon.icns')) else 'assets/app_icon.ico'

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VoiceNotes',
    icon=app_icon,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Windowed GUI application for end users
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='VoiceNotes',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='VoiceNotes.app',
        icon='assets/app_icon.icns' if os.path.exists('assets/app_icon.icns') else None,
        bundle_identifier='com.voicenotes.desktop',
        info_plist={
            'CFBundleName': 'VoiceNotes',
            'CFBundleDisplayName': 'VoiceNotes',
            'CFBundleGetInfoString': 'VoiceNotes - Offline Speech Transcriber with Speaker Diarization',
            'CFBundleIdentifier': 'com.voicenotes.desktop',
            'CFBundleVersion': '0.5.3',
            'CFBundleShortVersionString': '0.5.3',
            'NSHumanReadableCopyright': 'VoiceNotes Contributors',
            'NSMicrophoneUsageDescription': 'VoiceNotes requires microphone access for audio recording and live voice dictation.',
            'NSHighResolutionCapable': True,
        },
    )
