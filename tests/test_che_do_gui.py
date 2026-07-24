# -*- coding: utf-8 -*-
"""Chế độ hiệu năng OCR trên giao diện: nhãn, lựa chọn, và truyền xuống engine.

Phần lớn chạy KHÔNG cần màn hình: gọi thẳng hàm của lớp App với một đối tượng
giả, nhờ vậy chứng minh được đường đi của chế độ mà không phải dựng cửa sổ Tk.
"""
import os
import queue
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import app                                   # noqa: E402
from bctc import workers as W                # noqa: E402


# ----------------------------------------------------------------- đồ giả
class _Var:
    """Thay cho tk.StringVar/BooleanVar."""

    def __init__(self, value):
        self._v = value

    def get(self):
        return self._v

    def set(self, v):
        self._v = v


class _VarLoi:
    """Biến hỏng: .get() ném lỗi (mô phỏng Tk đã bị huỷ)."""

    def get(self):
        raise RuntimeError("biến đã bị huỷ")


class _Log:
    def __init__(self):
        self.records = []

    def info(self, msg, *a):
        self.records.append(("info", msg, a))

    def warning(self, msg, *a):
        self.records.append(("warning", msg, a))

    def error(self, msg, *a):
        self.records.append(("error", msg, a))

    def texts(self, level=None):
        return [r[1] for r in self.records if level is None or r[0] == level]


class _Co:
    """Thay cho threading.Event (chỉ cần is_set / wait)."""

    def is_set(self):
        return False

    def wait(self):
        return True


class _EngineGia:
    def __init__(self, ket_qua=None):
        self.calls = []
        self.ket_qua = ket_qua if ket_qua is not None else []

    def convert_many(self, *a, **kw):
        self.calls.append((a, kw))
        return self.ket_qua


class _AppGia:
    """Mượn đúng các hàm thật của App, bỏ hết phần dựng giao diện."""

    _selected_mode = app.App._selected_mode
    _flog_warn = app.App._flog_warn
    _set_mode_enabled = app.App._set_mode_enabled
    _worker = app.App._worker

    def __init__(self, mode="balanced", hi_quality=False):
        self.mode_var = mode if isinstance(mode, (_Var, _VarLoi)) else _Var(mode)
        self.hi_quality = _Var(hi_quality)
        self._flog = _Log()
        self.msg_q = queue.Queue()
        self._cancel = _Co()
        self._resume = _Co()


# ------------------------------------------------------- nhãn <-> mã chế độ
def test_du_nhan_va_ghi_chu_cho_moi_che_do():
    for m in W.MODES:
        assert m in W.MODE_LABELS and W.MODE_LABELS[m].strip()
        assert m in app.MODE_NOTE and app.MODE_NOTE[m].strip()


def test_nhan_ve_ma_khu_hoi_dung_chieu():
    for m in W.MODES:
        assert app._mode_from_label(W.MODE_LABELS[m]) == m


@pytest.mark.parametrize("la", ["", "Linh tinh", "eco", "Tiết kiệm", None])
def test_nhan_la_thi_ve_can_bang(la):
    assert app._mode_from_label(la) == W.MODE_BALANCED


def test_goi_y_nhac_du_ba_che_do():
    for m in W.MODES:
        assert W.MODE_LABELS[m] in app.MODE_HINT


# --------------------------------------------------------- _selected_mode()
def test_mac_dinh_la_can_bang():
    assert _AppGia()._selected_mode() == W.MODE_BALANCED


@pytest.mark.parametrize("m", list(W.MODES))
def test_doc_dung_che_do_hop_le(m):
    assert _AppGia(m)._selected_mode() == m


def test_che_do_la_ve_can_bang_va_co_ghi_log():
    a = _AppGia("siêu tốc")
    assert a._selected_mode() == W.MODE_BALANCED
    canh_bao = a._flog.texts("warning")
    assert canh_bao, "phải ghi log khi bỏ qua chế độ lạ, không im lặng"
    assert "siêu tốc" in canh_bao[0]


def test_bien_hong_van_ve_can_bang_va_ghi_log():
    a = _AppGia(_VarLoi())
    assert a._selected_mode() == W.MODE_BALANCED
    assert a._flog.texts("warning")


# --------------------------------------- _worker truyền chế độ xuống engine
@pytest.mark.parametrize("m", list(W.MODES))
def test_worker_truyen_che_do_da_chon(monkeypatch, m):
    eng = _EngineGia(["kq"])
    monkeypatch.setattr(app, "_engine", lambda: eng)
    a = _AppGia(m)

    a._worker(["a.pdf", "b.pdf"], "/tmp/ra")

    assert len(eng.calls) == 1
    _, kw = eng.calls[0]
    assert kw["mode"] == m
    assert a.msg_q.get_nowait() == ("done", ["kq"])


def test_worker_che_do_la_van_chay_bang_can_bang(monkeypatch):
    eng = _EngineGia()
    monkeypatch.setattr(app, "_engine", lambda: eng)
    a = _AppGia("turbo")

    a._worker(["a.pdf"], "/tmp/ra")

    assert eng.calls[0][1]["mode"] == W.MODE_BALANCED
    assert a._flog.texts("warning")


def test_worker_ghi_che_do_vao_log_chan_doan(monkeypatch):
    monkeypatch.setattr(app, "_engine", lambda: _EngineGia())
    a = _AppGia(W.MODE_ECO)

    a._worker(["a.pdf"], "/tmp/ra")

    dong = [t for t in a._flog.texts("info") if "Bắt đầu convert" in t]
    assert dong, "vẫn phải có dòng log lúc bắt đầu"
    assert "chế độ" in dong[0]
    args = [r[2] for r in a._flog.records
            if r[0] == "info" and "Bắt đầu convert" in r[1]][0]
    assert W.MODE_ECO in args
    assert W.MODE_LABELS[W.MODE_ECO] in args


def test_worker_giu_nguyen_dpis_theo_chat_luong_cao(monkeypatch):
    eng = _EngineGia()
    monkeypatch.setattr(app, "_engine", lambda: eng)

    _AppGia(hi_quality=False)._worker(["a.pdf"], "/tmp/ra")
    _AppGia(hi_quality=True)._worker(["a.pdf"], "/tmp/ra")

    assert eng.calls[0][1]["dpis"] == (180, 235)
    assert eng.calls[1][1]["dpis"] == (180, 220, 290)


def test_worker_bao_loi_thay_vi_nem_ra_ngoai(monkeypatch):
    class _Vo:
        def convert_many(self, *a, **kw):
            raise ValueError("hỏng")

    monkeypatch.setattr(app, "_engine", lambda: _Vo())
    a = _AppGia()
    a._worker(["a.pdf"], "/tmp/ra")
    kind, payload = a.msg_q.get_nowait()
    assert kind == "fatal" and "hỏng" in payload


# ------------------------------------------------ phần cần màn hình (Tk)
def _tk_hoac_bo_qua():
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except Exception as e:                      # máy không có màn hình
        pytest.skip("Không dựng được cửa sổ Tk: %r" % (e,))
    return tk, root


def test_o_chon_che_do_dung_ba_nhan_va_mac_dinh_can_bang():
    tk, root = _tk_hoac_bo_qua()
    try:
        from tkinter import ttk
        var = tk.StringVar(value=W.MODE_BALANCED)
        nhan = tk.StringVar(value=W.MODE_LABELS[W.MODE_BALANCED])
        cb = ttk.Combobox(root, state="readonly", textvariable=nhan,
                          values=[W.MODE_LABELS[m] for m in W.MODES])
        assert list(cb["values"]) == [W.MODE_LABELS[m] for m in W.MODES]
        assert var.get() == W.MODE_BALANCED

        # người dùng chọn "Tiết kiệm điện" -> mã phải thành 'eco'
        nhan.set(W.MODE_LABELS[W.MODE_ECO])
        var.set(app._mode_from_label(nhan.get()))
        assert var.get() == W.MODE_ECO
    finally:
        root.destroy()
