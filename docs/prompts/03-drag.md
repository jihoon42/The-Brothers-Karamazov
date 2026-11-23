# Prompt 03: drag characters on the page, and publish the page

Written on 2026-11-21 in the claude.ai chat, for Claude Code running in this folder. Extended on
2026-11-23 with publishing (sections 5 and 6) before it was run.

The start is commit 1b1b7c2 on main, with nothing of yours uncommitted.

## What this is

Two things.

First, on the page, a viewer can now drag a character. This is the follow-up to the decision in
prompt 02 that node positions are only the arrangement the page opens with.

- While a character is dragged, the characters linked to it follow and overlapping marks move
  apart. The others stay where they are.
- A dropped character stays where it was put.
- Changing the unit, the range or the minimum count moves nothing.
- A new button, 배치 되돌리기, restores the opening arrangement.
- A press that moves less than 4 px (10 px for touch) is still a click and selects.

The change is one patch to `analysis/web_template.html`. It was written and tested in the chat
workspace: headless Chrome driven with real mouse and touch input, 58 checks, on a page built
from this repository's `results/web_data.json`. Your part is to apply it, rebuild the page, and
confirm that the page built here is byte for byte the page that was tested.

Second, the page goes on the web with GitHub Pages, under the free github.io address. A
workflow publishes the folder `web/` and nothing else, on every push to main that changes
`web/`. It comes as `docs/prompts/03-pages.yml`, and you copy it to
`.github/workflows/pages.yml` in section 5. Before starting this prompt, JiHoon set the
repository's Pages source to GitHub Actions.

## Changed from the chat side

These are already in the folder:

- `CLAUDE.md`. Read `git diff CLAUDE.md` before anything else. The main change: you work from
  this file and the prompt, in English, and you no longer read or edit `docs/01-progress.md`.
- `docs/01-progress.md`. Updated in the chat for this task. Do not edit it.
- `docs/prompts/03-drag.md` (this file) and `docs/prompts/03-drag.patch`.
- `docs/prompts/03-pages.yml`, the publishing workflow. The chat side cannot write under
  `.github/`, so you copy it there in section 5. It goes into a commit of its own.

If a step does not go as described, stop and report. Do not repair the patch, the template, the
page or the workflow by hand.

## 1. Starting state

`git status --short` must list exactly this:

     M CLAUDE.md
     M docs/01-progress.md
    ?? docs/prompts/03-drag.md
    ?? docs/prompts/03-drag.patch
    ?? docs/prompts/03-pages.yml

and these two files must have these md5 values:

    aa159fec980e50689ddc1e88ab6567c4  analysis/web_template.html
    d1dd8a97c974d5e5885c30500e67ecf8  docs/prompts/03-pages.yml

## 2. Apply and rebuild

    git apply --check docs/prompts/03-drag.patch
    git apply docs/prompts/03-drag.patch
    .venv/bin/python analysis/07_build_web.py

Run only 07. Nothing under `results/network/` or `results/words/` is involved.

## 3. Checks

a. md5 values:

       3c9ad8602f9ca32f9d7e364ce2518b71  analysis/web_template.html
       8d1abdbdd4c64eeeaa2c58f6a06fb6c1  results/web_data.json
       dc7efd1689474d725bd73644085bdcbd  web/index.html

   `results/web_data.json` is the value it already had: the data does not change. The value
   for `web/index.html` is that of the page tested in the chat.

b. `git status --short` lists exactly this:

        M CLAUDE.md
        M analysis/web_template.html
        M docs/01-progress.md
        M web/index.html
       ?? docs/prompts/03-drag.md
       ?? docs/prompts/03-drag.patch
       ?? docs/prompts/03-pages.yml

c. Take a headless Chrome screenshot of `web/index.html` at 1440x900 into a temporary folder
   outside the repository and look at it. The network looks as it did after prompt 02 (the
   father's house at the top, Alyosha's side on the left, Mitya's side on the right, the boys
   at the bottom). At the top right of the picture there are now four buttons, the last one
   배치 되돌리기, drawn faded because nothing has been moved yet. The paragraph under 읽는 법
   ends with 인물을 끌면 자리를 옮길 수 있습니다.

## 4. First commit: the drag

Commit these six files, and only these:

    git add CLAUDE.md analysis/web_template.html docs/01-progress.md web/index.html docs/prompts/03-drag.md docs/prompts/03-drag.patch
    git commit -m "Let viewers drag characters on the page"

## 5. Second commit: the workflow

    mkdir -p .github/workflows
    cp docs/prompts/03-pages.yml .github/workflows/pages.yml
    git add .github/workflows/pages.yml docs/prompts/03-pages.yml
    git commit -m "Publish web/ on GitHub Pages"

`.github/workflows/pages.yml` must have md5 `d1dd8a97c974d5e5885c30500e67ecf8`, and
`git status --short` must now print nothing. The Git rules in `CLAUDE.md` hold for both
commits: no attribution lines.

## 6. Push and check the site

JiHoon asks for the push in this prompt:

    git push

The push starts the workflow. The site is expected at

    https://jihoon42.github.io/The-Brothers-Karamazov/

If `gh` is installed and logged in, follow the run (`gh run list --workflow pages.yml`, then
`gh run watch` on it) and take the address from
`gh api repos/jihoon42/The-Brothers-Karamazov/pages --jq .html_url`. Otherwise poll the address
above every 20 seconds for up to 10 minutes.

d. The address answers 200, and the md5 of the bytes it serves is
   `dc7efd1689474d725bd73644085bdcbd`, the same as `web/index.html`. Fetch it with plain
   `curl -s`, without asking for compression.

If the site does not come up, change nothing and report what you saw, with the run's result if
you can see it. The likely cause is a Pages source that is not set to GitHub Actions: JiHoon sets
it under Settings, Pages and runs the workflow again from the Actions tab (it has a manual
trigger).

## Report

Checks a to d with pass or fail, anything that came out differently, both commit hashes, and
the address the site answers at.

## For later work on this code

How the patch is put together, in case a later task touches it.

- Pointer handling sits on the `<svg>` element, not on the nodes, because `render()` replaces
  every node on each call. One pointer at a time is tracked in `pid`. `grab` is a press on a
  character, `drag` a press on the background (panning, as before).
- A press on a character becomes a drag once it moves past the slop. Until then releasing it
  selects, so selection now happens on `pointerup`. The node's `click` listener remains only
  for clicks that arrive without a pointer press, as assistive technology sends them.
- `simStart` records the current positions as home and starts a small simulation: each node
  is pulled toward its home, linked nodes try to keep the distance they had, overlapping marks
  are pushed apart, and the dragged node is pinned to the pointer. Releasing lets it cool and
  stop. Because home is taken afresh at every drag, earlier moves do not creep back.
- `openLayout` runs once per node set, on its first draw: it only separates overlapping marks
  and stores the result as the opening arrangement that 배치 되돌리기 restores.
- Collision radii are fixed in data coordinates, so the result does not depend on screen size
  or zoom.
- While the simulation runs, a label keeps the side it had in the previous frame unless
  another side is clearly better, and hover is switched off. Without these two, labels jump
  and the picture flickers, since every frame is a full redraw.
- With `prefers-reduced-motion`, there is no animation loop: neighbours move with the pointer
  and the layout finishes at once on release.
- Not done: moving a character with the keyboard.
- Publishing: the workflow uploads `web/` only. Any push to main that changes `web/`
  republishes the page, so whatever is written into `web/` is public after the next push.
