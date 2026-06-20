import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { Overline, Loading } from "./ui.jsx";

// Renders the immutable constitution floors straight from
// GET /api/v1/policies -> constitution_floors. Nothing hardcoded.
const ROW_DEFS = [
  ["daily_send_limit", "DAILY_CAP", (v) => `${v} / day`],
  ["max_company_emails_30d", "PER_COMPANY_30D", (v) => `${v}`],
  ["subject_max_chars", "SUBJECT_MAX", (v) => `${v} chars`],
  ["min_words", "MIN_WORDS", (v) => `${v}`],
  ["max_words", "MAX_WORDS", (v) => `${v}`],
  ["min_personalization", "PERSONALIZATION", (v) => `≥ ${v}`],
  ["max_exclamations", "EXCLAMATIONS", (v) => `≤ ${v}`],
  ["followup_days", "FOLLOWUP_DAYS", (v) => `[${(v || []).join(", ")}]`],
  ["qa_max_retries", "QA_RETRIES", (v) => `${v}`],
  ["min_match_score", "MIN_MATCH_SCORE", (v) => `${v}`],
];

export default function ConstitutionPanel({ className = "" }) {
  const [floors, setFloors] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api
      .getPolicies()
      .then((p) => setFloors(p?.constitution_floors || null))
      .catch(() => setError(true));
  }, []);

  return (
    <aside
      data-testid="constitution-panel"
      className={`border border-dashed border-border bg-surface p-4 ${className}`}
    >
      <div className="flex items-center justify-between mb-1">
        <Overline>CONSTITUTION</Overline>
        <span className="font-mono text-[9px] text-muted-foreground/60">HARD LIMITS</span>
      </div>
      <p className="font-mono text-[10px] leading-relaxed text-muted-foreground mb-3">
        Immutable limits from the API. Policies may tighten, never loosen.
      </p>
      {error ? (
        <div className="font-mono text-[10px] text-red-500 uppercase tracking-wider">ERR · /policies unreachable</div>
      ) : !floors ? (
        <Loading label="LOADING FLOORS…" />
      ) : (
        <dl className="divide-y divide-border/70">
          {ROW_DEFS.filter(([k]) => floors[k] !== undefined).map(([k, label, fmt]) => (
            <div key={k} className="flex items-center justify-between py-1.5">
              <dt className="font-mono text-[10px] tracking-wider text-muted-foreground">{label}</dt>
              <dd className="font-mono text-[11px] font-semibold tabular-nums">{fmt(floors[k])}</dd>
            </div>
          ))}
        </dl>
      )}
    </aside>
  );
}
