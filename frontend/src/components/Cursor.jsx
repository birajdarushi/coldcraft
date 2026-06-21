import { useEffect, useRef } from "react";

/**
 * Decorative cursor accent: a blue dot inside a dark ring that sit directly
 * under the pointer. The native cursor is kept (drawn on top by the OS); both
 * the dot and ring track the pointer exactly with no trailing.
 */
export default function Cursor() {
  const dotRef = useRef(null);
  const ringRef = useRef(null);

  useEffect(() => {
    if (!window.matchMedia("(pointer: fine)").matches) return;
    const dot = dotRef.current;
    const ring = ringRef.current;
    if (!dot || !ring) return;

    const onMove = (e) => {
      const t = `translate(${e.clientX}px, ${e.clientY}px)`;
      dot.style.transform = t;
      ring.style.transform = t;
    };
    const down = () => ring.classList.add("cursor-down");
    const up = () => ring.classList.remove("cursor-down");

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mousedown", down);
    window.addEventListener("mouseup", up);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mousedown", down);
      window.removeEventListener("mouseup", up);
    };
  }, []);

  return (
    <>
      <div ref={ringRef} className="cursor-ring" aria-hidden="true" />
      <div ref={dotRef} className="cursor-dot" aria-hidden="true" />
    </>
  );
}
