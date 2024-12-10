"""This module provides a minimal implementation of some functions for transcoding `.wav` files to other formats using `ffmpeg`.

If users need more flexible encoding options or advanced features (like parallel transcoding), we recommend directly using `ffmpeg` or a more feature-rich library.
"""

__all__ = [
    "wav_to_flac",
    "wav_to_mp3",
    "avi_to_mp4",
]

import logging
import subprocess
from pathlib import Path
from typing import List

def transcode_wav(directory: Path, format: str, options: List[str] = []):
    """
    转码目录中的所有 WAV 文件为指定格式。

    参数:
    - directory (Path): 包含 WAV 文件的目录路径。
    - format (str): 目标格式（例如 "flac", "mp3" 等）。
    - options (List[str]): 传递给 ffmpeg 的额外参数。
    """
    for wav_file in directory.rglob("*.wav"):
        if not wav_file.is_file():
            continue

        filename_trans = wav_file.with_suffix(f".{format}")
        temp_file_trans = wav_file.with_suffix(f".temp.{format}")

        if filename_trans.exists():
            try:
                filename_trans.unlink()
            except OSError as e:
                logging.error(f"无法移除现有文件 {filename_trans.name}：{e}")
                continue

        logging.info(f"开始转码 {wav_file.name} 到 {format}")
        
        # 不显示 ffmpeg 标准输出和标准错误，只显示最终结果提示
        ffmpeg_cmd = ["ffmpeg", "-y", "-i", str(wav_file)] + options + [str(temp_file_trans)]
        try:
            subprocess.run(
                ffmpeg_cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            logging.error(f"转码 {wav_file.name} 失败。")
            # 如果是 flac 格式，尝试备用参数
            if format.lower() == "flac":
                if temp_file_trans.exists():
                    temp_file_trans.unlink()
                fallback_options = ["-vn", "-c:a", "flac", "-ar", "44100", "-sample_fmt", "s16", "-ac", "2"]
                ffmpeg_cmd_fallback = ["ffmpeg", "-y", "-i", str(wav_file)] + fallback_options + [str(temp_file_trans)]
                try:
                    subprocess.run(
                        ffmpeg_cmd_fallback,
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except subprocess.CalledProcessError:
                    logging.error(f"使用备用参数转码 {wav_file.name} 仍然失败。")
                    if temp_file_trans.exists():
                        temp_file_trans.unlink()
                    continue
            else:
                # 不是 flac 格式且失败，直接继续
                if temp_file_trans.exists():
                    temp_file_trans.unlink()
                continue

        if temp_file_trans.exists():
            try:
                filename_trans.unlink(missing_ok=True)
                temp_file_trans.rename(filename_trans)
                logging.info(f"成功转码 {wav_file.name}，删除源文件。")
                wav_file.unlink()
            except OSError as e:
                logging.error(f"无法重命名临时文件 {temp_file_trans} 为 {filename_trans}：{e}")
                if temp_file_trans.exists():
                    temp_file_trans.unlink()
        else:
            logging.error(f"临时文件 {temp_file_trans} 未创建。转码失败。")


def wav_to_flac(subdir: Path):
    """
    转码子目录中的所有 WAV 文件为 FLAC 格式，优先使用无损转换。

    参数:
    - subdir (Path): 包含 WAV 文件的子目录路径。
    """
    transcode_wav(subdir, "flac", ["-c:a", "flac", "-compression_level", "0"])


def wav_to_mp3(subdir: Path):
    """
    转码子目录中的所有 WAV 文件为 MP3 格式。

    参数:
    - subdir (Path): 包含 WAV 文件的子目录路径。
    """
    for wav_file in subdir.glob("*.wav"):
        mp3_file = wav_file.with_suffix(".mp3")
        temp_mp3_file = wav_file.with_suffix(".temp.mp3")

        logging.info(f"转码 {wav_file} 到 mp3 ...")
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-i", str(wav_file),
            "-c:a", "libmp3lame",
            "-b:a", "320k",
            str(temp_mp3_file)
        ]

        try:
            subprocess.run(
                ffmpeg_cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            mp3_file.unlink(missing_ok=True)
            temp_mp3_file.rename(mp3_file)
            wav_file.unlink()
            logging.info(f"成功转码 {wav_file} 到 {mp3_file}")
        except subprocess.CalledProcessError:
            logging.error(f"转码 {wav_file} 失败。")
            if temp_mp3_file.exists():
                temp_mp3_file.unlink()


def transcode_avi(directory: Path, format: str, options: List[str] = []):
    """
    转码目录中的所有 AVI 文件为指定格式。

    参数:
    - directory (Path): 包含 AVI 文件的目录路径。
    - format (str): 目标格式（例如 "mp4", "mkv" 等）。
    - options (List[str]): 传递给 ffmpeg 的额外参数。
    """
    for avi_file in directory.rglob("*.avi"):
        if not avi_file.is_file():
            continue

        filename_trans = avi_file.with_suffix(f".{format}")
        temp_file_trans = avi_file.with_suffix(f".temp.{format}")

        if filename_trans.exists():
            try:
                filename_trans.unlink()
            except OSError as e:
                logging.error(f"无法移除现有文件 {filename_trans.name}：{e}")
                continue

        logging.info(f"开始转码 {avi_file.name} 到 {format}")

        ffmpeg_cmd = ["ffmpeg", "-y", "-i", str(avi_file)] + options + [str(temp_file_trans)]
        try:
            subprocess.run(
                ffmpeg_cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            logging.error(f"转码 {avi_file.name} 到 {format} 失败。")
            if temp_file_trans.exists():
                temp_file_trans.unlink()
            continue

        if temp_file_trans.exists():
            try:
                filename_trans.unlink(missing_ok=True)
                temp_file_trans.rename(filename_trans)
                logging.info(f"成功转码 {avi_file.name} 到 {filename_trans.name}，删除源文件。")
                avi_file.unlink()
            except OSError as e:
                logging.error(f"无法重命名临时文件 {temp_file_trans} 为 {filename_trans}：{e}")
                if temp_file_trans.exists():
                    temp_file_trans.unlink()
        else:
            logging.error(f"临时文件 {temp_file_trans} 未创建。转码失败。")


def avi_to_mp4(directory: Path):
    """
    转码目录中的所有 AVI 文件为 MP4 格式，使用无损转换（拷贝流）。

    参数:
    - directory (Path): 包含 AVI 文件的目录路径。
    """
    transcode_avi(directory, "mp4", ["-c:v", "copy", "-c:a", "copy"])
