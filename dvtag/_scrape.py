__all__ = [
    "ParsingError",
    "scrape",
]

import json
import re
from html import unescape
from urllib.parse import urljoin, urlparse

from ._doujin_voice import DoujinVoice
from ._utils import create_request_session

_session = create_request_session()


class ParsingError(Exception):
    """Exception raised when the parsing metadata from web."""

    def __init__(self, message: str, workno: str):
        self.workno = workno
        super().__init__(f"{message} for {workno}")


def _get_200(url):
    rsp = _session.get(url)
    if rsp.status_code != 200:
        rsp.raise_for_status()
    return rsp


def scrape(workno: str) -> DoujinVoice:
    # First visit the URL with the workno from the folder name
    initial_url = f"https://www.dlsite.com/maniax/work/=/product_id/{workno}.html"
    rsp = _get_200(initial_url)

    # 检查是否发生重定向
    if rsp.url == initial_url:
        # 未发生重定向，直接使用 initial_url 并添加 locale 参数
        parsed_url = urlparse(initial_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        url = f"{base_url}?locale=zh_CN"
    else:
        # 发生重定向，按原逻辑处理
        parsed_url = urlparse(rsp.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        url = f"{base_url}?locale=zh_CN"

    # Get the HTML content from the final URL
    html = _get_200(url).text

    if m := re.search(r'data-product-name="(.+)"\s*data-maker-name="(.+)"', html):
        name = unescape(m.group(1))
        circle = unescape(m.group(2))
    else:
        raise ParsingError(f"no work name found", workno)

    if m := re.search(r"\"og:image\"[\s\S]*?content=\"(.+?)\"", html):
        image_url = urljoin("https://www.dlsite.com", unescape(m.group(1)))
    else:
        raise ParsingError(f"no cover image url found", workno)

    seiyus: list[str] = []
    if m := re.search(r"<th>声优</th>[\s\S]*?<td>[\s\S]*?(<a[\s\S]*?>[\s\S]*?)</td>", html):
        seiyu_list_html = m.group(1)
        for seiyu_html in re.finditer(r"<a[\s\S]*?>(.+?)<", seiyu_list_html):
            seiyus.append(unescape(seiyu_html.group(1)))

    genres = [unescape(m[1]) for m in re.finditer(r'work\.genre">(.+)\</a>', html)]

    if m := re.search(r"www\.dlsite\.com/.*?/new/=/year/([0-9]{4})/mon/([0-9]{2})/day/([0-9]{2})/", html):
        sale_date = "{}-{}-{}".format(m.group(1), m.group(2), m.group(3))
    else:
        raise ParsingError(f"no sale date found", workno)

    # Try extracting more accurate information from chobit
    chobit_api = f"https://chobit.cc/api/v1/dlsite/embed?workno={workno}"
    res = _get_200(chobit_api).text

    try:
        data = json.loads(res[9:-1])
        if data["count"]:
            work = data["works"][0]
            if work["file_type"] == "audio":
                image_url = work["thumb"].replace("media.dlsite.com/chobit", "file.chobit.cc", 1)

            # We may get a shorter, yet more accurate article title (with no promotion)
            if work["work_name"] in name:
                name = work["work_name"]

    except Exception as e:
        raise ParsingError("unable to extract metadata from chobit", workno) from e

    return DoujinVoice(
        id=workno, name=name, image_url=image_url, seiyus=seiyus, circle=circle, genres=genres, sale_date=sale_date
    )
