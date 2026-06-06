# -*- coding: utf-8 -*-
"""
Sinh sprite capybara ĐI BỘ cho hiệu ứng "đi qua lại" trên header lúc convert.
Cắt từ sprite-sheet gốc của Rainloaf (assets/mini_capy_src.png — hàng 'WALK').

TÍN DỤNG (bắt buộc theo giấy phép):
    Capybara sprite by Rainloaf — https://rainloaf.itch.io/capybara-sprite-sheet
    Được dùng tự do cho dự án (kể cả thương mại) kèm ghi công Rainloaf.

Xuất:
    assets/capybara.png            sprite-sheet  N cột x 2 hàng
                                   (hàng 0 = đi PHẢI · hàng 1 = đi TRÁI)
    assets/capybara/right_*.png, left_*.png   (các khung lẻ, tham khảo)

Chạy:  python assets/make_capybara.py
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "mini_capy_src.png")
OUT = os.path.join(HERE, "capybara")

BG = (135, 30, 81)          # màu nền của sprite-sheet gốc
WALK_Y = (86, 113)          # dải hàng "WALK" trên sheet gốc
WALK_X_START = 37           # bỏ cột nhãn chữ bên trái
COL_GAP = 2                 # khoảng trống tối thiểu giữa 2 khung
SCALE = 2                   # phóng to (nearest) cho nét pixel
PAD_X = 2                   # đệm ngang mỗi ô


def _is_bg(p):
    return abs(p[0] - BG[0]) + abs(p[1] - BG[1]) + abs(p[2] - BG[2]) <= 30


def main():
    src = Image.open(SRC).convert("RGBA")
    W, H = src.size
    px = src.load()
    A = [[(0 if _is_bg(px[x, y]) else 1) for x in range(W)] for y in range(H)]

    y0, y1 = WALK_Y

    def col_has(x):
        return any(A[y][x] for y in range(y0, y1))

    cols = [x for x in range(WALK_X_START, W) if col_has(x)]

    # gom các cột liền nhau thành từng khung
    frames = []
    s = last = None
    for x in cols:
        if s is None:
            s = last = x
        elif x - last <= COL_GAP:
            last = x
        else:
            frames.append((s, last))
            s = last = x
    if s is not None:
        frames.append((s, last))

    # cắt từng khung (trim sát nội dung), nền -> trong suốt
    crops = []
    for a, b in frames:
        ys = [y for y in range(y0, y1) if any(A[y][x] for x in range(a, b + 1))]
        ty0, ty1 = min(ys), max(ys)
        im = Image.new("RGBA", (b - a + 1, ty1 - ty0 + 1), (0, 0, 0, 0))
        ip = im.load()
        for yy in range(ty0, ty1 + 1):
            for xx in range(a, b + 1):
                if A[yy][xx]:
                    ip[xx - a, yy - ty0] = px[xx, yy]
        crops.append(im)

    # ô chuẩn: rộng = max + đệm; cao = max; căn ĐÁY (chân chạm đất), giữa ngang
    cw = max(im.width for im in crops) + 2 * PAD_X
    ch = max(im.height for im in crops)
    cells = []
    for im in crops:
        cell = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        cell.paste(im, ((cw - im.width) // 2, ch - im.height), im)
        cells.append(cell.resize((cw * SCALE, ch * SCALE), Image.NEAREST))

    fw, fh = cw * SCALE, ch * SCALE
    rights = [c.transpose(Image.FLIP_LEFT_RIGHT) for c in cells]  # gốc quay trái -> lật = phải
    lefts = cells
    n = len(cells)

    os.makedirs(OUT, exist_ok=True)
    for i, c in enumerate(rights):
        c.save(os.path.join(OUT, f"right_{i}.png"))
    for i, c in enumerate(lefts):
        c.save(os.path.join(OUT, f"left_{i}.png"))

    sheet = Image.new("RGBA", (fw * n, fh * 2), (0, 0, 0, 0))
    for i, c in enumerate(rights):
        sheet.paste(c, (i * fw, 0), c)
    for i, c in enumerate(lefts):
        sheet.paste(c, (i * fw, fh), c)
    sheet.save(os.path.join(HERE, "capybara.png"))

    print("frame=%dx%d  cols=%d  sheet=%dx%d" % (fw, fh, n, *sheet.size))
    print("=> Cập nhật trong app.py: CAPY_W=%d, CAPY_H=%d, CAPY_COLS=%d" % (fw, fh, n))


if __name__ == "__main__":
    main()
