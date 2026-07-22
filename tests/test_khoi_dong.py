# -*- coding: utf-8 -*-
"""app.py không được kéo theo thư viện nặng lúc import."""
import re
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NANG = ("fitz", "pymupdf", "pytesseract", "PIL")


def test_import_app_khong_keo_theo_thu_vien_nang():
    ma = (
        "import sys; sys.argv=['app'];"
        "import importlib; importlib.import_module('app');"
        "print(','.join(sorted(m for m in sys.modules if m.split('.')[0] in %r)))"
        % (NANG,)
    )
    r = subprocess.run([sys.executable, "-c", ma], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    nap = [m for m in r.stdout.strip().split(",") if m]
    assert not nap, "app.py kéo theo thư viện nặng lúc import: %s" % nap


def test_max_files_van_dung_150():
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    assert re.search(r"^MAX_FILES\s*=\s*150", src, re.M), \
        "MAX_FILES phải là hằng số 150, không lấy từ engine lúc import"
