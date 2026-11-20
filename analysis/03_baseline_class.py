#!/usr/bin/env python3
"""03_baseline_class.py : 수업 코드(BookNetworkAnalyzer)를 한 줄도 고치지 않고 카라마조프에 돌린다

class_code/network_characters03_1109.ipynb 에서 class 정의 셀을 그대로 읽어 실행한다.
결과는 results/baseline_class/ 에 남기고, 뒤에서 만드는 네트워크와 비교하는 기준선으로 쓴다.
"""
import csv, json, os, string, sys, tempfile, time, warnings
from collections import Counter

# 수업 코드는 set 의 순서에 따라 후보 인물 수가 달라진다(돌릴 때마다 1,055명, 1,065명 등).
# 기준선 숫자를 다시 만들 수 있도록 hash seed 를 고정한다. 다른 seed 는 PYTHONHASHSEED=1 처럼 준다.
if os.environ.get("PYTHONHASHSEED") is None:
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable] + sys.argv)
from pathlib import Path

import nltk
import numpy as np
import pandas as pd
import spacy
import networkx as nx
from pyvis.network import Network
from IPython.display import HTML, display

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent.parent
NB = HERE / "class_code/network_characters03_1109.ipynb"
BOOK = HERE / "data/karamazov_garnett.txt"
OUT = HERE / "results/baseline_class"


def load_class_source() -> str:
    nb = json.loads(NB.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        src = "".join(cell.get("source", []))
        if cell.get("cell_type") == "code" and src.lstrip().startswith("class BookNetworkAnalyzer"):
            return src
    raise SystemExit("class cell not found")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    os.chdir(tempfile.mkdtemp())       # 수업 코드는 HTML을 현재 폴더에 쓴 뒤 save_dir 로 복사한다
    exec(compile(load_class_source(), str(NB), "exec"), globals())

    t0 = time.time()
    analyzer = BookNetworkAnalyzer()   # noqa: F821  (위 exec 로 정의됨)
    analyzer.load_book(str(BOOK))
    analyzer.get_sentence_sequences()
    analyzer.process_characters()
    n_candidates = len(analyzer.characters)
    analyzer.build_network_data(threshold=2)
    t1 = time.time()

    analyzer.plot_network_by_importance_styling(
        centrality_type="pagerank", node_color="#3498DB",
        apply_importance_size=False, output_filename="styled_network_final.html")
    analyzer.visualize_character_words(
        target_char="Alyosha", top_n=10, apply_importance_size=False,
        output_filename="alyosha_words_network.html")
    analyzer.save_analysis_results(
        save_dir=str(OUT), target_person="Alyosha",
        styled_net_file="styled_network_final.html", target_net_file="alyosha_words_network.html")

    G = analyzer.G
    deg = nx.degree_centrality(G)
    wdeg = analyzer.weighted_degree_centrality
    freq = analyzer.df_connections.sum().to_dict()
    top_deg = sorted(deg.items(), key=lambda x: -x[1])[:30]
    top_w = sorted(wdeg.items(), key=lambda x: -x[1])[:30]
    summary = dict(
        sentences=len(analyzer.sequences), candidates=n_candidates,
        nodes=G.number_of_nodes(), edges=G.number_of_edges(), seconds=round(t1 - t0, 1),
        top_degree=[(k.strip(), round(v, 4)) for k, v in top_deg],
        top_weighted_degree=[(k.strip(), int(v)) for k, v in top_w],
        nodes_all=sorted(n.strip() for n in G.nodes()),
        mention_counts={k.strip(): int(v) for k, v in freq.items() if k in G.nodes()},
    )
    summary["hash_seed"] = os.environ["PYTHONHASHSEED"]
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("sentences", "candidates", "nodes", "edges", "seconds")}))
    print("top degree:", [k for k, _ in summary["top_degree"]])
    print("top weighted:", summary["top_weighted_degree"][:20])
    print("nodes:", summary["nodes_all"])


if __name__ == "__main__":
    main()
