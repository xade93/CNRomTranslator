#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, csv, json, os, re, sys
from xml.sax.saxutils import escape as xesc
from rapidfuzz import fuzz, process
import seq_utils

# normalize common fullwidth punctuation to ASCII
FW_MAP = {ord('，'): ',', ord('！'): '!', ord('？'): '?', ord('（'): '(', ord('）'): ')',
          ord('：'): ':', ord('；'): ';', ord('【'): '[', ord('】'): ']', ord('、'): ',',
          ord('—'): '-', ord('－'): '-', ord('～'): '~', ord('　'): ' '}

PUNCT = FW_MAP


def norm(s: str) -> str:
    # map fullwidth punctuation and collapse spaces
    s = s.translate(PUNCT)
    s = re.sub(r"[\uFF01-\uFF60\u3000]", lambda m: FW_MAP.get(ord(m.group(0)), m.group(0)), s)
    s = s.replace('\u3000', ' ')
    s = re.sub(r"\s+", " ", s.strip())
    meta = r"(简体|繁体|中文|汉化|英化|破解版|修正版|修复|补丁|整合|合集|典藏|完全版|年度版|豪华版|v\d|ver\.?\d|beta|demo)"
    s = re.sub(rf"\((?=[^)]*{meta})[^)]*\)", "", s, flags=re.I)
    s = re.sub(rf"\[(?=[^\]]*{meta})[^\]]*\]", "", s, flags=re.I)
    # strip surrounding quotes and punctuation
    s = s.strip(' "\'`')
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_aliases(csv_dir: str) -> dict:
    # returns mapping of normalized alias -> canonical CN name
    path = os.path.join(csv_dir, 'name_alias(Chinese).json')
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return {}
    amap = {}
    for en, v in data.items():
        default = v.get('default')
        if not default:
            continue
        # map default itself
        amap[norm(default).lower()] = default
        for a in v.get('alias', []) + v.get('others', []):
            if a:
                amap[norm(a).lower()] = default
        for a in v.get('alias-en', []):
            if a:
                amap[norm(a).lower()] = default
    return amap


def apply_alias(s: str, amap: dict) -> str:
    if not amap:
        return s
    ln = s.lower()
    if ln in amap:
        return amap[ln]
    # replace alias substring in original string (preserve non-matched case)
    for a_norm, can in amap.items():
        if a_norm in ln:
            return re.sub(re.escape(a_norm), can, s, flags=re.I)
    return s


# sequence helpers are provided by seq_utils; enabled via `--seq` flag.


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


def ask_choice(rf, score, stem_cn, csv_cn, csv_en, remaining: int):
    print(
        f"\n[LOW] ({score}) {rf}\n"
        f"  File CN : {stem_cn}\n"
        f"  CSV  CN : {csv_cn}\n"
        f"  CSV  EN : {csv_en}\n"
        f"  Remaining to review: {remaining}\n",
        file=sys.stderr,
    )
    print(
        "Choose: [a]ccept CSV EN, [k]eep original, [m]anual input (default keep)",
        file=sys.stderr,
    )
    ans = input("> ").strip()
    if not ans:
        return stem_cn
    a = ans.lower()
    if a in ("a", "y", "yes"):
        return csv_en
    if a in ("k", "keep"):
        return stem_cn
    if a in ("m", "i", "man", "manual"):
        print("Enter manual name (empty to keep original):", file=sys.stderr)
        manual = input("name> ").strip()
        return manual if manual else stem_cn
    # fallback
    return stem_cn


def top_candidates(query_raw: str, query_norm: str, cn_norm: list[str], cn_list: list[str], cn2en: dict, limit: int = 6):
    # return list of (csv_cn, csv_en, score) sorted desc
    return [
        (cn_list[int(idx)], cn2en.get(cn_list[int(idx)], ''), int(score), cand_norm)
        for cand_norm, score, idx in process.extract(query_norm, cn_norm, scorer=fuzz.WRatio, limit=limit)
    ]


def seq_normalize(s: str) -> str:
    # proxy to seq_utils; will behave even if seq disabled
    return seq_utils.seq_normalize(s)


def ask_choice_multi(rf: str, query_raw: str, candidates: list, remaining: int):
    """
    candidates: list of (csv_cn, csv_en, score, cand_norm)
    """
    print(f"\n[LOW] {rf}\n  Remaining to review: {remaining}\n", file=sys.stderr)
    for i, (csv_cn, csv_en, score, _cand_norm) in enumerate(candidates, start=1):
        print(f"  [{i}] ({score}) CSV CN: {csv_cn}  -> EN: {csv_en}", file=sys.stderr)
    print("Choices: number to accept, [a]ccept top1, [k]eep original, [m]anual input (default keep)", file=sys.stderr)
    ans = input("> ").strip()
    if not ans:
        return None
    a = ans.lower()
    if a in ("a", "1"):
        return candidates[0][1] if candidates else None
    if a in ("k", "keep"):
        return None
    if a in ("m", "man", "i", "manual"):
        print("Enter manual name (empty to keep original):", file=sys.stderr)
        manual = input("name> ").strip()
        return manual if manual else None
    # numeric selection
    if re.match(r"^\d+$", ans):
        idx = int(ans) - 1
        if 0 <= idx < len(candidates):
            return candidates[idx][1]
    return None


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
        # prefer candidates whose seq tokens intersect with query
        digit_intersect = 1 if (qd and cd and qd & cd) else 0
        return (exact, digit_ok, digit_intersect, len(cand_norm))

    best = max(tied, key=key)
    return int(best[2]), int(best[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("system")
    ap.add_argument("--csv-dir", default=".")
    ap.add_argument("--rom-list", default="-")
    ap.add_argument("--th", type=int, default=90)
    ap.add_argument("--seq", action="store_true", help="enable sequel/number normalization and prioritization (adhoc)")
    args = ap.parse_args()

    csv_path = os.path.join(args.csv_dir, f"{args.system}.csv")
    if not os.path.isfile(csv_path):
        print(f"[ERR] CSV not found: {csv_path}", file=sys.stderr)
        return 2

    cn_list, cn2en = load_csv(csv_path)
    alias_map = load_aliases(args.csv_dir)
    # normalized candidate names (with alias and seq normalization)
    cn_norm = [norm(c) for c in cn_list]
    global digits_set
    if args.seq:
        # use sequence-normalized candidate list
        cn_norm_seq = [seq_normalize(apply_alias(norm(c), alias_map)).lower() for c in cn_list]
        # enable digits_set implementation from seq_utils
        digits_set = seq_utils.extract_seq_tokens
    else:
        cn_norm_seq = [apply_alias(norm(c), alias_map).lower() for c in cn_list]
        digits_set = lambda s: set()

    roms = parse_ls(read_lines(args.rom_list))
    if not roms:
        print("[ERR] no ROM names provided", file=sys.stderr)
        return 2

    total, auto_ok, prompted = len(roms), 0, 0
    results = []
    pending_idx = []

    for rf in roms:
        stem = os.path.splitext(rf)[0] or rf
        stem_n = norm(stem)
        stem_n_alias = apply_alias(stem_n, alias_map)
        stem_n_seq = seq_normalize(stem_n_alias).lower()

        idx, score = best_match(stem, stem_n_seq, cn_norm_seq)
        if idx >= 0:
            csv_cn = cn_list[idx]
            csv_en = cn2en.get(csv_cn, "")
        else:
            score, csv_cn, csv_en = 0, "", ""

        if not csv_en:
            # no CSV mapping available
            results.append({"rf": rf, "stem": stem, "csv_cn": "", "csv_en": "", "score": 0, "chosen": stem})
        elif score >= args.th:
            # auto-accepted
            auto_ok += 1
            results.append({"rf": rf, "stem": stem, "csv_cn": csv_cn, "csv_en": csv_en, "score": score, "chosen": csv_en})
        else:
            prompted += 1
            cands = top_candidates(stem, stem_n_seq, cn_norm_seq, cn_list, cn2en, limit=6)
            # record top candidate as detected CN/EN
            top_cn = cands[0][0] if cands else ""
            top_en = cands[0][1] if cands else ""
            results.append({"rf": rf, "stem": stem, "csv_cn": top_cn, "csv_en": top_en, "score": score, "candidates": cands, "chosen": None})
            pending_idx.append(len(results)-1)

    # Second pass: interactive review of pending low-confidence matches
    if pending_idx:
        print(f"\n[INFO] {len(pending_idx)} titles require human intervention...\n", file=sys.stderr)
        for i, ridx in enumerate(pending_idx):
            rec = results[ridx]
            remaining = len(pending_idx) - i
            disp = ask_choice_multi(rec["rf"], rec["stem"], rec.get("candidates", []), remaining)
            if not disp:
                # keep original
                rec["chosen"] = rec["stem"]
            else:
                # if disp matches a candidate EN, find its CN
                matched = None
                for cn, en, score, _norm in rec.get("candidates", []):
                    if en == disp:
                        matched = (cn, en)
                        break
                if matched:
                    rec["csv_cn"], rec["csv_en"] = matched
                    rec["chosen"] = matched[1]
                else:
                    # manual input
                    rec["chosen"] = disp
            results[ridx] = rec

    # Print condensed mapping lines for LLM review, prefixed by a short prompt
    print("Mappings (copy-paste below to LLM for double check):\n", file=sys.stderr)
    print("This is output from a ROM name fuzzy matching program that takes Chinese ROM names and attempt to match them against a database of official Chinese names & English names. Each line is of format <original name> -> <CN detected name> -> <EN detected name>, please help double check each line below and report possible mistake in detection, if any. I only care if the game is the same one, so matching to different region version, different language is all ok. The system is %s.\n" % args.system, file=sys.stderr)

    for rec in results:
        fn = rec.get("rf")
        detected_cn = rec.get("csv_cn") or ""
        detected_en = rec.get("csv_en") or ""
        chosen = rec.get("chosen") or rec.get("stem")
        # line: <filename> -> <CN detected name> -> <EN detected name or chosen>
        print(f"{fn} -> {detected_cn} -> {chosen}", file=sys.stderr)

    # Write XML to hard-coded file
    out = ['<?xml version="1.0"?>', "<gameList>"]
    for rec in results:
        rf = rec.get("rf")
        name = rec.get("chosen") or rec.get("stem")
        out.append("  <game>")
        out.append(f"    <path>{xesc('./' + rf)}</path>")
        # omit <name> if we fell back to raw filename (no match)
        if name and name != rec.get("stem"):
            out.append(f"    <name>{xesc(name)}</name>")
        out.append("  </game>")
    out.append("</gameList>\n")
    with open('./gamelist_generated.xml', 'w', encoding='utf-8') as fh:
        fh.write("\n".join(out))

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