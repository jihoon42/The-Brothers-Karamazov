"""bknet.py : 카라마조프 인물·어휘 네트워크의 공통 함수

수업 코드(Bookworm 노트북, BookNetworkAnalyzer)의 흐름을 그대로 따른다.

    load_book -> get_sentence_sequences -> load_characters -> find_connections
    -> calculate_cooccurence -> get_interaction_df -> networkx -> PyVis

달라진 곳은 세 군데다.

  1. 인물 목록  자동 추출(대문자로 시작하는 고유명사) 대신 손으로 만든 별칭표
                data/characters.csv 를 쓴다. Bookworm 의 load_characters 가 받는
                "한 줄에 한 인물, 쉼표로 별칭" 형식을 넓힌 것이다.
  2. 이름 찾기  'Harry ' 처럼 뒤에 공백이 붙은 문자열을 세는 대신 단어 경계로 찾는다.
                긴 별칭부터 맞추므로 'Fyodor Pavlovitch' 를 'Fyodor' 로 또 세지 않는다.
                별칭마다 적용할 권/장을 정할 수 있다 (Karamazov@10 = 10권에서만).
  3. 공출현 단위  문장(수업 방식)뿐 아니라 문단, 장으로도 센다.
"""
from __future__ import annotations

import bisect
import csv
import itertools
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

import networkx as nx
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"

csv.field_size_limit(10**9)


# --------------------------------------------------------------------------- 본문
def load_book(book_path=DATA / "karamazov_garnett.txt", lower: bool = False) -> str:
    """수업 코드 #01 과 같다."""
    with open(book_path, encoding="utf-8") as f:
        book = f.read()
    return book.lower() if lower else book


def load_paragraphs(path=DATA / "paragraphs.csv") -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    df["text"] = df["text"].astype(str)
    return df


def load_chapters(path=DATA / "chapters.csv") -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8")


_PUNKT = None


def get_sentence_sequences(book: str) -> List[str]:
    """수업 코드 #02 와 같다 (NLTK punkt)."""
    return [book[s:e] for s, e in sentence_spans(book)]


def sentence_spans(text: str) -> List[Tuple[int, int]]:
    global _PUNKT
    if _PUNKT is None:
        import nltk
        _PUNKT = nltk.data.load("tokenizers/punkt/english.pickle")
    return list(_PUNKT.span_tokenize(text))


def build_sentences(paragraphs: pd.DataFrame) -> pd.DataFrame:
    """문단마다 문장으로 잘라 문장 표를 만든다. start/end 는 문단 안의 글자 위치."""
    rows = []
    for p in paragraphs.itertuples(index=False):
        for s, e in sentence_spans(p.text):
            rows.append((len(rows), p.pid, p.book, p.chapter, s, e, p.text[s:e]))
    return pd.DataFrame(rows, columns=["sid", "pid", "book", "chapter", "start", "end", "text"])


# --------------------------------------------------------------------------- 인물과 별칭
@dataclass(frozen=True)
class AliasSpec:
    text: str
    char_id: str
    layer: str                                   # name | role | pronoun
    scope: Optional[FrozenSet[Tuple[int, int]]]  # (권, 장). 장 0 은 그 권 전체. None 은 어디서나

    def applies(self, book: int, chapter: int) -> bool:
        return self.scope is None or (book, 0) in self.scope or (book, chapter) in self.scope


@dataclass
class Character:
    id: str
    name: str
    name_ko: str
    kind: str
    group: str
    aliases: List[AliasSpec] = field(default_factory=list)
    note: str = ""
    desc: str = ""


def _parse_alias(raw: str, char_id: str, layer: str) -> AliasSpec:
    raw = raw.strip()
    if "@" not in raw:
        return AliasSpec(raw, char_id, layer, None)
    text, sc = raw.split("@", 1)
    scope = set()
    for part in sc.split(","):
        part = part.strip()
        if "." in part:
            b, c = part.split(".")
            scope.add((int(b), int(c)))
        else:
            scope.add((int(part), 0))
    return AliasSpec(text.strip(), char_id, layer, frozenset(scope))


def load_characters(path=DATA / "characters.csv") -> List[Character]:
    """별칭표를 읽는다. aliases 는 이름, role_aliases 는 'the elder' 같은 호칭이다."""
    out = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            ch = Character(r["id"], r["name"], r["name_ko"], r["kind"], r["group"], note=r.get("note", ""),
                           desc=r.get("desc_ko", ""))
            for col, layer in (("aliases", "name"), ("role_aliases", "role")):
                for raw in (r.get(col) or "").split(";"):
                    if raw.strip():
                        ch.aliases.append(_parse_alias(raw, ch.id, layer))
            out.append(ch)
    return out


# 대심문관 장(5권 5장)에서 예수는 이름 없이 대문자 대명사로만 불린다.
# 이 규칙은 그 장을 따로 볼 때만 켠다 (layers 에 "pronoun" 을 넣었을 때).
PRONOUN_RULES = [
    ("christ", frozenset({(5, 5)}), re.compile(r"(?<!\w)(Thou|Thee|Thy|Thine|Thyself|Him|Himself)(?!\w)")),
    ("christ", frozenset({(5, 5)}), re.compile(r"(?<=[a-z,;:] )(He|His)(?!\w)")),   # 문장 첫머리의 He 는 뺀다
]

# 인물을 가리키는 것이 아닌 굳은 표현. 찾으면 그 자리를 비워 둔다.
BLOCKERS = ["for Christ’s sake", "Christ’s sake"]


class MentionFinder:
    def __init__(self, characters: Sequence[Character], layers: Iterable[str] = ("name", "role")):
        self.layers = tuple(layers)
        self.specs: Dict[str, List[AliasSpec]] = defaultdict(list)
        for ch in characters:
            for sp in ch.aliases:
                if sp.layer in self.layers:
                    for surface in self._surfaces(sp.text):
                        self.specs[surface].append(sp)
        surfaces = sorted(set(self.specs) | set(BLOCKERS), key=lambda s: (-len(s), s))
        self.regex = re.compile(r"(?<!\w)(" + "|".join(re.escape(s) for s in surfaces) + r")(?!\w)")

    @staticmethod
    def _surfaces(text: str):
        out = {text}
        if text[0].islower():                      # the elder / The elder
            out.add(text[0].upper() + text[1:])
        return out

    def find(self, text: str, book: int, chapter: int):
        """(start, end, char_id, alias, layer) 목록. 같은 자리는 한 번만 쓴다."""
        out = []
        for m in self.regex.finditer(text):
            cands = [sp for sp in self.specs.get(m.group(1), ()) if sp.applies(book, chapter)]
            if not cands:
                continue
            scoped = [sp for sp in cands if sp.scope is not None]
            for sp in (scoped or cands):           # 'the Poles' 처럼 두 사람을 함께 가리키는 별칭은 둘 다
                out.append((m.start(1), m.end(1), sp.char_id, sp.text, sp.layer))
        if "pronoun" in self.layers:
            taken = [(s, e) for s, e, *_ in out]
            for char_id, scope, rx in PRONOUN_RULES:
                if (book, chapter) in scope or (book, 0) in scope:
                    for m in rx.finditer(text):
                        if not any(s <= m.start(1) < e for s, e in taken):
                            out.append((m.start(1), m.end(1), char_id, m.group(1), "pronoun"))
        out.sort()
        return out


def find_mentions(paragraphs: pd.DataFrame, sentences: pd.DataFrame, characters: Sequence[Character],
                  layers: Iterable[str] = ("name", "role")) -> pd.DataFrame:
    """본문 전체에서 인물이 불린 자리를 찾는다. 한 행이 한 번의 언급이다."""
    finder = MentionFinder(characters, layers)
    sent_starts: Dict[int, Tuple[List[int], List[int]]] = {}
    for pid, g in sentences.groupby("pid", sort=False):
        sent_starts[pid] = (g["start"].tolist(), g["sid"].tolist())
    chap_seq = {}
    rows = []
    for p in paragraphs.itertuples(index=False):
        key = (p.book, p.chapter)
        chap_seq.setdefault(key, len(chap_seq) + 1)
        starts, sids = sent_starts.get(p.pid, ([0], [-1]))
        for s, e, cid, alias, layer in finder.find(p.text, p.book, p.chapter):
            sid = sids[max(0, bisect.bisect_right(starts, s) - 1)]
            rows.append((p.pid, sid, p.book, p.chapter, chap_seq[key], cid, alias, layer, s, e))
    return pd.DataFrame(rows, columns=["pid", "sid", "book", "chapter", "chap_seq", "char_id",
                                       "alias", "layer", "start", "end"])


# --------------------------------------------------------------------------- 공출현
UNIT_COLUMN = {"sentence": "sid", "paragraph": "pid", "chapter": "chap_seq"}


def find_connections(mentions: pd.DataFrame, unit: str = "sentence") -> pd.DataFrame:
    """수업 코드 #09 와 같은 표. 행은 단위(문장/문단/장), 열은 인물, 값은 언급 횟수."""
    col = UNIT_COLUMN[unit]
    return mentions.groupby([col, "char_id"]).size().unstack(fill_value=0)


def calculate_cooccurence(df: pd.DataFrame, binary: bool = True, min_mentions: int = 1) -> pd.DataFrame:
    """수업 코드 #10 과 같은 내적. binary=True 면 한 단위에 함께 나온 것을 1번으로 센다
    (수업 코드는 언급 횟수의 곱을 더한다. binary=False 가 그 방식이다)."""
    import numpy as np
    x = df.values
    if binary:
        x = (x >= min_mentions).astype("int64")
    co = x.T.dot(x)
    np.fill_diagonal(co, 0)
    return pd.DataFrame(co, columns=df.columns, index=df.columns)


def get_interaction_df(cooccurence: pd.DataFrame, threshold: int = 0) -> pd.DataFrame:
    """수업 코드 #11 과 같다."""
    import numpy as np
    rows, cols = np.where(np.triu(cooccurence.values, 1) > threshold)
    return pd.DataFrame({"source": cooccurence.index[rows], "target": cooccurence.columns[cols],
                         "value": cooccurence.values[rows, cols].astype(int)})


def cooccurrence_edges(mentions: pd.DataFrame, unit: str = "sentence", min_mentions: int = 1,
                       binary: bool = True) -> pd.DataFrame:
    df = find_connections(mentions, unit)
    return get_interaction_df(calculate_cooccurence(df, binary=binary, min_mentions=min_mentions))


def build_graph(edges: pd.DataFrame, threshold: int = 0) -> nx.Graph:
    g = nx.Graph()
    for r in edges.itertuples(index=False):
        if r.value > threshold:
            g.add_edge(r.source, r.target, weight=int(r.value), distance=1.0 / r.value)
    return g


def centralities(g: nx.Graph) -> pd.DataFrame:
    n = g.number_of_nodes()
    deg = dict(g.degree())
    out = pd.DataFrame({
        "degree": pd.Series(deg),
        "degree_centrality": pd.Series(nx.degree_centrality(g)),
        "strength": pd.Series(dict(g.degree(weight="weight"))),
        "pagerank": pd.Series(nx.pagerank(g, weight="weight")),
        "betweenness": pd.Series(nx.betweenness_centrality(g, weight="distance")),
    })
    try:
        out["eigenvector"] = pd.Series(nx.eigenvector_centrality(g, weight="weight", max_iter=1000))
    except Exception:
        out["eigenvector"] = float("nan")
    return out


def communities(g: nx.Graph, seeds: Sequence[int] = range(20), resolution: float = 1.0):
    """Louvain 을 seed 를 바꿔 여러 번 돌려 modularity 가 가장 높은 분할을 고른다.
    돌릴 때마다 얼마나 달라지는지도 함께 돌려준다 (분할끼리의 NMI)."""
    from sklearn.metrics import normalized_mutual_info_score as nmi
    nodes = sorted(g.nodes())
    parts, mods = [], []
    for s in seeds:
        comms = nx.community.louvain_communities(g, weight="weight", resolution=resolution, seed=s)
        lab = {}
        for i, c in enumerate(sorted(comms, key=lambda c: (-len(c), sorted(c)[0]))):
            for v in c:
                lab[v] = i
        parts.append([lab[v] for v in nodes])
        mods.append(nx.community.modularity(g, comms, weight="weight"))
    best = max(range(len(parts)), key=lambda i: mods[i])
    stab = [nmi(parts[best], p) for i, p in enumerate(parts) if i != best]
    return (dict(zip(nodes, parts[best])), mods[best],
            dict(n_runs=len(parts), modularity_min=min(mods), modularity_max=max(mods),
                 nmi_to_best_mean=sum(stab) / len(stab), nmi_to_best_min=min(stab),
                 n_communities=sorted(Counter(len(set(p)) for p in parts).items())))


# --------------------------------------------------------------------------- 품사·lemma (spaCy)
def parse_paragraphs(paragraphs: pd.DataFrame, model: str = "en_core_web_sm", cache_dir: Optional[Path] = None,
                     n_process: int = 4, chunk: int = 800):
    """문단을 spaCy 로 분석한다. 한 번에 다 돌리면 오래 걸리므로 chunk 단위로 저장해 두고,
    다시 부르면 저장된 것을 읽는다. cache_dir 를 주지 않으면 ~/.cache/bknet 을 쓴다."""
    import spacy
    from spacy.tokens import DocBin
    cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "bknet" / model
    cache_dir.mkdir(parents=True, exist_ok=True)
    nlp = spacy.load(model, disable=["ner"])
    texts = paragraphs["text"].tolist()
    docs = []
    for i in range(0, len(texts), chunk):
        f = cache_dir / f"docs_{i:05d}_{len(texts)}.spacy"
        if f.exists():
            part = list(DocBin().from_disk(f).get_docs(nlp.vocab))
        else:
            part = list(nlp.pipe(texts[i:i + chunk], n_process=n_process, batch_size=40))
            DocBin(docs=part, store_user_data=False).to_disk(f)
        docs.extend(part)
    return docs


def log_odds_z(count_a: Counter, count_b: Counter, prior: Counter, prior_strength: float = 1000.0) -> Dict[str, float]:
    """한 집단(a)에 유난히 많이 나오는 낱말을 가리는 점수 (Monroe, Colaresi & Quinn 2008 의
    informative Dirichlet prior log-odds). 값이 클수록 a 쪽에 치우친 낱말이다. 빈도가 낮아
    우연일 수 있는 낱말은 점수가 작게 나온다."""
    import math
    na, nb, n0 = sum(count_a.values()), sum(count_b.values()), sum(prior.values())
    scale = prior_strength / n0
    a0 = prior_strength
    out = {}
    for w, ya in count_a.items():
        yb = count_b.get(w, 0)
        aw = prior.get(w, 0) * scale + 0.01
        d = (math.log((ya + aw) / (na + a0 - ya - aw)) - math.log((yb + aw) / (nb + a0 - yb - aw)))
        var = 1.0 / (ya + aw) + 1.0 / (yb + aw)
        out[w] = d / math.sqrt(var)
    return out
