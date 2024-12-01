__all__ = [
    "create_request_session",
    "extract_titles",
    "get_audio_paths_list",
    "get_image",
    "get_picture",
    "get_png_byte_arr",
    "get_workno",
    "extract_id3_tags",
    "extract_flac_tags",
    "extract_mp4_tags",
]

import configparser
import io
import logging
import os
import re
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from natsort import os_sort_key
from PIL import Image, UnidentifiedImageError
from requests.adapters import HTTPAdapter, Retry

# 初始化配置对象
_config = None

def get_config():
    """读取配置文件 config.ini，如果未读取过则初始化配置对象。

    Returns:
        configparser.ConfigParser: 配置对象
    """
    global _config
    if _config is None:
        _config = configparser.ConfigParser()
        config_file = os.path.join(os.path.dirname(__file__), 'config.ini')
        _config.read(config_file, encoding='utf-8')
    return _config

# 正则表达式，用于匹配作品编号（例如 RJ123456）
_workno_pat = re.compile(r"(R|B|V)J\d{6}(\d\d)?", flags=re.IGNORECASE)

def get_workno(name: str) -> Optional[str]:
    """从给定的字符串中提取作品编号（例如 RJ123456）。

    Args:
        name (str): 输入字符串

    Returns:
        Optional[str]: 作品编号（大写），如果未找到则返回 None
    """
    m = _workno_pat.search(name)
    if m:
        return m.group().upper()
    return None

def create_request_session(max_retries=5) -> requests.Session:
    """创建支持重试机制的请求会话。

    Args:
        max_retries (int, optional): 最大重试次数。默认为 5。

    Returns:
        requests.Session: 请求会话对象
    """
    session = requests.Session()
    retries = Retry(
        total=max_retries,
        backoff_factor=0.1,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def get_image(url: str) -> Optional[Image.Image]:
    """从 URL 获取图片。

    Args:
        url (str): 图片的 URL

    Returns:
        Optional[Image.Image]: 成功则返回 Image 对象，否则返回 None
    """
    try:
        response = create_request_session().get(url, stream=True)
        response.raise_for_status()
        return Image.open(response.raw)
    except (requests.exceptions.RequestException, UnidentifiedImageError) as e:
        logging.error(f"Error getting image from {url}: {e}")
        return None

def get_png_byte_arr(im: Image.Image) -> BytesIO:
    """将 Image 对象转换为 PNG 格式的字节数组。

    Args:
        im (Image.Image): Image 对象

    Returns:
        BytesIO: 包含 PNG 数据的字节流
    """
    img_byte_arr = io.BytesIO()
    im.save(img_byte_arr, format='PNG')
    return img_byte_arr

def get_picture(png_byte_arr: BytesIO, width: int, height: int, mode: str) -> Picture:
    """创建 FLAC 格式的 Picture 对象。

    Args:
        png_byte_arr (BytesIO): PNG 数据的字节流
        width (int): 图片宽度
        height (int): 图片高度
        mode (str): 图片模式（如 'RGB'）

    Returns:
        Picture: FLAC 格式的 Picture 对象
    """
    picture = Picture()
    picture.mime = "image/png"
    picture.width = width
    picture.height = height
    picture.type = 3  # Front cover

    # 根据模式设置颜色深度
    if mode == "RGB":
        picture.depth = 24
    elif mode == "RGBA":
        picture.depth = 32
    else:
        picture.depth = 0  # Unknown

    picture.data = png_byte_arr.getvalue()
    return picture

def _walk(basepath: Path):
    """递归遍历目录，获取文件列表。

    Args:
        basepath (Path): 基础路径

    Yields:
        List[Path]: 当前目录下的文件列表
    """
    dirs: List[Path] = []
    files: List[Path] = []
    for file in basepath.iterdir():
        if file.is_dir():
            dirs.append(file)
        else:
            files.append(file)
    yield files

    dirs = sorted(dirs, key=lambda d: os_sort_key(d.name))
    for d in dirs:
        yield from _walk(d)

def get_audio_paths_list(basepath: Path) -> Tuple[
    List[List[Path]], List[List[Path]], List[List[Path]], List[List[Path]]
]:
    """递归获取指定路径下的音频和视频文件路径列表。

    Args:
        basepath (Path): 基础路径

    Returns:
        Tuple[List[List[Path]], List[List[Path]], List[List[Path]], List[List[Path]]]:
        flac_paths_list, m4a_paths_list, mp3_paths_list, mp4_paths_list
    """
    flac_paths_list: List[List[Path]] = []
    m4a_paths_list: List[List[Path]] = []
    mp3_paths_list: List[List[Path]] = []
    mp4_paths_list: List[List[Path]] = []

    for files in _walk(basepath):
        flac_paths: List[Path] = []
        m4a_paths: List[Path] = []
        mp3_paths: List[Path] = []
        mp4_paths: List[Path] = []

        for file in files:
            if file.suffix.lower() == ".flac":
                flac_paths.append(file)
            elif file.suffix.lower() == ".m4a":
                m4a_paths.append(file)
            elif file.suffix.lower() == ".mp3":
                mp3_paths.append(file)
            elif file.suffix.lower() == ".mp4":
                mp4_paths.append(file)

        if flac_paths:
            flac_paths_list.append(flac_paths)
        if m4a_paths:
            m4a_paths_list.append(m4a_paths)
        if mp3_paths:
            mp3_paths_list.append(mp3_paths)
        if mp4_paths:
            mp4_paths_list.append(mp4_paths)

    return flac_paths_list, m4a_paths_list, mp3_paths_list, mp4_paths_list

# 用于匹配音轨标题的正则表达式
_title_pat = re.compile(
    r"^(#|■|◆|【|$|(?:【?tr(?:ack)?|トラック|音轨|とらっく)[\-_‗\s\.．・,：]*)?(\d+)([\-_‗\s\.．・,：】$]+|(?=[「『【]))(.+)",
    re.IGNORECASE,
)

from typing import List
from pathlib import Path

def extract_titles(sorted_stems: List[str], files: List[Path]) -> List[str]:
    """
    从排序后的文件名列表中提取标题，并根据配置添加文件类型后缀和音效后缀。

    Args:
        sorted_stems (List[str]): 排序后的文件名列表（不含扩展名）。
        files (List[Path]): 对应的文件路径列表。

    Returns:
        List[str]: 处理后的标题列表，包含后缀。
    """
    config = get_config()
    add_file_type_suffix = config.getboolean('Settings', 'add_file_type_suffix', fallback=True)
    add_sound_effect_suffix = config.getboolean('Settings', 'add_sound_effect_suffix', fallback=True)

    extracted_titles: List[str] = []

    for i, (stem, file) in enumerate(zip(sorted_stems, files)):
        # 尝试匹配正则表达式
        m = _title_pat.match(stem)
        if m:
            # 如果匹配成功，提取标题部分
            title = m.group(4)
        else:
            # 如果匹配失败，使用原始文件名作为标题
            title = stem

        # 添加文件类型后缀
        if add_file_type_suffix:
            if file.suffix.lower() == ".mp3":
                title += "-便携版"
            elif file.suffix.lower() == ".flac":
                title += "-高保真"

        # 添加音效后缀
        if add_sound_effect_suffix:
            parent_folder_name = file.parent.name.lower()
            grandparent_folder_name = file.parent.parent.name.lower()  # 检查父文件夹的父文件夹

            sound_effect_pattern = r"(se|効果音|音效|声音效果)"
            no_sound_pattern = r"(没有|无|無|入れ前|なし|off|no|未含|未加|カット)"
            has_sound_pattern = r"(有|あり|含|on|有り|付き|つき)"

            if re.search(sound_effect_pattern, parent_folder_name) or \
               re.search(sound_effect_pattern, grandparent_folder_name):

                if re.search(no_sound_pattern, parent_folder_name) or \
                   re.search(no_sound_pattern, grandparent_folder_name):
                    title += "-无音效"
                elif re.search(has_sound_pattern, parent_folder_name) or \
                     re.search(has_sound_pattern, grandparent_folder_name):
                    title += "-含音效"

        extracted_titles.append(title)

    return extracted_titles
    
def extract_id3_tags(tags: ID3) -> dict:
    """
    提取 ID3 标签的相关字段，用于比较。

    Args:
        tags (ID3): ID3 标签对象。

    Returns:
        dict: 包含标签字段的字典。
    """
    fields = {}
    for frame_id in ['APIC:', 'TALB', 'TPE2', 'TDRC', 'TCON', 'TPOS', 'TPE1', 'TIT2', 'TRCK']:
        frame = tags.get(frame_id)
        if frame:
            fields[frame_id] = frame.__dict__
    return fields

def extract_flac_tags(tags: FLAC) -> dict:
    """
    提取 FLAC 标签的相关字段，用于比较。

    Args:
        tags (FLAC): FLAC 标签对象。

    Returns:
        dict: 包含标签字段的字典。
    """
    fields = {}
    for key in ["album", "albumartist", "date", "title", "tracknumber", "genre", "artist", "discnumber"]:
        value = tags.get(key)
        if value:
            fields[key] = value
    # 提取图片信息
    if tags.pictures:
        fields["picture"] = tags.pictures[0].data
    else:
        fields["picture"] = None
    return fields

def extract_mp4_tags(tags: MP4) -> dict:
    """
    提取 MP4 标签的相关字段，用于比较。

    Args:
        tags (MP4): MP4 标签对象。

    Returns:
        dict: 包含标签字段的字典。
    """
    fields = {}
    for key in ["covr", "\xa9alb", "\xa9day", "\xa9nam", "aART", "\xa9ART", "\xa9gen", "trkn", "disk"]:
        value = tags.get(key)
        if value:
            fields[key] = value
    return fields
