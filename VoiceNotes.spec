# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

datas = [
    ('models', 'models'),
    ('samples', 'samples'),
]

# Collect metadata and data files for machine learning packages
datas += collect_data_files('faster_whisper')
datas += collect_data_files('onnxruntime')

binaries = []
binaries += collect_dynamic_libs('ctranslate2')
binaries += collect_dynamic_libs('onnxruntime')
binaries += collect_dynamic_libs('soundfile')

hiddenimports = [
    'faster_whisper',
    'ctranslate2',
    'onnxruntime',
    'soundfile',
    'sounddevice',
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VoiceNotes',
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
