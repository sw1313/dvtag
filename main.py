import argparse
import logging
from importlib.metadata import version
from pathlib import Path

from dvtag import get_workno, tag
from utils import wav_to_flac, wav_to_mp3

logging.basicConfig(level=logging.INFO, format="%(message)s")


def start(dirpath: Path, w2f: bool, w2m: bool):
    # 获取所有子文件夹
    subdirs = [file for file in dirpath.iterdir() if file.is_dir()]

    # 提取每个子文件夹的 RJ 号
    worknos = []
    for subdir in subdirs:
        workno = get_workno(subdir.name)
        if workno:
            worknos.append((subdir, workno))

    # 按 RJ 号排序
    worknos.sort(key=lambda x: x[1])

    # 遍历排序后的文件夹列表
    for subdir, workno in worknos:
        if w2f:
            wav_to_flac(subdir)
        if w2m:
            wav_to_mp3(subdir)
        tag(subdir, workno)


def main():
    parser = argparse.ArgumentParser(prog="dvtag", description="Doujin Voice Tagging Tool (tagging in place)")
    parser.add_argument("-v", "--version", action="version", version=version(parser.prog))
    parser.add_argument("dirpath", type=str, help="a required directory path")
    parser.add_argument(
        "-w2f", default=False, action=argparse.BooleanOptionalAction, help="transcode all wav files to flac [LOSELESS]"
    )
    parser.add_argument(
        "-w2m", default=False, action=argparse.BooleanOptionalAction, help="transcode all wav files to mp3"
    )

    args = parser.parse_args()
    path = Path(args.dirpath).absolute()

    start(path, args.w2f, args.w2m)


if __name__ == "__main__":
    main()
