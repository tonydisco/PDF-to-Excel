# -*- coding: utf-8 -*-
"""
Sinh BẢN NHÁP ground-truth từ pipeline hiện tại để người dùng đối chiếu & sửa.

Quy trình (bước B-A0, kiểu bán tự động):
  1) chạy parser trên 1 PDF -> kết quả {key: {code: (cur, prior)}}
  2) ghi ra bench/truth/<tên>.draft.json theo schema chuẩn (xem bench/README.md)
  3) NGƯỜI DÙNG mở file, đối chiếu PDF gốc, sửa ô SAI, đổi tên bỏ '.draft' -> thành truth thật.

Dùng:
  ./.venv/bin/python bench/make_truth_draft.py "sample data/03_CTCP DV Ben Thanh 2025.pdf"
  ./.venv/bin/python bench/make_truth_draft.py "sample data" --filter 03 "18_Cty CP Sai gon Mui Ne 2025 - Hợp nhất"
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fitz
from bctc import ocr, parser

KEYS = ["CDKT", "KQHDKD", "LCTT"]
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "truth")


def make_one(pdf_path, hq=False):
    name = os.path.splitext(os.path.basename(pdf_path))[0]
    dpis = (180, 220, 290) if hq else (180, 235)
    doc = fitz.open(pdf_path)
    results, warnings, meta, conflicts = parser.extract_consensus(doc, dpis=dpis)
    doc.close()

    conflict_codes = {(k, c) for k, c, *_ in conflicts}
    draft = {
        "pdf": os.path.basename(pdf_path),
        "don_vi": "đồng",
        "_note": "BẢN NHÁP do OCR sinh — đối chiếu PDF gốc, sửa ô sai rồi đổi tên bỏ '.draft'. "
                 "Ô có '?' ở khoá _review là điểm OCR hai lần đọc lệch, nên soát kỹ.",
        "_review": sorted(f"{k}:{c}" for k, c in conflict_codes),
    }
    for k in KEYS:
        draft[k] = {code: [cur, prior] for code, (cur, prior) in sorted(results.get(k, {}).items())}

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, name + ".draft.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(draft, fh, ensure_ascii=False, indent=2)
    n = sum(len(draft[k]) for k in KEYS)
    print(f"  ✔ {out}  ({n} mã, {len(conflict_codes)} ô nghi ngờ)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="1 file PDF hoặc thư mục")
    ap.add_argument("--filter", nargs="*", default=None)
    ap.add_argument("--hq", action="store_true")
    args = ap.parse_args()

    ocr.configure_tesseract()
    if os.path.isdir(args.path):
        pdfs = sorted(f for f in os.listdir(args.path) if f.lower().endswith(".pdf"))
        if args.filter:
            pdfs = [f for f in pdfs if any(s.lower() in f.lower() for s in args.filter)]
        paths = [os.path.join(args.path, f) for f in pdfs]
    else:
        paths = [args.path]

    print(f"Sinh nháp truth cho {len(paths)} file:")
    for p in paths:
        make_one(p, hq=args.hq)


if __name__ == "__main__":
    main()
