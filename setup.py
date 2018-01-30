
from setuptools import setup

setup(
    name="public-drive-urls",
    version='0.4.0',
    author="Brian Peterson",
    author_email="bepetersn@gmail.com",
    description="Find Google Drive download URLs from a file's sharing URL",
    license="MIT",
    url='https://github.com/bepetersn/public-drive-urls/',
    py_modules=['public_drive_urls'],
    classifiers=[
    ],
    install_requires=['requests'],
    extras_require={ 
        'test': ['nose', 'mock'],
        'dev': ['pip-tools']
    }
)
