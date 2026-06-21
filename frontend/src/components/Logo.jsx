import { Square } from "lucide-react";

/**
 * Coldcraft brand mark — a solid square framing a smaller square, with an
 * accent square notched into the bottom-right corner. Mirrors the mark used in
 * the app shell sidebar so the landing intro can "settle" into the same shape.
 */
export function LogoMark({ size = 28, className = "" }) {
  const inner = Math.round(size * 0.43);
  const corner = Math.max(4, Math.round(size * 0.29));
  const off = Math.max(2, Math.round(size * 0.07));
  return (
    <div
      className={`relative bg-foreground flex items-center justify-center shrink-0 ${className}`}
      style={{ width: size, height: size }}
      data-testid="logo-mark"
    >
      <Square
        className="text-background"
        strokeWidth={3}
        fill="currentColor"
        style={{ width: inner, height: inner }}
      />
      <span
        className="absolute bg-accent"
        style={{ width: corner, height: corner, right: -off, bottom: -off }}
      />
    </div>
  );
}
