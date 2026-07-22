# -*- coding: utf-8 -*-
import pytest

from bctc import workers as W


@pytest.mark.parametrize("logical,eco,balanced,mx", [
    (2, 1, 1, 1),
    (4, 1, 1, 3),
    (8, 1, 3, 7),
    (16, 1, 7, 15),
])
def test_worker_count_theo_so_luong_logic(logical, eco, balanced, mx):
    assert W.worker_count(W.MODE_ECO, logical) == eco
    assert W.worker_count(W.MODE_BALANCED, logical) == balanced
    assert W.worker_count(W.MODE_MAX, logical) == mx


def test_luon_it_nhat_mot_luong():
    for lg in (0, 1, 2):
        for m in (W.MODE_ECO, W.MODE_BALANCED, W.MODE_MAX):
            assert W.worker_count(m, lg) >= 1


def test_che_do_la_mac_dinh_can_bang():
    assert W.worker_count(logical=8) == W.worker_count(W.MODE_BALANCED, 8)


def test_che_do_khong_hop_le_quay_ve_can_bang():
    assert W.worker_count("linh tinh", 8) == W.worker_count(W.MODE_BALANCED, 8)
