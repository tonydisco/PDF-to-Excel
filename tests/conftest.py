# -*- coding: utf-8 -*-
"""Fixture dùng chung cho bộ kiểm thử."""
import os
import pytest

DEFAULT_CORPUS = "/Users/motmi/Documents/DAYS/Y-NHI/BTG/Documents"


@pytest.fixture(scope="session")
def corpus_root():
    """Thư mục corpus BCTC. Tự bỏ qua test nếu máy không có corpus."""
    root = os.environ.get("BCTC_CORPUS", DEFAULT_CORPUS)
    if not os.path.isdir(root):
        pytest.skip(f"Không tìm thấy corpus tại {root} (đặt biến BCTC_CORPUS)")
    return root
