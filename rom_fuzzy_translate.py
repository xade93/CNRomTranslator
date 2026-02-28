#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, csv, os, re, sys
from xml.sax.saxutils import escape as xesc
from rapidfuzz import fuzz, process

PUNCT = str.maketrans({"，": ",", "！": "!", "？": "?", "（": "(", "）": ")"})


def norm(s: str) -> str:
    s = re.sub(r"\s+", " ", s.strip().translate(PUNCT))
    meta = r"(简体|繁体|中文|汉化|英化|破解版|修正版|修复|补丁|整合|合集|典藏|完全版|年度版|豪华版|v\d|ver\.?\d|beta|demo)"
    s = re.sub(rf"\((?=[^)]*{meta})[^)]*\)", "", s, flags=re.I)
    s = re.sub(rf"\[(?=[^\]]*{meta})[^\]]*\]", "", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def read_lines(path: str):
    if path == "-":
        return sys.stdin.read().splitlines()
    return open(path, "r", encoding="utf-8").read().splitlines()


def parse_ls(lines):
    out = []
    for ln in lines:
        ln = ln.strip()
        if ln:
            out += [p for p in re.split(r"\s{2,}", ln) if p]
    return out


def load_csv(csv_path):
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        keys = {k.strip().lower(): k for k in (r.fieldnames or [])}
        en_k = keys.get("name en")
        cn_k = keys.get("name cn")
        if not en_k or not cn_k:
            raise ValueError(f"Bad CSV headers: {r.fieldnames}")
        cn_list, cn2en = [], {}
        for row in r:
            en = (row.get(en_k) or "").strip()
            cn = (row.get(cn_k) or "").strip()
            if cn and en and cn not in cn2en:
                cn2en[cn] = en
                cn_list.append(cn)
        return cn_list, cn2en


def ask_choice(rf, score, stem_cn, csv_cn, csv_en):
    print(
        f"\n[LOW] ({score}) {rf}\n"
        f"  File CN : {stem_cn}\n"
        f"  CSV  CN : {csv_cn}\n"
        f"  CSV  EN : {csv_en}\n"
        f"Use EN match? [y/N] (default keep CN)",
        file=sys.stderr,
    )
    ans = input("> ").strip().lower()
    return csv_en if ans == "y" else stem_cn


def digits_set(s: str) -> set[str]:
    # Keep only small "sequel-ish" numbers; ignore years like 1999/2000 etc.
    return {m for m in re.findall(r"\d{1,2}", s) if 1 <= int(m) <= 30}


def best_match(query_raw: str, query_norm: str, cn_norm: list[str]) -> tuple[int, int]:
    """
    Return (idx in cn_norm/cn_list, score). Uses better scorer + deterministic tie-breaks:
      1) exact normalized match
      2) digit-set equality when query has digits (e.g. 2 vs none)
      3) longer candidate (more specific) wins
    """
    top = process.extract(query_norm, cn_norm, scorer=fuzz.WRatio, limit=8)
    if not top:
        return -1, 0

    best_score = int(top[0][1])
    tied = [t for t in top if int(t[1]) == best_score]

    qd = digits_set(query_raw)

    def key(t):
        cand_norm, _score, idx = t
        cd = digits_set(cand_norm)
        exact = (cand_norm == query_norm)
        digit_ok = (qd == cd) if qd else True
        return (exact, digit_ok, len(cand_norm))

    best = max(tied, key=key)
    return int(best[2]), int(best[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("system")
    ap.add_argument("--csv-dir", default=".")
    ap.add_argument("--rom-list", default="-")
    ap.add_argument("--th", type=int, default=90)
    args = ap.parse_args()

    csv_path = os.path.join(args.csv_dir, f"{args.system}.csv")
    if not os.path.isfile(csv_path):
        print(f"[ERR] CSV not found: {csv_path}", file=sys.stderr)
        return 2

    cn_list, cn2en = load_csv(csv_path)
    cn_norm = [norm(c) for c in cn_list]

    roms = parse_ls(read_lines(args.rom_list))
    if not roms:
        print("[ERR] no ROM names provided", file=sys.stderr)
        return 2

    total, auto_ok, prompted = len(roms), 0, 0
    entries = []

    for rf in roms:
        stem = os.path.splitext(rf)[0] or rf
        stem_n = norm(stem)

        idx, score = best_match(stem, stem_n, cn_norm)
        if idx >= 0:
            csv_cn = cn_list[idx]
            csv_en = cn2en.get(csv_cn, "")
        else:
            score, csv_cn, csv_en = 0, "", ""

        if not csv_en:
            disp = stem
        elif score >= args.th:
            disp = csv_en
            auto_ok += 1
        else:
            prompted += 1
            disp = ask_choice(rf, score, stem, csv_cn, csv_en)

        entries.append((rf, disp))

    # Write XML
    out = ['<?xml version="1.0"?>', "<gameList>"]
    for rf, name in entries:
        out += [
            "  <game>",
            f"    <path>{xesc('./' + rf)}</path>",
            f"    <name>{xesc(name)}</name>",
            "  </game>",
        ]
    out.append("</gameList>\n")
    sys.stdout.write("\n".join(out))

    pct = lambda x: f"{x*100/total:.1f}%" if total else "0.0%"
    print(
        f"\n[INFO] Total: {total}\n"
        f"[INFO] Auto-accepted (>= {args.th}): {auto_ok} ({pct(auto_ok)})\n"
        f"[INFO] Prompted (< {args.th}): {prompted} ({pct(prompted)})\n",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())