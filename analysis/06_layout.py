#!/usr/bin/env python3
"""06_layout.py : 네트워크 그림의 노드 자리를 정하고 정지 그림을 그린다

문단 단위 네트워크의 묶음(커뮤니티)마다 원을 하나 잡고 그 안에서 Kamada-Kawai 로 자리를 정한 뒤,
이름표가 겹치지 않게 조금씩 밀어낸다.
자리는 results/network/layout.csv 에 저장해 웹 페이지와 그림이 같은 배치를 쓴다.
단위(문장/문단/장)나 권을 바꿔도 노드는 제자리에 있어야 변화가 눈에 들어오기 때문이다.
"""
import json
import math
import sys
import zlib
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bknet

NET = bknet.RESULTS / "network"
FIG = bknet.ROOT / "docs" / "figs"
W, H = 1400.0, 1000.0          # 그림 좌표계
SEED = 3

# 커뮤니티 색은 그 묶음에 누가 들어 있는가로 정한다 (묶음 번호나 크기가 아니라).
# 세 가지 색은 색각 이상 시뮬레이션에서 모든 쌍이 구별되는 조합이고, 넷째 묶음은 무채색과 네모로 가른다.
ANCHORS = ["alyosha", "mitya", "kolya", "fyodor"]
SLOT_COLOR = {"alyosha": "#2a78d6", "mitya": "#eb6834", "kolya": "#1baf7a", "fyodor": "#6b6a66"}


def community_slots(part: dict, strength: dict) -> dict:
    """community 번호 -> slot 이름(alyosha/mitya/kolya/fyodor). 닻이 되는 인물이 든 묶음이 그 색을 갖는다."""
    comms = {}
    for v, k in part.items():
        comms.setdefault(k, []).append(v)
    slot_of, used = {}, set()
    for a in ANCHORS:
        k = part.get(a)
        if k is not None and k not in slot_of:
            slot_of[k] = a
            used.add(a)
    free = [a for a in ANCHORS if a not in used]
    for k in sorted(comms, key=lambda k: -sum(strength.get(v, 0) for v in comms[k])):
        if k not in slot_of:
            slot_of[k] = free.pop(0) if free else "fyodor"
    return slot_of


def separate(pos, boxes, iters=400, pad=6.0):
    """이름표 상자가 겹치면 서로 밀어낸다."""
    ids = list(pos)
    p = {v: np.array(pos[v], dtype=float) for v in ids}
    for _ in range(iters):
        moved = False
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                dx, dy = p[b] - p[a]
                ox = (boxes[a][0] + boxes[b][0]) / 2 + pad - abs(dx)
                oy = (boxes[a][1] + boxes[b][1]) / 2 + pad - abs(dy)
                if ox > 0 and oy > 0:
                    moved = True
                    if ox * 0.6 < oy:
                        s = ox / 2 * (1 if dx >= 0 else -1)
                        p[a][0] -= s; p[b][0] += s
                    else:
                        s = oy / 2 * (1 if dy >= 0 else -1)
                        p[a][1] -= s; p[b][1] += s
        if not moved:
            break
    return {v: (float(p[v][0]), float(p[v][1])) for v in ids}


def induced(G, nodes):
    """노드 순서를 이름순으로 고정한 부분 그래프. networkx 의 subgraph 는 집합 순서를 따라가서
    실행할 때마다 배치가 달라질 수 있다."""
    H = nx.Graph()
    H.add_nodes_from(sorted(nodes))
    H.add_edges_from((u, v, d) for u, v, d in G.edges(data=True) if u in H and v in H)
    return H


def community_layout(G, part, strength):
    """묶음마다 원 하나를 잡아 그 안에서 자리를 정한 뒤, 다른 묶음과 많이 이어진 인물을 그쪽 가장자리로 당긴다."""
    comms = {}
    for v, k in part.items():
        comms.setdefault(k, []).append(v)
    n_total = sum(len(m) for m in comms.values())
    base = math.sqrt(0.50 * W * H / (math.pi * n_total))
    R = {k: base * math.sqrt(len(m)) for k, m in comms.items()}

    # 묶음끼리의 자리: 묶음 사이 공출현이 많을수록 가깝게
    MG = nx.Graph()
    MG.add_nodes_from(comms)
    for u, v, d in G.edges(data=True):
        cu, cv = part[u], part[v]
        if cu != cv:
            w = MG.get_edge_data(cu, cv, {"weight": 0})["weight"] + d["weight"]
            MG.add_edge(cu, cv, weight=w)
    for a, b in MG.edges():
        MG[a][b]["distance"] = 1.0 / math.log1p(MG[a][b]["weight"])
    cpos = nx.kamada_kawai_layout(MG, weight="distance") if MG.number_of_edges() else nx.circular_layout(MG)
    cpos = {k: np.array(p) * 420.0 for k, p in cpos.items()}
    for _ in range(600):                       # 원이 겹치지 않을 때까지 밀고, 너무 벌어지지 않게 가운데로 당긴다
        for a in comms:
            for b in comms:
                if a < b:
                    d = cpos[b] - cpos[a]
                    dist = float(np.hypot(*d)) or 1e-6
                    need = R[a] + R[b] + 26
                    if dist < need:
                        push = (need - dist) / 2 * d / dist
                        cpos[a] -= push; cpos[b] += push
        centre = sum(cpos.values()) / len(cpos)
        for a in comms:
            cpos[a] -= 0.004 * (cpos[a] - centre)

    pos = {}
    for k, members in comms.items():
        sub = induced(G, members)
        local = {}
        for comp in sorted(nx.connected_components(sub), key=lambda c: sorted(c)[0]):
            cg = induced(sub, comp)
            if len(comp) == 1:
                local[next(iter(comp))] = np.array([0.0, 0.0])
            else:
                kk = nx.kamada_kawai_layout(cg, weight="distance")
                local.update({v: np.array(p) for v, p in kk.items()})
        pts = np.array([local[v] for v in members])
        pts -= pts.mean(axis=0)
        rmax = max(np.hypot(pts[:, 0], pts[:, 1]).max(), 1e-6)
        for v, pt in zip(members, pts):
            pos[v] = cpos[k] + pt / rmax * R[k] * 0.86
    # 다른 묶음과의 연결이 많은 인물은 그 묶음 쪽으로
    for v in list(pos):
        total = sum(d["weight"] for _, _, d in G.edges(v, data=True)) or 1.0
        pull = np.zeros(2)
        for _, u, d in G.edges(v, data=True):
            if part[u] != part[v]:
                direction = cpos[part[u]] - cpos[part[v]]
                pull += d["weight"] / total * direction / (np.hypot(*direction) or 1.0)
        pos[v] = pos[v] + pull * R[part[v]] * 0.9
    # 한두 사람하고만 이어진 인물은 가장 가까운 상대 곁의 빈자리로 옮긴다
    deg = dict(G.degree())
    leaves = [v for v in G if deg[v] <= 2]
    anchor = {v: max(G[v], key=lambda u: G[v][u]["weight"]) for v in leaves}
    rng = np.random.default_rng(SEED)
    for v in leaves:
        pos[v] = pos[anchor[v]] + rng.normal(0, 30, 2)
    others = list(pos)
    for _ in range(300):
        for v in leaves:
            u = anchor[v]
            d = pos[v] - pos[u]
            dist = float(np.hypot(*d)) or 1e-6
            pos[v] = pos[v] + (64.0 - dist) * 0.25 * d / dist          # 상대에게서 일정한 거리
            for w in others:
                if w is v:
                    continue
                d2 = pos[v] - pos[w]
                dist2 = float(np.hypot(*d2)) or 1e-6
                if dist2 < 58.0 and w != u:
                    pos[v] = pos[v] + (58.0 - dist2) * 0.5 * d2 / dist2  # 다른 노드는 피한다
    return {v: (float(p[0]), float(p[1])) for v, p in pos.items()}, {k: (float(c[0]), float(c[1]), R[k]) for k, c in cpos.items()}


def place_labels(pos, radius, font, names, order):
    """이름표를 큰 노드부터 놓는다. 아래, 위, 오른쪽, 왼쪽 가운데 다른 것과 덜 겹치는 자리를 고른다."""
    placed, out = [], {}
    def box(cx, cy, w, h):
        return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    def overlap(a, b):
        return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    node_boxes = {v: box(pos[v][0], pos[v][1], 2 * radius[v] + 2, 2 * radius[v] + 2) for v in pos}
    for v in order:
        x, y = pos[v]
        w = len(names[v]) * font[v] * 0.60 + 4
        h = font[v] * 1.25
        r = radius[v]
        cands = [("below", x, y + r + h / 2 + 2), ("above", x, y - r - h / 2 - 2),
                 ("right", x + r + w / 2 + 4, y), ("left", x - r - w / 2 - 4, y)]
        best = None
        for where, cx, cy in cands:
            b = box(cx, cy, w, h)
            cost = sum(overlap(b, q) for q in placed) + sum(overlap(b, nb) for u, nb in node_boxes.items() if u != v)
            if best is None or cost < best[0] - 1e-9:
                best = (cost, where, cx, cy, b)
            if cost == 0:
                break
        placed.append(best[4])
        out[v] = (best[1], best[2], best[3], best[0])
    return out


def fit(pos, margin=70.0, extra=None):
    xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
    sx = (W - 2 * margin) / (max(xs) - min(xs)); sy = (H - 2 * margin) / (max(ys) - min(ys))
    s = min(sx, sy)
    sx, sy = min(sx, 1.5 * s), min(sy, 1.5 * s)      # 화면을 채우되 한쪽으로 1.5배 넘게 늘이지는 않는다
    ox = (W - sx * (max(xs) - min(xs))) / 2; oy = (H - sy * (max(ys) - min(ys))) / 2
    return {v: (ox + (p[0] - min(xs)) * sx, oy + (p[1] - min(ys)) * sy) for v, p in pos.items()}


def main():
    nodes = pd.read_csv(NET / "nodes.csv", index_col=0)
    E = pd.read_csv(NET / "edges_paragraph.csv")
    G = bknet.build_graph(E, threshold=1)
    giant = induced(G, max(nx.connected_components(G), key=len))
    part = nodes["community"].dropna().astype(int).to_dict()
    strength = nodes["strength"].fillna(0).to_dict()
    smax = max(strength.values())
    pos, _ = community_layout(giant, part, strength)

    # 방향을 고정한다: 알료샤 쪽 묶음을 왼편, 미챠 쪽 묶음을 오른편에 두고 아버지의 집이 위로 오게 뒤집는다
    ids = sorted(pos)
    pts = np.array([pos[v] for v in ids])
    centre = lambda anchor: pts[[i for i, v in enumerate(ids) if part[v] == part[anchor]]].mean(axis=0)
    ca, cm = centre("alyosha"), centre("mitya")
    ang = math.atan2(cm[1] - ca[1], cm[0] - ca[0])
    rot = np.array([[math.cos(-ang), -math.sin(-ang)], [math.sin(-ang), math.cos(-ang)]])
    pts = (pts - (ca + cm) / 2) @ rot.T
    cf = pts[[i for i, v in enumerate(ids) if part[v] == part["fyodor"]]].mean(axis=0)
    if cf[1] > 0:
        pts[:, 1] *= -1
    pos = fit({v: (pts[i, 0], pts[i, 1]) for i, v in enumerate(ids)})

    radius = {v: 5 + 21 * math.sqrt(strength.get(v, 0) / smax) for v in nodes.index}
    font = {v: 10.5 + 13 * math.sqrt(strength.get(v, 0) / smax) for v in nodes.index}
    boxes = {v: (max(2 * radius[v], len(nodes.loc[v, "name"]) * font[v] * 0.42), 2 * radius[v] + font[v] * 1.1) for v in nodes.index}
    pos = separate(pos, boxes, iters=600)
    pos = fit(pos)
    pos = separate(pos, boxes, iters=300)

    # 두 번 이상 함께 나온 상대가 없는 인물: 한 번 함께 나온 상대가 있으면 그 곁에, 없으면 아래쪽 줄에
    loose = [v for v in nodes.index if v not in pos]
    tray = []
    for v in loose:
        cand = E[((E.source == v) & E.target.isin(pos)) | ((E.target == v) & E.source.isin(pos))].sort_values(["value", "source", "target"], ascending=[False, True, True])
        if len(cand):
            r = cand.iloc[0]
            u = r.target if r.source == v else r.source
            ang = (zlib.crc32(v.encode()) % 360) / 180 * math.pi      # 실행마다 같은 자리에 오도록
            pos[v] = (pos[u][0] + (radius[u] + 46) * math.cos(ang), pos[u][1] + (radius[u] + 46) * math.sin(ang))
        else:
            tray.append(v)
    pos = separate(pos, boxes, iters=300)
    pos = fit(pos, margin=80.0)
    for i, v in enumerate(sorted(tray)):
        pos[v] = (W - 110 - 150 * i, H - 42)
    G = giant

    lay = pd.DataFrame({"x": {v: round(p[0], 1) for v, p in pos.items()}, "y": {v: round(p[1], 1) for v, p in pos.items()}})
    lay.index.name = "id"
    lay.to_csv(NET / "layout.csv")

    # ---- 정지 그림
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    slot_of = community_slots(part, strength)
    G = [v for v in nodes.index if v not in tray]
    order = sorted(G, key=lambda v: -strength.get(v, 0))
    labels_at = place_labels({v: pos[v] for v in G}, radius, font, nodes["name"].to_dict(), order)
    fig, ax = plt.subplots(figsize=(14, 10), dpi=150)
    fig.patch.set_facecolor("#fcfcfb"); ax.set_facecolor("#fcfcfb")
    wmax = E.value.max()
    for r in E[E.value >= 2].sort_values(["value", "source", "target"]).itertuples(index=False):
        (x1, y1), (x2, y2) = pos[r.source], pos[r.target]
        same = part.get(r.source) == part.get(r.target)
        col = SLOT_COLOR[slot_of[part[r.source]]] if same and r.source in part else "#898781"
        ax.plot([x1, x2], [y1, y2], color=col, lw=0.4 + 5.0 * math.sqrt(r.value / wmax), alpha=0.18 + 0.5 * (r.value / wmax) ** 0.5,
                solid_capstyle="round", zorder=1)
    for v in G:
        x, y = pos[v]
        slot = slot_of.get(part.get(v), "fyodor")
        col = SLOT_COLOR[slot] if v in part else "#c3c2b7"
        embedded = nodes.loc[v, "kind"] == "embedded"
        marker = "s" if slot == "fyodor" and v in part else "o"
        ax.scatter([x], [y], s=(radius[v] * 1.55) ** 2, marker=marker, facecolor="#fcfcfb" if embedded else col,
                   edgecolor=col if embedded else "#fcfcfb", linewidth=2.2 if embedded else 1.6, zorder=3)
        where, lx, ly, cost = labels_at[v]
        ax.text(lx, ly, nodes.loc[v, "name"], ha="center", va="center", fontsize=font[v] * 0.62,
                color="#0b0b0b" if strength.get(v, 0) > smax * 0.05 else "#52514e", zorder=4,
                fontweight="bold" if strength.get(v, 0) > smax * 0.12 else "normal")
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    handles = []
    labels = {"alyosha": "Alyosha's circle", "mitya": "Mitya's circle", "kolya": "The boys", "fyodor": "The father's house"}
    for slot in ANCHORS:
        if slot in slot_of.values():
            handles.append(plt.Line2D([], [], marker="s" if slot == "fyodor" else "o", color="none", markerfacecolor=SLOT_COLOR[slot],
                                      markeredgecolor="#fcfcfb", markersize=11, label=labels[slot]))
    handles.append(plt.Line2D([], [], marker="o", color="none", markerfacecolor="#fcfcfb", markeredgecolor="#52514e",
                              markeredgewidth=1.8, markersize=10, label="Figure inside an embedded story"))
    ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=10, labelcolor="#52514e")
    ax.set_title("The Brothers Karamazov: characters named in the same paragraph (two or more times)",
                 loc="left", fontsize=13, color="#0b0b0b", pad=10)
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "network_paragraph.png", bbox_inches="tight", facecolor=fig.get_facecolor())
    print("layout nodes", len(pos), "saved", FIG / "network_paragraph.png")
    print("slots", {int(k): v for k, v in slot_of.items()})


if __name__ == "__main__":
    main()
