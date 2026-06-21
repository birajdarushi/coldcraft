/**
 * Coldcraft brand mark — a solid square framing a smaller square, with an
 * accent square notched into the bottom-right corner. Mirrors the mark used in
 * the app shell sidebar so the landing intro can "settle" into the same shape.
 * Supports starting the perimeter-walking animation on hover.
 */
export function LogoMark({ size = 28, className = "" }) {
  const inner = Math.round(size * 0.43);
  const corner = Math.max(4, Math.round(size * 0.29));
  const off = Math.max(2, Math.round(size * 0.07));
  const border = Math.max(1, Math.round(size * 0.07));

  return (
    <div 
      className={`brand-mark-container ${className}`}
      style={{
        "--logo-size": `${size}px`,
        "--logo-corner": `${corner}px`,
        "--logo-offset": `${off}px`,
        "--logo-border": `${border}px`,
        "--logo-inner": `${inner}px`,
      }}
    >
      <div className="brand-mark-logo" data-testid="logo-mark">
        <div className="brand-mark-inner" />
        <span className="brand-mark-accent" />
      </div>
    </div>
  );
}
