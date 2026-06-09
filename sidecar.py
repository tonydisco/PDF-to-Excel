# -*- coding: utf-8 -*-
"""
Sidecar HTTP cho app desktop (Tauri). Dùng http.server STDLIB — không thêm
dependency — và tái dùng toàn bộ lõi `bctc/` (OCR + parser + excel + cân đối).

Endpoints (JSON, có CORS):
  GET  /health                      -> {ok, has_vie, tesseract}
  POST /convert   {path, hq?}       -> {name, found, conflicts, balanceOk, statements[], balance[]}
  POST /export    {path, out_dir?}  -> {out_path}            (ghi .xlsx)
  POST /ratios    {statements?...}  -> (sẽ thêm ở ratio_engine)

Chạy:  ./.venv/bin/python sidecar.py --port 8756
"""
import os
import sys
import json
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fitz
from bctc import ocr, parser, engine, excel_writer
from bctc import templates as T

KEYS = ["CDKT", "KQHDKD", "LCTT"]
SHEET_TITLES = {
    "CDKT": "Bảng cân đối kế toán",
    "KQHDKD": "Kết quả hoạt động kinh doanh",
    "LCTT": "Lưu chuyển tiền tệ",
}


def _template_for(key, values):
    if key == "LCTT":
        return excel_writer.pick_lctt_template(values)
    return T.STATEMENTS[key][1]


def _statement_rows(key, values, flags):
    """Dựng danh sách dòng theo KHUNG template + giá trị đã bóc + cờ nghi ngờ."""
    rows = []
    for code, label, level, kind in _template_for(key, values):
        cur = prior = None
        if code in values:
            cur, prior = values[code]
        rows.append({
            "code": code,
            "label": label,
            "level": level,
            "kind": kind,
            "cur": cur,
            "prior": prior,
            "flagCur": (code, 3) in flags,
            "flagPrior": (code, 4) in flags,
        })
    return rows


def convert(pdf_path, hq=False):
    dpis = (180, 220, 290) if hq else (180, 235)
    doc = fitz.open(pdf_path)
    results, warnings, meta, conflicts = parser.extract_consensus(doc, dpis=dpis)
    doc.close()

    flags_by_key = excel_writer._flags_by_key(conflicts)
    statements = []
    for key in KEYS:
        vals = results.get(key, {})
        if not vals:
            continue   # khớp #2: chỉ trả báo cáo có dữ liệu
        statements.append({
            "key": key,
            "title": SHEET_TITLES[key],
            "rows": _statement_rows(key, vals, flags_by_key.get(key, set())),
        })

    checks = engine._check_balance(results.get("CDKT", {}))
    balance = [{"label": d, "ok": ok, "detail": detail} for d, ok, detail in checks]
    balance_ok = (len(checks) > 0 and all(ok for _, ok, _ in checks)) if checks else None

    return {
        "name": os.path.splitext(os.path.basename(pdf_path))[0],
        "found": sum(1 for k in KEYS if results.get(k)),
        "conflicts": len(conflicts),
        "balanceOk": balance_ok,
        "statements": statements,
        "balance": balance,
        "warnings": warnings,
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def do_OPTIONS(self):
        self._send(204, {})

    def do_GET(self):
        if self.path.startswith("/health"):
            tess, td = ocr.locate_tesseract()
            self._send(200, {"ok": True, "tesseract": tess, "has_vie": ocr.has_vietnamese()})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        data = self._body()
        try:
            if self.path.startswith("/convert"):
                path = data.get("path")
                if not path or not os.path.exists(path):
                    return self._send(400, {"error": "thiếu/không thấy file 'path'"})
                self._send(200, convert(path, hq=bool(data.get("hq"))))
            elif self.path.startswith("/export"):
                path = data.get("path")
                out_dir = data.get("out_dir") or os.path.join(os.path.dirname(path), "Excel_output")
                r = engine.convert_pdf(path, out_dir)
                self._send(200, {"out_path": r.get("out_path")})
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, *args):
        pass  # im lặng, tránh spam stdout (Tauri đọc stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8756)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    ocr.configure_tesseract()
    try:
        srv = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as e:
        # Cổng đã có sidecar khác phục vụ -> thoát êm (tránh trùng, không traceback).
        print(f"BCTC sidecar: cổng {args.port} đang bận ({e}); thoát.", flush=True)
        return
    print(f"BCTC sidecar listening on http://{args.host}:{args.port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
