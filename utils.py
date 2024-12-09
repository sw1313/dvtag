"""This module provides a minimal implementation of some functions for transcoding `.wav` files to other formats using `ffmpeg`.

If users need more flexible encoding options or advanced features(like parallel transcoding), we recommend directly using `ffmpeg` or a more feature-rich library.
"""

__all__ = [
    "wav_to_flac",
    "wav_to_mp3",
    "avi_to_mp4",
]

import logging
import os
import subprocess
from pathlib import Path
from typing import List

def transcode_wav(dir: Path, format: str, options: List[str] = []):
    for dirpath, _, filenames in os.walk(dir):
        for filename_wav in filenames:
            if not filename_wav.lower().endswith(".wav"):
                continue
            filename_trans = filename_wav[:-3] + format

            file_wav = os.path.join(dirpath, filename_wav)
            file_trans = os.path.join(dirpath, filename_trans)
            if os.path.exists(file_trans):
                logging.warning(f"{filename_trans} already exists.")
                continue

            logging.info(f"Start transcoding {filename_wav} to {format}")

            returncode = subprocess.call(
                ["ffmpeg", "-i", file_wav, *options, file_trans], stdout=open(os.devnull, "w"), stderr=subprocess.STDOUT
            )
            if returncode == 0:
                logging.info(f"Transcoded {filename_wav} successfully, deleting this source file")
                os.remove(file_wav)
            else:
                logging.fatal(f"Failed to transcode {filename_wav} to {format}. Check your ffmpeg")


def wav_to_flac(dir: Path):
    transcode_wav(dir, "flac")


def wav_to_mp3(dir: Path):
    transcode_wav(dir, "mp3", ["-b:a", "320k"])


def transcode_avi(dir: Path, format: str, options: List[str] = []):
    # 类似 transcode_wav 的逻辑，但是过滤 .avi 文件并转为 mp4
    for dirpath, _, filenames in os.walk(dir):
        for filename_avi in filenames:
            if not filename_avi.lower().endswith(".avi"):
                continue
            filename_trans = filename_avi[:-3] + format

            file_avi = os.path.join(dirpath, filename_avi)
            file_trans = os.path.join(dirpath, filename_trans)
            if os.path.exists(file_trans):
                logging.warning(f"{filename_trans} already exists.")
                continue

            logging.info(f"Start transcoding {filename_avi} to {format}")

            returncode = subprocess.call(
                ["ffmpeg", "-i", file_avi, *options, file_trans], stdout=open(os.devnull, "w"), stderr=subprocess.STDOUT
            )
            if returncode == 0:
                logging.info(f"Transcoded {filename_avi} successfully, deleting this source file")
                os.remove(file_avi)
            else:
                logging.fatal(f"Failed to transcode {filename_avi} to {format}. Check your ffmpeg")


def avi_to_mp4(dir: Path):
    # 这里的转码参数可根据需要调整
    # 使用拷贝流，如果报错则改用转码，如 ["-c:v", "libx264", "-c:a", "aac", "-strict", "experimental"]
    transcode_avi(dir, "mp4", ["-c:v", "copy", "-c:a", "copy"])
