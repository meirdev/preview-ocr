import csv
import dataclasses
from collections import defaultdict
from enum import Enum
from typing import DefaultDict

import pytesseract
from PIL import Image


class Language(str, Enum):
    heb = "heb"
    eng = "eng"


@dataclasses.dataclass
class Text:
    level: int
    page: int
    block: int
    paragraph: int
    line: int
    word: int
    left: float
    top: float
    width: float
    height: float
    conf: str
    text: str

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Text":
        return cls(
            level=int(row["level"]),
            page=int(row["page_num"]),
            block=int(row["block_num"]),
            paragraph=int(row["par_num"]),
            line=int(row["line_num"]),
            word=int(row["word_num"]),
            left=float(row["left"]),
            top=float(row["top"]),
            width=float(row["width"]),
            height=float(row["height"]),
            conf=row["conf"],
            text=row["text"],
        )


def get_text(filename: str, include_empty: bool = False, lang: list[str] = ["eng", "heb"]) -> list[Text]:
    with Image.open(filename) as image:
        data = pytesseract.image_to_data(image, "+".join(lang))

    text = map(Text.from_row, csv.DictReader(data.splitlines(), delimiter="\t"))

    if not include_empty:
        text = filter(lambda i: i.text.strip(), text)

    return list(text)


def fix_size_and_position(text: list[Text]) -> None:
    group_by_line: DefaultDict[tuple[int, int, int, int], list[Text]] = defaultdict(list)
    for i in text:
        group_by_line[(i.page, i.paragraph, i.block, i.line)].append(i)

    for group in group_by_line.values():
        height = max(i.height for i in group)
        top = min(i.top for i in group)

        # prev_i = None
        for i in group:
            i.height = height
            i.top = top

            # if prev_i:
                # eng
                # prev_i.width = i.left - prev_i.left
                # heb
                # i.width = prev_i.left - i.left

            # prev_i = i


def get_plain_text(text: list[Text]) -> str:
    if len(text) == 0:
        return ""

    plain_text = []

    line = None
    for i in text:
        if line != i.line:
            sep, line = "\n", i.line
        else:
            sep = " "

        plain_text += [sep, i.text]

    return "".join(plain_text).strip()
