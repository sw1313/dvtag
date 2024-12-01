__all__ = [
    "tag",
]

import configparser
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
from ._utils import (
    extract_titles,
    get_audio_paths_list,
    get_image,
    get_png_byte_arr,
    extract_flac_tags,
    extract_id3_tags,
    extract_mp4_tags,
)

def tag_mp3s(mp3_paths: List[Path], dv: DoujinVoice, png_bytes_arr: Optional[BytesIO], disc_number: Optional[int], add_chinese_tag: bool):
    """
    为 MP3 文件添加标签信息。

    Args:
        mp3_paths (List[Path]): MP3 文件路径列表。
        dv (DoujinVoice): 包含标签信息的对象。
        png_bytes_arr (Optional[BytesIO]): 封面图片的字节数组，可选。
        disc_number (Optional[int]): 光盘编号，可选。
        add_chinese_tag (bool): 是否添加中文标签。
    """
    files = list(os_sorted(mp3_paths))
    titles = extract_titles(sorted_stems=[f.stem for f in files], files=files)

    for trck, title, p in zip(range(1, len(files) + 1), titles, files):
        try:
            tags = ID3(p)
            old_tags = extract_id3_tags(tags)

            # 清除将要修改的标签帧
            for frame in ['APIC:', 'TALB', 'TPE2', 'TDRC', 'TCON', 'TPOS', 'TPE1', 'TIT2', 'TRCK']:
                if frame in tags:
                    del tags[frame]

            # 创建 genres 的本地副本
            if add_chinese_tag:
                lrc_files = [f for f in p.parent.iterdir() if f.name.startswith(p.stem) and f.suffix.endswith(".lrc")]
                if lrc_files:
                    if dv.genres:
                        genres = list(dv.genres)
                        if '中文' not in genres:
                            genres.append('中文')
                    else:
                        genres = ['中文']
                else:
                    genres = dv.genres
            else:
                genres = dv.genres

            # 添加新的标签信息
            if png_bytes_arr:
                tags.add(APIC(mime="image/png", desc="Front Cover", data=png_bytes_arr.getvalue()))
            tags.add(TALB(text=[dv.name]))  # 专辑名称
            tags.add(TPE2(text=[dv.circle]))  # 乐团/团体
            tags.add(TDRC(text=[dv.sale_date]))  # 发行日期
            if genres:
                tags.add(TCON(text=[";".join(genres)]))  # 流派
            if disc_number:
                tags.add(TPOS(text=[str(disc_number)]))  # 光盘编号
            if dv.seiyus:
                tags.add(TPE1(text=dv.seiyus))  # 艺术家/声优
            tags.add(TIT2(text=[title]))  # 标题
            tags.add(TRCK(text=[str(trck)]))  # 音轨编号

            new_tags = extract_id3_tags(tags)

            # 如果标签有变化，则保存
            if old_tags != new_tags:
                tags.save(p, v1=0)
                logging.info(f"已为 '{p.name}' 添加标签：曲目 {trck}, 光盘 {disc_number}, 标题 '{title}'")

        except ID3NoHeaderError:
            logging.warning(f"MP3 文件 '{p.name}' 没有 ID3 头。尝试使用 FFmpeg 修复...")

            # 创建临时文件用于 FFmpeg 转码
            temp_dir = os.path.dirname(str(p))
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=temp_dir) as temp_f:
                temp_file_path = temp_f.name

            # 使用 FFmpeg 转码修复文件
            ffmpeg_cmd = [
                "ffmpeg", "-i", str(p), "-c:v", "copy", "-c:a", "libmp3lame",
                "-qscale:a", "0", "-ac", "2", "-y", temp_file_path
            ]
            try:
                subprocess.run(ffmpeg_cmd, check=True)
            except subprocess.CalledProcessError as e:
                logging.error(f"FFmpeg 处理 '{p.name}' 失败：{e}")
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                continue

            # 替换原始文件
            try:
                os.replace(temp_file_path, str(p))
            except OSError as e:
                logging.error(f"无法用处理后的文件替换 '{p.name}'：{e}")
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                continue

            # 重新尝试添加标签
            try:
                tags = ID3(p)
                old_tags = extract_id3_tags(tags)

                for frame in ['APIC:', 'TALB', 'TPE2', 'TDRC', 'TCON', 'TPOS', 'TPE1', 'TIT2', 'TRCK']:
                    if frame in tags:
                        del tags[frame]

                # 创建 genres 的本地副本
                if add_chinese_tag:
                    lrc_files = [f for f in p.parent.iterdir() if f.name.startswith(p.stem) and f.suffix.endswith(".lrc")]
                    if lrc_files:
                        if dv.genres:
                            genres = list(dv.genres)
                            if '中文' not in genres:
                                genres.append('中文')
                        else:
                            genres = ['中文']
                    else:
                        genres = dv.genres
                else:
                    genres = dv.genres

                if png_bytes_arr:
                    tags.add(APIC(mime="image/png", desc="Front Cover", data=png_bytes_arr.getvalue()))
                tags.add(TALB(text=[dv.name]))
                tags.add(TPE2(text=[dv.circle]))
                tags.add(TDRC(text=[dv.sale_date]))
                if genres:
                    tags.add(TCON(text=[";".join(genres)]))
                if disc_number:
                    tags.add(TPOS(text=[str(disc_number)]))
                if dv.seiyus:
                    tags.add(TPE1(text=dv.seiyus))
                tags.add(TIT2(text=[title]))
                tags.add(TRCK(text=[str(trck)]))

                new_tags = extract_id3_tags(tags)

                if old_tags != new_tags:
                    tags.save(p, v1=0)
                    logging.info(f"已为 '{p.name}' 添加标签：曲目 {trck}, 光盘 {disc_number}, 标题 '{title}'")

            except ID3NoHeaderError:
                logging.error(f"无法修复 '{p.name}' 的 ID3 头。跳过...")
                continue
                

def tag_flacs(files: List[Path], dv: DoujinVoice, png_bytes_arr: Optional[BytesIO], disc: Optional[int], add_chinese_tag: bool):
    """
    为 FLAC 文件添加标签信息。

    Args:
        files (List[Path]): FLAC 文件路径列表。
        dv (DoujinVoice): 包含标签信息的对象。
        png_bytes_arr (Optional[BytesIO]): 封面图片的字节数组，可选。
        disc (Optional[int]): 光盘编号，可选。
        add_chinese_tag (bool): 是否添加中文标签。
    """
    sorted_files = list(os_sorted(files))
    titles = extract_titles(sorted_stems=[f.stem for f in sorted_files], files=sorted_files)

    for trck, title, p in zip(range(1, len(sorted_files) + 1), titles, sorted_files):
        tags = FLAC(p)
        old_tags = extract_flac_tags(tags)

        # 清除并添加封面图片
        if png_bytes_arr:
            tags.clear_pictures()
            picture = Picture()
            picture.type = 3  # Front cover
            picture.mime = "image/png"
            picture.desc = 'Front Cover'
            picture.data = png_bytes_arr.getvalue()
            tags.add_picture(picture)

        # 创建 genres 的本地副本
        if add_chinese_tag:
            lrc_files = [f for f in p.parent.iterdir() if f.name.startswith(p.stem) and f.suffix.endswith(".lrc")]
            if lrc_files:
                if dv.genres:
                    genres = list(dv.genres)
                    if '中文' not in genres:
                        genres.append('中文')
                else:
                    genres = ['中文']
            else:
                genres = dv.genres
        else:
            genres = dv.genres

        # 更新标签信息
        tags["album"] = dv.name
        tags["albumartist"] = dv.circle
        tags["date"] = dv.sale_date
        tags["title"] = title
        tags["tracknumber"] = str(trck)
        if genres:
            tags["genre"] = genres
        if dv.seiyus:
            tags["artist"] = dv.seiyus
        if disc:
            tags["discnumber"] = str(disc)

        new_tags = extract_flac_tags(tags)

        # 如果标签有变化，则保存
        if old_tags != new_tags:
            tags.save(p)
            logging.info(f"已为 '{p.name}' 添加标签：曲目 {trck}, 光盘 {disc}, 标题 '{title}'")
            

def tag_mp4s(files: List[Path], dv: DoujinVoice, png_bytes_arr: Optional[BytesIO], disc: Optional[int], add_chinese_tag: bool):
    """
    为 MP4 文件添加标签信息。

    Args:
        files (List[Path]): MP4 文件路径列表。
        dv (DoujinVoice): 包含标签信息的对象。
        png_bytes_arr (Optional[BytesIO]): 封面图片的字节数组，可选。
        disc (Optional[int]): 光盘编号，可选。
        add_chinese_tag (bool): 是否添加中文标签。
    """
    sorted_files = list(os_sorted(files))
    titles = extract_titles(sorted_stems=[f.stem for f in sorted_files], files=sorted_files)

    for trck, title, p in zip(range(1, len(sorted_files) + 1), titles, sorted_files):
        tags = MP4(p)
        old_tags = extract_mp4_tags(tags)

        # 添加封面图片
        if png_bytes_arr:
            tags["covr"] = [MP4Cover(png_bytes_arr.getvalue(), imageformat=MP4Cover.FORMAT_PNG)]

        # 创建 genres 的本地副本
        if add_chinese_tag and '中文' in str(p.parent):
            if dv.genres:
                genres = list(dv.genres)
                if '中文' not in genres:
                    genres.append('中文')
            else:
                genres = ['中文']
        else:
            genres = dv.genres

        # 更新标签信息
        tags["\xa9alb"] = dv.name  # 专辑名称
        tags["\xa9day"] = dv.sale_date  # 发行日期
        tags["\xa9nam"] = title  # 标题
        tags["aART"] = dv.circle  # 专辑艺术家
        tags["\xa9ART"] = dv.seiyus  # 艺术家/声优

        # 将流派列表转换为以逗号分隔的字符串
        if genres:
            tags["\xa9gen"] = ', '.join(genres)  # 流派

        tags["trkn"] = [(trck, 0)]  # 音轨编号
        if disc:
            tags["disk"] = [(disc, 0)]  # 光盘编号

        new_tags = extract_mp4_tags(tags)

        # 如果标签有变化，则保存
        if old_tags != new_tags:
            tags.save(p)
            logging.info(f"已为 '{p.name}' 添加标签：曲目 {trck}, 光盘 {disc}, 标题 '{title}'")
            

def tag(basepath: Path, workno: str):
    """
    主标签函数，根据提供的路径和作品编号，为音频文件添加标签。

    Args:
        basepath (Path): 音频文件的基础路径。
        workno (str): 作品编号。
    """

    # 读取 config.ini 配置文件
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    add_chinese_tag = config.getboolean('Settings', 'add_chinese_tag', fallback=True)  # 读取 add_chinese_tag 配置项，默认为 False

    # 获取音频文件列表
    flac_paths_list, m4a_paths_list, mp3_paths_list, mp4_paths_list = get_audio_paths_list(basepath)
    if not flac_paths_list and not m4a_paths_list and not mp3_paths_list and not mp4_paths_list:
        return

    # 获取作品信息
    try:
        dv = scrape(workno)
    except ParsingError:
        raise
    except Exception as e:
        logging.exception(f"在抓取 {workno} 的元数据时发生错误：{e}")
        return

    # 输出作品信息
    logging.info(f"[{workno}] 准备添加标签...")
    logging.info(f" 圈名: {dv.circle}")
    logging.info(f" 专辑: {dv.name}")
    logging.info(f" 声优: {', '.join(dv.seiyus)}")
    logging.info(f" 流派: {', '.join(dv.genres)}")
    logging.info(f" 日期: {dv.sale_date}")

    # 获取封面图片
    try:
        image = get_image(dv.image_url)
        png_bytes_arr = get_png_byte_arr(image)
    except Exception as e:
        logging.warning(f"获取 {dv.image_url} 的图片时出错：{e}")
        png_bytes_arr = None  # 如果获取图片失败，设置为 None

    # 确定光盘编号
    disc = None
    total_lists = len(flac_paths_list) + len(m4a_paths_list) + len(mp3_paths_list) + len(mp4_paths_list)
    if total_lists > 1:
        disc = 1

    # 为 FLAC 文件添加标签
    for flac_files in flac_paths_list:
        tag_flacs(flac_files, dv, png_bytes_arr, disc, add_chinese_tag)
        if disc:
            disc += 1

    # 为 M4A 文件添加标签
    for m4a_files in m4a_paths_list:
        tag_mp4s(m4a_files, dv, png_bytes_arr, disc, add_chinese_tag)
        if disc:
            disc += 1

    # 为 MP3 文件添加标签
    for mp3_files in mp3_paths_list:
        tag_mp3s(mp3_files, dv, png_bytes_arr, disc, add_chinese_tag)
        if disc:
            disc += 1

    # 为 MP4 文件添加标签
    for mp4_files in mp4_paths_list:
        tag_mp4s(mp4_files, dv, png_bytes_arr, disc, add_chinese_tag)
        if disc:
            disc += 1

    logging.info(f"[{workno}] 完成。")
