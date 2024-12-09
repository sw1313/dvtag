import argparse
import logging
from importlib.metadata import version
from pathlib import Path
import os
import time

from dvtag import get_workno, tag
from utils import wav_to_flac, wav_to_mp3, avi_to_mp4  # 引入刚新增的 avi_to_mp4 函数

logging.basicConfig(level=logging.INFO, format="%(message)s")


def start(dirpath: Path, w2f: bool, w2m: bool, time_range=None, a2m: bool = False):
    # 获取所有子文件夹
    subdirs = [file for file in dirpath.iterdir() if file.is_dir()]

    # 提取每个子文件夹的 RJ 号
    worknos = []
    for subdir in subdirs:
        workno = get_workno(subdir.name)
        if workno:
            if time_range:
                # 获取文件夹修改时间
                modify_timestamp = os.path.getmtime(subdir)
                modify_time = time.strftime("%Y%m%d%H%M%S", time.localtime(modify_timestamp))

                # 判断文件夹修改时间是否在指定时间范围内
                if len(time_range) == 1 and modify_time >= time_range[0]:
                    worknos.append((subdir, workno))
                elif len(time_range) == 2 and time_range[0] <= modify_time <= time_range[1]:
                    worknos.append((subdir, workno))
            else:
                worknos.append((subdir, workno))

    # 按 RJ 号排序
    worknos.sort(key=lambda x: x[1])

    # 遍历排序后的文件夹列表
    for subdir, workno in worknos:
        if w2f:
            wav_to_flac(subdir)
        if w2m:
            wav_to_mp3(subdir)
        if a2m:
            avi_to_mp4(subdir)  # 调用新增的函数，将 avi 转为 mp4
        tag(subdir, workno)


def main():
    parser = argparse.ArgumentParser(prog="dvtag", description="Doujin Voice Tagging Tool (tagging in place)")
    parser.add_argument("-v", "--version", action="version", version=version(parser.prog))
    parser.add_argument("dirpath", type=str, help="a required directory path")
    parser.add_argument(
        "-w2f", default=False, action=argparse.BooleanOptionalAction, help="transcode all wav files to flac [LOSELESS]"
    )
    parser.add_argument(
        "-w2m", default=False, action=argparse.BooleanOptionalAction, help="transcode all wav files to mp3 1 "
    )
    parser.add_argument(
        "-a2m", default=False, action=argparse.BooleanOptionalAction, help="transcode all avi files to mp4"
    )
    parser.add_argument(
        "--time", "-t", type=str, help="specify the time range to filter directories, format: YYYYMMDDHHMMSS or YYYYMMDDHHMMSS-YYYYMMDDHHMMSS"
    )

    args = parser.parse_args()
    path = Path(args.dirpath).absolute()

    time_range = None
    if args.time:
        time_range = args.time.split("-")
        for i, t in enumerate(time_range):
            try:
                time.strptime(t, "%Y%m%d%H%M%S")
                time_range[i] = t
            except ValueError:
                raise ValueError("Invalid time format. Please use YYYYMMDDHHMMSS or YYYYMMDDHHMMSS-YYYYMMDDHHMMSS")

    start(path, args.w2f, args.w2m, time_range, args.a2m)


if __name__ == "__main__":
    main()
