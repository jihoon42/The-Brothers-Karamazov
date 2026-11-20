#!/usr/bin/env python3
"""05_words.py : 인물별 어휘 네트워크 (명사, 동사, 형용사의 lemma)

세 가지 방식으로 인물과 낱말을 잇는다.

  freq     수업 방식. 인물이 나온 문장에 함께 나온 낱말을 품사별로 세어 빈도순으로 고른다.
  keyness  같은 자료에서, 다른 문장보다 그 인물의 문장에 유난히 많이 나오는 낱말을 고른다.
           (빈도순으로 뽑으면 say, know, man 같은 말이 모든 인물에게 똑같이 올라온다.)
  syntax   문장 구조로 잇는다. 인물이 주어인 동사, 목적어인 동사, 인물을 꾸미거나 서술하는
           형용사, 인물의 것으로 나오는 명사(Alyosha's face).

결과는 results/words/ 에 쓴다.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bknet

OUT = bknet.RESULTS / "words"
POS = ("NOUN", "VERB", "ADJ")
TOP = 40
MIN_SENTENCES = 8        # 이보다 적게 나온 인물은 어휘 네트워크를 만들지 않는다
SYNTAX_RELS = ("subj_verb", "obj_verb", "pred_adj", "mod_adj", "poss_noun", "pred_noun")


# spaCy 가 사전형을 잘못 잡는 낱말 (elder -> eld, stared -> star)
LEMMA_FIX = {("ADJ", "eld"): "elder", ("VERB", "star"): "stare"}
# 품사를 잘못 잡았거나(rouble, valet 을 형용사로) to-morrow 가 쪼개져 남은 조각
DROP = {("ADJ", "rouble"), ("ADJ", "valet"), ("NOUN", "morrow")}
# 옛 2인칭 말투의 기능어 (Thou didst ... ). 불용어 목록에 없어서 따로 뺀다
ARCHAIC = {"thou", "thee", "thy", "thine", "thyself", "ye", "didst", "dost", "hast", "hadst", "art", "wert",
           "wilt", "shalt", "wouldst", "couldst", "shouldst", "canst", "mayest", "mightest"}
# 따옴표 뒤에 주어가 도치되는 말하기 동사 ("...," cried Mitya). 파서가 주어를 목적어로 읽는 일이 잦다
SPEECH_VERBS = {"say", "cry", "ask", "answer", "exclaim", "mutter", "whisper", "shout", "murmur", "repeat", "add",
                "observe", "reply", "laugh", "interrupt", "begin", "continue", "pronounce", "declare", "roar",
                "scream", "shriek", "protest", "persist", "assent", "conclude", "explain", "remark", "retort",
                "snap", "snarl", "growl", "moan", "sigh", "sob", "smile", "falter", "stammer", "bawl", "yell",
                "pipe", "drawl", "admit", "agree", "insist", "inquire", "respond", "babble", "announce", "comment"}


def fix_lemma(tok):
    lem = tok.lemma_.lower()
    return LEMMA_FIX.get((tok.pos_, lem), lem)


def content_lemma(tok):
    """수업 코드와 같은 조건(불용어·구두점 제외)에 고유명사 제외와 몇 가지 정리를 더했다."""
    if tok.pos_ not in POS or tok.is_stop or not tok.is_alpha:
        return None
    low = tok.lower_
    if low in ARCHAIC:
        return None
    if low in ("day", "night", "morrow") and tok.i >= 2 and tok.doc[tok.i - 1].text == "-" and tok.doc[tok.i - 2].lower_ == "to":
        return None                                  # to-day, to-night, to-morrow
    lem = fix_lemma(tok)
    if (tok.pos_, lem) in DROP or len(lem) <= 2:
        return None
    return lem


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    P = bknet.load_paragraphs()
    S = bknet.build_sentences(P)
    C = bknet.load_characters()
    M = bknet.find_mentions(P, S, C, layers=("name", "role"))
    docs = bknet.parse_paragraphs(P)
    assert len(docs) == len(P)

    sent_starts = {pid: (g["start"].tolist(), g["sid"].tolist()) for pid, g in S.groupby("pid", sort=False)}
    mentions_by_pid = defaultdict(list)
    for m in M.itertuples(index=False):
        mentions_by_pid[m.pid].append(m)

    import bisect
    sent_lemmas = defaultdict(list)                 # sid -> [(lemma, pos)]
    syntax = defaultdict(Counter)                   # (char, rel) -> Counter(lemma)
    n_tokens = 0
    for pid, doc in zip(P.pid.tolist(), docs):
        starts, sids = sent_starts.get(pid, ([0], [-1]))
        ms = mentions_by_pid.get(pid, [])
        covered = set()
        roots = []
        for m in ms:
            span = doc.char_span(m.start, m.end, alignment_mode="expand")
            if span is None:
                continue
            covered.update(t.i for t in span)
            roots.append((m.char_id, span.root, span))
        for tok in doc:
            n_tokens += 1
            if tok.i in covered:
                continue
            lem = content_lemma(tok)
            if lem:
                sid = sids[max(0, bisect.bisect_right(starts, tok.idx) - 1)]
                sent_lemmas[sid].append((lem, tok.pos_))
        # 따옴표 안팎 표시: 대사 속에서 불린 이름("Mitya! Mitya!" cried Fyodor)을 바깥 동사의 주어로 읽지 않기 위해
        inq, depth = [], 0
        for tok in doc:
            if tok.text == "“":
                depth = 1
            inq.append(depth)
            if tok.text == "”":
                depth = 0
        # 문장 구조로 잇기
        for cid, t, span in roots:
            in_span = {x.i for x in span}
            if t.head.i != t.i and inq[t.i] != inq[t.head.i]:
                continue
            if t.dep_ in ("nsubj", "nsubjpass"):
                h = t.head
                verbs = [h] + [c for c in h.children if c.dep_ == "conj" and c.pos_ == "VERB"
                               and not any(g.dep_ in ("nsubj", "nsubjpass") for g in c.children)]
                for v in verbs:
                    if v.pos_ == "VERB" and v.is_alpha:
                        rel = "subj_verb" if t.dep_ == "nsubj" else "obj_verb"   # 수동문의 주어는 당하는 쪽
                        syntax[(cid, rel)][fix_lemma(v)] += 1
                if h.lemma_ == "be" or h.pos_ == "AUX" or h.lemma_ in ("seem", "look", "become", "grow", "feel", "remain"):
                    for c in h.children:
                        if c.dep_ in ("acomp", "attr", "oprd") and c.is_alpha:
                            if c.pos_ == "ADJ":
                                syntax[(cid, "pred_adj")][fix_lemma(c)] += 1
                            elif c.pos_ == "NOUN":
                                syntax[(cid, "pred_noun")][fix_lemma(c)] += 1
            elif t.dep_ in ("dobj", "dative", "iobj") and t.head.pos_ == "VERB" and t.head.is_alpha:
                h = t.head
                inverted = (t.dep_ == "dobj" and h.i < t.i and fix_lemma(h) in SPEECH_VERBS
                            and not any(c.dep_ in ("nsubj", "nsubjpass") for c in h.children))
                syntax[(cid, "subj_verb" if inverted else "obj_verb")][fix_lemma(h)] += 1
            elif t.dep_ == "pobj" and t.head.dep_ in ("prep", "agent", "dative") and t.head.head.pos_ == "VERB":
                v = t.head.head
                if v.is_alpha:
                    rel = "subj_verb" if t.head.dep_ == "agent" else "obj_verb"
                    syntax[(cid, rel)][fix_lemma(v)] += 1
            elif t.dep_ == "poss" and t.head.pos_ == "NOUN" and t.head.is_alpha and t.head.i not in in_span:
                syntax[(cid, "poss_noun")][t.head.lemma_.lower()] += 1
            for c in t.children:
                if c.i in in_span or not c.is_alpha:
                    continue
                if c.dep_ == "amod" and c.pos_ == "ADJ" and (c.pos_, fix_lemma(c)) not in DROP:
                    syntax[(cid, "mod_adj")][fix_lemma(c)] += 1
                elif c.dep_ == "appos" and c.pos_ == "NOUN":
                    syntax[(cid, "pred_noun")][c.lemma_.lower()] += 1

    # 인물이 나온 문장 묶음
    char_sids = {cid: set(g.sid) for cid, g in M.groupby("char_id")}
    total = {p: Counter() for p in POS}
    for sid, items in sent_lemmas.items():
        for lem, pos in items:
            total[pos][lem] += 1
    syn_total = {rel: Counter() for rel in SYNTAX_RELS}
    for (cid, rel), cnt in syntax.items():
        syn_total[rel].update(cnt)

    by_id = {c.id: c for c in C}
    result, flat = {}, []
    for cid, sids in sorted(char_sids.items(), key=lambda kv: -len(kv[1])):
        if len(sids) < MIN_SENTENCES:
            continue
        mine = {p: Counter() for p in POS}
        for sid in sids:
            for lem, pos in sent_lemmas.get(sid, ()):
                mine[pos][lem] += 1
        entry = dict(name=by_id[cid].name, n_sentences=len(sids), freq={}, keyness={}, syntax={})
        for pos in POS:
            rest = total[pos] - mine[pos]
            z = bknet.log_odds_z(mine[pos], rest, total[pos])
            entry["freq"][pos] = [[w, int(c)] for w, c in mine[pos].most_common(TOP)]
            key = sorted(((w, int(mine[pos][w]), round(s, 2)) for w, s in z.items() if mine[pos][w] >= 3),
                         key=lambda t: -t[2])[:TOP]
            entry["keyness"][pos] = [list(t) for t in key]
            for rank, (w, c) in enumerate(mine[pos].most_common(TOP), 1):
                flat.append((cid, "freq", pos, rank, w, c, round(z.get(w, 0.0), 2)))
            for rank, (w, c, s) in enumerate(key, 1):
                flat.append((cid, "keyness", pos, rank, w, c, s))
        for rel in SYNTAX_RELS:
            cnt = syntax.get((cid, rel), Counter())
            rest = syn_total[rel] - cnt
            z = bknet.log_odds_z(cnt, rest, syn_total[rel], prior_strength=300.0) if cnt else {}
            rows = sorted(((w, int(c), round(z.get(w, 0.0), 2)) for w, c in cnt.items()), key=lambda t: (-t[1], -t[2]))[:TOP]
            entry["syntax"][rel] = [list(t) for t in rows]
            entry["syntax"][rel + "_total"] = int(sum(cnt.values()))
            for rank, (w, c, s) in enumerate(rows, 1):
                flat.append((cid, "syntax", rel, rank, w, c, s))
        result[cid] = entry

    (OUT / "character_words.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame(flat, columns=["char_id", "method", "pos_or_relation", "rank", "lemma", "count", "z"]).to_csv(
        OUT / "character_words.csv", index=False)
    meta = dict(tokens=n_tokens, sentences_with_content=len(sent_lemmas), characters=len(result),
                vocabulary={p: len(total[p]) for p in POS}, content_tokens={p: int(sum(total[p].values())) for p in POS},
                syntax_links={rel: int(sum(syn_total[rel].values())) for rel in SYNTAX_RELS})
    (OUT / "summary.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(meta))
    for cid in ("alyosha", "mitya", "ivan", "fyodor", "smerdyakov", "grushenka", "zossima", "kolya"):
        e = result[cid]
        print(f"\n== {e['name']} ({e['n_sentences']} sentences)")
        for pos in POS:
            print(f"  freq    {pos:<4}: " + ", ".join(f"{w} {c}" for w, c in e["freq"][pos][:12]))
            print(f"  keyness {pos:<4}: " + ", ".join(f"{w} {c}" for w, c, s in e["keyness"][pos][:12]))
        for rel in SYNTAX_RELS:
            print(f"  {rel:<10} ({e['syntax'][rel + '_total']}): " + ", ".join(f"{w} {c}" for w, c, s in e["syntax"][rel][:12]))


if __name__ == "__main__":
    main()
