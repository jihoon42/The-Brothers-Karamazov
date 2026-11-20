# Prompt 01: move to the Mac, make the results machine-independent

Written on 2026-11-20 in the claude.ai chat, for Claude Code running in this folder.

This project has just moved here from a claude.ai chat workspace. Until now the code has only
run inside a Linux VM. `CLAUDE.md` applies as always. Before you start, read sections 3, 5.1, 10
and 12 of `docs/01-progress.md`.

Goal: make this Mac the place where the pipeline runs, and make its results independent of the
machine they are computed on. Work through the steps in order.

If step 1, 2 or 3 does not go as described, stop and tell me. If a check in step 4 fails, do not
fix anything: finish the remaining checks, skip steps 5 and 6, and report.

## 1. Import commit

The folder is not a git repository yet. Run `git init -b main` and commit everything exactly as
it is, before you change or run anything. Message: `Import project from the chat workspace`.
The Git rules in `CLAUDE.md` hold: no attribution lines, no push.

## 2. Environment

    uv venv --python 3.12
    uv pip install -r requirements.txt
    .venv/bin/python -m nltk.downloader punkt_tab stopwords

`02_check_pdf.py` needs `pdftotext`: run `brew install poppler` if it is missing. If `uv` is
missing or an install fails, stop and tell me instead of choosing another route.

## 3. Patch: an explicit order for ties

    git apply docs/prompts/01-tie-order.patch

The patch gives every sort an explicit tie order, inserts graph nodes in id order, rounds floats
when they are written, and corrects a stale docstring in `06_layout.py`. Section 12.2 of the
progress note explains why. After applying it, the three files must have these md5 values
(`md5 -r` on macOS):

    f99f20227eb71495f467267da4244648  analysis/bknet.py
    51935e65aebde1032552e0ae0615a0b6  analysis/04_network.py
    7ef64a1a946e20749953a3da847920e7  analysis/06_layout.py

## 4. Rerun and check

Run 01, 02, 04, 05, 06 and 07 with `.venv/bin/python`, in that order. Do not run 03:
`results/baseline_class/` stays as it is.

Check each of these and note pass or fail.

a. 01 prints 5830 paragraphs, 96 chapters, 13 books and 349323 words.

b. 02 prints `서로 다른 곳 24군데`. It was written against GNU diff and checked with poppler 22
   and 24. If this Mac gives another count, report the count and the versions of `pdftotext` and
   `diff`, and move on.

c. 04 prints 8522 mentions and, for the paragraph unit, 64 nodes, 343 edges and communities of
   22, 20, 14 and 8.

d. `git status --short` lists exactly these twelve files as modified, and nothing else:

       analysis/bknet.py
       analysis/04_network.py
       analysis/06_layout.py
       results/network/edges_sentence.csv
       results/network/edges_paragraph.csv
       results/network/edges_chapter.csv
       results/network/nodes.csv
       results/network/summary.json
       results/network/layout.csv
       results/web_data.json
       web/index.html
       docs/figs/network_paragraph.png

   Nothing under `data/`, `results/words/` or `results/baseline_class/` may change, nor
   `mentions.csv`, `mentions_by_book.csv`, `sentences_index.csv` or `edges_by_book.csv`.

e. These five files must have these md5 values. They came out identical on two machines (Linux
   aarch64 and x86_64) and under Python 3.10, 3.12 and 3.13:

       51da07428d147edceaba6bc0cfbc18a5  results/network/edges_sentence.csv
       45fcb4cb6d1cefc233bfdce314b4eccc  results/network/edges_paragraph.csv
       93b5601798fcc57c245abd528dfe7fc4  results/network/edges_chapter.csv
       d0f2a1e4de934d6375e0e512f705eeff  results/network/nodes.csv
       0592ff8f32d6312edd63ac7e43902fb9  results/network/summary.json

f. Node positions are allowed to differ between machines by about a pixel. In
   `results/network/layout.csv` these six should hold within 2 px. Report the largest deviation.

       alyosha    333.6  476.6
       mitya      844.5  414.4
       ivan       463.1  391.9
       fyodor     726.9  280.4
       kolya      654.0  739.7
       grushenka 1159.4  561.9

g. Run 04 to 07 a second time. Nothing may change: compare the md5 of every file under
   `results/`, `web/` and `docs/figs/` before and after.

h. Take a headless Chrome screenshot of `web/index.html` at 1440x900 into a temporary folder
   outside the repository and look at it. It should show four communities: the father's house
   (grey squares) at the top, Alyosha's side on the left, Mitya's side on the right, the boys at
   the bottom. If Chrome is not installed, say so and skip this check.

## 5. Update `docs/01-progress.md`

Keep the note's register (plain declarative Korean prose) and write no em dash. Change only
these four places.

- Section 5.1: the NMI mean changes from 0.99 to the value now in
  `results/network/summary.json` under `units.paragraph.community_stability` (expected 0.98).
  The minimum stays 0.90.
- Section 10: remove item 1 (the move to the Mac) and renumber the rest. The item on dialogue
  then says `3번까지` instead of `4번까지`.
- Section 12.2, last paragraph: it says the fix is not in the code yet. Replace that paragraph
  with this, filling in the date:

  > 이 수정은 (날짜)에 맥에서 넣었다. 넣으면서 달라진 것은 두 가지다. 5.1절의 NMI 평균이 0.99에서 0.98이 됐다(최소 0.90과 스무 번 모두 묶음이 넷인 것은 그대로다). 그리고 그림에서 인물 몇의 자리가 바뀌었다. 티모페이, 페르호틴의 심부름꾼 미샤, 페르호틴이 100픽셀 넘게 옮겨 갔고(그림의 폭은 1,400이다) 미챠 쪽 묶음의 안쪽 배열이 달라졌다. 네 묶음의 자리와 방향은 그대로다. 그 밖의 숫자는 바뀌지 않았다.

- Section 12.3: add one paragraph after the existing one that says what was confirmed on this
  Mac. Two to four sentences: the date, the macOS version and chip, the Python version; whether
  the numbers and the five md5 values came out as listed; the largest deviation in check f; what
  02 printed and with which versions of `pdftotext` and `diff`.

## 6. Commit

Message: `Fix tie order so results do not depend on the machine`. It holds the three scripts,
the regenerated results and the progress note.

## Report

The versions you installed or found (Python, uv, poppler, diff), checks a to h with pass or
fail, anything that came out differently, and the two commit hashes.
