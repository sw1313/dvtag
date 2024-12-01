# DVTAG

A command-line tool designed to tag your doujin voice library.照原库修复了图片刮削失败报错的问题，修复mp3不包含ID3 header报错的问题，修复某些特殊中文RJ号会进行二次跳转引导正确的RJ号，添加mp4文件的刮削，修改刮削语言为简中
添加一个配置文件config.ini，可选是否在标题标签添加文件类型后缀和音效后缀，可选是否在流派标签添加中文。如果add_file_type_suffix设置为true，则标题标签添加文件类型后缀，mp3文件后缀添加"-便携版",flac文件后缀添加"-高保真"，如果add_sound_effect_suffix设置为true，则标题标签添加音效后缀，如果文件所在父文件夹含有SE为是的关键词，文件后缀添加"-有音效"，如果文件所在父文件夹含有SE为否的关键词，文件后缀添加"-无音效"，以让在plex等媒体库在拥有同名文件的时候区分文件区别。如果add_chinese_tagx设置为true，则流派标签添加一项"中文"

## How DVTAG Works

DVTAG operates by recursively searching the directory specified by the user. This directory can be a relative path, or even the current directory. It looks for all directories that have a work number in their names.

A work number is a unique identifier from the product link on dlsite, in the format of `RJxxxxxx`, `BJxxxxxx`, or `VJxxxxxx`, where `xxxxxx` can be either 6 or 8 digits.

For every supported audio file format found inside each of these directories, DVTAG uses the corresponding work number to fetch metadata from the web. It then tags the audio files with this metadata.

## Installation

暂时没修改原安装部分，可能需要直接运行main

DVTAG requires Python 3.9 or higher. 

$ dvtag -h
usage: python main.py [-h] [-v] [-w2f] [-w2m] dirpath

Doujin Voice Tagging Tool (tagging in place)

positional arguments:
  dirpath        a required directory path

options:
  -h, --help     show this help message and exit
  -v, --version  show program's version number and exit
  -w2f           transcode all wav files to flac [LOSELESS]
  -w2m           transcode all wav files to mp3

```

Please ensure that every doujin voice folder name contains a specific work number format - like `RJ123123`, `rj123123 xxx`, `xxxx RJ01123123`, `BJ01123123`, `VJ123123`, etc.asmrasmrasmrasmrasmrasmrasmrasmrasmr

To tag your library, use the `dvtag` command:

```bash
python main.py /path/to/your/library
```

## Transcoding

Transcoding is an additional functionality of DVTAG. If you have `wav` audio files and you want to convert these all to `flac` or `mp3`, run with option `-w2f` or `-w2m`. For example:

```bash
python main.py -w2f /path/to/your/library
```

Please note that transcoding depends on ffmpeg and users seeking additional related features should use the ffmpeg tool directly.


