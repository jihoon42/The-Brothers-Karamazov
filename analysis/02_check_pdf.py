#!/usr/bin/env python3
"""02_check_pdf.py : 분석용 본문이 처음 받은 PDF와 같은 글인지 단어 단위로 대조

brothers-karamazov.pdf (Project Gutenberg #28054 조판본)에서 좌표와 함께 단어를 뽑아
쪽 머리말과 여백의 쪽 표시([012] 등)를 좌표로 걸러 낸 뒤,
data/karamazov_garnett.txt 의 단어열과 GNU diff 로 비교한다.

필요: poppler 의 pdftotext, diff
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PDF = HERE / "brothers-karamazov.pdf"
TXT = HERE / "data/karamazov_garnett.txt"

RE_PAGE = re.compile(r"<page [^>]*>(.*?)</page>", re.S)
RE_LINE = re.compile(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', re.S)
RE_WORD = re.compile(r"<word[^>]*>(.*?)</word>")
DASH = chr(0x2014)      # 본문의 긴 줄표. 낱말을 가를 때 쓴다
ENT = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&apos;": "'"}


def unescape(s: str) -> str:
    for k, v in ENT.items():
        s = s.replace(k, v)
    return s


def norm(w: str) -> str:
    return "".join(ch for ch in w.lower() if ch.isalnum())


def pdf_tokens(tmp: Path):
    out = tmp / "bbox.html"
    subprocess.run(["pdftotext", "-bbox-layout", str(PDF), str(out)], check=True)
    html = out.read_text(encoding="utf-8")
    pages = []
    for pm in RE_PAGE.finditer(html):
        lines = []
        for lm in RE_LINE.finditer(pm.group(1)):
            words = [unescape(w) for w in RE_WORD.findall(lm.group(5))]
            lines.append((float(lm.group(2)), float(lm.group(1)), words))
        pages.append(lines)

    def is_heading(lines, text):
        return any(" ".join(w) == text for _, _, w in lines if _ > 55 or True)

    first = next(i for i, ls in enumerate(pages) if any(" ".join(w) == "Part I" and y > 55 for y, x, w in ls))
    last = next(i for i, ls in enumerate(pages) if i > first and any(" ".join(w) == "Footnotes" and y > 55 for y, x, w in ls))

    words, n_header, n_margin = [], 0, 0
    pending = ""
    for ls in pages[first:last]:
        for y, x, ws in sorted(ls, key=lambda t: (t[0], t[1])):
            if y < 55:              # 쪽 머리말 (쪽 번호, 책 제목, 장 제목)
                n_header += 1
                continue
            ws2 = []
            for w in ws:
                if re.fullmatch(r"\[\d{3}\]", w):   # 여백의 원서 쪽 표시
                    n_margin += 1
                    continue
                ws2.append(w)
            if not ws2:
                continue
            if pending:
                ws2[0] = pending + ws2[0]
                pending = ""
            if ws2[-1].endswith("-") and len(ws2[-1]) > 1:   # 줄 끝 하이픈: 다음 줄 첫 단어와 잇는다
                pending = ws2.pop()
            words.extend(ws2)
    if pending:
        words.append(pending)
    toks = []
    for w in words:
        for piece in w.split(DASH):
            n = norm(piece)
            if n:
                toks.append(n)
    return toks, dict(pages=last - first, header_lines=n_header, margin_marks=n_margin)


def txt_tokens():
    toks = []
    for w in TXT.read_text(encoding="utf-8").split():
        for piece in w.split(DASH):
            n = norm(piece)
            if n:
                toks.append(n)
    return toks


def main():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a, info = pdf_tokens(tmp)
        b = txt_tokens()
        (tmp / "a.txt").write_text("\n".join(a) + "\n", encoding="utf-8")
        (tmp / "b.txt").write_text("\n".join(b) + "\n", encoding="utf-8")
        r = subprocess.run(["diff", str(tmp / "a.txt"), str(tmp / "b.txt")], capture_output=True, text=True)
    print(f"PDF 본문 쪽수 {info['pages']}, 걸러 낸 머리말 줄 {info['header_lines']}, 여백 쪽 표시 {info['margin_marks']}")
    print(f"PDF 단어 {len(a)}  /  본문 텍스트 단어 {len(b)}")
    hunks, cur = [], None
    for line in r.stdout.splitlines():
        if re.match(r"^\d", line):
            cur = dict(head=line, pdf=[], txt=[])
            hunks.append(cur)
        elif line.startswith("< "):
            cur["pdf"].append(line[2:])
        elif line.startswith("> "):
            cur["txt"].append(line[2:])
    print(f"서로 다른 곳 {len(hunks)}군데")
    for h in hunks[:60]:
        print(f"  {h['head']:>18}  PDF: {' '.join(h['pdf'])[:60]!r:<40}  TXT: {' '.join(h['txt'])[:60]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
