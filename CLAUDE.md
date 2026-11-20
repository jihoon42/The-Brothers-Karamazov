# Karamazov network

Character and word networks of *The Brothers Karamazov* (Constance Garnett's 1912 translation,
Project Gutenberg #28054). It is the toy project of the course 언어의미와정보 at Hongik University,
and one person works on it: JiHoon.

`docs/01-progress.md` records what was decided, what was built and every number that came out.
Read the sections that bear on your task before you start. Section 9 lists known limits,
section 10 what is left, section 12 the environment and what is known about reproducibility.

## The assignment

1. Network analysis of a book of your choice, using the course's 9 November practice code
2. A network of the characters
3. A word network for each character (nouns, verbs, adjectives, as lemmas)
4. A new story of one or two A4 pages, built from a small network
5. Code, text file and results submitted as one .zip

Items 1 to 3 are done for the English text. Still open: item 4 (its material is the Grand
Inquisitor chapter set against the Gospel of Thomas), a comparison with the Russian original,
the zip, and publishing the page for items 1 to 3. Submission is after December. No Colab
notebook is needed; the scripts are submitted as they are.

## How work arrives

Tasks are planned in a claude.ai chat, and the prompt you receive was written there by JiHoon
and Claude together. Long prompts are kept as files under `docs/prompts/`, one per task, with
any patch they need beside them.

Stay inside what the prompt covers. Small fixes needed to finish the task are fine. Anything
beyond the prompt that would change a result, a number quoted in the docs, or
`data/characters.csv` is JiHoon's decision: stop and ask. End each task with a short report of
what changed, which numbers moved and what you could not do.

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
| `docs/01-progress.md` | Progress note: decisions, results, limits, what is left |
| `docs/prompts/` | Prompts from the chat and their patches, kept as a record. Do not edit. |
| `brothers-karamazov.pdf` | The PDF the project started from. 02 checks the text against it. |

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

## Rules

Results

- Same input, same output. Rerunning 04 to 07 must reproduce the files byte for byte on one
  machine, and everything except node positions must match across machines too (positions, and
  so the page and the figure, may differ by under a pixel). To keep that: give every sort an
  explicit tie order (`kind="stable"` or more sort keys), insert nodes in sorted order, use
  `zlib.crc32` rather than `hash()`, fix seeds, round floats when writing.
- Every number in a document comes from a file under `results/`. If a rerun moves a number,
  update the document in the same task and name the change in your report.
- Report what comes out. Do not adjust code or the alias table to make a number match an
  earlier one.

Writing

- Answer JiHoon in the language he writes to you in.
- Documents are in Korean and explain in connected prose (줄글), not in bullet fragments. Tables
  and lists only where the content is a table or a list.
- Keep the register of the file you edit. `docs/01-progress.md` is a working note in plain
  declarative style. Anything written for other readers (a README, the submission, text on the
  web page) uses 존댓말 for prose and noun endings for lists, never 반말.
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
- The community colours were checked for colour-vision deficiency over all pairs. Three hues
  passed, so the fourth community is a neutral grey drawn as squares. Do not add a fourth hue or
  swap a colour without running the same check. The part-of-speech colours passed it too.
- Text takes ink colours, never a series colour. Dark mode is defined under both
  `prefers-color-scheme: dark` and `:root[data-theme="dark"]`. The table view of the same data
  stays available.
