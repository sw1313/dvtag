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
            filename_trans = filename_wav[:-4] + format  # 修正索引，防止去除 ".wav" 变成 "wa"

            file_wav = os.path.join(dirpath, filename_wav)
            file_trans = os.path.join(dirpath, filename_trans)
            temp_file_trans = file_trans + ".temp"

            if os.path.exists(file_trans):
                try:
                    os.remove(file_trans)
                    logging.info(f"Removed existing file {filename_trans} to allow overwriting.")
                except OSError as e:
                    logging.error(f"Failed to remove existing file {filename_trans}: {e}")
                    continue  # 跳过此文件，继续处理下一个文件

            logging.info(f"Start transcoding {filename_wav} to {format}")

            returncode = subprocess.call(
                ["ffmpeg", "-y", "-i", file_wav, *options, temp_file_trans],
                stdout=open(os.devnull, "w"),
                stderr=subprocess.STDOUT
            )
            if returncode == 0:
                try:
                    if os.path.exists(file_trans):
                        os.remove(file_trans)
                    os.rename(temp_file_trans, file_trans)
                    logging.info(f"Transcoded {filename_wav} successfully, deleting this source file")
                    os.remove(file_wav)
                except OSError as e:
                    logging.error(f"Failed to rename temporary file for {filename_trans}: {e}")
            else:
                logging.fatal(f"Failed to transcode {filename_wav} to {format}. Check your ffmpeg")
                if os.path.exists(temp_file_trans):
                    os.remove(temp_file_trans)

def wav_to_flac(dir: Path):
    transcode_wav(dir, "flac")

def wav_to_mp3(dir: Path):
    transcode_wav(dir, "mp3", ["-b:a", "320k"])

def transcode_avi(dir: Path, format: str, options: List[str] = []):
    for dirpath, _, filenames in os.walk(dir):
        for filename_avi in filenames:
            if not filename_avi.lower().endswith(".avi"):
                continue
            filename_trans = filename_avi[:-4] + format  # 修正索引，防止去除 ".avi" 变成 "av"

            file_avi = os.path.join(dirpath, filename_avi)
            file_trans = os.path.join(dirpath, filename_trans)
            temp_file_trans = file_trans + ".temp"

            if os.path.exists(file_trans):
                try:
                    os.remove(file_trans)
                    logging.info(f"Removed existing file {filename_trans} to allow overwriting.")
                except OSError as e:
                    logging.error(f"Failed to remove existing file {filename_trans}: {e}")
                    continue  # 跳过此文件，继续处理下一个文件

            logging.info(f"Start transcoding {filename_avi} to {format}")

            returncode = subprocess.call(
                ["ffmpeg", "-y", "-i", file_avi, *options, temp_file_trans],
                stdout=open(os.devnull, "w"),
                stderr=subprocess.STDOUT
            )
            if returncode == 0:
                try:
                    if os.path.exists(file_trans):
                        os.remove(file_trans)
                    os.rename(temp_file_trans, file_trans)
                    logging.info(f"Transcoded {filename_avi} successfully, deleting this source file")
                    os.remove(file_avi)
                except OSError as e:
                    logging.error(f"Failed to rename temporary file for {filename_trans}: {e}")
            else:
                logging.fatal(f"Failed to transcode {filename_avi} to {format}. Check your ffmpeg")
                if os.path.exists(temp_file_trans):
                    os.remove(temp_file_trans)

def avi_to_mp4(dir: Path):
    # 这里的转码参数可根据需要调整
    # 使用拷贝流，如果报错则改用转码，如 ["-c:v", "libx264", "-c:a", "aac", "-strict", "experimental"]
    transcode_avi(dir, "mp4", ["-c:v", "copy", "-c:a", "copy"])
