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
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fitz
from bctc import ocr, parser, engine, excel_writer, ratio_engine
from bctc import templates as T

# Cache kết quả OCR theo (path, hq) -> để /ratios & /convert lặp không OCR lại.
_CACHE = {}

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


def render_page_png(pdf_path, page, dpi=110):
    """Render 1 trang PDF -> PNG bytes (1-based page). Dùng cho khung xem ở UI."""
    doc = fitz.open(pdf_path)
    idx = max(0, min(doc.page_count - 1, int(page) - 1))
    pix = doc[idx].get_pixmap(dpi=int(dpi))
    data = pix.tobytes("png")
    doc.close()
    return data


def _extract(pdf_path, hq=False):
    """OCR + định vị (có cache). Trả (results, warnings, conflicts, located, page_count)."""
    key = (os.path.abspath(pdf_path), bool(hq))
    if key in _CACHE:
        return _CACHE[key]
    dpis = (180, 220, 290) if hq else (180, 235)
    doc = fitz.open(pdf_path)
    results, warnings, meta, conflicts = parser.extract_consensus(doc, dpis=dpis)
    scope = parser.locate_pages(doc)
    page_count = doc.page_count
    doc.close()
    located = {}
    for p0, k in scope:
        located.setdefault(k, p0 + 1)              # 1-based, trang đầu mỗi báo cáo
    out = (results, warnings, conflicts, located, page_count)
    _CACHE[key] = out
    return out


def ratios(pdf_path, hq=False):
    results, *_ = _extract(pdf_path, hq)
    return ratio_engine.compute(results)


def convert(pdf_path, hq=False):
    results, warnings, conflicts, located, page_count = _extract(pdf_path, hq)

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
        "pageCount": page_count,
        "pages": located,                          # {CDKT: 7, KQHDKD: 9, ...}
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
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            tess, _ = ocr.locate_tesseract()
            self._send(200, {"ok": True, "tesseract": tess, "has_vie": ocr.has_vietnamese()})
        elif parsed.path == "/page":
            q = parse_qs(parsed.query)
            path = (q.get("path") or [None])[0]
            page = (q.get("page") or ["1"])[0]
            dpi = (q.get("dpi") or ["110"])[0]
            if not path or not os.path.exists(path):
                return self._send(400, {"error": "thiếu/không thấy file"})
            try:
                data = render_page_png(path, page, dpi)
            except Exception as e:
                return self._send(500, {"error": f"{type(e).__name__}: {e}"})
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "max-age=600")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
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
            elif self.path.startswith("/ratios"):
                path = data.get("path")
                if not path or not os.path.exists(path):
                    return self._send(400, {"error": "thiếu/không thấy file 'path'"})
                self._send(200, ratios(path, hq=bool(data.get("hq"))))
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
