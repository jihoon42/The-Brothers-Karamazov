# Karamazov network

Character and word networks of *The Brothers Karamazov* (Constance Garnett's 1912 translation,
Project Gutenberg #28054). It is the toy project of the course 언어의미와정보 at Hongik University,
and one person works on it: JiHoon.

What you need for a task is in this file and in the prompt you are given, both in English.
`docs/01-progress.md` is JiHoon's running note, in Korean. It is written and kept up to date in
the chat, from your reports and from the files under `results/`. You do not need to read it and
you do not edit it.

## The assignment

1. Network analysis of a book of your choice, using the course's 9 November practice code
2. A network of the characters
3. A word network for each character (nouns, verbs, adjectives, as lemmas)
4. A new story of one or two A4 pages, built from a small network
5. Code, text file and results submitted as one .zip

Items 1 to 3 are done for the English text, and their page is published from `web/` with GitHub
Pages. Still open: item 4 (its material is the Grand Inquisitor chapter set against the Gospel
of Thomas), a comparison with the Russian original, and the zip. Submission is after December.
No Colab notebook is needed; the scripts are submitted as they are.

## How work arrives

Tasks are planned in a claude.ai chat, and the prompt you receive was written there by JiHoon
and Claude together. Long prompts are kept as files under `docs/prompts/`, one per task, with
any patch they need beside them.

Stay inside what the prompt covers. Small fixes needed to finish the task are fine. Anything
beyond the prompt that would change a result, a number quoted in the docs, or
`data/characters.csv` is JiHoon's decision: stop and ask.

Some files are changed from the chat side before you start (this file, the note, the prompt and
its patch). The prompt names them and says whether they go into your commit.

End each task with a short report in English: what changed, which numbers moved and what you
could not do. The note is updated from that report, so give exact values and the file each one
is in.

## Layout

| Path | What it is |
|---|---|
| `data/raw/pg28054-0.txt` | Source text as downloaded. Never edit. |
| `data/karamazov_garnett.txt`, `data/paragraphs.csv`, `data/chapters.csv` | Clean text and its tables, written by 01 |
| `data/characters.csv` | Alias table for 70 characters, made by hand. The only hand-edited input. |
| `class_code/` | The course notebooks. Never edit. |
| `analysis/` | Scripts 01 to 07, the shared module `bknet.py`, the page template `web_template.html` |
| `results/`, `web/index.html`, `docs/figs/` | Generated. Never edit by hand. |
| `results/baseline_class/` | Output of the class code, kept frozen (see Traps) |
| `docs/01-progress.md` | JiHoon's progress note, in Korean. Kept in the chat. Do not edit. |
| `docs/prompts/` | Prompts from the chat and their patches, kept as a record. Do not edit. |
| `brothers-karamazov.pdf` | The PDF the project started from. 02 checks the text against it. |
| `.github/workflows/pages.yml` | Publishes `web/` with GitHub Pages on every push to main that changes `web/` |

## Environment and running

    uv venv --python 3.12
    uv pip install -r requirements.txt       # exact versions, the spaCy model included
    .venv/bin/python -m nltk.downloader punkt_tab stopwords
    brew install poppler                     # pdftotext, needed only by 02

    .venv/bin/python analysis/01_prepare_text.py   # raw text -> clean text, paragraph and chapter tables
    .venv/bin/python analysis/02_check_pdf.py      # word-by-word check against the PDF: 24 differing spots
    .venv/bin/python analysis/04_network.py        # mentions, co-occurrence networks, centrality, communities
    .venv/bin/python analysis/05_words.py          # word networks per character (the first run parses the text)
    .venv/bin/python analysis/06_layout.py         # node positions and the static figure
    .venv/bin/python analysis/07_build_web.py      # web/index.html (--split DIR writes index.html and data.json apart)

After editing `data/characters.csv`, rerun 04 to 07. After editing `analysis/web_template.html`,
rerun 07.

Numbers that must come out: 5,830 paragraphs, 96 chapters and 349,323 words from 01; 8,522
mentions from 04; in the paragraph network 64 characters, 343 edges and four communities of
22, 20, 14 and 8.

## Known limits of the analysis

These are known and recorded. Do not try to fix one unless a prompt asks for it.

- Pronouns are not resolved. Only places where a character is called by a name or a title count.
- In dialogue the speaker and the listener are often named in different paragraphs, so
  co-occurrence within a paragraph misses much of who talks to whom.
- Paragraphs vary widely in length: the median is 26 words and the longest is 1,794.
- Title aliases (the elder, the old man, the captain) are restricted by chapter in
  `data/characters.csv`, and some wrong matches remain.
- The Christ node is mostly talk about Christ inside other characters' speech.
- The people in Zossima's recollections connect to no one, because the narrator there is "I".
- Parts of speech and lemmas come from `en_core_web_sm`, a small model for modern English, run
  on a 1912 translation. The Grand Inquisitor chapter has archaic second-person verbs.
- The Korean names and one-line descriptions (`name_ko`, `desc_ko`) are drafts.

## Traps

- `03_baseline_class.py` runs the class code unmodified, and the class code's output depends on
  the Python version, the hash seed and the machine. `results/baseline_class/` holds the run that
  the docs and the page describe (Python 3.10.12, PYTHONHASHSEED=0, Linux aarch64). Do not rerun
  03 into it. `BASE_NOT_PERSON` and `BASE_FRAGMENT` in `07_build_web.py` were sorted by hand for
  exactly that run.
- spaCy parses are cached in `~/.cache/bknet/en_core_web_sm/`, in files named only by chunk
  position and number of paragraphs. Delete the cache when the text, the model or the spaCy
  version changes. A different text with the same number of paragraphs would silently read the
  old parses, so give `bknet.parse_paragraphs` its own `cache_dir` for any other text.
- The novel's text uses em dashes and curly quotes. Match those characters, not their ASCII
  look-alikes, when searching it.
- NLTK 3.10 refuses to download its data through a proxy. `NLTK_ALLOW_PROXIED_URLOPEN=1` allows it.
- A pinned version can install and still fail to import on this Mac. scipy 1.15.3 did: its
  macosx_14_0 wheel does not load on macOS 27, which is why scipy is pinned at 1.16.3. After
  changing a pin, import the package before trusting the environment.

## Rules

Results

- Same input, same output. Rerunning 04 to 07 must reproduce the files byte for byte on this
  machine, and the files written by 04 and 05 must match byte for byte on any other machine
  too. To keep that: give every sort an explicit tie order (`kind="stable"` or more sort keys),
  insert nodes in sorted order, use `zlib.crc32` rather than `hash()`, fix seeds, round floats
  when writing.
- Node positions are the exception, by decision. `layout.csv` and what is built from it
  (`web_data.json`, `web/index.html`, the PNG figure) come out differently on other machines
  and under other scipy builds, and that is accepted: positions are only the arrangement the
  page opens with, and on the page a viewer can drag nodes. Do not spend effort on making
  positions match across machines, and do not check them against a reference.
- Every number in a document comes from a file under `results/`. If a rerun moves any number,
  name it in your report with the old value, the new value and the file.
- Report what comes out. Do not adjust code or the alias table to make a number match an
  earlier one.

Writing

- Answer JiHoon in the language he writes to you in. Reports are in English.
- You do not write Korean prose documents. The note, and later the README and the text of the
  submission, are written in the chat. If a task seems to need one, say so in the report.
- Code comments, docstrings and the text on the web page are in Korean, because the submission
  is read in Korean. Keep the register of the file you edit: comments are plain declarative
  sentences, and text on the page uses 존댓말 for sentences and noun endings for labels, never
  반말. When a prompt gives Korean wording, use it as given.
- No em dash (U+2014) anywhere you write: replies, documents, code comments, commit messages.
  Code that needs the character writes `chr(0x2014)`.
- Keep technical terms in English inside Korean text when a translation would read worse
  (co-occurrence, lemma, modularity, PageRank).
- Never describe AI involvement as work handed over (맡겼다). Where the assignment asks for AI
  use to be disclosed, such as a README, describe it as collaboration (협업), and disclose it
  only there.

Git

- Commit only when the prompt or JiHoon asks. Never push unless asked.
- No `Co-Authored-By` line, no `Claude-Session` line and no "Generated with Claude Code" line,
  in commits or in pull requests. This overrides the default attribution.

Web page (`analysis/web_template.html`)

- One self-contained file: vanilla JS and SVG, no libraries, nothing fetched from outside.
- The page is public at https://jihoon42.github.io/The-Brothers-Karamazov/. The workflow
  publishes `web/` and nothing else, on every push to main that changes `web/`, so anything
  written into `web/` is on the web after the next push.
- Positions on the page. `layout.csv` gives the arrangement the page opens with, after one pass
  that only separates overlapping marks. A viewer can drag a character: linked neighbours
  follow, overlapping marks move apart, and a dropped node stays where it was put. Changing the
  unit, the range or the minimum count moves nothing. The button 배치 되돌리기 restores the
  opening arrangement. A press that moves less than 4 px (10 px for touch) is a click and
  selects.
- `render()` rebuilds the whole SVG on every call, and while a drag settles it runs on every
  frame. Anything that must outlive a redraw (pointer capture, drag state, the previous label
  choices) lives on the `<svg>` element or in module state, never on a node element.
- The community colours were checked for colour-vision deficiency over all pairs. Three hues
  passed, so the fourth community is a neutral grey drawn as squares. Do not add a fourth hue or
  swap a colour without running the same check. The part-of-speech colours passed it too.
- Text takes ink colours, never a series colour. Dark mode is defined under both
  `prefers-color-scheme: dark` and `:root[data-theme="dark"]`. The table view of the same data
  stays available.
