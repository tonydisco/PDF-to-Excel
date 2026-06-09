// Nền "water flow ma mị": 2 lớp conic xoáy NGƯỢC CHIỀU (blue ↔ teal ↔ sage)
// hòa vào nhau bằng mix-blend screen -> 2 màu cuộn vào nhau như nước.
// Thêm blob blue/coral cho chiều sâu, vignette gom sáng, noise mịn. Không bắt chuột.
export function Ambient() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-[oklch(0.13_0.006_262)]">
      {/* Lớp nước 1 — xoáy thuận */}
      <div
        className="water-swirl absolute -inset-[35%] blur-[90px]"
        style={{
          background:
            "conic-gradient(from 0deg at 50% 50%, oklch(0.58 0.17 250 / 88%), oklch(0.66 0.13 205 / 82%), oklch(0.72 0.11 165 / 85%), oklch(0.62 0.15 215 / 82%), oklch(0.58 0.17 250 / 88%))",
        }}
      />
      {/* Lớp nước 2 — xoáy ngược, lệch pha màu -> chỗ chồng nhau blend thành cyan */}
      <div
        className="water-swirl-rev absolute -inset-[35%] blur-[105px]"
        style={{
          background:
            "conic-gradient(from 150deg at 50% 50%, oklch(0.72 0.11 165 / 72%), oklch(0.56 0.17 255 / 85%), oklch(0.66 0.13 200 / 72%), oklch(0.6 0.16 250 / 85%), oklch(0.72 0.11 165 / 72%))",
        }}
      />

      {/* blob nhấn cho hồn aurora */}
      <div
        className="aurora-blob absolute -top-[18%] left-[8%] size-[46vw] rounded-full blur-[120px]"
        style={{ background: "radial-gradient(circle, oklch(0.6 0.17 250 / 75%), transparent 62%)", mixBlendMode: "screen" }}
      />
      <div
        className="aurora-blob-3 absolute bottom-[-22%] right-[6%] size-[40vw] rounded-full blur-[120px]"
        style={{ background: "radial-gradient(circle, oklch(0.66 0.16 38 / 55%), transparent 64%)", mixBlendMode: "screen" }}
      />

      {/* vignette gom sáng vào giữa, tối dần ra mép */}
      <div
        className="absolute inset-0"
        style={{ background: "radial-gradient(120% 115% at 50% 34%, transparent 42%, oklch(0.09 0.012 262 / 86%) 100%)" }}
      />
      <div className="noise-overlay absolute inset-0" />
    </div>
  )
}
