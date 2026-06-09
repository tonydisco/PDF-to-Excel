# -*- coding: utf-8 -*-
"""
Scorer benchmark độ chính xác (bước B-A0).

Chạy pipeline hiện tại trên các PDF và đo:
  - Proxy KHÔNG cần ground-truth (chạy được trên mọi file):
      * coverage: tìm thấy mấy / 3 báo cáo (CDKT, KQHDKD, LCTT)
      * balance-pass: tỉ lệ phép kiểm cân đối ĐẠT (270=440, 100+200=270, 300+400=440)
      * conflicts: số ô "nghi ngờ" (hai lần đọc lệch)
      * time: giây / file
  - Cell-accuracy CÓ ground-truth (nếu có bench/truth/<tên>.json):
      * tỉ lệ ô đọc ĐÚNG so với đáp án (tách cur / prior)

Dùng:
  ./.venv/bin/python bench/score.py "sample data" --out bench/results.md
  ./.venv/bin/python bench/score.py "sample data" --filter 23 35 --out /tmp/sub.md
  ./.venv/bin/python bench/score.py "sample data" --truth bench/truth --hq
"""
import os
import sys
import json
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fitz
from bctc import ocr, parser, engine
from bctc import templates as T

KEYS = ["CDKT", "KQHDKD", "LCTT"]


def score_file(pdf_path, dpis, truth=None, digit_pass=True):
    name = os.path.splitext(os.path.basename(pdf_path))[0]
    rec = {"name": name, "ok": False, "error": None}
    try:
        doc = fitz.open(pdf_path)
        t0 = time.time()
        results, warnings, meta, conflicts = parser.extract_consensus(
            doc, dpis=dpis, digit_pass=digit_pass)
        rec["time"] = round(time.time() - t0, 1)
        doc.close()

        rec["rows"] = {k: len(results.get(k, {})) for k in KEYS}
        rec["found"] = sum(1 for k in KEYS if rec["rows"][k] > 0)
        checks = engine._check_balance(results.get("CDKT", {}))
        rec["n_checks"] = len(checks)
        rec["n_pass"] = sum(1 for _, ok, _ in checks if ok)
        rec["balance_ok"] = (rec["n_checks"] > 0 and rec["n_pass"] == rec["n_checks"])
        rec["conflicts"] = len(conflicts)
        rec["warnings"] = warnings
        rec["ok"] = True

        if truth:
            tot = hit = 0
            for k in KEYS:
                exp = truth.get(k, {})
                got = results.get(k, {})
                for code, pair in exp.items():
                    for i in range(2):                       # 0=cur, 1=prior
                        if pair[i] is None:
                            continue
                        tot += 1
                        g = got.get(code)
                        if g and g[i] == pair[i]:
                            hit += 1
            rec["cell_tot"] = tot
            rec["cell_hit"] = hit
            rec["cell_acc"] = round(100 * hit / tot, 1) if tot else None
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
    return rec


def main():
    ap = argparse.ArgumentParser(description="Benchmark scorer cho BCTC PDF->Excel")
    ap.add_argument("pdf_dir", help="Thư mục chứa PDF")
    ap.add_argument("--truth", default=None, help="Thư mục truth/*.json (cell-accuracy)")
    ap.add_argument("--filter", nargs="*", default=None,
                    help="Chỉ chạy file có tên chứa các chuỗi này")
    ap.add_argument("--limit", type=int, default=None, help="Giới hạn số file")
    ap.add_argument("--hq", action="store_true", help="Chất lượng cao (3 DPI)")
    ap.add_argument("--digit-pass", action="store_true",
                    help="Bật pass chỉ-chữ-số (B-A1, thí nghiệm — mặc định TẮT vì làm tệ hơn)")
    ap.add_argument("--out", default=None, help="Ghi báo cáo Markdown ra file")
    args = ap.parse_args()

    dpis = (180, 220, 290) if args.hq else (180, 235)
    ocr.configure_tesseract()
    if not ocr.has_vietnamese():
        print("THIẾU gói tiếng Việt (vie) cho Tesseract.", file=sys.stderr)
        sys.exit(1)

    pdfs = sorted(f for f in os.listdir(args.pdf_dir) if f.lower().endswith(".pdf"))
    if args.filter:
        pdfs = [f for f in pdfs if any(s.lower() in f.lower() for s in args.filter)]
    if args.limit:
        pdfs = pdfs[:args.limit]

    recs = []
    for i, f in enumerate(pdfs, 1):
        path = os.path.join(args.pdf_dir, f)
        truth = None
        if args.truth:
            tp = os.path.join(args.truth, os.path.splitext(f)[0] + ".json")
            if os.path.exists(tp):
                truth = json.load(open(tp, encoding="utf-8"))
        print(f"[{i}/{len(pdfs)}] {f} ...", file=sys.stderr, flush=True)
        rec = score_file(path, dpis, truth, digit_pass=args.digit_pass)
        recs.append(rec)
        tag = (f"acc={rec.get('cell_acc')}% " if rec.get("cell_acc") is not None else "")
        if rec["ok"]:
            print(f"      found {rec['found']}/3  balance {rec['n_pass']}/{rec['n_checks']}"
                  f"  conflicts {rec['conflicts']}  {tag}{rec['time']}s",
                  file=sys.stderr, flush=True)
        else:
            print(f"      LỖI: {rec['error']}", file=sys.stderr, flush=True)

    print(render(recs, bool(args.truth)))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(render(recs, bool(args.truth)))
        print(f"\n→ đã ghi {args.out}", file=sys.stderr)


def render(recs, has_truth):
    ok = [r for r in recs if r["ok"]]
    lines = ["# Benchmark BCTC PDF→Excel", ""]
    n = len(recs)
    lines.append(f"- Số file: {n} (chạy được {len(ok)})")
    if ok:
        avg_found = sum(r["found"] for r in ok) / len(ok)
        n_bal = sum(1 for r in ok if r["balance_ok"])
        avg_t = sum(r["time"] for r in ok) / len(ok)
        tot_conf = sum(r["conflicts"] for r in ok)
        lines.append(f"- Coverage TB: {avg_found:.2f}/3 báo cáo")
        lines.append(f"- Balance-pass (đủ mọi phép): {n_bal}/{len(ok)} file")
        lines.append(f"- Tổng ô nghi ngờ: {tot_conf} · Thời gian TB: {avg_t:.1f}s/file")
        if has_truth:
            tt = sum(r.get("cell_tot", 0) for r in ok)
            th = sum(r.get("cell_hit", 0) for r in ok)
            if tt:
                lines.append(f"- **Cell-accuracy tổng: {100*th/tt:.1f}%** ({th}/{tt} ô)")
    lines.append("")
    hdr = "| File | CDKT | KQ | LC | Balance | Conflicts | Time(s) |"
    sep = "|---|---|---|---|---|---|---|"
    if has_truth:
        hdr = hdr[:-1] + " Cell-acc |"
        sep = sep[:-1] + "---|"
    lines += [hdr, sep]
    for r in recs:
        if not r["ok"]:
            row = f"| {r["name"]} | — | — | — | LỖI | — | — |"
            if has_truth:
                row = row[:-1] + " — |"
            lines.append(row)
            continue
        bal = f"{r['n_pass']}/{r['n_checks']}" + (" ✓" if r["balance_ok"] else " ⚠")
        row = (f"| {r["name"]} | {r['rows']['CDKT']} | {r['rows']['KQHDKD']} | "
               f"{r['rows']['LCTT']} | {bal} | {r['conflicts']} | {r['time']} |")
        if has_truth:
            acc = r.get("cell_acc")
            row = row[:-1] + f" {acc if acc is not None else '—'} |"
        lines.append(row)
    return "\n".join(lines)


if __name__ == "__main__":
    main()
