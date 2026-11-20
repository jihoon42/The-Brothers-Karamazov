# Prompt 02: finish the move

Written on 2026-11-20 in the claude.ai chat, for Claude Code running in this folder.

This continues prompt 01, which stopped in step 4: the import commit exists, the tie-order patch
is applied but not committed, and no result has been regenerated. Two things came out of your
report. The pinned scipy wheel does not load on macOS 27, and the node positions from 06 change
with the scipy build by far more than the note assumed.

Decisions taken in the chat:

- scipy is now pinned at 1.16.3. Your dry run showed that the files written by 04 are the same
  under 1.15.3 and 1.16.3, and it installs with the plain command, with no platform flag to
  remember.
- Node positions will not be made identical across machines. They are only the arrangement the
  page opens with, and a later task lets nodes settle and be dragged in the browser. So this
  Mac's positions are taken as they come, check f from prompt 01 is dropped, and `layout.csv`
  and the files built from it are not compared with any reference.

`requirements.txt`, `CLAUDE.md` and `docs/01-progress.md` were already changed from the chat
side. Read section 12 of the progress note again before you start.

An earlier draft of this prompt came with a patch, `docs/prompts/02-exact-layout.patch`, which
rewrote the layout code to make positions exact. That approach was dropped before use. If the
file is still in the folder, delete it. It must not be applied or committed.

If step 1 does not go as described, stop and tell me. If a check in step 2 fails, do not fix
anything: finish the remaining checks, skip steps 3 and 4, and report.

## 1. Environment

    uv pip install -r requirements.txt
    .venv/bin/python -c "import scipy, scipy.sparse, scipy.optimize, scipy.stats, sklearn; print(scipy.__version__)"

The second command must print 1.16.3. No other pinned version may change.

## 2. Rerun and check

Run 04, 05, 06 and 07 with `.venv/bin/python`, in that order. 01 and 02 already passed on this
Mac and are not rerun. Do not run 03.

Check each of these and note pass or fail. The letters follow prompt 01.

c. 04 prints 8522 mentions and, for the paragraph unit, 64 nodes, 343 edges and communities of
   22, 20, 14 and 8.

d. `git status --short` lists exactly these fifteen files as modified and this one as
   untracked, and nothing else:

        M analysis/bknet.py
        M analysis/04_network.py
        M analysis/06_layout.py
        M requirements.txt
        M CLAUDE.md
        M docs/01-progress.md
        M results/network/edges_sentence.csv
        M results/network/edges_paragraph.csv
        M results/network/edges_chapter.csv
        M results/network/nodes.csv
        M results/network/summary.json
        M results/network/layout.csv
        M results/web_data.json
        M web/index.html
        M docs/figs/network_paragraph.png
       ?? docs/prompts/02-finish-move.md

e. These five files must have these md5 values. They came out identical on Linux aarch64 and
   x86_64, under Python 3.10, 3.12 and 3.13, and under scipy 1.15.3 and 1.16.3:

       51da07428d147edceaba6bc0cfbc18a5  results/network/edges_sentence.csv
       45fcb4cb6d1cefc233bfdce314b4eccc  results/network/edges_paragraph.csv
       93b5601798fcc57c245abd528dfe7fc4  results/network/edges_chapter.csv
       d0f2a1e4de934d6375e0e512f705eeff  results/network/nodes.csv
       0592ff8f32d6312edd63ac7e43902fb9  results/network/summary.json

   `layout.csv`, `web_data.json`, `web/index.html` and the PNG have no reference value.

g. Run 04 to 07 a second time. Nothing may change: compare the md5 of every file under
   `results/`, `web/` and `docs/figs/` before and after.

h. Take a headless Chrome screenshot of `web/index.html` at 1440x900 into a temporary folder
   outside the repository and look at it. It should show four communities: the father's house
   (grey squares) at the top, Alyosha's side on the left, Mitya's side on the right, the boys at
   the bottom. Say whether any labels or nodes pile up badly.

## 3. Update `docs/01-progress.md`

Keep the note's register (plain declarative Korean prose) and write no em dash. Change only
these four places.

- Section 5.1: the NMI mean changes from 0.99 to the value now in
  `results/network/summary.json` under `units.paragraph.community_stability` (expected 0.98).
  The minimum stays 0.90.
- Section 10: remove item 1 (the move to the Mac) and renumber the rest. The item on dialogue
  then says `3번까지` instead of `4번까지`.
- Section 12.2, last paragraph (it begins `정렬 순서 수정은 맥의 코드에 들어가 있고`): replace it
  with this, filling in the date.

  > 정렬 순서 수정은 (날짜)에 맥에서 넣고 scipy 1.16.3으로 다시 돌렸다. 달라진 것은 두 가지다. 5.1절의 NMI 평균이 0.99에서 0.98이 됐다(최소 0.90과 스무 번 모두 묶음이 넷인 것은 그대로다). 그리고 그림에서 묶음 안의 배열이 달라졌다. 네 묶음의 자리와 방향은 그대로다. 그 밖의 숫자는 바뀌지 않았다.

- Section 12.3: add one paragraph at the end that says what was confirmed on this Mac in this
  run. Two to four sentences: the date, the scipy version that loaded, whether the printed
  numbers and the five md5 values came out as listed, and that a second run changed nothing.

## 4. Commit

One commit with everything in check d (the fifteen modified files and the new one). Message:
`Fix tie order and pin a scipy that loads on macOS 27`. The Git rules in `CLAUDE.md` hold: no
attribution lines, no push.

## Report

The scipy version that loaded, checks c, d, e, g and h with pass or fail, anything that came out
differently, and the commit hash.
