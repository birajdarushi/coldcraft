import { Lock } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import { Panel, Banner, Overline, PlannedBadge, Button } from "../components/ui.jsx";

// These screens map to endpoints that do not exist yet (Phase 3–4).
// With mock data removed, they honestly show the planned contract and
// disabled controls instead of fabricating rows.

function NotImplemented({ endpoints, summary }) {
  return (
    <div className="space-y-4 max-w-3xl">
      <Banner tone="warn">
        <Lock className="inline w-3 h-3 mr-1 -mt-0.5" />
        ENDPOINT NOT IMPLEMENTED — backend route does not exist yet. No data to display.
      </Banner>
      <Panel title="Planned contract" code="forward spec">
        <p className="font-mono text-[12px] leading-relaxed text-foreground/90 mb-3">{summary}</p>
        <Overline>Intended endpoints</Overline>
        <ul className="mt-2 space-y-1">
          {endpoints.map((e) => (
            <li key={e} className="font-mono text-[11px] text-muted-foreground">
              <span className="text-accent">▸</span> {e}
            </li>
          ))}
        </ul>
        <div className="mt-4">
          <Button variant="secondary" disabled>Unavailable</Button>
        </div>
      </Panel>
    </div>
  );
}

export function Workflow() {
  return (
    <AppShell title="Workflow" subtitle="// PHASE 2 · TARGET-COMPANY ORCHESTRATION" right={<PlannedBadge />}>
      <div className="p-5">
        <NotImplemented
          summary="One action orchestrates the upstream funnel for a company: intel → matched jobs → draft suggestion. Mailer is blocked if intel is incomplete (same research threshold as Compose)."
          endpoints={["POST /api/v1/workflows/target-company"]}
        />
      </div>
    </AppShell>
  );
}

export function Followups() {
  return (
    <AppShell title="Follow-ups" subtitle="// PHASE 3 · FOLLOW-UP WORKER MONITOR" right={<PlannedBadge />}>
      <div className="p-5">
        <NotImplemented
          summary="A worker processes due follow-ups (respecting features.auto_followups). Tasks have status (scheduled / sent / cancelled). Replies cancel a sequence. A manual 'run now' trigger is available."
          endpoints={["POST /api/v1/workers/followups/run", "GET /api/v1/tasks"]}
        />
      </div>
    </AppShell>
  );
}

export function Replies() {
  return (
    <AppShell title="Replies" subtitle="// PHASE 3 · REPLY INGESTION" right={<PlannedBadge />}>
      <div className="p-5">
        <NotImplemented
          summary="Inbound replies (webhook or IMAP poll) set campaign status=replied and cancel pending follow-ups. Reply handling at POST /campaigns/{id}/reply already exists and is wired in the campaign detail screen."
          endpoints={["POST /api/v1/webhooks/gmail", "POST /api/v1/campaigns/{id}/reply (live)"]}
        />
      </div>
    </AppShell>
  );
}

export function NetworkPaths() {
  return (
    <AppShell title="Network" subtitle="// PHASE 4 · WARM PATHS" right={<PlannedBadge />}>
      <div className="p-5">
        <NotImplemented
          summary="Import a LinkedIn CSV and surface the top-ranked warm intro paths to a target company, with an advisory reply-probability once enough labeled sends exist (ML after 30+ outreach events)."
          endpoints={["POST /api/v1/network/import", "GET /api/v1/network/paths?company=X"]}
        />
      </div>
    </AppShell>
  );
}
