# 카라마조프 가의 형제들: 인물과 어휘의 네트워크

도스토옙스키의 『카라마조프 가의 형제들』로 등장인물 네트워크와 인물별 어휘 네트워크를 만들고, 그 결과에서 출발해 짧은 이야기를 새로 썼습니다. 홍익대학교 「언어의미와정보」 토이 프로젝트입니다(김지훈, 2026년 11월).

**결과 페이지: [jihoon42.github.io/The-Brothers-Karamazov](https://jihoon42.github.io/The-Brothers-Karamazov/)**

설치 없이 브라우저에서 바로 열립니다. 인물을 누르면 곁에 자주 나오는 인물과 그 인물에게 붙는 낱말이 열리고, 인물을 끌어서 자리를 옮길 수도 있습니다. 함께 나온 단위(문장, 문단, 장)와 권, 최소 횟수를 바꿔 볼 수 있고, 수업 코드를 그대로 돌린 결과와 표로 된 자료도 같은 페이지에서 볼 수 있습니다.

## 과제 항목과 결과물

| 과제 | 결과물 |
|---|---|
| 1. 읽은 책의 네트워크 분석 | Constance Garnett 영역본(1912) 전체: 96장, 5,830문단, 349,323단어 |
| 2. 등장인물 사이의 네트워크 | 결과 페이지, `results/network/` |
| 3. 인물별 어휘 네트워크 (명사, 동사, 형용사의 사전형) | 결과 페이지에서 인물을 누르면 열림, `results/words/` |
| 4. 작은 네트워크로 만든 새 이야기 | [「항아리」](story/hangari.md) |
| 5. 코드, 텍스트 파일, 결과 | 이 저장소 |

## 무엇을 했나

- **수업 코드를 먼저 그대로 돌렸습니다.** 대문자로 시작하는 낱말 1,080개가 인물 후보로 잡혔고, 네트워크에 남은 57개 노드 가운데 인물 이름은 31개였습니다. 나머지는 Fyodorovitch, Ivanovna 같은 이름 조각 10개와 God, Thou, Moscow 같은 인물 아닌 말 16개였고, 알료샤 한 사람이 네 노드로 나뉘기도 했습니다. 이 결과는 `results/baseline_class/`에 그대로 남겨 두었습니다.
- **별칭표를 만들어 인물을 다시 찾았습니다.** 70명의 이름, 별칭, 호칭을 `data/characters.csv`에 정리하고, 본문에서 인물이 불린 자리 8,522곳을 찾았습니다.
- **같은 문단에 함께 나온 인물을 이었습니다.** 두 번 이상 함께 나온 쌍만 이어 64명, 343쌍의 네트워크를 얻었습니다. Louvain으로 나눈 묶음은 알료샤 쪽 22명, 미챠 쪽 20명, 콜랴 쪽 14명, 표도르 쪽 8명입니다. 제목은 '형제들'이지만 알료샤와 이반은 같은 묶음에, 미챠는 다른 묶음에 있습니다. 묶음 사이를 잇는 정도를 나타내는 매개 중심성은 알료샤 0.65, 미챠 0.63, 콜랴 0.26 순입니다. 같은 방법으로 문장 단위와 장 단위 네트워크도 만들어 견주었습니다.
- **인물마다 붙는 낱말을 모았습니다.** spaCy로 품사와 사전형(lemma)을 붙이고, 인물 이름이 나온 문장의 명사, 동사, 형용사를 세 가지 방식으로 골랐습니다. 빈도순(수업 방식), 그 인물에게 유난히 많은 말(keyness), 문장 구조(인물이 주어일 때의 동사, 인물에게 붙는 형용사 등)입니다.
- **「대심문관」 장의 작은 네트워크로 이야기를 썼습니다.** 문단 네트워크에서 대심문관은 이반, 알료샤, 그리스도하고만 이어집니다. 결과 파일에는 개 페레즈본에서 대심문관까지 가는 가장 짧은 길(페레즈본, 콜랴, 알료샤, 이반, 대심문관)도 남아 있습니다. 이야기는 이 길을 거꾸로 따라, 이반이 지은 서사시를 알료샤가 콜랴에게 들려주는 틀로 짰고, 여기에 도마복음을 더해 원작에 없는 하룻밤을 썼습니다.

## 폴더 구성

| 경로 | 내용 |
|---|---|
| `web/index.html` | 결과 페이지. GitHub Pages로 그대로 공개됩니다 |
| `analysis/` | 분석 스크립트 01~07, 공용 모듈 `bknet.py`, 페이지 틀 `web_template.html` |
| `data/` | 받은 그대로의 원문(`raw/`), 정리한 본문과 문단·장 표, 손으로 만든 별칭표 `characters.csv` |
| `results/` | 스크립트가 만든 결과: 인물 네트워크(`network/`), 낱말(`words/`), 수업 코드 결과(`baseline_class/`) |
| `class_code/` | 수업에서 받은 실습 노트북 |
| `story/` | 4번 이야기 |
| `docs/` | 진행 기록, Claude Code에 준 작업 지시문(`prompts/`), 정적 그림 |
| `brothers-karamazov.pdf` | 같은 판본을 조판한 PDF. `02_check_pdf.py`가 본문을 대조할 때 씁니다 |

## 다시 돌려 보기

macOS, Python 3.12, uv 기준입니다. 패키지 버전은 `requirements.txt`에 고정해 두었습니다.

```sh
uv venv --python 3.12
uv pip install -r requirements.txt
.venv/bin/python -m nltk.downloader punkt_tab stopwords
brew install poppler                            # 02에만 필요합니다

.venv/bin/python analysis/01_prepare_text.py    # 원문 정리, 문단·장 표
.venv/bin/python analysis/02_check_pdf.py       # PDF와 단어 단위 대조
.venv/bin/python analysis/04_network.py         # 인물 네트워크, 중심성, 묶음
.venv/bin/python analysis/05_words.py           # 인물별 낱말 (처음에는 본문 분석에 시간이 걸립니다)
.venv/bin/python analysis/06_layout.py          # 노드 배치와 정적 그림
.venv/bin/python analysis/07_build_web.py       # web/index.html
```

`03_baseline_class.py`는 수업 코드를 고치지 않고 돌리는 스크립트입니다. 결과가 Python 버전과 실행 환경에 따라 달라지기 때문에, `results/baseline_class/`에는 처음 돌린 결과(Python 3.10)를 그대로 두었습니다.

## 한계

- 대명사는 풀지 않았습니다. 인물이 이름이나 호칭으로 불린 자리만 셉니다.
- 대화에서는 말하는 사람과 듣는 사람의 이름이 서로 다른 문단에 나오는 일이 많아서, 문단 공출현으로는 누가 누구와 이야기하는지를 다 잡지 못합니다.
- 품사와 사전형은 현대 영어용 작은 모델(spaCy `en_core_web_sm`)로 붙였습니다. 본문은 1912년 번역이고, 「대심문관」 장에는 Thou, hast 같은 옛 2인칭 표현이 많습니다.

## 출처와 작업 방식

- 본문: Project Gutenberg #28054, Constance Garnett 영역(1912). `data/raw/`에 받은 그대로 두었습니다.
- 이 프로젝트는 Anthropic의 Claude와 협업해 진행했습니다. 분석 설계와 코드, 문서, 이야기 초안은 claude.ai에서 함께 만들었고, 맥에서의 실행과 커밋은 Claude Code와 함께 했습니다. Claude Code에 준 작업 지시문은 `docs/prompts/`에 남겨 두었습니다.
