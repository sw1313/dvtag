__all__ = [
    "create_request_session",
    "extract_titles",
    "get_audio_paths_list",
    "get_image",
    "get_picture",
    "get_png_byte_arr",
    "get_workno",
]

import io
import re
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from mutagen.flac import Picture
from mutagen.id3 import PictureType
from natsort import os_sort_key
from PIL import Image, UnidentifiedImageError
from requests.adapters import HTTPAdapter, Retry

import configparser
import os

_config = None

def get_config():
    global _config
    if _config is None:
        _config = configparser.ConfigParser()
        config_file = os.path.join(os.path.dirname(__file__), 'config.ini')
        _config.read(config_file, encoding='utf-8')
    return _config

_workno_pat = re.compile(r"(R|B|V)J\d{6}(\d\d)?", flags=re.IGNORECASE)


def _walk(basepath: Path):
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
        for f in _walk(d):
            yield f


def get_audio_paths_list(basepath: Path) -> Tuple[
    List[List[Path]], List[List[Path]], List[List[Path]], List[List[Path]]
]:
    """Gets audio and video files(Path) from basepath recursively

    Args:
        basepath (Path): base path

    Returns:
        Tuple[List[List[Path]], List[List[Path]], List[List[Path]], List[List[Path]]]: 
        flac paths list, m4a paths list, mp3 paths list, mp4 paths list
    """
    flac_paths_list: List[List[Path]] = []
    m4a_paths_list: List[List[Path]] = []
    mp3_paths_list: List[List[Path]] = []
    mp4_paths_list: List[List[Path]] = []  # 新增对 .mp4 文件的支持

    for files in _walk(basepath):
        flac_paths: List[Path] = []
        m4a_paths: List[Path] = []
        mp3_paths: List[Path] = []
        mp4_paths: List[Path] = []  # 用于收集当前文件夹的 .mp4 文件

        for file in files:
            if file.suffix.lower() == ".flac":
                flac_paths.append(file)
            elif file.suffix.lower() == ".m4a":
                m4a_paths.append(file)
            elif file.suffix.lower() == ".mp3":
                mp3_paths.append(file)
            elif file.suffix.lower() == ".mp4":  # 添加对 .mp4 文件的判断
                mp4_paths.append(file)

        if len(flac_paths):
            flac_paths_list.append(flac_paths)
        if len(m4a_paths):
            m4a_paths_list.append(m4a_paths)
        if len(mp3_paths):
            mp3_paths_list.append(mp3_paths)
        if len(mp4_paths):
            mp4_paths_list.append(mp4_paths)

    return flac_paths_list, m4a_paths_list, mp3_paths_list, mp4_paths_list


def get_workno(name: str) -> Optional[str]:
    """Gets workno(of dlsite) from a given string

    Args:
        name (str): A string

    Returns:
        Optional[str]: Returns a string(upper case, like
    """
    m = _workno_pat.search(name)
    if m:
        return m.group().upper()
    return None


def get_image(url: str) -> Optional[Image.Image]:
    """Gets image from url

    Args:
        url (str): image url

    Returns:
        Optional[Image.Image]: Returns Image if success, otherwise None
    """
    try:
        cover_path = create_request_session().get(url, stream=True).raw
        return Image.open(cover_path)
    except (requests.exceptions.RequestException, UnidentifiedImageError) as e:
        print(f"Error getting image from {url}: {e}")
        return None


_png_modes_to_bpp = {
    "1": 1,
    "L": 8,
    "P": 8,
    "RGB": 24,
    "RGBA": 32,
    "I": 32,
}


def get_png_byte_arr(im: Image.Image) -> BytesIO:
    if im.mode not in _png_modes_to_bpp:
        im = im.convert("RGB" if im.info.get("transparency") is None else "RGBA")
    img_byte_arr = io.BytesIO()
    im.save(img_byte_arr, "png")
    return img_byte_arr


def get_picture(png_byte_arr: BytesIO, width: int, height: int, mode: str) -> Picture:
    picture = Picture()
    picture.mime = "image/png"
    picture.width = width
    picture.height = height
    picture.type = PictureType.COVER_FRONT

    picture.depth = _png_modes_to_bpp[mode]
    picture.data = png_byte_arr.getvalue()

    return picture


def create_request_session(max_retries=5) -> requests.Session:
    """Creates a request session that supports retry mechanism

    Args:
        max_retries (int, optional): Maximum retry times. Defaults to 5.

    Returns:
        requests.Session: Request session
    """
    session = requests.Session()
    retries = Retry(total=max_retries, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


_title_pat = re.compile(
    r"^(#|■|◆|【|$|(?:【?tr(?:ack)?|トラック|音轨|とらっく)[\-_‗\s\.．・,：]*)?([\d]+)([\-_‗\s\.．・,：】$]+|(?=[「『【]))(.+)",
    re.IGNORECASE,
)


def extract_titles(sorted_stems: List[str], files: List[Path]) -> List[str]:
    """
    从排序后的文件名列表中提取标题，并根据文件类型和父文件夹名称添加后缀。

    Args:
        sorted_stems (List[str]): 排序后的文件名列表（不含扩展名）。
        files (List[Path]): 对应的文件路径列表。

    Returns:
        List[str]: 提取的标题列表，包含后缀。
    """
    config = get_config()
    add_file_type_suffix = config.getboolean('Settings', 'add_file_type_suffix', fallback=True)
    add_sound_effect_suffix = config.getboolean('Settings', 'add_sound_effect_suffix', fallback=True)

    if len(sorted_stems) <= 1:
        return sorted_stems

    if (m := _title_pat.match(sorted_stems[0])) is None:
        return sorted_stems

    pref: str | None = m.group(1)
    suff: str = m.group(3)
    diff: int = int(m.group(2))

    if pref:
        if pref == "【" and not suff.startswith("】"):
            return sorted_stems
        if pref == "(" and not suff.startswith(")"):
            return sorted_stems

    extracted: List[str] = []

    for i, stem in enumerate(sorted_stems):
        m = _title_pat.match(stem)
        if not m:
            return sorted_stems

        if m.group(1) != pref or m.group(3) != suff:
            return sorted_stems
        if int(m.group(2)) - i != diff:
            return sorted_stems

        title = m.group(4)
        
        # 添加文件类型后缀
        if add_file_type_suffix:
            if files[i].suffix.lower() == ".mp3":
                title += "-便携版"
            elif files[i].suffix.lower() == ".flac":
                title += "-高保真"

        # 添加音效后缀
        if add_sound_effect_suffix:
            parent_folder_name = files[i].parent.name.lower()
            if any(keyword in parent_folder_name for keyword in ("se", "效果音", "音效")):
                if any(keyword in parent_folder_name for keyword in ("无", "無", "入れ前", "なし", "off", "no")):
                    title += "-无音效"
                elif any(keyword in parent_folder_name for keyword in ("有", "あり", "含", "on")):
                    title += "-含音效"

        if title in extracted:
            return sorted_stems

        extracted.append(title)

    return extracted
