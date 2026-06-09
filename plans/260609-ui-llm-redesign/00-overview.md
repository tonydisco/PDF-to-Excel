# Redesign UI + Hệ thống phân tích LLM — Tổng quan

> Ngày 2026-06-09. Phase thiết kế (chưa code). Theo yêu cầu task #3 + #4.

## Quyết định đã chốt (user, 2026-06-09)
- **#4 ranh giới cloud:** chỉ gửi **chỉ số/tỉ số tổng hợp** lên LLM cloud — KHÔNG gửi PDF/bản gốc.
- **Thứ tự:** thiết kế #3/#4 **trước**; code extraction (#1 B-A3) sau.
- **#3 UI tech:** user yêu cầu mình đề xuất stack hiện đại+tối ưu → khuyến nghị ở [01-ui-redesign.md](01-ui-redesign.md) §2 (**Tauri 2 + React/shadcn + Python sidecar**; phương án nhẹ-rủi-ro: pywebview). **Chờ chốt.**

## Tài liệu
- [01-ui-redesign.md](01-ui-redesign.md) — techstack + kiến trúc + màn hình (trọng tâm: **review từng PDF**) + lộ trình + đóng gói.
- [02-llm-analysis.md](02-llm-analysis.md) — hybrid: **ratio_engine local tất định + LLM diễn giải**, ranh giới privacy, schema gửi đi, consent UX, lộ trình.

## Nguyên tắc xuyên suốt
1. **Lõi OCR Python (`bctc/`) giữ nguyên** — không vứt bỏ thành quả; UI mới gọi qua sidecar.
2. **Dữ liệu scan không rời máy**; chỉ tỉ số tổng hợp (có đồng ý) mới lên cloud.
3. **Số học tính local & tất định; LLM chỉ diễn giải** (không bịa số) — cùng triết lý B-A3.
4. **Phase build dùng skill** design-taste-frontend / ui-ux-pro-max / shadcn MCP.

## Việc còn mở (sau khi chốt thiết kế)
- Chốt techstack #3 → POC đóng gói Python sidecar trong vỏ chọn.
- Quay lại **#1 B-A3** (cần 3 `bench/truth/*.draft.json` đã sửa để đo cell-accuracy).
- Coverage **ngân hàng/TCTD** (template riêng) — còn tồn từ phase trước.
