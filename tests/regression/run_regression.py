# -*- coding: utf-8 -*-
"""
Chạy bộ hồi quy: tầng 1 (đối chiếu đáp án), tầng 2 (độ phủ + cân đối),
tầng 3 (tài nguyên). Xuất một file JSON để so sánh trước/sau.

Dùng:
    python -m tests.regression.run_regression --out baseline.json
    python -m tests.regression.run_regression --out sau-gd1.json --tier2-sample 300
"""
import os
import sys
import json
import glob
import random
import argparse
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from bctc import engine, ocr                         # noqa: E402
from tests.regression import groundtruth, metrics    # noqa: E402
from tests.regression.resources import ResourceProbe  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STMT_KEYS = ("CDKT", "KQHDKD", "LCTT")


def load_pairs():
    path = os.path.join(HERE, "pairs.json")
    if not os.path.exists(path):
        raise SystemExit(
            "Chưa có pairs.json. Chạy 'python -m tests.regression.build_pairs' "
            "rồi xác nhận thủ công trước.")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["pairs"]


def _ma_trung(d):
    """Các mã số bị TRÙNG sau chuẩn hoá (vd. '1' và '01' trong cùng dict)."""
    seen = set()
    dup = set()
    for k in (d or {}):
        c = metrics.canon(k)
        if c in seen:
            dup.add(c)
        seen.add(c)
    return sorted(dup)


def _khong_trung_ma(d, nguon, kind):
    """
    True nếu dict an toàn để đưa vào phép so/đo. False nếu có mã số trùng
    nhau sau chuẩn hoá: khi đó metrics._norm_map sẽ lặng lẽ ghi đè một giá
    trị, tức là mọi phép so trên dict đó chạy trên dữ liệu ĐÃ MẤT. Trường
    hợp này phải bỏ qua báo cáo (đếm vào 'loi_trung_ma'), không bao giờ so
    tiếp như không có gì.
    """
    d = d or {}
    if len(metrics._norm_map(d)) == len(d):
        return True
    print("     !!! CẢNH BÁO TRÙNG MÃ: %s trong %s có mã số trùng nhau sau "
          "chuẩn hoá (%s) — BỎ QUA báo cáo này (đếm vào 'loi_trung_ma'), "
          "không so sánh trên dữ liệu đã mất."
          % (kind, nguon, ", ".join(_ma_trung(d))))
    return False


def _convert(pdf_path, out_dir):
    """Chạy engine trên 1 PDF, trả về (results, resource_probe) hoặc (None, probe)."""
    with ResourceProbe() as probe:
        try:
            res = engine.convert_pdf(pdf_path, out_dir)
        except Exception:
            traceback.print_exc()
            return None, probe
    return res, probe


def run_tier1(pairs, out_dir):
    """Đối chiếu giá trị tuyệt đối với đáp án."""
    by_pdf = {}
    for p in pairs:
        by_pdf.setdefault(p["pdf"], []).append(p)

    total = {"dung": 0, "sot": 0, "lech": 0, "thua": 0}
    loi_trung_ma = 0
    per_file = []
    for pdf, group in sorted(by_pdf.items()):
        print("  [tầng 1] %s" % os.path.basename(pdf))
        res, probe = _convert(pdf, out_dir)
        if res is None:
            per_file.append({"pdf": pdf, "error": True})
            continue
        # engine.convert_pdf trả dict có khoá 'rows'; giá trị thật nằm ở
        # kết quả bóc tách -> đọc lại từ file Excel là thừa, nên ta gọi thẳng
        # parser qua engine và lấy 'results' đã lưu trong biến trả về.
        got = res.get("results") or {}
        f_counts = {"dung": 0, "sot": 0, "lech": 0, "thua": 0}
        f_trung = []
        for item in group:
            kind = item["kind"]
            if kind not in STMT_KEYS:
                continue          # CDPS không có sheet tương ứng
            try:
                expected = groundtruth.read_statement(item["excel"])
            except Exception as e:
                print("     ⚠ không đọc được đáp án: %s" % e)
                continue
            actual = got.get(kind, {})
            if not (_khong_trung_ma(expected, item["excel"], kind)
                    and _khong_trung_ma(actual, pdf + " (kết quả bóc tách)", kind)):
                loi_trung_ma += 1
                f_trung.append(kind)
                continue
            c = metrics.compare(expected, actual)
            for k in f_counts:
                f_counts[k] += c[k]
        for k in total:
            total[k] += f_counts[k]
        entry = {"pdf": pdf, "counts": f_counts,
                 "wall": probe.wall, "cpu": probe.cpu}
        if f_trung:
            entry["loi_trung_ma"] = f_trung
        per_file.append(entry)
    return {"total": total, "per_file": per_file, "loi_trung_ma": loi_trung_ma}


def run_tier2(pdf_paths, out_dir):
    """Độ phủ + tỷ lệ đạt cân đối, không cần đáp án."""
    cov_sum = {k: 0.0 for k in STMT_KEYS}
    cov_n = {k: 0 for k in STMT_KEYS}
    bal_ok = bal_total = 0
    ok_files = 0
    loi_trung_ma = 0
    per_file = []
    for pdf in pdf_paths:
        print("  [tầng 2] %s" % os.path.basename(pdf))
        res, probe = _convert(pdf, out_dir)
        if res is None:
            per_file.append({"pdf": pdf, "error": True})
            continue
        got = res.get("results") or {}
        covs = {}
        f_trung = []
        for k in STMT_KEYS:
            vals = got.get(k, {})
            if not _khong_trung_ma(vals, pdf + " (kết quả bóc tách)", k):
                loi_trung_ma += 1
                f_trung.append(k)
                continue
            covs[k] = metrics.coverage(vals, k)
            cov_sum[k] += covs[k]
            cov_n[k] += 1
        if "CDKT" in covs:        # chỉ chấm cân đối khi CDKT không trùng mã
            o, t = metrics.balance_score(got.get("CDKT", {}))
            bal_ok += o
            bal_total += t
            bal = [o, t]
        else:
            bal = None
        ok_files += 1
        entry = {"pdf": pdf, "coverage": covs, "balance": bal,
                 "wall": probe.wall, "cpu": probe.cpu,
                 "rss_mb": probe.peak_rss_mb}
        if f_trung:
            entry["loi_trung_ma"] = f_trung
        per_file.append(entry)
    return {
        "n_files": ok_files,
        "coverage_avg": {k: cov_sum[k] / max(1, cov_n[k]) for k in STMT_KEYS},
        "balance_pass_rate": (bal_ok / float(bal_total)) if bal_total else 0.0,
        "per_file": per_file,
        "loi_trung_ma": loi_trung_ma,
    }


def sample_corpus(root, n, seed=20260719):
    """Mẫu phân tầng theo thư mục năm để phủ đều các giai đoạn."""
    pdfs = [f for f in glob.glob(os.path.join(root, "**", "*.pdf"), recursive=True)
            if os.path.isfile(f) and os.path.getsize(f) > 0]
    rnd = random.Random(seed)
    rnd.shuffle(pdfs)
    return pdfs[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="file JSON kết quả")
    ap.add_argument("--tier2-sample", type=int, default=30)
    ap.add_argument("--skip-tier1", action="store_true")
    args = ap.parse_args()

    root = os.environ.get(
        "BCTC_CORPUS", "/Users/motmi/Documents/DAYS/Y-NHI/BTG/Documents")
    report = {"meta": {"corpus": root, "tier2_sample": args.tier2_sample}}

    # convert_pdf được gọi trực tiếp (không qua convert_many) nên phải tự
    # cấu hình Tesseract như convert_many vẫn làm.
    ocr.configure_tesseract()

    out_dir = tempfile.mkdtemp(prefix="bctc_reg_")
    print("Thư mục kết quả tạm: %s" % out_dir)

    with ResourceProbe() as overall:
        if not args.skip_tier1:
            print("Tầng 1 — đối chiếu đáp án")
            report["tier1"] = run_tier1(load_pairs(), out_dir)
        print("Tầng 2 — độ phủ + cân đối (%d file)" % args.tier2_sample)
        report["tier2"] = run_tier2(sample_corpus(root, args.tier2_sample), out_dir)

    report["tier3"] = {"wall": overall.wall, "cpu": overall.cpu,
                       "peak_rss_mb": overall.peak_rss_mb}

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print("\n================ TÓM TẮT ================")
    if "tier1" in report:
        t = report["tier1"]["total"]
        tot = sum(t.values()) or 1
        print("Tầng 1: đúng=%d (%.1f%%) sót=%d lệch=%d thừa=%d"
              % (t["dung"], 100.0 * t["dung"] / tot, t["sot"], t["lech"], t["thua"]))
    t2 = report["tier2"]
    print("Tầng 2: %d file | độ phủ CĐKT=%.1f%% KQ=%.1f%% LC=%.1f%% | cân đối đạt=%.1f%%"
          % (t2["n_files"], 100 * t2["coverage_avg"]["CDKT"],
             100 * t2["coverage_avg"]["KQHDKD"], 100 * t2["coverage_avg"]["LCTT"],
             100 * t2["balance_pass_rate"]))
    t3 = report["tier3"]
    print("Tầng 3: thực=%.1fs CPU=%.1fs RSS đỉnh=%.0fMB"
          % (t3["wall"], t3["cpu"], t3["peak_rss_mb"]))
    n_trung = (report.get("tier1", {}).get("loi_trung_ma", 0)
               + t2["loi_trung_ma"])
    if n_trung:
        print("!!! %d báo cáo bị bỏ qua vì trùng mã sau chuẩn hoá "
              "(xem 'loi_trung_ma' trong JSON)." % n_trung)
    print("Đã lưu: %s" % args.out)


if __name__ == "__main__":
    main()
