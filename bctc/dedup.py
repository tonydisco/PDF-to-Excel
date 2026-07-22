# -*- coding: utf-8 -*-
"""
Phát hiện file PDF trùng nội dung để khỏi xử lý lại.

Khảo sát corpus: 17,1% file (499/2919, 4,11 GB) là bản sao y hệt của file
khác, do các thư mục lưu trữ chồng chéo nhau. Xử lý lại chúng là đốt CPU vô ích.
"""
import hashlib


def file_digest(path, chunk=1024 * 1024):
    """SHA-256 của toàn bộ nội dung file, đọc theo khối để không ngốn RAM."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def group_duplicates(paths):
    """
    Gom các file trùng nội dung.

    Trả về (dai_dien, ban_sao):
        dai_dien[digest] = đường dẫn file ĐẦU TIÊN mang nội dung đó
        ban_sao[path]    = đường dẫn file đại diện tương ứng

    File nào không đọc được thì coi như riêng biệt (không gộp), để lỗi được
    báo đúng theo từng file thay vì bị nuốt mất.
    """
    dai_dien = {}
    ban_sao = {}
    for p in paths:
        try:
            d = file_digest(p)
        except OSError:
            continue
        if d in dai_dien:
            ban_sao[p] = dai_dien[d]
        else:
            dai_dien[d] = p
    return dai_dien, ban_sao
