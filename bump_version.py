# -*- coding: utf-8 -*-
"""
Tăng phiên bản ứng dụng (Semantic Versioning: MAJOR.MINOR.PATCH).

Cách dùng:
    python bump_version.py patch     # 1.0.0 -> 1.0.1  (sửa lỗi nhỏ)
    python bump_version.py minor     # 1.0.1 -> 1.1.0  (thêm tính năng)
    python bump_version.py major     # 1.1.0 -> 2.0.0  (thay đổi lớn)
    python bump_version.py patch --tag        # đồng thời tạo git tag vX.Y.Z
    python bump_version.py patch --tag --push # tạo tag và push (CI sẽ build Release)

Không truyền gì -> mặc định 'patch'. Phiên bản được lưu trong version.py.
"""
import os
import re
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
VF = os.path.join(HERE, "version.py")
PARTS = {"major", "minor", "patch"}


def read_version():
    text = open(VF, encoding="utf-8").read()
    m = re.search(r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"', text)
    if not m:
        sys.exit("Không tìm thấy __version__ hợp lệ trong version.py")
    return text, tuple(int(x) for x in m.groups())


def main():
    args = sys.argv[1:]
    part = next((a for a in args if a in PARTS), "patch")
    if args and args[0] not in PARTS and not args[0].startswith("--"):
        sys.exit("Tham số không hợp lệ. Dùng: patch | minor | major")

    text, (maj, mnr, pat) = read_version()
    if part == "major":
        maj, mnr, pat = maj + 1, 0, 0
    elif part == "minor":
        mnr, pat = mnr + 1, 0
    else:
        pat += 1
    new = f"{maj}.{mnr}.{pat}"

    new_text = re.sub(r'(__version__\s*=\s*")\d+\.\d+\.\d+(")',
                      rf"\g<1>{new}\g<2>", text)
    open(VF, "w", encoding="utf-8").write(new_text)
    print(f"✓ Phiên bản mới: {new}  (bump {part})")

    if "--tag" in args:
        tag = f"v{new}"
        subprocess.run(["git", "add", "version.py"], cwd=HERE, check=False)
        subprocess.run(["git", "commit", "-m", f"chore: bump version {new}"],
                       cwd=HERE, check=False)
        subprocess.run(["git", "tag", tag], cwd=HERE, check=False)
        print(f"✓ Đã commit + tạo tag {tag}")
        if "--push" in args:
            subprocess.run(["git", "push"], cwd=HERE, check=False)
            subprocess.run(["git", "push", "origin", tag], cwd=HERE, check=False)
            print(f"✓ Đã push commit và tag {tag} (CI sẽ build Release)")
        else:
            print(f"  Để phát hành: git push && git push origin {tag}")


if __name__ == "__main__":
    main()
