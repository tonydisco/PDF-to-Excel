# -*- coding: utf-8 -*-
"""
Sinh icon launcher cho ứng dụng theo bảng màu Coolors
(navy 3D405B · cream F4F1DE · terracotta E07A5F · sage 81B29A · sand F2CC8F).

Tạo ra trong thư mục assets/:
    icon.png (1024)  ·  icon_256.png  ·  icon.ico (Windows)  ·  icon.iconset/ (cho .icns)

Chạy:  python assets/make_icon.py
Sau đó (macOS) tạo .icns:  iconutil -c icns assets/icon.iconset -o assets/icon.icns
"""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))

NAVY = (61, 64, 91)
CREAM = (244, 241, 222)
TERRA = (224, 122, 95)
SAGE = (129, 178, 154)
SAND = (242, 204, 143)
WHITE = (255, 255, 255)

SS = 4  # hệ số khử răng cưa (supersampling)


def render(size):
    """Vẽ icon ở kích thước `size` px (vẽ lớn gấp SS lần rồi thu nhỏ)."""
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # nền bo góc (navy)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.225), fill=NAVY)

    # trang giấy (cream) — đại diện báo cáo tài chính
    x0, y0, x1, y1 = int(s * 0.22), int(s * 0.17), int(s * 0.78), int(s * 0.83)
    pr = int(s * 0.05)
    d.rounded_rectangle([x0, y0, x1, y1], radius=pr, fill=CREAM)

    pad = int(s * 0.045)
    gx0, gy0, gx1, gy1 = x0 + pad, y0 + pad, x1 - pad, y1 - pad

    # hàng tiêu đề: 1 ô terracotta + 1 ô sand (gợi cột Mã số / số liệu)
    row_h = int((gy1 - gy0) / 6)
    d.rounded_rectangle([gx0, gy0, gx0 + int((gx1 - gx0) * 0.42), gy0 + row_h],
                        radius=int(row_h * 0.30), fill=TERRA)
    d.rounded_rectangle([gx0 + int((gx1 - gx0) * 0.50), gy0,
                         gx1, gy0 + row_h],
                        radius=int(row_h * 0.30), fill=SAND)

    # lưới bảng (sage) — gợi bảng Excel
    lw = max(2, int(s * 0.012))
    body_top = gy0 + row_h + int(row_h * 0.5)
    for k in range(1, 4):
        yy = body_top + k * int((gy1 - body_top) / 4)
        d.line([gx0, yy, gx1, yy], fill=SAGE, width=lw)
    for k in range(1, 3):
        xx = gx0 + k * int((gx1 - gx0) / 3)
        d.line([xx, body_top - int(row_h * 0.4), xx, gy1], fill=SAGE, width=lw)

    # huy hiệu "đã chuyển đổi": vòng tròn sage + dấu check trắng, góc dưới phải
    cx, cy, cr = x1 - int(s * 0.02), y1 - int(s * 0.02), int(s * 0.13)
    d.ellipse([cx - cr - lw * 2, cy - cr - lw * 2, cx + cr + lw * 2, cy + cr + lw * 2],
              fill=NAVY)                                   # viền tách khỏi trang
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=SAGE)
    cw = max(3, int(s * 0.022))
    d.line([cx - int(cr * 0.45), cy + int(cr * 0.02),
            cx - int(cr * 0.08), cy + int(cr * 0.38)], fill=WHITE, width=cw, joint="curve")
    d.line([cx - int(cr * 0.08), cy + int(cr * 0.38),
            cx + int(cr * 0.48), cy - int(cr * 0.30)], fill=WHITE, width=cw, joint="curve")

    return img.resize((size, size), Image.LANCZOS)


def main():
    # PNG chính
    render(1024).save(os.path.join(HERE, "icon.png"))
    render(256).save(os.path.join(HERE, "icon_256.png"))

    # Windows .ico (nhiều kích thước trong 1 file)
    ico_sizes = [16, 32, 48, 64, 128, 256]
    render(256).save(os.path.join(HERE, "icon.ico"),
                     sizes=[(n, n) for n in ico_sizes])

    # macOS .iconset (để iconutil tạo .icns)
    iconset = os.path.join(HERE, "icon.iconset")
    os.makedirs(iconset, exist_ok=True)
    spec = [(16, "16x16"), (32, "16x16@2x"), (32, "32x32"), (64, "32x32@2x"),
            (128, "128x128"), (256, "128x128@2x"), (256, "256x256"),
            (512, "256x256@2x"), (512, "512x512"), (1024, "512x512@2x")]
    for px, name in spec:
        render(px).save(os.path.join(iconset, f"icon_{name}.png"))

    print("Đã tạo icon trong:", HERE)


if __name__ == "__main__":
    main()
