from setuptools import setup

APP = ['Applecode.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': [
        'selenium',
        'webdriver_manager',
        'tkinter',
        'requests',
    ],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)