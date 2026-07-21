# -*- coding: utf-8 -*-
"""Canh bộ cài Inno Setup không bị vô tình đảo ngược về onefile.

Không dựng được bộ cài trên máy dev (cần Windows + ISCC) nên chỉ kiểm tra
tĩnh: cấu trúc job windows trong workflow và các dòng then chốt của .iss.
"""
import os

import pytest

_GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(_GOC, ".github", "workflows", "build-tkinter.yml")
ISS = os.path.join(_GOC, "installer", "BCTC_Setup.iss")


def _doc(duong_dan):
    with open(duong_dan, encoding="utf-8") as fh:
        return fh.read()


def test_ci_windows_dung_bo_cai_inno():
    """Job windows phải dựng Setup.exe bằng ISCC, hết dấu vết copy onefile cũ."""
    yaml = pytest.importorskip(
        "yaml", reason="pyyaml chỉ cài cho máy dev, không phải phụ thuộc runtime")
    cac_buoc = yaml.safe_load(_doc(WORKFLOW))["jobs"]["windows"]["steps"]

    buoc_iscc = [b for b in cac_buoc if "ISCC.exe" in str(b.get("run", ""))]
    assert buoc_iscc, "job windows thiếu bước gọi ISCC.exe"
    assert "BCTC_Setup.iss" in buoc_iscc[0]["run"], (
        "bước ISCC phải biên dịch installer\\BCTC_Setup.iss")

    duong_dan_artifact = [
        str((b.get("with") or {}).get("path", ""))
        for b in cac_buoc if "upload-artifact" in str(b.get("uses", ""))
    ]
    assert "installer/Output/BCTC_PDF_to_Excel-Setup.exe" in duong_dan_artifact, (
        "artifact windows phải là bộ cài Setup.exe do Inno Setup dựng")

    # Bước "Đổi tên & gom" cũ copy dist\BCTC_PDF_to_Excel.exe — sau onedir
    # đường dẫn đó là THƯ MỤC, bước này gãy. Không được để nó quay lại.
    assert "BCTC_PDF_to_Excel-windows.exe" not in _doc(WORKFLOW), (
        "còn dấu vết bước copy .exe onefile cũ trong workflow")


def test_iss_khop_dau_ra_onedir():
    """Kịch bản .iss phải trỏ đúng thư mục onedir và tên file CI upload."""
    src = _doc(ISS)
    assert 'Source: "..\\dist\\BCTC_PDF_to_Excel\\*"' in src, (
        "Source phải trỏ vào dist\\BCTC_PDF_to_Excel — tên COLLECT() trong "
        "pdf2excel.spec")
    assert "OutputBaseFilename=BCTC_PDF_to_Excel-Setup" in src, (
        "OutputBaseFilename phải khớp đường dẫn artifact CI upload")
    assert "PrivilegesRequiredOverridesAllowed=dialog" in src, (
        "phải cho phép cài không cần admin — máy văn phòng thường bị khoá quyền")
