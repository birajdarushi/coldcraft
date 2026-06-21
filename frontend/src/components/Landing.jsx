import { useEffect, useRef, useState } from "react";
import { LogoMark } from "./Logo.jsx";

const SEEN_KEY = "coldcraft-intro-seen";

/**
 * Intro splash. The logo starts large and centered; on the first click, scroll,
 * touch, or key press it animates ("tracks") up to the top-left where the app
 * shell's brand mark lives, then unmounts to reveal the app. Shows once per tab
 * session so in-session navigation doesn't replay it.
 */
export default function Landing() {
  const [visible, setVisible] = useState(() => {
    if (typeof window === "undefined") return false;
    return sessionStorage.getItem(SEEN_KEY) !== "1";
  });
  const [leaving, setLeaving] = useState(false);
  const enteredRef = useRef(false);

  useEffect(() => {
    if (!visible) return;
    const enter = () => {
      if (enteredRef.current) return;
      enteredRef.current = true;
      sessionStorage.setItem(SEEN_KEY, "1");
      setLeaving(true);
      window.setTimeout(() => setVisible(false), 900);
    };
    const onKey = (e) => {
      if (["Enter", " ", "Escape", "ArrowDown"].includes(e.key)) enter();
    };
    window.addEventListener("click", enter);
    window.addEventListener("wheel", enter, { passive: true });
    window.addEventListener("touchstart", enter, { passive: true });
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("click", enter);
      window.removeEventListener("wheel", enter);
      window.removeEventListener("touchstart", enter);
      window.removeEventListener("keydown", onKey);
    };
  }, [visible]);

  if (!visible) return null;

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Enter Coldcraft"
      data-testid="landing-intro"
      className={`fixed inset-0 z-50 grid-bg bg-background flex items-center justify-center cursor-pointer select-none transition-opacity duration-700 ${
        leaving ? "opacity-0 pointer-events-none" : "opacity-100"
      }`}
    >
      <div
        className={`intro-move flex flex-col items-center ${leaving ? "" : "intro-in"}`}
        style={
          leaving
            ? {
                transform:
                  "translate(calc(-50vw + 150px), calc(-50vh + 32px)) scale(0.33)",
                opacity: 0,
              }
            : undefined
        }
      >
        <LogoMark size={84} />
        <div className="text-center leading-none mt-7">
          <div className="font-sans font-extrabold tracking-tighter uppercase text-5xl">
            Coldcraft
          </div>
          <div className="font-mono text-[11px] tracking-[0.4em] text-muted-foreground mt-3">
            GTM·ENGINE
          </div>
        </div>
        <div
          className={`font-mono text-[10px] tracking-[0.35em] uppercase text-muted-foreground mt-12 transition-opacity duration-300 ${
            leaving ? "opacity-0" : "opacity-100 animate-pulse"
          }`}
        >
          Click or scroll to enter
        </div>
      </div>
    </div>
  );
}
