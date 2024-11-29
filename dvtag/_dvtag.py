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
from ._utils import (
    extract_titles,
    get_audio_paths_list,
    get_image,
    get_png_byte_arr,
    extract_flac_tags,
    extract_id3_tags,
    extract_mp4_tags,
)


def tag_mp3s(mp3_paths: List[Path], dv: DoujinVoice, png_bytes_arr: Optional[BytesIO], disc_number: Optional[int]):
    files = list(os_sorted(mp3_paths))
    titles = extract_titles(sorted_stems=[f.stem for f in files], files=files)

    for trck, title, p in zip(range(1, len(files) + 1), titles, files):
        try:
            tags = ID3(p)
            old_tags = extract_id3_tags(tags)

            for frame in ['APIC:', 'TALB', 'TPE2', 'TDRC', 'TCON', 'TPOS', 'TPE1', 'TIT2', 'TRCK']:
                if frame in tags:
                    del tags[frame]

            if png_bytes_arr:
                tags.add(APIC(mime="image/png", desc="Front Cover", data=png_bytes_arr.getvalue()))
            tags.add(TALB(text=[dv.name]))
            tags.add(TPE2(text=[dv.circle]))
            tags.add(TDRC(text=[dv.sale_date]))
            if dv.genres:
                tags.add(TCON(text=[", ".join(dv.genres)]))
            if disc_number:
                tags.add(TPOS(text=[str(disc_number)]))
            if dv.seiyus:
                tags.add(TPE1(text=dv.seiyus))
            tags.add(TIT2(text=[title]))
            tags.add(TRCK(text=[str(trck)]))

            new_tags = extract_id3_tags(tags)

            if old_tags != new_tags:
                tags.save(p, v1=0)
                logging.info(f"Tagged <track: {trck}, disc: {disc_number}, title: '{title}'> to '{p.name}'")

        except ID3NoHeaderError:
            logging.warning(f"MP3 file '{p.name}' has no ID3 header. Trying to fix with FFmpeg...")

            temp_dir = os.path.dirname(str(p))
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=temp_dir) as temp_f:
                temp_file_path = temp_f.name

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

            try:
                os.replace(temp_file_path, str(p))
            except OSError as e:
                logging.error(f"Failed to replace '{p.name}' with the processed file: {e}")
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                continue

            try:
                tags = ID3(p)
                old_tags = extract_id3_tags(tags)

                for frame in ['APIC:', 'TALB', 'TPE2', 'TDRC', 'TCON', 'TPOS', 'TPE1', 'TIT2', 'TRCK']:
                    if frame in tags:
                        del tags[frame]

                if png_bytes_arr:
                    tags.add(APIC(mime="image/png", desc="Front Cover", data=png_bytes_arr.getvalue()))
                tags.add(TALB(text=[dv.name]))
                tags.add(TPE2(text=[dv.circle]))
                tags.add(TDRC(text=[dv.sale_date]))
                if dv.genres:
                    tags.add(TCON(text=[", ".join(dv.genres)]))
                if disc_number:
                    tags.add(TPOS(text=[str(disc_number)]))
                if dv.seiyus:
                    tags.add(TPE1(text=dv.seiyus))
                tags.add(TIT2(text=[title]))
                tags.add(TRCK(text=[str(trck)]))

                new_tags = extract_id3_tags(tags)

                if old_tags != new_tags:
                    tags.save(p, v1=0)
                    logging.info(f"Tagged <track: {trck}, disc: {disc_number}, title: '{title}'> to '{p.name}'")

            except ID3NoHeaderError:
                logging.error(f"Failed to fix ID3 header for '{p.name}'. Skipping...")
                continue


def tag_flacs(files: List[Path], dv: DoujinVoice, png_bytes_arr: Optional[BytesIO], disc: Optional[int]):
    sorted_files = list(os_sorted(files))
    titles = extract_titles(sorted_stems=[f.stem for f in sorted_files], files=sorted_files)

    for trck, title, p in zip(range(1, len(sorted_files) + 1), titles, sorted_files):
        tags = FLAC(p)
        old_tags = extract_flac_tags(tags)

        if png_bytes_arr:
            tags.clear_pictures()
            picture = Picture()
            picture.type = 3  # Front cover
            picture.mime = "image/png"
            picture.desc = 'Front Cover'
            picture.data = png_bytes_arr.getvalue()
            tags.add_picture(picture)

        tags["album"] = dv.name
        tags["albumartist"] = dv.circle
        tags["date"] = dv.sale_date
        tags["title"] = title
        tags["tracknumber"] = str(trck)
        if dv.genres:
            tags["genre"] = dv.genres
        if dv.seiyus:
            tags["artist"] = dv.seiyus
        if disc:
            tags["discnumber"] = str(disc)

        new_tags = extract_flac_tags(tags)

        if old_tags != new_tags:
            tags.save(p)
            logging.info(f"Tagged <track: {trck}, disc: {disc}, title: '{title}'> to '{p.name}'")


def tag_mp4s(files: List[Path], dv: DoujinVoice, png_bytes_arr: Optional[BytesIO], disc: Optional[int]):
    sorted_files = list(os_sorted(files))
    titles = extract_titles(sorted_stems=[f.stem for f in sorted_files], files=sorted_files)

    for trck, title, p in zip(range(1, len(sorted_files) + 1), titles, sorted_files):
        tags = MP4(p)
        old_tags = extract_mp4_tags(tags)

        if png_bytes_arr:
            tags["covr"] = [MP4Cover(png_bytes_arr.getvalue(), imageformat=MP4Cover.FORMAT_PNG)]
        tags["\xa9alb"] = dv.name
        tags["\xa9day"] = dv.sale_date
        tags["\xa9nam"] = title
        tags["aART"] = dv.circle
        tags["\xa9ART"] = dv.seiyus
        tags["\xa9gen"] = dv.genres
        tags["trkn"] = [(trck, 0)]
        if disc:
            tags["disk"] = [(disc, 0)]

        new_tags = extract_mp4_tags(tags)

        if old_tags != new_tags:
            tags.save(p)
            logging.info(f"Tagged <track: {trck}, disc: {disc}, title: '{title}'> to '{p.name}'")


def tag(basepath: Path, workno: str):
    flac_paths_list, m4a_paths_list, mp3_paths_list, mp4_paths_list = get_audio_paths_list(basepath)
    if not flac_paths_list and not m4a_paths_list and not mp3_paths_list and not mp4_paths_list:
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
    logging.info(f" Date:    {dv.sale_date}")

    try:
        image = get_image(dv.image_url)
        png_bytes_arr = get_png_byte_arr(image)
    except Exception as e:
        logging.warning(f"Error getting image from {dv.image_url}: {e}")
        png_bytes_arr = None  # Set png_bytes_arr to None if image retrieval fails

    disc = None
    total_lists = len(flac_paths_list) + len(m4a_paths_list) + len(mp3_paths_list) + len(mp4_paths_list)
    if total_lists > 1:
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

    for mp4_files in mp4_paths_list:
        tag_mp4s(mp4_files, dv, png_bytes_arr, disc)
        if disc:
            disc += 1

    logging.info(f"[{workno}] Done.")
