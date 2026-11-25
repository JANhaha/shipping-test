"""Extract structured observations from an actively displayed public report graphic."""

import re
import struct
from datetime import datetime
from functools import lru_cache
from urllib.parse import urlsplit

import requests

from data.mysteel_reports import MysteelReportError, REQUEST_HEADERS


MAX_IMAGE_BYTES = 4 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def approved_report_image(candidates, published_at):
    day = datetime.fromisoformat(published_at).strftime("%Y/%m/%d")
    path = re.compile(rf"/wz/uploaded/steel/{day}/[0-9a-f]{{32}}\.png", re.I)
    matches = []
    for candidate in candidates:
        try:
            url = urlsplit(candidate)
        except (TypeError, ValueError):
            continue
        if (url.scheme == "https" and re.fullmatch(r"img\d{2}\.mysteelcdn\.com", url.netloc)
                and not url.query and not url.fragment and path.fullmatch(url.path)):
            matches.append(url.geturl())
    matches = list(dict.fromkeys(matches))
    if len(matches) != 1:
        raise MysteelReportError("No single date-matched public report graphic.")
    return matches[0]


def read_report_image(url):
    headers = {**REQUEST_HEADERS, "Accept": "image/png"}
    try:
        with requests.get(url, headers=headers, timeout=(5, 12), allow_redirects=False, stream=True) as response:
            if response.status_code != 200:
                raise MysteelReportError(f"Report graphic returned HTTP {response.status_code}.")
            if response.headers.get("Content-Type", "").split(";", 1)[0].strip() != "image/png":
                raise MysteelReportError("Report graphic did not return a PNG.")
            data = bytearray()
            for chunk in response.iter_content(chunk_size=32768):
                data.extend(chunk)
                if len(data) > MAX_IMAGE_BYTES:
                    raise MysteelReportError("Report graphic exceeds size limit.")
    except requests.RequestException as error:
        raise MysteelReportError(f"Report graphic request failed ({type(error).__name__}).") from error
    if len(data) < 24 or data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise MysteelReportError("Invalid report graphic header.")
    width, height = struct.unpack(">II", data[16:24])
    if not (600 <= width <= 3000 and width * 1.2 <= height <= 6000 and width * height <= 10_000_000):
        raise MysteelReportError("Unexpected report graphic dimensions.")
    return bytes(data)


@lru_cache(maxsize=1)
def _ocr_engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR(
        det_limit_side_len=4096,
        det_limit_type="max",
        use_cls=False,
        intra_op_num_threads=2,
        inter_op_num_threads=1,
    )


def get_report_groups(image_candidates, published_at):
    url = approved_report_image(image_candidates, published_at)
    image = read_report_image(url)
    try:
        from data.mysteel_market_signals import extract_market_signals
        from data.mysteel_report_tables import extract_report_tables

        cells, _ = _ocr_engine()(image, use_cls=False)
        if not cells:
            raise MysteelReportError("Report graphic did not contain readable cells.")
        result = extract_report_tables(cells, image)
        ordered = sorted(cells, key=lambda cell: min(point[1] for point in cell[0]))
        market_text = "\n".join(text for _, text, confidence in ordered if confidence >= 0.82)
        result["market_signals"] = extract_market_signals(market_text)
    except (ImportError, ValueError, RuntimeError) as error:
        raise MysteelReportError(f"Report graphic extraction failed ({type(error).__name__}).") from error
    if not any(result.get("groups", {}).values()):
        raise MysteelReportError("No validated route quotes in the report graphic.")
    return result
