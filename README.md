# Music Downloader

A simple Python-based music downloader powered by `yt-dlp` and `FFmpeg`.

It allows you to:

- Download a single song
- Download multiple songs in parallel
- Search music automatically from YouTube and SoundCloud
- Download using a song name or direct URL
- Save a default download folder
- Automatically detect browser cookies for better download success

---

# Features

- Automatic dependency installation (`yt-dlp` and `FFmpeg`)
- Windows and Linux support
- Multi-threaded downloads
- Automatic metadata and thumbnail embedding
- Supports:
  - YouTube
  - SoundCloud
- Interactive terminal menu

---

# Requirements

- Python 3.10 or newer
- Internet connection

---

# Installation Guide

## 1. Install Python

### Windows

Download Python from:

https://www.python.org/downloads/windows/

IMPORTANT:
During installation, enable:

```text
Add Python to PATH
```

Verify installation:

```bash
python --version
```

---

### Linux

Most Linux distributions already include Python.

Verify:

```bash
python3 --version
```

If Python is missing:

#### Ubuntu / Debian

```bash
sudo apt update
sudo apt install python3 python3-pip -y
```

#### Arch Linux

```bash
sudo pacman -S python python-pip
```

#### Fedora

```bash
sudo dnf install python3 python3-pip
```

---

# Download the Script

Save the script as:

```text
music_downloader.py
```

Or clone/download your repository.

---

# Install Dependencies

The script automatically tries to install:

- yt-dlp
- FFmpeg

However, you can install them manually if needed.

---

## Windows Manual Dependency Installation

### Install yt-dlp

Using Winget:

```bash
winget install yt-dlp.yt-dlp
```

Or using Chocolatey:

```bash
choco install yt-dlp -y
```

---

### Install FFmpeg

Using Winget:

```bash
winget install Gyan.FFmpeg
```

Or Chocolatey:

```bash
choco install ffmpeg -y
```

---

## Linux Manual Dependency Installation

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install yt-dlp ffmpeg -y
```

### Arch Linux

```bash
sudo pacman -S yt-dlp ffmpeg
```

### Fedora

```bash
sudo dnf install yt-dlp ffmpeg -y
```

---

# How to Run

## Windows

Open CMD or PowerShell in the script folder:

```bash
python music_downloader.py
```

---

## Linux

Open terminal in the script folder:

```bash
python3 music_downloader.py
```

---

# How to Use

When the program starts, you will see:

```text
1. Download one song
2. Download multiple songs
3. Set default music path
4. Exit
```

---

## Download One Song

Choose:

```text
1
```

Then enter:

- A song name

Example:

```text
Daft Punk - One More Time
```

OR a direct URL:

```text
https://www.youtube.com/watch?v=example
```

Then choose the download folder.

---

## Download Multiple Songs

Choose:

```text
2
```

Enter one song per line:

```text
Song 1
Song 2
Song 3
```

Type:

```text
0
```

when finished.

Downloads will run in parallel automatically.

---

## Set Default Download Folder

Choose:

```text
3
```

Then enter your preferred music folder path.

The configuration is saved in:

```text
musicex_config.json
```

---

# Output Formats

The downloader automatically tries:

1. M4A
2. MP4 audio
3. MP3 (192K)

Metadata and thumbnails are embedded automatically.

---

# Notes

- Some downloads may require browser cookies
- The script automatically detects:
  - Firefox
  - Chrome
  - Chromium
  - Brave
  - Edge

---

# Troubleshooting

## yt-dlp Not Found

Install manually:

```bash
pip install -U yt-dlp
```

---

## FFmpeg Not Found

Install FFmpeg manually using your package manager.

---

## Downloads Fail

Try:

```bash
yt-dlp -U
```

Or test with a different song/source.

---

# Example

```bash
python music_downloader.py
```

```text
Music Downloader
1. Download one song
2. Download multiple songs
3. Set default music path
4. Exit
```

---

# License

Personal use project.

