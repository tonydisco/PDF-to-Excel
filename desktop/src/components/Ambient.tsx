// Nền tối SẠCH + "dòng nước" trong VÙNG NHỎ (xanh lá + navy thẫm).
// Tối ưu hiệu năng: displacement TĨNH (tính 1 lần, cache) + chuyển động bằng
// transform xoáy (GPU rẻ) -> mượt, không tính lại noise mỗi frame.
const SOFT_MASK = "radial-gradient(circle at 50% 50%, #000 24%, transparent 70%)"

export function Ambient() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden bg-[oklch(0.15_0.005_262)]">
      {/* Bộ lọc chất lỏng TĨNH: làm méo khối màu thành dạng nước (không animate -> rẻ) */}
      <svg className="absolute size-0" aria-hidden focusable="false">
        <defs>
          <filter id="liquid" x="-30%" y="-30%" width="160%" height="160%">
            <feTurbulence type="fractalNoise" baseFrequency="0.011 0.014" numOctaves="2" seed="7" result="noise" />
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="120" xChannelSelector="R" yChannelSelector="G" />
          </filter>
        </defs>
      </svg>

      {/* Orb chính (góc trên-trái): 2 lớp xoáy ngược chiều qua warp tĩnh -> chảy/cuộn */}
      <div
        className="absolute -top-[16%] -left-[8%] size-[42vw]"
        style={{ maskImage: SOFT_MASK, WebkitMaskImage: SOFT_MASK }}
      >
        <div
          className="water-swirl absolute -inset-1/4"
          style={{
            filter: "url(#liquid) blur(36px)",
            background:
              "conic-gradient(from 0deg at 50% 50%, oklch(0.62 0.13 165 / 85%), oklch(0.40 0.13 256 / 92%), oklch(0.62 0.13 165 / 80%), oklch(0.36 0.12 258 / 92%), oklch(0.62 0.13 165 / 85%))",
          }}
        />
        <div
          className="water-swirl-rev absolute -inset-1/4"
          style={{
            filter: "url(#liquid) blur(42px)",
            background:
              "conic-gradient(from 140deg at 50% 50%, oklch(0.38 0.13 256 / 88%), oklch(0.64 0.12 168 / 75%), oklch(0.34 0.12 258 / 90%), oklch(0.6 0.13 162 / 75%), oklch(0.38 0.13 256 / 88%))",
          }}
        />
      </div>

      {/* Orb phụ (góc dưới-phải): blob nhẹ, breathing (rẻ, không filter) */}
      <div
        className="aurora-blob-3 absolute -bottom-[16%] right-[-6%] size-[28vw] rounded-full blur-[90px]"
        style={{ background: "radial-gradient(circle, oklch(0.42 0.12 256 / 70%), oklch(0.58 0.12 168 / 40%), transparent 68%)" }}
      />

      <div className="noise-overlay absolute inset-0" />
    </div>
  )
}
