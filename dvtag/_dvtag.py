__all__ = [
    "tag",
]

import logging
import os
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, TALB, TCON, TDRC, TIT2, TPE1, TPE2, TPOS, TRCK, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4Cover
from natsort import os_sorted
from PIL import Image

from ._doujin_voice import DoujinVoice
from ._scrape import ParsingError, scrape
from ._utils import extract_titles, get_audio_paths_list, get_image, get_png_byte_arr


def tag_mp3s(mp3_paths: List[Path], dv: DoujinVoice, png_bytes_arr: Optional[BytesIO], disc_number: Optional[int]):
    sorted = list(os_sorted(mp3_paths))
    titles = extract_titles(sorted_stems=[f.stem for f in sorted])

    for trck, title, p in zip(range(1, len(sorted) + 1), titles, sorted):
        try:
            tags = ID3(p)  # 读取标签信息

            # 仅在获取图片成功时才清除 APIC 标签和添加封面
            if png_bytes_arr:
                if 'APIC:' in tags:
                    del tags['APIC:']  # 清除原有的 APIC 标签
                tags.add(APIC(mime="image/png", desc="Front Cover", data=png_bytes_arr.getvalue()))

            # 无论图片是否获取成功，都更新其他标签信息
            tags.add(TALB(text=[dv.name]))
            tags.add(TPE2(text=[dv.circle]))
            tags.add(TDRC(text=[dv.sale_date]))
            if dv.genres:
                tags.add(TCON(text=[";".join(dv.genres)]))
            if disc_number:
                tags.add(TPOS(text=[str(disc_number)]))
            if dv.seiyus:
                tags.add(TPE1(text=dv.seiyus))
            tags.add(TIT2(text=[title]))
            tags.add(TRCK(text=[str(trck)]))

            if ID3(p) != tags:
                tags.save(p, v1=0)
                logging.info(f"Tagged <track: {trck}, disc: {disc_number}, title: '{title}'> to '{p.name}'")

        except ID3NoHeaderError:
            logging.warning(f"MP3 file '{p.name}' has no ID3 header. Trying to fix with FFmpeg...")

            # 在与 MP3 文件相同的磁盘驱动器上创建临时文件
            temp_dir = os.path.dirname(str(p))
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=temp_dir) as temp_f:
                temp_file_path = temp_f.name

            # 使用 FFmpeg 重新编码 MP3 文件，输出到临时文件
            ffmpeg_cmd = [
                "ffmpeg", "-i", str(p), "-c:v", "copy", "-c:a", "libmp3lame",
                "-qscale:a", "0", "-ac", "2", "-y", temp_file_path
            ]
            try:
                subprocess.run(ffmpeg_cmd, check=True)
            except subprocess.CalledProcessError as e:
                logging.error(f"FFmpeg failed to process '{p.name}': {e}")
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                continue

            # 替换原文件
            try:
                os.replace(temp_file_path, str(p))
            except OSError as e:
                logging.error(f"Failed to replace '{p.name}' with the processed file: {e}")
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                continue

            try:
                tags = ID3(p)  # 重新读取标签信息

                # 仅在获取图片成功时才清除 APIC 标签和添加封面
                if png_bytes_arr:
                    if 'APIC:' in tags:
                        del tags['APIC:']  # 清除原有的 APIC 标签
                    tags.add(APIC(mime="image/png", desc="Front Cover", data=png_bytes_arr.getvalue()))

                # 无论图片是否获取成功，都更新其他标签信息
                tags.add(TALB(text=[dv.name]))
                tags.add(TPE2(text=[dv.circle]))
                tags.add(TDRC(text=[dv.sale_date]))
                if dv.genres:
                    tags.add(TCON(text=[";".join(dv.genres)]))
                if disc_number:
                    tags.add(TPOS(text=[str(disc_number)]))
                if dv.seiyus:
                    tags.add(TPE1(text=dv.seiyus))
                tags.add(TIT2(text=[title]))
                tags.add(TRCK(text=[str(trck)]))

                if ID3(p) != tags:
                    tags.save(p, v1=0)
                    logging.info(f"Tagged <track: {trck}, disc: {disc_number}, title: '{title}'> to '{p.name}'")

            except ID3NoHeaderError:  # 处理 FFmpeg 修复后仍然无法读取标签的情况
                logging.error(f"Failed to fix ID3 header for '{p.name}'. Skipping...")
                continue


def tag_mp4s(files: List[Path], dv: DoujinVoice, png_bytes_arr: Optional[BytesIO], disc: Optional[int]):
    sorted = list(os_sorted(files))
    titles = extract_titles(sorted_stems=[f.stem for f in sorted])

    for trck, title, p in zip(range(1, len(sorted) + 1), titles, sorted):
        tags = MP4(p)

        # 仅在获取图片成功时才清除 covr 标签和添加封面
        if png_bytes_arr:
            if "covr" in tags:
                del tags["covr"]

            cover = MP4Cover(png_bytes_arr.getvalue(), MP4Cover.FORMAT_PNG)
            tags["covr"] = [cover]

        # 无论图片是否获取成功，都更新其他标签信息
        tags["\xa9alb"] = [dv.name]
        tags["\xa9day"] = [dv.sale_date]
        tags["\xa9nam"] = [title]
        tags["aART"] = [dv.circle]
        tags["\xa9ART"] = [";".join(dv.seiyus)]
        tags["\xa9gen"] = [";".join(dv.genres)]
        tags["trkn"] = [(trck, 0)]
        if disc:
            tags["disk"] = [(disc, 0)]

        if tags != MP4(p):
            tags.save(p)
            logging.info(f"Tagged <track: {trck}, disc: {disc}, title: '{title}'> to '{p.name}'")


def tag_flacs(files: List[Path], dv: DoujinVoice, png_bytes_arr: Optional[BytesIO], disc: Optional[int]):
    sorted = list(os_sorted(files))
    titles = extract_titles(sorted_stems=[f.stem for f in sorted])

    for trck, title, p in zip(range(1, len(sorted) + 1), titles, sorted):
        tags = FLAC(p)

        # 仅在获取图片成功时才清除图片和添加封面
        if png_bytes_arr:
            tags.clear_pictures()  # 清除原有图片

            image = Image.open(png_bytes_arr)
            picture = Picture()
            picture.type = 3
            picture.mime = "image/png"
            picture.desc = 'Front Cover'
            picture.data = png_bytes_arr.getvalue()
            tags.add_picture(picture)  # 添加封面

        # 无论图片是否获取成功，都更新其他标签信息
        tags["album"] = [dv.name]
        tags["albumartist"] = [dv.circle]
        tags["date"] = [dv.sale_date]
        tags["title"] = [title]
        tags["tracknumber"] = [str(trck)]
        if dv.genres:
            tags["genre"] = dv.genres
        if dv.seiyus:
            tags["artist"] = dv.seiyus
        if disc:
            tags["discnumber"] = [str(disc)]

        if tags != FLAC(p):
            tags.save(p)
            logging.info(f"Tagged <track: {trck}, disc: {disc}>, title: '{title}'>  to '{p.name}'")


def tag(basepath: Path, workno: str):
    flac_paths_list, m4a_paths_list, mp3_paths_list, mp4_paths_list = get_audio_paths_list(basepath)  # 接收四个列表
    if not flac_paths_list and not m4a_paths_list and not mp3_paths_list and not mp4_paths_list:  # 检查所有列表
        return

    try:
        dv = scrape(workno)
    except ParsingError:
        raise
    except Exception as e:
        logging.exception(f"An error occurred during scraping metadata for {workno}: {e}.")
        return

    logging.info(f"[{workno}] Ready to tag...")
    logging.info(f" Circle: {dv.circle}")
    logging.info(f" Album:  {dv.name}")
    logging.info(f" Seiyu:  {','.join(dv.seiyus)}")
    logging.info(f" Genre:  {','.join(dv.genres)}")
    logging.info(f" Date:   {dv.sale_date}")

    try:
        image = get_image(dv.image_url)
        png_bytes_arr = get_png_byte_arr(image)
    except Exception as e:
        logging.warning(f"Error getting image from {dv.image_url}: {e}")
        png_bytes_arr = None  # Set png_bytes_arr to None if image retrieval fails

    disc = None
    if len(flac_paths_list) + len(m4a_paths_list) + len(mp3_paths_list) + len(mp4_paths_list) > 1:  # 包含 mp4_paths_list
        disc = 1

    for flac_files in flac_paths_list:
        tag_flacs(flac_files, dv, png_bytes_arr, disc)
        if disc:
            disc += 1

    for m4a_files in m4a_paths_list:
        tag_mp4s(m4a_files, dv, png_bytes_arr, disc)
        if disc:
            disc += 1

    for mp3_files in mp3_paths_list:
        tag_mp3s(mp3_files, dv, png_bytes_arr, disc)
        if disc:
            disc += 1

    for mp4_files in mp4_paths_list:  # 添加 MP4 文件处理循环
        tag_mp4s(mp4_files, dv, png_bytes_arr, disc)
        if disc:
            disc += 1

    logging.info(f"[{workno}] Done.")
