# -*- coding: utf-8 -*-
"""locate_pages chỉ được chạy MỘT lần dù bóc tách ở nhiều DPI."""
import fitz
import pytest

from bctc import parser


def _doc_rong():
    d = fitz.open()
    d.new_page()
    return d


def test_extract_nhan_tham_so_scope():
    import inspect
    assert "scope" in inspect.signature(parser.extract).parameters


def test_extract_consensus_chi_goi_locate_pages_mot_lan(monkeypatch):
    calls = []

    def fake_locate(doc, **kw):
        calls.append(1)
        return []

    def fake_extract(doc, lang="vie", dpi=300, page_range=None, digit_pass=False,
                     log=lambda *_: None, scope=None):
        if scope is None:
            fake_locate(doc)
        return {k: {} for k in ("CDKT", "KQHDKD", "LCTT")}, [], {}

    monkeypatch.setattr(parser, "locate_pages", fake_locate)
    monkeypatch.setattr(parser, "extract", fake_extract)

    doc = _doc_rong()
    parser.extract_consensus(doc, dpis=(180, 235, 290))
    doc.close()

    assert len(calls) == 1, "locate_pages phải chạy 1 lần, đang chạy %d lần" % len(calls)
