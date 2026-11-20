#!/usr/bin/env python3
"""07_build_web.py : 결과를 한 파일짜리 웹 페이지로 묶는다

results/ 아래의 표를 모아 JSON 하나로 만들고, analysis/web_template.html 의
/*__DATA__*/ 자리에 넣어 web/index.html 을 쓴다. 페이지는 이 파일 하나로 열리고
바깥으로 나가는 요청이 없다 (글꼴, 라이브러리, 데이터 모두 안에 들어 있다).
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import networkx as nx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bknet

NET = bknet.RESULTS / "network"
WORDS = bknet.RESULTS / "words"
BASE = bknet.RESULTS / "baseline_class"
WEB = bknet.ROOT / "web"
TEMPLATE = Path(__file__).resolve().parent / "web_template.html"
UNITS = ("sentence", "paragraph", "chapter")
TOPW = 14

spec = importlib.util.spec_from_file_location("layout06", Path(__file__).resolve().parent / "06_layout.py")
layout06 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout06)

# 수업 코드가 '등장인물'로 뽑은 57개 낱말을 손으로 가른 것 (PYTHONHASHSEED=0 실행 기준)
BASE_NOT_PERSON = {"Father", "Glory", "God", "Lord", "Madame", "Moscow", "Pan", "President", "Son", "Superior",
                   "Thee", "They", "Thou", "Thy", "Thyself", "You"}
BASE_FRAGMENT = {"Alexandrovna", "Borissovitch", "Fyodorovitch", "Ignatyevna", "Ivanovna", "Karamazov",
                 "Kondratyevna", "Kuzmitch", "Parfenovitch", "Pavlovitch"}


def num(x, nd=4):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), nd)


def build_data():
    nodes = pd.read_csv(NET / "nodes.csv", index_col=0)
    lay = pd.read_csv(NET / "layout.csv", index_col=0)
    by_book = pd.read_csv(NET / "mentions_by_book.csv", index_col=0)
    by_book.columns = [int(c) for c in by_book.columns]
    chapters = bknet.load_chapters()
    chars = {c.id: c for c in bknet.load_characters()}
    summary = json.loads((NET / "summary.json").read_text(encoding="utf-8"))
    ids = list(nodes.index)
    idx = {v: i for i, v in enumerate(ids)}
    books = sorted(chapters.book.unique())

    slots = {}
    for unit in UNITS:
        suffix = "" if unit == summary["main_unit"] else f"_{unit}"
        part = nodes["community" + suffix].dropna().astype(int).to_dict()
        strength = nodes["strength" + suffix].fillna(0).to_dict()
        slot_of = layout06.community_slots(part, strength)
        slots[unit] = {v: slot_of[k] for v, k in part.items()}

    out_nodes = []
    for v in ids:
        r = nodes.loc[v]
        u = {}
        for unit in UNITS:
            suffix = "" if unit == summary["main_unit"] else f"_{unit}"
            if pd.notna(r["strength" + suffix]):
                u[unit] = dict(deg=int(r["degree" + suffix]), str=int(r["strength" + suffix]), pr=num(r["pagerank" + suffix]),
                               btw=num(r["betweenness" + suffix]), c=slots[unit].get(v))
        out_nodes.append(dict(
            id=v, name=r["name"], ko=r["name_ko"], kind=r["kind"], desc=chars[v].desc,
            mentions=int(r["mentions"]), byBook=[int(by_book.loc[v, b]) if v in by_book.index and b in by_book.columns else 0 for b in books],
            first=r["first_chapter"], last=r["last_chapter"], x=float(lay.loc[v, "x"]), y=float(lay.loc[v, "y"]), u=u))

    edges = {}
    for unit in UNITS:
        E = pd.read_csv(NET / f"edges_{unit}.csv")
        edges[unit] = [[idx[a], idx[b], int(w)] for a, b, w in E.itertuples(index=False)]
    EB = pd.read_csv(NET / "edges_by_book.csv")
    edges_by_book = {}
    for (unit, book), g in EB.groupby(["unit", "book"]):
        edges_by_book.setdefault(unit, {})[int(book)] = [[idx[a], idx[b], int(w)] for a, b, w in g[["source", "target", "value"]].itertuples(index=False)]

    comm = {}
    for unit in UNITS:
        groups = {}
        for v, s in slots[unit].items():
            groups.setdefault(s, []).append(v)
        suffix = "" if unit == summary["main_unit"] else f"_{unit}"
        comm[unit] = [dict(slot=s, top=max(m, key=lambda v: nodes.loc[v, "strength" + suffix]), size=len(m))
                      for s, m in sorted(groups.items(), key=lambda kv: layout06.ANCHORS.index(kv[0]))]

    W = json.loads((WORDS / "character_words.json").read_text(encoding="utf-8"))
    words = {}
    for cid, e in W.items():
        syn = e["syntax"]
        adj = {}
        for rel in ("pred_adj", "mod_adj"):
            for w, c, z in syn[rel]:
                adj[w] = adj.get(w, 0) + c
        words[cid] = dict(
            n=e["n_sentences"],
            freq={p: e["freq"][p][:TOPW] for p in ("NOUN", "VERB", "ADJ")},
            key={p: [[w, c] for w, c, z in e["keyness"][p][:TOPW]] for p in ("NOUN", "VERB", "ADJ")},
            syn=dict(subj=[[w, c] for w, c, z in syn["subj_verb"][:TOPW]], obj=[[w, c] for w, c, z in syn["obj_verb"][:TOPW]],
                     adj=sorted(([w, c] for w, c in adj.items()), key=lambda t: -t[1])[:TOPW],
                     poss=[[w, c] for w, c, z in syn["poss_noun"][:TOPW]]))

    # 수업 코드 기준선
    bsum = json.loads((BASE / "summary.json").read_text(encoding="utf-8"))
    BE = pd.read_csv(BASE / "character_interactions.csv")
    BE["source"] = BE["source"].str.strip(); BE["target"] = BE["target"].str.strip()
    BG = nx.Graph()
    for a, b, w in BE.itertuples(index=False):
        BG.add_edge(a, b, weight=int(w))
    bpos = nx.kamada_kawai_layout(BG, weight=None)
    bids = sorted(BG.nodes(), key=lambda v: -BG.degree(v, weight="weight"))
    bidx = {v: i for i, v in enumerate(bids)}
    xs = [p[0] for p in bpos.values()]; ys = [p[1] for p in bpos.values()]
    def sc(p):
        return (90 + (p[0] - min(xs)) / (max(xs) - min(xs)) * (layout06.W - 180), 80 + (p[1] - min(ys)) / (max(ys) - min(ys)) * (layout06.H - 160))
    baseline = dict(
        candidates=bsum["candidates"], sentences=bsum["sentences"],
        nodes=[dict(id=v, x=round(sc(bpos[v])[0], 1), y=round(sc(bpos[v])[1], 1),
                    cat="other" if v in BASE_NOT_PERSON else "fragment" if v in BASE_FRAGMENT else "name") for v in bids],
        edges=[[bidx[a], bidx[b], int(d["weight"])] for a, b, d in BG.edges(data=True)])

    book_rows = chapters.groupby("book").agg(title=("book_title", "first"), words=("n_words", "sum"), chapters=("chapter", "count"))
    meta = dict(text=summary["text"], mentions=summary["mentions"], mentions_by_layer=summary["mentions_by_layer"],
                characters=summary["characters"], min_weight=summary["min_weight"],
                books=[dict(book=int(b), title=r.title, words=int(r.words), chapters=int(r.chapters)) for b, r in book_rows.iterrows()],
                units={u: {k: summary["units"][u][k] for k in ("nodes", "edges", "giant_nodes", "density", "avg_clustering", "modularity", "units_with_two_or_more")}
                       for u in UNITS},
                unit_comparison=summary["unit_comparison"], class_style=summary["class_style"], width=layout06.W, height=layout06.H)
    return dict(meta=meta, nodes=out_nodes, edges=edges, edgesByBook=edges_by_book, communities=comm, words=words, baseline=baseline)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", metavar="DIR", help="index.html 과 data.json 을 따로 쓴다 (웹에 올릴 때)")
    args = ap.parse_args()

    data = build_data()
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    WEB.mkdir(parents=True, exist_ok=True)
    (bknet.RESULTS / "web_data.json").write_text(blob, encoding="utf-8")
    print("data bytes", len(blob.encode("utf-8")), "nodes", len(data["nodes"]), "words for", len(data["words"]))
    html = TEMPLATE.read_text(encoding="utf-8")
    assert html.count("/*__DATA__*/") == 1
    # 한 파일짜리: 더블클릭으로 열리고 제출용 zip 에 넣기 좋다
    (WEB / "index.html").write_text(html.replace("/*__DATA__*/", blob), encoding="utf-8")
    print("wrote", WEB / "index.html", (WEB / "index.html").stat().st_size, "bytes")
    if args.split:
        out = Path(args.split)
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(html.replace("/*__DATA__*/", "null"), encoding="utf-8")
        rows = [json.dumps({"key": k, "value": v}, ensure_ascii=False, separators=(",", ":")) for k, v in data.items()]
        (out / "data.json").write_text("[\n" + ",\n".join(rows) + "\n]\n", encoding="utf-8")
        print("wrote", out / "index.html", "and data.json")


if __name__ == "__main__":
    main()
