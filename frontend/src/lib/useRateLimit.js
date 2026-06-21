import { useCallback, useEffect, useState } from "react";

// Shows a countdown after a Gemini rate-limit (429) so the user knows when the
// per-minute window clears. Usage:
//   const rl = useRateLimit();
//   catch (e) { if (rl.isRateLimit(e)) rl.start(); }
//   <button disabled={rl.active}>… {rl.active && `(retry in ${rl.remaining}s)`}
export function useRateLimit() {
  const [until, setUntil] = useState(0); // epoch ms when retry is allowed
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (until <= Date.now()) return;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [until]);

  const remaining = Math.max(0, Math.ceil((until - now) / 1000));
  const active = remaining > 0;

  const start = useCallback((seconds = 60) => {
    setUntil(Date.now() + seconds * 1000);
    setNow(Date.now());
  }, []);

  const isRateLimit = useCallback(
    (e) => e?.status === 429 || /rate limit/i.test(e?.detail || e?.message || ""),
    []
  );

  return { active, remaining, start, isRateLimit };
}
