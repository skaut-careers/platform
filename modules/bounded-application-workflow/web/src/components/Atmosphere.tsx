/** Quiet nature accents — decorative only. */
export function Atmosphere() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="sun-glow" />

      <svg
        className="absolute bottom-0 left-0 h-36 w-full text-forest/10"
        viewBox="0 0 1200 160"
        preserveAspectRatio="none"
      >
        <path
          d="M0 160 V100 C200 68 300 120 460 88 C620 56 720 110 880 82 C1020 58 1100 100 1200 76 V160 Z"
          fill="currentColor"
        />
        <path
          d="M0 160 V122 C240 104 360 138 520 118 C700 94 840 136 1000 116 C1100 104 1160 122 1200 118 V160 Z"
          className="fill-[#82825c]/18"
        />
      </svg>

      <svg
        className="absolute right-10 top-24 h-28 w-28 text-muted/20"
        viewBox="0 0 120 120"
        fill="currentColor"
      >
        <ellipse cx="40" cy="78" rx="6" ry="10" transform="rotate(-18 40 78)" />
        <ellipse cx="40" cy="78" rx="6" ry="10" transform="rotate(42 40 78)" />
        <ellipse cx="40" cy="78" rx="6" ry="10" transform="rotate(102 40 78)" />
        <circle cx="40" cy="78" r="3" className="fill-[#d4b56a]/55" />
      </svg>
    </div>
  );
}
