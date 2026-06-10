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
from bctc import ocr, parser, engine, excel_writer, excel_reader, ratio_engine, llm_analysis
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


def _ratios_for(path, hq=False):
    """Tỉ số cho 1 file: PDF -> OCR; .xlsx (app xuất) -> đọc lại Excel (validate)."""
    if path.lower().endswith((".xlsx", ".xls")):
        return ratio_engine.compute(excel_reader.read_results(path))
    return ratios(path, hq)


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

    try:
        size_mb = round(os.path.getsize(pdf_path) / 1048576, 1)
    except OSError:
        size_mb = None
    return {
        "name": os.path.splitext(os.path.basename(pdf_path))[0],
        "sizeMB": size_mb,
        "found": sum(1 for k in KEYS if results.get(k)),
        "conflicts": len(conflicts),
        "balanceOk": balance_ok,
        "statements": statements,
        "balance": balance,
        "warnings": warnings,
        "pageCount": page_count,
        "pages": located,                          # {CDKT: 7, KQHDKD: 9, ...}
    }


def _to_num(v):
    """Ép giá trị edit (số/None) -> int nếu nguyên, float nếu lẻ, None nếu rỗng."""
    if v is None or isinstance(v, bool):
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return int(n) if n == int(n) else n


# col ("cur"/"prior") -> nhãn conflict tương ứng (để bỏ highlight ô đã sửa).
_LABEL_FOR_COL = {"cur": "cuối năm/năm nay", "prior": "đầu năm/năm trước"}


def export_xlsx(path, out_dir=None, edits=None, hq=False):
    """Ghi Excel TỪ kết quả OCR đã cache + áp chỉnh sửa của người dùng.
    KHÔNG OCR lại từ PDF -> số đã sửa/đã soát trong Review được giữ nguyên."""
    results, _warnings, conflicts, _located, _pc = _extract(path, hq)
    results = {k: dict(v) for k, v in results.items()}   # copy, không đụng cache
    edited = set()
    for e in (edits or []):
        key, code, col = e.get("key"), e.get("code"), str(e.get("col"))
        if not key or not code:
            continue
        idx = 0 if col == "cur" else 1
        cur, prior = results.get(key, {}).get(code, (None, None))
        pair = [cur, prior]
        pair[idx] = _to_num(e.get("value"))
        results.setdefault(key, {})[code] = (pair[0], pair[1])
        edited.add((key, code, _LABEL_FOR_COL.get(col, "")))
    # Ô đã sửa -> bỏ khỏi danh sách conflict (không tô vàng trong Excel).
    conf = [c for c in (conflicts or []) if (c[0], c[1], c[2]) not in edited]

    out_dir = out_dir or os.path.join(os.path.dirname(path), "Excel_output")
    os.makedirs(out_dir, exist_ok=True)
    name = os.path.splitext(os.path.basename(path))[0]
    out_path = os.path.join(out_dir, name + ".xlsx")
    excel_writer.save(name, results, out_path, conflicts=conf)
    return out_path


def reocr_cell(path, key, code, col):
    """Đọc lại 1 ô: re-OCR toàn tài liệu ở DPI cao (hq) rồi lấy giá trị ô đó.
    Lần đầu chậm (đọc lại cả file, có cache); các ô sau cùng file tức thì."""
    results = _extract(path, hq=True)[0]
    pair = results.get(key, {}).get(code)
    if not pair:
        return None
    return pair[0 if str(col) == "cur" else 1]


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
        elif parsed.path == "/listdir":
            q = parse_qs(parsed.query)
            d = (q.get("dir") or [None])[0]
            if not d or not os.path.isdir(d):
                return self._send(400, {"error": "thiếu/không thấy thư mục"})
            try:
                files = sorted(
                    os.path.join(d, f) for f in os.listdir(d)
                    if f.lower().endswith(".pdf") and not f.startswith(".")
                )
            except OSError as e:
                return self._send(500, {"error": str(e)})
            self._send(200, {"files": files})
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
        elif parsed.path == "/llm/status":
            self._send(200, llm_analysis.status())
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
                self._send(200, _ratios_for(path, hq=bool(data.get("hq"))))
            elif self.path.startswith("/export"):
                path = data.get("path")
                if not path or not os.path.exists(path):
                    return self._send(400, {"error": "thiếu/không thấy file 'path'"})
                out_path = export_xlsx(
                    path,
                    out_dir=data.get("out_dir") or None,
                    edits=data.get("edits"),
                    hq=bool(data.get("hq")),
                )
                self._send(200, {"out_path": out_path})
            elif self.path.startswith("/reocr"):
                path = data.get("path")
                if not path or not os.path.exists(path):
                    return self._send(400, {"error": "thiếu/không thấy file 'path'"})
                val = reocr_cell(path, data.get("key"), data.get("code"), data.get("col"))
                self._send(200, {"value": val})
            elif self.path.startswith("/sizes"):
                # Dung lượng file (MB) — KHÔNG OCR, đọc ngay khi thêm vào hàng đợi.
                out = {}
                for p in (data.get("paths") or []):
                    try:
                        out[p] = round(os.path.getsize(p) / 1048576, 1) if p and os.path.exists(p) else None
                    except OSError:
                        out[p] = None
                self._send(200, {"sizes": out})
            elif self.path.startswith("/llm/key"):
                provider = data.get("provider")
                if provider not in llm_analysis.PROVIDERS:
                    return self._send(400, {"error": "provider không hợp lệ"})
                llm_analysis.save_key(provider, data.get("key") or "")
                self._send(200, {"ok": True, "status": llm_analysis.status()})
            elif self.path.startswith("/analyze/compare"):
                items = data.get("items") or []
                if not items:
                    return self._send(400, {"error": "thiếu danh sách 'items' để so sánh"})
                parts = []
                for it in items:
                    p = it.get("path")
                    if not p or not os.path.exists(p):
                        return self._send(400, {"error": f"không thấy file: {p}"})
                    label = it.get("label") or os.path.splitext(os.path.basename(p))[0]
                    parts.append((label, llm_analysis.build_payload(_ratios_for(p, hq=bool(data.get("hq"))))))
                payload = llm_analysis.build_compare_payload(parts)
                if data.get("dryRun"):
                    return self._send(200, {"payload": payload})
                provider = data.get("provider") or "anthropic"
                model = data.get("model")
                key = llm_analysis.resolve_key(provider, data.get("key"))
                result = llm_analysis.analyze_compare(provider, model, payload, key)
                self._send(200, {"payload": payload, "provider": provider, "model": model, "result": result})
            elif self.path.startswith("/analyze"):
                path = data.get("path")
                if not path or not os.path.exists(path):
                    return self._send(400, {"error": "thiếu/không thấy file 'path'"})
                # Tỉ số tính tất định trên máy -> serialize MỘT chỗ -> payload thật.
                payload = llm_analysis.build_payload(_ratios_for(path, hq=bool(data.get("hq"))))
                if data.get("dryRun"):
                    # Xem trước: trả đúng chuỗi sẽ gửi, KHÔNG gọi mạng.
                    return self._send(200, {"payload": payload})
                provider = data.get("provider") or "anthropic"
                model = data.get("model")
                key = llm_analysis.resolve_key(provider, data.get("key"))
                # Egress (gọi cloud) CHỈ ở dòng dưới — sau khi người dùng đã đồng ý.
                result = llm_analysis.analyze(provider, model, payload, key)
                self._send(200, {"payload": payload, "provider": provider, "model": model, "result": result})
            else:
                self._send(404, {"error": "not found"})
        except (llm_analysis.LLMError, excel_reader.ExcelFormatError) as e:
            self._send(400, {"error": str(e)})
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
