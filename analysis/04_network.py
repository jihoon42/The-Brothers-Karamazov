#!/usr/bin/env python3
"""04_network.py : 인물 공출현 네트워크

data/characters.csv 의 별칭표로 본문에서 인물이 불린 자리를 찾고,
문장 / 문단 / 장 단위의 공출현 네트워크를 만든 뒤 중심성과 커뮤니티를 계산한다.
결과는 results/network/ 에 쓴다.
"""
import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bknet

OUT = bknet.RESULTS / "network"
MIN_WEIGHT = 2          # 두 번 이상 함께 나온 쌍만 엣지로 본다
UNITS = {"sentence": dict(min_mentions=1), "paragraph": dict(min_mentions=1), "chapter": dict(min_mentions=2)}
MAIN_UNIT = "paragraph"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    P = bknet.load_paragraphs()
    S = bknet.build_sentences(P)
    C = bknet.load_characters()
    by_id = {c.id: c for c in C}
    M = bknet.find_mentions(P, S, C, layers=("name", "role"))
    M.to_csv(OUT / "mentions.csv", index=False)
    S.drop(columns=["text"]).to_csv(OUT / "sentences_index.csv", index=False)

    summary = dict(
        text=dict(paragraphs=int(len(P)), sentences=int(len(S)), words=int(P.n_words.sum()),
                  chapters=int(P.groupby(["book", "chapter"]).ngroups)),
        characters=len(C), mentions=int(len(M)), mentions_by_layer={k: int(v) for k, v in M.layer.value_counts().items()},
        min_weight=MIN_WEIGHT, main_unit=MAIN_UNIT, units={},
    )

    # ---- 인물별 기본 통계
    nodes = pd.DataFrame([dict(id=c.id, name=c.name, name_ko=c.name_ko, kind=c.kind, group=c.group) for c in C]).set_index("id")
    nodes["mentions"] = M.groupby("char_id").size()
    nodes["mentions_name"] = M[M.layer == "name"].groupby("char_id").size()
    nodes["mentions_role"] = M[M.layer == "role"].groupby("char_id").size()
    nodes["n_sentences"] = M.groupby("char_id").sid.nunique()
    nodes["n_paragraphs"] = M.groupby("char_id").pid.nunique()
    nodes["n_chapters"] = M.groupby("char_id").chap_seq.nunique()
    first = M.sort_values("pid", kind="stable").groupby("char_id").first()
    last = M.sort_values("pid", kind="stable").groupby("char_id").last()
    nodes["first_chapter"] = first.book.astype(str) + "." + first.chapter.astype(str)
    nodes["last_chapter"] = last.book.astype(str) + "." + last.chapter.astype(str)
    for col in ("mentions", "mentions_name", "mentions_role", "n_sentences", "n_paragraphs", "n_chapters"):
        nodes[col] = nodes[col].fillna(0).astype(int)

    by_book = M.groupby(["char_id", "book"]).size().unstack(fill_value=0)
    by_book.to_csv(OUT / "mentions_by_book.csv")

    # ---- 단위별 네트워크
    graphs, cens, parts = {}, {}, {}
    for unit, kw in UNITS.items():
        E = bknet.cooccurrence_edges(M, unit, **kw).sort_values(["value", "source", "target"], ascending=[False, True, True])
        E.to_csv(OUT / f"edges_{unit}.csv", index=False)
        G = bknet.build_graph(E, threshold=MIN_WEIGHT - 1)
        comp = max(nx.connected_components(G), key=len)
        giant = bknet.build_graph(E[E.source.isin(comp) & E.target.isin(comp)], threshold=MIN_WEIGHT - 1)
        part, mod, stab = bknet.communities(giant)
        cen = bknet.centralities(giant)
        graphs[unit], cens[unit], parts[unit] = giant, cen, part
        comm = defaultdict(list)
        for v, k in part.items():
            comm[k].append(v)
        comm_list = []
        for k in sorted(comm):
            mem = sorted(comm[k], key=lambda v: -cen.loc[v, "strength"])
            comm_list.append(dict(index=int(k), label=by_id[mem[0]].name, size=len(mem), members=mem))
        units_multi = int((bknet.find_connections(M, unit).gt(0).sum(axis=1) >= 2).sum())
        summary["units"][unit] = dict(
            pairs_any=int(len(E)), units_with_two_or_more=units_multi,
            nodes=G.number_of_nodes(), edges=G.number_of_edges(), giant_nodes=giant.number_of_nodes(),
            density=round(nx.density(giant), 4), avg_clustering=round(nx.average_clustering(giant), 4),
            modularity=round(mod, 4),
            community_stability={k: round(v, 6) if isinstance(v, float) else v for k, v in stab.items()},
            communities=comm_list,
            top_edges=[(a, b, int(v)) for a, b, v in E.head(25).itertuples(index=False)],
            top={col: [(v, round(float(x), 4)) for v, x in cen[col].sort_values(ascending=False, kind="stable").head(15).items()]
                 for col in ("degree", "strength", "pagerank", "betweenness")},
        )
        suffix = "" if unit == MAIN_UNIT else f"_{unit}"
        for col in cen.columns:
            nodes[col + suffix] = cen[col]
        nodes["community" + suffix] = pd.Series(part)

    # ---- 단위를 바꿔도 결론이 유지되는가
    comp = {}
    for a, b in itertools.combinations(UNITS, 2):
        common = cens[a].index.intersection(cens[b].index)
        ea = {frozenset(e) for e in graphs[a].edges()}
        eb = {frozenset(e) for e in graphs[b].edges()}
        from sklearn.metrics import normalized_mutual_info_score as nmi
        comp[f"{a}_vs_{b}"] = dict(
            common_nodes=len(common),
            spearman={col: round(float(spearmanr(cens[a].loc[common, col], cens[b].loc[common, col]).statistic), 3)
                      for col in ("degree", "strength", "pagerank", "betweenness")},
            edge_jaccard=round(len(ea & eb) / len(ea | eb), 3),
            community_nmi=round(float(nmi([parts[a][v] for v in common], [parts[b][v] for v in common])), 3),
        )
    summary["unit_comparison"] = comp

    # ---- 권별 네트워크 (슬라이더용)
    rows = []
    for unit in ("sentence", "paragraph"):
        for book, mb in M.groupby("book"):
            E = bknet.cooccurrence_edges(mb, unit)
            E.insert(0, "book", book)
            E.insert(0, "unit", unit)
            rows.append(E)
    pd.concat(rows).to_csv(OUT / "edges_by_book.csv", index=False)

    # ---- 수업에서 해 본 분석을 같은 그래프에 (clique, 최단 경로, HITS)
    G = graphs[MAIN_UNIT]
    cliques = sorted(nx.find_cliques(G), key=len, reverse=True)
    hubs, auth = nx.hits(G, max_iter=1000)
    path = nx.dijkstra_path(G, "perezvon", "inquisitor", weight="distance") if {"perezvon", "inquisitor"} <= set(G) else []
    summary["class_style"] = dict(
        largest_clique=sorted(cliques[0], key=lambda v: -cens[MAIN_UNIT].loc[v, "strength"]), largest_clique_size=len(cliques[0]),
        n_largest_cliques=sum(1 for c in cliques if len(c) == len(cliques[0])),
        hits_authority_top=[(v, round(x, 4)) for v, x in sorted(auth.items(), key=lambda t: -t[1])[:8]],
        path_perezvon_to_inquisitor=path,
    )

    # ---- 수업 코드 기준선과 견주기
    base_path = bknet.RESULTS / "baseline_class/summary.json"
    if base_path.exists():
        base = json.loads(base_path.read_text(encoding="utf-8"))
        alias_tokens = defaultdict(set)
        for c in C:
            for sp in c.aliases:
                for tok in sp.text.split():
                    alias_tokens[tok].add(c.id)
        base_nodes = base["nodes_all"]
        covered = {n: sorted(alias_tokens[n]) for n in base_nodes if n in alias_tokens}
        persons_split = Counter(cid for ids in covered.values() for cid in ids)
        summary["baseline_class"] = dict(
            candidates=base["candidates"], nodes=base["nodes"], edges=base["edges"], sentences=base["sentences"],
            nodes_that_are_name_parts=len(covered), nodes_not_persons=sorted(set(base_nodes) - set(covered)),
            persons_split_into_several_nodes={k: v for k, v in persons_split.items() if v > 1},
            distinct_persons_covered=len(persons_split),
        )

    nodes = nodes.sort_values("mentions", ascending=False, kind="stable")
    nodes.round(10).to_csv(OUT / "nodes.csv")
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    name = {c.id: c.name for c in C}
    print(f"mentions {len(M)}  characters with >=1 mention {int((nodes.mentions > 0).sum())}")
    for unit, u in summary["units"].items():
        print(f"[{unit}] nodes {u['nodes']} edges {u['edges']} giant {u['giant_nodes']} density {u['density']} "
              f"clustering {u['avg_clustering']} modularity {u['modularity']} "
              f"communities {[(c['label'], c['size']) for c in u['communities']]}")
    print("unit comparison:", json.dumps(comp))
    print("class-style:", json.dumps(summary["class_style"], ensure_ascii=False))
    print("baseline:", json.dumps({k: v for k, v in summary.get("baseline_class", {}).items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
