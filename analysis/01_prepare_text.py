#!/usr/bin/env python3
"""01_prepare_text.py : Project Gutenberg #28054 plain text -> 분석용 본문

입력  data/raw/pg28054-0.txt   (The Brothers Karamazov, Constance Garnett 번역, UTF-8)
출력  data/karamazov_garnett.txt  본문만 남긴 텍스트. 문단 하나가 한 줄이고 문단 사이는 빈 줄.
      data/paragraphs.csv          문단마다 한 행 (어느 부, 권, 장에 속하는지 포함)
      data/chapters.csv            장마다 한 행 (문단 수, 단어 수)

하는 일
  1. Project Gutenberg 머리말, 차례, 각주 목록, 라이선스 문구를 잘라 낸다.
  2. 줄바꿈으로 끊긴 문단을 한 줄로 잇는다 (수업 코드는 'Fyodor Pavlovitch'처럼
     이름 사이에 줄바꿈이 끼면 세지 못한다).
  3. 이탤릭 표시(_..._)와 각주 번호((1)~(9))를 지운다.
  4. PART / Book / Chapter 제목을 읽어 문단마다 위치를 붙인다.
"""
import argparse
import csv
import re
from pathlib import Path

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman_to_int(s: str) -> int:
    total = 0
    for ch, nxt in zip(s, s[1:] + " "):
        v = ROMAN[ch]
        total += -v if nxt in ROMAN and ROMAN[nxt] > v else v
    return total


RE_PART = re.compile(r"^PART ([IVX]+)$")
RE_BOOK = re.compile(r"^Book ([IVX]+)\. (.+)$")
RE_CHAP = re.compile(r"^Chapter ([IVXL]+)\. (.+)$")
RE_FOOTREF = re.compile(r"\((\d)\)")

# 받은 PDF(2015년 조판)와 단어 단위로 대조했을 때 달랐던 유일한 곳. PDF 쪽이 고쳐진 판이다.
PATCHES = [("Blurring things out!", "Blurting things out!")]
RE_ITALIC = re.compile(r"_([^_\n]+)_")


def clean_inline(s: str) -> str:
    s = RE_ITALIC.sub(r"\1", s)
    s = s.replace("_", "")
    s = RE_FOOTREF.sub("", s)
    return s


def main() -> None:
    here = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(here / "data/raw/pg28054-0.txt"))
    ap.add_argument("--outdir", default=str(here / "data"))
    args = ap.parse_args()

    raw = Path(args.raw).read_text(encoding="utf-8").replace("\r\n", "\n")
    for a, b in PATCHES:
        assert raw.count(a) == 1, a
        raw = raw.replace(a, b)
    lines = raw.split("\n")

    start = next(i for i, l in enumerate(lines) if l.strip() == "PART I")
    end = next(i for i, l in enumerate(lines) if l.strip() == "FOOTNOTES")
    body = lines[start:end]

    n_footrefs = sum(len(RE_FOOTREF.findall(l)) for l in body)

    # 빈 줄로 끊어 block으로 나눈다
    blocks, cur = [], []
    for l in body:
        if l.strip() == "":
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(l.rstrip())
    if cur:
        blocks.append(cur)

    part = book = chap = 0
    part_label = book_title = chap_title = ""
    paragraphs = []  # dict rows
    out_txt = []
    for blk in blocks:
        first = blk[0].strip()
        joined = " ".join(x.strip() for x in blk)
        m_part = RE_PART.match(first)
        m_book = RE_BOOK.match(joined)
        m_chap = RE_CHAP.match(joined)
        if m_part and len(blk) == 1:
            part = roman_to_int(m_part.group(1))
            part_label = f"Part {m_part.group(1)}"
            out_txt.append(first)
            continue
        if first == "EPILOGUE" and len(blk) == 1:
            part, part_label = 5, "Epilogue"
            book, book_title, chap, chap_title = 13, "Epilogue", 0, ""
            out_txt.append(first)
            continue
        if m_book and not blk[0].startswith(" "):
            book = roman_to_int(m_book.group(1))
            book_title = clean_inline(m_book.group(2)).strip()
            chap, chap_title = 0, ""
            out_txt.append(f"Book {m_book.group(1)}. {book_title}")
            continue
        if m_chap and not blk[0].startswith(" "):
            chap = roman_to_int(m_chap.group(1))
            chap_title = clean_inline(m_chap.group(2)).strip()
            out_txt.append(f"Chapter {m_chap.group(1)}. {chap_title}")
            continue

        indented = all(x.startswith("    ") for x in blk)
        if indented:
            kind = "verse"
            text = "\n".join(clean_inline(x.strip()) for x in blk)
            out_txt.append("\n".join("    " + clean_inline(x.strip()) for x in blk))
        else:
            kind = "prose"
            text = re.sub(r"\s+", " ", clean_inline(joined)).strip()
            out_txt.append(text)
        paragraphs.append(
            dict(pid=len(paragraphs), part=part, part_label=part_label, book=book,
                 book_title=book_title, chapter=chap, chapter_title=chap_title,
                 kind=kind, n_words=len(text.split()), text=text)
        )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "karamazov_garnett.txt").write_text("\n\n".join(out_txt) + "\n", encoding="utf-8")

    with open(outdir / "paragraphs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(paragraphs[0].keys()))
        w.writeheader()
        w.writerows(paragraphs)

    chapters, seen = [], {}
    for p in paragraphs:
        key = (p["book"], p["chapter"])
        if key not in seen:
            seen[key] = dict(seq=len(chapters) + 1, part=p["part"], part_label=p["part_label"],
                             book=p["book"], book_title=p["book_title"], chapter=p["chapter"],
                             chapter_title=p["chapter_title"], first_pid=p["pid"],
                             n_paragraphs=0, n_words=0)
            chapters.append(seen[key])
        seen[key]["n_paragraphs"] += 1
        seen[key]["n_words"] += p["n_words"]
    with open(outdir / "chapters.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(chapters[0].keys()))
        w.writeheader()
        w.writerows(chapters)

    n_words = sum(p["n_words"] for p in paragraphs)
    print(f"paragraphs {len(paragraphs)} (verse {sum(p['kind']=='verse' for p in paragraphs)})")
    print(f"chapters {len(chapters)}  books {len({c['book'] for c in chapters})}  words {n_words}")
    print(f"footnote refs removed {n_footrefs}")
    orphan = [p for p in paragraphs if p["book"] == 0 or (p["chapter"] == 0)]
    print(f"paragraphs outside any chapter: {len(orphan)}")
    for p in orphan[:5]:
        print("   ", p["pid"], p["book"], p["chapter"], p["text"][:70])


if __name__ == "__main__":
    main()
